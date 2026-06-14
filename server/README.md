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
| POST | `/api/v1/detect` | Device Token | ESP32 1차. mock 추론 + notification 저장, `request_id`(ULID) 발급 |
| POST | `/api/v1/enrich` | Device Token | ESP32 2차. 해당 notification 에 사진/STT mock 채움 |
| GET | `/api/v1/notifications` | Dashboard Token | 대시보드 폴링. cursor pagination |
| GET | `/api/v1/stats` | Dashboard Token | 대시보드 폴링. `period=today` 집계 |
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
    utils.py          # KST 시간 / ULID / mock ML
    errors.py         # 통일 JSON 에러 (HTTP 8종)
    auth.py           # Device / Dashboard Bearer Token 데코레이터
    rate_limit.py     # device_id 5초당 1회 (in-memory)
    models.py         # Notification / IdempotencyKey
    routes.py         # /api/v1 Blueprint (4종)
```
