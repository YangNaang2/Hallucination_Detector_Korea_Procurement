"""CPU multilingual-E5-small, full token-window coverage, parent-preserving retrieval."""
import argparse
import gc
import time

import numpy as np

import rag_pilot as p

MODEL = p.WORK / 'e5'
REVISION = '614241f622f53c4eeff9890bdc4f31cfecc418b3'


class Encoder:
    def __init__(self):
        import torch
        from transformers import AutoModel, AutoTokenizer
        self.torch = torch
        torch.set_num_threads(4)
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA GPU is required for embedding rebuild')
        self.device = torch.device('cuda')
        self.gpu_name = torch.cuda.get_device_name(0)
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
        self.model = AutoModel.from_pretrained(MODEL, local_files_only=True, trust_remote_code=False).to(self.device)
        self.model.eval()

    def window_ids(self, text, prefix):
        ids = self.tokenizer(prefix + text, add_special_tokens=False)['input_ids']
        # Every token appears; prefix also present in each continuation window.
        prefix_ids = self.tokenizer(prefix, add_special_tokens=False)['input_ids']
        windows = []
        for start in range(0, max(1, len(ids)), 344):
            window = ids[start:start+384]
            if start:
                window = prefix_ids + window
            windows.append(self.tokenizer.build_inputs_with_special_tokens(window))
            if start + 384 >= len(ids):
                break
        if any(len(w) > 512 for w in windows):
            raise ValueError('embedding window exceeds tokenizer limit')
        return windows

    def encode_ids(self, batch):
        torch = self.torch
        padded = self.tokenizer.pad({'input_ids':batch}, padding=True, return_tensors='pt').to(self.device)
        with torch.inference_mode():
            hidden = self.model(**padded).last_hidden_state
            mask = padded['attention_mask'].unsqueeze(-1).bool()
            mean = hidden.masked_fill(~mask, 0).sum(1) / mask.sum(1)
            output = torch.nn.functional.normalize(mean, p=2, dim=1)
        return output.cpu().numpy().astype('float32')


def build():
    chunks = p.load_chunks()
    encoder = Encoder()
    windows, parents, counts = [], [], []
    for i,c in enumerate(chunks):
        ws = encoder.window_ids(c['text'], 'passage: ')
        counts.append(len(ws))
        windows.extend(ws)
        parents.extend([i]*len(ws))
    vectors = []
    start = time.perf_counter()
    for i in range(0, len(windows), 8):
        vectors.append(encoder.encode_ids(windows[i:i+8]))
        if i % 200 == 0:
            print('embedded', i, '/', len(windows), 'seconds', round(time.perf_counter()-start), flush=True)
    np.savez(p.WORK / 'vectors.npz', vectors=np.concatenate(vectors), parents=np.array(parents),
             chunk_ids=np.array([c['chunk_id'] for c in chunks]))
    manifest = p.read(p.OUT/'index_manifest.json')
    config = dict(model='intfloat/multilingual-e5-small', revision=REVISION, license='MIT', device='cuda', gpu_name=encoder.gpu_name,
                  precision='float32', pooling='attention-mask mean', normalization='L2',
                  query_prefix='query: ', passage_prefix='passage: ', limit_tokens=512,
                  token_window=384, stride=344, truncation=False,
                  parent_chunks=len(chunks), embedding_windows=len(windows),
                  max_windows_per_parent=max(counts), dimension=384, batch_size=8, threads=4,
                  build_seconds=time.perf_counter()-start, corpus_hash=manifest['corpus_hash'],
                  note='parent entity text remains intact for generation; similarity is max over its windows')
    p.dump(p.OUT/'embedding_config.json', config)
    manifest['vector_index'] = 'indexed_local_numpy'
    p.dump(p.OUT/'index_manifest.json', manifest)
    print('embedding complete', len(windows), flush=True)


class Dense:
    def __init__(self):
        config = p.read(p.OUT/'embedding_config.json')
        if config['corpus_hash'] != p.read(p.OUT/'index_manifest.json')['corpus_hash']:
            raise ValueError('stale vector index')
        data = np.load(p.WORK/'vectors.npz', allow_pickle=False)
        self.vectors, self.parents = data['vectors'], data['parents']
        self.ids = data['chunk_ids'].tolist()
        self.positions = {cid:i for i,cid in enumerate(self.ids)}
        queries = np.load(p.WORK/'query_vectors.npz', allow_pickle=False)
        self.query_vectors = dict(zip(queries['hashes'].tolist(), queries['vectors']))
        if str(queries['revision']) != REVISION:
            raise ValueError('stale query embedding model')

    def scores(self, question, permitted):
        # Restrict vector rows before similarity, not after selecting global neighbors.
        allowed = {self.positions[c['chunk_id']] for c in permitted}
        selected = np.array([i for i,parent in enumerate(self.parents) if int(parent) in allowed])
        key = p.digest(question)
        if key not in self.query_vectors:
            raise ValueError('precompute this query embedding before starting generation model')
        q = self.query_vectors[key]
        similarities = (self.vectors[selected] @ q.T).max(axis=1)
        scores = {}
        for i, score in zip(selected, similarities):
            parent = int(self.parents[i])
            scores[parent] = max(scores.get(parent, -1), float(score))
        return [scores[self.positions[c['chunk_id']]] for c in permitted]


def query_vectors():
    """Precompute query-only vectors, then exit to release model RAM before generation.

    This cache contains no answers, retrieved documents, conversation or session state.
    Runtime ACL is still applied before scoring document vectors.
    """
    encoder = Encoder()
    hashes, vectors = [], []
    for request in p.read(p.OUT/'runtime/requests.json'):
        p.no_gold(request)
        question = request['question']
        hashes.append(p.digest(question))
        encoded = encoder.encode_ids(encoder.window_ids(question, 'query: '))
        if len(encoded) != 1:
            raise ValueError('long multi-window query needs separate rag query policy')
        vectors.append(encoded)
    np.savez(p.WORK/'query_vectors.npz', hashes=np.array(hashes), vectors=np.array(vectors), revision=np.array(REVISION))
    print('query vectors complete',len(hashes),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--queries-only',action='store_true')
    args=parser.parse_args()
    if not args.queries_only:build()
    query_vectors()
