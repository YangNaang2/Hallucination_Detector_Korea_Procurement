# 워크스테이션 원천 자료 이전

2026-09-13 생성. Git에 포함하지 않은 원천 자료를 별도로 이전하기 위한 안내다.

## 전달 파일

- 이 PC: `work/source-transfer/astra-source-transfer.zip`
- 크기: 78,758,157 bytes
- SHA-256: `6d7ccf12f034887204436a19e15f441c3c119d46ac074f504b0cdef62ce0d918`
- 별도 체크섬: `work/source-transfer/astra-source-transfer.zip.sha256`
- 실제 원천 루트: `C:/Users/aidan/AppData/Local/Temp/astra-source-review`

ZIP과 원천 파일은 Git에 올리지 않는다. 사용자가 USB 또는 직접 파일 전송으로 워크스테이션에 전달해야 한다. 이 문서의 커밋/push는 ZIP 전송을 의미하지 않는다.

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
