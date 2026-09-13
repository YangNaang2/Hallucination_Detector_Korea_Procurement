"""Query-only context routing. No evaluation dataset, labels or gold evidence access."""
import re

METADATA_HEADERS = {'## scenario_id', '## scenario_version', '## company_id', '## version', '## bid_key'}


def needs_public(req):
    return req['scenario_id'].startswith('SC-L1-') or bool(re.search(
        r'공고|참가|요건|하한|대체|조건|공개.*협약', req['question']))


def candidates_for_query(req, candidates):
    # Identifiers remain available as document/chunk metadata and the request header.
    return [c for c in candidates if c['text'].splitlines()[0] not in METADATA_HEADERS
            and (needs_public(req) or c['security_level'] != 'L1')]


def preferred_public(query, candidates, order):
    public = [i for i in order if candidates[i]['security_level']=='L1']
    # An amount threshold must come from a performance-condition paragraph, not a
    # total project budget or an empty price/consortium form. This is not a gold lookup.
    if '실적' in query and re.search(r'금액|하한|상한', query):
        threshold = [i for i in public if '실적' in candidates[i]['text']
                     and '금액' in candidates[i]['text']
                     and re.search(r'이상|이하|초과|미만', candidates[i]['text'])]
        if threshold:
            return threshold[:1]
    return public[:1]


def named_entities(query, candidates, order):
    identifiers=set(re.findall(r'C\d{2}-(?:PRJ|CERT|SERVICE|P)-\d+',query))
    ids = [i for i in order if candidates[i]['security_level']!='L1'
            and identifiers.intersection(re.findall(r'C\d{2}-(?:PRJ|CERT|SERVICE|P)-\d+',candidates[i]['text'].splitlines()[0]))]
    code_matches=[]
    for i in order:
        if candidates[i]['security_level']=='L1':continue
        match=re.search(r'^\| (?:state_change / )?업종·인증 코드 \| ([^|]+) \|',candidates[i]['text'],re.M)
        if match and match[1].strip() in query:
            code_matches.append((i,match[1].strip()))
    # Preserve both sides when multiple business codes are explicitly compared.
    # Read only the already-authorized candidate records, not a gold/company lookup.
    if len({code for _,code in code_matches})>=2:
        ids += [i for i,_ in code_matches]
    return list(dict.fromkeys(ids))
