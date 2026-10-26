# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트

띵동(DdingDong) — 청각장애인용 현관 부착형 소리 분류 알림 시스템(졸업작품). 모노레포: `firmware/`(ESP32-S3) · `server/`(Flask) · `dashboard/`(React) · `ml/`(YAMNet) · `tools/decisions-rag/`(개발 도구, 제품과 무관).

## 🔴 작업 규칙

- **`docs/decisions.md`가 모든 결정의 SSoT**(6,600줄+). 코드 주석·PR이 「카테고리 N.M」으로 이 문서를 인용한다. 핀 표·상수·정책을 바꾸려면 decisions.md를 먼저 고친다. 변경 이력은 `docs/decisions-log.md`.
  - `decisions-rag` MCP(`search_decisions` / `get_section`)로 찾을 수 있지만 결과는 힌트다. 인용 전에 원문을 `grep`으로 다시 확인한다.
  - 평가 질문·정답을 decisions.md에 쓰지 않는다(RAG 인덱스 오염).
- **커밋 메시지**: 한국어 + 이모지, `{이모지} {Type}: {한국어 설명}` (예: `🐛 Fix: …`, `✨ Feat: …`). 상세 = `docs/git-convention.md`. 한 커밋 = 한 목적.
- **비밀값**: `.env`, `.env.local`, `firmware/include/secrets.h`는 읽기·수정이 `.claude/settings.json` deny 규칙과 `.claude/hooks/block-secrets.py` 훅으로 막혀 있다. 템플릿(`.env.example`, `secrets.h.template`)만 다룬다.
- 「계측 → 실측 → 판정」(카테고리 20): 판정 로직·임계값 PR 전에 관측 하네스를 먼저 세우는 것이 이 repo의 관례다. 테스트는 negative control(일부러 깨뜨린 변형이 **반드시 실패**하는지)까지 확인한다.

## 명령어

### server (모두 `server/`에서, stdlib unittest)
```bash
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cp .env.example .env              # DEVICE_TOKEN / DASHBOARD_TOKEN — 사람이 직접 실행(훅이 차단함)
FLASK_APP=app venv/bin/flask run --host=0.0.0.0 --port=5000   # mock ML · 보드가 붙으려면 0.0.0.0 필수(run.py는 127.0.0.1로만 띄운다) · NCP 키가 설정돼 있으면 STT는 실호출(과금)
DDINGDONG_MODEL_PATH="$HOME/ddingdong_runs/<run 폴더>/inference_savedmodel" FLASK_APP=app venv_real/bin/flask run --host=0.0.0.0 --port=5000   # 실모델(venv_real = Python 3.11 + TensorFlow)
# 서버를 `--debug` · `FLASK_DEBUG=1`로 띄우지 않는다(`python run.py`도 debug=True라 해당) — 응답이 보드 버퍼(767 B)를 넘을 수 있다(decisions.md 33.37(e) · 사용자 결정 2026-10-26)
python3 -m unittest discover -s app/tests -t .          # 전체
python3 -m unittest app.tests.test_detect_regression    # 단일 모듈
python3 -m unittest inference.tests.test_inference_contract -v   # TF 없으면 predict 테스트 skip
```

### dashboard (`dashboard/`)
```bash
npm run dev       # vite :5173, /api → localhost:5000 프록시 (클라이언트는 상대경로 /api/v1/... 필수)
npm run build     # tsc -b && vite build
npm run lint
npm run ssr-nc    # 테스트 러너 대신: 소스를 일시 변형 → SSR 렌더 → 텍스트 단언 → 복원 (negative control 하네스)
```
환경변수: `VITE_API_BASE_URL`(비우면 상대경로), `VITE_DASHBOARD_TOKEN`.

### firmware (`firmware/`, PlatformIO)
```bash
~/.platformio/penv/bin/pio run -e <env>                 # 빌드 (default_envs = poc) · pio는 PATH에 없다
~/.platformio/penv/bin/pio run -e <env> -t upload
~/.platformio/penv/bin/pio device monitor -b 115200
```
호스트 단위 테스트는 실제 헤더/소스를 그대로 include·링크해 `c++`로 빌드한다. 정확한 명령은 각 `firmware/tools/*_test.cpp` 상단 주석에 있다(repo 루트 기준). 예:
```bash
c++ -std=c++17 -Wall -I firmware/include -I firmware/tools/host_stubs \
    -o /tmp/tjt firmware/tools/tof_judge_test.cpp firmware/src/tof_common.cpp && /tmp/tjt
```
장비 절차는 `firmware/*_RUNBOOK.md`.

### ml (repo 루트에서 `python -m ml.…`, Python 3.11/3.12)
```bash
python -m ml.pipeline.run_all --data-root "<dataset>" --decisions ml/pipeline/retrain_data_decisions.csv
DDINGDONG_YAMNET_HANDLE="$YAMNET" python -m ml.training.train    --data-root "$DATA" --classes doorbell,knock,fire_alarm,other --out-dir "$RUN"
DDINGDONG_YAMNET_HANDLE="$YAMNET" python -m ml.training.evaluate --data-root "$DATA" --classes doorbell,knock,fire_alarm,other --out-dir "$RUN"
python -m ml.pipeline.tests.test_pipeline        # 각 tests 모듈 단독 실행 가능
python -m ml.curation.tests.test_slice_negatives # 일부 curation 테스트는 ffmpeg 필요
```
데이터셋은 repo 밖에 있다(`--data-root`). `--classes`에는 기본값이 없다. `$YAMNET` = YAMNet 로컬 사본 폴더 — 빠지면 `ml/training/config.py` 기본값(tfhub URL)으로 가서 불완전 캐시에서 실패할 수 있다(decisions.md 33.34(c)). train · evaluate · export 명령마다 붙인다.

## 아키텍처

### 2단계 알림 흐름 (펌웨어 ↔ 서버)
1. **1차 `/api/v1/detect`** (Device Token): 보드가 음향 트리거(64ms 버퍼 RMS, `auto_trig.h`)로 오디오 스냅샷과 ToF 메타를 보낸다. 서버가 추론(`DDINGDONG_MODEL_PATH`를 지정하면 실모델, 없으면 mock)하고 카카오 '나에게 보내기'로 텍스트를 보낸 뒤 notification을 저장한다. 응답의 `request_id`(ULID)와 `enrich_status`가 2차 진행 여부를 정한다.
2. **2차 `/api/v1/enrich`**: 보드가 카메라 1장과 5.12초 녹음을 보낸다. 서버는 사진을 로컬에 저장해 public `/captures/<id>`로 서빙하고, STT(Naver CSR; `NCP_*`가 없으면 mock)를 거쳐 카카오 2차(사진 feed + 자막)를 보낸다. 카카오 memo API에는 이미지 업로드가 없어서 서버가 직접 public URL을 호스팅해야 한다.

외부 연동(모델 · STT · 카카오)은 모두 **env 게이트**다. 값이 없으면 mock으로 동작하므로 로컬 테스트에 자격증명이 필요 없다.

### server
- `app/__init__.py`의 `create_app` 팩토리, Flask-SQLAlchemy + SQLite. 시간은 DB에 naive UTC로 저장하고 응답은 KST ISO8601(+09:00, ms)로 직렬화한다.
- 응답 스키마 SSoT = `dashboard/src/types/`(`notification.ts` · `stats.ts` · `api.ts`)와 1:1. 한쪽을 바꾸면 반대쪽도 바꾼다.
- 초인종 개인 등록: `registration_api.py`(API) → `registration.py`(저장 층, commit 없음) → `registration_observe.py`(/detect 안 훅, 카카오 **앞**에서 판정하고 **뒤**에서 기록) → `sound_match.py`(numpy 멜 + DTW-cosine).
- `server/inference/`는 `app`과 형제 패키지다(오디오 디코드 · SavedModel lazy-load). `routes.py`·`model_serving.py`가 이 패키지를 import한다. 오디오 계약 = PCM int16 LE mono 16kHz.
- 매직 넘버는 `app/constants.py`, `inference/constants.py`에 모은다. 에러 형식 = `app/errors.py`, 인증 = `app/auth.py`(Device / Dashboard Bearer 분리).
- 테스트는 실제 데이터 폴더(캡처 사진 · 기본 DB)를 건드리지 않게 격리한다(최근 수정 #117, #118 참고).

### firmware
- `platformio.ini`의 **env 하나 = 독립 바이너리**. 모든 env가 `build_src_filter = -<*>` 다음에 필요한 `.cpp`만 나열하는 **화이트리스트** 방식이다(카테고리 27.6). `+<*>` 블랙리스트로 쓰면 여러 `*_main.cpp`의 `setup()/loop()`가 중복 정의된다. 새 env도 처음부터 화이트리스트로 만든다.
- 공용 모듈 `*_common.cpp`(camera · mic · tof · uplink)를 env들이 조합한다. 진단용 env(`*_probe`, `*_pinscan` 등)와 이전 env는 **frozen**이다. 고치지 말고 복제해서 새 env를 만든다. env 이름 = `{domain}_{purpose}` 소문자 스네이크.
- 제품 경로 = `enrich_uplink`(수동 's' 트리거) / `enrich_autotrig`(같은 소스 + `-DENRICH_AUTO_TRIGGER`).
- 카메라가 들어가는 env는 `-DCAMERA_MODEL_XIAO_ESP32S3`가 필수다(없으면 `camera_common.h`의 `#error`). ToF를 쓰는 env는 SparkFun VL53L5CX를 `lib_deps`에 넣는다.
- 판정 로직은 순수 헤더(`auto_trig.h`, `noise_stats.h`, `trig_line.h` 등)로 분리해 호스트에서 검산한다. 실제 core는 Arduino-ESP32 2.0.17이다(PIO 패키지 버전 `3.20017`을 core 3.x로 잘못 읽지 말 것).
- 핀 표 SSoT = decisions.md 카테고리 2 (마이크 I2S1 GPIO2/3/7, ToF I2C GPIO5/6).

### ml
`01_clips` → `02_preprocessed` → 중복 제거 + **원본(source) 단위 그룹 split**(그룹 키 해시 고정, 증강 이전) → `03_augmented`(train만) → `05_final_dataset` → YAMNet frozen 임베딩 위 head 학습.
- 출력은 waveform 16kHz mono를 유지한다. 멜 변환은 학습 스크립트가 맡는다.
- 클래스 허용 집합 = `ml.pipeline.config.CLASSES`(doorbell / knock / fire_alarm / other). 라벨 인덱스는 이 순서로 정규화하고, 실행별 진실 = run 폴더 `labels.json`. 서버 `PREDICTED_CLASSES`와 맞아야 한다.
- `retrain_data_decisions.csv`(exclude / relabel_other)는 D1 중복 제거 **뒤에** 적용한다. 목록이 데이터와 어긋나면 조용히 건너뛰지 않고 즉시 실패한다. `02_preprocessed` 원본은 지우지 않는다.
- `ml/curation/`: `other` 네거티브 후보 선별·조각내기(데이터셋은 읽기 전용).
