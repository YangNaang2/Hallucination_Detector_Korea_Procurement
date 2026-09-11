"""수집기(narajangteo_ingest.py)가 '파싱 실패'로 캐시해 둔 parsed JSON을 옆으로 치워서 재실행 시 다시 파싱되게 한다.

배경: 수집기는 parsed/<sha>.json 이 존재하면 내용이 status=failed 여도 그대로 재사용한다(cached=True).
      파서가 설치되지 않은 상태에서 한 번 돌면 실패 결과가 캐시에 남아, 이후 재실행해도 다시 파싱하지 않는다.
동작: manifest.jsonl 에서 status=failed 인 행의 parsed_path 를 parsed_failed_backup/ 로 이동한다. 삭제하지 않는다.
      raw 원본은 건드리지 않으므로 재실행 시 다운로드는 생략되고 파싱만 다시 한다.

사용:
  python g2b_reset_failed_parse.py --src /home/piai/다운로드/narajangteo_rag_ingest/data/2026-04           # 대상만 세기
  python g2b_reset_failed_parse.py --src /home/piai/다운로드/narajangteo_rag_ingest/data/2026-04 --apply   # 실제 이동
그 다음 수집기를 같은 인자로 다시 실행한다:
  python narajangteo_ingest.py --year 2026 --month 4 --out ./data
"""
import argparse
import json
from pathlib import Path
import shutil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help='manifest.jsonl 과 parsed/ 가 있는 월 폴더')
    ap.add_argument('--apply', action='store_true', help='실제로 이동한다. 없으면 개수만 출력')
    ap.add_argument('--status', default='failed', help='이동 대상 status (기본 failed, 예: failed,low_quality)')
    args = ap.parse_args()
    src = Path(args.src)
    manifest = src / 'manifest.jsonl'
    if not manifest.is_file():
        raise SystemExit(f'없음: {manifest}')
    backup = src / 'parsed_failed_backup'
    targets = set(s.strip() for s in args.status.split(','))
    seen, moved, missing = set(), 0, 0
    with manifest.open(encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            p = row.get('parsed_path')
            if row.get('status') not in targets or not p or p in seen:
                continue
            seen.add(p)
            path = Path(p)
            if not path.is_file():
                missing += 1
                continue
            if args.apply:
                backup.mkdir(exist_ok=True)
                shutil.move(str(path), str(backup / path.name))
            moved += 1
    verb = '이동' if args.apply else '이동 예정'
    print(f'status in {sorted(targets)}: parsed JSON {verb} {moved}개, 이미 없음 {missing}개, 백업 폴더 {backup}')
    if not args.apply:
        print('실제로 이동하려면 --apply 를 붙여 다시 실행')


if __name__ == '__main__':
    main()
