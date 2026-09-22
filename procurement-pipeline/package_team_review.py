"""Build four offline reviewer packs; raw sources stay in ignored work/ only."""
import argparse
import hashlib
import html
import json
import sqlite3
import zipfile
from pathlib import Path
from urllib.parse import quote


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def page(title, body):
    return '<!doctype html><html lang="ko"><meta charset="utf-8"><title>' + html.escape(title) + '''</title>
<style>body{max-width:1100px;margin:36px auto;padding:0 24px;font:16px/1.8 system-ui;color:#172235;background:#f5f7fa}article,section{background:white;padding:24px;margin:24px 0;border:1px solid #cdd6e1;border-radius:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}summary{cursor:pointer;font-weight:bold;color:#165b91}a{color:#165b91}h1,h2,h3{line-height:1.4}.extra{border-left:6px solid #c68117;padding:16px}.meta{color:#556479;font-size:13px;overflow-wrap:anywhere}nav{position:sticky;top:0;background:#e8eff7;padding:10px}details{margin:16px 0}table{border-collapse:collapse}td,th{padding:8px;border:1px solid #ccc}</style>''' + body + '</html>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--source-root', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    pilot = root / 'project-docs/환각라벨링/pilot-25-v1'
    delivery = pilot / 'team-delivery'
    out = root / 'work/team-review-delivery'
    out.mkdir(parents=True, exist_ok=True)
    labels = [json.loads(x) for x in (pilot / 'labels_draft.jsonl').read_text(encoding='utf-8').splitlines()]
    by_id = {r['question_id']: r for r in labels}
    groups = json.loads((delivery / 'assignments.json').read_text(encoding='utf-8'))['groups']
    ids = [q for g in groups for q in g['question_ids']]
    assert len(groups) == 4 and len(ids) == len(set(ids)) == 25 and set(ids) == set(by_id)
    assert [len(g['question_ids']) for g in groups] == [7, 6, 6, 6]
    cache = json.loads((args.source_root / 'source-texts.json').read_text(encoding='utf-8'))
    cache_by_path = {r['relative'].replace('\\', '/'): r for r in cache}
    db = sqlite3.connect((root / 'work/rag-pilot/index.sqlite').as_uri() + '?mode=ro', uri=True)
    report = {'reviewers': 4, 'questions': 25, 'human_approval': 'pending', 'training_ready': False,
              'checks': ['unique complete assignment', 'chunk hashes and canonical offsets', 'evidence exact quotes',
                         'source binary hashes', 'ZIP CRC and every entry hash', 'no extra package files'], 'packages': []}
    esc = html.escape
    for n, group in enumerate(groups, 1):
        rows = [by_id[q] for q in group['question_ids']]
        pack = out / group['team_id']
        pack.mkdir(exist_ok=True)
        expected_files = set()

        def write(rel, data):
            dest = pack / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            expected_files.add(rel)
            return rel

        def source(p):
            rel = p['path'].replace('\\', '/')
            if p['security_level'] == 'L1':
                record = cache_by_path[rel]
                binary = (args.source_root / Path(rel)).read_bytes()
                assert sha(binary) == record['sha256'] == p['sha256']
                text = record['text']
                dest = '자료/' + rel
            else:
                original = (root / rel).resolve()
                assert original.is_relative_to(root)
                binary = original.read_bytes()
                doc = json.loads(binary)
                text = doc['content']
                assert doc['company_id'] == p['company_id']
                dest = '자료/' + rel
            write(dest, binary)
            assert text[p['text_start']:p['text_end']] == p['text']
            return dest

        title = f'팀원 {n} · 환각 구절 검수 {len(rows)}문항'
        instruction = (delivery / '작업지시서.md').read_text(encoding='utf-8')
        write('작업지시서.md', instruction.encode('utf-8'))
        write('GUIDELINES.md', (pilot / 'GUIDELINES.md').read_bytes())
        # Preformatted Markdown remains fully readable without third-party scripts.
        write('00_작업지시서.html', page(title, '<h1>' + title + '</h1><p><a href="01_검수도움.html">질문·답변·근거 열기 →</a></p><section><pre>' + esc(instruction) + '</pre></section>').encode('utf-8'))
        workbook = next((delivery / group['team_id']).glob('*.xlsx'))
        write(workbook.name, workbook.read_bytes())
        body = '<h1>' + title + '</h1><p>에이전트 초안은 정답이 아닙니다. 질문·실제 답변·입력 근거를 먼저 읽고, Excel의 노란 입력 칸에 검수 의견을 남기세요.</p>'
        body += '<p>이 파일은 여러 회사의 L2/L3를 포함한 팀 내부 평가용 자료입니다. 실제 사용자 권한에 따른 서비스 화면이나 검색 입력으로 사용하지 않습니다.</p>'
        body += '<nav>' + ' · '.join(f'<a href="#{r["question_id"]}">{i+1}번</a>' for i, r in enumerate(rows)) + '</nav>'
        chunk_count = 0
        for r in rows:
            assert r['human_approval'] == 'pending' and r['training_ready'] is False
            assert sha(r['actual_answer'].encode()) == r['answer_sha256']
            body += f'<article id="{r["question_id"]}"><h2>{esc(r["question_id"])}</h2><p class="meta">{esc(r["company_id"])} · 공고 {esc(r["bid_key"])} · 시나리오 {esc(r["scenario_id"])} / {esc(r["scenario_version"])}</p>'
            body += '<h3>질문</h3><pre>' + esc(r['question']) + '</pre><h3>실제 생성 답변 — 원문 그대로</h3><pre>' + esc(r['actual_answer']) + '</pre><h3>생성 시 입력 근거</h3>'
            entries = [(m, False) for m in r['prompt_context_manifest']]
            entries += [(e, True) for e in r['evidence'] if e['scope'] != 'prompt_context']
            seen = set()
            for m, extra in entries:
                cid = m['chunk_id']
                if (cid, extra) in seen:
                    continue
                seen.add((cid, extra))
                p = json.loads(db.execute('SELECT payload FROM corpus WHERE chunk_id=?', (cid,)).fetchone()[0])
                assert sha(p['text'].encode()) == m.get('text_sha256', m.get('chunk_sha256'))
                source_link = source(p)
                if not extra and p.get('company_id'):
                    assert p['company_id'] == r['company_id']
                    assert p['security_level'] in r['user_context']['allowed_security_levels']
                relevant = [e for e in r['evidence'] if e['chunk_id'] == cid]
                for e in relevant:
                    assert p['text'][e['start']-p['text_start']:e['end']-p['text_start']] == e['quote']
                label = '추가 검수 전용 — 모델 입력에 없었음' if extra else f'[{m["citation"]}]'
                body += f'<details class="{"extra" if extra else ""}" open><summary>{label} · {esc(p["security_level"])} · {"합성 회사 문서" if p.get("company_id") else "실제 공고"}</summary>'
                body += f'<p class="meta">{esc(cid)}<br>정본 문자 위치 [{p["text_start"]}, {p["text_end"]}) · <a href="{quote(source_link)}">원문 파일 열기</a><br>{esc(p["path"])}</p>'
                body += '<pre>' + esc(p['text']) + '</pre>'
                body += '<p class="meta">검수시트 근거 ID: ' + esc(', '.join(e['evidence_id'] for e in relevant) or '전체 입력 참고') + '</p></details>'
                chunk_count += 1
            body += '<details><summary>근거 확인 후 열기: 기대답 · 에이전트 구절 초안 · 품질 메모</summary><h3>기대답 (검수 필요)</h3><pre>' + esc(r['expected_answer']) + '</pre><p>' + esc(r['agent_note']) + '</p>'
            for s in r['draft_spans'] + r['review_candidates']:
                body += '<section><b>' + esc(s.get('span_id', s.get('candidate_id', '후보'))) + ' · ' + esc(s['label']) + '</b><pre>' + esc(s['quote']) + '</pre><p>' + esc(s['reason']) + '</p><p class="meta">' + esc(', '.join(s['evidence_ids'])) + '</p></section>'
            body += '<pre>' + esc('\n'.join(r['quality_issues'])) + '</pre></details></article>'
        write('01_검수도움.html', page(title, body).encode('utf-8'))
        # The workbook's common guide links to review.html; retain a working alias.
        write('review.html', page(title, body).encode('utf-8'))
        manifest = {'team_id': group['team_id'], 'question_ids': group['question_ids'], 'human_approval': 'pending',
                    'purpose': 'offline internal human review; never RAG input or training approval',
                    'files': [{'path': p, 'sha256': sha((pack / p).read_bytes())} for p in sorted(expected_files)]}
        write('manifest.json', (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode())
        assert {p.relative_to(pack).as_posix() for p in pack.rglob('*') if p.is_file()} == expected_files, 'Unexpected stale files; use a fresh output directory'
        zipname = f'팀원{n}_환각검수_{len(rows)}문항.zip'
        with zipfile.ZipFile(out / zipname, 'w', zipfile.ZIP_DEFLATED) as z:
            for rel in sorted(expected_files):
                z.write(pack / rel, arcname=rel)
        with zipfile.ZipFile(out / zipname) as z:
            assert z.testzip() is None
            assert set(z.namelist()) == expected_files
            for rel in expected_files:
                assert sha(z.read(rel)) == sha((pack / rel).read_bytes())
        report['packages'].append({'team_id': group['team_id'], 'questions': len(rows), 'span_rows': group['span_rows'],
                                   'context_chunk_occurrences': chunk_count, 'files': len(expected_files), 'zip': zipname,
                                   'zip_bytes': (out / zipname).stat().st_size, 'zip_sha256': sha((out / zipname).read_bytes())})
    db.close()
    dump(delivery / 'package_validation.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
