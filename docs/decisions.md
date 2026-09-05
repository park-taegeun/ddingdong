# 🔴 Decisions (SSoT — Single Source of Truth)

> 본 문서는 띵동 프로젝트의 **모든 결정**의 단일 진실 원천(SSoT)이다.
> 코드/펌웨어 작업 전 반드시 git pull로 최신본을 받은 후 작업할 것.
> 결정 변경 시 본 채팅방(전략) → 본 문서 갱신 → 채팅방 2(구현) 순서.
>
> 변경 이력은 `decisions-log.md` 참조.

---

## 카테고리 1: 하드웨어

- **메인**: XIAO ESP32-S3 Sense Pre-Soldered (8MB PSRAM, OV3660, USB-C)
  - ※ OV3660 → `xclk_freq_hz=20000000` 분기 필수
  - **OV3660 실측 확정 (2026-06-22 PoC-(17) 1차 부팅 검증)**: 시리얼 `sensor_t.id.PID = 0x3660` = 라이브러리 `OV3660_PID(0x3660)` 일치 → 가정(OV3660)이 실측으로 확정됨. xclk 20MHz 분기 = 정합, **센서 코드 수정 불필요**. (PSRAM 8MB OCTAL 인식 / QVGA JPEG 연속 캡처 정상 → 카테고리 32 참조)
  - **WiFi = 외장 u.FL/IPEX 안테나 필수 (2026-06-22 PoC-(17) 실측 확정)**: 안테나 미장착 시 PRIMARY/FALLBACK 양쪽 SSID 15s timeout 반복. **u.FL 안테나 장착 즉시 RSSI -53dBm 강신호로 0.7초 내 연결** + HTTPS POST 200. 시연 체크리스트 0순위 항목 (미장착 = WiFi 100% 실패). 카테고리 23(모바일 핫스팟) 정합.
- **마이크**: INMP441 (THC-AS01 호환 칩, SNR 61dBA) — `I2S_NUM_1`
- **사람 감지**: VL53L5CX-SATEL (8x8 ToF, I2C)
- **핀 페리페럴**: I2S0(카메라) ↔ I2S1(마이크) 분리, strapping 핀(D0/D3/D6/D7) 회피

---

## 카테고리 2: 핀 표 (변경 시 반드시 갱신)

| 모듈 | 신호 | XIAO | GPIO | 페리페럴 |
|------|------|------|------|---------|
| INMP441 | SCK | D1 | 2 | I2S1 |
| INMP441 | WS  | D2 | 3 | I2S1 |
| INMP441 | SD  | D8 | 7 | I2S1 |
| INMP441 | VDD/GND/L_R | 3V3/GND/GND | - | - |
| VL53L5CX | SDA | D4 | 5 | I2C |
| VL53L5CX | SCL | D5 | 6 | I2C |
| VL53L5CX | PWREN | 3V3 직결 | - | (전원 enable) |
| VL53L5CX | LPn   | 3V3 직결 | - | (I2C enable) |

★ **PWREN/LPn을 HIGH로 구동하지 않으면 센서 셧다운 상태로 SDA를 LOW 고착 → I2C 전면 불통** (2026-08-07 실측 확정, 카테고리 9.1 참조). SDA=D4(GPIO5)/SCL=D5(GPIO6)는 실측 일치 = SSoT 유지.

---

## 카테고리 3: 시스템 흐름

- **ToF**: 상시 ON (8x8 그리드 15Hz), ESP32에서 차단 X, 메타데이터로 첨부
- **음향 트리거**: 단순 RMS 임계값 (옵션 A), PoC 1주차 자체 측정 후 80% 지점 확정
  - ⚠️ **2026-09-02 주의 (6.3(e))**: M3 배경 rms 2.4M은 **랩실 사람 대화가 포함된 값 = 무음 기준선 아님** — 이 값으로 "80% 지점"을 산출하면 안 됨. 확정 = 조용한 환경 재측정 + 초인종/노크 실측 후 분리점(M5 소관). **임계값 미확정 유지.**
- **클래스별 ToF 정책 분기 (서버)**:
  - 화재경보: ToF 우회 (무조건 발송)
  - 노크: ToF 사람 검증
  - 초인종: ToF + (등록 시) SP/DTW + cosine
- **신뢰도 임계값**: 70% 미만 미전송
  - ~~🔴 **코드 불일치 (2026-07-06 PoC-(22) catch, 미결/정정 예정)**: 본 SSoT=**0.70**인데 서버 `server/app/constants.py:15 CONFIDENCE_THRESHOLD = 0.6` → **코드가 SSoT 위반**. 단, 데모 시드(`server/seed.py`)는 confidence를 명시 세팅해 `/detect` 임계값 로직을 타지 않으므로 발표 데모는 무영향. **코드 정정(0.6→0.7)은 별도 fix PR 필요**(2026-07-06 미착수) → 다음 서버 코드 작업 시 우선.~~ ※ 임계값 SSoT = 본 카테고리 3(seed.py 주석의 "6.1 계열" 표기와 무관).
  - ✅ **해결 (2026-07-07 PoC-(24), PR #19)**: `server/app/constants.py:15 CONFIDENCE_THRESHOLD` **0.6→0.7** 정정, SSoT(0.70) 정합. 경계 = `server/app/utils.py:94 if top < CONFIDENCE_THRESHOLD`(strict) → 정확히 0.70 = 발송(경계 미포함 제외) = "70% 미만 미전송" 정합. 정의 = constants.py 단일 SSoT(참조 = utils.py 1곳).
  - **⚠️ [미결 — §9 사용자 판단 요청] 화재경보가 신뢰도 게이트도 우회하는가 (2026-09-02 감사 G12)**: 위 "클래스별 ToF 정책 분기" ①과 "신뢰도 임계값" ②가 코드상 함께 참조될 때 범위가 불명확하다.
    - ① "화재경보: ToF 우회 (무조건 발송)"
    - ② "신뢰도 임계값: 70% 미만 미전송"
    - 코드 실측(`server/app/utils.py`): `fire_alarm` 분기(78행대, `if predicted_class == "fire_alarm":`)가 신뢰도 비교(87행대, `if confidence < CONFIDENCE_THRESHOLD:`)**보다 먼저** 위치해 즉시 `return`한다 — 즉 현재 구현은 **화재경보가 ①뿐 아니라 ②도 함께 우회**하는 쪽으로 되어 있다(저신뢰 화재경보도 1차 발송됨).
    - **본 문서는 결론을 내리지 않는다**(문서 전용 세션, §9 대상). ①의 "무조건"이 ToF 게이트 문맥에 한정되는지 신뢰도 게이트까지 포함하는지, doorbell→fire_alarm 오분류가 confusion matrix상 10건으로 최다인 점이 시연 리스크가 되는지, 화재경보는 지속음이라 miss해도 다음 트리거에서 재포착되는지 — 이 판단들은 **사용자 결정 필요**.
    - **[상태 갱신] 실경로 재현 확인 (실측 2026-09-05 / 문서 반영 2026-09-05, 근거유형 = 실측)**: mock 예측 반복 호출에서 `fire_alarm` 신뢰도 **0.91 / 0.82 / 0.66 / 0.58 / 0.53 / 0.47** 건이 관찰됐고, 임계값 0.70 **미만인 건들도 1차 카카오톡이 발송**됐다 — 위 코드 실측의 "저신뢰 화재경보도 1차 발송됨"이 **실경로에서 재현**된 것이다(2026-09-03 A-1 실측 때는 mock 랜덤이 0.92라 미재현이었다). ⚠️ **본 갱신도 결론을 내리지 않는다** — 상태만 "코드 실측 → 실경로 재현 확인"으로 올리며, 판단은 여전히 사용자 대기다.
- **카메라 캡처**: Lokch777 패턴 멀티코어 (Core 1 병렬)
- **1차 알림 목표**: ≤5초 (텍스트), **2차 알림 목표**: ≤15초 (사진+STT)

---

## 카테고리 4: ML

- **YAMNet Fine-tuning**: raw waveform(16kHz mono) → 1024-dim → Dense(3)
- librosa는 16kHz mono 변환 전용 (멜스펙트로그램 직접 입력 X)
- **초인종 개인 등록**: 멜스펙트로그램 2D 템플릿 + FastDTW SP/DTW + cosine distance
- **train/val/test 분할**: 파일 단위 필수 (data leakage 방지)
- **predicted_class 3종 (enum, 2026-05-28 PoC-(14) 확정)**: 초인종(`doorbell`) / 노크(`knock`) / 화재경보(`fire_alarm`) — Dense(3) 출력 매핑. 서버/대시보드 API 전역 enum (코드: `dashboard/src/types/notification.ts` `PredictedClass`). 한글 표기 = **"초인종"** (카테고리 3/5 SSoT 컨벤션, "도어벨" 미사용 — 카테고리 29.5 참조)

---

## 카테고리 5: ML 데이터

- **확보량(01_clips)**: 초인종 436 / 노크 714 / 화재경보 1648 = **2,798클립**
- **분할 결과**: train 1954 / val 434 / test 410
- **직접 녹음 계획(필수)**: 초인종 90 / 노크 180 / 화재경보 240
- **Augmentation**:
  - time-stretching ×0.85/1.15
  - BG noise SNR(초인종·노크 10/20dB / 화재 25/35dB)
  - volume -6dB
  - pitch ±2semitone (한국 환경음만)
    - ※ **"한국 환경음" 정의 확정 (2026-07-07 PoC-(24), PR #21)**: = `direct_` prefix 직접녹음 클립. AI Hub S_103(화재)는 제외(prefix 없어 구조적 미포함). 상세 = 33.3-①.
  - SpecAugment freq=10/time=5
- **클래스 가중치**: class_weight + sample_weight 1.5~2.0배 (한국 환경음)
- **제외**: FSD50K Alarm 435, AudioSet fire_alarm 100 (대부분 차량 사이렌)
- **저장 정책**: 8주차 진입 시 재정의 (현재 `ml/` 폴더는 `.gitkeep`만)

### 5.1 데이터 저장 정책 확정 + 실측 배분 (2026-07-01 신설 — 위 계획값 append, 훼손 X)

> ML 크리티컬 패스 선작업(2026-07-01) 실측. 위 "확보량/분할 결과/저장 정책"은 **계획값**(파일단위 가정) → 본 5.1이 **실측 확정값**. 상세 = 카테고리 33 + decisions-log 2026-07-01.

- **직접녹음 파일명 확장 (2026-07-09 PoC-(26))**: `direct_doorbell_{유닛}_{테이크}.wav`(예: `direct_doorbell_A_01.wav`). 근거 = USP 재검증(DTW 스파이크)의 원본그룹핑이 **유닛을 알아야 재-누름 intra 측정 가능** — 기존 `direct_doorbell_001`은 파일=원본그룹이라 재-누름이 전부 inter로 구조적 오분류(측정 불가). `direct_` prefix 유지 → pitch 마커(33.3-①) 호환. ~~※ **DTW 스파이크에 유닛 그룹핑 모드 추가 필요**(`--clips-dir` 04 재실행 전, 소액 PR = 후속).~~
  - **✅ 해소: PR #31 (2026-08-03 PoC-(33), `a332343`)**: 자동 `direct_` prefix 분기(KOREAN_SOURCE_MARKERS 컨벤션 정합) 추가 → `--clips-dir 04` 재실행만으로 재-누름 intra 측정 가능. 회귀 근거 = 01_clips **436→182 그룹 불변 + 멤버십 sha256 before==after 동일**(1.713 재현성·비교가능성 보존) + 단위테스트 19/19, 마진 공식·거리·정규화·출력 무변경. ⚠️ **04=0이라 실 개체 마진 미산출**(그룹핑 로직+회귀 검증까지만) — 실측 = 직접녹음 유입 후 defer(학습 19).
- **4유닛 녹음 프로토콜 확정 (2026-07-09 PoC-(26))**: 시연 도어벨 **4개**(★ 같은 모델 ×2 필수 — 옆집 최악 케이스=동일 제품) × 15~18테이크 ≈ 90클립. inter = C(4,2)=**6쌍**(같은모델 1쌍 + 다른모델 5쌍). 3유닛 검토했으나 4유닛 확정(inter 6쌍이 벤치 신뢰도 = 1.713 상한 교훈 = 오염 벤치 회피). 부스엔 필요시 3개, 녹음은 4유닛.
- **저장 위치 확정**: 데이터셋은 원래 repo 밖 형제 폴더 → **OS TCC(EPERM)** 로 Claude Code 접근 차단(카테고리 저장소 룰 reference `repo_sibling_tcc_block`) → **학부생 홈 `~/ML 학습 데이터/ddingdong_dataset` 로 이동 확정**. repo엔 **오디오 미커밋**(`.gitignore` `*.wav` 등), **코드/config/manifest 스키마만** 버전관리. 실 파이프라인·학습 실행 = 학부생 로컬 셸(`DDINGDONG_DATA_ROOT="…" python -m ml.pipeline.run_all`).
- **폴더 구조 실측(6단계)**: `00_source_raw`(FSD50K 4만 dump 포함, **입력 아님**) / `01_clips`(**정본 입력 2,798** = doorbell 436 / knock 714 / fire_alarm 1648, 16k mono Int16) / `02_preprocessed` / `03_augmented` / `04_direct_recording`(현재 **0**, 8주차 직접 녹음 유입 슬롯) / `05_final_dataset`(조립 산출).
- **빈 클립 6개 실측**: `01_clips/fire_alarm` 의 AI Hub S_103 원본 6개가 **length-0 wav** → preprocess가 skip(fire_alarm 1648 → **1642**). 원본 삭제 X, **코드 가드로 처리**(PR #11 skip + PR #14 stale auto-clean). 상세 = 카테고리 33.1.
- **05 실측 배분(원본단위 group split + train만 augment 반영)**: **train 11,586 / val 437 / test 424**. 위 계획값(train 1954/val 434/test 410, 파일단위 가정)과 다름 = ① 원본(source) 단위 그룹 분할(누수 방지, PR #12) ② train만 증강 유입 ③ fire_alarm 빈 6개 제외 반영. 상세 = 카테고리 33.2.

---

## 카테고리 6: 서버

- AWS EC2 t3.small (서울, 2GB RAM)
- Nginx + Gunicorn(워커 2개, `preload_app=True`) + Flask
- SQLite + Flask-SQLAlchemy
- TLS: Let's Encrypt + ESP32는 `setInsecure()` (PoC 한계)
- **API**: `/api/v1/*` 버저닝 (2026-05-28 확정 — 기존 `POST /api/detect`·`POST /api/enrich`에서 버저닝 전환, decisions-log 2026-05-28 참조)
- **구현 골격 (2026-06-14 Phase 2-1차, PR #2 `37a92b3`)**: `server/` = Flask app factory + Blueprint(`/api/v1`) + Flask-SQLAlchemy 모델 2종(`notifications` / `idempotency_keys` 24h TTL) + 엔드포인트 4종. ML 추론 = mock(실제 YAMNet 11주차), HTTPS/EC2 = 11주차(현재 로컬 http). 상세 = 카테고리 8.1 2-1차 항목
- **미결 (rate limit Redis 교체, 11주차)**: 현재 rate limit = in-memory dict. Gunicorn 워커 2개(`preload_app=True`) 시 워커별 dict 분리 → rate limit 무효화. 11주차 배포 진입 시 Redis(공유 스토어) 교체 필요
- **CORS 처리 (2026-06-15 Phase 2-2차, PR #3 `cec9c9b`)**: `flask-cors` 미설치 → React dev 서버 → Flask 호출 시 **Vite dev proxy(dev 전용)**로 동일 origin 우회 (대시보드 `VITE_API_BASE_URL=/api/v1` 상대 경로 → Vite가 백엔드로 프록시, 백엔드 CORS 헤더 미추가)
- **미결 (배포 CORS, 11주차)**: Vite dev proxy = 개발 전용. 11주차 배포 진입 시 proxy 무효 → Nginx 동일 origin 서빙(대시보드 정적 + `/api/v1` 리버스 프록시) or 백엔드 CORS 헤더 별도 필요
- **🟡 [신규 미결] 2워커 동시성 — `/enrich` 재처리 가드(409) 경합 (발견 2026-09-05 / 문서 반영 2026-09-05, 근거유형 = 논증)**: 같은 `client_request_id`로 `/enrich`가 동시에 들어오면 409 가드가 경합할 수 있다(SELECT~UPDATE 간 격리 없음). 기존 구조의 성질이나 7.6 2차 발송이 붙으며 결과가 "**중복 사진 발송**"으로 커졌다. 실 ESP32는 단일 기기 + 5초 rate limit이라 현실 위험은 낮다. 해소 = 위 rate limit Redis 교체와 동일한 11주차 구간.

### 6.1 API 명세 1차 확정 (2026-05-28 PoC-(14), Phase 1 대시보드 셋업 연동)

> 상세 요청/응답 JSON 구조 = `dashboard/src/types/` (`api.ts` / `notification.ts` / `stats.ts`) + PoC-(14) 채팅방. 본 카테고리엔 **결정 + 근거만** (JSON 미박음).

- **엔드포인트 버저닝**: `/api/v1/*` — `detect`(ESP32→서버 1차) / `enrich`(ESP32→서버 2차 사진+음성) / `notifications`(대시보드 폴링) / `stats`(대시보드 폴링). 근거: 향후 API 변경 시 v1/v2 병행 + 대시보드 폴링 엔드포인트 확장
- **인증 분리**: Device Bearer Token (ESP32, `firmware/include/secrets.h`) ↔ Dashboard Bearer Token (React, `.env`) — 디바이스/대시보드 권한 도메인 분리
- **통신**: HTTPS 강제 (Let's Encrypt + ESP32 `setInsecure()`, 본 카테고리 TLS 항목 일치)
- **요청 추적 분리**: `client_request_id` (ESP32 자체 생성, 재시도 멱등 키) + `request_id` (서버 ULID 발급) — 디바이스/서버 추적 ID 분리 (코드: `notification.ts`)
- **HTTP Status 8종 + rate limit**: `device_id` 5초당 1회, 초과 시 `Retry-After` 헤더
- **Idempotency**: `idempotency_keys` 테이블 (24시간 TTL) — `client_request_id` 기반 재시도 중복 차단
- **stats period**: `today` 단일 (Phase 1, 코드 `stats.ts` `StatsPeriod`)
- **stats 알림 속도(`timing_metrics`) 실계측 도입 (2026-07-06 PoC-(22), PR #18 `d57f3ae`)**: `_build_stats`의 `timing_metrics` 하드코딩 0 placeholder → **실 타임스탬프 집계**로 전환. 1차 지연 = `primary_sent_at − detected_at`(ms), 2차 지연 = `secondary_sent_at − detected_at`(ms), 달성률 = 1차 ≤5초 / 2차 ≤15초 이내 비율(목표 = 카테고리 3 연동). null 안전(`sent_at is not None` 필터로 미발송·2차 미완료건 자동 제외) + ZeroDivision 가드. `stats.ts` `TimingMetrics` 6키(avg/max ms ×2 + under-rate ×2)와 1:1 정합(신규 필드 발명 X, 학습 16). **의의**: 원래 11주차 실 계측 몫을 선작업 → 실 하드웨어 데이터 유입 시 그대로 실값 산출(데모 픽션 아님, 재사용 코드). **수정 2곳 한정**(routes.py timing 블록 + `seed.py`), 타 집계·프론트·타입 무변경.
  - ~~**🟡 [신규 미결] `primary_sent_at`이 `detected_at`과 동일 변수로 세팅됨 (2026-09-02 감사 G14)**: `server/app/routes.py`(139/147행대) 확인 결과 `detected_at=now` / `primary_sent_at=now if pred["primary_sent"] else None` — 두 값이 **같은 `now`**를 공유한다. 그 결과 위 1차 지연(`primary_sent_at − detected_at`)이 **real 경로에서도 항상 0ms**로 집계된다. 실제 처리 지연(디코딩+추론+판정)이 존재함에도 timing_metrics가 이를 반영하지 못함 — 11주차 실계측 정합성에 영향.~~ **✅ 해소 (2026-09-03 PoC-(39), PR #40 `70aea1d`)**: `routes.py`에서 `detected_at`과 `primary_sent_at`을 분리 세팅하도록 배선 → 1차 지연 실측 **171ms**(변경 전 구조적 항상 0ms). 카카오 왕복 실측 p95 84.1ms(7.2)와 자릿수 정합(상세 = 카테고리 7.5(a)).
- **detected_at 정의 명확화 (신규 결정, 2026-07-31 PoC-(30))**: 위 `timing_metrics`(1차 지연 = `primary_sent_at − detected_at`) 계산식의 detected_at 시작점 = **ESP32 트리거 시각**(소리 감지 순간)으로 확정 — 서버 수신 시각 아님. ※ decisions.md SSoT에 미결로 등록된 적 없음(취소선 대상 없음, 순수 신규 명확화). 근거 = ① 청각장애인 체감(초인종 울림~폰 알림 전체) 정직 반영 ② HTTPS 포함 전체 체인 p95 ≈2.0초(카테고리 6.2)라 5초 예산에 3초 여유 = 정직하게 재도 달성률 손실 0(오히려 방어력↑). ⚠️ **구현은 11주차 defer**: ESP32가 트리거 타임스탬프를 `/detect` payload에 동봉 + ESP32-서버 시계 동기화(NTP) 필요 = 통합 소관. 현재는 **정의 확정만**, 구현 방식은 11주차.
- **데모 시드 + 더미 이미지 인프라 (2026-07-06 PoC-(22), PR #16 `6b26bd6`)**: `server/seed.py` = 결정론적 5건(초인종 완료 / 노크 완료 / 노크 2차 처리중 / 화재 우회 / 초인종 미발송) DB 시드(delete→insert idempotent, `detected_at` 동적 오늘 → stats "오늘" 필터 통과, `idempotency_keys` 보존). 더미 이미지 = `dashboard/public/static/captures/*.svg`(가로 2:1, 직접 생성 → 저작권·초상권 무관, vite public 서빙 → 프록시·정적 라우트 0줄). PR #18에서 썸네일 `object-cover` 세로중앙 safe-zone 재작성으로 **잘림 수정**. mock random으로 재현 불가한 3클래스·상태 조합을 대체하는 발표용 완성 UX 확정 렌더 목적(8.3 연동).

### 6.2 ML 추론 서빙 조기경보 실측 (2026-07-08 PoC-(25), PR #22 `169a2fc`)

> 8주차 fine-tuning·11주차 EC2 배포 전, "YAMNet+TF가 t3.small(2GB)에 fit + 5초 지연 예산 통과"라는 최대 서버 리스크를 선제 de-risk. 산출 = `server/inference/` sibling 패키지(라이브 app 무수정, lazy TF import). ※ 실측 = 학부생 로컬 M4 venv(실 SavedModel, 2층). 더미 기준(1층)은 숫자 무의미 — 벤치 하네스 경고 배너 참조.

- **메모리 (peak RSS 489.1MB / 2048MB 예산 → OK)**: 분해 = baseline 35.8 → +TF import **375.8**(대부분 여기) → +YAMNet load **51.9** → infer 489.1. **TFLite 전환 불필요**(권고선 = 예산 85% ≈ 1740.8MB, 489.1은 한참 미달). 상수 = `server/inference/constants.py`(`MEM_BUDGET_MB=2048` / `TFLITE_ADVISE_RATIO=0.85`).
- **지연 (p50 4.26ms / p95 6.74ms / 5000ms 예산 → OK)**: M4 하한값 — t3.small이 수 배 느려도 예산 여유. **★ 함의: 1차 ≤5초 병목은 ML 추론이 아님.** 실 병목 = ESP32 오디오 업로드(네트워크) + 카카오 발송 왕복 → 14주차 타이밍 튜닝 타겟을 ML에서 네트워크/외부 API로 재조정.
  - ※ 7/29 카카오 실측으로 정정: 카카오 왕복 p95 84.1ms — 실 병목은 **업로드 단독**(카테고리 7.2 참조).
- **gunicorn 2워커**: `preload_app=True` fork 후 모델 페이지 copy-on-write 공유 → 실메모리 ≈ 1×모델 + 2×워커 오버헤드(2×모델 아님). 워커 1개 하한 490MB → 2워커 최악 ~1.5GB, 2GB 안(11주차 EC2 최종 확인).
- **🔴 wire 계약 갭 (통합 리스크, 11주차 통합 체크포인트로 못 박음)**: 현재 `/detect` = `client_request_id`+`device_id` JSON만 수신, **오디오 바이트 미수신**(`mock_prediction()` = random). byte→waveform **디코딩** 계약은 `audio_decode.py`에 정의(PCM int16 LE / 16kHz / mono / ÷32768 → [-1,1])되나, **transport 계약(multipart / base64 / raw body)은 미정의** = 11주차 통합 시 확정 필요. + ~~**int16 가정은 firmware 미검증**(INMP441 I2S 24/32bit → ESP32 int16 변환 여부 미확인) → 포맷 불일치 잠복.~~ **✅ 2026-09-02 해소 — tz=6 실측으로 `int16 = raw >> 14` 확정**(PR #38 `25b0d16`, 상세 = 신설 절 **6.3**). 서버 `audio_decode.py` int16 LE 계약과 정합 = 포맷 불일치 잠복 해소.
- **transport 계약 A안 확정 (2026-07-09 PoC-(26))**: multipart/form-data + int16 PCM raw bytes(64KB/2초). 근거 = 업로드가 1차 5초 병목 후보(본 카테고리)라 페이로드 최소화(base64 +33% 오버헤드 회피) + `audio_decode.py` int16 계약 무수정 정합 + 메타(`client_request_id`/`device_id`) form field 동봉. → **wire 갭 transport 절반 CLOSE.** 나머지 절반(INMP441 I2S 24/32bit→ESP32 int16 변환 검증)은 마이크 결선 후. → **✅ 2026-09-02 나머지 절반도 CLOSE**(M1~M4 완주, `>>14` 확정 — 6.3). **wire 계약 갭 전체 CLOSE.**
- **PR #24 (server, /detect 실 오디오 배선, `6ab693f`)**: JSON→multipart 교체 + `server/inference/audio_decode.py`(frozen) import 호출로 디코딩. 디코딩 계약 실증 — 합성 440Hz 사인톤 64KB → 32,000 샘플/float32/RMS **0.353528**(이론 0.5/√2=0.3536 일치)/decode 0.038ms. curl 회귀 10종 0(rate limit 429/idempotency 200 replay/auth 401/타 라우트 200·200·409 무변경). 게이트 순서 = idempotency→rate limit→decode→mock. `numpy==2.5.1` 라이브 venv 추가(TF 미유입, audio_decode는 numpy 전용). 상수 `AUDIO_FILE_FIELD="audio"`/`AUDIO_MAX_BYTES=320000`. 예측 = mock 유지(스코프 분리).
- **PR #25 (firmware, ESP32 업로드 측정 하네스, `f0e4163`)**: 합성 int16 PCM(PSRAM) + multipart POST + 지연측정(N=14, ≥6초 간격, p50/p95). 컴파일 성공(RAM 13.5%/Flash 22.2%, Stage 2 트리거 미달). ~~**⏳ 런타임 미실측**(보드 USB 미연결 → compile-only + prereq 체크리스트 핸드오프)~~ **✅ 런타임 실측 완료 (2026-07-28 PoC-(27))**: iPhone 핫스팟(2.4GHz, RSSI -45) + Flask 로컬(172.20.10.3, M4). Phase1 64KB×14 = p50 305/p95 1043ms(min156/max1879), 201 14/14. 스윕 32/64/128KB avg 95.7/318.3/358.0(크기 2배여도 미미=무선 오버헤드 지배). 분해 connect 270/post 279/total 549 = **TCP 연결이 지연 절반**. 판정: 5초 예산 대비 p95 20%, 업로드 병목 아님. 인사이트: keep-alive 재사용 시 지연 절감 여지(14주차 튜닝 타겟). iter11~13 튐=핫스팟 간헐 스파이크. 로그 원본 = repo 밖 ddingdong-측정결과/upload_spike_2026-07-28.txt. whitelist env(env:poc blacklist 미접촉). secrets = gitignored blind-append 플레이스홀더(실 값 = 학부생 런타임 전 교체).
- **서빙 연결 3결정 (2026-07-09 PoC-(26) Step 6 조사, frozen 수정 불요 = 전부 라이브 앱 신규코드)**: (a) 모델 **싱글턴 1회 로드**(요청당 3.66s 로드는 5초 예산 잠식) (b) **TF 라이브 venv 추가 = RSS +375~490MB(본 카테고리 실측) 실발생 → 11주차 EC2 2GB 재확인 + 아키텍처 결정**(웹프로세스 상주 vs 별도 서빙 프로세스) (c) (1,3) softmax → `mock_prediction` 딕셔너리 매핑 신규. ※ **infer 103ms(콜드 첫 호출, 그래프 트레이싱/워밍업 포함) ≠ 위 6.74ms(웜 추론)** — 위상 구분(혼동 방지).
  - ※ **2026-07-29 확정 = b-1 웹프로세스 상주**(gunicorn preload + ModelRunner 싱글턴 상주, COW 공유). 근거 = 실측 RSS 489MB = 2GB의 24%(분리 압박 없음) + 추론 웜 6.74ms(IPC 분리 이득 0) + 졸작 규모에 b-2(별도 서빙 프로세스) 오버엔지니어링. ⚠️ 트리거 = 11주차 EC2(t3.small) 실측 RSS 예산 초과 시 b-2 재검토(M4는 하한). chunk 2(/detect 실 서빙 통합)의 선행 게이트 해소.
- **★ 1차 5초 체인 전 구간 실측 완성 (2026-07-29)**: 업로드 p95 1043ms(7/28, 본 카테고리 PR #25) + 디코딩 0.04ms(PR #24) + 추론 웜 p95 6.74ms(PR #22, 콜드 첫 호출 시 103ms) + 카카오 왕복 p95 84.1ms(7/29, 카테고리 7.2) = **합산 p95 ≈ 1134ms = 5초 예산의 23%**(콜드 추론 가정 시 ≈1230ms = 25%). 잔여 여유 ≈ 3.87초. **판정: 동기 발송으로 충분 — 비동기 발송 아키텍처 불필요.** 실질 병목 = 업로드 단독(체인의 92%). "카카오 왕복 = 유일 미측정 구간" **CLOSE**. (실측 상세 = 카테고리 7.2)
- **HTTPS(TLS) 업로드 재실측 하네스 (2026-07-29 신설, PR #26 branch `feat/upload-spike-tls-harness`)**: 위 7/28 실측은 평문 HTTP(로컬) — 프로덕션(6.1: Let's Encrypt ECDSA P-256 + `setInsecure()`)이 체인 92% 구간에 얹는 **TLS 핸드셰이크 가산분(Δ_TLS)이 최대 미지수**라 재실측 신설. 구성 = `env:upload_spike_tls` whitelist(+`upload_spike_tls_*` 3파일, 7/28 하네스 frozen 복제) + `firmware/tools/tls_probe_server.py`(ECDSA P-256 self-signed :5001, transport 전용 — 실 /detect auth/파싱 미복제). 설계 = **헤드라인은 진짜 콜드**(이터마다 WiFiClientSecure 신규 생성 — 실이벤트 cadence상 프로덕션은 매번 콜드) + **Δ_TLS 인터리브 분해**(이터마다 같은 포트에 평문 TCP 프로브 → secure 풀 연결 back-to-back, Δ=동일 순간 RF 조건) + 1순위 가치 = 신뢰성(핸드셰이크 성공률/HTTP 200 2층)·메모리(heap 워터마크+PSRAM) + 협상 cipher/TLS 버전 per-iter 로깅(ECDHE-ECDSA 실반영 검증) + 64KB multipart×14(≥6s) + [부기록] back-to-back 세션 재개 관찰. **★ Step 1 설치 core 실측 (학습 15)**: Arduino-ESP32 **2.0.17**(패키지 `3.20017` 접두는 PIO 규약 — platformio.ini 상단 주석 "core 3.x"는 오독) / mbedTLS **2.28.7** / **TLS 1.3 미지원 확정**(sdkconfig TLS1_2까지만) → **측정 = TLS 1.2 / 2-RTT**. §9 정지 보고 후 pivot 승인: 프로덕션 클라이언트도 동일 core라 실전도 1.2/2-RTT 협상 = 본 측정이 프로덕션 대표(대표성 손실 아님). `setBufferSizes()`는 ESP32에 부재(ESP8266 전용) — TLS 버퍼 = sdkconfig `MBEDTLS_SSL_MAX_CONTENT_LEN=16384` 고정, heap 부족 시 축소 튜닝 불가(워터마크 관찰로 대체). 판정 기준(F5, 부트 배너 박제) = ① 핸드셰이크 성공률 ≥13/14 ② heap 최저 워터마크 >40KB + 리셋 0회 ③ Δ_TLS 가산 후에도 5초 예산 여유 내. 프로덕션 추정식 = 로컬_핸드셰이크(CPU분 근사) + 2-RTT×EC2_RTT + DNS 1회(별도 가산 — "완료" 아닌 근사임을 명시, 학습 19). **⏳ 런타임 미실측**(compile-only 핸드오프 — 학부생 flash + tls_probe_server 기동 후 판정. secrets.h blind-append 플레이스홀더 교체 필요). → **✅ 2026-07-29 런타임 실측 완료 (PoC-(29))**: Δ_TLS(tls_handshake) **p50 678 / p95 862ms**. secure_connect(TCP+TLS) p50 720 / p95 882ms vs 평문 TCP connect p50 48 / p95 245ms. post(64KB) p50 917 / p95 1105ms. **total(conn+post) p50 1677 / p95 1863ms**. 성공 14/14 + HTTP 200 14/14. heap 최저 워터마크 244,616B(리셋 0회). **세션 재개 없음** — Phase 2 back-to-back tls_hs ~695ms = 콜드와 동일 → connect마다 fresh 핸드셰이크(context7 정합). 협상 cipher = `TLS-ECDHE-ECDSA-WITH-AES-256-GCM-SHA384`(F4 cert 실반영 확인), 측정 = TLS 1.2/2-RTT(core 2.0.17 mbedTLS 2.28.7, 1.3 미지원). 조건 = iPhone 핫스팟 RSSI -37 + 로컬 `tls_probe_server.py`(M4, ECDSA P-256 self-signed). 프로덕션 가산 = 2-RTT×EC2_RTT(~15ms) + DNS 1회 ≈ +50ms → **추정 total p95 ≈ 1.9초**. **★ 함의: TLS 켜도 1차 체인 총합 p95 ≈ 2.0초 = 예산 40% — 동기 발송 충분, keep-alive 필수 아님**(콜드 862ms를 매 이벤트 물어도 예산 내). 7/28 HTTP total 1043 대비 Δ +820ms = TLS 핸드셰이크분. 실측 로그 원본 = repo 밖 `~/ddingdong-측정결과/upload_spike_tls_2026-07-29.txt`. PR #26(`ca19230` 머지).
- **※ 2026-07-29 실측 정합 주석 (core 버전 / pio 경로)**: firmware core = Arduino-ESP32 **2.0.17** / mbedTLS **2.28.7**. 지침 등의 "v3.20017"은 **PIO 패키지 버전 문자열**(`3.20017.241212`)이며 core 3.x 아님(레거시 `driver/i2s.h` 의존 = 2.0.x 확정). pio 실행 = `~/.platformio/penv/bin/pio` 절대경로(PATH 미등록, 7/28·7/29 재현).
- **2차 /enrich wire 계약 서버 절반 착수 (2026-07-31 PoC-(30), PR #27)**: transport = multipart/form-data(1차 A안 동형) + 이미지·오디오 파트 **둘 다 required**(ESP32 항상 둘 다 전송). 상수 = `IMAGE_FILE_FIELD="image"` / `IMAGE_MAX_BYTES=512000`(★ abuse/메모리 가드 전용, 캡처 해상도 무관 — 해상도 확정 11주차) 신설 / `AUDIO_*` 재사용. 이미지 검증 = 크기 + SOI 매직바이트(0xFFD8). 오디오 = 프로즌 `audio_decode.py` import 디코딩(합성 사인톤 RMS 0.3535 실증). curl 15종 회귀 0. **mock 상태전이 커밋**(mock_enrichment로 image_url/stt/enrich_status/secondary_sent_at 세팅 + db.commit) — 실 카카오 이미지 업로드/Clova STT는 11주차(스코프 분리, detect mock 동형). `enrich_status` 재처리 가드(409). → 2차 15초 체인 계약 토대. **나머지 절반 = ESP32측 이미지/오디오 전송 펌웨어**(마이크·카메라 결선 후).
- **/detect 실추론 배선 = 1차 5초 체인 마지막 mock 조각 실코드화 (2026-07-31 PoC-(30), PR #28)**: `mock_prediction()` → `ModelRunner` 싱글턴(프로즌 `server/inference/model_runner.py` import, 파일 무수정) 실추론 교체. env 게이트 `DDINGDONG_MODEL_PATH`(부재 시 mock 유지 = CI·문서환경 안 깨짐, 실 외부 API 미통합). TF **lazy import**(요청경로 밖) + 실추론 모드 TF 부재 시 fail-fast(조용한 mock 폴백 방지). warmup = **app factory 기동 1회**(요청당 3.66s 로드 회피, 본 카테고리 (a)) — ⚠️ **gunicorn preload+post_worker_init COW 최적화는 11주차 배포 defer**(현 dev=flask 단일프로세스라 검증 불가, 학습 15). 콜드스타트 = "제거"가 아닌 "**요청경로 밖 이동 + 서버 기동 후 첫 준비 ~4s = 시연 전 예열 필수**"(학습 19 정직표기).
  - **★ pivot 기록**: 위임 초기 가정("threshold 게이트가 routes.py 예측 뒤")은 **실측 반박** — 판정 로직(threshold 비교 / fire_alarm 우회 / ToF mock / primary_sent·enrich_status·skip_reason 결정)이 **`mock_prediction()`(utils.py) 안에 랜덤 생성과 응집**돼 있어 "예측값만 교체" 불가. → §9 정지 후 pivot 승인: `_apply_prediction_policy()` **순수 추출**(로직 무변경, 리팩토링 전후 500시드 mock 반환 dict **바이트 동일** 증명) → mock/real 경로 공유. `CONFIDENCE_THRESHOLD=0.7` 값·strict 경계(`if top < 0.7`) 불변. `utils.py`는 프로즌 아님(라이브 앱). 학습 19 사례 추가(위임 근본원인 진단도 코드 재검증).
  - ~~**⏳ real 모드 미검증**: 이 배선은 로컬 TF 미설치 환경이라 **로직만 검증**(합성 (1,3) 점수 3종 → pending/skipped 분기 정상 + fail-fast 실증). 실 SavedModel warmup 로그(load_ms/warmup_ms) + real curl = **학부생 로컬 M4 venv 검증 대기**(`make_dummy_savedmodel` 더미 + `DDINGDONG_MODEL_PATH` 기동). "완료" 아닌 "로직 검증 + real 런타임 대기"로 표기.~~ **✅ real 로컬 검증 완료 (2026-07-31 PoC-(30))**: 학부생 로컬 M4, Python 3.11 별도 venv(`server/venv_real` — 기존 `server/venv`=3.14는 TF wheel 부재로 real 불가)에서 `make_dummy_savedmodel` 더미 SavedModel(서빙 시그니처 (1,None)f32→(1,3)f32 정합, random-init 스텁 배너) + `DDINGDONG_MODEL_PATH` 기동 → real 추론 경로 실증. curl `/detect`(합성 int16 64KB) → HTTP 201 + `all_scores` 합=1.00(doorbell 0.37/knock 0.46/fire_alarm 0.17) + confidence 0.46 < 0.7 → `skip_reason=low_confidence` + `primary_sent=false`(=`_apply_prediction_policy` threshold 게이트가 real 경로에서도 작동) + `enrich_status=skipped`(상태전이 일관). "로직 검증 + real 런타임 대기" → "**real 경로 로컬 검증 완료**"로 승격(학습 19 정직 표기 — 미검증을 완료로 오기 안 했기에 실측 후 정직 승격).
- **`model_serving.py` frozen 등록 확정**: 위 real 검증 통과로 `server/app/model_serving.py`가 **frozen 등록 확정**(라이브 앱 import 호출만, 파일 무수정 대상 편입). ※ "real 검증 후 frozen 등록 후보" → 확정.
- **numpy 버전 규명 (2026-07-31)**: `requirements.txt` `numpy==2.5.1` 핀 = PR #24(`6ab693f`)에서 `server/venv`(Python 3.14) 최신 안정값을 그대로 하드핀한 **우연값**(`audio_decode.py` 요구 하한 아님 — 커밋/주석에 버전 근거 없음, "PyPI 최신 안정 2026-06-14 확인" 명시). 라이브+프로즌 numpy 사용처 전수 = numpy 2.0 breaking API 의존 0(전부 1.17 이전 불변 코어 API), `venv_real`(numpy 1.26.4)에서 프로즌 4종 실행 + `audio_decode` RMS 0.353528 비트 일치 실증(학습 15). → **numpy 1.26.4 안전 확정**.
- ~~**[미결 신규] `requirements.txt` numpy==2.5.1 핀 완화**: 위 규명(3.14 우연값) → `numpy>=1.26,<3` 류 완화 합당(TF 2.16 = numpy 1.26 요구, py3.12+에선 2.x). 처리 = 11주차 EC2 배포 시 python/numpy 정식 확정 or 소액 PR. 이번 태스크 미수정(requirements 무수정 원칙).~~ **✅ 해소 (2026-08-02 PoC-(32), PR #30 `50995ba`)**: `numpy==2.5.1` → `numpy>=1.26,<3` 완화 반영. 임시 venv install 검증(해석 버전 회귀 0 + `audio_decode` RMS 0.353539 재현) 통과.
- ~~**[소액 정정 후속] `server/inference/README.md` + `__init__.py` stale 문구**: PR #22(`169a2fc`) 시점 "server/app이 이 패키지를 import하지 않는다" 서술 = PR #28(`a0b87a2`) 이후 거짓(`routes.py`가 `model_serving`/`model_runner` import). 코드가 SSoT라 당장 무해, 소액 문서 PR 후보(H 묶음: 노션 오타 + `constants.py:25` 주석 + DTW 유닛 그룹핑 모드와 함께).~~ **✅ 해소 (2026-08-02 PoC-(32), PR #30 `50995ba`)**: `routes.py`/`model_serving.py` 실 import 근거로 "더 이상 standalone 아님" 현행 정정 완료(README.md + `__init__.py`).
- ~~**🔴 [신규 미결] `/detect` 계약에 ToF 메타 필드 부재 (2026-09-02 감사 G10)**: 요청 스키마(`server/app/routes.py`)는 `client_request_id`/`device_id`/오디오 파일만 수신 — ToF 필드는 **아예 없다**. 그 결과 클래스별 ToF 분기(`server/app/utils.py:92,101`)가 입력 없이 **하드코딩 문자열**을 반환한다(92행 = `"zone_count=9 >= 8 + motion=true"`, low_confidence 분기 / 101행 = `"zone_count=11 >= 8 + motion=true"`, 통상 분기 — 값 자체는 다르지만 둘 다 입력 무관 상수). ★ **2026-09-02 7.4 터널 실측 응답에서도 센서 미연결 상태로 동일 문자열이 재현**됨(실물 증거, 근거유형=실측). 필요 필드 4종 = `tof_presence` / `tof_near_count` / `tof_center_mm` / `tof_motion_ndet`(9.3·9.4 계측/판정 계층 출력과 정합). ⚠️ **11주차 통합 시 wire 계약 확정 필요** — 오디오 wire 계약(본 절 CLOSE 완료분)과 별개로 미확정.~~ **✅ 수신측 CLOSE (실측 2026-09-04 / 문서 반영 2026-09-05, PR #43 `8827946`)**: 4종 필드 wire 수신 + 클래스별 ToF 정책 실입력 구동을 실코드화하고 ④런타임에서 위 하드코딩 문자열 소멸을 확인했다(상세 = 신설 절 **6.4**). ⚠️ **G10 수신측 CLOSE ≠ G10 CLOSE** — 송신측(마이크 M5-d + 통합 펌웨어가 실제로 ToF 메타를 실어 보내는 코드)은 여전히 **0줄**이며, 11주차 통합 체크포인트는 그대로 유효하다.
- **🟡 [신규 미결] 2초 오디오 캡처 윈도우가 1차 5초 예산에 미반영 (2026-09-02 감사 G29)**: 본 절 "★ 1차 5초 체인 전 구간 실측 완성"(합산 p95 ≈1134ms = 23%)은 **이미 캡처된** 64KB(2초) 오디오를 업로드하는 시간만 잰다. 그 2초를 **언제 벌어들이는지**(사후 녹음 vs 사전 링버퍼)가 예산에 미반영이다(근거유형 = **논증**). 사후 녹음(트리거 후 2초 녹음 → 그제서야 업로드 시작) 설계라면 실질 p95 ≈ **3,954ms(예산의 79%)**, 사전 링버퍼(상시 녹음 중이라 트리거 시점에 이미 최근 2초가 확보돼 있음) 설계라면 ≈ **1,954ms(39%)** — **설계 선택 하나가 예산의 40%p를 좌우**한다. → ~~**M5(마이크 최종 결선) 착수 전 결정 필요.**~~ **✅ 2026-09-04 확정 — B안(하이브리드) 채택 (2026-09-03 사용자 결정, 근거유형 = 논증)**: 트리거 시점 기준 pre-roll 일부 + post 일부로 2초 페이로드를 구성한다. 기각 사유 = 전량 pre-roll(A안, ≈1,954ms/39%)이면 트리거 이전 구간이 대부분 무음이라 소리 본체가 빠져 학습 클립 분포와 어긋남(G28 악화) / 전량 사후(C안, ≈3,954ms/79%)이면 어택이 빠지는데 doorbell이 이미 최약 클래스(precision 0.730/recall 0.742, G27)라 입력에서 특징을 깎을 수 없음. B안 예산 ≈3,454ms(69%). 구현 비용 = I2S가 M2~M4 구조상 이미 상시 읽고 있어 링버퍼는 "읽은 것을 안 버리는" 것뿐(PR #41로 이미 확보, 상세 = 6.3(h)). ⚠️ **pre/post 비율은 미확정** — 32슬롯 = 8(0.512s)+24(1.536s)가 버퍼 정수배로 떨어진다는 사실만 기록하며, 비율 확정 판단은 M5-c 소관으로 남긴다.
  - **🔗 [파급] `KAKAO_HTTP_TIMEOUT_SECONDS` 재계산 필요 (역방향 stale 해소, 발견 2026-09-04, 근거유형 = 논증)**: 상수값 1.5초는 **"사전 링버퍼"(A안) 전제로 역산**된 값이었다(5000 − 업로드 1900 − 105 ≈ 3000 ÷ 2회). G29가 B안으로 확정됐으므로 재계산 = 5000 − post 1500 − 업로드 1900 − 105 = 1,495 ÷ 2회 ≈ **750ms**. ⚠️ **본 항목은 문서 등재만 한다** — 상수 코드 값 변경은 별도 PR 소관이며 본 Set에서 미수행.
- ⚠️ **기준선 표기 정정 (발견 2026-09-03 / 문서 반영 2026-09-03)**: 위 앵커 수치 "1134ms=23%"는 **HTTP 기준**(7/28 업로드 실측 1043ms)이고, 본 항목의 산술(3,954ms/1,954ms)은 **HTTPS 기준**(7/29 재실측 1863ms, 본 카테고리 HTTPS 하네스 항목)이다 — 업로드 1043ms→1863ms 전환(+820ms, TLS 핸드셰이크분)이 합계 1134→1954 이동의 원인. 40%p 결론은 어느 기준선이든 불변이라 판단 자체는 유효(수치·결론 변경 없음), 본 정정은 독자가 1134→1954 전환을 복원 가능하게 하는 표기 보강이다.

### 6.3 마이크 M 시리즈 — INMP441 결선 → 계측 → 실측 → int16 변환 확정 (2026-09-02 PoC-(37) 신설)

6.2 wire 계약 갭의 **나머지 절반**(INMP441 I2S 24/32bit → ESP32 int16 변환 검증)을 **M1 결선 → M2 계측 → M3 실측 → M4 판정** 4단계로 완주했다. **결론 = `int16 = raw >> 14` 확정.** ※ 계층 분리는 PR #36(ToF Stage B-1)이 확립한 **"계측 → 실측 → 판정"** 패턴의 **2회차 적용**(원칙 등재 = 카테고리 20).

**(a) M1 결선 (2026-09-02)**

INMP441 M/F 점퍼 **6가닥**. 모듈이 **2열×3핀** 구조라 브레드보드 직접 삽입 불가 → **공중 부양 + 점퍼 직결**.

| 신호 | 브레드보드 위치 | XIAO 핀 |
|---|---|---|
| SCK | J6 | D1 |
| WS | J7 | D2 |
| SD | B10 | D8 |
| L/R | C6 | GND (좌채널 고정) |
| GND | A6 | GND |
| VDD | A35 | 3V3 경유 |

- ★ **VDD가 A35인 이유** = XIAO가 D행을 점유해 **E7이 보드에 덮여 물리적 접근 불가**. ToF 빨강선이 B35(SATEL IOVDD)에 있어 **같은 줄 A35로 3V3 확보**.
- ※ **음향 포트 = 실크면 중앙 구멍**. 핀은 반대면이므로 결선 시 자연히 노출됨.
- ※ 카테고리 2 핀 표(SCK=D1 / WS=D2 / SD=D8 / VDD·GND·L_R=3V3·GND·GND)와 **GPIO 배정 일치** — 본 표는 브레드보드 **물리 위치 추가분**(9.1(d) ToF 결선표와 동일 성격)이며 핀 표 변경 아님.

**(b) M2 계측 PR (#37, `17ce212`) — raw int32 통계 계측 계층**

- `or_acc` 비트 OR 누적 + trailing zeros(`tz`) + min/max/mean/pp/rms + hex 덤프. **변환·판정 0줄**(관측 전용).
- footprint: RAM **+4B**(`.data`, libm 초기화 워드 / **신규 심볼 0** 실측) / Flash **+1140B**.

**(c) M3 ④런타임 실측 (2026-08-20, 랩실) — 근거유형 = 실측**

- 39윈도우(w=233~271). 구간 = 무자극 w=233~248 / 박수 w=249~266 / 육성 w=267~271.
- ★ **`or=0xFFFFFFC0`, `tz=6`이 전 구간 불변** — 진폭 60배 변동에도 무변화. → 하위 6비트 항상 0 = ~~**raw는 24bit를 6칸 좌시프트한 형태**~~ **raw는 6비트 정렬 시프트 구조(tz=6)이며 그 위 유효 폭은 미확정** 확정. ⚠️ **2026-09-04 반증(상세 = 6.3(k))** — "그 위가 24bit"라는 유효 폭 상한 전제는 M5-b 실측으로 깨졌다. tz=6 자체는 재확인 유지.
- `err=0` / 배경 rms **2,104,135~2,646,435** / 박수 max **296,542,208**.
- mean(DC) **-1,210,351 ~ +1,045,075** — **부호까지 변동**.
- ★ **3종 프로토콜 중 ③은 부분 충족** — "초인종/육성" 중 **육성만 실측, 초인종 음원 미실측**. 초인종은 스펙트럼이 달라 **헤드룸 재확인이 M5 과제**.

**(d) M4 판정 PR (#38, `25b0d16`) + ④런타임 통과 (2026-09-02)**

- ★ **shift 확정: `int16 = raw >> 14`**
  - 도출(근거유형 = **호스트 산술 검산**): `tz=6` → raw = 24bit << 6. ~~24bit max `8388607 << 6 >> 14 = 32767 = INT16_MAX` **정확 일치**.~~ ⚠️ **2026-09-04 반증(발견 2026-09-03 / 문서 반영 2026-09-04, 상세 = 6.3(k))** — 이 검산은 "raw 상한 = 24bit << 6 = 536,870,848"을 전제하나, M5-b 실측 raw max가 그 2.95배(1,585,489,920)로 전제 자체가 깨졌다. **shift=14가 틀렸다는 뜻은 아니다** — tz=6은 그대로 유효하며, shift 재판정은 도어벨 실측 후로 보류(6.3(k) 참조).
  - 폐기안: `>>16`(기존 주석 계획) — 약 **12dB 손실**. 치명적이진 않으나 정확도 저하.
- saturation 가드 포함(`INT16_MIN`/`INT16_MAX` clamp + clip 카운트).
- footprint: RAM **순증 0**(union으로 int32/int16 흡수, `.bss` 13280 불변, 신규 심볼 0) / Flash **+392B**.
- ④런타임(근거유형 = **실측**): 27윈도우 `raw/i16` 비 = **16,390~16,786**(기대 16384), **clip=0 전 구간**.
- ★ 편차 +2.5%는 raw rms(double) vs i16 rms(정수 반올림) **양자화 오차** — 작은 값일수록 편차 큼(rms=32 → 16786 / rms=1287 → 16390) = **예상 거동**.
- ⚠️ **clip=0은 int16 풀스케일의 9% 조건에서의 실증**이다. 9/02 박수 i16 max=**2,928**로 8/20 박수(환산 18,099 = 55%)보다 **7.4배 약했다** → **헤드룸 상한 검증 아님**. saturation 로직 자체는 PR #38 **호스트 검산 7건**으로 증명 — 이는 **논증**이며 위 ④런타임 실측과 **같은 층위 아님**.

**(e) 미해결 잔여 (defer — 판정 방법 병기)**

- **DC 오프셋**: 부호까지 변동하는 저주파 드리프트 → **단순 뺄셈 불가**. 판정 방법 = M5에서 **조용한 환경 장시간 로그**로 주기·진폭 측정 후 HPF 필요성 판정.
- **RMS 트리거 임계값**: 카테고리 3 "80% 지점" **미확정**. ⚠️ **배경 rms 2.4M은 랩실 사람 대화가 포함된 값 = 무음 기준선 아님** — 이 값으로 임계값을 정하면 안 된다. 판정 방법 = 조용한 환경 재측정 → 초인종/노크 실측 → 분리점 산출.
  - **🟡 [신규] 입력 레벨 정합 미검증 (2026-09-02 감사 G28)**: 서빙측 정규화(`server/inference/audio_decode.py`)는 `÷32768` 고정(풀스케일 가정)인데, 마이크 실측 레벨은 2회 측정에서 크게 변동했다 — 8/20 박수(6.3(c)) 대비 9/02 박수(6.3(d))가 풀스케일 기준 약 55%→9%로 낮아짐(근거유형 = 논증, 두 세션 raw 값 비교). 이 변동폭이 YAMNet 학습 데이터의 RMS 분포와 **대조된 적이 없다** — 실기기 입력 레벨이 학습 데이터 가정과 어긋나면 추론 정확도에 영향을 줄 수 있다. 9.3(H) 하위 원칙 사례 ②(동일 위치 대조 미수행)와 원인이 겹치므로, M5에서 동일 프로토콜로 재측정할 때 함께 판정.
- **초인종 음원 헤드룸**: (c) ③ 부분 충족분. M5 소관.

**(f) 측정 로그 원본**: repo 밖 `~/ddingdong-측정결과/mic_m3_2026-08-20/` 및 `~/ddingdong-측정결과/mic_m4_2026-09-02/` (`.gitignore` 차단분, SSoT엔 요약만).

**(g) ★ "체감 상태 ≠ 실제 상태" 재실증**: 9/02 측정에서 학부생 **체감** 박수 시점(w=21~22)과 **로그 실제**(w=18~20)가 **3~4윈도우(약 10~13초) 어긋났다**. 2026-08-12 9.3(e)/(H)에서 확립한 원칙의 재실증 사례 — 실측 판정은 체감이 아니라 로그가 기준.

**(h) M5-a PR #41(`b4b880a`, 내부 커밋 `b3e9c9d`) — 2초 PSRAM 링버퍼 계측 계층 (2026-09-03)**

- 신설: `MIC_RING_SLOTS=32`(2.048s = 32,768샘플 = 65,536B int16) / `MicRingStatus` / `initMicRingBuffer` / `micRingSlot`(inline) / `micRingAdvance`. 채택 근거 = 2.000초는 31.25버퍼라 정수배가 아니므로 부분 버퍼 처리 로직을 피하려 32(2.048초) 채택. 서버 수용 확인 = 서빙 시그니처 `waveform(1,None)` 가변 길이 + `AUDIO_MAX_BYTES` 320,000 대비 20.5%.
- ★ **위임 원안 API 기각**: bool 반환 + 내부 전역 보관안이 본 파일 3곳에 명문화된 "static/전역 신설 금지 = RAM 순증 0" 컨벤션과 충돌(전역 포인터 1개 = `.bss` +4B) → `int16_t*` 반환 + `micRingSlot(base, idx)` 순수 함수로 변경(카테고리 29 "위임과 실제 컨벤션 충돌 시 기존 컨벤션 우선" 적용, 근거유형 = 논증).
- footprint(근거유형 = 실측): RAM 순증 0(4회 연속) / Flash +804B(오브젝트 868B와 링크 804B 차 -64B는 Xtensa 링커 relaxation + `.str1.1` 문자열 병합).
- ④런타임(2026-09-03, 랩실 사람 없음, 근거유형 = 실측): ring=on / PSRAM 8,386,231 → 8,320,559(Δ 65,672 = 링버퍼 65,536 + 헤더 136) / gaps=0(전 42윈도우) / wrap-around 전수 정합(w=5 idx=9 wraps=6 → w=42 idx=3 wraps=64, 검산 9+1850=1859=58×32+3, 6+58=64 일치).
- ★ **negative control 미검출 사례(방법론 자산)**: 위임 지정 변형(MOD 32→31)을 최초 negative control이 검출하지 못했다 — 모듈러를 줄이면 버퍼를 덜 쓸 뿐 경계를 넘지 않기 때문. 커버리지 불변식을 양방향(31 부족/33 초과)으로 보강해 재검출하도록 수정(근거유형 = 논증 + 재현 실측).

**(i) M5-a2 PR #42(`d024e23`, 내부 커밋 `462c029`) — 윈도우 진폭 누적 관측 계층 (2026-09-03)**

- 배경(근거유형 = 실측): (h) ④런타임에서 **의도적으로 친 박수가 전혀 검출되지 않았다**. 로그 게이트가 50버퍼당 1버퍼 = 시간의 2%만 관측 — 약 100ms인 박수가 이 창에 들어갈 확률이 2%. → **8/20 M3(6.3(c))의 박수 검출이 오히려 우연이었다**는 재해석.
- 신설: micTask 지역 누적 4종(`win_peak`/`win_rms_max`/`win_rms_min`/`win_clip`) + `win_nbuf` → `[mic][M5a2]` 별도 로그 줄. 판정 로직 0줄.
- footprint(근거유형 = 실측): RAM 순증 0(5회 연속) / Flash +268B.
- ★ **센티넬 없는 설계**: `win_nbuf == 0 || rms < win_rms_min` 가드만 사용 — 센티넬 상수가 없어 "누출 경로를 막을" 필요 자체가 소멸(방어 코드 대신 문제의 부재, 근거유형 = 논증).
- ★ **위임 자기모순 발견 + 해소**: "PSRAM 실패 시에도 진폭 관측 유효"(원 지시)와 "M2 로그 포맷 불변"(원 지시)이 union 구조상 양립 불가(폴백 dst = `audio_buffer.i16` = raw[0..511]과 동일 메모리) — 후자를 우선하고 폴백 윈도우는 n/a 분기 처리(카테고리 27/29 패턴 재적용).
- ★ **negative control 2회차 부족 사례(방법론 자산)**: 위임 지정 "센티넬 오초기화" 변형은 위반 0건이었다 — `win_nbuf==0` 가드가 있으면 첫 표본이 무조건 덮으므로 그 변형은 **무해**했다. 센티넬이 실제로 새는 유일 경로는 "표본 0건 윈도우"였고, 신규 negative control(NC-2)을 추가해 오변형에서 `2,147,483,647` 출력을 검출. 지정 문구대로만 돌렸으면 근거 없이 "안전"으로 오판할 뻔했다(근거유형 = 논증 + 재현 실측).
- B4 오프바이원 실증(근거유형 = 실측): 게이트가 `buf_count` 1, 51, 101…에서 열려 첫 윈도우만 1버퍼, 이후 정확히 50버퍼 — 이 위상이 (h) 실측(w=5 → buf_count 201 = 6×32+9)과 교차검증됨.

**(j) M5-b ④런타임 실측 — 무음 기준선 + 분리 마진 + 시리얼 절단 정량화 (2026-09-03, 랩실 사람 없음, 근거유형 = 실측)**

- 로그 원본: `~/ddingdong-측정결과/mic_m5b_2026-09-03/monitor.txt`(446줄, `.gitignore` 차단분 — SSoT엔 요약만).
- 프로토콜: ①무자극 w=7~63(57윈도우) ②박수 w=64~76 ③노크 w=77~86. 구간 경계는 자기보고 기준(±1윈도우). w=5,6은 측정 개시 직후 접촉음 추정으로 판정 제외.

| 구간 | rms_min | rms_max | peak | clip |
|---|---|---|---|---|
| ①무자극 | 63~79 | 97~171 | 359~724 | 0 전 구간 |
| ②박수 | 65~72 | 3,740~21,626 | 5,869~32,768 | 0~311 |
| ③노크 | 63~71 | 988~4,009 | 8,584~13,885 | 0~2 |

- ★ **무음 기준선 = rms_min 최솟값 63**(w=40, 안정 구간 63~79) — 6.3(e)의 "배경 rms 2.4M은 랩실 대화 포함이라 무음 기준선 아님" 갭을 메운다. ⚠️ 단 "조용한 랩실"이지 완전 무음은 아니다(에어컨·공조음 상시 포함) — 이 두 사실은 항상 같은 문장으로 인용할 것.
- 분리 마진: rms_max 171 vs 노크 988 = **5.8배** / peak 724 vs 8,584 = **11.9배**.
- ★ peak 마진이 rms의 약 2배이나, 본 값은 **3.2초 윈도우 집계**이고 실제 트리거는 64ms 버퍼 단위이므로 그대로 적용 불가 — **카테고리 3 SSoT("단순 RMS 임계값") 변경 판단은 M5-c로 보류**(근거유형 = 논증, 본 Set에서 SSoT 미변경).
- ★ 박수 구간 w=67(peak 428)/w=73(peak 1299)이 무자극 수준 — 3.2초 윈도우 사이에 이벤트가 미포함됐다는 실증. **윈도우 단위로는 이벤트 타이밍을 잡을 수 없다** = 트리거 판정은 버퍼 단위여야 한다는 근거.
- 시리얼 절단 정량화: (h) M5-a 로그 기준 **31줄/147줄 = 21.1%** 손상. 손상 형태는 줄 끝 절단이 아니라 줄 중간 10~15B 덩어리 소실. 태그별: M2(141B) 57.9% / raw dump(108B) 12.5% / M4(81B) 16.7% / M5a(80B) 0% / MEM(78B) 0% — **≤80B 62줄에서 손상 0건**, 손상률이 줄 길이에 단조 증가.
- ★ baud 대역폭 가설 약화(근거유형 = 실측 + 논증): ① 보드 정의에 `-DARDUINO_USB_MODE=1`+`-DARDUINO_USB_CDC_ON_BOOT=1` → Serial이 UART가 아니라 **USB CDC**. 115200은 호스트 포트 명목값일 뿐 장치측 전송률과 무관(실측 = 빌드 설정 원문) ② 평균 듀티 = 윈도우당 323B ÷ 3.2s = 101B/s ÷ 11,520B/s = **0.9%**(논증) ③ UART라면 FIFO 포화 시 블로킹이지 드롭이 아니다 — 관측된 것은 중간 덩어리 소실(논증, 미실측). → `monitor_speed` 상향은 효과 없을 공산이나 **어느 쪽도 확정 아님**, 확정하려면 ④런타임 A/B 필요.

**(k) ★★ M4 판정 근거 2건 반증 (발견 2026-09-03 / 문서 반영 2026-09-04, 근거유형 = 실측 반전 5회차)**

- **(k-1) "24bit 유효 폭" 전제 반증**: (d)의 검산은 raw 상한 = 24bit << 6 = 536,870,848을 전제한다. M5-b 실측 raw max = **1,585,489,920**(w=69) = 전제값의 **2.95배**. 역산 시 `1,585,489,920 >> 6 = 24,773,280`으로 24bit signed 최대(8,388,607)를 약 3배 초과한다. → **tz=6(정렬 폭)은 전 구간 불변으로 재확인**됐다(재현 실측). 반증된 것은 "그 위가 24bit"라는 유효 폭 부분뿐이다. (c)/(d)의 해당 서술은 위에서 취소선 처리했다.
- **(k-2) mic_common.h 내부 "헤드룸 약 1.8배" 서술과의 정합 확인**: `firmware/include/mic_common.h`(88~90행) 주석은 "박수 max 296542208 >> 14 = 18099 = 풀스케일 55% → 클리핑 없음, 헤드룸 약 1.8배"라 적고 있으나, **본 decisions.md에는 이 "헤드룸 확정" 프레이밍이 애초에 등재된 적이 없다**(grep 확인 — (d)는 이미 "헤드룸 상한 검증 아님"으로 유보돼 있었다) → 취소선 대상 문구 부재이므로 **순수 신설로 처리**(학습 17 catch, 2026-09-03 [B]/[C] 선례 준용). 오늘 박수 raw max는 296,542,208의 **5.35배**이고 clip=311(w=64)/163(w=69)/124(w=72) 등이 실측돼, mic_common.h 주석의 "헤드룸 1.8배·클리핑 없음" 서술은 이제 근거를 잃었다. ⚠️ **mic_common.h 주석 정정은 본 Set 범위 밖(별도 코드 PR 소관, firmware/ 0줄 수정 원칙)** — 본 문서는 그 서술이 실측과 어긋난다는 사실만 기록한다.
- ⚠️ **shift=14가 틀렸다는 뜻이 아니다.** shift 상향(`>>15`/`>>16`)은 클리핑을 줄이지만 저음압 해상도를 버린다 — 노크는 clip=0~2로 거의 무영향이었고 박수만 크게 걸렸다. **초인종 실측 음압이 없는 상태에서 shift를 바꾸면 그 자체가 "측정 전 확정"**이다(카테고리 29 원칙 적용) → shift 판정은 도어벨 4유닛 수령 후 동일 위치 재측정까지 보류.
- ★ **실측 반전 5회차**: ① ToF near 8→20 폐기(내부 추정) ② 마이크 `>>16`→`>>14`(내부 추정) ③ ToF aggmax≥50→ndet≥1(내부 추정) ④ 카카오 200자 상한(외부 공식 문서) ⑤ 본 건. ①②③은 **우리 내부 추정**이 실측에 뒤집힌 사례, ④는 **외부 공식 문서**가 우리 가정을 뒤집은 사례, **⑤는 우리가 실측으로 세운 근거표 자체가 후속 실측에 뒤집힌 첫 사례**라는 점에서 성격이 다르다.

### 6.4 `/detect` ToF 메타 wire 확장 — G10 수신측 CLOSE (2026-09-04 PoC-(41) 신설, PR #43 `8827946`)

6.2 G10 미결("`/detect` 계약에 ToF 메타 필드 부재")의 **수신측 절반**을 실코드화했다. ⚠️ **G10 수신측 CLOSE ≠ G10 CLOSE** — 송신측(마이크 M5-d + 통합 펌웨어가 실제로 ToF 메타를 실어 보내는 코드)은 **0줄**이며, 본 절이 닫은 것은 "서버가 받을 준비를 마쳤다"까지다.

**(a) 산출물 (근거유형 = 실측, `git show 8827946 --stat` 대조)**
- 신설 `server/app/tof_meta.py` = 순수 함수 4개(`absent_meta` / `parse_tof_meta` / `telemetry_summary` / `evaluate_gate`).
- `constants.py` = wire 필드명 4(`TOF_PRESENCE_FIELD` / `TOF_NEAR_COUNT_FIELD` / `TOF_CENTER_MM_FIELD` / `TOF_MOTION_NDET_FIELD`) + 구조 상수 2(`TOF_ZONE_TOTAL=64` / `TOF_MOTION_AGGREGATE_TOTAL=16`).
- 수신 필드 4종 = 6.2 G10이 지정한 `tof_presence` / `tof_near_count` / `tof_center_mm` / `tof_motion_ndet` **그대로**(신규 필드 발명 0, 학습 16).

**(b) ★ 핵심 설계 — 서버는 `tof_presence`를 재판정하지 않는다 (근거유형 = 논증)**
- Stage A 디바운스 3프레임(9.2)과 Stage B-2 latch 75프레임(9.4)은 **시간축 판정**이라 단발 POST 스냅샷 하나로 재구성할 수 없다. 그래서 presence는 펌웨어가 판정한 결과를 **그대로 신뢰**하고, 나머지 3필드는 증거·표시용 telemetry로만 쓴다.
- 필드 표기 어휘(`near=n/64` / `center=NNNNmm` / `ndet=n/16`)를 9.3(b) 로그 필드 정의와 맞췄다 → 통합 후 **서버 기록 ↔ 펌웨어 시리얼 로그 대조 가능**.

**(c) 부재·범위이탈 처리 (근거유형 = 논증)**
- ToF 필드 부재 = **fail-open**(A-1 1차 발송 경로 무회귀). 단 "게이트 통과"와 "ToF 부재로 미적용"이 **응답·DB·로그에서 구분 가능해야 한다**는 불변식을 세웠다.
- 범위 이탈 = 400 거절도 아니고 부재와도 다른 **제3상태 "invalid"**로 기록.
- ★ **`tof_center_mm` 상한 미설정**: 9.2(c) 최대 관측치 2953mm는 "그날 그 자리의 값"이지 센서 구조 상한이 아니다. 상한으로 박으면 **실측 없는 판정을 코드에 고정**하는 셈이라(9.4(c) `aggmax` 기각 논리와 동형) 음수만 거르고 상한은 두지 않되 사유 코드를 각인했다.

**(d) 회귀 + 전 분기 열거 (근거유형 = 실측)**
- 회귀 케이스 기존 30 → **42**(신규 12).
- 전 분기 **648건** 열거(ToF 4상태 × telemetry 3필드 각 3상태 = 108 × 클래스 3 × 신뢰도 2), 미정의 동작 **0**.
- ★★ **648건이 고유 24행 결정표로 완전 붕괴** — 결과가 (클래스, 신뢰도, ToF state, presence) **4-튜플만으로** 결정되고 telemetry 3필드는 결과에 영향 **0**. 이것이 (b) "서버가 재판정하지 않음"의 **코드 증명**이다.
- negative control 5건 전건 검출. ★ 위임이 예고한 NC-3 함정("ToF 부재를 presence=true로 취급")이 **실재**했다 — `primary_sent`만 보는 케이스는 전건 무해했고, `applied`/`passed`/`reason`을 **함께 고정한** 전용 케이스 1건만 실패했다(카테고리 20 「negative control 함정 예고」 연동).

**(e) ④런타임 실측 (실호출 + 카카오톡 화면 대조, 실측 2026-09-04 / 문서 반영 2026-09-05, 근거유형 = 실측)**
- **하드코딩 문자열 소멸 확인** — 6.2 G10이 실물 증거로 인용한 `zone_count=9 >= 8 + motion=true` / `zone_count=11 …`이 실호출 응답에서 **사라졌다**(9/02 터널 실측·9/03 A-1에서 두 번 재현됐던 바로 그 값).
- ToF 부재 → `{"applied":false,"passed":null,"reason":"tof_absent"}` + `primary_sent=true`(A-1 경로 무회귀).
- doorbell·knock + `presence=false` → `primary_sent=false` + `notification_status.skip_reason="tof_rejected"` + `primary_sent_at=null` + **카카오톡 미도착**(차단이 화면으로 증명됨).
- fire_alarm → 우회 + `reason="fire_alarm_bypass (presence=false near=1/64 center=2953mm ndet=0/16)"`, 카카오톡 도착(카테고리 3 클래스별 ToF 정책 정합).
- 결정표 24행 중 **실경로 확인 9행**(나머지는 회귀 테스트 커버).

**(f) 🟡 [신규 미결] 가짜 ToF 하드코딩 잔존 (발견 2026-09-04 / 문서 반영 2026-09-05, 근거유형 = 실측 grep)**: `/detect` 경로에서는 소멸했으나 `server/seed.py`(시드 5건 중 **4건**) + `dashboard/src/lib/mock-data.ts`(5건 중 **4건**)에 `zone_count=… >= 8 + motion=true` 문자열이 **그대로 남아 있다**(나머지 1건씩은 `fire_alarm_bypass`). PR #43 범위 밖이었으나, **부스 데모에서 seed 데이터가 화면에 뜨면 가짜 ToF 문자열이 관람객에게 보인다**(카테고리 26 연동). 해소 = 데모 시나리오 소관.

**관련**: 6.2(G10 원 미결 / wire 계약) / 카테고리 3(클래스별 ToF 정책 · 신뢰도 임계값 · G12) / 9.2·9.3·9.4(Stage A / B-1 / B-2) / 7.6(A-2 2차 알림) / 카테고리 20(계측 → 실측 → 판정)

---

## 카테고리 7: STT + 알림

- **STT**: Naver Clova Speech (CSR) — 인터폰 노이즈 CER 6.49%
  - **note (발견, 결정 아님, 2026-08-02)**: 콘솔 화면 catch + 공식 안내 확인 — 네이버가 CSR 기능을 CLOVA Speech로 통합 제공 안내. CSR 문서(User Guide 14 / FAQ 6)는 잔존하나 신규 이용이 CLOVA Speech로 유도되는지 불명. ∴ STT 제품 선택(CSR 유지 가능 여부 vs CLOVA Speech 전환) 재검토 필요 — 11주차 서버 연동 전 확정. A-1 STT 왕복 실측은 제품 결정 후 defer.
  - **✅ 결정: STT 제품 = CSR 유지 확정 (2026-08-03 PoC-(33))**: 위 2026-08-02 통합 발견 note의 재검토 결론. 근거 3 — ① NCP 콘솔 `AI·Application Service > AI·NAVER API > Application` 등록 화면에서 **CSR 신규 선택 가능 확인**(학부생 화면 catch, 2026-08-03 — 학습 13 화면 우선, 문서 결론보다 우선) ② CSR 스펙(최소 16kHz 이상 · 최대 60초 · REST 파일 업로드)이 우리 용도(5초/16kHz mono)와 정합 ③ 네이버 통합 배너는 종료 공지 아님(CSR 잔존). 폴백 = **CLOVA Speech 단문인식**(REST 60초, CSR과 동일 파일 업로드 패턴) — gRPC 스트리밍은 이질적 프로토콜이라 후순위. ~~⚠️ **A-1 STT 왕복 실측 = 미실측(defer, 학습 19)** — 제품 결정으로 언블록됐으나 실측 자체는 미수행. 선행 = CSR Application 생성 + Client ID/Secret 발급(학부생 몫, 30.9 참조).~~ **✅ 왕복 ④런타임 실증 완료 (실측 2026-09-05 / 문서 반영 2026-09-05, 근거유형 = 실측)**: 실 CSR 호출 왕복 **0.892초**(15초 예산의 5.9%) + 한국어 인식 성공. 15초 단위 과금도 콘솔 화면 숫자로 확증(상세 = 30.9). ⚠️ **왕복 실증 ≠ STT 서버 배선** — `server/`의 STT 호출 코드는 여전히 **0줄**이고 7.6 A-2 자막은 mock 문구(`_MOCK_TRANSCRIPTS`)다. 이 두 사실은 분리해 읽어야 한다. ⚠️ **요금 불일치 발견**: CSR 실요금 ≈ **15초당 4원**(2026 KR 요금표) ↔ 기존 SSoT(30.9) "초당 0.5원/분당 30원" 불일치 → 30.9에서 취소선+현행값 정정.
- **카카오톡**: '나에게 보내기' (memo) — 비즈 앱 심사 회피
- **이미지**: ~~카카오 이미지 업로드 API (S3 불필요)~~ **memo엔 이미지 업로드 API 부재 — image_url=서버 자체 public 호스팅 필수 (2026-07-31 PoC-(30) E 실사)**: 카카오톡 메시지 API(나에게 보내기)엔 이미지 파일 업로드 엔드포인트 부재. memo 3종(default/custom/scrap) 전부 이미지를 `content.image_url`(사전 호스팅된 public URL 문자열)로만 수신 — 이미지 바이트 미통과. mud-kage CDN을 뱉는 카카오 이미지 업로드 API는 **비즈메시지/친구톡** 계열(비즈채널+심사 필요)이라 memo 경로(비즈앱 심사 회피 목적, 본 카테고리)와 배치. ∴ 진실 = 서버(11주차 EC2)가 ESP32 캡처 이미지를 스스로 public URL로 호스팅(EC2 static route 등, "S3 제품"은 회피 가능하나 public 호스팅 자체는 필수) 후 그 URL을 `image_url`에 실어 `memo/default/send` 호출. 이미지 feed 스코프 = `talk_message` 단일(텍스트와 동일, 추가 동의 불필요). ⚠️ 11주차 2차 체인 아키텍처(이미지 호스팅 방식 = EC2 static route vs 오브젝트 스토리지) 확정 필요.
  - **✅ A-2 스켈레톤 완료 (2026-08-02 PoC-(32), PR #29 `c30e728`)**: 위 정정 후속으로 서버측 public 호스팅 **스켈레톤 실코드화**. 핵심 결정 = opaque capability URL(`secrets.token_urlsafe` 랜덤 키, `notification_id` 미유래 — 추측 불가) + 비인증 서빙 라우트(`GET /captures/<opaque_id>`, 카카오 lazy fetch가 비인증이라 인증 붙이면 깨짐 → 유일 게이트 = opaque 키 + 경로 화이트리스트로 traversal 차단) + TTL 72h(lazy fetch 특성상 짧게 못 잡음, cleanup 헬퍼는 미스케줄) + 로컬 파일시스템 단일 concrete 구현(`image_store.py`, 11주차 EC2 static route 또는 오브젝트 스토리지로 이 모듈만 교체 지점). 로컬 라운드트립 실증(enrich 저장 → image_url 발급 → GET 200 + 바이트 일치, curl 회귀 25종 0 fail). ★ 실 public 호스팅 제품(EC2 static vs 오브젝트 스토리지) 확정은 여전히 11주차 미결 — 스켈레톤 완료지 호스팅 방식 확정 아님.
- **토큰**: 액세스 6시간 + 리프레시 60일, SQLite 저장
  - **★ 재발급 (2026-09-02)**: 본 카테고리 7.2/7.3 실측일(2026-07-29·07-31)로부터 리프레시 토큰 만료를 추정하면 **2026-09-27~29**로, **발표 구간(9/21~9/30)과 겹치는 리스크**가 있었다(⚠️ 근거유형 = **논증** — 최초 발급일 기록이 코드·문서 어디에도 없어 7.2/7.3 실측일로부터의 **추정**이었음). 카카오 디벨로퍼스 REST API 테스트 도구에서 재발급(인증 앱 = Ddingdong(1456718) / 스코프 = **talk_message 단독** 확인) → 60일 리셋으로 발표 구간 리스크 소멸. 토큰 실값은 env 경유만, 본 문서 미기록. **재발경로 차단**: 본 재발급일(2026-09-02)을 SSoT로 남겨 다음 만료 추정이 다시 추정이 되지 않게 한다 — 다음 만료 예상 ≈ **2026-11-01 전후**(60일). ⚠️ **정정 (발견 2026-09-03 / 문서 반영 2026-09-03)**: 위 '재발급'은 REST API 테스트 도구가 수행한 **access 토큰 재발급**이었다 — 이 도구는 access 토큰만 발급하며, refresh 토큰 재발급은 인가 코드 흐름(OAuth)으로만 가능하다는 사실이 이후 확인됐다(상세 = 카테고리 7.5(e)). '60일 리셋'·'다음 만료 예상' 서술은 이 사실이 밝혀지기 전의 **추정**이었던 것으로 재해석한다. 2026-09-03 OAuth 인가 코드 흐름으로 refresh를 정식 재발급해 실측 완료 — `refresh_token_expires_in=5,183,999초(60일)`, 다음 만료 ≈ **2026-11-02**(이번엔 추정이 아니라 실측).
- **토큰 상태 API (2026-05-28 확정)**: 대시보드 응답은 절대 만료시각 대신 **상대값** `kakao_token_expires_in_minutes` + `status` enum(`valid`/`expiring`/`expired`) 노출 — 클라이언트 시계 오차 무관 + 대시보드 "토큰 만료 임박" 경고 UI 직결 (코드: `dashboard/src/types/stats.ts` `SystemHealth`)
- **2차 알림**: best-effort + 1회 재시도 — **재시도 단위 확정 (2026-09-05, PR #44 `a431961`)**: 재시도는 "**실패한 건만 개별 1회**"이며, 2건(사진 feed / 자막 text)을 통째로 재시도하지 않는다(성공한 사진의 중복 발송 방지). 상세 = 7.6(c).
- **화재경보 알림 형식** (2026-05-09 추가, 카테고리 26 시연 시나리오 연동): 강조 표현 + 정부 지정 대응 수칙 동시 발송. 1차 알림만 (2차 사진 + 자막 미발송). ToF 사람 검증 우회 (카테고리 3과 동일 정책)

### 7.1 화재경보 청각장애인 대응 수칙 확정 (2026-06-30 PoC-(20))

위 "화재경보 알림 형식"의 **정부 지정 대응 수칙 본문을 확정**. 1차 출처 조사 → 페르소나 누수 3건 정정 → 베테랑 검증 통과(2026-06-30). 본 수칙 = **도움말 카드(B 단계 교체)** + **카카오 알림 본문(11~14주차)** 공용 SSoT.

> **도움말 화면 반영 완료** (PR #9 `ca61e1b`) — 구 카피 → 아래 **확정 카피 ① 4단계 verbatim** 교체(카테고리 8.3 B-3·B-4 참조). 카카오 알림 본문(확정 카피 ②, 11~14주차)은 **미반영 유지**.

**핵심 전환 결정 (결함 3건 교정)**:
- ① "119 즉시 신고" → **"즉시 대피, 안전 확보 후 신고"** (음성통화 전제 제거 — 청각장애인은 음성 신고 불가).
- ② **대피-신고 순서 역전 교정** (공식 = "불 끄기·신고보다 대피가 우선").
- ③ **출처 라벨 부재** → 카피에 출처 명기.

**페르소나 누수 3건 정정 (소리 전제 제거)**:
- catch 1 — "불이야! 외치기"(S1 1단계, 음성 전제) = 카피에서 **의도적 제외**(복원 금지). 비상벨은 시각표시 화재경보기로 대체 반영.
- catch 2 — 신고수단을 **확정 수단 우선**으로 배치: ①119 영상통화(수어) ②119 문자 = 메인 / 「긴급신고 바로앱」 = 이름만 보조 병기(앱 내부 기능 추정 서술 금지).
- catch 3 — "구조 요청"(음성 전제) → **시각·문자 수단**으로 구체화(위치 전송 + 손전등·밝은 천).

**확정 카피 ① 대시보드 도움말용** (검증 완료, 임의 윤문 금지):
```
🔥 화재경보가 울리면
1. 바로 대피하세요. 끄기·신고보다 대피가 먼저입니다.
2. 엘리베이터 대신 비상계단으로, 젖은 천으로 입·코를 가리고 낮은 자세로 이동하세요.
3. 안전한 곳에 도착한 뒤 119에 신고하세요.
   → 119 영상통화(수어)나 문자로 신고하세요. 음성통화 없이 가능합니다.
     「긴급신고 바로앱」도 사용할 수 있습니다.
4. 대피가 어려우면 화장실·베란다 창문 쪽으로 이동해,
   휴대폰으로 119에 위치를 알리고(영상·문자), 창밖으로 손전등·밝은 천을 흔들며 구조를 기다리세요.
ⓘ 출처: 소방청 「119 안전교육」(청각장애인용) · 119 영상통화 신고(손말이음센터 107)
```

**확정 카피 ② 카카오 알림용** (검증 완료, 임의 윤문 금지):
```
🚨[띵동] 화재경보 감지 🚨
지금 화재경보가 울리고 있습니다.
① 즉시 대피 (끄기·신고보다 대피 먼저)
② 엘리베이터 ✕, 비상계단 ◯ / 젖은 천으로 코·입 가리고 낮은 자세로
③ 안전한 곳 도착 후 119 신고
   ▸ 119 영상통화(수어)·문자로 신고 (음성통화 없이 OK) · 「긴급신고 바로앱」 가능
④ 못 나가면 화장실·베란다 창문 쪽으로
   ▸ 휴대폰으로 119에 위치 전송(영상·문자) + 창밖으로 손전등·밝은 천 흔들기
— 소방청 청각장애인 화재 행동요령
```

**출처 등급**:
- S1 소방청 「119 안전교육」(청각장애인용) 교재 — **1차 최우선** (페르소나 직격, 행동요령 전수 근거).
- S4 손말이음센터(107) — 119 영상통화(수어) 현행성 근거 (1차).
- S2·S3 긴급신고 바로앱(행안부) — 앱 **존속 확인**, 단 최신 업데이트 **2024-01-20** → 메인 아닌 **보조 병기** 근거 (영상통화·문자가 메인이라 현행성 리스크 흡수).
- S5 korea.kr "청각·언어장애인 119 직접 신고" 2025.4.17 개통 — 보조.

**잔존 유보 1건**: "손전등·밝은 천 흔들기" = 1차 출처(S1~S6) 직접 근거 없는 **일반 시각 구조신호** → 발표 전 시·도 소방본부 청각장애인 자료에서 직접 근거 추가 확인 권고. 과한 구체화 금지.

### 7.2 카카오 memo(나에게 보내기) 왕복 지연 실측 (2026-07-29 신설)

> 1차 5초 예산의 **마지막 미측정 구간**이던 카카오 발송 왕복을 실측. 하네스 = repo 밖 커스텀 스크립트(N=10 실발송 + 메시지 미발송 소켓 프로브로 연결분해 — 카톡 도배 없이 DNS/TCP/TLS 수치 확보), 컨벤션 = 7/28 upload_spike(p50/p95 + TCP 분해) 재사용.

- **실측 (memo default/send 왕복)**: **p95 84.1ms / p50 69.2 / min 51.4 / max 93.0 / avg 67.8**, 성공 **10/10**(전 요청 http 200 + result_code 0). 웜(keep-alive 재사용, iter2~10) p50 67.8/p95 72.8ms, 콜드(iter1, 신규 연결 포함) 93.0ms → **keep-alive 절감 25.2ms**. 연결분해(콜드 avg) dns 38.4 / tcp 7.1 / tls 20.8 = conn 66.3ms.
- **조건**: 학부생 로컬 M4 → 카카오 kapi.kakao.com(서울), 텍스트 memo, N=10, 간격 2s(도배/rate limit 회피 상한). **하한 성격** — 단, EC2 서울 리전은 지리적으로 유사 조건이라 대표성 있음. 2차 이미지 memo(이미지 업로드 API 경유)는 별개·미측정.
- **★ 함의: 1차 5초 예산에서 카카오는 병목 아님** (p95 84.1ms = 예산의 1.7%). 전 구간 합산 판정은 카테고리 6.2 참조.
- 측정 로그 원본 = repo 밖 `ddingdong-측정결과/kakao_memo_2026-07-29.txt` (SSoT엔 요약만, 원본 미커밋). PR 없음(문서 단독, 측정 스크립트도 repo 밖). 토큰은 env `KAKAO_ACCESS_TOKEN` 경유만 — 코드·로그·문서 어디에도 값 미기록.

### 7.3 카카오 2차 이미지 memo 왕복 실측 (2026-07-31 PoC-(30) 신설)

> 1차 텍스트 memo(7.2)에 이어, 2차 15초 체인의 마지막 미측정 카카오 구간(이미지 memo)을 실측. 하네스 = 7.2 컨벤션 재사용(repo 밖 커스텀 스크립트, N=10, p50/p95 + 연결분해) + `content.image_url` 크기 스윕 추가.

- **실측 (feed/default/send 왕복, image_url 크기 3스윕)**: 실측 40.5/97.3/200.4KB × N=10, 성공 **30/30**. **p95 = 487.9 / 461.3 / 485.3ms**(크기순). **크기 민감도 = 없음**(p95 스프레드 26.6ms) → 카카오가 발송 시점에 `image_url`을 동기 fetch하지 않음(URL 문자열만 전송, lazy 로딩 추정) — 이미지 크기가 카카오 왕복을 늘리지 않음.
- **★ 정직 표기**: 절대값(수백 ms, 텍스트 memo 84.1ms 대비 5~6배)은 feed `object_type` 서버 처리 비용 + **로컬 WiFi/핫스팟 노이즈**(60KB 변형 tcp 1008ms 스파이크, 7/29 텍스트 측정의 핫스팟 튐과 동류)가 섞인 하한/근사 — "정밀 수치"가 아닌 "**크기 민감 없음 + 15초 예산 여유(p95 490ms ≈ 예산 3.3%)**"로 위상 구분. 조건 = 학부생 로컬 M4 → kapi.kakao.com(서울).
- **함의**: 2차 15초 체인에서 **카카오는 병목 아님**. 실 리스크 3곳으로 좁혀짐 — ① 이미지 public 호스팅(11주차 아키텍처, 카테고리 7 정정 연동) ② Naver Clova STT 왕복(미측정) ③ ESP32 2차 페이로드 업로드(이미지+5초 오디오, 1차보다 큼, 미측정).
- 측정 로그 원본 = repo 밖 `~/ddingdong-측정결과/kakao_image_memo_2026-07-31.txt`. 하네스도 repo 밖(7.2 정책 동일). PR 없음(문서 단독). 토큰은 env 경유만, 미기록.

### 7.4 Cloudflare Tunnel 이미지 호스팅 실측 — EC2 없이 2차 체인 관통 (2026-09-02 신설)

카테고리 7 "이미지" 항목의 미결("11주차 2차 체인 아키텍처... 확정 필요")과 연동. 2026-09-02 전체 시스템 감사가 "부스 = 모바일 핫스팟 NAT 뒤(카테고리 23) → 카카오가 로컬 URL을 fetch할 수 없다 → EC2가 필수 선행"이라는 결론을 냈으나, 감사 스스로 찾아낸 대안(②Cloudflare Tunnel)을 "실측 근거 없는 논증"으로 강등한 채 마무리했다. 본 절은 그 대안을 **실측으로 검증**한 결과다.

**(a) 실측 결과 (2026-09-02, 전 구간 통과, 근거유형 = 실측)**
- 터널 관통: 외부에서 `/api/v1/stats` 호출 시 서버 자체 401 응답까지 도달(인증 게이트 정상 작동 확인).
- 외부 경로: `/detect` 201 / `/enrich` 200.
- `DDINGDONG_CAPTURE_URL_BASE` env 값만 교체 → `image_url`이 상대경로에서 전체 https URL로 전환. **코드 0 수정**(~~`server/app/config.py:37`~~ → **실물 48행**(2026-09-05 재확인, 코드 증가에 따른 문서 드리프트 · 결론 무영향)이 이미 `os.environ.get("DDINGDONG_CAPTURE_URL_BASE", "/captures")`로 env 주입식이었기 때문 — 6.1/본 카테고리 스켈레톤 설계가 이미 이 교체를 예정하고 있었음, PR #29 `c30e728`).
- 브라우저 렌더 확인 + **카카오 memo 발송 후 카카오톡 앱에서 이미지 실제 렌더 확인**(7.3 실측 이후 처음으로 실제 이미지 픽셀이 카톡 앱까지 도달).
- 부수 실증: threshold 0.7 게이트 real 경로 작동(confidence 0.47/0.60 → skipped, 0.71 → pending, 카테고리 3·6.2 정합) / `/enrich` 409 재처리 가드 작동 / device·dashboard 토큰 분리 인증 작동.

**(b) ★ 판정: 감사 결론 "EC2가 크리티컬 패스의 유일 선행 조건" 폐기.** EC2는 "필수 선행" → **"정식 배포 수단"**으로 위상이 바뀐다. 발표 크리티컬 패스는 EC2 확보가 아니라 펌웨어(마이크 M5, ToF Stage B 검증)로 이동한다.

**(c) ★★ 단서 — 터널은 안전망이지 정공법이 아니다 (반드시 병기)**:
- 무료 quick tunnel은 **임시 주소**라 재기동 시 주소가 바뀐다 → 발표 당일 절차(터널 기동 → 새 주소 확인 → env 교체 → 서버 재시작)를 **리허설로 못 박아야** 실전에서 안 깨진다.
- 무료 quick tunnel은 Cloudflare 자체 고지상 **가동 보장이 없다**(안정적 SLA 없음).
- 정공법은 여전히 **EC2**이며, 본 절의 터널 경로는 "EC2 없이도 데모는 성립한다"는 **백업 경로**다. ⚠️ 이 단서가 누락되면 다음 세션이 EC2 준비를 영구 스킵할 위험이 있다.

**(d) ★ 재기동 절차 확정 + 관통 확인 = 변수격리 도구 (실측 2026-09-05 / 문서 반영 2026-09-05, 근거유형 = 실측)**
- (c)가 "리허설로 못 박아야 한다"고 적어둔 절차를 실제로 수행했다 — 이번 세션 중 **컴퓨터 재부팅으로 터널·서버가 모두 소실**돼 전 절차를 재수행한 것이 **발표 당일 리스크의 실물 예행**이 됐다.
- 확정 절차: **터널 기동 → 새 주소 확인 → `.env`의 `DDINGDONG_CAPTURE_URL_BASE` 교체 → 서버 재기동 → 터널 관통 확인.**
- ★ **관통 확인 = 변수격리 도구**: 외부 URL로 `/api/v1/notifications`를 호출해 **401이면 서버 도달 성공**(인증만 미통과), **530/502면 터널이 서버를 못 찾은 것**이다. 한 번의 호출로 터널 문제와 서버 문제를 가른다.
- ★ **env 위치 이동**: 9/02 실측 때 `DDINGDONG_CAPTURE_URL_BASE`는 **셸 인라인**이었고 `.env`에 없었음이 이번에 확인됐다. 이제 `.env`에 박혀 있어 서버 재기동만으로 값이 유지된다. ⚠️ 단 `.env` 추가 편집에는 별도 위생 규칙이 붙는다(카테고리 21 「시크릿 파일(`.env`) 편집 위생」).

**(관련 감사 항목) 2026-09-02 감사 G22(🔴)**: "부스 NAT 환경에서 로컬 호스팅 이미지의 카카오 fetch 불가"는 본 절 (a)~(c)의 실측으로 **대안 경로가 확인됨** — 위험 자체는 여전히 유효(EC2 미준비 시)하나, 유일한 해소책은 아님이 실증됨.

**관련**: 카테고리 7 "이미지" 항목(2026-07-31 PoC-(30) 정정) / 카테고리 6.1 `CAPTURE_URL_BASE`(env 주입 설계) / 카테고리 6.2 wire 계약 / 카테고리 23(시연 네트워크 = 모바일 핫스팟, NAT 배경)

### 7.5 A-1 카카오톡 1차 텍스트 알림 end-to-end 완주 + 토큰 재발급 실무 확정 (2026-09-03 PoC-(39) 신설, PR #40 `70aea1d`)

카카오톡 1차 텍스트 알림(A-1)을 코드 0줄 상태에서 end-to-end 관통까지 완주했다. 과정에서 사전 추정이 실측·화면 catch로 뒤집힌 사례가 다수 나왔다 — 이하 (a)~(i)에 **근거유형을 분리**해 기록한다.

**(a) end-to-end 관통 완주 (근거유형 = 실측, 학부생 로컬 M4 + `flask run`)**
- 토큰 SQLite 모델 + 자동 갱신 + memo 실발송 + 확정 카피 ② 배선(PR #40).
- 부트스트랩 → 갱신 API 실호출 성공(access 토큰 길이 64).
- `/detect` 실호출 → doorbell 0.79 → `primary_sent=true` → 카카오톡 도착 확인(화면 catch).
- `fire_alarm` 0.92 → 확정 카피 ② 266자 전문 도착(절단 없음, 화면 catch).
- doorbell 0.68 → `primary_sent=false`(threshold 0.7 엄격 경계 실경로 실증, 카테고리 3 정합).
- 감사 항목 G18/G21/G24 CLOSE. ⚠️ 본 3건은 **decisions.md 미등재**(Notion DB3 전용 감사 ID) — 노션 반영은 별도 세션 소관.

**(b) ★ 확정 카피 ② 200자 상한 반증 (근거유형 = 실측, 7.1 연동)**
- 카카오 공식 문서 + 담당자 답변 기준 "text 템플릿 200자 상한, 초과 시 말줄임표 절단"이 실측으로 반증됐다. 266자 / 603 bytes / 9줄이 절단 없이 렌더됨(HTTP 200, `result_code` 0).
- ⚠️ decisions.md에는 애초 "200자 상한" 서술 자체가 존재하지 않았다(취소선 대상 없음, 순수 신규 실측 등재).
- 성격 구분: 앞선 실측 반전 3회(ToF near 8→20 폐기 / 마이크 `>>16`→`>>14` / ToF aggmax≥50→ndet≥1)는 전부 내부 추정·문서가 뒤집힌 것이었다. 본 건은 **외부 1차 출처(카카오 공식 문서)가 실화면 앞에서 뒤집힌 첫 사례**다.
- 파급: 분할 발송·축약 카피 전부 불요. 코드에 분할 로직 0줄.
- ⚠️ "200자가 무엇을 의미하는지"(byte 기준인지 등)는 미확인 — 추측 기록 금지.
- 재검증 방법 = 프로브 컨벤션(repo 밖 1회 발송, 토큰 env 경유) 재실행 후 카톡 육안 확인.

**(c) ★ 카카오 REST API 키 rotate = 유령 미결 확정 (근거유형 = 실측 화면 catch, 학습 21 계열)**
- 2026-07-31 노출 이후 이월돼 있던 "REST키·client_secret rotate" 항목. ⚠️ **decisions.md 미등재**(Notion DB3 전용 추적 항목).
- 실화면 catch: 플랫폼 키 카드 ⋮ 메뉴 = 수정 / 복제 키 생성뿐(삭제·재발급 없음). 수정 페이지 = 리다이렉트 URI / 클라이언트 시크릿 / 추가 정보뿐, 키 값 재발급 항목 부재.
- 즉 노출된 REST API 키를 무효화할 방법이 콘솔에 없다 — rotate는 애초 **실행 불가능한 작업**이었다.
- 대안 = client_secret 재발급으로 토큰 교환 관문 복원(재발급일 2026-09-03).
- 위협 평가(근거유형 = **논증**): REST키 단독으로는 memo 발송 불가 — 인가 코드는 등록된 Redirect URI로만 전달, 토큰 교환에 client_secret 필수, 사용자 본인 동의 필요, memo는 토큰 소유자 본인에게만 발송.
- 기각한 대안: 호출 허용 IP 설정(카카오 공식 권고) — 부스가 모바일 핫스팟(카테고리 23)이라 IP 가변, 적용 시 데모 파손.

**(d) ★ 카카오 콘솔 경로 정정 (근거유형 = 실측 화면 catch, 학습 13 화면 우선)**
- client_secret 위치 실측: 앱 설정 → 플랫폼 키 → REST API 키 카드 → [클라이언트 시크릿] 칩(URL 패턴 `/console/app/{appId}/config/platform-key/rest/{keyId}`).
- 콘솔이 멀티 REST 키 구조로 개편됨(+ REST API 키 추가 / 복제 키 생성 존재). 클라이언트 시크릿은 REST 키에 종속, 키 발급 시 기본 활성화.
- REST API 키 생성 일시 = 2026-05-14(카테고리 30.2 외부 계정 셋업일과 정합).
- ⚠️ 본 세션에서 AI가 콘솔 경로·기능 유무를 3회 연속 오안내(① REST키 재발급 UI 부재 추정→오류 ② 시크릿 위치→오류 ③ rotate 가능 판단→오류), 2026-09-02 NCP 콘솔 경로 오안내에 이은 연속. → **원칙: AI가 제시한 외부 콘솔 경로·기능 유무는 화면 catch 전까지 전부 추정.**

**(e) ★ 카카오 OAuth refresh 토큰 부트스트랩 절차 확정 (근거유형 = 실측)**
- REST API 테스트 도구는 access 토큰만 발급한다. refresh는 인가 코드 흐름(OAuth)으로만 얻는다 — 본 카테고리 상단 "토큰" 항목의 2026-09-02 재발급 기술을 이 사실로 정정했다(해당 위치 정정 각주 참조).
- 확정 절차: Redirect URI 등록(`http://localhost:5000/oauth`) → 인가 URL 접속 → 동의 → `ERR_CONNECTION_REFUSED` 페이지 주소창에서 `code=` 값 복사(서버 미기동이 정상) → curl로 토큰 교환.
- refresh 발급일 = 2026-09-03, `refresh_token_expires_in` = 5,183,999초(60일). 다음 만료 ≈ **2026-11-02**. 이제 추정이 아니라 실측이다(2026-09-02 재발급은 추정이었음).
- 자동 갱신 배선 완료 — 잔여 1개월 미만 시 카카오가 refresh를 재발급해 내려주면 코드가 저장 → 서버가 주기적으로 돌면 만료가 구조적으로 계속 리셋된다. ⚠️ "잔여 1개월 미만일 때만 재발급"은 공식 문서 서술(근거유형 = **문서 인용, 미실측**). 판정 방법 = 2026-10월 초 갱신 시 `refresh_token` 값 변경 여부를 로그로 확인.
- ✅ **자동 갱신 배선 ④런타임 실증 (실측 2026-09-05 / 문서 반영 2026-09-05, 근거유형 = 실측)**: `.env`의 `KAKAO_ACCESS_TOKEN`이 만료(`ACCESS_TOKEN_EXPIRED`, code -401) 상태였는데도 카카오톡 발송이 성공했다. DB(`kakao_tokens` SINGLETON_ID=1)의 access 토큰으로 `/v1/user/access_token_info`를 조회하니 `expires_in 21083`초 — 6시간 TTL(21600) 대비 **약 8.6분 전 발급**이고, 그 시각이 그날 첫 `/detect` 호출 시점과 일치한다. → PR #40의 **401 자가 치유 + refresh 갱신 배선이 실동작함이 시계로 증명**됐다(위 "자동 갱신 배선 완료"의 미검증 꼬리표 해소). ⚠️ 단 **"잔여 1개월 미만일 때만 refresh 재발급"은 여전히 문서 인용·미실측**이며, 판정 방법(2026-10월 초 갱신 시 `refresh_token` 값 변경 여부 로그 확인)도 그대로 유효하다.
- ⚠️ 조건: 만료 전 서버가 최소 1회 발송해야 갱신이 돈다. 장기 미가동 시 본 절차 재실행.
- 토큰·시크릿 실값은 본 문서에 미기록.

**(f) ★ 데스크톱 vs 모바일 렌더 차이 — 카피 조정 불요 판정 (근거유형 = 실측 화면 catch)**
- 데스크톱 카카오톡에서 확정 카피 ②의 어절이 줄 끝에서 분절되는 현상 관측(예: "천/으로", "음/성통화").
- 5060 노안 사용자 가독성 우려로 줄바꿈 조정을 검토했으나, 휴대폰 카카오톡 실화면 확인 결과 분절 미발생 → 조치 불요로 판정.
- 원칙: 렌더 결과는 클라이언트 폭에 종속된다. 실사용 환경(모바일)을 확인하지 않고 데스크톱 화면만 보고 카피를 손대면 7.1 검증본을 훼손하게 된다.

**(g) ★ feed/commerce 템플릿 본문 2줄 제약 → A-2 defer (근거유형 = 문서 인용, 미실측)**
- 이미지 포함 템플릿은 본문을 2줄만 표시한다(카테고리 7 "이미지" A-2 스켈레톤 항목과 연동). A-2(2차 이미지 + STT 자막)에 직결 — 자막이 길면 잘린다.
- ⚠️ 본 건의 근거유형은 (b)에서 반증된 200자 건과 **동일**(문서 인용에서 출발, 미실측) — (b)처럼 반증될 수도, 그대로일 수도 있다. 판정 전까지 결론 선반영 금지.
- 판정 방법: A-2 착수 전 실 feed 발송 1건(긴 더미 자막 + 임의 public URL) 후 카카오톡 앱 화면에서 몇 줄까지 보이는지 육안 확인(프로브 컨벤션 재사용).
- 실측 후 결정 대상 = ① 자막 길이 상한 정책 ② 텍스트 memo + 이미지 memo 2건 분할 여부(7.3 실측 p95 490ms = 15초 예산 3.3%라 분할해도 예산 여유 충분).
- ✅ **판정 완료 — 2줄 제약 실재 확증 (실측 2026-09-04 / 문서 반영 2026-09-05, 근거유형 = 문서 인용·미실측 → 실측 승격)**: 위 판정 방법대로 실계정 memo feed **3단계 프로브** + 모바일 카카오톡 육안을 수행했다. P1 자막 15자 → **1줄 전문 렌더** / P2 자막 52자 → **2줄 절단 + 말줄임표** / P3 자막 110자 → **2줄 절단 + 말줄임표**.
  - **판정 1**: feed description **2줄 상한 실재**. 문서 인용이 맞았다.
  - **판정 2**: **상한 기준은 글자 수가 아니라 줄 수이며, 절단 지점은 렌더 폭에 종속된다.** 52자와 110자가 둘 다 2줄에서, 서로 **다른 글자 위치**에서 잘렸다 → 서버에서 "자막 N자 상한"을 정하는 것은 **원리적으로 불가능**하다. 이 판정이 7.6(e) "자막 길이 상한 상수를 만들지 않는다" 설계를 낳았다.
  - **결정 대상 ② 확정**: 분할 채택(사진 feed 1건 + 자막 text 1건). 상세 = 7.6.
  - ★★ **근거유형 교훈**: 위 (b)에서 **반증된** 200자 건과 본 건은 **같은 "문서 인용·미실측" 등급**이었는데 결과는 갈렸다(하나는 반증, 하나는 확증) — **근거유형이 같아도 결과는 갈린다.** 프로브 없이 "이번에도 문서가 틀렸겠지"로 넘어갔다면 자막이 잘린 채 A-2를 짰을 것이다.

**(h) ★★ 7.4(c) 단서 실증 — 터널 주소 소멸 (근거유형 = 실측 화면 catch)**
- 2026-09-02 터널 실측으로 카톡에 전송했던 이미지가 2026-09-03 확인 시 회색 빈 박스로 렌더됨(이미지 fetch 실패).
- 7.4(c) "quick tunnel은 임시 주소라 재기동 시 변경"이 실물로 증명됨. 발표 당일 리허설 필요성의 직접 근거.

**(i) 회귀 테스트 자산 부재 → 자산화 (학습 21 계열)**
- 카테고리 6.2의 "curl 회귀 10종/15종/25종" 서술은 **실행 기록이지 repo에 실행 가능한 자산으로 존재한 적이 없었다**(PR #40 작업 중 확인) — 6.2 본문은 당시 실제 수행한 수동 실행 기록이라 정정 대상 아님.
- PR #40에서 `server/app/tests/test_detect_regression.py`로 자산화(stdlib unittest, ~~30 케이스~~ → **60 케이스**(PR #43 +12 / PR #44 +18 누적, 2026-09-05 실측)). 실행 = `server/`에서 ~~`python3 -m unittest app.tests.test_detect_regression`~~ → **`venv/bin/python3 -m unittest app.tests.test_detect_regression`**(2026-09-05 정정 — 시스템 python3에는 flask가 없어 import 단계에서 실패한다). ⚠️ negative control 실행 시에는 여기에 `-B`를 더한다(카테고리 20 「negative control은 `python3 -B`로 실행」).

**관련**: 카테고리 6.2(G14/wire 계약/curl 회귀) / 7.1(확정 카피 ①②) / 7.4(터널 이미지 호스팅) / 카테고리 20(계측→실측→판정 원칙) / 카테고리 30.2(카카오 앱 셋업)

### 7.6 A-2 카카오톡 2차 알림 배선 — 사진 feed + 자막 text 2건 분할 발송 (2026-09-05 PoC-(41) 신설, PR #44 `a431961`)

카테고리 7 "2차 알림 = best-effort + 1회 재시도"와 7.5(g) feed 2줄 판정을 근거로 A-2 **발송 배선**을 실코드화했다. ⚠️ **A-2 발송 배선 CLOSE ≠ A-2 완료** — 자막이 아직 **mock 문구**(`server/app/utils.py` `_MOCK_TRANSCRIPTS`)이고 실 STT 소스 배선은 **0줄**이다(카테고리 7 STT 항목 참조). 발송 경로와 자막 소스는 분리해 읽어야 한다.

**(a) 산출물 (근거유형 = 실측)**
- `kakao.py` 함수 5개 신설(`_feed_description` / `_build_secondary_title` / `_post_memo_feed` / `_send_part` / `send_secondary`).
- `constants.py` 3종(`KAKAO_SECONDARY_MAX_ATTEMPTS=2` / `KAKAO_FEED_BUTTON_TITLE` / `SECONDARY_FEED_TITLES`).

**(b) 발송 순서 = 사진 먼저, 자막 나중 (근거유형 = 논증)**
"누가 왔는지"가 "뭐라고 말했는지"보다 먼저 필요하다. 분할 자체의 예산 여유는 7.3 실측(feed p95 ≈490ms = 15초 예산의 3.3%)이 이미 보증한다.

**(c) 재시도 = 실패한 건만 개별 1회 (근거유형 = 논증)**
- 2건 통째 재시도는 **금지** — 성공한 사진이 중복 발송된다.
- 분류는 **예외 클래스 기준**: `KakaoSendError`만 재시도, `KakaoTokenError`(401)는 재시도 없음(7.5 A-1 자가 치유 규약 정합).
- ★ 사진에서 401을 받으면 **자막 왕복도 태우지 않는다** — 이벤트당 왕복 상한을 지키는 A-1 성질의 2차 확장.

**(d) ★ 상태 표현 = 기존 키 값 조합, 프론트 수정 0 (근거유형 = 실측)**
- `secondary_sent` = **전부 성공** / `secondary_sent_at` = 사진 전달 시각 / `enrich_status="failed"` = 자막 실패. `to_dict()` 최상위 키 수 **11 불변**(프론트 `NotificationItem` **11필드**와 1:1, 양쪽 실물 대조).
- ★ **결정적 근거(실측)**: `NotificationStatusBadge.derive()`가 `secondary_sent`를 `enrich_status`보다 **먼저** 본다 → `secondary_sent`를 "사진 성공"으로 정의하면 **부분 성공이 "전송 완료"로 렌더**된다. 그래서 "전부 성공"으로 정의했다.
- `EnrichStatus`의 `"failed"`는 프론트에 **선언은 돼 있으나 서버가 한 번도 낸 적 없던 값**이다 — 6.4의 `tof_check.passed` null과 같은 "선언된 값 형태를 처음 쓰는" 확장.
- `/enrich` 종결 상태에 `"failed"` 추가 → 재처리 시 이미 성공한 사진의 **중복 발송 차단**.

**(e) 자막 부재 · 길이 정책 (근거유형 = 논증, 근거가 되는 판정은 7.5(g) 실측)**
- 자막 부재 시 = feed 1건만 발송, text 미호출. **자막 없음 ≠ 실패**로 구분한다.
- description = 감지 시각 1줄("9월 5일 13:39 감지", 약 20자 고정). 7.5(g)가 "상한 기준은 글자 수가 아니라 줄 수"라고 판정했으므로 **자막 길이 상한 상수를 만들지 않고, 애초에 상한이 필요 없는 길이만 생성**하는 방식을 택했다.

**(f) 동기 발송 유지 (근거유형 = 논증·산술, 입력 실측 = 7.3 / 6.2)**
정상 p95 ≈1초(15초 예산의 6.5%), 최악 ≈7.5초(50%) — 펌웨어 `HTTP_TIMEOUT_MS=10000` 안. 비동기 발송 아키텍처 불요(6.2의 1차 판정과 동형).

**(g) 회귀 + 전 분기 열거 (근거유형 = 실측)**
- 회귀 케이스 기존 42 → **60**(신규 18).
- 전 분기 **164건** 열거(자막 유무 2 × feed 시도대본 9 × text 시도대본 9 + 토큰 실패 2), 미정의 동작 **0** → **고유 6행 결정표로 붕괴**.
- negative control **7건** 전건 검출(지정 NC-1~3 + 자체 설계 NC-5~7 + 함정 NC-4). ★ NC-4(발송 순서 뒤집기)가 **실재** — 결과만 검사하는 케이스로는 무해했고 **wire 요청 시퀀스를 직접 검사**해야 잡혔다(카테고리 20 연동).

**(h) ④런타임 실측 (터널 + 실호출 + 카카오톡 화면, 실측 2026-09-05 / 문서 반영 2026-09-05, 근거유형 = 실측)**
- 카카오톡 **3건 도착** — 1차 텍스트 → 사진 카드 → 자막. **순서 실물 확인**.
- 사진 렌더 정상(600×400 JPEG) / description "9월 5일 13:39 감지" 절단 없음 / 자막 "계세요? 옆집인데요." 전문 표시.
- 2차 체인 지연 = 13:39:04.434 → 13:39:07.044 = **2.61초**(15초 예산의 17.4%). ⚠️ **ESP32 캡처·업로드 미포함** — 2차 전 구간 수치가 아니다.
- `doorbell 0.70`이 `pending`으로 통과 = 신뢰도 경계(strict `<`) **실증 3회차**(카테고리 3 정의 / 7.4(a) / 7.5(a)에 이은).

**(i) 🟡 [신규 미결] 2차 자막 실패의 영구 포기 정책 (발견 2026-09-05 / 문서 반영 2026-09-05, 근거유형 = 논증)**: (d)에서 `/enrich` 종결 상태에 `"failed"`를 넣어 재처리를 막았다. 대안(중복 사진 발송)보다 낫다고 판단했으나, **일시적 네트워크 실패와 영구 실패를 구분할 근거가 아직 없다**(PR #44 한계 = 네트워크 타임아웃 미재현). 트리거 = 실 ESP32 2차 클라이언트 연동 후 재판단.

**관련**: 카테고리 7(2차 알림 재시도 정책 / 이미지 public 호스팅 / STT) / 7.3(이미지 memo 왕복) / 7.4(터널) / 7.5(A-1 · feed 2줄 판정) / 6.4(ToF 메타 wire) / 8.3(뱃지 과소 표기 미결) / 카테고리 30.9(CSR 왕복·과금)

---

## 카테고리 8: 대시보드

- Vite + React + shadcn/ui (Tailwind)
- REST 폴링 3초
- 접근성 UI: 단계별 온보딩 + 물음표 모달

### 8.1 5/26~6/14 chunk 단계별 진행 결정 (2026-05-26 신설, 메이크잇펀 일시품절 chunk 활용)

**배경**:
- 메이크잇펀 일시품절 catch (2026-05-26 14:20, decisions.md 카테고리 22.7 도착 정정) → 부품 도착 약 6/17~6/19 예상
- 5/26~6/14 약 20일 chunk = 부품 무관 작업 진행 영역 → 학부생 제안 (5/26): "부품은 15일까지 대기하고 그 전에 다른 작업을 하는 건 어때 예를 들어 뭐 웹 대시보드를 개발한다던가 (ui 등) 부품 없이도 뭐 할 게 있지 않을까?"
- 학습 17 유도리 마인드 정합 — 외부 의존 chunk 슬립 시 부품 무관 작업 자유 재배치 가능

**결정**: 단계별 진행 (Phase 1 React 단독 → Phase 2 React + Flask)

**근거**:
- 학부생 React 익숙 + Flask 처음 (학부생 직접 catch, 5/26)
- 동시 진행 (A + B) 시 학습 부담 매우 높음 + catch 그물 작동 위험 ↑
- 단계별 진행 = 학부생 익숙 영역 (React) 먼저 진행 → Phase 2 진입 시 Flask 1차 학습 + React 익숙 상태 = 학습 시간 분산 + 9월 발표 안정성 ↑

**Phase 1: React 웹 대시보드 단독**:
- 작업 범위: Vite + React + shadcn/ui + Tailwind 셋업 + UI 골격 + 핵심 컴포넌트 (알림 카드 / 통계 / 설정 / 접근성 UI) + mock JSON 데이터 (카테고리 4 API 명세 1차 안 기반) + REST 폴링 3초 구조
- 위임 프롬프트 진행 방식: 카테고리 4 + 8 cross-reference catch 강제 (API 명세 1차 결정) + find-skills MCP 활용 강제 (frontend / react / vite / shadcn-ui) + 코드 작성 자체 검증 3단계 강제
- **✅ 완료 (2026-05-28 PoC-(14), PR #1 머지)**: 69파일 / 9180줄. Playwright 실동작 검증 통과 (5종 알림 카드 분기 + 다크모드 + Pretendard 실로드 + 콘솔 0 에러). 확정 기술 스택 / 컴포넌트 17개 / 디자인 토큰 = 카테고리 8.2 / API 명세 = 카테고리 6.1·4·7. ※ Phase 2 전환 = 학부생 자율 (날짜 미고정, 학습 17 정합)

**Phase 2: React + Flask 동시 (Flask 학습 진입)**:
- 작업 범위: Flask + SQLAlchemy 모델 + API 엔드포인트 (학부생 MacBook M4 로컬 진행) + POST /api/detect + POST /api/enrich 1차 구현 (카테고리 4) + React mock → 실제 API 전환 + REST 폴링 실제 동작 검증 + 미니 E2E 통합 1차
- 위임 프롬프트 진행 방식: Flask 학습 곡선 catch 강제 (학부생 첫 진입 = Claude Code MCP가 본문 설명 + 코드 작성 + 학습 영역 분리 강제) + 자체 검증 3단계 강제
- AWS EC2 인스턴스 띄우는 시점 = 11~12주차 (7/27 이후) 진입 시 (Phase 2는 로컬 단독, AWS 비용 0원)
- **✅ 2-1차 완료 (2026-06-14, PR #2 `37a92b3`, 브랜치 `feat/server-flask-skeleton` 머지 후 삭제)**: Flask 백엔드 골격 — app factory + Blueprint(`/api/v1`) + 모델 2종(`notifications` / `idempotency_keys` 24h TTL) + 엔드포인트 4종(`detect` / `enrich` / `notifications` / `stats`). 인증 Device/Dashboard Token 분리 + rate limit(device_id 5초 1회) + idempotency + HTTP Status 8종, curl 15종 통과. ML 추론 = mock(실제 YAMNet 11주차), HTTPS/EC2 = 11주차(현재 로컬 http). **JSON 1:1 = `dashboard/src/types/`** (api.ts / notification.ts / stats.ts) — SSoT 단일화 유지. 상세 = 카테고리 6 + 6.1
- **✅ 2-2차 완료 (2026-06-15, PR #3 `cec9c9b`)**: React mock → 실제 Flask API 연동. `dashboard/src/types/api.ts`에 cursor 메타(`next_cursor` / `has_more`) additive 추가 + mock → 실제 fetch 전환(`apiGet` 공용 헬퍼로 DRY, 폴링 훅 무수정) + Vite dev proxy로 CORS 우회. env `VITE_API_BASE_URL=/api/v1`(상대 경로, proxy 경유). 미니 E2E 전항목 통과: seed 11건 렌더 + detect 오늘 주입 → stats 0→1 반영 + CORS 0건 + 폴링 3초 + 콘솔 0 에러 + tsc/eslint/build 통과. CORS 처리 상세 = 카테고리 6
- **follow-up (stats 폴링 중복, 2026-06-15 발굴)**: 2-2차 연동 후 `/stats`가 폴링 주기당 2회 호출됨 — `useStats`(통계 섹션) + `useDevice`(헤더 디바이스 상태)가 독립 폴러로 각자 호출. GET은 rate-limit 제외 + 3초 주기라 현재 안전하나, 공유 폴러 or Context 통합 권고(추후 폴리시 or 11주차). 학습 16(기존 컨벤션 우선)에 따라 이번엔 미변경
  - **정정 (2026-06-29 PoC-(19) 베테랑 리뷰 실측, 위 "2회"는 과소 집계 — 이력성 보존, 덮어쓰기 X)**: `/stats` 폴러 실측 = **3중** (StatsPage + StatsCardsSection + Header 독립 폴러). 추가로 Phase B B-1a(aria-live announce)가 notifications **announcer 폴러 +1** 신설 → **폴링 통합 대상 = stats 3중 + announcer 1**. 통합(공유 폴러/Context)은 여전히 deferred (카테고리 8.3 미결, 11주차 or 폴리시). 학습 16 정합 미변경 유지.

**Phase 1 → Phase 2 전환 트리거** (학부생 자율, 학습 17 정합 — 날짜 박지 X):
- Phase 1 React UI 골격 + mock 데이터 완성도 학부생 자체 평가 후
- 학부생 컨디션 + 학교 일정 + Flask 학습 진입 의지 catch 후
- 메이크잇펀 도착 catch 결과 (6/15 이전 / 이후) 무관

**SSoT 영역 vs 학부생 자율 영역**:
- SSoT 박음: Phase 1 / Phase 2 작업 범위 + Phase 2 로컬 진행 강제 (AWS 비용 0원)
- 학부생 자율 (날짜 X): Phase 1 → Phase 2 전환 시점 + 일별 작업 강도 + 휴식 chunk + Phase 2 완료 시점 + 메이크잇펀 도착 후 PoC 진입 시점

**학습 17 본문 강화 사례 (5/26 본 결정 진행 중 발굴)**:
- Claude (AI) 초기 박은 추천 본문에 세부 날짜 (Phase 1 5/26~6/3 / Phase 2 6/4~6/14) 박음
- 학부생 push back "단계별로 세부 날짜까지는 확정짓지마" → 학습 17 유도리 마인드 직접 위반 catch
- 정정 = chunk 단위 작업 범위만 SSoT, 세부 날짜 박지 X = AI 본인도 학습 17 catch 그물 작동 대상
- decisions-log 2026-05-26 entry로 영구 반영

### 8.2 Phase 1 확정 기술 스택 + 컴포넌트 + 디자인 토큰 (2026-05-28 PoC-(14))

**기술 스택**:
- Vite + React 19 + TypeScript + Tailwind v4 (CSS-first, `@theme inline` — `tailwind.config.js` 없음) + shadcn/ui
- 라우팅: React Router (v7 설치, v6 호환 API) — 5페이지 + 404
- 데이터 fetching: `fetch` + `useEffect` custom hook (`usePolling`) — TanStack Query 미채택 (Phase 1 단순성)
- 상태: Context API + `useState` (`OnboardingContext` / `SettingsContext`) — Zustand 미채택
- 아이콘: Lucide React / 차트: shadcn/ui Chart (recharts, lazy 분할)
- 폰트: Pretendard Variable

**컴포넌트 17개 (4계층) + StatsCardsSection**:
- 레이아웃 3: AppShell / Header / Sidebar
- 통계카드 4: TotalDetectionsCard / ClassDistributionCard / TimingMetricsCard / SystemHealthCard (+ StatsCardsSection 묶음)
- 알림 5: NotificationCard / List / Image / STT / StatusBadge
- 보조 5: EmptyState / ErrorBoundary / HelpTooltip / LoadingSkeleton / OnboardingModal

**페이지 5종 (+404)**: Home / Notifications / Stats / Settings / Help

**디자인 토큰**:
- 컬러 / 타이포 (Pretendard 정량) / 터치 타겟 (44 / 48 / 52 / 56px 단계)
- 화재경보 강조: `shake` + `pulse-border` 애니메이션 (+ `prefers-reduced-motion` 대응)
- 디자인 영감: 한국 대중 앱 (카카오톡 / 토스 / 당근) 우선

### 8.3 Phase B 접근성 + 베테랑 리뷰 (2026-06-29 PoC-(19) 신설)

> Phase 2 완료(2-2차, PR #3) 이후 별도 chunk. 웹 대시보드 **베테랑 리뷰(read-only)** + **접근성 3PR(B-0/B-1a/B-1b)** 완결. 8.1/8.2(Phase 1/2 기록) 보존, 본 절은 Phase B 결과 전용.

**B-0 — dashboard tsconfig strict 활성화 (✅ PR #5 `56e44b8` 머지)**:
- dashboard `tsconfig` strict 모드 활성화 = Phase B 접근성 작업의 타입 안전 토대.

**B-1a — a11y 색상 단독 의존 해소 + aria-live announce (✅ PR #6 `e9b9879` 머지)**:
- 상태 표시 색상 단독 의존 해소(텍스트/아이콘 병행) + `aria-live` announcer로 폴링 갱신 스크린리더 공지.
- ※ announcer = notifications 폴러 **1개 신규** → 폴링 통합 대상에 합산 (8.1 follow-up 정정 = stats 3중 + announcer 1).
- ※ PR #6 머지 시 로컬 main 미동기화로 PR #5 strict 커밋이 끌려오고 merge commit 생성된 사건 → **학습 18 신설 근거**(카테고리 20).

**B-1b — Skip-to-content + 모바일 drawer 포커스 트랩/복원 (✅ PR #7 `3408d97` 머지)**:
- 본문 바로가기(skip link) + 모바일 drawer 키보드 포커스 트랩 + 닫을 때 트리거로 포커스 복원.

**베테랑 리뷰 결과 (read-only, 본 리뷰 코드 0 수정)**:
- 🔴 Critical **0건** / 🟡 4건 / 🟢 6건 / **deferred 6건**. 🟡🟢 항목은 Phase B 작업(B-0/B-1a/B-1b)으로 분류·반영.
- deferred 6건 대표 4건: ① 폴러 통합(stats 3중 + announcer 1 → 공유 폴러/Context) ② Pretendard self-host(현재 번들/CDN 의존) ③ large-text 모드 ④ **SR 실청취 미검증**(코드상 aria 반영했으나 실제 스크린리더 청취 테스트 미수행).

**Phase B 잔존 미착수 (11주차 or 폴리시 — 본 chunk 미변경)**:
- 폴러 통합 / Pretendard self-host / large-text 모드 / SR 실청취 실측 — 전부 deferred. 학습 16(기존 컨벤션 우선) 정합으로 권고만 박음, 코드 미변경.

**B-2 ~ B-4 — 페르소나 정합 (2026-06-30 PoC-(20), 웹 대시보드 5060 페르소나 직격)**:

- **B-2 라이트 테마 기본 전환 (✅ PR #8 `a615162` feat, 머지 `3544db4`)**: 다크 기본 → **라이트 기본**(SettingsContext default 전환, 다크는 토글+localStorage opt-in **보존** — 통째 제거 X). ※ 위임 "다크 위주" 가설 = 실측상 `:root` 라이트 토큰 **이미 완비**로 거짓 판명(학습 17 catch). 폰트 토큰 상향(`--text-body` 16→17 / `--text-caption` 14→15). footer dev cruft("Phase 1·v0.1") 제거. 연결배지 3구분(online=초록 / offline=빨강 / processing=노랑 — 색+shape+텍스트, WCAG 1.4.1). 근거: 타겟 5060 노안 가독성.
- **B-3·B-4 시스템 건강 카드 + 화재 카피 반영 + 대비 보정 (✅ PR #9 `ca61e1b` 머지)**:
  - 빈 화면 에러카드 → **"시스템 정상 작동" 안심 카드**(SystemHealthSummaryCard, 3지표 기기/마지막감지/신호).
  - **타입 SSoT ㄴ안**(학습 16/29): 기존 `SystemHealth`(device_status/device_last_seen_at 기보유) + `signal_strength` **additive**(신규 필드 난립 X). 서버 mock + mock-data 1:1.
  - ※ `device_status` mock=online 고정(빈 상태 안심 전제, **실 heartbeat 연동 11주차**). 빈 vs 에러 구분 보존(emptySlot = 정상-빈만 대체, loading/error 무영향).
  - 도움말 화재 카드 = **7.1 확정 카피 ① 4단계 verbatim 교체**(7.1 → 도움말 화면 반영 완결).
  - 화재 텍스트 대비 보정(`#FF4444` 3.0:1 → `#CC0000` ~5.2:1, salience fill `#FF4444` 유지).

**잔존(여전히 deferred — B-2~B-4로 미해소, 갱신)**:
- 폴러 통합 — **카운트 갱신**: stats 3중 + announcer 1 + **건강카드 useDevice +1**. / Pretendard self-host / ~~large-text 모드~~ **[2026-07-06 정정 → shipped, B-5 참조]** / SR 실청취 실측. → 11주차 or 폴리시.
- (신규) **화재 번호뱃지 대비** ~~~3:1(큰 글씨라 WCAG 1.4.3 large-text 3:1 충족 추정) → 발표 전 실측 권고. 과한 단정 금지.~~ **[2026-07-06 실측 확정 → B-5]**: white on `#FF4444` = **3.41:1** (large-text 3:1 충족 ✓ / normal-text 4.5:1 미달). 보정안 `#CC0000` = 5.89:1(미착수).

**GitHub Flow**: 코드 PR #8/#9 = 8~9번째 사이클(feat 브랜치 + Squash 머지 + self-approve). 학습 18(웹 머지 후 pull) 2회 정상 fast-forward.

**B-5 — 발표 데모 마무리 + Phase B 잔존 2건 정정 (2026-07-06 PoC-(22), PR #16·#17·#18)**:

- **알림 사진 전체화면 라이트박스 + "크게 보기" 힌트 뱃지 (✅ PR #17 `c25f789`)**: radix Dialog(shadcn) 재사용 라이트박스 — 3경로 닫기(X 44px / 배경 / ESC) + 포커스 트랩·복원 + scroll-lock + `aria-modal`, 이미지 `object-contain`(확대 시 무크롭). 힌트 뱃지 = `Maximize2` 아이콘 + "크게 보기" 텍스트 병기(WCAG 1.4.1 색 단독 의존 해소), `bg-black/60` 흰텍스트 대비, caption 15px 노안 상향, `pointer-events-none`(히트영역 유지) + `aria-hidden`(SR 중복 방지). → 8.3 접근성 계열 확장.
- **더미 이미지 썸네일 잘림 수정 (✅ PR #18 `d57f3ae`)**: `demo-*.svg`를 가로 2:1(480×240) + 콘텐츠 세로중앙 safe-zone으로 재작성 → 카드 썸네일 `object-cover h-40` 크롭에도 텍스트 안 잘림. (동 PR의 서버 timing 실계측 = 카테고리 6.1 참조.)
- 🟢 **[정정] large-text 모드 = deferred → shipped 확정**: 위 잔존 리스트의 "large-text 모드 deferred"는 **stale**. 실측 = `dashboard/src/index.css:160 html.large-text{ zoom:1.15 }` + `SettingsContext`(largeText state + `<html>` 클래스 토글) + `SettingsPage` 토글 배선 전부 **shipped**. 문서만 정정(코드 무변경).
- 🟡 **[정정] 화재 번호뱃지 대비 = "~3:1 추정" → 실측 3.41:1 확정**: white on `#FF4444`(`--danger`/`--status-failed`) = **3.41:1**. WCAG 1.4.3 large-text 3:1은 **충족**하나 normal-text 4.5:1은 **미달**. 보정안 = `bg-danger-deep #CC0000` = **5.89:1**(코드: `dashboard/src/index.css` `--danger-deep`). ~~보정 **미착수**(별도 소형 a11y PR 예정) → 발표는 large-text 3:1 충족으로 진행 가능.~~ ※ 본문 텍스트 대비는 PR #9에서 이미 `#CC0000` 보정 완료(위 B-3·B-4), 본 건은 **번호뱃지 배경** 한정.
- ✅ **보정 완료 (2026-07-07 PoC-(24), PR #20)**: 화재 번호뱃지 배경 `bg-danger`(#FF4444)→`bg-danger-deep`(#CC0000) = **5.89:1**(WCAG AA normal 4.5:1 충족). 대상 = `NotificationCard.tsx:104` / `HelpPage.tsx:87` 스텝 번호뱃지 2곳. salience fill `#FF4444`(shake/pulse-border animate)는 유지(텍스트 대비 요소 아님).
- **데모 시드 인프라 (PR #16 `6b26bd6`)**: 상세 = 카테고리 6.1 seed 항목. 8.3 관점 = 발표용 완성 UX(사진/자막/2차 처리중/미발송) 한 화면 확정 렌더.

**신규 미결 2건 (발견 2026-09-05 / 문서 반영 2026-09-05, PR #43·#44 파급, 근거유형 = 실측)**:
- 🟡 **뱃지 과소 표기**: `NotificationStatusBadge.derive()`가 (사진 실패 + 자막 성공) / (자막 없음 + 사진 실패) 조합을 "1차 발송"으로 렌더한다. 금지선인 "부분 성공 → 완전 성공" **오표기는 아니지만** 과소 표기다(7.6(d) 연동 — `derive()`가 `secondary_sent`를 `enrich_status`보다 먼저 보는 순서가 원인). 해소 = `derive()` 분기 1개 추가, K 대시보드 소액 PR 소관.
- 🟡 **ToF 상세가 화면에 미표시**: `dashboard/src/components`·`pages`에서 `tof_check` 참조 **0건**(실측 grep). USP 2층의 1차가 ToF 융합 서사(카테고리 33 「USP 2층 재정립」 / 26.1)인데 **화면에 그 근거가 없다** — 6.4로 서버가 실 ToF 값을 내기 시작했으므로 표시 대상이 생겼다. 해소 = K 대시보드 소액 PR 소관.

---

## 카테고리 9: VL53L5CX 사람 검증 단계

- **Stage A (필수)**: zone count 임계값 (1m 이내 ≥8 zone)
  - ※ **2026-08-08 PoC-(35) ④런타임 검증 완료** (PR #34 `ecfe5a0` 실코드화 + PR #35 `af1fbf9` 디바운스): 임계값 8 실측 타당성 확인(무인 near 0~2 / 1m 사람 9~13) — 상세 = 9.2. **Stage B는 여전히 ④런타임 미검증**(Motion Indicator, 아래 Stage B 절). ※ **2026-08-12 PoC-(36) 갱신**: Stage B-1 **계측 계층**(관측 전용, presence 판정 무융합)은 ④런타임 실측 완료(9.3) — 판정 융합·임계값 확정은 B-2 미결.
- **Stage B (필수)**: Motion Indicator + ~~per-zone threshold~~ **aggregate 단위 motion 검출** (2026-08-12 PoC-(36) 정정)
  - ★ **정정 근거 (2026-08-12)**: motion 데이터는 per-zone(8x8=64)이 아니라 **aggregate 단위**. 8x8 해상도에서 활성 aggregate 16개, 각 2x2 super-zone. `map_id = (i%8)/2 + 4*(i/16)`. 배열 = `motion_indicator.motion[32]`. 근거 = 라이브러리 실물(`vl53l5cx_plugin_motion_indicator` 계열 / `motion_indicator.cpp:150-155`).
  - ★ **설계 파급**: Stage A는 8x8 zone 단위로 near를 세는데 motion은 4x4라 "near로 잡힌 그 zone이 움직이는가"를 1:1로 물을 수 없다. 2x2 단위로만 가능 → **사람과 정지 사물이 같은 super-zone에 겹치면 분리가 원리적으로 불가**. (실측 = 9.3)
  - 발원 = 2026-07-09 판정 B에서 함수 시그니처만 확인하고 반환 자료형 shape 미확인(학습 15 ②단계를 함수까지만 수행) / 반영 = 2026-08-12.
- **Stage C/D (선택)**: NanoEdge AI / Passing-by filter

### Stage B Motion Indicator 노출 확정 (2026-07-09 PoC-(26), 판정 B)
- 래퍼(`SparkFun_VL53L5CX`) 전용 메서드 0건 — **번들 ULD 함수**(`vl53l5cx_motion_indicator_init`/`_set_distance_motion`/`_set_resolution`)를 `imager.Dev` public 핸들로 직접 호출. `VL53L5CX_DISABLE_MOTION_INDICATOR` 매크로 주석처리(platform.h)로 컴파일 활성. `.motion_indicator` 필드 ResultsData 상주. RAM 순증 **+156B**(Motion_Configuration, 무거운 모션 머신러리는 현 footprint 기지불).
- **학습 15 4단계 중 ③컴파일까지 확정 / ④런타임 = 센서 대기**(브레드보드 결선 후). frozen 파일 0 수정(import 검증만). 스크래치 프로브는 repo 밖.
- ※ **2026-08-07 갱신(카테고리 9.1)**: 브레드보드 브링업 성공으로 센서 자체 런타임(`tof_dummy` 기본 8x8/15Hz 프레임)은 실동작 확정. 단 **Motion Indicator 전용 런타임(본 절 대상)은 해당 env 재빌드로 별도 재확인 대기** — 브링업 로그는 `tof_dummy`(프레임 카운트)라 `.motion_indicator` 필드 런타임은 미측정.

### 9.1 브레드보드 브링업 실측 확정 (2026-08-07 PoC-(34) 신설)

2026-08-06~07 이틀에 걸친 VL53L5CX-SATEL 브레드보드 브링업이 **2026-08-07 성공**. `env:tof_dummy` 런타임 로그로 확정.

**(a) 성공 로그 (verbatim 실측)**
```
[tof] VL53L5CX ready (8x8, 15Hz, continuous)
[BOOT] tofTask started on Core 0 priority 3
[tof] frame #1 (8x8, 64 zones)
[tof] frame #31 (8x8, 64 zones)
[MEM:tofTask-entry] Heap free=359108 min=354320 / PSRAM 8386295 free
```

**(b) ★ 근본원인 = PWREN/LPn 미구동 (오늘 최대 발견)**
PWREN·LPn 두 핀이 HIGH로 구동되지 않으면 VL53L5CX가 셧다운 상태로 남고, 그 상태에서 **SDA 라인을 LOW로 물어** I2C START 컨디션 자체가 성립 불가 → 어떤 핀 조합으로도 0x29 ACK가 안 나오던 현상의 단일 원인. 근거(외부 문서, 각 15단어 이내 인용):
- DS13754: "drive LPn to logic1 to enable I2C comms" (LPn HIGH = I2C 활성).
- AN5717: PWR_EN = 온보드 5V→3V3 레귤레이터 enable 게이트.
- UM2884 §4.1 초기화 시퀀스: LPn=High, I2C_RST=0(LOW).

**(c) SATEL 실측 핀맵 (브레드보드 세로줄 번호 기준)**
SATEL 배치 = E행, 삼각형(▶) 마커 = 36번. `B30=SDA / B31=SCL / B33=PWREN / B34=LPn / B35=IOVDD / B36=GND`.
※ 뒷면 실크를 **단일 열로 읽은 기존 가정은 오독** — AN5717 Table 1 = SATEL은 **9핀 커넥터 2개**(전원/아날로그 열 + 디지털 열) 구조.

**(d) 최종 결선 6가닥 (재현용 SSoT — 다음 세션이 이 표만으로 복원 가능)**

| 색 | XIAO | SATEL |
|---|---|---|
| 빨강 | B7 (3V3) | B35 (IOVDD) |
| 검정 | B6 (GND) | B36 (GND) |
| 주황 | J9 (D4) | B30 (SDA) |
| 카키 | J10 (D5) | B31 (SCL) |
| 추가① | A7 (3V3) | B33 (PWREN) |
| 추가② | C7 (3V3) | B34 (LPn) |

XIAO 배치 = D행/H행 5~11번(3V3 = D행 7열). 카테고리 2 핀 표의 SDA=D4(GPIO5)/SCL=D5(GPIO6)는 실측 일치 = SSoT 유지.

**(e) 진단 하네스 2종 (오늘의 방법론 산출)**
- **PR #32 `env:tof_pinscan`** (`06e671f`): XIAO GPIO 11개 × 순서쌍 110개 순회로 0x29 ACK 소프트웨어 탐색. 배선 1회 고정 + 플래시 1회로 수동 순회 대체.
- **PR #33 `env:tof_lineprobe`** (`601937d`): INPUT_PULLDOWN/PULLUP 5회 다수결로 외부 pull-up 검출 = **멀티미터 없이 전원·배선을 실측하는 수단** 확립. ★ **2회 대조 실험(SATEL 연결/분리) 설계가 "LOW 출처 = SATEL측" 격리의 결정타** → XIAO·브레드보드 결백 증명.

**(f) 소거된 원인 (전부 실측 기반)**

| 후보 | 판정 근거 |
|---|---|
| I2C 클럭 (1M/400k/100k) | 전 구간 동일 증상 |
| 센서 개체 불량 | 예비 센서(2장 중 2번째)도 동일 |
| 신호선 배선 | pinscan 110 순서쌍 전수 NONE FOUND |
| XIAO GPIO 점유(카메라/SD) | lineprobe 분리 대조로 반증. Seeed wiki상 D4/D5 자유핀 |
| SATEL 보드 결함 | 2장 동일 → 계통 원인(개체 결함 아님) |

**(g) ⚠️ 미결 — I2C 클럭 정책**: `firmware/include/tof_common.h` `TOF_I2C_FREQ_HZ`가 8/06 실험으로 1000000→400000 **미커밋 수정** 상태이며, 400kHz에서 15Hz 프레임 정상 동작 실측 확인. **본 문서 태스크는 코드 무변경** — 클럭 정책 확정(1MHz 복원 or 400kHz 정식 채택)은 **별도 코드 PR로 defer**.
  - ✅ **해소 (2026-08-08 PoC-(35), PR #34 `ecfe5a0`)**: `TOF_I2C_FREQ_HZ` 400000을 정식 커밋으로 확정. 근거 = 15Hz는 datasheet 8x8 mode 상한이라 1MHz 상향 시 프레임레이트 이득 0, 참조 구현 OnlyFeet도 400kHz 사용, 1MHz 실환경 검증은 실익 부재로 미수행. ※ 12①·14-2·16.1의 400kHz cross-ref는 2026-08-07 append 완료분(재수정 불요), 17.1 "I2C max 1 Mbits/s"는 datasheet 상한 서술이라 무접촉.

**(h) ⚠️ 미결 — Stage A/B 구현**: `tof_test.cpp`는 현재 프레임 카운트 로그만. 64 zone 순회 / `target_status` 5·9 valid 필터 / center 4 zone / zone count 임계값(카테고리 9 Stage A)은 TODO 주석 상태 — 별도 코드 태스크.
  - ✅ **Stage A 해소 (2026-08-08 PoC-(35), PR #34 `ecfe5a0` + PR #35 `af1fbf9`)**: 64 zone 순회 / `target_status` 5·9 valid 필터 / center 4 zone 평균(div-by-zero 가드) / zone count 임계값(8) 실코드화 + 연속 3프레임 대칭 디바운스 도입, ④런타임 검증 통과. 상세 = 9.2.
  - ⚠️ **Stage B 미결 유지**: Motion Indicator(`vl53l5cx_motion_indicator_init` 등) 실구현·④런타임 미착수. ~~`VL53L5CX_DISABLE_MOTION_INDICATOR` 매크로가 `.pio/libdeps/` 내부라 클린 빌드 시 원복되는 문제(재현 방법 확정 선행)는 `tof_test.cpp` 주석에 각인된 상태로 존치.~~
    - ✅ **무효 확정 (2026-08-12 PoC-(36)) — 매크로 원복 문제는 유령이었음**: Motion Indicator는 라이브러리 기본값으로 활성이며 매크로 패치는 불필요. 클린 빌드로 원복될 대상 자체가 없음. 본 미결 항목은 무효.
      - 근거 (전체 3개 ref 전수 확인 — 학습 13): ① `sparkfun/SparkFun_VL53L5CX_Arduino_Library`의 **v1.0.3 / main / master 3개 ref 모두** `src/platform.h:121`이 `// #define VL53L5CX_DISABLE_MOTION_INDICATOR`(주석 상태)로 배포 ② 로컬 파일 sha256 = `c061451cdd498746659cbb8e5519a930b5ab77a00298295d4e83f0ac63ce09d9` → 업스트림과 바이트 동일 = 무수정 확인 ③ `platform.h:118~121`은 옵션 disable 매크로 4종이 **전부 주석 상태**인 블록 = SparkFun 기본값이 전 기능 활성.
      - ★ **발원 ≠ 반영 분리**: 발원 = 2026-07-09 판정 B의 "매크로 주석처리로 컴파일 활성" 표현이 **관찰 서술**(이미 주석돼 있어 활성)인데 **행위 서술**(우리가 주석처리함)로 오독되어 2026-08-08에 "클린 빌드 원복 리스크"로 파생 / 반증·문서 반영 = 2026-08-12.
      - ★ **학습 21 신설 (2026-08-12)**: **미결 항목 자체가 유령일 수 있다 — 등재된 미결도 실물(코드·라이브러리·ref) 검증 대상**. 등재된 ⚠️ 미결이라고 존재를 전제하지 말고, 취소선 처리 전 실물로 재현 가능한지 먼저 확인. (SSoT 학습 번호: 18=PR 웹 머지 후 로컬 main pull / 19=근본원인 진단 재검증 / 20=원격 브랜치 `git ls-remote`(카테고리 20) / **21=미결도 유령일 수 있다**)
    - ✅ **실구현 착수 (2026-08-12 PoC-(36), PR #36 `84f2272`, 브랜치 `feat/firmware-tof-stage-b-1`, 3파일 +97줄)**: Stage B-1 **계측 계층**(관측 전용) 실코드화 + ④런타임 실측 완료 — 상세 = **9.3**. presence 판정 무융합·임계값 미하드코딩. (판정 융합·임계값 확정 = B-2 소관 미결)

### 9.2 Stage A ④런타임 검증 완료 (2026-08-08 PoC-(35) 신설)

PR #34(`ecfe5a0`, Stage A 실코드화 + I2C 400kHz 정식) → PR #35(`af1fbf9`, 연속 3프레임 대칭 디바운스)로 Stage A가 실코드화되고, 2026-08-08 학부생 로컬 ④런타임 실측을 통과했다.

**(a) 검증 결과**: 사람 1명 접근(2.9m→5.6cm) 전 구간에서 presence 상태 전환이 **정확히 1회**만 발생. 무인 기준선 near 0~2에서 전환 로그 0건. Stage A(zone count 임계) 로직 실효 확정.

**(b) 성공 로그 (verbatim 실측)**
```
presence: NONE -> DETECTED (near=13/64, center=1015mm, streak=3)
```
전환 직후 near가 13→9로 하락했음에도 DETECTED 유지 = **디바운스 실효 실증**(단일 프레임 하락으로 반전되지 않음).

**(c) 거리-near_count 실측 곡선** (사람 1명 접근, 8x8/15Hz/400kHz) — 본 문서 내 단일 수록 지점

| center | near |  | center | near |
|---|---|---|---|---|
| 2953mm | 0 |  | 869mm | 29 |
| 2918mm | 2 |  | 756mm | 30 |
| 1240mm | 0 |  | 634mm | 40 |
| 1196mm | 0 |  | 529mm | 51 |
| 1011mm | 10 |  | 431mm | 56 |
| 995mm | 9 |  |  |  |
| 972mm | 13 |  |  |  |

무인 기준선 = near 0~2 (시야 내 물체 제거 상태).

**(d) 임계값 8 타당성 (실측 근거 신설, 값 변경 없음)**: 1m 지점 사람 = near 9~13 / 무인 = 0~2 → 임계값 8이 양측에서 분리됨. ★ 세션 중 "8→20 상향" 안이 제기됐으나 근거 수치(near 37~55)가 실제로는 center 410~562mm(0.4~0.6m) 값이었음이 판명되어 **폐기** — 20 적용 시 1m 사람(near 9~13) 미검출 위험(**학습 19 실증 사례**).

**(e) 디바운스 N=3 결정 (PR #35)**: 확정 상태와 다른 raw 판정이 연속 3프레임이어야 전환(진입/이탈 **대칭**). 근거 = 15Hz에서 3프레임 ≈ 200ms, 실측 플리커는 전부 1~2프레임 폭이라 소거되고 200ms는 사람 인지 지연으로 무시 가능. 비대칭은 실측 근거 부재로 미도입. 임계 경계(약 1m 정지)에서 near가 7↔8 왕복하며 presence가 매 프레임 반전되던 플리커(PR #34 실측)를 소거.

**(f) ⚠️ Stage B는 여전히 ④런타임 미검증**: 본 절은 **Stage A 전용** 완료 보고. Motion Indicator(Stage B, 위 Stage B 절 + 9.1(h))는 실구현·런타임 미착수 — **"Stage A 완료"가 "ToF 사람 검증 완료"를 의미하지 않음**. Stage C/D(NanoEdge AI / Passing-by)도 미착수. ※ **2026-08-12 PoC-(36) 갱신**: Stage B-1 계측 계층은 ④런타임 실측 완료(9.3). 단 이는 **관측 전용**이며 presence 판정 융합은 여전히 B-2 미결 — "계측 완료 ≠ Stage B 판정 완료".

### 9.3 Stage B-1 Motion Indicator 계측 계층 ④런타임 실측 (2026-08-12 PoC-(36) 신설)

PR #36(`84f2272`, 브랜치 `feat/firmware-tof-stage-b-1`, 3파일 +97줄)로 Motion Indicator **계측 계층**(관측 전용, presence 판정 무융합·임계값 미하드코딩)을 실코드화하고, 2026-08-12 학부생 로컬 ④런타임 실측을 통과했다. **본 절은 계측(관측) 전용** — 판정 융합·임계값 확정은 B-2 소관(§9.3(F)).

**(a) 초기화 성공 로그 (verbatim 실측)**
```
[tof][StageB-1] motion indicator ready (8x8, 400~1500mm, 16 aggregates)
```
③컴파일 → ④런타임 통과. motion 감시창 400~1500mm는 ST 기본값.

**(b) 로그 필드 정의**: `g1`=global_indicator_1 / `ndet`=nb_of_detected_aggregates / `st`=status / `aggmax`=aggregate motion 최댓값. near·center 동반 출력(측정 조건 자동 부착).

**(c) 4종+ 대조 실측 결과표** (2026-08-12, 실내 책상 환경, 8x8/15Hz/I2C 400kHz)

| 상황 | near/64 | ndet/16 | aggmax |
|---|---|---|---|
| ① 무자극 기준선 (25프레임 연속) | 0 | 0 | 12~24 (스파이크 1회 37) |
| ② 정지 사물 1m (center≈1244~1339mm) | 10~11 | 0 | 14~22 |
| ③ 사람 1m 정지(체감) | 9~42 | 0 | 18~42 |
| ④ 사람 접근 스윕 (center 1144→264mm) | 10~64 | 1~5 | 45~544 |
| ⑤ 근접 자극 (center 249~253mm) | 31~34 | 6 | 114 |

**(d) ★ 핵심 결론 3건**
1. **Stage B 유효성 확정** — 정지 사물(ndet=0)과 접근하는 사람(ndet 1~6)이 완전히 분리. near로는 둘 다 임계값 8을 넘겨 구분 불가하나 motion으로는 갈림. = Stage B가 "선택"이 아니라 **"필수"**라는 판단이 실측으로 확인됨.
2. **정지한 사람은 정지 사물과 구분 불가** — ③이 ②와 동일하게 ndet=0. "가만히 서 있다"고 체감한 30초 동안 실제 center는 1069→805mm로 약 20cm 표류했으나 그 속도로는 motion이 뜨지 않음. 즉 motion 검출은 **속도 의존**.
3. **임계값 후보** = `ndet ≥ 1` 또는 ~~`aggmax ≥ 50` (노이즈 상한 37 / 사람 하한 45 사이)~~. ⚠️ **확정은 B-2 소관 — 본 절에서 확정 금지**.
   - **★ 산술 오기 정정 (2026-09-02 PoC-(38), PR #39 임계값 판정 과정에서 실측표 5행 전수 대조로 catch)**: 50은 45보다 커서 "37과 45 사이"가 아니다 — 실제 허용 구간은 **38~45**다. 이 값을 그대로 채택했다면 위 (c)표 ④(사람 접근 스윕, aggmax 하한 45)에서 **미탐**이 발생했을 것이다. ★ 이것은 **판단 오류가 아니라 산술 오기**다 — 후보를 제시한 판단 자체(motion 파생 지표로도 임계값을 잡아볼 수 있다는 방향성)는 유효했고, 구간 서술("37/45 사이")과 예시값("50")이 어긋난 것뿐이다. → 최종 채택값·기각 근거 3종은 **§9.4** 참조.

**(e) ★ 측정 환경 주의 (기존 원칙의 재실증)**: 첫 부팅 시 near=15/64, center=426mm로 기준선이 오염된 상태였고, 센서 지향 방향을 조정해 near=0/64를 확보한 뒤에야 유효 측정이 시작됨. ③컴파일과 ④런타임 사이의 **"측정 환경 유효성" 층**이 이번에도 작동(9.3(H) 재실증).

**(f) Stage A 회귀**: 임계값 8 / 디바운스 N=3 무변경 상태에서 정상 동작 확인(presence NONE↔DETECTED 전환이 streak=3으로 실동작).

**(F) Stage B-2 설계 방향 (수치 확정 아님 — 방향만 기록)**
- (d)-2로부터: **"현재 움직이는가"가 아니라 "최근 N초 안에 움직였는가"로 설계**해야 함.
- 논리 = 초인종을 누르는 사람은 반드시 걸어와서 누르므로 접근 과정에서 motion 발생. 반면 택배 상자는 놓인 뒤 영구히 movement 0. → motion 이벤트를 일정 시간 유지(**latch**)하는 구조 필요.
- **Stage A 디바운스와 방향이 반대**: A = "연속 N프레임 충족해야 인정" / B = "최근 N프레임 중 1회라도 검출되면 유지".
- ⚠️ N 값·latch 시간·임계값은 **전부 B-2 소관. 본 작업에서 수치 확정 금지**.

**(G) ⚠️ 미결 — 벽면 실사용 환경 정확도 미측정 (발견 2026-08-08 / 문서 반영 2026-08-12)**: 거리-near 곡선(9.2) 및 금일 motion 실측(본 절)은 모두 실내 책상/바닥 환경. **현관 부착 시 벽·문틀 반사 영향은 미측정** — 실사용 환경 정확도는 별도 실측 소관. ⚠️ 미결.

**(H) 환경 오염과 알고리즘 결함의 분리 원칙 (발견 2026-08-08 / 문서 반영 2026-08-12)**: Stage A 첫 실측의 전환 로그 도배는 **플리커가 아니라 센서 위 케이블을 15cm에서 감지한 것**이었음(center=118~175mm가 증거). → 무자극 기준선을 먼저 확보하고 조용해진 뒤 자극할 것. **③컴파일과 ④런타임 사이에 "측정 환경 유효성" 층이 하나 더 있음**(본 절 (e)로 재실증).

- **★ 하위 원칙 — "동일 위치 대조" (2026-09-02 등재, 사례 2건 / 근거유형 = 실측 2건 귀납)**: 대조군과 실험군은 **같은 자리·같은 조건**에 두어야 한다. 위치·거리·세기가 함께 변하면 관측 차이가 **어느 변수 탓인지 분리되지 않고**, 판정 자체가 성립하지 않는다. (H) 본문이 "환경 오염 vs 알고리즘 결함"의 분리라면, 본 하위 원칙은 그 앞단인 **자극 조건의 통제**를 다룬다.
  - **사례 ① 2026-08-12 ToF Stage B-1 (본 절)**: ②정지 사물과 ③사람을 **같은 위치**에 두어야 motion 차이와 위치(거리) 차이가 섞이지 않는다. 위치를 함께 바꾸면 near/center 변화가 "움직임 때문"인지 "더 가까워서"인지 분리 불가.
  - **사례 ② 2026-09-02 마이크 M4 (6.3(d))**: 같은 "박수" 자극인데 **거리·세기 조건이 통제되지 않아** 8/20 대비 **7.4배 약했다**(9/02 i16 max **2,928** vs 8/20 박수 환산 **18,099**). 그 결과 clip=0이 풀스케일 9% 조건의 값에 그쳐 **헤드룸 상한 검증이 불성립** = 조건 미통제가 판정을 무효화한 실증.
  - → **적용**: M5 등 후속 실측은 대조군(무자극)과 실험군(자극)을 **동일 마이크 위치·동일 거리·동일 세기 프로토콜**로 잡고, 조건을 바꿀 때는 **한 번에 한 변수만** 바꾼다.

**(I) 8/12 측정 로그 원본 = 미보존 확정 (2026-09-02 실측 판정, 데이터 손실 없음)**: 지침·인계 패키지에 3주간 등재돼 있던 "⏳ 미이관 TODO: 2026-08-12 Stage B-1 로그 → `tof_stage_b1_2026-08-12`"는 **이관 대기가 아니라 원본 부재**였다. 2026-09-02 실측 = `~/ddingdong-측정결과/`에 `tof_stage_b1_2026-08-12` **부재**(존재분 = `tof_bringup_2026-08-06_실패세션` / `tof_stage_a_2026-08-08` / `mic_m3_2026-08-20` / `mic_m4_2026-09-02` 등) + repo 내 `firmware/logs` **부재** + device-monitor 로그 **0건**. → 상태를 **"미이관 TODO" → "원본 미보존 확정"**으로 전환한다. ⚠️ 단 **데이터 손실 없음** — 4종+ 대조 실측표는 본 절 (c)에, 초기화 로그 verbatim은 (a)에 **decisions.md 본문 보존**돼 있어 재현·인용 가능. ★ **학습 21 계열**(등재된 미결 자체가 유령일 수 있다 — 여기서는 "할 일"이 아니라 "대상 부재"였음).

### 9.4 Stage B-2 판정 계층 확정 + ④런타임 실측 (2026-09-02 PoC-(38) 신설, PR #39 `a0953fb`)

9.3(F)에서 방향만 잡아두고 수치 확정을 보류했던 Stage B-2(motion 판정 + Stage A presence 융합)를 실코드화했다. **본 절은 판정 계층 확정** — 계측(관측)은 9.3 소관, 벽면 실사용 정확도는 여전히 미측정(9.3(G) 잔존).

**(a) 채택 임계값 = `TOF_MOTION_NDET_MIN = 1` 단독**

- **기각 근거 3종** (근거유형 = 논증, 9.3(c) 5행 실측표 대조):
  ① `aggmax ≥ 50`은 9.3(d)-3 정정에서 밝힌 **산술 모순**이 직접 사유 — 등재 근거 자체가 "37/45 사이"인데 50은 그 바깥.
  ② 산술 오기를 바로잡아도 실제 허용 구간(38~45)은 **폭이 좁고**, 그 안의 43·44는 9.3(c) 실측표에 값이 없어 **신규 창작**이 된다.
  ③ `aggmax`는 raw motion을 여러 단계 가공한 **파생 피크값**이라 사람이 임의로 경계를 박아야 하는 자리다 — 9.2에서 임계값 8→20 오판이 났던 바로 그 구조. `ndet`은 ST 디바이스 자체가 이미 "검출/비검출"로 판정한 값이라 그런 여지가 없다.
- **조합안(AND/OR) 기각**: AND는 두 조건 중 더 보수적인 쪽(=미탐 위험이 큰 쪽)을 그대로 상속. OR는 9.3(c) 실측표상 `ndet≥1`이 이미 잡는 행 이외에 **추가로 포착하는 행이 0건**이라 이득 없이 복잡도만 늘림.

**(b) latch 파라미터 = `TOF_MOTION_LATCH_FRAMES = 75`(15Hz × 5초)**

- 근거유형 = **논증**(실측 아님) — 9.3(c)에는 시간축(연속 프레임) 데이터가 없어 "5초"라는 값 자체는 설계 추론.
- 구조 = "최근 N프레임 중 1회라도 검출되면 유지"(이벤트 보존). Stage A 디바운스("연속 N프레임 충족해야 인정" = 노이즈 억제)와 **방향이 정반대**(9.3(F) 예고대로).

**(c) footprint (2안 실빌드 대조, `a0953fb` 커밋 로그 실측)**: RAM **20,124B — 순증 0**(latch를 `uint8_t`로 두어 달성) / Flash 372,777 → 373,013B(**+236B**).

**(d) ★ ④런타임 실측 (2026-09-02, 랩실, `~/ddingdong-측정결과/tof_stage_b2_2026-09-02/monitor.txt`, 182줄)**

- **latch 만료**: `#4621` `PERSON -> NONE (presence=DETECTED, latch=0/75)` — **근거유형 = 논증 → 실측 승격**. 설계값 75프레임(5.0초)에 대해 **≈4.9초 실측 일치**.
- **latch 붙잡기**: `#4291~#4351` 구간, StageB-1 `ndet=0/16` 연속인데도 fused는 `PERSON` 유지(직전 `#4281`에서 latch=75/75로 재충전된 뒤 `#4377`까지 유지).
- **AND 융합이 presence측에서 끊긴 사례**: `#3811` `#4377` `#4649` `#5020` — 전부 latch가 73~75/75로 아직 높은데도 fused가 `NONE`으로 전환. presence(Stage A)가 먼저 `NONE`으로 떨어져 AND가 끊긴 것 = motion latch가 아니라 presence측이 게이트가 된 사례.
- **재충전**: `#4648` `NONE -> PERSON (latch=75/75, ndet=1)`.

**(e) ⚠️ 미충족 항목 — 프로토콜 ②(정지 사물 대조) 미수행**: 9.3(H) 하위 원칙("동일 위치 대조")이 요구하는 3종 프로토콜 중 ②를 이번 ④런타임 세션에서 수행하지 못했다. 사유 = 센서 시야 가장자리 오염(near가 2~8/64로 상시 낮게 뜨고 center는 대부분 `n/a`)으로 유효한 대조군(정지 사물)을 확보하지 못함. → **본 절은 부분 충족**. Stage B-2 **구현·③컴파일·④런타임(사람 자극 경로) 완료 ≠ Stage B 검증 완료.**

**(f) ★ 위임 전제 오류 2건 (학습 19, 실코드 대조로 catch)**:
① `presence_state`는 `tof_common.cpp`가 아니라 `tof_test.cpp`의 `tofTask` 내부 `static bool`이다(`firmware/src/tof_test.cpp:67`).
② `motion_indicator`는 (B-1 로그 블록의) 15프레임 게이트 안에서만 읽히므로, B-2는 그 값을 재사용하지 않고 **매 프레임 독립적으로 다시 참조**한다(`firmware/src/tof_test.cpp:188`, B-1 블록 이동 없이 우회).

**관련**: 9.3(d)-3(산술 오기 정정) / 9.3(F)(방향 예고) / 9.3(H)(동일 위치 대조 원칙, 본 절 (e)가 부분 충족 사례) / 학습 19(위임 전제 재검증)

---

## 카테고리 10: Git Convention

- 모든 commit 메시지는 **한국어**로 작성
- 형식: `{이모지} {Type}: {한국어 설명}`
- 사용 가능한 Type 14종은 `docs/git-convention.md` 참조
- 예시: `✨ Feat: camera_test.cpp 골격 추가`

---

## 카테고리 11: 사전 준비 일정 (5/7~5/17, 11일, 옵션 A)

- 5/7 (목): 사전 검증 ①② + monorepo 셋업 ✅
- 5/8 (금): WiFi 더미 테스트 (Day 2 우선, 가장 위험)
- 5/9 (토): 카메라 단독
- 5/10 (일): 마이크 단독
- 5/11 (월): ToF 단독 + 최종 점검 + 5/15 검증 체크리스트
- 5/12 (화): 외부 계정 + self-checkpoint (코어 분배 재검토)
- 5/13 (수, Day 7): 졸작 중간 발표 (데모 시나리오 v1, 피드백 0건 → 카테고리 26 v1 확정) + AWS 가입 + 보안 4종 (35분) + 카카오 디벨로퍼스 셋업 (5/14 오전 11분, Day 7 통합 — 학부생 의도) → 외부 계정 셋업 완료, 카테고리 30 신설
- 5/14 (목): 호환성 추가 검증
- 5/15 (금): 부품 수령 + 결선
- 5/16 (토): 결선 마무리 + 1차 부팅
- 5/17 (일): 1차 부팅 + 5/18 준비

> 변경 사유: 사전 검증 ①②를 5/7 오전에 우선 배치 (코드 작성 전제조건). WiFi를 Day 2 우선 처리로 변경 (가장 위험한 작업 회복 시간 확보).

**5/17 이후 Day N 명명 폐기** (2026-05-25 학습 17 신규 발굴 근거):
- 사전 준비 11일 Day 1~Day 11 명명은 본 카테고리 11 본문에 한정 보존 (학습 8 원본 보존 패턴)
- 5/17 이후 외부 의존 가변 chunk 진입 시 Day N 명명 폐기 결정 (학부생 의도, 2026-05-25 PoC-(12) 본 작업)
- 폐기 사유: 학교 일정 / 부품 도착 / 외부 의존 chunk는 정량 일정 트래킹 불가능 → 학습 17 유도리 마인드 정합
- 신규 명명 패턴: 날짜 기반 ("5/25 (월)") + 학습 9 chunk 경계 정렬 + 학습 17 유도리 마인드
- 노션 DB1 row 제목 패턴 동시 전환 (Day 1~Day 8 보존, 5/25 row부터 날짜 명명)
- decisions-log.md entry 헤더 패턴 동시 전환 (2026-05-25 entry부터 날짜 명명)

---

## 카테고리 12: 사전 검증 결과

### ① VL53L5CX SparkFun lib + ESP32-S3 — 조건부 GO
- **4가지 워크어라운드**: I2C 1MHz / SATEL 모듈 / 단일 센서 / Adafruit_VL53L5 폴백
  - ※ 2026-08-07 실측: 브레드보드+20cm 점퍼 환경에서 **400kHz로 15Hz 프레임 정상 동작**. 1MHz 실환경 검증은 미수행 — 클럭 정책 확정은 별도 코드 PR (카테고리 9.1(g) 참조).
- **참고 코드**: https://github.com/susesKaninchen/OnlyFeet (XIAO Sense + 8x8/15Hz, 2026-05 활성)
- Arduino-ESP32 core 3.x + SparkFun lib 1.0.3 호환성 확인됨 (monorepo 셋업 시 자동 검증, 카테고리 16 참조)
- 시간 영향: +1h (5/11 ToF 코드)

### ② Lokch777 패턴 OV3660 멀티코어 — OV2640 포팅 추정 GO
- 실질 OV3660 멀티코어 사례 5건 (OnlyFeet 80% 매칭 + 4건)
- 5/9 카메라 코드 7가지 + build_flags 사전 반영 (카테고리 13)
- 5/21 코어 분배 잠정 안 (5/12 재검토, 카테고리 15)
- 시간 영향: +1h (5/21 PoC 통합)

---

## 카테고리 13: 5/9 카메라 코드 사전 반영 사항

```c
.xclk_freq_hz = 20000000          // Medium 권장
.fb_count = 2                     // dual buffer 필수
.fb_location = CAMERA_FB_IN_PSRAM
.grab_mode = CAMERA_GRAB_LATEST
.jpeg_quality = 12                // Medium 권장값, 화질-용량 균형
.pixel_format = PIXFORMAT_JPEG
.frame_size = FRAMESIZE_QVGA      // 또는 VGA
```

- `esp_camera_fb_return()` 후 `vTaskDelay(pdMS_TO_TICKS(30))` 필수
- 추가: 메모리 진단 코드 (PSRAM total/free, heap free, assertion)
- 참고: https://github.com/susesKaninchen/OnlyFeet/blob/main/src/main.cpp + Manjot Khangura Medium 글

---

## 카테고리 14: 5/11 ToF 코드 사전 반영 사항

1. `platformio.ini` `lib_deps` (이미 카테고리 16에 반영됨):
   - `sparkfun/SparkFun VL53L5CX Arduino Library` (메인)
   - `https://github.com/adafruit/Adafruit_VL53L5.git` (폴백)
2. `setup()`에 `Wire.setClock(1000000)` 명시
   - ※ 2026-08-07 실측: 브레드보드 환경 **400kHz로 15Hz 프레임 정상 동작**. 1MHz 실환경 미검증 — 클럭 정책 확정은 별도 코드 PR (카테고리 9.1(g) 참조).
3. 단일 센서 구성 (issue #5 회피)
4. SATEL 모듈 사용 (제네릭 모듈 init fail 회피)
5. 빌드 단계 즉시 검증: Arduino-ESP32 core 3.x 호환성 (이미 확인됨)

참고: https://github.com/susesKaninchen/OnlyFeet/blob/main/src/main.cpp

---

## 카테고리 15: 5/21 PoC 통합 코어 분배 잠정 안 (5/12 재검토)

```
Core 0:
  - micTask     (priority 4)
  - tofTask     (priority 3)

Core 1:
  - cameraTask  (priority 4)
  - wifiTask    (priority 3)   ← 별도 task로 분리 (cameraTask blocking 회피)
```

### 5/12 재검토 항목 (단독 테스트 결과 기반)
1. mic priority 5 vs 4 비교 (RMS 손실 발생 여부)
2. cameraTask 단독 vs writerTask 분리 시 fb_get 안정성
3. ToF 15Hz 유지율 (다른 task에 의해 누락되는지)

> **5/12 메모리 self-checkpoint 결과 (카테고리 17.1.1)**: 정적 SRAM 18.2% / Flash 31.6%, Plan B 미발동 → **메모리 측면 잠정안 유지 가능**. 타이밍 self-checkpoint (17.1.2) 결과 대기 (5/15+ 부품 도착 후).

---

## 카테고리 16: monorepo + PlatformIO 셋업 결과 (2026-05-07)

- **컴파일**: SUCCESS (14.25초, RAM 5.6% / Flash 7.6%)
- **platform**: `espressif32@7.0.0`
- **framework-arduinoespressif32**: `3.20017.241212` (Arduino-ESP32 core 3.x)
- **SparkFun VL53L5CX 1.0.3**: 호환성 확인 완료
- **Adafruit_VL53L5**: PlatformIO Registry 미등록 → GitHub URL 직접 사용 (master 브랜치)
- **PlatformIO CLI**: ~~`/tmp/pio-venv` (PEP 668 호환 venv)~~ → **`~/.platformio/penv` (표준 위치, 2026-06-22 PoC-(17) 정정)**
  - **학습 14 사례 (정적 기록의 재부팅 무효화)**: `/tmp/pio-venv`는 5/7 기록 시점엔 유효했으나 **`/tmp`는 재부팅 시 소실** → 6/22 부팅 검증 착수 시 penv 부재 catch. 공식 `get-platformio.py` 설치 스크립트로 `~/.platformio/penv`(표준 경로)에 PlatformIO Core **6.1.19** 복구 (system python 무수정). 정적 기록을 실측으로 정정 = 학습 14 그물 작동 사례 영구 반영.
- **Commit**: `6f1cecf` + `dd55759`
- **5/11 ToF 코드 작성 시 결정 사항**: Adafruit_VL53L5 master 추적 vs commit pin (master 추적 불안정 시 commit pin)
- **⚠️ env:poc `build_src_filter` blacklist 회귀 (2026-06-22 PoC-(17) catch)**: `[env:poc]`는 blacklist 방식(`+<*>` 후 camera만 제외)이라, **5/10 mic_test / 5/11 tof_test 추가 후 각자의 `setup()`/`loop()`가 poc 빌드에 흡수 → multiple definition 링크 충돌**. 5/8 이후 poc 미재빌드로 잠복하다 6/22 부팅 검증에서 발현. 1차 검증은 `PLATFORMIO_BUILD_SRC_FILTER` 환경변수 override로 mic/tof 제외 후 우회 빌드(파일 0 수정). ~~**근본 수정 = whitelist 통일 별도 위임 (카테고리 27.6 / DB3 등록 예정)**~~ → **✅ 정정 (해소 PR #4 `c4c8f47` / 발견 2026-09-02 세션 / 문서 반영 2026-09-02)**: 근본 수정은 **이미 완료돼 있었다**. 2026-09-02 `firmware/platformio.ini` 실물 조회 결과 **실존 env 9개 전부 whitelist**(`-<*>` 선행) — `poc` / `camera_v1` / `camera_v2` / `mic_dummy` / `tof_dummy` / `upload_spike` / `upload_spike_tls` / `tof_pinscan` / `tof_lineprobe`. "별도 위임 예정" 서술은 3개월간 잔존한 **stale**(27.6은 6/22 시점에 이미 ✅ 완료 기록). ★ **학습 21 3회차**(등재된 미결도 실물 검증 대상 — 8/12 매크로 유령 → 9/02 poc blacklist).

### 16.1 더미 테스트 누적 RAM/Flash 측정 결과 (2026-05-11 갱신)

PlatformIO env 분리 구조로 5/8~5/11 더미 테스트 결과 누적:

| 일자 | env | 작업 | RAM | Flash | 핵심 commit |
|------|-----|------|-----|-------|-------------|
| 2026-05-07 | (단일) | monorepo 초기 셋업 | 5.6% | 7.6% | `6f1cecf`, `dd55759` |
| 2026-05-08 | poc | WiFi + HTTPS 더미 | 13.8% | 25.8% | `3ec17d4` |
| 2026-05-09 | camera_v1 | 카메라 단독 (cameraTask) | 7.0% | 9.4% | `aa6116d`, `8ce56ed` |
| 2026-05-09 | camera_v2 | 카메라 분리 (writerTask) | 7.0% | 9.4% | `aa6116d`, `8ce56ed` |
| 2026-05-10 | mic_dummy | 마이크 단독 (INMP441 + I2S1) | 8.1% | 8.1% | `ff3f46b`, `eb1b451` |
| 2026-05-11 | tof_dummy | ToF 단독 (VL53L5CX + I2C) | 6.1% | 11.1% | `b2434af`, `dd8ed66` |

**5/10 mic_dummy 부연**:
- 라이브러리: legacy `driver/i2s.h` (arduino-esp32 v3.20017 SDK packaging 제약, 카테고리 28 학습 15 참조)
- 정적 메모리: `audio_buffer` + `scratch` = 8 KiB BSS (DMA 32-bit mono × 1024 frames × 2 buffer 정적 할당, 카테고리 29 학습 16 참조)
- INMP441 250ms 파워업 노이즈 처리 + 14 DMA buffers 폐기 (datasheet 2^18 SCK cycles ≈ 256ms 일치)

**5/11 tof_dummy 부연**:
- 라이브러리: SparkFun_VL53L5CX_Arduino_Library 1.0.3 (1차) + Adafruit_VL53L5 master (폴백, lib_deps만 등록 dead code elimination)
- 메모리: mic 대비 RAM ↓ (I2S DMA 4 KiB 부재) / Flash ↑ (VL53L5CX FW upload buffer ~86KB 포함)
- I2C 1MHz / 8x8 64 zones / 15Hz (datasheet 8x8 mode max, SparkFun Example3 검증 패턴)
  - ※ 2026-08-07 실측: 브레드보드+20cm 점퍼 환경 **400kHz로 15Hz 프레임 정상 동작**. 1MHz 실환경 미검증 — 클럭 정책 확정은 별도 코드 PR (카테고리 9.1(g) 참조).
- graceful: `initToF()` 실패 시 task spawn 생략 → `loop()` idle 진단만 (mic_test 패턴 100% 일치)
- 학습 13 catch 33개 / 학습 14 mic 컨벤션 100% 일치 / 학습 15 단계 4 (런타임) 5/15+ 보류

**env 분리 구조 (build_src_filter)**:
- `env:poc` — WiFi 더미 테스트 (5/8 본 작업)
- `env:camera_v1` — Version A (cameraTask 단독)
- `env:camera_v2` — Version B (writerTask 분리)
- `env:mic_dummy` — 마이크 단독 (5/10 신규)
- `env:tof_dummy` — ToF 단독 (5/11 신규)

**5/12 메모리 self-checkpoint 입력 데이터 (정적 budget)**:
- 320KB SRAM 한계 / 3.34MB Flash 한계 / 8MB PSRAM 한계
- 5/8 사전 추정: SRAM 22% / Flash 42% / PSRAM 50KB (~0.6%) — **5/12 실측으로 정정됨**
- 5/12 실측 (방법 1 delta sum, 카테고리 17.1.1.1): SRAM **18.2%** / Flash **31.6%** / PSRAM 50KB — Plan B 미발동 (카테고리 17.1.1.2 Stage 1 임계값 25%/40% 안전 여유)
- **동적 heap 측정 (`ESP.getMinFreeHeap()` + stack high-water mark)** 은 **11주차 통합 테스트로 분리** (카테고리 17 별도 검증 항목 참조)

---

## 카테고리 17: 별도 검증 항목

- **11주차 진입 전** esp32-camera issue #620 (WiFi join 후 fb_get fail) 재현 시도
  - 워크어라운드 후보: `fb_count=3` / WiFi power save 비활성화 / init 순서 변경
  - URL: https://github.com/espressif/esp32-camera/issues/620
  - **동적 heap 추적 (`ESP.getMinFreeHeap()` + stack high-water mark) 동시 진행** (2026-05-09 추가, SRAM 동적 소비 분석)
- **5/12 self-checkpoint**: 단독 테스트 4개 종합 → 5/21 통합 코어 분배 최종 확정 (카테고리 15)
  - **2026-05-08 갱신**: 자성리얼 부품 배송 일정 변경(카테고리 22.6, commit `847c599`) 카스케이드로 self-checkpoint 분리. 17.1 참조.

### 17.1 self-checkpoint 분리 (2026-05-08 갱신)

자성리얼 부품 배송 일정 변경(5/15~5/28)으로 5/9~5/11 실측 데이터 수집 불가. 단, 5/8 WiFi 테스트와 동일한 "더미 테스트" 패턴(컴파일 + 메모리 사용량)은 부품 없이 진행 가능. self-checkpoint 입력 데이터를 메모리(부품 X 가능) + 타이밍(부품 필요)으로 분리.

#### 17.1.1 메모리 self-checkpoint (5/12 진행, 부품 X)

- **진행 시점**: 5/12 (5/9~5/11 더미 테스트 직후)
- **입력 데이터**: 5/9~5/11 더미 테스트 컴파일 결과
  - WiFi 더미 테스트 (5/8 commit `3ec17d4`): RAM 13.8% / Flash 25.8% ✅
  - 카메라 더미 테스트 v1/v2 (5/9 commit `aa6116d` + `8ce56ed`): RAM 7.0% / Flash 9.4% ✅
  - 마이크 더미 테스트 (5/10 commit `eb1b451`): RAM 8.1% / Flash 8.1% ✅
  - ToF 더미 테스트 (5/11 commit `dd8ed66`): RAM 6.1% / Flash 11.1% ✅
- **검증 범위**: **정적 budget 검증 한정** (컴파일 시점 측정값)
- **동적 heap 측정 (런타임)** 은 11주차 통합 테스트로 분리 (카테고리 17 참조)
- **검증 항목**:
  - PSRAM 8MB 한계 안에 들어오는지
  - 통합 시 메모리 fragmentation 위험 평가
  - 카메라 frame buffer + I2S DMA 버퍼 + ToF zone 데이터 동시 보유 가능성
- **산출물**: 통합 메모리 budget 표 (카메라 + 마이크 + ToF + WiFi 합산)

##### 17.1.1.1 통합 budget 추정 결과 (2026-05-12 갱신)

**산출 방법** — 방법 1 (delta sum, 채택) + 방법 2 (단순 합산, 참고):

| 일자 | env | RAM | Flash | RAM delta (vs baseline) | Flash delta (vs baseline) |
|------|-----|-----|-------|-------------------------|----------------------------|
| 2026-05-07 | (단일 baseline) | 5.6% | 7.6% | — | — |
| 2026-05-08 | poc (WiFi+HTTPS) | 13.8% | 25.8% | +8.2pp | +18.2pp |
| 2026-05-09 | camera_v2 | 7.0% | 9.4% | +1.4pp | +1.8pp |
| 2026-05-10 | mic_dummy | 8.1% | 8.1% | +2.5pp | +0.5pp |
| 2026-05-11 | tof_dummy | 6.1% | 11.1% | +0.5pp | +3.5pp |

> 베이스라인 정의: 5/7 monorepo 셋업 시 단일 env (Arduino core + FreeRTOS + Serial + USB CDC + nvs_flash 등 공통 부분)

**방법 1 — delta sum (정적 추정 채택)**:
- RAM = baseline + Σ(delta) = 5.6 + 8.2 + 1.4 + 2.5 + 0.5 = **18.2%** (~59,640 bytes / 320 KiB)
- Flash = baseline + Σ(delta) = 7.6 + 18.2 + 1.8 + 0.5 + 3.5 = **31.6%** (~1,056,178 bytes / 3.34 MB)
- 근거: 베이스라인은 모든 env에 공통 포함 → 1회만 카운트, 페리페럴별 delta는 중복 없이 가산

**방법 2 — 단순 합산 (참고용, 베이스라인 4× 중복)**:
- RAM: 13.8 + 7.0 + 8.1 + 6.1 = **35.0%** (Σ env, 베이스라인 4중 카운트)
- Flash: 25.8 + 9.4 + 8.1 + 11.1 = **54.4%** (Σ env, 베이스라인 4중 카운트)
- 한계: 통합 binary는 단일 baseline + 페리페럴별 코드 → 방법 2는 over-count

**페리페럴별 정적 contribution (방법 1 delta 분해)**:

| 페리페럴 | RAM delta | Flash delta | PSRAM | 출처 / 근거 |
|---------|-----------|-------------|-------|-------------|
| WiFi/HTTPS | +8.2pp (~26.9 KB) | +18.2pp (~608 KB) | 0 | esp_wifi.a + lwIP + wpa_supplicant + mbedtls (HTTPS) + WiFiClientSecure + HTTPClient + ArduinoJson. arduino-esp32 v3.20017 issue #5990·#9741 (WIFI_STA 진입 시 ~45KB heap 점유 패턴 일치) |
| 카메라 OV2640/OV3660 | +1.4pp (~4.6 KB) | +1.8pp (~60 KB) | runtime fb (별도) | esp_camera v2.1.2 driver + 센서 테이블. frame buffer는 `fb_location=CAMERA_FB_IN_PSRAM`으로 PSRAM 점유 (카테고리 13) |
| 마이크 INMP441 | +2.5pp (~8.2 KB) | +0.5pp (~17 KB) | 0 | legacy `driver/i2s.h` (카테고리 28 학습 15) + `audio_buffer + scratch = 8 KiB BSS` (32-bit × 1024 frames × 2 buffer 정적 할당, 카테고리 16.1 5/10 부연 일치) |
| ToF VL53L5CX | +0.5pp (~1.6 KB) | +3.5pp (~117 KB) | 0 | SparkFun_VL53L5CX_Arduino_Library 1.0.3 + Wire. RAM = `VL53L5CX_ResultsData ~1356B BSS` (카테고리 16.1 5/11 부연 일치). Flash 117KB ⊃ FW upload buffer ~84KB (UM2884 — 매 power-on 마다 host MCU가 I2C로 upload, RAM-based sensor) |

**PSRAM 활용 분석**:
- 카메라 frame buffer 한정: QVGA JPEG `fb_count=2` × `jpeg_quality=12` + line buffer + DMA descriptor → 약 50 KB 추정 (5/8 사전 추정 보존)
- 다른 페리페럴(WiFi/Mic/ToF): PSRAM 점유 0
- PSRAM 점유율: 50/8192 = **0.6%** — 8MB 한계 대비 매우 여유

**통합 추정값 (정적, 동적 별도)**:

| 자원 | 정적 추정 (5/12) | 동적 한계 (11주차 측정 예정, 추정치) | ESP32-S3 한계 |
|------|-----------------|----------------------------------|----------------|
| SRAM (BSS+DATA) | 18.2% (~59.6 KB) | + α (런타임 heap, 추정 +30~50% peak) | **320 KB** (arduino-esp32 user-available, datasheet 512KB 중 ROM/cache 점유 제외) |
| Flash | 31.6% (~1.06 MB) | (정적 한정, 동적 Flash X) | **3.34 MB** (default partition table) / 8 MB physical |
| PSRAM | ~50 KB (0.6%) | + α (카메라 동적 alloc 시 frame queue 변동) | **8 MB** (XIAO ESP32-S3 Sense) |

**5/8 PoC-(5) 사전 추정과의 차이 (정정 분석)**:

| 자원 | 사전 추정 (5/8) | 갱신 결과 (5/12) | 차이 | 정정 사유 |
|------|----------------|-----------------|------|-----------|
| SRAM | 22% | 18.2% | **-3.8pp** | mic delta 사전 +5% 가정 → 실측 +2.5pp / tof delta 사전 +3% 가정 → 실측 +0.5pp |
| Flash | 42% | 31.6% | **-10.4pp** | tof FW image 사전 +6%(~200KB) 가정 → 실측 +3.5pp(~117KB, FW 84KB + driver) |
| PSRAM | 50 KB | 50 KB | 0 | 카메라 frame buffer만 PSRAM 점유, 사전 추정 일치 |

→ **실측 결과 모두 사전 추정 안에 안전 수렴**. Plan B 트리거 미발동.

##### 17.1.1.2 Plan B 트리거 정량화 (2026-05-12 신설)

**임계값 산정 근거** (학습 16 적용 — 위임 프롬프트 일반론 30/50/70% 대신 ESP32-S3 한계 + 동적 마진 기반 재산정):

- ESP32-S3 user-available SRAM 320 KB (datasheet 출처)
- 정적 18.2% + 동적 typical 30~50% peak = peak 50~70% (WiFi + Camera 동시 활성 사례 기준)
- WiFi peak 동적 점유 ~80 KB (TLS handshake + lwIP TX/RX + HTTPClient body, arduino-esp32 issue #5990·#5630 패턴 인용)
- Camera I2S DMA + line buffer ~16 KB IRAM (frame buffer는 PSRAM)
- 4 task stacks ~16-32 KB
- Heap fragmentation 안전 마진 ~30-40 KB

| Stage | 트리거 조건 (정적 분석 기반) | 대응 |
|-------|------------------------------|------|
| **Stage 1** (알람) | 정적 SRAM ≥ **25%** OR 정적 Flash ≥ **40%** | 알람만, 작업 계속. `ESP.getMinFreeHeap()` + stack high-water mark 동적 측정 권장 (11주차 정식 항목, 카테고리 17) |
| **Stage 2** (최적화) | 정적 SRAM ≥ **35%** OR 정적 Flash ≥ **60%** | 최적화 검토. 후보: mic DMA buffer 8→4 (4 KiB BSS 절감) / VL53L5CX FW를 PSRAM 이전 (Flash ~84KB 절감) / WiFi sdkconfig minimal / HTTPS RX buffer 축소 |
| **Stage 3** (Plan B) | 정적 SRAM ≥ **50%** OR 정적 Flash ≥ **75%** | Plan B 발동. 후보: 카메라 QVGA → CIF / ToF 8x8 → 4x4 모드 (RAM ¼ 절감) / Adafruit_VL53L5 폴백 제거 / WiFi → ESP-NOW 대체 (lwIP/mbedtls 제외) |

> **현 상태 (5/12)**: 정적 SRAM 18.2% / Flash 31.6% — **모든 Stage 미발동** (Stage 1 임계값 25% / 40% 안전 여유)

##### 17.1.1.3 분석 근거 출처 (catch 24개 항목)

1. **ESP32-S3 datasheet** (5개): 512 KB on-chip SRAM (user-available 320 KB) / 8MB·16MB·32MB Flash 옵션 / 8MB·16MB PSRAM 옵션 / dual-core LX7 @ 240MHz / WiFi 802.11 b/g/n + BT 5 LE 통합 — Espressif ESP32-S3 Datasheet v2.2 (`espressif.com`)
2. **arduino-esp32 v3.20017** (4개): WIFI_STA 진입 시 ~45KB heap 점유 (issue #5990) / WiFi.h include만 ~500KB Flash (issue #9741) / MIN free heap 60-90KB peak / framework-arduinoespressif32@3.20017.241212 (카테고리 16)
3. **ESP-IDF heap_caps** (3개): `MALLOC_CAP_8BIT` / `MALLOC_CAP_DMA` (internal SRAM 한정) / `MALLOC_CAP_SPIRAM` 분리 — `heap_caps_get_free_size()` API 노출 (학습 15 검증)
4. **esp_camera 패턴** (4개): `fb_count` 다중 시 continuous mode (double-speed) / `CAMERA_FB_IN_PSRAM` (default high-res) / `CAMERA_FB_IN_DRAM` 옵션 (PSRAM 부재 시) / esp32-camera v2.1.2 ESP Component Registry / WiFi join 후 fb_get fail (issue #620, 카테고리 17 11주차 항목)
5. **legacy driver/i2s.h DMA** (3개): arduino-esp32 v3.20017 packaging `i2s_std.h` 미노출 (카테고리 28 학습 15 일치) / DMA buffer 정적 할당 패턴 (mic_dummy 8 KiB BSS) / I2S0/I2S1 controller 분리 (ESP32-S3 dual)
6. **VL53L5CX** (5개): FW upload ~84 KB (UM2884) / 매 power-on마다 I2C upload / RAM-based sensor (internal flash 없음) / I2C max 1 Mbits/s (datasheet) / ULD driver `/VL53L5CX_ULD_API` (SparkFun 1.0.3 = ULD 1.3.x 기반)

※ **용어 주석 (2026-09-02 부착)**: 위 항목 2·5의 **"arduino-esp32 v3.20017"**은 **PIO 패키지 버전 문자열**(`framework-arduinoespressif32@3.20017.241212`)이며 **core 3.x가 아니다** — 실제 core = **Arduino-ESP32 2.0.17**(카테고리 6.2 "2026-07-29 실측 정합 주석" 참조, 레거시 `driver/i2s.h` 의존이 2.0.x 근거). 원문은 5/12 당시 출처 표기 그대로 **보존**하고 상호 참조만 부착. ※ `mic_common.h`의 동일 오독은 PR #37에서 코드측 정정 완료.

##### 17.1.1.4 한계

- **정적 분석 한정**: BSS + DATA + Flash 컴파일 시점 측정. 동적 heap fragmentation / 런타임 peak / task stack high-water mark 미반영
- **동적 heap 측정** (`ESP.getMinFreeHeap()` + `uxTaskGetStackHighWaterMark()`): 부품 도착 후(5/15+) 또는 11주차 통합 테스트로 분리 (카테고리 17)
- **페리페럴 동시 활성 fragmentation**: PoC 1주차 통합 시 실측 (5/21 시점, 카테고리 15·17.1.3)
- **Plan B 임계값**: 정적 분석 기반 1차 추정 — 동적 측정 후 (11주차) 재조정 가능
- **WiFi 동적 추정 80 KB**: arduino-esp32 일반 패턴 인용, 본 프로젝트 HTTPClient + ArduinoJson 7.x 조합 실측 미진행

#### 17.1.2 타이밍 self-checkpoint (부품 도착 + 실측 후)

- **진행 시점**: 부품 도착 + 단독 실측 완료 후 (잠정 5/18+, 부품 도착 시점 따라 가변)
- **입력 데이터**: 실측 데이터 3종 (카테고리 15 "5/12 재검토 항목" 원본 보존)
  1. mic priority 5 vs 4 비교 (RMS 손실 발생 여부)
  2. cameraTask 단독 vs writerTask 분리 시 fb_get 안정성
  3. ToF 15Hz 유지율 (다른 task에 의해 누락되는지)
- **검증 항목**: 코어 분배 잠정안(Core 0 = mic + tof / Core 1 = camera + wifi) 유효성
- **산출물**: 코어 분배 최종안 (또는 잠정안 수정안)

#### 17.1.3 5/21 통합 코어 분배 최종 확정 시점 영향

- 메모리 self-checkpoint(5/12) + 타이밍 self-checkpoint(부품 도착 후) 모두 완료 후 진행
- **5/12 메모리 self-checkpoint 결과 (카테고리 17.1.1)**: SRAM 18.2% / Flash 31.6%, Plan B 미발동 → 메모리 측면 잠정안 유지 가능
- 부품 도착 시점에 따라 자연 연기 가능성:
  - **최단 (5/15 도착)**: 5/18 타이밍 self-checkpoint → 5/21 가능 (PoC 1주차 진행 중)
  - **중간/최장 (5/22~5/28 도착)**: PoC 1주차 진입 후 처리 → Plan B 다단계 트리거 검토와 연결
- PoC 1주차 진행 상황 보면서 재평가 (5/21 시점 변경 X, 시점은 잠정 유지)

> 학부생 의사결정: **옵션 A** (PoC-(5), 2026-05-08). 카테고리 15 "5/12 재검토 항목" 원본 보존, 본 17.1이 분리 정의로 추가.

---

## 카테고리 18: 채팅방 운영 구조

### SSoT 우선순위
1. **GitHub repo (decisions.md / decisions-log.md)** — 최상위
2. 의사결정 채팅방 (PoC-(2) / 후속 채팅방, 도메인별 분리)
3. 도메인 위임 프롬프트 생성기 채팅방 (직접 코드 X)
4. Claude Code MCP (실제 작업 수행)
5. 노션 PoC 트래킹 (사람용 VIEW)

### 작업 체인
```
[의사결정 채팅방] ↔ [도메인 위임 생성기] → [Claude Code MCP] → [GitHub + 노션]
```

### Claude Code MCP 활용 원칙
1. `find-skills` MCP로 적합 skill 탐색 먼저 (강제)
2. skill 발견 시 → skill + 관련 MCP 조합
3. skill 없으면 → MCP 단독 수행 (검색 절차 절대 생략 X)
4. 활용 MCP: `github` / `context7` / `firecrawl-mcp` / `playwright` / `notion`

### github MCP write 인증 이슈 (2026-06-29 PoC-(19) catch)

- **현상**: MCP "connected" 상태여도 write(PR 생성·파일 push 등) 시 `Bad credentials` 발생 가능 — **MCP 연결 ≠ GitHub PAT 유효**.
- **트리거**: 다음 write 작업에서 `Bad credentials` 재현 시 → GitHub PAT 재발급.
- **우회**: git 자체 명령(`git push origin main` 등)으로 대체. 문서 단독 변경은 main 직 push라 git-native로 무손실 대체 가능(카테고리 20).

### 채팅방 분리 트리거
- **시점 기반**: chunk 종료 시점
- **컨텍스트 무게 기반**: 응답 느려지거나 헷갈림
- **사건 기반**: 큰 의사결정 후

### 인계 패키지 형식
```
# [채팅방 이름] 인계 패키지
## 🔗 SSoT
## ✅ 직전 채팅방 완료 사항 (5~7개)
## 🚧 진행 중 / 미결 사항 (3~5개)
## ⏸️ 다음 채팅방의 첫 액션 (1~3개)
## 🚨 미결정 / 보류 사항
## 📌 작업 원칙
```

### 컨텍스트 무게 자체 모니터링 (2026-05-07 추가)

클로드(의사결정 채팅방)가 학부생이 먼저 묻기 전에 능동적으로 채팅방 분리 제안.

**무거움 신호 8가지:**
1. 응답 텀 길어짐
2. 이전 결정 재확인 빈도 증가
3. 동일 주제 반복 질문
4. 컨텍스트 윈도우 한계 근접 추정
5. 한 채팅방에 도메인 4개+ 누적
6. 큰 의사결정 후 chunk 종료 시점 도래
7. **일자 전환** (자정 넘어 작업 일자 바뀜 → 새 chunk 경계) *(2026-07-06 지침 싱크 append — 지침 8개 대비 decisions.md 6개 뒤처짐 정정)*
8. **패턴 전환** (작업 도메인·모드 급전환 = 문서↔코드, ML↔대시보드 등) *(2026-07-06 지침 싱크 append)*

**알림 형식:**
```
⚠️ 컨텍스트 무게 알림
🔍 감지 신호: [구체적 신호]
📊 현재 무게 추정: [경량/중간/무거움/매우 무거움]
🎯 분리 추천 시점: [지금 즉시 / 특정 시점 / 모니터링 지속]
📦 인계 패키지 준비 가능: YES/NO
💬 학부생 결정 필요
```

학부생 결정: 분리 진행 / 분리 보류 / 무시 (보류·무시 시에도 신호 누적 추적 계속)

---

## 카테고리 19: 노션 PoC 트래킹

- **위치**: 노션 워크스페이스 "청각 장애인용 초인종" → "킥" 하위에 "띵동(Ddingdong) PoC 트래킹" 페이지
- **도입 일자**: 2026-05-07
- **갱신 주기**: 매일 작업 종료 시
- **갱신 방식**: Claude Code MCP에 위임 프롬프트 제공
- **SSoT 아님** (VIEW), GitHub `decisions.md`와 충돌 시 **GitHub 우선**
- **의사결정은 절대 노션에서 X**

### 셋업 완료 결과 (2026-05-07)

- 페이지 1개 + 데이터베이스 3개 (가독성 6원칙 통과)
- 노션 페이지 ID: `359d8df0-3cab-816a-aedb-ec6341cc135e`
- DB1 (일자별 진행 로그) ID: `62a11105-c858-4eff-a151-268f3ffc4c9f`
- DB2 (사전 검증 결과) ID: `e9697017-4372-4253-8aac-ae4b4f391fd6`
- DB3 (미결정 항목) ID: `a319c04a-9201-417f-8552-7d6e99b2958f`

### Velog 분리 운영 (2026-05-07 추가)

- Velog 발행 기록은 학부생이 별도 노션 페이지에서 관리
- PoC 트래킹의 외부 링크에 Velog 시리즈 URL은 참고용으로 유지
- 매일 밤 루틴의 노션 갱신 위임 프롬프트 작성 시 Velog 관련 갱신 (발행 사실, Entry 번호, URL) 포함 금지
- PoC 트래킹은 개발 진행 트래킹 전용

### 노션 plan 게이트 정정 (2026-07-06 PoC-(22) Set 3 실측)

- **당초 우려**: 노션 워크스페이스가 Business plan API 게이트로 DB row 열람·갱신 차단 → hand-mirror(수기 반영) 필요 추정.
- **실측 정정**: ~~`notion-query-data-sources`(SQL 쿼리)만 Business plan 차단.~~ **`notion-search` + `notion-fetch`(by-ID)로 DB row 실 열람·특정 갱신은 우회 가능** → hand-mirror 불필요. DB3(미결정 항목, `a319c04a-9201-417f-8552-7d6e99b2958f`) 3출처 오염 상태에서도 by-ID fetch로 특정 row 접근 확인.
  - ✅ **정정 (2026-08-07 PoC-(34) Set 3 실측 발견 → 2026-08-08 PoC-(35) 문서 반영)**: 단일 data source 대상 `notion-query-data-sources` SQL 전수 스캔이 **정상 작동**함을 실측(DB3 42행 전수 조회, `has_more:false`) → "SQL만 Business plan 차단" 서술은 해소. **멀티 data source 조인 쿼리만 잔여 제약**. ★ 발견일(2026-08-07 실측 — 당시 프로젝트 지침·인계 패키지엔 반영됐으나 decisions.md만 미반영 = SSoT 역방향 stale) ≠ 문서 반영일(2026-08-08 세션 초 3소스 대조에서 catch).
- ※ 갱신 후 `notion-update-content`는 old_str 불일치 시에도 silent success(no-op) 가능 → **편집 후 re-fetch 검증 필수**.

---

## 카테고리 20: Git 워크플로우 (5/18 도입 예정)

### 사전 준비 단계 (~5/17)
- main 직 push 유지

### PoC 1주차 ~ 본격 개발 (5/18~)
- **GitHub Flow 단순화 모델** 도입
- **브랜치 명명**: `feat/{domain}-{task}` (firmware/ml/server/dashboard/fix)
- **main 보호 룰**: PR을 통해서만 머지
- **Squash merge** 기본
- **PR 머지 조건**: 컴파일 통과 + 한국어/이모지 commit + 금지 파일 미수정 + self-approve
- **Claude Code MCP 자동 처리**: 브랜치 생성 + 작업 + push + PR 생성
- **학부생**: PR 리뷰 + 머지

### 문서/코드 변경 push 분리 (2026-05-28 명문화)
- **문서 단독 변경** (`docs/*.md` — decisions.md / decisions-log.md / git-convention.md 등): **main 직접 push 허용** (PR 불필요)
- **코드 변경** (`firmware/` / `dashboard/` / `ml/` / `server/`): **feat 브랜치 + PR 강제**
- 근거: PR 목적 = 코드 품질 catch (컴파일 / 리뷰). 문서는 충돌·리뷰 불필요 → SSoT 갱신 지연 방지
- **Squash merge 기본 유지** (완화 X). ※ PR #1(2026-05-28)은 merge commit으로 머지된 1회성 예외 — repo Settings에서 Squash merging 활성화 후 복구 예정 (decisions-log 2026-05-28 참조)

### PR 웹 머지 후 로컬 main 동기화 필수 (2026-06-29 학습 18 신설)

학습 18 (PR 웹 머지 후 로컬 main 동기화 필수): GitHub 웹에서 PR squash 머지 시 remote main에 새 해시 커밋 생성 → 로컬 main 미반영. 다음 feature 브랜치 따기 전 `git checkout main && git pull origin main` 강제. 누락 시 squash로 사라진 원본 커밋 위에서 브랜치가 갈라져 다음 PR이 이전 PR 커밋을 끌고 감(2026-06-29 PR #6 = PR #5 strict 커밋 끌려옴 + merge commit 생성 사례). "git pull 폐지" 룰(동일 로컬 머신)의 명시적 예외 = PR 웹 머지 직후. 정상 복구 = fast-forward pull(rewrite 0).

### 원격 브랜치 실존은 `git ls-remote origin` (2026-08-08 학습 20 신설, 문서 반영 2026-08-12)

학습 20 (원격 브랜치는 `git ls-remote origin`으로 확인): 브랜치 삭제/정리 전 catch는 `git branch -r`(**스테일 로컬 추적 캐시**)이 아니라 `git ls-remote origin`(**진짜 origin 상태**)로 해야 함. `git branch -r`은 마지막 fetch 시점의 캐시라 이미 삭제된 원격 브랜치를 살아있는 것처럼 보이게 함 → `git remote prune origin`으로 stale 추적 ref 정리. `refs/pull/N/head`는 **닫힌 PR 아카이브라 삭제 대상 아님**(GitHub이 유지). 대량 불일치 catch 시 §9(임의 진행 금지, 사용자 판단 요청). **발견 = 2026-08-08 PoC-(35) 세션 / 문서 반영 = 2026-08-12 PoC-(36)** — 지침·인계 패키지엔 반영됐으나 decisions.md만 미등재였던 **SSoT 역방향 stale**. ★ 학습 18·19는 이미 등재돼 있으나 20만 부재 상태였음 → 학습 번호 SSoT 부재가 번호 혼동 재발의 원인이므로 정의와 함께 등재. (SSoT 학습 번호: 18=PR 웹 머지 후 로컬 main pull / 19=근본원인 진단 재검증 / **20=원격 브랜치 ls-remote** / 21=미결도 유령일 수 있다(9.1(h)))

### 관측/판정 계층 PR 단위 분리 — "계측 → 실측 → 판정" (2026-09-02 등재, ~~2회 실증~~ → **3회 실증**(2026-09-03 PoC-(39) [J-확정]))

센서·신호 계열 기능은 **한 PR에 계측과 판정을 섞지 않는다.** ① **계측 PR** = 관측 전용(통계·로그만, 변환·판정 0줄, 임계값 미하드코딩) → ② **④런타임 실측**으로 실제 수치 확보 → ③ **판정 PR** = 확보된 수치를 근거로 변환·임계값 확정. 근거 = 판정을 먼저 코드에 박으면 **실측 전에 임계값을 추정으로 고정**하게 되고, 실측 후 되돌릴 때 계측 코드까지 함께 흔들려 무엇이 원인인지 분리 불가해진다. ~~**실증 2회** — (1) 2026-08-12 ToF Stage B-1: PR #36 계측 계층 → ④런타임 실측(9.3) → 임계값 확정은 B-2로 분리. **B-2는 2026-09-02 PR #39로 완료됨**(9.4) — (1) 사례는 계측→실측→판정 3단계가 **PR #36→PR #39로 전부 완주**된 것으로 갱신한다(발견·문서 반영 = 2026-09-03 PoC-(39)). ⚠️ 총 실증 횟수("실증 2회") 표기 변경 여부(PR #34→#35 ToF Stage A 디바운스를 별도 3번째 실증으로 셀지)는 **사용자 판단 보류** — 임의 변경 금지. (2) 2026-09-02 마이크: PR #37 raw int32 계측 → M3 ④런타임(tz=6 실측) → PR #38 `>>14` 판정(6.3). 두 경우 모두 **실측값이 사전 추정을 뒤집었다**(마이크는 기존 주석 계획 `>>16` → `>>14`). ★ **발견·정착 = 2026-08-12 PoC-(36) / decisions.md 등재 = 2026-09-02 PoC-(37)** — 지침·인계엔 있었으나 원칙 자체는 미등재였던 **SSoT 역방향 stale**(실행 사례는 9.3·6.3에 있었으나 원칙 문장 부재).~~ **✅ [J-확정] 실증 횟수 3회로 갱신 (결정 2026-09-03 PoC-(39), 사용자 확정)**: 위 보류를 해소해 아래 3건으로 재정리한다. (1) **2026-08-08 ToF Stage A**: PR #34 관측 → ④런타임 실측(9.2 거리-near 곡선) → PR #35 판정(임계값 8 확정). 실측이 뒤집은 것 = "8→20 상향" 안 폐기(근거유형 = 실측, 9.2(d)). (2) **2026-08-12~09-02 ToF motion**: PR #36 계측 → ④런타임 실측(9.3) → PR #39 판정(9.4). 실측이 뒤집은 것 = `aggmax≥50` → `ndet≥1`(근거유형 = 실측). (3) **2026-09-02 마이크 shift**: PR #37 계측 → M3 ④런타임 실측(tz=6) → PR #38 판정(6.3). 실측이 뒤집은 것 = `>>16` → `>>14`(근거유형 = 실측). ★ **근거 등급 분리(숨기지 않음)**: (2)(3)은 이 3단계 패턴을 **의식하고 설계한 사례**다. (1)은 **사후 소급 분류**다 — PR #34는 Stage A 구현 PR로 기획됐지 "관측 전용 계측 PR"로 설계된 것이 아니다. 패턴이 명시적으로 정착된 시점은 **2026-08-12 PR #36부터**이며, 원칙 문장의 decisions.md 등재는 **2026-09-02**다. 그럼에도 3회로 세는 이유 = 3단계 구조(계측→실측→판정)가 (1)에서도 실제로 성립했고, "실측이 사전 추정을 뒤집는다"는 본 원칙의 **가장 강한 근거**(near 8→20 상향안 폐기)가 (1)에서 나왔기 때문이다.

### negative control은 `python3 -B`로 실행 — `.pyc` 캐시 오염 (발견 2026-09-05 / 문서 반영 2026-09-05, 근거유형 = 실측)

PR #44 negative control 실행 중 NC-5의 실패 목록이 NC-4의 것을 **통째로 포함한 8건**으로 나왔다. 조사 결과 **NC-4의 순서 swap 변형이 두 블록을 맞바꾸기만 해 파일 크기가 보존됐고, 복원 쓰기가 같은 초 안에 일어나 `.pyc` 무효화 조건(mtime + size)을 둘 다 피했다** → 캐시된 변형 바이트코드가 로드됐다. `python3 -B`로 재실행해 참값을 얻었다.
- ★ 이번엔 오염이 **거짓 양성 방향**이라 "설명 안 되는 실패 목록"이 단서를 줬다. **반대 방향이었다면**(변형이 캐시 때문에 미적용돼 "검출 X") 근거 없이 "가드가 없다"는 결론을 얻고 **없는 문제를 고치러 갔을 것**이다.
- → **자산화: negative control은 `python3 -B`로 돌린다**(회귀 실행 명령은 7.5(i)).
- ★ **층이 다르다**: PR #41(MOD 31 무해) → #42(센티넬 무해) → #43(NC-3 함정 실재)의 계보 4회차이지만, 앞 셋은 **불변식 설계 문제**이고 본 건은 **실행 환경 문제**다. 같은 계보로 뭉뚱그리면 대책이 어긋난다.

### negative control 함정 예고 = 2회 연속 적중 (발견 2026-09-05 / 문서 반영 2026-09-05, 근거유형 = 실측)

PR #43 NC-3(ToF 부재를 통과로 위장, 6.4(d))과 PR #44 NC-4(발송 순서 뒤집기, 7.6(g)) 둘 다 **실재**했다. 두 경우 모두 **결과만 검사하는 케이스로는 무해**했고, 전용 불변식(응답 3키 동시 고정 / wire 요청 시퀀스 검사)을 설계해야 잡혔다. PR #41·#42의 "지정 변형이 무해했다" 실패 이후 위임에 **"그 변형이 어떤 불변식을 깨는지 함께 적으라"**를 넣은 것이 효과를 냈다. → negative control 설계 시 변형과 **"무엇을 검사하는가"를 짝지어** 명시할 것.

### 5/17 종료 시점 액션
- 본 카테고리 세부 룰 최종 확정
- PoC-(2) 인계 패키지에 포함

---

## 카테고리 21: 매일 밤 작업 종료 루틴

의사결정 채팅방에서 다음 3가지 동시 출력:
1. `decisions.md` 갱신 위임 프롬프트 → Claude Code MCP에 던지기
2. 프로젝트 지침 수정본 → 학부생이 직접 갱신 (정적 변경 시만)
3. 노션 갱신 위임 프롬프트 → Claude Code MCP에 던지기

**우선순위**: GitHub `decisions.md` > 프로젝트 지침 > 노션 (충돌 시 GitHub 우선)

### 프로세스 위생 — 좀비 Claude 인스턴스 (발견 2026-08-08 / 문서 반영 2026-08-12)

`--dangerously-skip-permissions` 세션은 **터미널을 닫아도 잔존**(좀비 프로세스). 주기적으로 `ps aux | grep claude`로 점검하고, 이상 시 `pkill -f claude` 후 **단일 재기동**. "실행 중이던 것이 전부 죽었다"는 개별 원인이 아니라 **계통 원인의 신호**로 읽을 것(좀비 누적으로 인한 리소스 경합 가능성). 발견 = 2026-08-08 PoC-(35) 세션 / 문서 반영 = 2026-08-12 PoC-(36) — 지침·인계엔 반영됐으나 decisions.md 미등재였던 역방향 stale.

### 시크릿 파일(`.env`) 편집 위생 (발견 2026-09-05 / 문서 반영 2026-09-05, 근거유형 = 실측)

`echo 'KEY=값' >> .env`를 **파일 끝 개행 확인 없이** 실행해 `KAKAO_REFRESH_TOKEN` 값 뒤에 URL이 이어붙어 **토큰이 무효화**됐다(복구 후 정상 동작 확인). 실측 실행 환경이 파손되면 그 위에서 낸 측정값이 전부 무효가 되므로, 위 「프로세스 위생」과 같은 층의 검증 유효성 문제다.
- **재발 방지 ①**: `.env`에 `>>` 하기 전 `tail -c 1 .env | xxd`로 마지막 바이트가 `0a`인지 확인한다.
- **재발 방지 ②**: `.env` 내용 확인은 `grep -oE '^[A-Z_][A-Z0-9_]*' .env`(키 이름만) 또는 키별 길이 출력으로 한다. **값을 찍는 grep은 시크릿을 화면에 노출한다** — 이 사고에서 리프레시 토큰이 실제로 화면에 노출됐다(값 자체는 본 문서 미기록, 카테고리 7 토큰 항목 원칙 동일).
- 🟡 **[신규 미결] `.gitignore` 패턴 폭**: 실측 결과 `.gitignore`는 `.env`와 `.env.local`만 잡고 **`.env.bak`은 잡지 않는다**(백업 파일이 `??`로 추적 시도됨을 확인). 패턴을 `.env*`로 넓히는 것이 안전하나, **본 등재는 기록만이며 `.gitignore` 수정은 별도 소관**이다.

### Claude Code MCP 위임 시 자체 검증 3단계 강제 (코드 작성 관련, 2026-05-07 추가)

코드 작성/수정/라이브러리 통합/빌드 설정 변경 등 코드 관련 모든 위임 프롬프트에 다음 섹션 항시 포함:

**자체 검증 3단계:**
- ① 효율성 검토 (시간/메모리/CPU 점유율 / 불필요한 연산 / 알고리즘 복잡도)
- ② 리팩토링 검토 (가독성 / DRY 원칙 / 함수 분리 / 매직 넘버 const화 / 네이밍 일관성)
- ③ 오류 방지 검토 (엣지 케이스 / null·undefined / 메모리 누수 / 동시성 / 보안 취약점 / 컴파일 경고)

각 단계별 발견 사항 + 수정 사항을 출력 끝에 별도 섹션으로 명시 (통과/수정/무관 표시).

**적용 범위**: 신규 코드 / 기존 코드 수정 / 라이브러리 통합 / 빌드 설정 변경
**예외**: 단순 문서 작성 / 노션 갱신 / 리서치

### 노션 매일 갱신 5단계 표준 워크플로우 (2026-05-07 추가)

3번 노션 갱신 위임 프롬프트 작성 시 다음 5단계 그대로 적용:

1. **DB1 일자별 진행 로그**에 새 row 추가
   - 형식: "Day N (M/D)" + 단계 + 상태 + 핵심 결정 + commits

2. **페이지 상단 📌 메타 콜아웃 overwrite**
   - 마지막 갱신 시각 / 현재 단계 / 다음 마일스톤

3. **📋 오늘의 작업 체크박스 갱신**

4. **일정 vs 실제 표** 해당 날짜 행에 실제 결과 입력

5. **DB3 미결정 항목 상태 자동 전환**
   - 트리거 일자 임박 시 🟡 보류 → 🔴 트리거 임박

ID 참조:
- 노션 페이지: `359d8df0-3cab-816a-aedb-ec6341cc135e`
- DB1: `62a11105-c858-4eff-a151-268f3ffc4c9f`
- DB2: `e9697017-4372-4253-8aac-ae4b4f391fd6`
- DB3: `a319c04a-9201-417f-8552-7d6e99b2958f`

---

## 카테고리 22: 부품 발주 변경 (2026-05-07)

### 22.1 디바이스마트 발주 취소
- **사유**: XIAO ESP32-S3 Sense Pre-Soldered (102010635) 품절 통보
- **취소 처리**: 5/8(금) 17시 자동 취소 → 23,870원 환불 예정
- **영향**: 다른 발주 부품 5개 (INMP441, VL53L5CX-SATEL, KEYES 점퍼선 3종)는 정상 진행

### 22.2 자성리얼 네이버 스마트스토어 대체 발주
- **판매처**: 자성리얼 (smartstore.naver.com/jasungreal)
- **상품**: Seeed Studio XIAO ESP32 S3 Sense - 2.4GHz Wi-Fi, BLE 5.0, OV2640 카메라 센서
- **주문번호**: 2026050753038371
- **결제일**: 2026-05-07
- **결제 금액**: 36,540원 (원가 51,300원 - 할인 14,760원)
- **결제 수단**: 네이버페이 포인트 2,668원 + 머니 33,872원
- **옵션**: Size: Pre-Soldered / Color: ESP32C3 (옵션 강제 묶음)
- **배송 형태**: 국내 일시 품절 → 미국 본사 해외 직발송 (자성리얼 SMS 통보, 2026-05-08)
- **배송 일정**: 5/15~5/28 도착 (영업일 5~14일, 해외 직배송 통관 변동 포함)
- **마지막 갱신 일자**: 2026-05-08
- **갱신 사유**: 판매자 SMS 회신(2026-05-08) — 통관정보 회신 완료 (개인통관고유번호 P210018836994 + 박태근 + 휴대폰)
- **신뢰성**: 자성리얼 누적 판매 8,974건, 별점 4.98, 정품 인증 + 2년 보증

### 22.3 의사결정 근거
- **후보 비교**: 자성리얼 (36,540원, Pre-Soldered 확정) vs 메이크잇펀 (31,600원, "부착" 표기 모호)
- **선택 이유**:
  - Pre-Soldered 옵션 명시 확정 → 납땜 작업 0
  - 5/8 발송 → 5/15 데드라인 안전
  - 누적 판매 8,974건 + 별점 4.98로 신뢰성 검증
  - 메이크잇펀 톡톡 답변 5/8 17시 데드라인 전 도착 어려움 → 시간 안전성 우선
- **트레이드오프**: 4,940원 추가 비용 vs 시간 안전성 + 납땜 작업 0 + 신뢰성 → 시간 안전성 선택

### 22.4 잉여 ESP32-C3 보드 활용 계획
- **상황**: 자성리얼 옵션 강제 묶음으로 ESP32-C3 보드 1개 잉여 동봉
- **활용 1 (백업)**: 메인 ESP32-S3 펌웨어 작업 중 부팅 실패/벽돌 시 ESP32-C3로 WiFi/HTTP 더미 테스트 임시 진행 (5/8 WiFi 더미 테스트 일정 백업)
- **활용 2 (시연 백업)**: 졸작 발표 시연 직전 메인 보드 고장 시 임시 대체 (단, 카메라 없음 → 1차 알림 텍스트만 시연 가능, 화재경보 분류 OK)
- **활용 3 (졸작 후)**: 다른 IoT 토이 프로젝트 (홈오토메이션, BLE 비콘 등)
- **결론**: 잉여 부품 = 비용 손해 X, 백업 가치 있음

### 22.5 즉시 액션 항목 갱신
- 🟢 디바이스마트 자동 취소 + 환불 23,870원 정상 처리 완료 (2026-05-09 확인)
- 🟡 자성리얼 배송 추적 (5/15~5/28 도착 예상, 해외 직발송)
- 🟢 도착 후 ESP32-S3 Sense + ESP32-C3 보드 검수 (도착 시점 기준)

### 22.6 사전 준비 11일 영향 평가 (2026-05-08 동적 갱신)

자성리얼 배송 일정 변경(5/9~5/11 → 5/15~5/28)에 따른 사전 준비 11일(5/7~5/17) 영향:

- **5/9~5/14 (6일)**: 부품 부재 → 외부 계정 셋업 전진 + 호환성 추가 검증으로 활용 (5/14~5/15 학교 축제 휴식, 5/16 NCP 통합)
  - AWS EC2 t3.small 셋업 ✅ (5/13, 카테고리 30.1)
  - 카카오 디벨로퍼스 앱 등록 ✅ (5/13~5/14, 카테고리 30.2)
  - Naver Cloud Platform 계정 생성 ✅ (5/16, 카테고리 30.7)
  - VL53L5CX SparkFun lib 추가 검증 ✅ (5/7 monorepo 셋업)
  - Adafruit_VL53L5 폴백 lib_deps 사전 작성 ✅ (5/7 monorepo 셋업)
- **5/15~5/17 (3일)**: 부품 도착 시 결선 + 1차 부팅 (최단 5/15 도착 가정)
- **5/18 PoC 1주차 진입**: 정상 (부품 도착 후)
- **최악 시나리오 (5/28 도착)**: PoC 1주차 진입 후 부품 도착 → Plan B 다단계 트리거 검토 필요 (별도 미결정 사항)

큰 틀 변동 X — 5/15 최단 도착이 기존 11일 안에 포함되며, 5/9~5/14 공백은 외부 계정/호환성 검증으로 자연 활용.

> 22.3 의사결정 근거의 "5/8 발송 → 5/15 데드라인 안전" 문구는 의사결정 시점의 가정이므로 보존(이력성). 본 22.6이 사후 갱신된 실제 일정.

### 22.7 자성리얼 발주 결과 catch + 메이크잇펀 재발주 (2026-05-23)

**자성리얼 부품 도착 후 학부생 직접 화면 catch 결과 (학습 13)**:
- 도착 부품: ESP32-C3 (22.4 잉여 동봉분 그대로 도착)
- **메인 보드 = XIAO ESP32 S3 Sense Pre-Soldered 미동봉** (22.2 명시 메인 보드 부재)
- 발주 시점 가정 (22.2 + 22.3) vs 도착 실제 결과 mismatch

**대체 발주 (학부생 5/23 즉시 처리)**:
- 판매처: 메이크잇펀 (네이버 스마트스토어)
- 상품: 시드 스튜디오 샤오 ESP32-S3 센스 - Seeed Studio XIAO ESP32-S3 Sense
- 옵션: 핀헤더 부착 (Pre-Soldered)
- 주문번호: 2026052312703221
- 결제일: 2026-05-23 14:44:10
- 결제 금액: 28,600원 (상품 25,600원 + 배송비 3,000원)
- 도착 예상 (5/23 시점 가정): 2026-05-26 (화) ~ 2026-05-29 (금), 영업일 3~5일 기준 (5/23 토 발주 → 주말 끼고 영업일 계산)
- **도착 예상 정정 (5/26 학부생 직접 화면 catch 결과, 학습 13)**: 메이크잇펀 김정열 판매자 발송일 변경 통보 (5/26 14:20 카카오톡) — **2026-06-15까지 입고 후 발송 예정** (일시품절, 상품준비중). 학습 14 catch 그물 작동 사례 (외부 환경 가정 검증 강제 — 발주 시점 catch만으로 부족, 발송 시점 별도 catch 강제)

**학습 14 catch 그물 작동 사례 (외부 환경 가정 검증 강제)**:
- 22.3 의사결정 근거 = 의사결정 시점 가정 (자성리얼 = Pre-Soldered 확정, 메이크잇펀 = "부착" 표기 모호)
- 22.7 = 도착 후 실제 화면 catch 결과 (자성리얼 = 메인 보드 부재, 메이크잇펀 = 핀헤더 부착 확실)
- 가정만으로 부족 → 도착 후 화면 직접 catch 강제 패턴 영구 반영

**22.6 사전 준비 11일 영향 재평가 (2026-05-25 동적 갱신)**:
- 사전 준비 11일 (5/7~5/17)은 학부생 5/14~5/15 학교 축제 휴식 + 5/16 Day 8 NCP 셋업으로 사실상 5/16 종료
- 5/17~5/22 (6일) 작업 0건 (학습 9 chunk 경계 정렬 6일 확장) → 22.6 "5/15~5/17 부품 도착 시 결선 + 1차 부팅" 자연 슬립
- 22.7 메이크잇펀 도착 5/26~5/29 예상 (5/23 시점 가정) → PoC 1주차 5/18 진입 자연 슬립
- **22.7 도착 정정 (5/26 catch, 학습 14)**: 메이크잇펀 일시품절 → 2026-06-15까지 입고 후 발송 → 도착 약 6/17~6/19 예상. 5/26~6/14 약 20일 chunk 자연 슬립
- 5/26~6/14 chunk 작업 방향 = 카테고리 8 (대시보드) Phase 1 / Phase 2 단계별 진행 (별도 카테고리 8 본문 + decisions-log 2026-05-26 entry 참조)
- 학습 17 유도리 마인드 정합 — 22주 마스터 가이드라인 정량 데드라인 X, 본 약 1개월 슬립도 가이드라인 안에서 흡수 가능 (졸업 발표 9/30 기준 약 18주 남음)
- 학습 17 (유도리 마인드, 22주 일정 = 가이드라인) 정합

**부품 전량 도착 catch 완료 (2026-06-15, 학습 13·14)**:
- 메이크잇펀 XIAO ESP32-S3 Sense Pre-Soldered 수령 — SKU `102010635`, ST 정품, 학부생 직접 화면 catch. 발송 예정 6/15 → **실제 6/15 조기 도착(추가 슬립 없음)**. 5/26 catch 시점 도착 예상 약 6/17~6/19 대비 조기 도착
- 디바이스마트 부품 전량 수령: INMP441 모듈("납땜" 버전) / VL53L5CX-SATEL(ST 정품, `497-VL53L5CX-SATEL-ND`) / 점퍼선 3종(M-M / M-F)
- **인두기 불필요 확정**: INMP441 라벨 "납땜"(헤더 사전 납땜) + VL53L5CX-SATEL 정품 헤더 박힘 + XIAO Pre-Soldered → 전량 납땜 완료 상태로 도착, 인두기 추가 구매 불요
- 다이소 잔여 구매 항목 = **브레드보드만** (USB-C 케이블 집 보유)

---

## 카테고리 23: 시연 네트워크 환경 = 모바일 핫스팟 (2026-05-08 결정)

### 배경
- 시연 장소: 학과 발표장
- 학과 발표장 학교 WiFi 신호 약함 (기존 WiFi 환경 의존 위험)
- 학교 WiFi는 802.1X (WPA2-Enterprise) 인증 필요

### 결정
- production 시연 환경 = WPA2-Personal (모바일 핫스팟)
- 개발 환경 = WPA2-Personal (집 WiFi)
- 학교 WiFi (802.1X / WPA2-Enterprise) 지원 통째로 폐기

### 영향
- 5/8 WiFi 더미 테스트 (commit 3ec17d4): WPA2-Personal 통합 환경
  - 빌드 환경 분리 (school/home) 폐기 → 단일 환경 유지
  - esp_wpa2.h / WPA2_ENT 코드 전부 미작성
  - 런타임 SSID fallback (PRIMARY → FALLBACK) 도입
  - secrets.h: PRIMARY (집) + FALLBACK (핫스팟) 2쌍 슬롯
- 사전 준비 11일 중 가장 큰 리스크 요인 (esp_wpa2.h 호환성) 제거
- WiFi 본 작업 시간 약 40% 단축 (1h~2h → 30분~1h)

### 폐기 옵션
- core 2.x 다운그레이드 (검토 안 함)
- 학교 WiFi 시연 (PoC 5주차 이후 연기 검토 안 함)

### 후속 영향
- 시연 당일: 핫스팟 SSID/비번 바뀌어도 secrets.h만 수정 후 재업로드 (재빌드 X)
- 발표장 환경 변경 시: 즉시 적응 가능 (런타임 fallback)

---

## 카테고리 24: IDE 환경 — clangd IntelliSense 시도 + 한계 + 우회 (2026-05-08 결정)

### 배경
- 학부생 IDE: Antigravity (VS Code fork)
- WiFi 본 작업 (commit 3ec17d4) 후 IDE에서 빨간 줄 21건 발생
- pio run -t compiledb 실행 후 15건으로 감소 (Arduino.h not found 해결)
- 그러나 ESP32 전용 컴파일러 플래그 (xtensa GCC) clangd 인식 못 함

### 시도 작업 (3 commits)

**시도 1 (commit 70c0664): .clangd 설정 추가**
- ESP32 전용 컴파일러 플래그 4종 clangd 무시 처리:
  - -mfix-esp32-psram-cache-issue (Xtensa GCC 전용)
  - -mlongcalls (Xtensa GCC 전용, LLVM은 ARM/MIPS/Hexagon만 지원)
  - -fstrict-volatile-bitfields (Xtensa GCC 전용)
  - -fno-tree-switch-conversion (GCC 전용)
- -ferror-limit=0 (clang 진단 표시 개수 제한 해제)
- 효과: Unknown argument 4종 사라짐 (15건 → 11건)

**시도 2 (commit d801e01): CompilationDatabase 경로 명시**
- 원인 분석: compile_commands.json이 firmware/ 안에 있어 clangd 매칭 실패
- 해결: CompileFlags 하위 `CompilationDatabase: firmware` 1줄 추가
- 효과: 효과 미달 (11건 → 11건, 변화 없음)

**시도 3 (보강, commit db38da0): compile_commands.json gitignore 차단**
- 부산물 파일 1.9MB + 절대경로 포함 → push 위험
- .gitignore에 단일 패턴 추가 (모든 하위 디렉토리 자동 매칭)
- 효과: push 위험 차단 완료 (`git check-ignore -v` 검증 통과)

### 잔존 진단 (11건)
- hal.h not found 1건 (헤더 경로 일부 인식 실패)
- JsonDocument operator[] 7건 (ArduinoJson 7.x C++17 features 인식 한계)
- serializeJson 1건 (cascading)
- HTTPClient::begin() 1건 (WiFiClientSecure 변환 인식 한계)
- WiFi.onEvent 1건 + template 1건 (core 3.x 시그니처 인식 한계)

### 결론
- ESP32 + clangd + ArduinoJson 7.x + Arduino-ESP32 core 3.x 조합에서 IDE 인식 한계 존재
- 펌웨어 동작 영향 0 (컴파일 SUCCESS 유지, RAM/Flash 변동 0%)
- 결정: **잔존 11건 무시, 작업 진행에 영향 없음**

### 향후 옵션 (필요 시)
- 옵션 A (현재 채택): 무시 (개발 시 살짝 거슬리지만 동작 영향 0)
- 옵션 B: clangd 끄고 VS Code 기본 IntelliSense 사용 (Cmd+, → `clangd.disable`)
- 옵션 C: ArduinoJson 7.x → 6.x 다운그레이드 (firmware/platformio.ini 수정 필요, 5/8 본 작업 영향 — 비추천)

### 5/9~5/11 작업 영향
- 카메라 / 마이크 / ToF 라이브러리 추가 시 동일 패턴 빨간 줄 가능
- 5/9~5/11 작업 시 빨간 줄 보여도 추가 트러블슈팅 X (이미 IDE 한계 판정)
- 라이브러리 추가 후 `cd firmware && pio run -t compiledb` 재실행은 권장 (compile_commands.json 갱신, 그러나 commit 안 됨)

---

## 카테고리 25: Khangura 함정 6개 코드 반영 표 (2026-05-09 신설)

출처: https://medium.com/@manjotkhangura/getting-esp32-s3-sense-ov3660-camera-working-a-weekend-deep-dive-941d9c1a05d8

| # | 함정 | 코드 반영 | 분류 | 반영 위치 / 미반영 사유 |
|---|------|-----------|------|--------------------------|
| #1 | OCTAL PSRAM | ✅ | 적절 | `camera_common.cpp:59-62` `psramFound()` + `platformio.ini:30` `BOARD_HAS_PSRAM` |
| #2 | Frame Buffer Overflows | 🟡 부분 | B (부품 도착 후) | `fb_count=2` ✅ `camera_common.h:43` / DMA mode sdkconfig 미반영 — OV3660 검출 + FB-OVF 관찰 시 보강 |
| #3 | Ran Out of PSRAM | ❌ | C (QVGA scope 무관) | HD frame buffer 한정. QVGA 0.25% 점유 → PSRAM 고갈 불가 |
| #4 | JPEG timeout | ✅ | 적절 | `camera_common.h:51` `vTaskDelay(30ms)` + `camera_common.h:41` xclk=20MHz + jpeg_quality=12 |
| #5 | Kconfig WiFi | ❌ | C (framework 차이) | ESP-IDF menuconfig 한정. Arduino + secrets.h가 등가 (5/8 main.cpp 반영) |
| #6 | Dark Images | 🟡 부분 | B (indoor footage 검증) | brightness 보정 ✅ `camera_common.cpp:81` (Khangura 직접 인용) / saturation은 Arduino-ESP32/Seeed 예제 출처 — 부품 도착 후 추가 gain tuning 결정 |

**요약**: ✅ 완전 반영 2개 (#1, #4), 🟡 부분 반영 2개 (#2, #6 → B 분류, 부품 도착 후), ❌ 미반영 2개 (#3 C scope 무관, #5 C framework 차이).

**부품 도착 후 (5/15~5/28) 처리 항목**:
- #2: OV3660 검출 + FB-OVF serial 로그 관찰 시 sdkconfig 패치 (PlatformIO `board_build.partitions` 또는 `platform_packages`로)
- #6: indoor footage 어두움 육안 판정 후 추가 gain/AEC tuning

**5/9 후속 질의 commit hash**: 검토만, 코드 보강 0건 (HEAD `8ce56ed` 유지)

---

## 카테고리 26: 시연 시나리오 틀 (2026-05-09 신설)

> 본 카테고리는 5/13 졸작 중간 발표 스크립트 기준으로 시연 시나리오 **확정 틀** 정착.
> 5/13 발표 후 추가 피드백 발생 시 갱신 가능 (학습 8 원본 보존 + 갱신 추적 패턴).
> **2026-05-13 발표 결과**: 교수님 반응 좋음, 추가 피드백 0건 → v1 그대로 확정 (DB1 v2 row 신설 불필요, DB3 미결정 "5/13 발표 후 카테고리 26 갱신 가능성" 🟢 해결 처리).
> 세부 디벨롭은 노션 "데모 시나리오" 페이지에서 트래킹 + Demo-Verify-(N) 채팅방 검증.
> 발표 스크립트 원본: `docs/presentation/2026-05-13-script.md`

### 26.1 USP 2개 (4/29 중간 발표 1순위 피드백 반영)

1. **도어캠 기능**: 카메라로 방문자 사진 → 카카오톡 알림 첨부 ("누가 왔는지" 시각화)
2. **음성 자막화 기능**: 마이크 추가 녹음 → STT 텍스트화 → 자막 첨부 ("뭐라고 했는지" 텍스트 전달)

기존 시스템 흐름(소리 감지 → ML 분류 → 카카오톡)에 위 2개 기능 얹는 방식. 시스템 방향 변경 X.

### 26.2 부스 환경 (3영역 구성)

- **왼쪽**: 폼보드 가벽 현관문 모형 + 인터폰 박스 (ESP32 + 카메라 + 마이크 + ToF 통합) + 노크면 + 손잡이
- **가운데**: 책상 (시연용 도어벨 4개 + 카카오톡 수신 스마트폰 + 대시보드 노트북)
- **오른쪽**: 가이드 보드 + 포스터

인터폰 박스 → 폼보드 뒤 케이블 → 노트북 연결 구조.

### 26.3 진입점 3개 (학생 자유 선택)

#### 진입점 1: 노크 + 발화 시연
- **학생 액션**: 폼보드 가벽 노크 + 인사말 ("안녕하세요 택배입니다")
- **시스템 흐름**: ESP32 트리거 → ML 분류 (노크) → ToF 사람 검증 → 5초 1차 알림 ("누군가 노크했어요") → 15초 2차 알림 (사진 + 자막)
- **USP 메시지**: "진동만으로 누가 와서 뭐라고 했는지 한 번에 파악"
- **준비 사항**: 폼보드 노크 면 구역 + 보강재 (충격이 마이크에 잘 전달되도록)

#### 진입점 2: 초인종 등록 + 분리 시연
- **등록 액션**: 학생이 4개 도어벨 중 1개 선택 → 3~5회 누름 → 시스템이 우리집 초인종 템플릿 저장 (SP/DTW + cosine, 카테고리 4 참조)
- **분리 액션**: 미등록 초인종 → 알림 X / 등록 초인종 → 1차 + 2차 알림
- **해제 액션**: 대시보드에서 등록 해제 + 다른 초인종 재등록 가능
- **USP 메시지**: "옆집 초인종 잘못 반응 X" ~~(SP/DTW)~~ **(ToF presence 1차 융합 + SP/DTW 보조 2차, 2026-07-09 PoC-(26) 정정)**
  - ※ **USP 정량 근거 상태 (2026-07-08 PoC-(25))**: 개체 간(옆집) 분리 = 미검증 확정 — pretest "8.42"는 **클래스 간**(초인종 vs 노크/화재) 값이라 개체 구분 근거로 무효, 스파이크 실측 마진 1.713(낙관 상한)도 권고선 2.0 미달. 직접녹음 재검증 대기(11~12주차). 상세 = 카테고리 33.5.
  - ※ **USP 2층 재정립 (2026-07-09 PoC-(26))**: 옆집 구분 1차 메커니즘 = **ToF 사람 존재 검증**(카테고리 9 Stage A/B, VL53L5CX 단독 — PIR 아님). 논리 = 우리집 초인종=문 앞 사람 있음(ToF 감지) / 옆집 초인종=소리만 벽 타고 새어듦, 문 앞 사람 없음(ToF 억제). SP/DTW = 등록 시 오디오 지문 **보조층**. 위 7/8 note의 8.42=클래스 간 규명 자체는 유효(2차 필터 변별)하나 "옆집 구분 주력 근거"라는 위상이 mislabel — 이전 "USP 붕괴" 판정은 **SP/DTW 단층 평가 아티팩트**. **정직 표기**: 양층 모두 런타임 미검증 — ToF presence 설계 견고하나 **미측정**(브레드보드 결선 후), SP/DTW 1.713은 낙관 상한(직접녹음 4유닛 재검증 대기). 현재 위상 = **"2층 설계 확정 + 양층 검증 예정"**(근거 없음 아님). 데모 방향 = **ToF presence 리드 시연**(우리집=사람+소리→알림 / 옆집=스피커 소리만·사람 없음→억제 / 등록=SP/DTW 오디오 보너스), SP/DTW 4종 라이브 단독 시연 = **NO**(1.713 약함 발표 노출 회피). 상세 = 카테고리 33.5.

#### 진입점 3: 화재경보 시연
- **학부생 액션**: 핸드폰으로 화재경보 음원 부스 마이크 근처 재생
- **시스템 흐름**: ESP32 트리거 → ML 분류 (화재경보) → ToF 사람 검증 우회 → **즉시 1차 알림** (강조 표현) + **정부 지정 화재 대응 수칙 동시 발송**
- **2차 알림 X** (사진 + 자막 미발송, 카테고리 7 참조)
- **USP 메시지**: "위급 상황 안전 최우선 + 대응 가이드 전달"

### 26.4 시연 메시지 3가지 (부스 마무리 시점)

1. 누가 와서 뭐라고 했는지 사진 + 자막으로 한 번에 알림 (USP 1 + 2)
2. 우리집과 옆집 초인종 구분 ~~(SP/DTW)~~ **(ToF presence 1차 융합 + SP/DTW 보조 2차, 2026-07-09 PoC-(26) 정정 — 26.3 진입점 2엔 반영됐으나 26.4 누락분을 2026-08-08 catch)**
3. 화재 시 안전 최우선 + 대응 가이드 동시 전달

### 26.5 부스 외 보완 (시연 백업 영상)

- 시연 전 별도 백업 영상 촬영 계획
- 활용 1: 현장 네트워크 문제 발생 시 대비
- 활용 2: 부스에서 보여줄 수 없는 실제 사용 환경 영상 (집안 실사용)
- 촬영 시점: 18주차 통합 테스트 이후

### 26.6 디벨롭 추적 항목 (시연 시나리오 → 시스템 결정 매핑)

본 카테고리는 시연 시나리오 **틀 확정**만 담당. 세부 디벨롭은 본 개발 진행하며 단계적 처리:

| 디벨롭 항목 | 영향 도메인 | 처리 시점 |
|-------------|-------------|-----------|
| 폼보드 노크 면 구역 + 보강재 설계 | 부스 환경 | PoC 5~6주차 |
| 시연용 도어벨 4종 선별 | ML | PoC 5주차 (ML 학습 데이터 기준) |
| 초인종 등록 응답 시간 정량 결정 | ML + Server | 11~12주차 |
| 초인종 4종 분리 정확도 측정 | ML | 8~10주차 (ML 학습 후) |
| 대시보드 등록 해제 UI / ToF 통과 표시 UI | Dashboard | 15~16주차 |
| 화재 대응 수칙 메시지 템플릿 / 정부 출처 검증 | Server (카카오톡) | 13~14주차 |
| 시연 백업 영상 촬영 | 시연 자체 | 18주차 이전 |

### 26.7 발표 스크립트 출처

- **원본 파일**: `docs/presentation/2026-05-13-script.md`
- **발표 일자**: 2026-05-13 졸작 중간 발표
- **반영 피드백**:
  - 4/29 1순위 = 데모 시나리오 구체화 + 청각장애인 킥
  - 4/29 2순위 = 시연 단순함 vs 시스템 복잡도 갭 해소

### 26.8 검증 채널 (Demo-Verify-(N) 채팅방)

- **신설 시점**: 5월 중 (시점 자유, 학부생 결정) → **7월 초 재설정 (2026-06-14)**: 메이크잇펀 부품 슬립(6/17~19 도착) + Phase 2 진행 중(2-1차 6/14 완료) + ML/시연 준비 단계(8주차~) 정렬. 정량 데드라인 X(학습 17 유도리 마인드) 유지. 상세 = 노션 DB3
- **임무**: 시연 시나리오 → 시스템 기능 매핑 + 구현 가능성 평가 + Gap 카드 작성
- **Gap 카드 누적 위치**: 노션 "데모 시나리오" 페이지 DB3
- **Gap 처리 분기**:
  - 분기 A: 관련 도메인 채팅방 인계 (PoC / ML / Server / Dashboard)
  - 분기 B: 데모 시나리오 채팅방 인계 (시나리오 수정으로 회피)
  - 분기 C: decisions.md 카테고리 26 갱신 + 다른 카테고리 갱신
  - 분기 D: 무시 (Gap 영향 미미)

### 26.9 PoC-(6) 1회 검증 결과 (Gap 5건 catch)

5/9 PoC-(6)에서 본 카테고리 신설 직전 1회 검증 시 catch한 Gap 5건:

| Gap | 시나리오 위치 | 우선순위 | 영향 도메인 |
|-----|---------------|----------|-------------|
| 1 | 진입점 1 ToF 통과 표시 | 🟡 시연 품질 | Dashboard |
| 2 | 진입점 1 자막 형태 (메시지 vs 이미지) | 🟡 시연 품질 | Server + Dashboard |
| 3 | 진입점 2 등록 응답 시간 | 🔴 시연 필수 | ML + Server |
| 4 | 진입점 2 초인종 4종 분리 정확도 | 🔴 시연 필수 | ML |
| 5 | 진입점 2 등록 해제 UI | 🔴 시연 필수 | Dashboard |

상세 카드는 노션 "데모 시나리오" 페이지 DB3에 누적 (위임 2 작업 결과).

---

## 카테고리 27: 위임 프롬프트 repo 구조 가정 검증 강제 (2026-05-10 신설)

**학습 14 — 5/10 마이크 더미 테스트 (PoC-(7)) 작업 시 catch한 패턴.**

### 27.1 패턴

위임 프롬프트 작성 시 인계 패키지의 추상 표현 ("camera_dummy 컨벤션 일치", "기존 패턴 따라" 등)을 신뢰하지 말고, **실제 파일 경로 + build 설정 패턴 catch 검증**을 사전 단계로 강제.

### 27.2 5/10 catch 사례

- **위임 프롬프트 가정**: `firmware/dummy_tests/camera_dummy/` 디렉토리 + 동일 패턴으로 `firmware/dummy_tests/mic_dummy/` 신설
- **실제 5/9 카메라 컨벤션**: `firmware/src/camera_*.cpp` 직접 배치 + `firmware/include/camera_common.h` + `firmware/platformio.ini`의 `build_src_filter`로 환경 격리
- **catch 주체**: Claude Code MCP가 첫 단계 `git status` / `ls firmware/` 실행 시 디렉토리 부재 발견 → "임의 결정 금지" 원칙으로 학부생에게 옵션 제시 (`AskUserQuestion`)
- **학부생 결정**: 옵션 1 "실제 카메라 패턴 일치" 채택 → `firmware/src/mic_*.cpp` + `firmware/include/mic_common.h` + `[env:mic_dummy]` 추가

### 27.3 firmware/ 컨벤션 (5/10 catch 결과 명문화)

**디렉토리 구조**:
```
firmware/
├── include/
│   ├── camera_common.h     (5/9 신설)
│   ├── mic_common.h        (5/10 신설)
│   ├── tof_common.h        (5/11 예정)
│   └── secrets.h           (gitignore)
├── src/
│   ├── main.cpp            (env:poc 본 작업, WiFi)
│   ├── camera_common.cpp   (5/9)
│   ├── camera_test_v1.cpp  (5/9, env:camera_v1)
│   ├── camera_test_v2.cpp  (5/9, env:camera_v2)
│   ├── mic_common.cpp      (5/10, env:mic_dummy)
│   ├── mic_test.cpp        (5/10, env:mic_dummy)
│   ├── tof_common.cpp      (5/11 예정)
│   └── tof_test.cpp        (5/11 예정)
└── platformio.ini
```

**환경 격리 패턴**:
```ini
[env:{module}_{version}]
build_src_filter =
  -<*>
  +<{module}_common.cpp>
  +<{module}_test{_version}.cpp>
```

### 27.4 예방책

- 위임 프롬프트 작성 전 `git log -p [관련 commit]` 또는 GitHub 직접 확인하여 실제 컨벤션 catch
- 위임 프롬프트의 첫 작업 단계에 "현재 상태 확인 (`git status` + `ls [관련 폴더]`)" 강제 명시
- 자체 검증 ② 리팩토링의 "기존 컨벤션 일치" 항목이 자동 catch 그물 역할 (mic_test.cpp의 `setup()` graceful return 패턴이 카메라 v1/v2와 1:1 매칭됨을 검증한 사례)

### 27.5 5/28 사례 — 라이브러리 설정 방식/버전 가정 검증 (Phase 1 대시보드)

- **위임 프롬프트 가정**: Tailwind 디자인 토큰을 `tailwind.config.js`에 박음 (= Tailwind v3 멘탈모델)
- **실제 (현재 공식 기본값)**: shadcn/ui + Vite 공식 경로 = **Tailwind v4 (CSS-first, 설정파일 없음, `@theme inline`)**
- **catch 주체**: Claude Code MCP가 context7 공식 문서 + `dashboard/package.json` 실제 설치 대조 → v4 기본값 catch. 토대(전체 디자인 토큰)라 되돌리기 비용 큼 → surface 후 진행, 학부생이 v4 채택 + `@custom-variant dark` / `tw-animate-css` 정정 스펙 직접 제시
- **명문화**: 위임 프롬프트가 박은 **라이브러리 설정 방식/버전 가정**도 SSoT(현재 설치 `package.json` + 공식 문서) 대조 대상. 학습 14(가정 검증)를 "repo 구조" → "툴링 버전/설정 기본값"으로 확장 (학습 15·17 정합)

### 27.6 6/22 사례 — env:poc만 blacklist 잔존 → whitelist 통일 방향 (PoC-(17) catch)

- **catch 배경**: 27.3 환경 격리 패턴은 모듈별 env를 **whitelist**(`-<*>` 후 필요 파일만 `+`)로 명문화했으나, `[env:poc]`만 **blacklist**(`+<*>` 후 camera 3종만 `-`) 잔존. 5/8 poc 작성 당시엔 `main.cpp` 단독이라 무해했으나, 5/10 mic_test / 5/11 tof_test가 각자 `setup()`/`loop()` 정의를 추가하며 **poc 빌드에 흡수 → multiple definition** (카테고리 16 회귀 기록 참조).
- **방향 (별도 코드 수정 위임 예정, 본 PoC-(17)은 문서/검증 전용 = 코드 0 수정)**: `[env:poc]`를 27.3 whitelist 패턴으로 통일 — `build_src_filter = -<*> +<main.cpp>` (poc는 WiFi 본 작업이라 main.cpp만 포함). 임시 우회(`PLATFORMIO_BUILD_SRC_FILTER` 환경변수)는 영구 해법 아님 → 재현성 위해 platformio.ini 본문 정정 필요.
- **예방 명문화**: env 추가 시 **blacklist(`+<*>`) 금지, whitelist(`-<*>` 후 `+` 명시) 강제**. 신규 `setup()`/`loop()` 정의 파일 추가 시 기존 모든 env의 src_filter 흡수 여부 재검증 (자체검증 ② 컨벤션 일치 그물 = 본 회귀 사전 catch 대상). DB3 등록 예정.
- ✅ **완료 (PR #4 `c4c8f47`, 2026-06-22)**: `[env:poc]` whitelist 통일(`build_src_filter = -<*> +<main.cpp>`) + 임시 우회(`PLATFORMIO_BUILD_SRC_FILTER` 환경변수) 제거. footprint = poc RAM 13.8% / Flash 25.8% = **5/8 원본 poc(commit `3ec17d4`) footprint 일치** → main.cpp 단독 컴파일·회귀 해소 증명.

### 27.7 repo 절대경로는 실측값만 사용 — `~` 축약 금지 (2026-09-02 등재, 실패 2회 실증)

- **패턴**: 위임 프롬프트에 repo 경로를 적을 때 `~/ddingdong` 같은 **축약·추정 경로를 쓰면 MCP가 진입 자체에 실패**한다. 본 repo 실경로는 `/Users/xorms/Desktop/서경대학교/시험 준비/26-1/공학종합설계1/프로젝트/ddingdong`으로 **공백과 한글을 포함**하며, 홈 직하에 있지 않다.
- **강제 규칙**: 위임 프롬프트 §3(작업 환경)에는 **`pwd` 실측 절대경로 전문**을 적고, 모든 셸 명령에서 **큰따옴표로 감싼다**. `~` 축약·상대경로·부분 경로 금지.
- **실증**: `~/ddingdong` 축약으로 **2회 진입 실패**(2026-08-12 PoC-(36) 세션에서 신설·지침 반영).
- ★ **발견 2026-08-12 / decisions.md 등재 2026-09-02** — 지침·인계 패키지엔 반영됐으나 decisions.md만 미등재였던 **SSoT 역방향 stale**. 카테고리 27(위임 프롬프트 repo 구조 **가정** 검증)의 최말단 사례 = 경로 가정.
- ※ 별건: repo **바깥** 폴더(`~/ddingdong-측정결과` 등)는 경로가 정확해도 OS 권한 계층에서 내용 접근이 막힐 수 있다 — 측정 로그 원본을 repo 밖에 두는 정책(6.2·7.2)과 함께 인지할 것.

---

## 카테고리 28: packaging 제약 vs 공식 권장 분리 검증 (2026-05-10 신설)

**학습 15 — 학습 13 (전제 검증) 보강 형태. 5/10 마이크 작업 시 첫 컴파일 실패 → 즉시 검증 → fallback 결정 사례.**

### 28.1 패턴

외부 출처(공식 문서)의 권장값 인용만으로는 부족. **실제 환경(SDK / 패키지) 노출 여부**까지 함께 검증해야 채택 결정 가능.

### 28.2 5/10 catch 사례

- **공식 권장 (ESP-IDF 5.x context7 docs)**: `driver/i2s_std.h` (new API). legacy `driver/i2s.h`는 deprecated, 5.0부터 redesign
- **실제 SDK (arduino-esp32 v3.20017 = framework-arduinoespressif32@3.20017)**: 새 API 헤더 미노출
  - 첫 컴파일 시도: `fatal error: driver/i2s_std.h: No such file or directory`
  - 직접 검증: `find ~/.platformio/packages/framework-arduinoespressif32/tools/sdk/esp32s3/include/driver/include/driver/` 결과 = `i2s.h`만, `i2s_std.h` 부재
- **채택 결정**: legacy `driver/i2s.h` fallback (deprecation warning 0건 컴파일 출력 직접 확인 — `pio run -e mic_dummy` 출력에 `warning:` / `deprecated` 문자열 0건)

### 28.3 4단계 검증 절차 (학습 13 보강)

모든 라이브러리/API 채택 결정 시 다음 4단계 순차 검증:

1. **공식 권장**: 공식 문서 / 출처 인용
2. **실제 패키지 헤더 노출**: SDK 설치 경로에서 `find` / `ls`로 헤더 파일 직접 확인
3. **컴파일 통과**: 더미 코드라도 `pio run -e [env]` SUCCESS 검증
4. **런타임 동작**: 부품 도착 후 실측 (5/15~5/28 자성리얼 부품 도착 후)

### 28.4 마이그레이션 트리거

- arduino-esp32가 새 API 헤더(`driver/i2s_std.h`) 노출 시 → legacy → new API 마이그레이션 검토
- 또는 ESP-IDF 직접 사용으로 전환 시 동일 마이그레이션
- 마이그레이션 전: legacy API 유지 (현재 동작 중인 코드 깨지 X)

---

## 카테고리 29: 위임 프롬프트와 실제 컨벤션 충돌 시 기존 컨벤션 우선 (2026-05-10 신설)

**학습 16 — 5/10 마이크 작업 시 위임 프롬프트의 구체 코드 패턴과 카메라 v1/v2 기존 컨벤션 충돌 catch.**

### 29.1 패턴

위임 프롬프트의 구체 코드 패턴 vs 기존 repo 컨벤션 충돌 시 → **기존 컨벤션 우선**. 위임 프롬프트는 일반론, 기존 컨벤션은 실제 검증된 패턴.

### 29.2 5/10 catch 사례

- **위임 프롬프트 (PoC-(7))**: `while (!Serial && millis() < 2000) { delay(10); }` (Serial race 방지 패턴 A, 일반 Arduino 컨벤션)
- **실제 카메라 v1/v2 컨벤션**: `Serial.begin(115200); delay(SERIAL_BOOT_DELAY_MS=200);` (패턴 B, 단순 delay 기반)
- **Claude Code MCP 채택**: 패턴 B (camera v1/v2 컨벤션 일치 원칙 우선 적용)
  - mic_test.cpp:42~43 `Serial.begin(115200); delay(MIC_SERIAL_BOOT_DELAY_MS);` (=200ms)
  - 카메라 v1/v2의 `delay(SERIAL_BOOT_DELAY_MS=200)`와 동일 구조

### 29.3 정책

- **원칙**: 일관성 우선. 위임 프롬프트는 일반론을 제시하지만, 기존 컨벤션은 이미 검증된 실측 패턴.
- **예외**: 기존 컨벤션이 명백한 오류일 때만 위임 프롬프트 패턴 채택 + decisions-log entry로 명시 변경 사유 기록
- **자동 catch**: 자체 검증 ② 리팩토링 항목 "camera v1/v2 컨벤션 일치"가 이 catch 그물 역할

### 29.4 위임 프롬프트 작성 시 반영

- 위임 프롬프트 작성 시 일반 패턴이 아닌 **"기존 [관련 모듈] 컨벤션 우선" 원칙을 명시**
- 예: "Serial init은 기존 카메라 v1/v2 컨벤션 (`delay(SERIAL_BOOT_DELAY_MS)`) 일치"
- 충돌 발생 시 Claude Code MCP가 기존 컨벤션 자동 채택할 수 있도록 명시 우선순위 부여

### 29.5 5/28 사례 — 용어 컨벤션 (도어벨 → 초인종)

- **위임 프롬프트 용어**: "도어벨" (일반 용어)
- **기존 SSoT 컨벤션**: predicted_class 한글 표기 = **"초인종"** (카테고리 3/4/5). "도어벨"은 카테고리 26 시연용 물리 장치 한정 용어
- **catch + 채택**: Claude Code MCP가 decisions.md SSoT 대조 → predicted_class 한글 표기 = "초인종" 채택 (`doorbell` 영문 enum은 코드 유지). 위임 프롬프트 **일반 용어 < 기존 SSoT 컨벤션** (학습 16 원칙 적용, 학습 17 catch 그물 연동)

---

## 카테고리 30: 외부 계정 셋업 SSoT (2026-05-13 신설, 2026-05-16 NCP 추가)

> Day 7 (5/13~5/14 오전 통합) AWS + 카카오 디벨로퍼스 + Day 8 (5/16) NCP 셋업 결과 SSoT. 카테고리 22.6의 "5/9~5/14 외부 계정 셋업 전진 활용" 실제 완료 결과.
> **자격증명(액세스 키 / 시크릿 / 토큰 / 카드번호 / 휴대폰번호)은 본 문서 절대 미기록** — `firmware/include/secrets.h` (.gitignore) / 환경변수로만 관리.

### 30.1 AWS (2026-05-13 23:06~23:41, 35분)

- **계정**: 메일 `bagtaegeun278@gmail.com` / Account ID `953926452053` / 별칭 `xorms` / 리전 `ap-northeast-2` (서울)
- **요금제**: 무료 (6개월, 200 USD 크레딧) — 유효 기간 ~2026-11-13. 졸작 9/30 종료가 무료 기간 안에 자연 수렴 (30.4 정책 변경 catch 근거)
- **2026-11-13 의사결정 트리거**: 졸업 후 AWS 자격증/취업/사이드 프로젝트 활용 계획 있으면 유료 전환, 없으면 자동 해지 수용
- **MFA**: 루트 사용자 ON, Google Authenticator (`xorms-iphone` 디바이스), 시크릿 키 iPhone 메모 잠금 저장
- **IAM 사용자**: `ddingdong-admin` (AdministratorAccess + 콘솔 액세스)
- **결제 알람 2종**:
  - `My Zero-Spend Budget` — 실 비용 $0.01 임계값 (무료 한도 초과 즉시 catch)
  - `My Monthly Cost Budget` — 월 $100 한도 (85% / 100% / 예상 100% 알림)

### 30.2 카카오 디벨로퍼스 (2026-05-14 10:26~10:37, 11분, Day 7 통합)

> 학부생 의도: 5/14 오전 작업이지만 Day 7 외부 계정 셋업 연속선상 통합 처리 (학습 9 chunk 경계 정렬 예외, decisions-log 2026-05-13 entry에 명시).

- **계정**: 기존 카카오 계정 재사용 (앱 3개 기존 운영 중: PICKL / PICKL 개발용 / 13기 중앙해커톤 피클)
- **신규 앱**: `Ddingdong` (앱 ID `1456718`) / 회사명 `xorms` / 카테고리 `라이프스타일`
- **카카오 로그인**: 활성화 (ON)
- **talk_message scope**: **선택 동의** 채택 (이용 중 동의 X) — 카테고리 7 "memo API + 비즈 앱 회피" 일치

### 30.3 카카오 비즈 앱 회피 결정 근거

- **채택**: 개인 개발자 계정 + talk_message "선택 동의" / **회피**: 비즈 앱 심사 (사업자 등록증 필요)
- **근거**:
  1. 시스템 흐름상 "나에게 보내기" (memo API)만 사용 → 비즈 앱 불필요 (카테고리 7 일치)
  2. 본인이 본인 계정에 동의하는 구조 → "선택 동의"로 충분
  3. "이용 중 동의" 대비 "선택 동의"가 더 단순 (카카오 로그인 시 동의 받음)
- **출처**: 카카오 디벨로퍼스 공식 문서 (talk_message scope 동의 항목 정책)

### 30.4 AWS 신규 가입자 정책 변경 catch (2024-07~)

- **변경 내용**: 신규 가입자 디폴트 = "무료 (6개월)" 또는 "유료" 플랜 선택 강제 (이전 무제한 free tier 디폴트 폐기)
- **무료 플랜**: 200 USD 크레딧 + 6개월 무료 + 6개월 후 또는 크레딧 소진 시 자동 해지
- **본 프로젝트 영향**: 졸작 9/30 종료가 무료 기간(~2026-11-13) 안에 자연 수렴 → 30.1 유효 기간 명시 근거
- **출처**: AWS 가입 화면 직접 catch (2026-05-13, `bagtaegeun278@gmail.com` 계정 생성 시)

### 30.5 11~14주차 카카오 진입 시 추가 작업 placeholder

본 5/14 셋업은 앱 생성 + 카카오 로그인 ON + scope 선택까지. 11~14주차 카카오톡 메시지 작업 진입 시 추가: 플랫폼 등록(Web) / Redirect URI 등록(EC2 도메인 기반) / 토큰 발급(액세스 6h + 리프레시 60d, 카테고리 7 일치) / 메시지 발송 테스트(memo API).

### 30.6 미진행 항목 (카테고리 22.6 대비)

- ~~**Naver Cloud Platform** (STT용, 카테고리 7) — 5/13 시점 미진행~~ → **5/16 완료** (30.7 신설, 카테고리 22.6 NCP 항목 ✅ 처리)
- 카테고리 22.6 5/9~5/14 외부 계정 셋업 항목: AWS ✅ (30.1) / 카카오 ✅ (30.2) / **NCP ✅ (30.7, Day 8)** → 3건 모두 완료

### 30.7 NCP (2026-05-16 14:36~15:00 통합, Day 8)

> 학부생 의도: 5/14~5/15 학교 축제 휴식 후 5/16 (Day 8) 재개. AWS / 카카오와 동일 패턴 직접 진행. 그린루키 사전 catch 강제 (MCP 위임 12분) → 미제휴 확정 → 옵션 B (메일 발송 X) 채택.

- **계정**: ID `2021304034@skuniv.ac.kr` (학교 이메일, 그린루키 신청 가능성 catch 위해 강제) / 회원 유형 개인 / 별칭 `xorms` (AWS 동일)
- **요금제**: 무료 (기본 크레딧 100,000원, 유효기간 3개월) — ~~유효 기간 ~2026-08-16~~ → **정정 = 유효기간 2026-05-01 ~ 2026-08-31**(2026-09-02 콘솔 화면 catch). 졸작 9/30 종료 시점 도달 시 자동 과금 발생 가능. ★ **발원 = 파생값 오류**: 5/16 화면 catch한 값은 "100,000원 / 3개월"이고, 8/16은 거기서 **가입일+3개월로 계산한 파생값**이었다. 실제 콘솔 표기는 5/01~8/31. → **학습 13의 새 변형**: "화면 catch한 값"과 "그 값에서 계산한 파생값"은 **신뢰도가 다르다 — 파생값도 catch 대상이다.**
- ~~**2026-08-16 의사결정 트리거**: 졸작 9월 진입 시 STT 사용 시점 (11~12주차 7/27~8/9) 안에 사용량 catch 후 결제수단 자동 과금 수용 OR 추가 크레딧 신청 결정~~ → **트리거 경과 (2026-09-02 확정, 30.9 참조)**: 크레딧은 2026-08-31 만료됐고 **잔액 100,000원 전액 미사용 소멸**. 결제수단 등록 상태이므로 **실과금 구간 진입**.
- **2차 인증**: SMS (휴대 전화번호) — AWS OTP (Google Authenticator)와 다른 방식, 학부생 의도 분리. 휴대폰 분실 시 lock-out 위험 인지 강제
- **결제수단**: 신용카드 등록 (회원가입 절차 중 자동), 자동 과금 활성화. **카드 번호 본 문서 미기록**
- **IP 보안 설정**: OFF (학부생 환경 IP 자주 변경 — 집/학교/카페/모바일 핫스팟)
- **Idle Time**: 3시간 (개발 작업 흐름 우선)

### 30.8 그린루키 사전 catch 결과 (MCP 위임, 학습 14 catch 그물 7건째 작동)

- **catch 시점**: 2026-05-16 14:55, Claude Code MCP 위임 12분 (예상 20~30분 대비 단축)
- **catch 결과**: **서경대 미제휴 사실상 확정**
- **3중 출처 일관 catch**:
  1. NCP 공식 그린루키 페이지 (https://www.ncloud.com/support/greenRookie) — playwright 동적 로딩 + 스크린샷 32개 기관 시각적 catch → 서경대 미포함
  2. 서경대 산학협력단 (https://sanhak.skuniv.ac.kr/) + 서경대 메인 (https://www.skuniv.ac.kr/) — 네이버 클라우드 / 그린루키 안내 0건
  3. 비공식 출처 (블로그 / Velog / Tistory) — 서경대 학생 그린루키 신청 사례 0건
- **대조군 사례**: 아주대 (https://www.ajou.ac.kr/kr/ajou/notice.do?mode=view&articleNo=103728), 서울대 (https://www.ncloud.com/intro/cases/SNU) 등 제휴 학교는 학교 공지 / 학생 후기 다수 존재
- **NCP 공식 블로그 (2021-09)** 인용: 11개 대학 제휴 (https://blog.naver.com/n_cloudplatform/222302707216) → 2026년 5월 시점 32개로 확장, 서경대 여전히 미포함
- **결정 (5/16)**: **옵션 B (메일 발송 X)** + 옵션 D 연기 (산학협력단 NCP 제휴 추진 메일, 5/18 이후 평일 진입 후 결정)
- **결정 정정 (2026-05-27, 학부생 직접)**: **옵션 D 폐기** — 학부생 작품 기간 (~2026-09-30) 안에서 NCP 제휴 추진 불가 + 후배 가치 창출 기회 폐기 수용. DB3 옵션 D row 🟢 해결됨 전환 강제.
- **헛수고 회피**: 메일 발송 + 5/18~5/19 거절 답변 회피 (단기 손실 5분, 단기 이득 0)
- **장기 가치**: 옵션 D 진행 시 후배 가치 창출 (학기 끝나기 전 처리 시 OK) — 5/27 폐기로 미실현

### 30.9 11~14주차 카카오 + NCP 진입 시 추가 작업 placeholder

본 5/16 NCP 셋업은 회원가입 + 결제수단 + 2차 인증 + 사전 catch까지. 11~14주차 카테고리 7 STT 작업 진입 시 추가:
- Clova Speech 서비스 활성화 (NCP 콘솔 → AI Services → CLOVA Speech)
- Application 등록 (Client ID + Client Secret 발급)
- API Gateway 연동 (REST API 호출용)
- ~~단가 catch: 초당 0.5원 (분당 30원), 띵동 추정 월 1,000~3,000원 → 기본 크레딧 100,000원 안전 수렴~~ **정정 (2026-08-03 PoC-(33), 카테고리 7 STT CSR 확정 시 재catch)**: 현행 CSR 요금 ≈ **15초당 4원**(2026 KR 요금표) — 기존 "초당 0.5원/분당 30원"과 불일치. 우리 용도(5초 클립 1건 ≈ 15초 단위 1과금 = 4원)로도 저빈도라 기본 크레딧 100,000원 안전 수렴 결론은 불변. 실 과금 시점 사용량 catch는 11~12주차 defer.
- ~~만료 일자 catch: 2026-08-16 (3개월) → 11~12주차 진입 후 자동 과금 발생 시점 catch 강제~~ → **정정 = 2026-08-31 만료 확정 + 경과**(아래 2026-09-02 블록).

**✅ CSR Application 등록 완료 + 호출 한도 실측 (2026-08-12 PoC-(36))**
- **Application 등록 완료**: 이름 `ddingdong-stt`, 서비스 = **CLOVA Speech Recognition(CSR) 단독**(CLOVA Voice-Premium 미선택), 등록일 2026-08-12. Client ID / Client Secret 발급 완료 (★ 실값은 env·secrets 경유만 — 본 문서 기록 금지).
- ★ **신규 실측 — 호출 한도**: **당일 30,000초 / 당월 300,000초**(콘솔 목록 화면 catch). 1건 5초 기준 당일 6,000건 / 당월 60,000건 → **실사용 대비 한도 제약 없음**.
- **콘솔 경로 정정**: CSR 등록은 ~~AI Services → CLOVA Speech~~ 가 아니라 좌측 메뉴 **`AI·NAVER API > Application`**. ※ AI Services 카테고리(8종)에는 CSR이 없음 — CLOVA Speech는 별개 제품(카테고리 7 STT CSR 확정 note 정합).
- **관문 ③ 간소화**: 등록 후 CSR 선택 유지 확인은 **목록 화면 "서비스구분" 열에서 직접 확인 가능** — 별도 [수정] 진입 불요.
- ~~크레딧 만료 2026-08-16은 **미해소 유지**(30.7 자동 과금 가능성 서술 유지).~~ → **정정 (2026-09-02)**: 만료일은 **2026-08-31**이었고, 그 날짜로 **만료 경과 + 잔액 전액 소멸** 확정. 아래 2026-09-02 블록 참조.

**✅ NCP 크레딧 만료 경과 + 호출 한도 설정 + 콘솔 경로 실측 (2026-09-02 PoC-(37), 외부 콘솔 화면 catch 4건)**

- **(1) 크레딧 만료일 정정**: ~~2026-08-16~~ → **유효기간 2026-05-01 ~ 2026-08-31**(콘솔 크레딧 관리 화면 표기). 8/16은 5/16 화면 catch값 "100,000원 / 3개월"에서 **가입일+3개월로 계산한 파생값**이었음. → **학습 13 새 변형 = 파생값도 catch 대상**(30.7 동반 정정).
- **(2) ★ 상태 = 만료 경과 (2026-09-02 기준 D+2)**: 잔액 **100,000원 전액 미사용 소멸**. 결제수단 **등록됨(신용카드 자동이체, 2026-05-16 등록)** → **실과금 구간 진입**. 단 **8월 청구요금 0원 / CSR 호출 이력 0건**(당월 0/300,000 · 당일 0/30,000) — 실지출 0원.
- **(3) 호출 한도 설정 완료 (2026-08-20 설정)**: **일 500초 / 월 5,000초** + **임계 70% 알림** + 통보대상 등록. 시스템 상한은 일 10,000,000 / 월 30,000,000. ⚠️ **화면 안내 원문 기준 소프트 한도** — "설정 적용 중 수 초 내 초과 호출 가능"이라 **하드 스톱이 아니다**.
- **(4) ★ 콘솔 경로 실측 정정 (URL 최초 등재)**
  - **크레딧/청구/결제 = `console.ncloud.com/billing/*`** (포털 마이페이지 **아님**). 트리 = `과금 정보 및 비용 관리 > 청구 및 결제 관리 > {청구서 / 결제 정보 관리 / 크레딧 관리 / 코인 관리 / 할인 관리}` + `비용 관리 > {Dashboard / Cost Insight / Cost Analysis / Budgets / 솔루션 이용 현황}`.
  - **Application/호출 한도 = `console.ncloud.com/naver-service/application`**. 버튼명 = **[한도 및 알림 설정]** (탭 3종 = 한도 설정 / 한도 변경 이력 / 통보대상 설정).
  - ⚠️ **`console.ncloud.com/service-quota/quota-status`는 별개다.** 거기 "AI·NAVER API 기본 한도 50, 사용량 1"은 **Application 개수 quota**이지 **호출량 한도가 아니다**(2026-09-02 화면 catch).
- ★ **콘솔 화면 catch 우선 원칙 2회차 실증**: 공식 문서(`guide.ncloud-docs.com`) 기반 **추정 경로가 실화면과 불일치**했다. 8/12 "AI Services 카테고리에 CSR 부재" catch에 이은 2회차 — **문서 결론보다 화면 catch 우선**(학습 13 계열).

**✅ CSR 왕복 ④런타임 실증 + 15초 단위 과금 실측 확증 (2026-09-05 PoC-(41), 실측 2026-09-05 / 문서 반영 2026-09-05)**

- **왕복 실호출 (근거유형 = 실측)**: `POST https://naveropenapi.apigw.ntruss.com/recog/v1/stt?lang=Kor`, 헤더 `X-NCP-APIGW-API-KEY-ID` / `X-NCP-APIGW-API-KEY`, `Content-Type: application/octet-stream`. 입력 = 16kHz mono 16bit PCM WAV **131,756 B**(약 4.1초, macOS `say` TTS 생성). 응답 = `{"text":"택배 왔습니다 문 앞에 두고 갈게요"}`, **왕복 0.892초**(15초 예산의 5.9%). ★ Client ID·Secret 실값은 env 경유만 — 본 문서 미기록(위 등록 항목 원칙 유지).
- ⚠️ **정직 표기**: 원문 첫 어절 "계세요?"가 **누락**됐다. TTS 어택이 약했는지 인식 실패인지 **미규명**이며, 실 육성 정확도는 별건이다(실측 1건) — **단정 금지**.
- ★★ **15초 단위 과금 = 문서 인용 → 실측 확증**: 콘솔 Usage Statistics에서 4.1초 호출 1건이 **usage=15**로 계상됐다(success 1 / failed 0). 위 "15초당 4원"(2026-08-03 재catch, 근거유형 = 문서 인용)이 **화면 숫자로 확정**됐다.
  - **설계 파급 (근거유형 = 논증, 위 실측 위)**: 5초를 쓰든 15초를 쓰든 **요금이 같다** → **2차 녹음을 15초까지 늘려도 추가 비용 0원**. 현재 5초 설계는 카카오 15초 예산 제약이지 **요금 제약이 아니다**.
  - 한도 소진 = 일 500초 중 15초(**3%**) / 월 5,000초 중 **0.3%**(위 (3) 호출 한도 대비).
- ★ **콘솔 경로 정정 (근거유형 = 실측 화면 catch, 학습 13 화면 우선 3회차)**: Usage Statistics 실제 URL = **`console.ncloud.com/naver-service/usage`**. 좌측 메뉴가 `Application` / `Usage Statistics` **2개로 분리**돼 있다(위 (4)의 `naver-service/application`은 Application 전용 경로). 필터 = Application `ddingdong-stt` / Service `CLOVA Speech Recognition (CSR)` / 기간.
- ⚠️ **왕복 실증 ≠ 서버 배선**: `server/`의 STT 호출 코드는 여전히 **0줄**이고 7.6 A-2 자막은 mock 문구다(카테고리 7 STT 항목 동반 등재).

### 30.10 학습 catch 사례 누적 (5/16 추가)

- **학습 13 catch 그물 작동 사례 (5/16)**: NCP 회원가입 화면 catch 시 "기본 크레딧 100,000원 / 3개월" 학부생 직접 catch → 사전 박았던 "100,000원 / 100일" 정정 사례. AI 일반 패턴 박기 X, 학부생 화면 catch 우선 강제
- **학습 14 catch 그물 작동 사례 7건째 (5/16)**: 그린루키 신청 메일 발송 전 학부생 사전 검증 강제 요구 → MCP 위임 catch → 미제휴 확정 → 헛수고 회피
- **위임 프롬프트 형식 SSoT 강제 작동 사례 (5/16)**: 그린루키 사전 catch 위임 프롬프트 9개 섹션 구조 준수 → MCP 12분 단축 완료 (효율 검증)

---

## 카테고리 31: Claude 박음 본문 사전 자가검증 3단계 강제 룰 (2026-05-27 신설)

> 2026-05-27 PoC-(13) 본 채팅방 학부생 push back catch 결과 SSoT 영구 반영. AI 본인도 학습 17 catch 그물 작동 대상 정직 영구 반영 (3차 강화 11건째 정직 작동 결정적 증거).

### 31.1 패턴

Claude가 학부생에게 코드 관련 제안 시 사전 자가검증 3단계 통과 후 박기 강제. 자가검증 누락 본문 = 학부생 push back catch 그물 작동 강제.

### 31.2 자가검증 3단계 (기존 코드 작성 위임 자체 검증 3단계와 동일)

**1단계: 효율성 검토** — 시간 / 메모리 / CPU / 알고리즘 복잡도 / 불필요한 연산 catch
**2단계: 리팩토링 검토** — 가독성 / DRY 원칙 / 함수 분리 / 매직 넘버 const화 / 네이밍 일관성 / 데이터 구조 일관성 / 기존 컨벤션 일치 (학습 16 정합)
**3단계: 오류 방지 검토** — 엣지 케이스 / null / 누락 데이터 / 충돌 / 타임스탬프 정확도 / 보안 / 동시성 / 컴파일 경고

### 31.3 적용 범위

- 코드 관련 제안 = API 명세 / 데이터 구조 / 아키텍처 / 컴포넌트 설계 / 라이브러리 선택 / 폴더 구조 / 명명 규칙 등 코드 영향 모든 결정
- **적용 제외**: 단순 의사결정 (옵션 D 폐기 / 매일 밤 루틴 / Phase 1 진입 시점 등)

### 31.4 백그라운드 진행 강제 (2026-05-27 학부생 push back 추가)

- 자가검증 3단계 = Claude 머릿속 진행, 응답 본문에 박지 X
- 응답 본문 = 자가검증 통과 결과만 박음 (가독성 ↑)
- 단, 학부생 요청 시 자가검증 본문 박음 가능 (디버깅 영역)

### 31.5 표시별 강제 출력 룰 (Claude 박음 본문 직접 적용 시 한정)

- **"통과"** → 검증 방법 1줄 강제 (백그라운드 진행 시 생략 가능)
- **"수정"** → Claude 박음 본문 정정 강제 (수정 전 → 수정 후 diff)
- **"무관"** → 근거 1줄 강제 (백그라운드 진행 시 생략 가능)

### 31.6 학습 17 3차 강화 정직 작동 11건째 (5/27 catch 결정적 증거)

- catch 사례: 결정 1 (`POST /api/detect` request body) Claude 박음 자가검증 누락 → 학부생 push back으로 강제 자가검증 적용 → 정직 정정 7건 catch (네이밍 / 데이터 구조 / 보안 / 타임스탬프 / NTP / device_id UUID / ToF 보강)
- catch 결과: Claude 박음 본문 자가검증 누락 패턴 = 학부생 push back catch 그물 정직 작동 = 학습 17 3차 강화 정직 영구 반영 강제

### 31.7 위임 프롬프트 9개 섹션 SSoT와의 관계

- 위임 프롬프트 9개 섹션 (PoC-(9) 5/13 영구 반영) = Claude Code MCP에 위임할 때 작동 룰
- 본 카테고리 31 = Claude (PoC 의사결정 채팅방 / 위임 프롬프트 생성기 채팅방) 박음 본문 직접 적용 룰
- 동일 자가검증 3단계 패턴 = 적용 영역 차이만 (위임 = MCP, 본 카테고리 = Claude 직접 박음)

---

## 카테고리 32: PoC-(17) 1차 부팅 검증 결과 (2026-06-22 신설)

> 5/7~5/11 작성 더미 펌웨어의 **실보드(XIAO ESP32-S3 Sense) 1차 부팅 검증**. USB-C 단독(결선 0)으로 가능한 2종(카메라·WiFi)만 진행. 학부생 = 의사결정/결과 판정, MCP = 실행/해석 (학부생 직접 디버깅 X). **검증 전용 = firmware 코드 0 수정 / commit·push 0 / secrets.h 미열람**.

### 32.1 검증 범위

- **대상 env**: `camera_v1` (cameraTask 단독) + `poc` (WiFi + HTTPS 더미)
- **미진행 (결선 필요 → 2단계로 분리)**: `mic_dummy`(INMP441 I2S 배선) / `tof_dummy`(VL53L5CX I2C 배선)
- **HEAD**: `0d15fe2` 불변 (검증 전 = 후, working tree clean)

### 32.2 카메라 (camera_v1) — ✅ PASS

- **센서 OV3660 실측 확정**: PID `0x3660` = 라이브러리 SSoT 일치 (카테고리 1 append 참조). 가정 적중 → 센서 코드 수정 불필요.
- init ✅ / **PSRAM 8MB OCTAL 인식** ✅ / QVGA(320x240) JPEG ~6KB 연속 캡처 ~28-30fps / **fb_get NULL 0건** / 힙 안정(~340KB, 누수 없음)
- 카테고리 17(#620 fb_get fail) = 카메라 단독에선 미발현 (인지만 유지)

### 32.3 WiFi (poc) — ✅ PASS (외장 안테나 장착 후)

- 안테나 미장착 시 양쪽 SSID 15s timeout 반복 → **u.FL 안테나 장착 즉시 `Connected via PRIMARY` (RSSI -53dBm, IP 할당, 0.7초 연결)** + **HTTPS POST status=200**
- 0순위 진단(외장 안테나 필수) 적중 — secrets.h 자격증명·2.4GHz는 정상이었음 (카테고리 1 WiFi 안테나 항목으로 영구 반영)
- 펌웨어 WiFi STA fallback/retry/backoff + WiFiClientSecure setInsecure() HTTPS POST 더미 전체 동작 확인

### 32.4 발견 이슈 2건 (별도 수정 위임 — 본 검증 코드 0 수정)

1. **env:poc src_filter blacklist 회귀** → 카테고리 16 회귀 기록 + 카테고리 27.6 방향. whitelist 통일 별도 위임 + DB3 등록 예정. → ✅ **수정 완료 (PR #4 `c4c8f47`)**: `[env:poc]` whitelist(`-<*> +<main.cpp>`) 통일 + 임시 우회 제거. footprint = 5/8 원본 poc footprint 일치(RAM 13.8% / Flash 25.8%)로 회귀 해소 검증 (카테고리 27.6 완료 항목 참조).
2. **camera_common.cpp PID 비교 버그**: `sensorIdToName()` 및 OV3660 보정 분기가 `id.PID == 0x36`로 비교하나 실제는 `uint16_t 0x3660` → ① 진단 라벨 `(UNKNOWN)` 오표기 ② **OV3660 dark-image 보정(Khangura #6, 카테고리 25) 미실행**. **캡처 자체는 정상**(QVGA JPEG 정상 출력)이라 1차 부팅엔 무영향이나, 시연 영상 밝기 보정 위해 `0x36 → 0x3660` 수정 필요. 별도 수정 위임 + DB3 등록 예정. → ✅ **수정 완료 (PR #4 `c4c8f47`)**: `0x36` 리터럴 → **`OV3660_PID` 매크로**로 정정 (`camera_common.cpp` L49 `case` 라벨 + L79 OV3660 dark-image 보정 분기 양쪽). 학습 15 헤더 노출 검증 통과(`sensor.h:22`에 `OV3660_PID` 정의 확인) → dark-image 보정 분기 정상 작동 복구.

### 32.5 환경 변경 1건 (코드 아님, 학부생 승인)

- PlatformIO Core **6.1.19** `~/.platformio/penv` 표준 경로 복구 (카테고리 16 정정 참조). `/tmp/pio-venv` 재부팅 소실 = 학습 14 사례.

### 32.6 제약 준수 증명

- firmware 파일 **0 수정/생성/삭제** (HEAD `0d15fe2` 불변, working tree clean)
- `secrets.h` 미열람·값 미출력 (`test -f` 존재 확인만), 시리얼 SSID/IP 마스킹 출력
- commit/push 0 (검증 전용), 임의 코드변경 결정 0 (블로커 3건 전부 `AskUserQuestion` 후 진행: pio 설치 / src_filter override / 안테나 확인)

---

## 카테고리 33: ML 파이프라인 구축 + YAMNet 예비 학습 결과 (2026-07-01 신설)

> 8~10주차 ML fine-tuning 크리티컬 패스 **선작업** 대량 진행(2026-07-01): dataset 파이프라인(`ml/pipeline`) 구축 + 4대 버그 fix + YAMNet 학습 골격(`ml/training`) + **예비 학습 성공(test 검증)**. 실 파이프라인·학습 = 학부생 로컬(데이터셋 EPERM), repo 안은 합성 더미 관통 검증만. 카테고리 4·5 SSoT 준수. 실측 배분·저장정책 = 카테고리 5.1.

### 33.1 데이터 파이프라인 (`ml/pipeline`, PR #10~#14)

- **스테이지 00~05**: `preprocess`(16k mono 검증 + peak 정규화 + 빈클립 skip → 02) → **원본(source) 단위 group split**(누수 방지, 증강 이전 → 03) → `augment`(**train만** waveform 증강 → 03) → `assemble`(train=원본+증강 / val·test=원본만 → 05) → `guards`(누수 assert). **전 산출 스테이지 auto-clean**(02/03/05, stale 방지).
- **source 단위 split 근거(PR #12)**: 파일명 = `{원본ID}_{조각7자리}`. 한 원본을 3초 간격 조각낸 클립이 train/val/test로 흩어지면 **data leakage** → 원본 단위 그룹 통째 배정. `config.PIECE_SUFFIX_PATTERN = re.compile(r"_\d{7}$")`(**끝 앵커 필수** — 중간 숫자 블록·소수점 좌표 미건드림) + `source_key` 단일 정의 + manifest `source_key` 컬럼 + 조기 무결성 assert(guards 도달 전). `guards.py` stem backstop = 이중 검사 미변경.
- **빈클립 가드(PR #11)**: `01_clips/fire_alarm` 길이 0.0초 wav 6개(AI Hub S_103)가 pink-noise FFT(길이 0)에서 크래시 → `config.MIN_DURATION_SEC=0.1`(파생 `MIN_SAMPLES=1600`) + preprocess skip(1차) + augment 진입 가드(2차). 원본 무수정, 정상 클립 무영향. fire_alarm 1648 → **1642**.
- **stale auto-clean(PR #14, 학습 19 근거)**: preprocess/augment는 `save_wav`로 덮어쓸 뿐 기존 파일 미삭제 → 가드 도입 **이전**(PR #10) 실행이 02로 흘린 빈클립 6개가 재실행에도 잔존 → split이 stale 02(1648)를 읽어 05로 **부활** → 크래시. 05 `clean_final`과 동일 안전 idiom(폴더명 검증·직하위만·상위/원본/manifest 절대 미삭제)을 02/03에 일반화. `run_all --no-clean` opt-out.
- **augment 스펙**: 카테고리 5 준수(time-stretch 0.85/1.15 · BG noise SNR · volume -6dB). **pitch shift = `KOREAN_SOURCE_MARKERS` 미설정으로 현재 0개**(미결, 33.3-①). SpecAugment는 학습 시점 몫(config에 파라미터만 기록).
- **PR 이력(SSoT 확정)**: #10 구축(`de05c7e`) · #11 빈클립 가드(`adbf349`) · #12 source split(`cd9c16e`) · #13 학습골격+05 auto-clean(`01715aa`) · #14 02/03 auto-clean(`749c4a6`). ※ #11/#12는 squash 커밋 subject에 `(#N)` 미표기 — PR 번호는 GitHub API 실측 확정.

### 33.2 YAMNet 예비 학습 (`ml/training`, PR #13)

- **모델 구조**: YAMNet(TF-hub) **frozen backbone** → 1024-d 임베딩 → head `Dense(128, relu)` + `Dropout(0.5)` → `Dense(3)`. **trainable params = 131,587**(head만). 원본 2,798개론 backbone 재학습 부족 → transfer learning 정석. 라벨 인덱스(`doorbell=0/knock=1/fire_alarm=2`)는 `ml.pipeline.config.CLASSES` 단일 출처 상속(학습·평가·배포 불일치 방지).
- **class_weight**: sklearn `'balanced'` **자동 산출**(하드코딩 금지). 실측 = doorbell 2.10 / knock 1.31 / fire_alarm 0.57.
- **예비 학습 결과 (2026-07-01, py3.11 + TF2.16, CPU)**: 30 epoch 중 **early stopping(best epoch 18)**. **val_accuracy 0.902 / val_macro_f1 0.856**.
- **test 성적 (n=424, 미사용 데이터)**: **accuracy 0.887 / macro_f1 0.848**.

  | class | precision | recall | f1 | support |
  |-------|-----------|--------|-----|---------|
  | doorbell | 0.730 | 0.742 | 0.736 | 62 |
  | knock | 0.873 | 0.889 | 0.881 | 108 |
  | fire_alarm | 0.932 | 0.921 | 0.927 | 254 |

- **의의**: 사전테스트 pre-trained Top-1(초인종 30 / 노크 40 / 화재 20%) 대비 **대폭 상승** → 카테고리 4 fine-tuning 필요성 수치 확정.
- **confusion 특이점**: `doorbell → fire_alarm` 오분류 **10건(최다)**. doorbell이 최소 클래스(support 62) → **8주차 직접 녹음(초인종 90 필수, 카테고리 5)** 으로 보강 예정. ※ **안전 방향 편향**: 역방향 `fire → doorbell` 놓침은 8건뿐 = 덜 위험한 쪽으로 편향(화재 누락 최소화).
- **체크포인트**: `ml/models/yamnet/best.keras` 저장(git 미커밋, `.gitignore`).
- **SavedModel export ✅ 완료 (2026-07-01 PoC-(22), PR #15)**: `ml/training/export.py` 독립 엔트리포인트(`python -m ml.training.export`)로 **재학습 없이** `best.keras`(head) + frozen YAMNet 합성 → 서빙 SavedModel 산출. 서빙 시그니처 = 입력 `waveform (1, None) float32`(배치 1 고정·단일 클립) → 출력 `(1, 3) float32`(라벨 순서 = `CLASSES` 상속 doorbell=0/knock=1/fire_alarm=2). 산출 아티팩트 = `ml/models/yamnet/inference_savedmodel/`(git 미커밋, `.gitignore`). 방식 = `tf.saved_model.save` → **Keras 3 `model.export()`** 로 전환하여 미추적 리소스 해소. ※ **근본원인 정정**: 당초 전제("frozen hub backbone 변수 미추적")는 방향은 맞았으나 정확한 메커니즘은 **`build_inference_model`(model.py)이 raw `hub.load()` 객체를 Keras `Lambda`(`yamnet_backbone`) 클로저로 캡처 → Lambda가 클로저 trackable을 객체 그래프에 미등록** → `.export()`의 `ExportArchive`가 서빙 `tf.function` 트레이스로 캡처 리소스를 함께 추적·직렬화해 해소(학습 19 정합 — 진단 재검증 후 실측 메커니즘 반영). 학부생 로컬 실 YAMNet export + reload 추론 검증 통과.

### 33.3 미결 항목 (발표/본학습/배포 전 결정) — **활성 미결 0건** (①② 2026-07-07 PoC-(24) 결정 확정·실행 defer / ③ 2026-07-01 클로즈)

1. **pitch shift 대상** (본학습 8주차 전): `KOREAN_SOURCE_MARKERS` 빈 상태 → 한국 환경음(AI Hub S_103 / 직접녹음)에 pitch ±2semitone 적용 여부 지정 필요. 현재 대상 0개 + 경고 로그(학부생 결정 트리거).
   - 🟢 **결정 확정 (2026-07-07 PoC-(24), PR #21)**: 대상 = **직접녹음만**(`direct_` prefix), **S_103(AI Hub 화재) 제외**. 근거 = 최약 클래스 doorbell 수혜 + 규격 화재음(ISO 8201) 왜곡 회피. 위상 = 보조 수단(실 지렛대 = 직접녹음 절대량). 실행 = **defer**(04_direct_recording=0 → 값 `()` 유지 + 결정 주석 각인, `ml/pipeline/config.py:69~`). 8주차 유입 시 `KOREAN_SOURCE_MARKERS=("direct_",)` 한 줄 교체로 활성화. 경고 로그는 `log.warning`→`log.info` 완화(의도된 정상 상태 명시, 매칭 로직 무변경).
2. **SpecAugment 적용** (발표 전): hub YAMNet은 waveform-in **블랙박스** → `embedding` 모드(기본)는 내부 로그멜 마스킹 주입 불가 = **미적용**. `logmel` 모드(로컬 core 배선)면 적용 가능. **레이어 구현·검증은 완료, 배선만 남음**.
   - 🟢 **결정 확정 (2026-07-07 PoC-(24), PR #21)**: **embedding 모드 유지 / logmel 배선 defer**. hub YAMNet blackbox로 embedding 경로엔 SpecAugment 미적용(불변). 레이어(`ml/training/spec_augment.py`) 구현·검증 완료·**보존**(삭제·비활성 X). 직접녹음 유입 후 A/B 비교로 배선 결정. `ml/training/train.py:78~` 배선 지점에 defer 주석 각인. ※ `SPECAUG_MODE` 상수는 소비처(분기)가 없어 **죽은 상수** → 미신설, 주석만(학습 16).
3. ~~**SavedModel export 버그** (11주차 배포 전): untracked resource 오류로 `best.keras` → SavedModel 변환 미완.~~ → **✅ 해결 (2026-07-01 PoC-(22), PR #15)**: `ml/training/export.py`에서 `model.export()`(Keras 3) 방식으로 전환해 미추적 리소스 해소, 학부생 로컬 실 YAMNet export + reload 추론 검증 통과. 근본원인 = Lambda(`yamnet_backbone`) 클로저가 raw `hub.load()` 객체를 캡처 → 객체 그래프에 trackable 미등록(상세 = 33.2 export 항목). ※ 이력 보존(학습 8 원본 보존 패턴) — 삭제하지 않고 해결 표기.

### 33.4 학습 19 신설 — 태스크/위임 프롬프트의 근본원인 진단도 코드로 재검증

> **학습 18과 별개** (SSoT 학습 18 = "PR 웹 머지 후 로컬 main pull", 카테고리 20). MCP가 본 건을 "학습 18"로 칭한 번호 충돌을 **학습 19로 정정 확정**.

**학습 19 (근본원인 진단 재검증, 2026-07-01 신설)**: 태스크/위임 프롬프트가 박은 **근본원인 진단(가설)도 SSoT(코드)로 재검증** 대상. 지정 수정이 코드상 no-op이면 맹목 적용 금지 → 진짜 원인 규명 후 pivot 승인받고 수정.

- **사례(2026-07-01, PR #14)**: 당초 가설 = "split이 `01_clips`(1648)를 읽어 빈클립이 부활" → **틀림**. `git log -L 80,82:ml/pipeline/split.py` 확인 결과 split은 **PR #10 최초 생성 시점부터 줄곧 `02_preprocessed`를 읽었음** → "01→02 교정"은 **no-op**. 진짜 원인 = preprocess/augment의 **02/03 stale auto-clean 부재**(05 `clean_final`만 존재) → `AskUserQuestion`으로 pivot 승인 후 수정.
- **위치**: 학습 17(AI 본인도 catch 그물 대상)의 **확장** — "위임 가정" → "위임의 근본원인 진단"까지 검증 범위 확대. 학습 14(가정 검증)·18(웹 머지 후 pull)과 별개 항목.

### 33.5 SP/DTW 초인종 개체 구분 스파이크 + pretest 8.42 정체 규명 → USP 정량 근거 재정립 (2026-07-08 PoC-(25) 신설)

> USP("옆집 초인종 잘못 반응 X" = 초인종 **개체 간** 구분) 알고리즘을 8주차 선제 de-risk. (B) 스파이크 실측 + (C) 발표자료 인용 "8.42" 포렌식 규명 종합 = **오늘 최대 발견**. 위상 = 프로토타입 스파이크(`ml/experiments/dtw_doorbell/`, PR #23 `086c6da`), 프로덕션 매칭 모듈 아님. 임계 튜닝·서버 통합 = 11~12주차.

**(B) 개체 구분 스파이크 실측 (PR #23 `086c6da`)**:
- **분리 마진 1.713** (= (inter평균 − intra평균) / pooled_std, Cohen's d류) → 권고선 2.0 미달 = **NO-GO / 재검토.**
- 분포: intra(같은 원본) 0.2601 ± 0.1150 / inter(다른 원본) 0.4263 ± 0.0748. 최고 정확도 **83.6%** @0.3509 / EER **17.5%** @0.3608.
- 데이터: `01_clips` doorbell 436클립 → **182 원본그룹**(AudioSet 85 + FSD50K 97), exact DTW backend(fastdtw 미설치 → numpy 폴백, (Ta+Tb) 정규화).
- **🔴 캐비앗(대문짝)**: intra = "한 소스 녹음의 인접 조각" ≠ 독립 재-누름 → **실 변동 누락 = 낙관 상한.** 실측치는 이보다 낮을 것. **진짜 판정 = 직접녹음(04) 재-누름 intra 재검증.**

**(C) pretest "8.42" 정체 규명 (읽기전용 포렌식, 코드 무변경)**:
- 발표자료·구두 인용 "SP/DTW 분리 마진 8.42"의 출처 = pretest repo `park-taegeun/ddingdong-pretest` `step4_dtw_evaluate.py`(commit `907c950`). 실측 대상 = **(B 유형) 클래스 간 분리**(초인종 vs 노크/화재경보) = YAMNet 3종 분류의 **2차 필터 변별력**.
- '초인종 vs 초인종(같은 집)' 버킷조차 실제론 서로 다른 FSD50K 클립 = **개체("우리집 vs 옆집") 개념이 pretest 데이터에 부재.**
- ∴ **8.42는 USP(초인종 개체 간 = 옆집 구분) 근거로 무효.** 폐기는 아님 — 위상만 "**초인종 vs 타클래스 2차 필터 변별력**"으로 명문화(유효한 숫자, USP 근거로만 부적격).
- **8.42 vs 오늘 1.713 직접 비교 무효**: 측정대상(클래스 간 vs 개체 간) · 특징(log-mel dB 128bin vs power-mel L2norm 64bin) · 정규화(raw fastdtw vs (Ta+Tb) 정규화) · 마진 정의(pretest는 **정의 부재** = avg/std 표에서 수기 산출 추정) — **4중 상이.** 서로 다른 문제를 잰 값.
- 확신도: 측정대상 = 클래스 간 → **높음**(pretest README L12 + `step4` 코드 + FSD50K 클래스 폴더 데이터 3중 일치). 정확한 8.42 산술 재현 → **낮음**(pretest 샘플·출력 미커밋, repo·git 히스토리 전체에 "8.42" 문자열 부재).
- ※ **8.42는 본 SSoT(decisions.md)에 원래 부재** — grep 0건 확인. 따라서 "취소선 정정" 대상 문구 없음 = **순수 신설 note로 위상 명문화**(없는 문구 취소선 = 날조 회피, 학습 19).

**USP 정량 근거 재정립**:
- 초인종 **개체 간** 분리 = pretest 미검증 확정. 현 최선 실측 = 스파이크 마진 1.713(낙관 상한) → 권고선 2.0 미달.
- 재검증 경로 = 직접녹음 90클립(재-누름 intra)으로 스파이크 코드 재실행(`ml/experiments/dtw_doorbell/`, `--clips-dir` = 04_direct_recording). 11~12주차.

### USP 2층 재정립 (2026-07-09 PoC-(26))
- 옆집 구분 메커니즘을 **2층 구조**로 재정립: **1차 = ToF 사람 존재 검증**(카테고리 9 Stage A/B, VL53L5CX 단독) / **2차 보조 = SP/DTW 오디오 지문**(등록 시). 이전 "USP 붕괴" 판정은 SP/DTW **단층 평가 아티팩트** — 8.42는 폐기 아님(클래스 간 2차 필터 변별로서 유효), 다만 "옆집 구분 주력 근거"라는 위상이 mislabel이었음.
- 논리: 우리집 초인종 = 문 앞 사람 있음(ToF 감지) → 알림. 옆집 초인종 = 소리만 벽 타고 새어듦, 문 앞 사람 없음(ToF 억제) → 미알림. 등록 시 SP/DTW = 오디오 지문 보조 매칭.
- **정직 표기(양층 런타임 미검증)**: ToF presence = 설계 견고하나 미측정(브레드보드 결선 후 측정). SP/DTW = 1.713 낙관 상한(직접녹음 4유닛 재검증 대기, 위 (B) 참조). 현재 위상 = "2층 설계 확정 + 양층 검증 예정"(근거 없음 아님, 미결정 아님) — 26.3 진입점 2 연동.
- **데모 방향**: ToF presence 리드 시연(우리집=사람+소리→알림 / 옆집=스피커 소리만·사람 없음→억제 / 등록=SP/DTW 오디오 보너스). SP/DTW 4종 라이브 단독 시연 = **NO**(1.713 약함 발표 노출 회피). 구체 시연 스크립트 = 데모 재설정 chunk 소관.

**미결 항목 (발표/통합 전)**:
1. ~~**USP 정량 근거 재정립** (발표 전): 8.42 = 클래스 간(2차 필터)로 위상 정정, 개체 구분은 직접녹음 재검증 대기(11~12주차). **발표 슬라이드의 8.42 "옆집 구분 근거" 인용 = 정정 대상.**~~ → **(2026-07-09 PoC-(26) 진화) USP 2층 설계 확정**(ToF presence 1차 융합 + SP/DTW 보조 2차). 양층 런타임 검증 대기(ToF=브레드보드 후 / SP/DTW=직접녹음 4유닛). 발표 슬라이드 = ToF 융합 서사로 재작성, 8.42는 2차 필터 변별로 재배치(폐기 아님).
2. ~~**인용 논문 위상 재검토** (발표 전): Meliza 2013 (PMC3745477) = 개체 구분 근거로 인용됐으나 개체 구분 자체가 미검증 → 논문 위상 재검토 필요(decisions-log 2025-04 SP/DTW 근거 항목 연동).~~ → **(2026-07-09 PoC-(26) 진화)** Meliza 2013(PMC3745477) 위상 = SP/DTW **보조층** 근거로 조정 완료(주력 근거 아님).
3. ~~**★ 별도 코드 태스크** (문서 아님, 본 태스크 §7 코드 무수정): `ml/experiments/dtw_doorbell/constants.py:25` `PRETEST_MARGIN = 8.42` 주석 "**pretest 분리 마진(카테고리 근거)**" = 존재하지 않는 SSoT 근거를 가리키는 **오도성 주석** → "**클래스 간 변별(pretest), USP 개체구분 근거 아님**"으로 정정 필요. 별도 코드 PR로 처리.~~ **✅ 해소 확인 (2026-08-07 PoC-(34))**: `git show HEAD:ml/experiments/dtw_doorbell/constants.py` 실측 = 주석이 이미 "`클래스 간 변별(pretest), USP 개체구분 근거 아님 — 실측 정합 비교 기준`"으로 정정 완료 상태. 코드는 이미 SSoT 정합, **문서만 미표기였던 stale** — 본 커밋으로 해소.

---
