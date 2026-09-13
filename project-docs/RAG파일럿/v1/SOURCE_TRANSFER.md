# 워크스테이션 원천 자료 이전

2026-09-13 생성. Git에 포함하지 않은 원천 자료를 별도로 이전하기 위한 안내다.

## 전달 파일

- 이 PC: `work/source-transfer/astra-source-transfer.zip`
- 크기: 78,758,157 bytes
- SHA-256: `6d7ccf12f034887204436a19e15f441c3c119d46ac074f504b0cdef62ce0d918`
- 별도 체크섬: `work/source-transfer/astra-source-transfer.zip.sha256`
- 실제 원천 루트: `C:/Users/aidan/AppData/Local/Temp/astra-source-review`

사용자의 추가 요청에 따라 ZIP과 체크섬을 같은 비공개 저장소의 GitHub Release 첨부파일로 전달한다. Git 커밋에는 대용량 원천 파일을 넣지 않는다. 모델·키·전체 실행 프롬프트는 Release에도 포함하지 않는다.

## GitHub에서 받기

Release: `source-transfer-v1-20260913`

저장소 주소: `https://github.com/YangNaang2/ko-lettucedetect`

워크스테이션에서 GitHub 인증 후 저장소 루트에서 실행한다. 미커밋 변경이 있으면 먼저 보존하고, 작업 브랜치에서는 `origin/main`을 안전하게 통합한다. 아래 `pull`은 수정 없는 main 체크아웃을 기준으로 한다.

```bash
git pull --ff-only origin main
mkdir -p work/source-transfer
gh release download source-transfer-v1-20260913 \
  --repo YangNaang2/ko-lettucedetect \
  --pattern 'astra-source-transfer.zip*' \
  --dir work/source-transfer
(cd work/source-transfer && sha256sum -c astra-source-transfer.zip.sha256)
```

기존 다운로드가 있으면 해시부터 확인하고 재사용한다. 다른 파일을 무조건 덮어쓰지 않는다. 저장소는 비공개이므로 브라우저 다운로드도 해당 저장소에 접근할 수 있는 GitHub 로그인이 필요하다. Codex 계정 로그인과 GitHub 저장소 인증은 별도다.

Git의 `Download ZIP` 또는 `git clone`만으로는 Release 첨부파일이 내려오지 않는다. 위 다운로드 단계까지 실행해야 원천 자료가 준비된다. 원천 자료 이후 GPU에 맞는 Linux 실행 환경·고정 모델 다운로드·색인 재구축은 워크스테이션에서 수행한다.

## ZIP 내용 및 검증

- `source-texts.json`: 기존 캐시를 바이트 그대로 보존.
- `source-texts.posix.json`: 각 레코드의 `relative`에서 Windows 역슬래시만 `/`로 변환. 본문·공고 ID·원본 해시·문자 offset은 변경하지 않음.
- `export/...`: 캐시가 참조하는 공고 51건의 원본 파일 183개. 기존 상대 폴더 구조 유지.
- `transfer-manifest.json`: 원본/변환 캐시 해시와 원본별 경로·해시·크기.

패키징 시 183개 원본의 SHA-256을 기존 캐시와 대조했고, 생성 ZIP의 CRC 및 압축 해제 내용의 원본별 SHA-256도 검사하여 통과했다. 이는 파싱 내용의 완전성을 새로 검증했다는 의미가 아니다. 기존 파싱 불가 첨부 상태는 그대로 유지했다.

모델, 벡터 색인, API 키, 전체 실행 프롬프트, 의존성 폴더는 포함하지 않았다.

## Linux에서 사용

1. ZIP과 체크섬을 저장소의 `work/source-transfer/`로 옮긴다.
2. `sha256sum -c astra-source-transfer.zip.sha256`로 전송 무결성을 확인한다.
3. ZIP 엔트리의 경로 이탈·기존 파일 충돌 여부를 확인하고, 같은 `work/source-transfer/` 아래에 압축을 푼다. 한글 경로는 UTF-8로 유지한다.
4. 원천 루트는 `<저장소>/work/source-transfer`, Linux용 캐시는 그 아래 `source-texts.posix.json`이다. 루트를 `export/`로 지정하면 안 된다. 캐시 상대 경로에 이미 `export/`가 포함된다.
5. manifest를 읽어 모든 원본 해시와 캐시 해시를 다시 검증한다. Linux용 캐시 해시는 경로 문자열 변환 때문에 원래 캐시와 다르며, 이를 출처 변환 이력으로 기록한다.
6. 후속 실행용 별도 출력 경로에 색인을 구축한다. 기존 v1 평가·선택·요청·결과를 덮어쓰지 않도록 먼저 실행기를 일반화한다. 기존 `prepare` 명령을 그대로 실행하면 v1 산출물을 갱신하므로 주의한다.

기존 GGUF는 워크스테이션에서 고정 revision/해시로 다시 다운로드할 수 있다. 색인은 이 원천 자료와 Git의 회사 문서에서 재구축한다. 275문항 실행에서는 미확보 입력과 정상적인 업무상 자료부족 응답을 구분한다.
