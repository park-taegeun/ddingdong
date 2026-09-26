# 띵동 서버 (Phase 2-1: Flask 백엔드 골격)

ESP32와 React 대시보드가 붙는 실제 API 표면 + DB. ML 추론은 mock(11주차 YAMNet 통합 예정),
React 연동은 Phase 2-2차, HTTPS/배포는 11주차. 본 단계는 **로컬 M4 + http** 단독 (카테고리 8.1).

## 스택

- Flask 3.1 (app factory 패턴)
- Flask-SQLAlchemy 3.1 + SQLite
- python-dotenv (토큰/설정 `.env` 주입)

## 셋업

```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # DEVICE_TOKEN / DASHBOARD_TOKEN 채우기 (.env 는 commit 금지)
python run.py          # http://127.0.0.1:5000
```

## 엔드포인트 (카테고리 6.1)

| 메서드 | 경로 | 인증 | 설명 |
| --- | --- | --- | --- |
| POST | `/api/v1/detect` | Device Token | ESP32 1차. 추론(`DDINGDONG_MODEL_PATH` 설정 시 실모델, 미설정 시 mock) → 카카오 1차 텍스트 발송 → notification 저장, `request_id`(ULID) 발급. 초인종 등록 계측 훅(수집 중 템플릿 저장 · 등록 뒤 거리 기록)이 같은 commit 에 얹힌다 |
| POST | `/api/v1/enrich` | Device Token | ESP32 2차. 사진을 로컬 저장해 public URL(`/captures/…`)로 채우고, 자막은 STT(`NCP_CLIENT_ID` · `NCP_CLIENT_SECRET` 설정 시 실 CSR, 미설정 시 mock 문구) → 카카오 2차(사진 feed + 자막 text) 발송 |
| GET | `/api/v1/notifications` | Dashboard Token | 대시보드 폴링. cursor pagination |
| GET | `/api/v1/stats` | Dashboard Token | 대시보드 폴링. `period=today` 집계 |
| GET | `/api/v1/registration` | Dashboard Token | 초인종 등록 상태 조회 (`none` · `collecting` · `registered` · `expired`) |
| POST | `/api/v1/registration/start` | Dashboard Token | 등록 템플릿 수집 시작. 본문 `target_count` · `expires_in_seconds` 필수. 수집 중·등록 완료면 409 |
| DELETE | `/api/v1/registration` | Dashboard Token | 등록 해제(템플릿 전부 삭제). 멱등 |
| GET | `/health` | 없음 | 헬스 체크 |

인증: `Authorization: Bearer <token>` (Device / Dashboard 분리).

## 응답 구조 SSoT

`dashboard/src/types/` (`notification.ts` / `stats.ts` / `api.ts`) 와 1:1.
시간은 DB에 naive UTC 저장, 응답은 KST ISO8601(+09:00, 밀리초) 직렬화.

## HTTP Status

200 / 201 / 400 / 401 / 404 / 409 / 429(Retry-After) / 500 — 상세는 `app/errors.py`.

## 디렉토리

```
server/
  run.py              # 진입점 (python run.py)
  requirements.txt
  .env.example
  app/
    __init__.py       # create_app (app factory)
    config.py         # .env 로드 + 설정
    extensions.py     # db = SQLAlchemy()
    constants.py      # 매직 넘버 중앙 관리
    utils.py          # KST 시간 / ULID / 예측 정책 / mock ML
    errors.py         # 통일 JSON 에러 (HTTP 8종)
    auth.py           # Device / Dashboard Bearer Token 데코레이터
    rate_limit.py     # device_id 5초당 1회 (in-memory)
    models.py         # Notification / IdempotencyKey / KakaoToken /
                      #   RegistrationState / RegistrationTemplate / RegistrationMatch
    routes.py         # /api/v1 Blueprint — detect · enrich · notifications · stats (4종)
    registration_api.py     # /api/v1/registration Blueprint (상태 · 시작 · 해제)
    registration.py         # 초인종 등록 저장 층 (commit 없음)
    registration_observe.py # /detect 등록 계측 훅 (관측 전용)
    sound_match.py    # 등록용 소리 비교 (numpy 멜 + DTW-cosine)
    captures.py       # /captures/<id> public 캡처 이미지 서빙 (비인증)
    image_store.py    # 로컬 이미지 스토어
    kakao.py          # 카카오 나에게 보내기 (토큰 · 1차 · 2차 발송)
    stt.py            # Naver CSR STT 클라이언트 (env 게이트)
    model_serving.py  # 실추론 모델 싱글턴 로더 (env 게이트)
    tof_meta.py       # /detect ToF 메타 4종 수신 · 검증
    tests/            # 서버 회귀 테스트 (detect_regression · sound_match · registration)
  inference/          # 오디오 디코드 · 모델 실행 (app 과 형제 패키지)
  tools/              # gate_axis_sweep · record_receiver
```
