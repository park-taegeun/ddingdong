# 띵동 서버 (Flask)

ESP32와 React 대시보드가 붙는 API + DB. 2단계 알림 흐름 = 1차 `/api/v1/detect`(추론 → 카카오 텍스트 → 알림 저장)
→ 2차 `/api/v1/enrich`(사진 호스팅 + STT 자막 → 카카오 사진 feed + 자막).
외부 연동은 모두 env 게이트다 — 값이 없으면 mock으로 동작해 로컬 테스트에 자격증명이 필요 없다.

| 연동 | env | 비었을 때 |
|------|-----|-----------|
| 실추론 모델 | `DDINGDONG_MODEL_PATH` | mock 추론 (카테고리 6.2) |
| STT (Naver CSR) | `NCP_CLIENT_ID` · `NCP_CLIENT_SECRET` (둘 다) | mock 자막 (카테고리 7 STT / 30.9) |
| 카카오 나에게 보내기 | `KAKAO_*` 4키 | 발송 건너뜀 (카테고리 7) |

키 전체 · 빈 값 규칙 = [`.env.example`](.env.example).

## 스택

- Flask 3.1 (app factory 패턴)
- Flask-SQLAlchemy 3.1 + SQLite
- python-dotenv (`server/.env` 주입 — 셸 환경 변수가 이긴다)
- numpy (등록용 소리 비교 `sound_match.py`). TensorFlow는 실모델용 별도 venv(`venv_real`, Python 3.11)에만.

## 셋업 · 기동 (모두 `server/`에서)

```bash
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cp .env.example .env              # 값 채우기 (.env 는 commit 금지)

# mock ML · 보드가 붙으려면 0.0.0.0 필수 · NCP 키가 설정돼 있으면 STT는 실호출(과금)
FLASK_APP=app venv/bin/flask run --host=0.0.0.0 --port=5000

# 실모델 (venv_real = Python 3.11 + TensorFlow)
DDINGDONG_MODEL_PATH="$HOME/ddingdong_runs/<run 폴더>/inference_savedmodel" FLASK_APP=app venv_real/bin/flask run --host=0.0.0.0 --port=5000
```

⚠️ `python run.py`는 `127.0.0.1`에만 뜬다 — 보드가 붙지 못한다.
시연 · 부스 기동(터널 · 실모델 서버 · 대시보드 한 번에)은 `tools/demo_up.py`(카테고리 26.12).

## 엔드포인트 (카테고리 6.1)

| 메서드 | 경로 | 인증 | 설명 |
| --- | --- | --- | --- |
| POST | `/api/v1/detect` | Device Token | ESP32 1차. 추론(`DDINGDONG_MODEL_PATH` 설정 시 실모델, 미설정 시 mock) → 카카오 1차 텍스트 발송 → notification 저장, `request_id`(ULID) 발급. 초인종 등록 계측 훅(수집 중 템플릿 저장 · 등록 뒤 거리 기록)이 같은 commit 에 얹힌다 |
| POST | `/api/v1/enrich` | Device Token | ESP32 2차. 사진을 로컬 저장해 public URL(`/captures/…`)로 채우고, 자막은 STT(`NCP_CLIENT_ID` · `NCP_CLIENT_SECRET` 설정 시 실 CSR, 미설정 시 mock 문구) → 카카오 2차(사진 feed + 자막 text) 발송 |
| POST | `/api/v1/heartbeat` | Device Token | ESP32 생존 보고. 기기당 1행 덮어쓰기, rate limit 미적용, 성공 = 204. 필드(`device_id` · `rssi` · `uptime_s` · `enrich_sent` · `fw`) 전부 필수 (카테고리 6.8) |
| GET | `/api/v1/notifications` | Dashboard Token | 대시보드 폴링. cursor pagination |
| GET | `/api/v1/stats` | Dashboard Token | 대시보드 폴링. `period=today` 집계 + 기기 상태(마지막 heartbeat 기준) |
| GET | `/api/v1/registration` | Dashboard Token | 초인종 등록 상태 조회 (`none` · `collecting` · `registered` · `expired`) |
| POST | `/api/v1/registration/start` | Dashboard Token | 등록 템플릿 수집 시작. 본문 `target_count` · `expires_in_seconds` 필수. 수집 중·등록 완료면 409 |
| DELETE | `/api/v1/registration` | Dashboard Token | 등록 해제(템플릿 전부 삭제). 멱등 |
| GET | `/captures/<opaque_id>` | 없음 | 캡처 사진 public 서빙 (카카오 feed · 대시보드가 읽는다, 카테고리 7) |
| GET | `/health` | 없음 | 헬스 체크 |

인증: `Authorization: Bearer <token>` (Device / Dashboard 분리).

## 응답 구조 SSoT

`dashboard/src/types/` (`notification.ts` / `stats.ts` / `api.ts`) 와 1:1.
시간은 DB에 naive UTC 저장, 응답은 KST ISO8601(+09:00, 밀리초) 직렬화.

## HTTP Status

200 / 201 / 204(heartbeat) / 400 / 401 / 404 / 409 / 429(Retry-After) / 500 — 상세는 `app/errors.py`.

## 디렉토리

```
server/
  run.py              # 진입점 (127.0.0.1 전용 — 위 ⚠️)
  requirements.txt
  .env.example        # env 템플릿 (키 전체 · 빈 값 규칙)
  seed.py             # 데모 알림 시드 (아래 ⚠️)
  purge_notifications.py  # 부스 자막 정리 — 지정 시간대 알림 행 삭제 (아래 ⚠️)
  app/
    __init__.py       # create_app (app factory) · 기동 가드(serving_level · model_labels)
    config.py         # server/.env 로드 + 설정
    extensions.py     # db = SQLAlchemy()
    constants.py      # 매직 넘버 중앙 관리
    utils.py          # KST 시간 / ULID / 예측 정책 / mock ML
    errors.py         # 통일 JSON 에러
    auth.py           # Device / Dashboard Bearer Token 데코레이터
    rate_limit.py     # device_id 5초당 1회 (in-memory)
    models.py         # Notification / IdempotencyKey / KakaoToken /
                      #   RegistrationState / RegistrationTemplate / RegistrationMatch /
                      #   RegistrationFailure / DeviceHeartbeat
    routes.py         # /api/v1 Blueprint — detect · enrich · heartbeat · notifications · stats
    registration_api.py     # /api/v1/registration Blueprint (상태 · 시작 · 해제)
    registration.py         # 초인종 등록 저장 층 (commit 없음)
    registration_observe.py # /detect 등록 판정(카카오 앞) + 템플릿 · 측정 · 실패 기록(카카오 뒤)
    sound_match.py    # 등록용 소리 비교 (numpy 멜 + DTW-cosine)
    captures.py       # /captures/<id> public 캡처 이미지 서빙 (비인증)
    image_store.py    # 로컬 이미지 스토어
    kakao.py          # 카카오 나에게 보내기 (토큰 · 1차 · 2차 발송)
    stt.py            # Naver CSR STT 클라이언트 (env 게이트)
    model_serving.py  # 실추론 모델 싱글턴 로더 (env 게이트)
    serving_level.py  # /detect 추론 입력 레벨(raw / peak) — 기동 시 결정, 잘못된 값 = 기동 실패
    model_labels.py   # 기동 시 run 폴더 labels.json ↔ 서빙 라벨 순서 대조, 불일치 = 기동 실패
    tof_meta.py       # /detect ToF 메타 수신 · 검증
    tests/            # 서버 회귀 테스트 (아래)
  inference/          # 오디오 디코드 · 모델 실행 (app 과 형제 패키지, inference/README.md)
  tools/              # demo_up(시연 기동) · gate_axis_sweep(게이트 축 스윕) · record_receiver(보드 녹음 수신기)
```

## 테스트 (stdlib unittest, `server/`에서)

모듈: `app/tests/` — `test_detect_regression` · `test_heartbeat` · `test_model_labels` · `test_purge_notifications` ·
`test_registration` · `test_round_gap_log` · `test_seed_guard` · `test_serving_level` · `test_sound_match`,
`inference/tests/` — `test_inference_contract`(TF 없으면 predict 테스트 skip). 현재 건수 = decisions.md 17.2.

```bash
python3 -m unittest discover -s app/tests -t .                    # 전체
python3 -m unittest app.tests.test_detect_regression              # 단일 모듈
python3 -m unittest inference.tests.test_inference_contract -v    # TF 있는 venv_real 로 돌리면 predict 포함
```

## 운영 도구 주의

- ⚠️ `seed.py` = 기본 DB의 알림을 **전부 삭제**한 뒤 데모 5건을 심는다. `--confirm-delete-all` 없으면 쓰기 0(종료 코드 2).
  부스 · 발표 전에 실행 금지 (PR #117, 카테고리 33.35(c)).
- ⚠️ `purge_notifications.py` = 드라이런이 기본(지울 행 수만 보여 주고 종료 코드 2). `--confirm-delete`를 붙여야 지운다.
  서버를 끈 뒤 실행 (카테고리 33.35(k)).
