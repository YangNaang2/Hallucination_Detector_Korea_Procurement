# 워크스테이션 후속 실행 — 원천 입력 대기, 275개 미실행

2026-09-13. 기준 e8d745f를 포함하는 origin/main ce5af2c에서 전용 브랜치 rag/workstation-275를 만들었다. 후속 변경은 발표용 구조도 7개 파일이며 RAG 코드는 변경되지 않았다. 기존 clone이나 AGENTS.md는 이 작업 폴더에서 발견하지 못했다. 프로젝트 진행현황 7절을 준수한다.

## 실제 상태

|구분|기존 유효 결과|신규 275|
|---|---:|---:|
|LLM 답변|20|0|
|LLM 없는 정상 차단|5|0|
|실행 실패|0|0|
|미실행|0|275|

고유 300개 중 처리된 것은 25개다. 입력 누락 때문에 시도하지 않은 275개를 실패·자료부족 정답·완료로 바꾸지 않았다. 기존 2개 재실행은 중복 집계하지 않는다. 기존 최신 선택표의 원시 파일 ID·상태를 대조하고 300 ID 집합에서 뺀 결과가 정확히 275개였다. `evaluation/selection.json`, `runtime/question_ids.json`, 정답 필드 없는 `runtime/requests.json`에 기록했다. 기존 데이터셋·split·회사 마스터·25개 결과는 보존했다.

기존 에이전트 검토: 핵심 수용 3, 인용 보완 4, 설명/계산 누락 5, 수정 필요 8, 정상 차단 5. 그 답변 오류는 이번 준비 작업으로 해결되었다고 주장하지 않는다. 신규 답변 내용 검토는 미실시, 사람 승인은 모두 pending, 환각 span 라벨링은 미실시다.

## 환경과 확인한 범위

Ubuntu 22.04.5, Xeon Silver 4210R 10코어/20스레드, RAM 약 62GiB. RTX A5000 PCI 장치는 감지되지만 실행 환경에 /dev/nvidia*가 없고 nvidia-smi가 실패했다. 로드된 커널 모듈 580.173.02와 설치된 사용자 라이브러리 580.178.04도 다르다. 실제 VRAM은 측정하지 못했다. GPU 가속은 사용하지 않았다. 재부팅·드라이버 변경은 수행하지 않았다.

분리된 `.venv-rag-workstation`에 저장소 지정 의존성과 CPU torch 2.14.0을 설치했다. 다른 환경은 수정하지 않았다. Qwen3-4B Q4_K_M과 multilingual-e5-small은 기존 revision으로 다운로드했으며 LFS 해시 및 Qwen3 기존 SHA를 검증했다. Linux CPU llama.cpp b10938 (f1e44dcc1) 버전과 모델 로딩·loopback 응답을 확인했다. context 4096, 최대 출력 768, CPU 8스레드 등 기존 프로필을 보존했다. 공개 인사 요청 smoke만 생성했고 300문항에 포함하지 않는다. 사용한 서버는 종료했다.

질의 275개는 E5로 약 11.95초에 임베딩했다. 문서 임베딩/색인은 없다. 짧은 인사나 질의 임베딩 시간으로 전체 RAG 완료 시간을 추정하지 않는다. 설치 직전 가용 디스크는 약 13GiB였으며 현황은 environment.json에 있다. 원천 이전 전 남은 공간을 확인한다.

## 원천 자료 이전이 필요한 이유

설정의 경로, /home/piai, /media/piai, /mnt, /tmp에서 기존 source-texts.json, index.sqlite, GGUF와 HWP/HWPX를 검색했지만 실행용 원천·캐시는 찾지 못했다. 이전 PC의 Windows 절대경로는 사용하지 않았다. 검색 범위 밖 다른 볼륨에 있다면 실제 경로를 제공해야 한다.

`sources/required.json`과 `sources/required.tsv`는 기존 L1 167문서/51공고의 공고번호·차수·문서 ID·파일명·상대경로·바이너리/정본 텍스트 SHA 목록이다. 첨부 ID는 기준 manifest에 없어 null로 명시했으며 만들어 넣지 않았다. 기존 제외 첨부 16개도 required.json에 이유와 함께 보존했다. 전체 기준은 223문서/3275부모 청크다. 신규 색인은 아직 없으므로 재구축 숫자를 주장하지 않는다.

공식 나라장터 [R26BK01415425-000 fileSeq 2](https://www.g2b.go.kr/pn/pnp/pnpe/UntyAtchFile/downloadFile.do?bidPbancNo=R26BK01415425&bidPbancOrd=000&fileSeq=2&fileType=&prcmBsneSeCd=03) 다운로드를 시험했다. PDF 247886바이트를 받았으나 기준 문서 해시와 불일치했다. `sources/recovery_probe.json`에 기록하고 원문은 무시되는 work/source-recovery에 두었다. 이를 기존 HWP나 전체 정본 파싱 캐시의 대체물로 색인하지 않았다. 이 한 건의 시험으로 모든 공식 자료가 확보 불가능하다고 단정하지 않는다. 동일 조건 비교를 위한 확실한 경로는 원래 PC에서 정본 캐시와 대응 원본을 이전하는 것이다.

이전 PC에서 `source-texts.json`과 거기에 연결된 원천 폴더를 복사한다. cache의 relative 경로(예: export/2026-04/.../원본/파일.hwp)가 source-root 아래에서 그대로 연결되도록 `work/source-transfer/raw/` 아래에 둔다. 원래 제외 16개도 가능하면 함께 옮긴다. 로컬 키·토큰은 이전하지 않는다. 기존 캐시가 없으면 동일 원본과 파서가 필요하며, 재파싱의 정본 텍스트 SHA/offset 차이를 별도 색인 버전으로 검토해야 한다. 평가 정답 인용, source bank, 추출시트를 전체 검색 자료로 대체하지 않는다.

## 직접 수정한 코드와 검증

- rag_pilot.dump: 임시 파일, flush/fsync, 원자적 replace로 문항/상태 저장 중단 시 이전 파일 보존.
- safe_path: Windows 상대경로 구분자를 Linux에서 처리하면서 절대경로·드라이브·상위 탈출 차단.
- rag_pilot.run: 명시 요청 경로, 중복 ID·금지 평가필드 검사. 기존 25개 기본값 보존.
- workstation_rag: 명시 dataset/ID 및 별도 output/work, 집합 차집합 준비, 문항별 append-only 시도, limit, 잠금, 재개/실패 명시 재시도. 성공만 골라 선택하지 않으며 최신 실패도 보존. 코드·질의·모델·색인·벡터 해시가 바뀌면 같은 run ID 재개 거절. 실행 필수 입력 확인 전에 문항을 완료나 실패로 기록하지 않음.
- 별도 Linux 다운로드/서버 실행기. 이전 Windows 설치기·Qwen2.5 다운로드를 새 실행에 사용하지 않음.
- 회사 입력 CSV 검사: Git의 LF 체크아웃을 CRLF로 정확 재구성한 SHA가 기존 기록과 일치하는 경우만 허용하고 그 사실 기록. 내용 변경 거부 검사를 추가. 원천 바이너리·정본 텍스트 해시 검사에는 이 예외를 적용하지 않음.

처음 166개 검사에서 CSV 줄바꿈 문제 1개가 발생했다. 수정 후 기존 158개 + 신규 9개 = 167개 통과했다(`validation/tests.json`, tests.txt). mock 기반 재개/중복/실패 보존/설정 변경 거부와 기존 ACL·계산·스키마 회귀 범위다. 실제 전체 원천 색인 무결성·275개 생성·내용 검토 통과를 의미하지 않는다. 현재 코드는 원천 도착 후 실제 작은 배치로 추가 검증해야 한다.

기존 REPORT의 검색 오류/합성 missing·보유주체·VAT/마진 문제는 읽어 확인했으나 실제 근거 없는 상태에서 새 계산기나 정답별 검색 규칙을 추가하지 않았다. 기존 25개를 먼저 개발·회귀 실행한다. 평가 275개 답변을 보고 이후 코드를 수정하면 해당 ID/split의 개발 노출을 기록하고 새 run ID로 영향 문항을 재실행한다.

## 재현 및 재개

아래 명령은 저장소 루트에서 실행한다. 다른 PC에서는 clone 경로로 cd한다. `work/` 자료는 git pull로 오지 않는다.

```bash
cd /home/piai/Documents/Codex/2026-09-13/files-pasted-by-the-user-ko/ko-lettucedetect
python3 -m venv .venv-rag-workstation
.venv-rag-workstation/bin/python -m pip install -r procurement-pipeline/requirements-rag-pilot.txt
.venv-rag-workstation/bin/python -m pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu
.venv-rag-workstation/bin/python procurement-pipeline/setup_workstation_rag.py
python3 procurement-pipeline/workstation_rag.py prepare
python3 procurement-pipeline/workstation_rag.py sources
# 원천 이전 및 required.json 대조 후 실행. 기존 25개 결과에는 쓰지 않음.
python3 procurement-pipeline/workstation_rag.py index --source-cache work/source-transfer/source-texts.json --source-root work/source-transfer/raw
.venv-rag-workstation/bin/python procurement-pipeline/workstation_rag.py embed
# 별도 터미널에서 foreground로 실행. Ctrl-C로 이 서버를 종료한다.
.venv-rag-workstation/bin/python procurement-pipeline/start_workstation_rag_server.py
# 먼저 기존 25개로 별도 회귀 cohort를 만들고 실제 검색/생성 검토를 수행한다.
# 그 뒤 신규 작은 배치: 아래 run ID를 새 조건에 맞게 확정한다.
.venv-rag-workstation/bin/python procurement-pipeline/workstation_rag.py run --run-id workstation275-v1 --limit 5
python3 procurement-pipeline/workstation_rag.py summarize --run-id workstation275-v1
# 검토 후 같은 조건의 미시도 ID만 계속한다.
.venv-rag-workstation/bin/python procurement-pipeline/workstation_rag.py run --run-id workstation275-v1 --limit 20
# 실패 재시도는 명시적으로 요청하며 이전 시도 파일은 보존한다.
.venv-rag-workstation/bin/python procurement-pipeline/workstation_rag.py run --run-id workstation275-v1 --retry-failed --limit 5
```

기존 25개 ID는 evaluation/selection.json의 baseline_unique_ids다. 별도 regression output/work를 --output/--work로 지정하고 --ids JSON 목록을 사용한다. 각 회귀 색인·프로필·질의 벡터를 해당 경로에 준비해야 한다. output을 기존 v1로 지정하는 것은 거부한다. 문서 벡터가 이미 있으면 재작성하지 않으며 새로운 output/work를 사용한다.

run 상태 파일의 attempts에 문항별 모든 시도와 경로가 저장된다. 모델/코드/색인 변경은 새로운 run ID로 구분한다. 이후 정오답과 무관하게 최신 명시 시도를 선택한다. 현재 275개는 모두 not_started이며 run ID는 아직 생성하지 않았다. 재개 코드를 실제 RAG로 검증한 것처럼 보고하지 않는다.

## 본 실행 후 필수 후속 검수

배치마다 ID 일치·중복/누락·빈 응답·잘림·타임아웃, ACL/tenant/역할/등급/시나리오/차수/날짜, 검색→프롬프트 chunk ID·해시·offset 연결을 자동 검증한다. summarize의 TSV는 실행 상태/답변 검토의 출발점이며 인용 지지 여부나 답변 정답을 자동 인증하지 않는다. 기존 evaluate/summarize의 post-run 근거 대조를 새 output에 연결하고 실제 근거로 무결성 검사 후 전 질문·답변을 내용 검토해야 한다. 특히 실적 금액, 인증 주체/missing/만료, VAT·마진·FTE·기간, 원문충돌을 검토한다. 이 단계는 원천 미확보로 아직 수행하지 않았다.

최신 원시 actual_answer를 수정하지 않고 별도 검토 파일에 verdict·이유·근거 ID/offset·검토자·코드 노출을 저장한다. 환각 span 라벨링 단계는 선택된 답변 및 prompt_evidence를 연결하고 실제 답변 문자열의 Unicode code point [start,end) 구간을 사람 검토 대상으로 넘긴다. 이번 작업의 span은 null, 사람 승인은 pending을 유지한다.

Git에는 코드·요청·환경·검토용 메타데이터만 올린다. 원문·캐시·모델·벡터·로컬 키·전체 프롬프트는 work/에만 둔다. 다음 에이전트는 resume_state.json과 evaluation/integrated_status.json부터 읽는다.
