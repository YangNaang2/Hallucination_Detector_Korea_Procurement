> 최신 변경: 현실 지도는 MapLibre + OpenFreeMap으로 복원했습니다. Mapbox 토큰과 .env는 현재 사용하지 않습니다. 아래 Mapbox 관련 내용은 이전 설정 기록입니다.

# Mapbox 연결 및 생태계 업데이트

## 사용자가 할 일

1. [Mapbox 계정](https://account.mapbox.com/)을 만들고 Access tokens에서 웹 데모용 **공개 토큰(pk.)**을 생성합니다. 공개 지도 읽기 권한 `styles:read`, `fonts:read`를 포함합니다. 비밀 업로드/쓰기 권한은 필요하지 않습니다.
2. 토큰의 Allowed URLs에 실행 주소 `http://127.0.0.1:8765/`를 허용합니다. localhost로 접속한다면 `http://localhost:8765/`도 별도로 허용합니다. 나중에 배포할 때 배포 주소를 추가합니다.
3. 이 폴더의 `.env`에 아래처럼 입력합니다. `.env`가 없으면 `.env.example`을 복사해 이름을 바꿉니다. Windows에서 `.env.txt`로 저장되지 않았는지 확인하세요.

```dotenv
VITE_MAPBOX_TOKEN=pk.발급받은_공개토큰
MAPBOX_LIGHT_PRESET=night
```

`NEXT_PUBLIC_MAPBOX_TOKEN`도 지원합니다. 둘 다 있으면 VITE 값을 우선합니다. Windows 프로세스 환경변수가 `.env`보다 우선합니다. 조명은 `dusk`로 바꿀 수도 있습니다.

4. 기존 실행 터미널을 Ctrl+C로 종료하고 `실행.bat`을 다시 실행합니다. 브라우저에서 Ctrl+F5로 갱신합니다. 새 주소는 **http://127.0.0.1:8765/**로 고정입니다.
5. Mapbox 계정의 사용량·요금 설정을 확인하세요. 이 데모가 무조건 무료라는 뜻은 아닙니다. 401/403이면 토큰 유효성, 읽기 권한과 Allowed URLs를 확인합니다.

토큰은 채팅에 보낼 필요 없습니다. 공개 브라우저 토큰은 지도 요청에서 보일 수 있습니다. `.env`를 쓴다고 비밀 토큰처럼 숨겨지는 것은 아닙니다.

## 구현

기존 Python 정적 서버를 유지했습니다. Vite/Next 프로젝트로 바꾸지 않고, 실행 서버가 두 환경변수 이름을 지원합니다. `/runtime-config.json`은 `pk.` 토큰과 조명값만 허용 목록으로 내보냅니다. `.env` 전체와 다른 환경변수는 내보내지 않습니다. `.env`는 정적 제공 디렉터리(dist) 밖이며 gitignore 대상입니다.

Mapbox GL JS 3.30.0 / `mapbox://styles/mapbox/standard` / `night` 기본 조명 / DEM 1.6배 지형입니다. 사용자 토큰이 없으면 현실 지도는 TOKEN REQUIRED, 가상 모드는 계속 사용할 수 있습니다. 기존 MapLibre 커스텀 홀로그램의 행렬 입력은 Mapbox 형식도 받도록 수정했습니다. 토큰 미제공 상태이므로 실제 Mapbox 렌더링과 커버리지는 아직 확인하지 않았습니다.

## 가상 생태계

| 섹터 | 지형·건축 | 공고·설비 |
|---|---|---|
| AI 데이터 밸리 | 평탄한 그리드·슬림 타워 | AI 연합 관제국 / 5만 연산 노드 냉각 / 분배 모듈 50식·펌프 12식 |
| 양자 신소재 산단 | 분화구·협곡·돔·반매립 큐브 | 양자재료공학원 / 파운드리 차폐 / 모듈 64식·검사 장비 8식 |
| 자율로보틱스 림 | 5단 테라스·스카이브릿지 | 림 오토메이션 / 로버 300대·도킹 스테이션 30식 |
| 바이오-마린 특구 | 호수 분지·수로·수면 플랫폼 | 해양바이오컨소시엄 / 센서 120식·부표 16식 |

모든 과업은 가상입니다. 내부 설비는 개별 실제 제품 모델이 아닌 수량·위치 확인용 단순 메시입니다. 운영 생태계는 시나리오이며 실제 자율 운영 시뮬레이터는 아닙니다. 12종 문서 48페이지 PDF도 변경된 공고·설비 ID에 맞춰 재생성했습니다.

검사: 구문·기존 화면 연결·문서/설비 ID·정상/불일치 규칙·환경변수 우선순위 및 공개 토큰 필터. PDF 표본 렌더 확인. 실제 GPU 화면/FPS와 토큰 사용 지도는 미검증입니다.

공식 자료: [토큰 관리·URL 제한](https://docs.mapbox.com/accounts/guides/tokens/), [Standard 조명](https://docs.mapbox.com/map-styles/guides/standard-styles/), [GL JS 초기 설정](https://docs.mapbox.com/mapbox-gl-js/example/initial-config-property/).
