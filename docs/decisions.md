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
- **핀 페리페럴**: 마이크 I2S1 ↔ 카메라 분리, strapping 핀(D0/D3/D6/D7) 회피. ★ **분리 근거는 「카메라 = I2S0」이 아니다** — ESP32-S3의 카메라는 **LCD_CAM 페리페럴**이며(ESP32 원조 프레이밍 오기 = 27.8(m)④), 실제 근거는 **핀 교집합 ∅ + I2C 포트 분리**(카메라 SCCB 포트1 / `Wire` 포트0)다(카테고리 2 · 6.6). **결론(분리됨)은 무변경**이다.

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
| OV3660 카메라 | XCLK | - | 10 | LCD_CAM |
| OV3660 카메라 | SIOD / SIOC (SCCB) | - | 40 / 39 | I2C **포트 1** |
| OV3660 카메라 | Y9~Y2 (데이터 8비트) | - | 48 / 11 / 12 / 14 / 16 / 18 / 17 / 15 | LCD_CAM |
| OV3660 카메라 | VSYNC / HREF / PCLK | - | 38 / 47 / 13 | LCD_CAM |
| OV3660 카메라 | PWDN / RESET | - | **-1 (미사용)** | - |

🆕 **[카메라 5행 신설 — 2026-09-18 PoC-(52), 근거유형 = 실측 코드 대조 `firmware/include/camera_common.h`]** 본 표에는 그동안 **카메라 행이 없었다**(대조군 = 같은 표에 INMP441 4행 · VL53L5CX 4행 생존). 실동작 핀은 **14개**이며 `PWDN`/`RESET`은 `-1`로 미사용이다.
- **핀 교집합 = ∅** — 마이크 I2S1 `{2, 3, 7}` · ToF I2C `{5, 6}` · 카메라 위 14핀은 서로 겹치지 않는다(근거유형 = 실측).
- ★ **I2C 포트가 갈린다 (근거유형 = 실측 설치 파일 대조)**: 카메라 SCCB는 sdkconfig `CONFIG_SCCB_HARDWARE_I2C_PORT1=y`로 **포트 1**, ToF가 쓰는 Arduino `Wire`는 `TwoWire Wire = TwoWire(0)`로 **포트 0**이다. ⇒ **카메라·ToF 동시 구동의 근거는 핀 분리만이 아니라 I2C 포트 분리이기도 하다.** 실측 = **6.6**.

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
  - ~~**⚠️ [미결 — §9 사용자 판단 요청] 화재경보가 신뢰도 게이트도 우회하는가 (2026-09-02 감사 G12)**: 위 "클래스별 ToF 정책 분기" ①과 "신뢰도 임계값" ②가 코드상 함께 참조될 때 범위가 불명확하다.~~ → **✅ [G12 확정] 2026-09-08 사용자 확정 — 화재경보는 ①(ToF 게이트)만 우회하고 ②(신뢰도 게이트)는 우회하지 않는다.** 아래 ①②·코드 실측·실경로 재현 서술은 **확정 이전의 이력으로 보존**한다(삭제 X). 확정 상세 = 본 블록 마지막 「[G12 확정]」 항목.
    - ① "화재경보: ToF 우회 (무조건 발송)"
    - ② "신뢰도 임계값: 70% 미만 미전송"
    - 코드 실측(`server/app/utils.py`): `fire_alarm` 분기(78행대, `if predicted_class == "fire_alarm":`)가 신뢰도 비교(87행대, `if confidence < CONFIDENCE_THRESHOLD:`)**보다 먼저** 위치해 즉시 `return`한다 — 즉 현재 구현은 **화재경보가 ①뿐 아니라 ②도 함께 우회**하는 쪽으로 되어 있다(저신뢰 화재경보도 1차 발송됨).
    - **본 문서는 결론을 내리지 않는다**(문서 전용 세션, §9 대상). ①의 "무조건"이 ToF 게이트 문맥에 한정되는지 신뢰도 게이트까지 포함하는지, doorbell→fire_alarm 오분류가 confusion matrix상 10건으로 최다인 점이 시연 리스크가 되는지, 화재경보는 지속음이라 miss해도 다음 트리거에서 재포착되는지 — 이 판단들은 **사용자 결정 필요**.
    - **[상태 갱신] 실경로 재현 확인 (실측 2026-09-05 / 문서 반영 2026-09-05, 근거유형 = 실측)**: mock 예측 반복 호출에서 `fire_alarm` 신뢰도 **0.91 / 0.82 / 0.66 / 0.58 / 0.53 / 0.47** 건이 관찰됐고, 임계값 0.70 **미만인 건들도 1차 카카오톡이 발송**됐다 — 위 코드 실측의 "저신뢰 화재경보도 1차 발송됨"이 **실경로에서 재현**된 것이다(2026-09-03 A-1 실측 때는 mock 랜덤이 0.92라 미재현이었다). ⚠️ **본 갱신도 결론을 내리지 않는다** — 상태만 "코드 실측 → 실경로 재현 확인"으로 올리며, 판단은 여전히 사용자 대기다. → **[2026-09-08 해소] 아래 [G12 확정] 항목으로 판단이 내려졌다.**
    - **✅ [G12 확정] 화재경보도 신뢰도 게이트를 우회하지 않는다 (결정 2026-09-08 PoC-(42) / 결정 주체 = 사용자 / 근거유형 = 논증, 입력 실측 = 33.2 confusion matrix + 아래 실경로 재현 / 구현 = PR #46 `82a4870`)**
      - **결정 내용**: 신뢰도 임계값 비교를 `fire_alarm` early return **앞으로** 옮긴다. `fire_alarm`의 **ToF presence 게이트 우회는 유지**한다. 즉 화재경보도 **신뢰도 0.70 미만이면 1차 미발송**(`skip_reason=low_confidence`)이고, 0.70 이상이면 ToF presence와 무관하게 발송한다. ①의 "무조건"은 **ToF 게이트 문맥**으로 확정, ②는 **클래스 무관 전역 게이트**로 확정.
      - **판단 근거 3 (근거유형 = 논증)**: ① 원 결정의 "무조건 발송"이 ToF 게이트 문맥에 한정되는지 신뢰도 게이트까지 포함하는지 **문면상 갈리지 않았다** — 확정이 필요했던 것은 코드가 아니라 문장이다. ② 부스 시연에서 초인종을 눌렀는데 화재 대피 알림이 나가면 **그 자체가 사고**다(33.2 confusion matrix `doorbell → fire_alarm` 오분류 **10건 = 최다**). ③ 화재경보는 **지속음**이라 1회 miss의 비용이 비대칭적으로 크지 않다 — 다음 트리거에서 재포착된다.
      - **실경로 재현 = 상시 동작이었다 (근거유형 = 실측)**: 2026-09-05 저신뢰 발송(**0.66 / 0.58 / 0.53 / 0.47**) + 2026-09-08 **`fire_alarm 0.45` 발송**. **잠복 결함이 아니라 상시 동작**이었다.
      - **불변 항목 (근거유형 = 실측, `git show 82a4870` 대조)**: `CONFIDENCE_THRESHOLD` 값(**0.7**)과 strict `<` 비교는 **무변경**. 바뀐 것은 **비교 시점**뿐이다. `fire_alarm_bypass` reason 어휘, ToF 게이트를 신뢰도 비교 뒤에 두는 배치도 불변. ∴ **0.70 경계 실증 3회**(2026-09-03 / 09-05 / 09-08)는 그대로 유효하다.
      - **커밋 타입 `🐛 Fix` 선택 근거 (근거유형 = 논증)**: 종전 코드는 본 카테고리 SSoT ②("70% 미만 미전송")를 **위반**하고 있었다 → 신규 기능(`✨ Feat`)이 아니라 **위반 정정**이다.
      - **회귀 (근거유형 = 실측)**: 83 → **89**건 전건 통과(신규 6 = 경계 0.70 / ToF 우회 유지 / 전 분기 48조합 → 고유 4행). 기존 고정 케이스 1건은 **갱신(삭제 아님)** — 이 지점이 미결이던 이력을 보존.
      - ★ **파급 = 본 카테고리 ② "신뢰도 임계값: 70% 미만 미전송"은 이제 3클래스 전부(초인종 / 노크 / 화재경보)에 적용된다.** 클래스별로 갈리는 것은 **ToF 게이트뿐**이다. 위 "클래스별 ToF 정책 분기"의 "화재경보: ToF 우회 (무조건 발송)"은 **ToF 문맥 한정**으로 읽어야 한다.
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
- **클래스 가중치**: ~~class_weight + sample_weight 1.5~2.0배 (한국 환경음)~~ → 🔴 **정정 (2026-09-17 PoC-(51), 근거유형 = 실측 전수 grep)**: `SAMPLE_WEIGHT_RANGE = (1.5, 2.0)`은 `ml/pipeline/config.py`에 **상수로만** 존재하고 `ml/` · `server/` 전수 grep에서 **소비처 0건**이다(대조군 = 같은 grep에서 정의 1건 생존). 실제로 학습에 걸리는 것은 `data.compute_class_weights` = sklearn `balanced`(`n_total / (n_classes · n_c)`) **자동 산출**뿐이며, 이는 「한국 환경음 1.5~2.0배」와 **다른 메커니즘**이다. ~~⚠️ **구현할지 서술을 실물에 맞출지 = 사용자 판단 대기**(웹 수집과 무관한 별건).~~ → 🆕 **부분 확정 (사용자 결정 D6 — 2026-09-21 PoC-(55), PR #69 `0461a94`, 근거유형 = 사용자 결정 + 실측)**: **「서술을 실물에 맞춘다」로 확정**됐고 `ml/pipeline/config.py`의 주석이 *「학습 스크립트가 소비」*에서 **「소비처 0건」**으로 교체됐다(**상수 값 `(1.5, 2.0)` · 존재 무변경**, 🗃️ Comment 커밋 분리). 🔴 **「구현할지」 축은 닫히지 않았다** — 같은 주석이 지금도 *「구현할지 서술만 맞출지는 사용자 판단 대기」*라 적는다(실측) ⇒ **부분만 닫힘**이다. 상세 = **5.2** · **33.12(a)**.
- **제외**: FSD50K Alarm 435, AudioSet fire_alarm 100 (대부분 차량 사이렌)
- **저장 정책**: 8주차 진입 시 재정의 (현재 `ml/` 폴더는 `.gitkeep`만)

### 5.1 데이터 저장 정책 확정 + 실측 배분 (2026-07-01 신설 — 위 계획값 append, 훼손 X)

> ML 크리티컬 패스 선작업(2026-07-01) 실측. 위 "확보량/분할 결과/저장 정책"은 **계획값**(파일단위 가정) → 본 5.1이 **실측 확정값**. 상세 = 카테고리 33 + decisions-log 2026-07-01.

- **직접녹음 파일명 확장 (2026-07-09 PoC-(26))**: `direct_doorbell_{유닛}_{테이크}.wav`(예: `direct_doorbell_A_01.wav`). 근거 = USP 재검증(DTW 스파이크)의 원본그룹핑이 **유닛을 알아야 재-누름 intra 측정 가능** — 기존 `direct_doorbell_001`은 파일=원본그룹이라 재-누름이 전부 inter로 구조적 오분류(측정 불가). `direct_` prefix 유지 → pitch 마커(33.3-①) 호환. ~~※ **DTW 스파이크에 유닛 그룹핑 모드 추가 필요**(`--clips-dir` 04 재실행 전, 소액 PR = 후속).~~
  - **✅ 해소: PR #31 (2026-08-03 PoC-(33), `a332343`)**: 자동 `direct_` prefix 분기(KOREAN_SOURCE_MARKERS 컨벤션 정합) 추가 → `--clips-dir 04` 재실행만으로 재-누름 intra 측정 가능. 회귀 근거 = 01_clips **436→182 그룹 불변 + 멤버십 sha256 before==after 동일**(1.713 재현성·비교가능성 보존) + 단위테스트 19/19, 마진 공식·거리·정규화·출력 무변경. ⚠️ **04=0이라 실 개체 마진 미산출**(그룹핑 로직+회귀 검증까지만) — 실측 = 직접녹음 유입 후 defer(학습 19).
- **4유닛 녹음 프로토콜 확정 (2026-07-09 PoC-(26))**: 시연 도어벨 **4개**(★ 같은 모델 ×2 필수 — 옆집 최악 케이스=동일 제품) × 15~18테이크 ≈ 90클립. inter = C(4,2)=**6쌍**(같은모델 1쌍 + 다른모델 5쌍). 3유닛 검토했으나 4유닛 확정(inter 6쌍이 벤치 신뢰도 = 1.713 상한 교훈 = 오염 벤치 회피). 부스엔 필요시 3개, 녹음은 4유닛.
  - 🟡 **[등재] 시연 도어벨 4유닛 구매 요건 확정 (2026-09-03 사용자 확정, PoC-(45) 문서 반영, 근거유형 = 사용자 확정)**: 위 4유닛 = **2종×2개**(A1·A2 같은 모델 다른 개체 = SP/DTW 최악 케이스 / B1·B2 다른 모델 = 음색 다양성). 구매 조건: ① **음량조절 필수**(INMP441 헤드룸 소진 구간 — 6.3(k) 헤드룸 반증과 연동) ② 건전지형 송수신기 세트 ③ "딩동" 계열, 4유닛 전부 **같은 프리셋** ④ 빠른배송. 개당 **7,000~25,000원**.
    - 🆕 **[현재값 주석 — 2026-09-16 PoC-(50), 근거유형 = 산술 + 프로젝트 지침 인용]** 위 **2종×2개(A1·A2 / B1·B2)** 확정 기준으로 다시 세면 `inter = C(4,2) = 6쌍`의 내역은 **같은 모델 2쌍(A1-A2 · B1-B2) + 다른 모델 4쌍**이다. ★ **위 2026-07-09 항목의 「같은모델 1쌍 + 5쌍」에 취소선을 긋지 않는다** — 그것은 **당시 구성(같은 모델 ×2 + 서로 다른 2종) 기준의 이력 서술**이고 **틀린 계산이 아니다**. 바뀐 것은 **구성**이다.
    - **선택 근거 [논증 — 출처 = 프로젝트 지침 11항, SSoT 첫 등재]**: **같은 모델 쌍이 1개뿐이면 그 쌍의 값이 우연인지 가를 수 없다** — 비교 대상이 없어 단일 관측이 된다. ∴ **A×2 + B×2**로 같은 모델 쌍을 **2개** 만들어 재현성을 확인할 수 있게 한다. ⚠️ **실 개체 마진은 여전히 미산출**(04 = 0)이다 — 위 PR #31 항목의 경계 표기 그대로.
- **저장 위치 확정**: 데이터셋은 원래 repo 밖 형제 폴더 → **OS TCC(EPERM)** 로 Claude Code 접근 차단(카테고리 저장소 룰 reference `repo_sibling_tcc_block`) → **학부생 홈 `~/ML 학습 데이터/ddingdong_dataset` 로 이동 확정**. repo엔 **오디오 미커밋**(`.gitignore` `*.wav` 등), **코드/config/manifest 스키마만** 버전관리. 실 파이프라인·학습 실행 = 학부생 로컬 셸(`DDINGDONG_DATA_ROOT="…" python -m ml.pipeline.run_all`).
- **폴더 구조 실측(6단계)**: `00_source_raw`(FSD50K 4만 dump 포함, **입력 아님**) / `01_clips`(**정본 입력 2,798** = doorbell 436 / knock 714 / fire_alarm 1648, 16k mono Int16) / `02_preprocessed` / `03_augmented` / `04_direct_recording`(현재 **0**, 8주차 직접 녹음 유입 슬롯) / `05_final_dataset`(조립 산출).
  - ⚠️ **[단서 — 2026-09-14 PoC-(47) 실측 `ls`]** 위 6단계 **외에** `01_extracted` · `manifests` **2개 폴더가 실물로 존재**한다. ~~🔴 **역할·내용은 미확인**이다 — 파이프라인 입력인지 중간 산출인지, 위 6단계와 어떤 관계인지 **확정하지 말 것**. **존재 사실까지만** 등재하며~~ → 🆕 **부분 해소 (2026-09-15 PoC-(48), 근거유형 = 실측, 계수 단위 = 클립 수 / 행 수 — 아래 sub-bullet)**. 위 6단계 서술은 **무변경**이다(취소선 대상 아님).
    - **`01_extracted`** = 클래스 **3폴더**(doorbell **107** / knock **270** / fire_alarm **171**, 계 **548** 클립). 파일명이 **순수 숫자 ID**로 `01_clips`의 AudioSet 네이밍(`<유튜브ID>_<초>_<초>_<오프셋>`)과 **계열이 다르다**. 두 매니페스트의 `filepath` 열에 `01_extracted` **0건**(대조군 = `02_preprocessed` **2792행** · `05_final_dataset` **12447행** 생존) ⇒ **학습 경로 미참조**다. 🔴 **파이프라인상 위치·소스 귀속은 여전히 미확정**이다(논증 단계 — 파이프라인 코드 미확인). **확정하지 말 것.**
    - **`manifests/final_manifest.csv` [신규 등재]** = **12,447행** 전건이 `05_final_dataset`을 가리키며 컬럼 = `filepath,class,split,origin,source_stem`. **12447 = 원본 2792 + 증강 9655**(snr **3862** / ts **3862** / vol **1931**)로 **산술 일치**한다.
    - 🔴 **`split_manifest.csv`와는 다른 문서다** — 후자는 **2792행**이고 `02_preprocessed`를 지시하며 컬럼 = `filepath,class,split,stem,source_key`다. ⇒ **split의 SSoT = `split_manifest.csv`이며 무변경**이다. `final_manifest.csv`는 **split 정의가 아니다.**
- **빈 클립 6개 실측**: `01_clips/fire_alarm` 의 AI Hub S_103 원본 6개가 **length-0 wav** → preprocess가 skip(fire_alarm 1648 → **1642**). 원본 삭제 X, **코드 가드로 처리**(PR #11 skip + PR #14 stale auto-clean). 상세 = 카테고리 33.1.
  - 🆕 **[2026-09-15 PoC-(49) 실측 포인터]** 이 **6개는 서로 바이트 동일**(각 **78 B**)이며 `01_clips`에만 있는 중복 그룹의 **전부**다. 또한 `01_extracted` 내부에서 **0바이트 빈 파일 30개**(doorbell 10 / knock 20)가 별도로 실측됐다 ⇒ **「길이 0」이 두 폴더에 걸쳐 존재**한다. 상세 = **33.7(g)**.
- **05 실측 배분(원본단위 group split + train만 augment 반영)**: **train 11,586 / val 437 / test 424**. 위 계획값(train 1954/val 434/test 410, 파일단위 가정)과 다름 = ① 원본(source) 단위 그룹 분할(누수 방지, PR #12) ② train만 증강 유입 ③ fire_alarm 빈 6개 제외 반영. 상세 = 카테고리 33.2.
  - 🆕 **[2026-09-15 PoC-(48) 실측]** `05_final_dataset/test` **424 파일 집합**이 `split_manifest.csv`의 test split과 **`stem` 전건 일치**(diff **0**, 표본 md5 일치)다. 33.6(b)의 「**개수 일치**」보다 **강한 확인**이다. 합계 **11,586 + 437 + 424 = 12,447** = `final_manifest.csv` 행 수와 일치한다.
  - 🔴 **[2026-09-15 PoC-(48)] 위 「누수 방지」의 범위 경계**: 원본단위 group split은 **파일명(`source_key`) 기준 그룹화**라 **내용이 동일한 파일은 애초에 방어 범위 밖**이다. **바이트 동일 파일에 의한 train/test 누수가 실측**됐다(test **79 / 424**). ⚠️ 위 「누수 방지, PR #12」 서술은 **틀린 것이 아니라 범위가 좁았다** — **취소선 대상이 아니다.** 수치·경계·한계·대응(**사용자 판단 대기**) = **33.7**.

### 5.2 한국 초인종·인터폰 웹 음원 조사 — 파이프라인 유입 요건 + split 파급 (2026-09-17 PoC-(51) 신설, 발견일 = 반영일 = 2026-09-17, 근거유형 = 항목별 병기)

> **조사 전용** 세션이다 — repo 쓰기 0 / 다운로드 0 / 설치 0 / 데이터셋 변경 0. 리포트 원본 = repo 밖 `~/ddingdong-측정결과/2026-09-17/web_audio_research/`(`.gitignore` 차단분 — SSoT엔 요약만). **결정·정책·수치 신설 0건**이며 전건 **사용자 판단 대기**로 남긴다.

**(a) 유입 경로 — `04_direct_recording` → `01_clips` 코드가 없다 (근거유형 = 실측 전수 grep)**

- `preprocess()`의 입력원은 `src_dir = paths.clips / cls` **하나뿐**이고, `04_direct_recording` 문자열의 repo 전수 grep 결과는 `docs/decisions.md` · README · dtw `--clips-dir` 인자 설명뿐 — **읽는 코드 0건**이다. `config.py`가 스스로 「파이프라인이 절대 건드리지 않는 폴더: `00_source_raw` / `01_extracted` / `04_direct_recording`」이라 적는다.
- ⇒ 파일을 `01_clips/{class}/`에 두면 **코드 변경 0**으로 유입되지만, **그 복사는 사람이 하는 수동 단계**이고 repo에 스크립트가 없다. ⚠️ 인계 계층의 「녹음이 들어오면 마커 한 줄 교체 + `run_all` 재실행」 취지 서술은 **이 사실과 어긋난다**(등재는 **지침 계층 소관** — 본 절은 실물만 적는다).
- 유입 전 **16kHz mono** 변환이 없으면 `preprocess()`가 samplerate/channels/frames 3가드에서 **로그만 남기고 조용히 skip**한다(중단 없음).
- 🆕 **[포인터 — 발견일 = 반영일 = 2026-09-20 PoC-(54), 근거유형 = 실측, 상세 = 33.10]** **파이프라인 입구 코드의 소재가 확인**됐다 — 조각내기·분할 스크립트 **7개**가 **별개 로컬 repo** `~/Desktop/xorms/프로젝트/ddingdong/pretest/scripts/`에 실재한다(33.7(i) 미결의 「소재 미확인」 축이 채워졌다). 🔴 **위 「`04_direct_recording` → `01_clips` 유입 경로가 코드에 0건」은 무변경**이다 — 그 7개도 이 경로를 만들지 않는다(세 전처리 스크립트는 `00_source_raw` · FSD50K dump에서만 읽는다). ⇒ **「그 복사는 사람이 하는 수동 단계」라는 위 판정도 무변경**이다.

**(b) 명명 — `direct_doorbell_{유닛}_{테이크}`는 테이크마다 source가 갈린다 (근거유형 = 실측)**

- `PIECE_SUFFIX_PATTERN = re.compile(r"_\d{7}$")`이고 `source_key()`는 `sub(..., count=1)`이다. `direct_doorbell_A_01`은 끝이 **2자리**라 제거 대상이 없어 **stem 전체 = source_key** ⇒ **테이크 1개 = source 1개**로 split에 흩어진다.
- `dtw_doorbell`의 `group_key()`는 `direct_` prefix면 `unit_id()`(끝 `_숫자`를 테이크로 간주) 분기를 타므로, **웹 수집분에 `direct_`를 붙이면 서로 다른 원본이 한 「유닛」으로 묶여 재-누름(intra)으로 오계상**된다. ⇒ 웹 수집분 명명·pitch 대상 포함 여부 = **사용자 판단 대기**(33.3① 「한국 환경음 = 직접녹음만」 정의를 건드린다).
- 🆕 **부분 해소 (사용자 결정 D3 · D5 — 2026-09-21 PoC-(55), PR #69 `0461a94`, 근거유형 = 사용자 결정 + 실측)**: **D3** = 직접녹음은 **유닛까지를 그룹 키**로 삼는다 — `config.source_key()`가 조각 suffix 제거 **후** 남은 끝 `_{테이크}`(`_\d+$`)를 한 번 더 제거하는 `direct_` 분기를 갖는다(`DIRECT_RECORDING_PREFIX` · `DIRECT_TAKE_PATTERN`) ⇒ **위 「테이크 1개 = source 1개」는 해소**됐고, `dtw_doorbell.group_key()`와 **같은 결과**를 내도록 맞춰 단위 테스트로 고정했다(유닛 A **2** · B **1**). **D5** = **웹 음원은 외부 평가 전용**이다 ⇒ 웹 수집분이 `01_clips`에 들어가지 않으므로 **「`direct_`를 붙이면 재-누름으로 오계상」 위험은 당면 경로에서 사라진다**. 🔴 **그러나 웹 수집분의 명명 · pitch 대상 범위 자체는 확정되지 않았다**(투입 시점이 오면 다시 걸린다) ⇒ **부분만 닫힘**. 상세 = **33.12(a)(d)**.

**(c) 🔴 split 파급 — doorbell source 1개 추가가 knock split을 흔든다 (근거유형 = 실측 재현)**

- `split_dataset()` 안에서 `rng = random.Random(config.SEED)`가 `for cls in config.CLASSES` **바깥**에 1회 생성돼 클래스마다 `rng.shuffle`을 **공유**한다.
- **baseline 재현 = 813 source 전건 일치**(불일치 0 / 813, 계수 단위 = source 수) — 셔플·배분 로직을 표준 라이브러리로 복제한 결과가 `split_manifest.csv`와 같다. **도구 신뢰를 먼저 확인한 뒤** 아래를 쟀다.
- **doorbell에 신규 source N개 추가 시 배정이 바뀌는 수**(계수 단위 = source 수 / 클립 수, 분모 = 기존 총수):

  | N | doorbell | knock | fire_alarm |
  |---|---|---|---|
  | 1 | 11 / 182 src · 31 / 436 clip | **45 / 360 src · 124 / 714 clip** | 0 / 271 src · 0 / 1642 clip |
  | 10 | 13 / 182 · 32 / 436 | 57 / 360 · 152 / 714 | 0 / 271 · 0 / 1642 |
  | 30 | 11 / 182 · 32 / 436 | 98 / 360 · 225 / 714 | 109 / 271 · 648 / 1642 |
  | 90 | 63 / 182 · 157 / 436 | 155 / 360 · 336 / 714 | 132 / 271 · 809 / 1642 |

- **[실측] doorbell에 단 1개를 더해도 knock 클립 124 / 714의 train/test 소속이 바뀐다.**
- ⚠️ **[실측] N=1 · 10에서 fire_alarm이 0인 것은 우연이지 안전장치가 아니다** — `random.Random(42)`로 `shuffle(182+N)` → `shuffle(360)` 후 다음 난수 3개가 N=0 / 1 / 10에서 동일하고 N=30 / 90에서 상이하다(Mersenne Twister의 워드 소비량이 우연히 맞은 구간).
- ⚠️ **[실측] 파급은 N에 단조 증가하지 않는다**(doorbell src변경 11 → 13 → 11 → 63).
- ⇒ **[논증] 웹 음원을 `01_clips`에 넣고 파이프라인을 재실행하는 순간 33.2의 f1 · 33.6의 게이트 축 · 33.7의 누수 수치가 전부 「다른 test set 위의 값」이 된다.** 33.7 누수 대응(사용자 판단 대기)과 **순서 의존**이다 — split이 재배치되면 이미 측정된 누수 79건의 구성 자체가 바뀐다.
- 🟢 **[실측] 외부 평가 경로는 이 얽힘이 없다**: `ml/training/evaluate.py`는 `{임의폴더}/05_final_dataset/test/{class}/`를, `server/tools/gate_axis_sweep.py`는 `{임의폴더}/manifests/split_manifest.csv`의 `split=test` 행을 읽으므로 **둘 다 코드 0줄 변경**으로 외부 세트를 받는다. 기존 05 · 매니페스트 **무접촉**이다. ⚠️ 단 후자의 사용 주의는 **33.8**.
- 🆕 **✅ 메커니즘 해소 (사용자 결정 D2 — 2026-09-21 PoC-(55), PR #69 `0461a94`, 근거유형 = 사용자 결정 + 실측, 계수 단위 = source 수 / 클립 수)**: **공유 `rng` + 셔플 + 개수 맞춤 배분(`_allocate`)이 폐지**되고 **그룹 해시 고정 배정**(`split.assign_split()` 순수 함수)으로 바뀌었다 ⇒ **「doorbell source 1개 추가가 knock split을 흔든다」는 메커니즘 자체가 없어졌다**. 실측 = **doorbell source +1에 기존 24 source의 배정 변경 0건**(단위 테스트 T4). 🔴 **위 표와 4개 관측(N 비단조 · N=1·10의 `fire_alarm` 0이 우연이라는 단서 등)에는 취소선을 긋지 않는다** — **2026-09-17 시점 코드에 대한 실측 이력**이며 **틀린 값이 아니다**. ⚠️ **「재실행하는 순간 33.2 · 33.6 · 33.7 수치가 다른 test set 위의 값이 된다」는 위 결론은 무변경**이고, **새 배정 기준에서 실제로 바뀌는 규모가 실측**됐다 — source `doorbell` **87** · `knock` **170** · `fire_alarm` **130**, test 클립 **424 → 335**(상세 = **33.12(c)**).

**(d) 학습 ↔ 서빙 음량 처리 비대칭 (근거유형 = 실측 코드 대조, 영향 미판정)**

- 학습 경로는 `preprocess()`가 `PEAK_NORMALIZE=True`로 `peak_normalize(y, TARGET_PEAK=0.95)`를 **파일에 구워** 02에 저장하고 05까지 전파한다. `ml/training/data.py`는 재정규화하지 않는다.
- 서빙 경로 `server/inference/audio_decode.decode_pcm16`은 `astype(np.float32) / NORM_DIVISOR`(÷32768)**만** 한다.
- ⇒ **두 경로의 입력 음량 분포가 다르다**는 사실까지만 등재한다. ⚠️ **영향은 판정하지 않는다** — 33.6(e) 계열의 「자리 차이」 축과 섞어 읽지 말 것. 관련 관측 = **33.6(g)**의 음량 축.

**(e) 웹 재고 조사 결과 (근거유형 = 항목별 병기)**

- 🔴 **[실측] AI Hub 「도시 소리 데이터」(73,864건 · 485.4h)의 대3 / 중10 / 소24 분류에 초인종 · 도어벨 · 인터폰 · 차임 클래스가 없다.** ⇒ 가장 큰 공개 한국 음향 데이터셋이 **이 목적에 쓸 수 없다**.
- **[문서 인용] 공유마당 CC BY 음원**에 인터폰벨 · 초인종 계열 연번이 존재한다 — 실물 확보·파일럿 = **33.6(g)**. ⚠️ **스튜디오 폴리 음원이지 실제 월패드 원음이라는 근거는 없다**(잔향·룸톤 부재 = 도메인 갭).
- **[논증] 「없던 음색(한국 아파트 인터폰)을 채운다」는 목적에 정면으로 맞는 웹 재고는 확인되지 않았다.** 유형별 실제 음색이 있을 곳(현장 녹음형)의 재고량은 **도구 한계로 측정하지 못했다** — 추정치를 적지 않는다.
- **[논증] 웹 수집은 직접 녹음 90개의 대체가 아니라 보완이다**: 웹이 채우는 것은 **다른 벨소리의 수**이고, 직접 녹음이 채우는 것은 **개체 구분(5.1 4유닛 재-누름)** 과 **INMP441 채널 특성**이다. `unit_id` 그룹핑이 웹 음원에는 성립하지 않는다(위 (b) 실측).
- ⚠️ **[실측] 보드 재녹음을 데이터로 남기는 경로가 코드에 없다** — `server/app/` · `server/inference/` 전수 grep에서 **wav 디스크 저장 0건**이고 `image_store.py`에 대응하는 오디오 모듈이 없다(`/detect`는 `decode_pcm16` 후 파일로 남기지 않는다). ⇒ 「코드가 있는데 안 켠 것」이 아니라 **없다**.

**(f) ~~🔵 [논증 — 미실증]~~ → ✅ 해소 (발견 2026-09-18 / 문서 반영 2026-09-19 PoC-(53), 근거유형 = 실측, 상세 = 33.7(h)) `01_extracted` 짝 없는 파일 수와 33.7(g) 0바이트 파일 수가 일치한다 — 같은 집합으로 확정**

- `01_clips`의 비-AudioSet source_key는 **전건**(doorbell 97 / 97 · knock 250 / 250 · fire_alarm 171 / 171) `01_extracted`에 같은 stem으로 존재한다(계수 단위 = 키 수, 근거유형 = 실측).
- ⇒ 짝이 없는 `01_extracted` 파일 수는 **doorbell 10 / knock 20**이며, 이는 **33.7(g)가 실측한 `01_extracted` 내부 0바이트 빈 파일 30개(doorbell 10 / knock 20)와 같은 수**다. ~~🔴 **같은 파일인지는 미확인**이다 — **논증이며 확정하지 말 것.**~~ → ✅ **[실측 2026-09-18]** `01_extracted` **0바이트 파일 30개**(doorbell 10 / knock 20) = `01_clips`에 **짝 없는 30개** — **양방향 차집합 0 / 0, 같은 집합으로 확정**(계수 단위 = 파일 수). ⚠️ 파일명이 순수 숫자로 fsd50k 계열 네이밍과 같으나 **귀속 실측은 범위 밖**(이름만 대조). 🆕 **mp3 171 (근거유형 = 실측, 이름만)**: `00_source_raw/aihub_alarm` mp3 171 이름 집합 = `01_extracted/fire_alarm` mp3 171 이름 집합 — **양방향 차집합 0**. 🔴 **바이트 동일성은 미판정**이다.
- 33.7(g)의 「`01_clips` · `02_preprocessed`와 바이트 동일 0(wav 한정)」과 **모순되지 않는다**(전처리·조각 자르기 전이라면 바이트가 다른 것이 자연스럽다 — 이 해석도 **논증**이다).
- 🆕 **[원인 규명 — 발견일 = 반영일 = 2026-09-21 PoC-(55), 근거유형 = 실측 이름 대조, 계수 단위 = 파일 수, 상세 = 33.14(c)]** 위 **0바이트 30개**(doorbell 10 / knock 20)는 FSD50K 로컬 덤프의 **0바이트 wav 2,414개 집합에 30 / 30 전건 포함**된다 — 30건 모두 `00_source_raw`에 **파일은 있고 크기가 0**이다. ⇒ **`01_extracted`의 0바이트는 조각내기 단계의 결함이 아니라 원천 0바이트가 그대로 흘러내려 온 것**이다. ⚠️ **이름 대조 기준**이며 바이트 귀속 실측이 아니다.

**(g) 🔴 사용자 판단 대기 (본 절은 어느 것도 확정하지 않는다)**

- 웹 수집분의 **클래스 정의**(실내 월패드 호출음 / 공동현관 · 경비실 호출음을 `doorbell`로 볼지 오경보 네거티브로 둘지) · **명명과 pitch 대상 범위** · **사용 순서**(외부 평가 전용 vs 즉시 학습 투입) · **split 대안 선택** · **33.7 누수 대응과의 순서** · **`SAMPLE_WEIGHT_RANGE` 미구현 처리**(위 카테고리 5 머리 정정).
- ⚠️ **장치 설치 위치(문 안 / 밖)와 마이크가 듣는 소리의 종류는 SSoT 미등재**다(`docs/decisions.md`에서 「설치 위치」 · 「월패드」 · 「도어락」 · 「차임」 **전부 0건** — 대조군 = 「인터폰」 매치는 전부 다른 맥락). 이것이 정해져야 수집 유형이 정해진다.
- 🆕 **[사용자 결정 반영 — 2026-09-21 PoC-(55), 근거유형 = 사용자 결정, 계수 단위 = 대기 항목 수] 위 대기 6항목의 분해**

  | 항목 | 판정 | 근거 |
  |---|---|---|
  | **사용 순서**(외부 평가 전용 vs 즉시 학습 투입) | ✅ **확정** | **D5 = 외부 평가 전용** |
  | **split 대안 선택** | ✅ **확정** | **D2 = 그룹 해시 고정 배정**(33.12(a)) |
  | **33.7 누수 대응과의 순서** | ✅ **확정** | 33.7(e) **①**(중복 제거 후 재split · 재학습) 확정 — **split 정비가 먼저**(33.12) |
  | **`SAMPLE_WEIGHT_RANGE` 미구현 처리** | 🟡 **부분** | **D6 = 서술을 실물에 맞춤**. **「구현할지」는 미확정**(카테고리 5 머리) |
  | **웹 수집분 클래스 정의** | 🔴 **미확정** | D5로 **학습 투입이 미뤄졌을 뿐** 정의 자체는 미결 |
  | **명명 · pitch 대상 범위** | 🔴 **미확정** | 위 **(b)** 부분 해소 참조 |

  - 🔴 **장치 설치 위치(문 안 / 밖)는 여전히 SSoT 미등재이며 사용자 판단 대기**다 — 2026-09-21 결정 대상에 **들어가지 않았다**(사용자 판단 대기로 명시 보류). 위 ⚠️ 줄 **무변경**.

**관련**: 5.1(직접녹음 4유닛 프로토콜 · 저장 위치 · `01_extracted` 존재) / 33.2(split · f1) / 33.3①(한국 환경음 정의) / **33.6(g)(본 조사의 실물 파일럿)** / 33.7(내용 중복 · 누수 — 순서 의존) / 33.8(`gate_axis_sweep` 외부 사용 주의) / 카테고리 20(계측 → 실측 → 판정)

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
  - 🆕 **[재판단 입력 — 2026-09-17 PoC-(51), 근거유형 = 논증, 입력 실측 = 6.5]** 2차 클라이언트 설계 조사로 **재판단 시점이 도래**했으나, 권고안(직렬 · `/detect` 응답 `enrich_status` 게이트 · 재시도 없음) 하에서는 **위험이 커지지 않는다**: ① 보드에 **재시도가 없어** 같은 `client_request_id`를 2회 발사하는 경로 자체가 없다 ② `/enrich` 요청이 `loop` 태스크 **한 곳**에서만 나간다 ③ `/detect` 5초 rate limit이 이벤트 간격 하한을 만든다. ⇒ **11주차 Gunicorn 다중 워커 전까지 현 미결 유지가 정합**이다. ⚠️ **미결을 닫지 않는다.** 상세 = **6.5**.

### 6.1 API 명세 1차 확정 (2026-05-28 PoC-(14), Phase 1 대시보드 셋업 연동)

> 상세 요청/응답 JSON 구조 = `dashboard/src/types/` (`api.ts` / `notification.ts` / `stats.ts`) + PoC-(14) 채팅방. 본 카테고리엔 **결정 + 근거만** (JSON 미박음).

- **엔드포인트 버저닝**: `/api/v1/*` — `detect`(ESP32→서버 1차) / `enrich`(ESP32→서버 2차 사진+음성) / `notifications`(대시보드 폴링) / `stats`(대시보드 폴링). 근거: 향후 API 변경 시 v1/v2 병행 + 대시보드 폴링 엔드포인트 확장
- **인증 분리**: Device Bearer Token (ESP32, `firmware/include/secrets.h`) ↔ Dashboard Bearer Token (React, `.env`) — 디바이스/대시보드 권한 도메인 분리
  - 🟡 **[등재] 토큰별 소관 엔드포인트 (PoC-(45) 문서 반영, 근거유형 = 실측 `server/app/auth.py`·`routes.py`)**: `/stats` 인증 = **`DASHBOARD_TOKEN`**. `DEVICE_TOKEN`은 `/detect`·`/enrich` 전용 — 혼동해 `/stats`에 `DEVICE_TOKEN`을 넣으면 **401**이 난다.
- **통신**: HTTPS 강제 (Let's Encrypt + ESP32 `setInsecure()`, 본 카테고리 TLS 항목 일치)
- **요청 추적 분리**: `client_request_id` (ESP32 자체 생성, 재시도 멱등 키) + `request_id` (서버 ULID 발급) — 디바이스/서버 추적 ID 분리 (코드: `notification.ts`)
- **HTTP Status 8종 + rate limit**: `device_id` 5초당 1회, 초과 시 `Retry-After` 헤더
- **Idempotency**: `idempotency_keys` 테이블 (24시간 TTL) — `client_request_id` 기반 재시도 중복 차단
- **stats period**: `today` 단일 (Phase 1, 코드 `stats.ts` `StatsPeriod`)
  - 🟡 **[등재] `today` 집계 구간 = 당일(00:00~23:59) (PoC-(45) 문서 반영, 근거유형 = 실측 `routes.py` `stats()`)**: KST 00:00:00~23:59:59.999(`period_start`/`period_end`)만 집계한다. 알림 목록에 과거 데이터가 있어도 **오늘 0건이면 통계는 0**이며 이는 결함이 아니다.
- **stats 알림 속도(`timing_metrics`) 실계측 도입 (2026-07-06 PoC-(22), PR #18 `d57f3ae`)**: `_build_stats`의 `timing_metrics` 하드코딩 0 placeholder → **실 타임스탬프 집계**로 전환. 1차 지연 = `primary_sent_at − detected_at`(ms), 2차 지연 = `secondary_sent_at − detected_at`(ms), 달성률 = 1차 ≤5초 / 2차 ≤15초 이내 비율(목표 = 카테고리 3 연동). null 안전(`sent_at is not None` 필터로 미발송·2차 미완료건 자동 제외) + ZeroDivision 가드. `stats.ts` `TimingMetrics` 6키(avg/max ms ×2 + under-rate ×2)와 1:1 정합(신규 필드 발명 X, 학습 16). **의의**: 원래 11주차 실 계측 몫을 선작업 → 실 하드웨어 데이터 유입 시 그대로 실값 산출(데모 픽션 아님, 재사용 코드). **수정 2곳 한정**(routes.py timing 블록 + `seed.py`), 타 집계·프론트·타입 무변경.
  - ~~**🟡 [신규 미결] `primary_sent_at`이 `detected_at`과 동일 변수로 세팅됨 (2026-09-02 감사 G14)**: `server/app/routes.py`(139/147행대) 확인 결과 `detected_at=now` / `primary_sent_at=now if pred["primary_sent"] else None` — 두 값이 **같은 `now`**를 공유한다. 그 결과 위 1차 지연(`primary_sent_at − detected_at`)이 **real 경로에서도 항상 0ms**로 집계된다. 실제 처리 지연(디코딩+추론+판정)이 존재함에도 timing_metrics가 이를 반영하지 못함 — 11주차 실계측 정합성에 영향.~~ **✅ 해소 (2026-09-03 PoC-(39), PR #40 `70aea1d`)**: `routes.py`에서 `detected_at`과 `primary_sent_at`을 분리 세팅하도록 배선 → 1차 지연 실측 **171ms**(변경 전 구조적 항상 0ms). 카카오 왕복 실측 p95 84.1ms(7.2)와 자릿수 정합(상세 = 카테고리 7.5(a)). ★ **[재오독 방지 앵커, 2026-09-09 PoC-(43)] G14는 본 문서 카테고리 6.1에 등재돼 있다** — 「트래킹 부재」가 아니다. 2026-09-09 위임이 G14를 미등재로 지목했으나 실측 반증됐다. **decisions.md 미등재인 감사 ID는 G18/G21/G24(Notion DB3 전용)뿐**이며 상세 3층 구분은 **27.8(f)**.
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
- ~~**🔴 [신규 미결] `/detect` 계약에 ToF 메타 필드 부재 (2026-09-02 감사 G10)**: 요청 스키마(`server/app/routes.py`)는 `client_request_id`/`device_id`/오디오 파일만 수신 — ToF 필드는 **아예 없다**. 그 결과 클래스별 ToF 분기(`server/app/utils.py:92,101`)가 입력 없이 **하드코딩 문자열**을 반환한다(92행 = `"zone_count=9 >= 8 + motion=true"`, low_confidence 분기 / 101행 = `"zone_count=11 >= 8 + motion=true"`, 통상 분기 — 값 자체는 다르지만 둘 다 입력 무관 상수). ★ **2026-09-02 7.4 터널 실측 응답에서도 센서 미연결 상태로 동일 문자열이 재현**됨(실물 증거, 근거유형=실측). 필요 필드 4종 = `tof_presence` / `tof_near_count` / `tof_center_mm` / `tof_motion_ndet`(9.3·9.4 계측/판정 계층 출력과 정합). ⚠️ **11주차 통합 시 wire 계약 확정 필요** — 오디오 wire 계약(본 절 CLOSE 완료분)과 별개로 미확정.~~ **✅ 수신측 CLOSE (실측 2026-09-04 / 문서 반영 2026-09-05, PR #43 `8827946`)**: 4종 필드 wire 수신 + 클래스별 ToF 정책 실입력 구동을 실코드화하고 ④런타임에서 위 하드코딩 문자열 소멸을 확인했다(상세 = 신설 절 **6.4**). ~~⚠️ **G10 수신측 CLOSE ≠ G10 CLOSE** — 송신측(마이크 M5-d + 통합 펌웨어가 실제로 ToF 메타를 실어 보내는 코드)은 여전히 **0줄**이며, 11주차 통합 체크포인트는 그대로 유효하다.~~ **✅ G10 CLOSE (송신측, 실측 2026-09-11 / 문서 반영 2026-09-11 PoC-(45) Set 1, PR #52 `b3414a4` + PR #53 `5049612`)**: PR #52가 오디오 2초 스냅샷 송신을, PR #53이 ToF 4필드 송신을 각각 실코드화해 송신측 0줄이 해소됐다(④런타임 = 6.3(m)·6.4(g)). ⚠️ **단서** — 실동작 확인 범위는 진단용 `env:mic_uplink` 기준이며, **제품 통합(`env:prod`)으로의 편입은 별개 미결**이다(11주차 소관).
- **🟡 [신규 미결] 2초 오디오 캡처 윈도우가 1차 5초 예산에 미반영 (2026-09-02 감사 G29)**: 본 절 "★ 1차 5초 체인 전 구간 실측 완성"(합산 p95 ≈1134ms = 23%)은 **이미 캡처된** 64KB(2초) 오디오를 업로드하는 시간만 잰다. 그 2초를 **언제 벌어들이는지**(사후 녹음 vs 사전 링버퍼)가 예산에 미반영이다(근거유형 = **논증**). 사후 녹음(트리거 후 2초 녹음 → 그제서야 업로드 시작) 설계라면 실질 p95 ≈ **3,954ms(예산의 79%)**, 사전 링버퍼(상시 녹음 중이라 트리거 시점에 이미 최근 2초가 확보돼 있음) 설계라면 ≈ **1,954ms(39%)** — **설계 선택 하나가 예산의 40%p를 좌우**한다. → ~~**M5(마이크 최종 결선) 착수 전 결정 필요.**~~ **✅ 2026-09-04 확정 — B안(하이브리드) 채택 (2026-09-03 사용자 결정, 근거유형 = 논증)**: 트리거 시점 기준 pre-roll 일부 + post 일부로 2초 페이로드를 구성한다. 기각 사유 = 전량 pre-roll(A안, ≈1,954ms/39%)이면 트리거 이전 구간이 대부분 무음이라 소리 본체가 빠져 학습 클립 분포와 어긋남(G28 악화) / 전량 사후(C안, ≈3,954ms/79%)이면 어택이 빠지는데 doorbell이 이미 최약 클래스(precision 0.730/recall 0.742, G27)라 입력에서 특징을 깎을 수 없음. B안 예산 ≈3,454ms(69%). 구현 비용 = I2S가 M2~M4 구조상 이미 상시 읽고 있어 링버퍼는 "읽은 것을 안 버리는" 것뿐(PR #41로 이미 확보, 상세 = 6.3(h)). ⚠️ **pre/post 비율은 미확정** — 32슬롯 = 8(0.512s)+24(1.536s)가 버퍼 정수배로 떨어진다는 사실만 기록하며, 비율 확정 판단은 M5-c 소관으로 남긴다.
  - **🔗 [파급] `KAKAO_HTTP_TIMEOUT_SECONDS` 재계산 필요 (역방향 stale 해소, 발견 2026-09-04, 근거유형 = 논증)**: 상수값 1.5초는 **"사전 링버퍼"(A안) 전제로 역산**된 값이었다(5000 − 업로드 1900 − 105 ≈ 3000 ÷ 2회). G29가 B안으로 확정됐으므로 재계산 = 5000 − post 1500 − 업로드 1900 − 105 = 1,495 ÷ 2회 ≈ **750ms**. ⚠️ **본 항목은 문서 등재만 한다** — 상수 코드 값 변경은 별도 PR 소관이며 본 Set에서 미수행.
    - 🟡 **[등재 — 2026-09-17 PoC-(51), 근거유형 = 실측 코드 대조] 같은 상수의 주석이 stale이다**: `server/app/constants.py`의 `KAKAO_HTTP_TIMEOUT_SECONDS` 주석 상단이 **「G29는 사용자 판단 대기 중인 미결」**이라 적고 있으나, **G29는 2026-09-04에 B안(하이브리드)으로 확정**됐다(위 본문). ⇒ 코드 주석이 **이미 닫힌 미결을 열린 것으로 서술**한다. ~~⚠️ **본 Set은 코드 무접촉**이므로 **정정 대상이라는 사실만 기록**하며, 주석 수정은 별도 PR 소관이다.~~ → ✅ **해소 (PR #65 `601e7a2` 2026-09-19 머지, 내부 커밋 `fe2b9f9`, 근거유형 = 실측 `git show`)**: 주석 앞머리를 **「2026-09-04에 B안(하이브리드)으로 확정(카테고리 6.2)」**으로 정정했다. ⚠️ **같은 블록 말미의 ★ 항이 이미 「B안 확정으로 750ms 재계산 필요」를 담고 있어 주석 블록 안에서 자기모순**이었다(실측). 🔴 **상수값 1.5 무변경 · 750ms 미기재** — 7.7(l)의 배율 ≈1.60 실측이 산술 전제를 흔들어 **PR-C 소관**이다. PR 요약 = **27.8(m)** 말미. 성격 = 27.8 계열의 **코드 주석 판**(6.3(k-2) `mic_common.h` 선례와 동형).
- 🔴 **[단서 — 2026-09-18 PoC-(53), 근거유형 = 실측 + 논증] 실기기 1차 rtt가 위 산술과 어긋난다. 🔴 원인은 지정하지 않는다.**
  - **실측(보드 시리얼, 2026-09-18 ④런타임 4건, 상세 = 6.7(d))**: `gate=skip` 건 **683ms** ↔ `gate=pending` 건 **4,301 / 4,902 / 5,814ms**. 위 「합산 p95 ≈1134ms = 23%」(HTTP 기준)·「A안 ≈1,954ms(39%)」(HTTPS 기준)와 **자릿수가 어긋난다**. ⚠️ 보드 rtt는 **보드가 보는 `/detect` 왕복 전체**라 위 성분 합산과 **계측 지점이 다르다**.
  - 🔴 **교란 3축이 분리되지 않는다** — ① **2차 동반 구간**(같은 세션에서 `/enrich`가 함께 돌았다) ② **세션 진행에 따른 핫스팟 열화**(같은 세션 후반에 카카오 **`URLError`** = 네트워크 도달 실패가 났다) ③ **[논증, 입력 실측 = `server/app/routes.py` 코드 구조] 두 군은 서버 작업량 자체가 다르다** — `if primary_sent:` 안에서만 `kakao.send_primary_text()`를 호출하므로 `tof_rejected`인 skip 건은 **카카오 왕복을 아예 태우지 않는다**. ⇒ 683ms ↔ 4~5초 차이에 **구조적 성분이 섞여 있다**.
  - **판정 방법** = skip 건과 pending 건을 **교대로 배치**해 재측정한다(2026-09-15 m2↔m5 교대 방식과 동형). ⚠️ **교대 배치만으로는 ③이 갈리지 않는다** — ③을 가르려면 **같은 게이트 결과 안에서** 2차 동반 유무를 바꾸거나 6.5(e) **M-1 성분 분해**가 필요하다.
  - ⚠️ **위 「1134ms」·「1,954ms」 서술은 취소선 대상이 아니다** — 각각 **2차 클라이언트가 없던 조건**에서의 성분 합산 산술이고, 본 단서는 그 **적용 경계**를 적는 것이다.
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
- **(k-2) mic_common.h 내부 "헤드룸 약 1.8배" 서술과의 정합 확인**: `firmware/include/mic_common.h`(88~90행) 주석은 "박수 max 296542208 >> 14 = 18099 = 풀스케일 55% → 클리핑 없음, 헤드룸 약 1.8배"라 적고 있으나, **본 decisions.md에는 이 "헤드룸 확정" 프레이밍이 애초에 등재된 적이 없다**(grep 확인 — (d)는 이미 "헤드룸 상한 검증 아님"으로 유보돼 있었다) → 취소선 대상 문구 부재이므로 **순수 신설로 처리**(학습 17 catch, 2026-09-03 [B]/[C] 선례 준용). 오늘 박수 raw max는 296,542,208의 **5.35배**이고 clip=311(w=64)/163(w=69)/124(w=72) 등이 실측돼, mic_common.h 주석의 "헤드룸 1.8배·클리핑 없음" 서술은 이제 근거를 잃었다. ~~⚠️ **mic_common.h 주석 정정은 본 Set 범위 밖(별도 코드 PR 소관, firmware/ 0줄 수정 원칙)** — 본 문서는 그 서술이 실측과 어긋난다는 사실만 기록한다.~~ → ✅ **해소 (PR #65 `601e7a2` 2026-09-19 머지, 내부 커밋 `a918173` + `8200669`, 근거유형 = 실측 grep + `git show`)**: `mic_common.h` 주석을 **반증 사실 + 본 (k-2) 포인터**로 정정했다(인용 수치 5.35배 / clip 311 · 163 · 124는 본 문면에서 grep해 옮김 — 창작 0). ★ **드리프트 재발 실증 — 「한쪽만 고쳐 드리프트를 남겼다」**: 위임이 「단일 파일(`mic_common.h`)」로 못박아 `a918173`만 냈으나, **`firmware/src/mic_test.cpp`에 같은 반증 서술**(*"clip > 0 이면 헤드룸(실측 1.8배) 소진 신호"*)이 **남아 있었다** — 27.8(m)⑤ 「같은 사실을 두 문서가 다르게 적는 드리프트」의 재발이다. **전수 grep으로 잔여 1건 확정**(계수 단위 = 줄 수: `firmware/` 전체 「1.8배」 = `mic_common.h` 정정분 + `mic_test.cpp` **2건**, 「헤드룸」은 + `tof_common.h`의 ToF 3.4배(무관) / 대조군 = `MIC_RAW_TO_INT16_SHIFT` grep **6건** — 도구 생존). MCP가 catch해 **같은 PR에 `8200669`로 얹었다**(27.8(o)③). **검증** = 전처리 md5 전후 동일(`1ccfe3f8…`) + **대조군 갈림**(`: -1;` → `: -2;` → `03e08322…`) + 복원 후 재일치 / `mic_dummy` 빌드 SUCCESS / 회귀 106. 🔴 **바이너리 md5 미사용**(툴체인 비결정 — 카테고리 20).
- ⚠️ **shift=14가 틀렸다는 뜻이 아니다.** shift 상향(`>>15`/`>>16`)은 클리핑을 줄이지만 저음압 해상도를 버린다 — 노크는 clip=0~2로 거의 무영향이었고 박수만 크게 걸렸다. **초인종 실측 음압이 없는 상태에서 shift를 바꾸면 그 자체가 "측정 전 확정"**이다(카테고리 29 원칙 적용) → shift 판정은 도어벨 4유닛 수령 후 동일 위치 재측정까지 보류.
- ★ **실측 반전 5회차**: ① ToF near 8→20 폐기(내부 추정) ② 마이크 `>>16`→`>>14`(내부 추정) ③ ToF aggmax≥50→ndet≥1(내부 추정) ④ 카카오 200자 상한(외부 공식 문서) ⑤ 본 건. ①②③은 **우리 내부 추정**이 실측에 뒤집힌 사례, ④는 **외부 공식 문서**가 우리 가정을 뒤집은 사례, **⑤는 우리가 실측으로 세운 근거표 자체가 후속 실측에 뒤집힌 첫 사례**라는 점에서 성격이 다르다.

**(l) 🟡 [등재] M5-d 착수 전 확인 사항 7건 (PoC-(45) 문서 반영, 근거유형 = 실측 코드 대조)**
- ① `MIC_TASK_STACK_SIZE=4096`(`firmware/include/mic_common.h`) — 업로드 코드가 같은 태스크에 붙는 구조가 되면 스택 부족 위험. M5-d 착수 Step 0 확인 항목. → **✅ 처리 (2026-09-11 PoC-(45) Set 1, PR #52)**: POST를 마이크 태스크에 붙이지 않고 loop 태스크에서 수행(프로즌 하네스가 동일 스택 크기에서 완주한 선례 재사용) + `stk_free`를 매 스냅샷 출력해 ④런타임에서 확인(6.3(m)).
- ② POST 실코드는 현재 프로즌 `upload_spike_common.cpp`에만 존재 — M5-d는 이를 복제해 신설 `uplink_common.cpp`로 옮긴다(원본 무수정 원칙, §7 동형). → **✅ 처리**: `uplink_common.cpp/.h` 신설, 원본 1바이트 무수정.
- ③ 하네스 wire 필드(`client_request_id`/`device_id`/오디오 파트명 `audio`)는 서버 `constants.py`(`AUDIO_FILE_FIELD` 등)와 **1:1 일치**(확인됨). → **✅ 처리(확인 유지)**: 실grep 대조 후 동일 조립.
- ④ `device_id` rate limit = **5초당 1회**(`DEVICE_RATE_LIMIT_SECONDS`, `rate_limit.py`) — 부스에서 연타하면 429. → **✅ 처리**: `UPLINK_DEVICE_ID`를 하네스와 분리해 서로의 429를 유발하지 않게 하고, 연타 429는 막지 않고 ④런타임 대조 실험 (b)로 관측(재시도 없음 정책 증명 겸용).
- ⑤ `client_request_id`는 ESP32측에서 `millis()` 기반으로 생성된다(`upload_spike_main.cpp`) — 충돌 가능성 있음. → **✅ 처리**: 부팅마다 `esp_random()` 32비트 nonce + 카운터(`m5d-<nonce8>-<seq>`)로 대체. 실제 위험은 "충돌"이 아니라 재부팅 후 같은 id 재생산 → 서버 24h 멱등 캐시 200 replay였고, ④런타임 대조 실험 (c)가 이를 확인.
- ⑥ `rate_limit.py`는 in-memory 구현이며 docstring 자체가 "11주차 다중 워커(Gunicorn) 배포 시 Redis 등 공유 저장소로 교체 필요"라고 명시한다 — 다중 워커 간 **비공유**. → **해당 없음**: 본 세션은 `flask run` 단일 프로세스 dev 서버(Runbook 3절). 다중 워커(Gunicorn) 배포는 11주차 소관.
- ⑦ `enrich_status`에 `"processing"` 상태는 아직 생성돼 있지 않다(서버 코드 전역 0건). → **스코프 제외**: `/enrich`·2차 알림 = I2 소관. 본 PR은 `/detect`만 호출, `enrich_status`에 무접촉(서버 무변경).

**(m) M5-d PR #52 — 오디오 배관 완성 + ④런타임 (2026-09-11 PoC-(45) Set 1, PR #52 `b3414a4`)**

설계 결정 4건:
- **D1** 트리거 = 시리얼 `s` 키 **수동 입력**(자동 판정 0줄, M5-c 소관 보류).
- **D2** 링버퍼 최근 2초를 **그대로** 전송(집계·가공 없음).
- **D3** ToF 필드 **미전송**(송신측 ToF는 PR #53 소관, 상세 6.4(g)).
- **D4** 신규 `env:mic_uplink` + 프로즌 `upload_spike_common.cpp`를 복제한 신설 `uplink_common.cpp/.h`(원본 무수정, §7 동형).

**④런타임 결과 (2026-09-11 10:30~10:45, 학교·아이폰 핫스팟, mock ML)**:
- (a) 조용함 → 손뼉 → 조용함: 보드 rms **99 → 4756 → 106**(손뼉 peak 32768 = clip).
- (b) 5초 안 연속 2회: 서버 10:41:19 **201** → 10:41:23 **429**, 이후 POST 없음(재시도 없음 확인).
- (c) RESET 후 전송: nonce `a8c501ff → c303b6db`, 2회차 **201**(200 replay 아님).
- 덤: fire_alarm 0.75(mock) → `fire_alarm_bypass` → **카톡 1차 알림 도착** = **실 보드 → 서버 → 카톡 1차 관통 첫 확인**. ⚠️ mock 판정이라 **분류 정확도 증거는 아니다** — 경로 관통 확인일 뿐.
- stk_free=2440 전 전송 불변 / psram_free 안정 / rtt 287~922ms.

**Runbook 전제와 실제가 다른 점 3건 (근거유형 = 실측)**:
1. 서버측 `detect audio decoded ... rms=` 줄이 **기본 로그 레벨에서 미출력** — Runbook 전제였던 서버측 rms 교차검증 불가. 확인 경로는 `/notifications` DB 조회로 대체.
2. 모니터 결과 줄(`http=`)이 **다음 입력 시점까지 지연 출력**(CDC 출력 지연 추정 — `lsof` ESTABLISHED 0건으로 보드 정지 아님은 확인). → **시각 판정은 서버 access log 기준**으로 못박음.
3. 시리얼 절단 **80B 상한**으로 `tof=fire_alarm_bypas` / `ring filled — 's' 키…` 등 **표시만 절단**(기능 무관, 6.3(j) 기존 절단 실측과 동형).

로그 원본 = repo 밖 `~/ddingdong-측정결과/2026-09-11/M5d_mic_uplink_runtime.log`.

**(n) 🔴 신규 미결 — ToF I2C 통신 활동 시 마이크 SD 비트 오류 (발견 2026-09-11, PoC-(45) Set 1, PR #53 댓글 + PR #54)**

실측 A/B (PR #53 댓글, 같은 자리·결선·수 분 차이, 펌웨어만 교체):
- ToF 측정 ON(조용한 전송 6회): peak **32767~32768 ×6**, rms 455~636.
- main `b3414a4`(ToF 전원만, 측정 OFF, 3회): peak **412~464**, rms 95~96(오전 PR #52 값과 일치).

실측 5모드 (PR #54 댓글, `env:mic_noiseprobe`, clip 수 = 스냅샷 3회):

| 모드 | 측정 | 통신 | 코어 | clip |
|---|---|---|---|---|
| m0 대조군 | OFF | OFF | – | 0·0·0 |
| m1(H2 격리) | ON | OFF(`sc 231->195` 전진 실측 확인) | – | 0·0·0 |
| m2(현행 재현) | ON | ON 400k | 0 | 3·5·6 / 3·9·9 |
| m3(엣지속도 H1) | ON | ON 100k | 0 | 4·3·6(`C0000000` 신규 출현, 읽기 도중) |
| m4(코어경합 H3) | ON | ON 400k | 1 | 4·9·6(m2와 동일 범위·비트 패턴) |

판정(Runbook 판정표 기준):
- **H2(센서 동작 전원) 기각 — 실측**(m1 clean).
- **H3(Core 0 태스크 경합) 기각 — 실측**(m4 ≈ m2).
- **H1 계열(I2C 버스 활동 → SD 비트 오류) = 가능성 높음 — 논증**: 클립 시점이 버스 활동 구간을 따라 이동(400k 읽기 사이 poll 구간 → 100k 읽기 도중), 클럭 변경 시 오류 비트 패턴 변화(`7F…` → `C0000000`), 샘플 단위 비트 오류(DMA 누락 아님). ⚠️ m3 클립 수는 m2 편차 내라 "엣지 수 비례"는 **미지지**.
- **경로 미분리**: 인접 배선 누화(SD B10 ↔ SCL J10, 같은 10번 열) vs 공통 접지 바운스 — 결선 변경 없이는 구분 불가(스코프 밖).

영향: ML 입력 오염 + M5-c 트리거 헛발동 위험. ~~C-0(6.3(c)~(k))는 ToF 미구동 펌웨어로 측정했으므로 **그 실측치 자체는 유효**하나, M5-c 임계값은 **문제 해결 후 통합 펌웨어로 재확인 필요**.~~ **[라벨 오기 정정 — 발견 2026-09-12 PoC-(46) / 문서 반영 2026-09-12]** 실질 주장은 그대로 유효하다: **6.3(c)~(k)는 ToF 미구동 펌웨어로 측정했으므로 그 실측치 자체는 유효**하고, **M5-c 임계값은 문제 해결 후 통합 펌웨어로 재확인 필요**하다. 틀린 것은 **그 값을 낸 주체의 라벨**이다 — 6.3(c)~(k)는 **이미 완료된 랩실 실측**이고 **C-0가 아니다**. 현 문구는 **"C-0 완료"로 오독될 위험**이 있어 취소선 처리했다.
- ⚠️ **경계 표기 (근거유형 = 실측 grep)**: `grep -nE "\bC-[0-9]" docs/` = **2건**(본 줄 + 27.8(h)②의 인계 문구 인용)이고, **`C-0`의 정의 자체가 `docs/` 어디에도 등재된 적이 없다**. 라벨이 **인계 계층에만** 살아 있어 오기가 SSoT 안에서 잡히지 않았다 — 27.8(h)①·(e)① 「출처 계층 착각」과 **같은 축의 역방향**(등재된 적 없는 라벨을 등재된 것처럼 본문에 쓴 경우)이다.
- **C-0가 무엇인가**: 위임·인계 계층 서술 = **미착수인 현관 인터폰 실측**(근거유형 = **인계 서술, repo 미검증**). ⇒ **C-0 정의의 SSoT 등재는 본 Set 범위 밖**(인계 계층 소관)이며, 여기서는 **본 줄의 라벨이 틀렸다는 사실까지만** 확정한다.

**해결책 = 사용자 판단 대기**(①펌웨어 필터 ②배선 조치 ③병행 — 방식·수치 확정 금지, §9 동형).

- 🟡 **[가설 검증 수단 — 해결책 아님] PR #55 ~~미머지~~ → 머지 `94aa9d9` — SD 내부 풀다운 판별 모드 m5·m6 (2026-09-12 PoC-(46) 등재, 근거유형 = 논증, ~~④런타임 미수행~~ → ④런타임 완료 2026-09-15 PoC-(49) = 아래 (p))**
  - 브랜치 `feat/firmware-noiseprobe-pulldown` HEAD **`dddde9b`**, ~~상태 **OPEN·미머지**(실측 = `git ls-remote origin` — 학습 20, `git branch -r` 미사용). **④런타임 미수행**(보드 실측 대기).~~ → **✅ 머지 `94aa9d9` (2026-09-15 PoC-(49)) · ④런타임 완료** — 원격·로컬 브랜치 **삭제 완료**(실측 = `git ls-remote origin`이 `refs/heads/main` 단일 — 학습 20, `git branch -r` 미사용). **결과·판정·한계 = 아래 (p)**.
  - **가설 (근거유형 = 논증, 미실측)**: INMP441은 LSB 출력 직후 SD를 **tri-state**하므로 데이터시트가 SD에 **100kΩ 풀다운을 권장**한다. 본 (n) 실측에서 오류 비트가 워드 **선두**(`7F…` MSB / 100k의 `C0000000` 상위 2비트)에 몰린 **위치**가 "Hi-Z → 재구동 직후 샘플되는 비트" 위치와 **일치**한다.
  - **모드** = **m5**(m2 + SD 내부 풀다운 ON, 그 외 전 필드 동일 = 실험군) / **m6**(m0 + 풀다운 ON = **풀다운 자체의 부작용 대조군**). 기존 m0~m4 다음 **빈 번호**임을 실물 대조 후 부여.
  - **호스트 테스트 신규 46 checks**(모드 불변식). 기존 `noise_stats_test` **61 checks** · `tof_judge_test` **196 checks**는 **유지**(수치 무변경).
  - 🔴 **★ 이것은 가설을 가르는 수단이지 해결책이 아니다.** m5/m6가 가르는 것은 **H1의 하위 가설**(내부 풀다운으로 억제되는가)뿐이며, 위 **해결책 ①②③은 여전히 사용자 판단 대기**다 — 본 항목이 그 판단을 대신하지 않는다. 성격 = (o)와 같은 **진단 하네스 계열**(제품 코드·판정 상수 0줄). 🆕 **[2026-09-15 PoC-(49)] ④런타임 결과가 나온 뒤에도 본 문장은 무변경**이다 — (p)가 가른 것은 **H1의 하위 가설뿐**이고 **해결책 ①②③은 그대로 사용자 판단 대기**다.

**(o) 진단 하네스 방법론 자산 등재 — `env:mic_noiseprobe` (2026-09-11 PoC-(45) Set 1, PR #54, 근거유형 = 실측)**

(n)의 기전 진단 전용 신설 env. 제품 코드(`mic_common.*`/`tof_common.*`/`mic_uplink_main.cpp`/`uplink_common.*`/프로즌 env) **0줄 수정**, 판정 상수·해결책 0줄 — 9.1(e) `tof_pinscan`·`tof_lineprobe` 선례와 같은 「방법론 자산」 성격(8.4(f) 소제목 어휘 재사용).

- 호스트 테스트: `noise_stats_test.cpp` **61 checks OK**, negative control 6종(4 검출 / 1 도달 불가 — 관측 해상도 한계 / 1 판별력 부족 → 보강 후 검출).
- 보드가 쓰는 `noise_stats.h`를 **테스트가 그대로 include**(복사 아님).
- 호스트 스텁 패턴(`firmware/tools/host_stubs/` — Serial·Wire·SparkFun 표면 4파일) 신설 — `tof_judge_test`(9.4(f) 참조)와 공유.
- 🟡 **[등재 — 2026-09-15 PoC-(48) 실측] 호스트 테스트는 ~~3종~~ → 4종이다**: `noise_stats_test` · `tof_judge_test` · **`firmware/tools/jsonpeek_test.cpp`** · 🆕 **`noise_modes_test`**. 앞의 둘은 SSoT에 등재돼 있으나 **`jsonpeek_test`는 decisions.md 0건**이었다(2026-09-15 실측, 대조군 = 같은 grep에서 `noise_stats_test` · `tof_judge_test` 생존). ~~⇒ **존재 사실까지만** 등재하며 checks 수·커버리지·최종 실행 결과는 **미측정**이다. **확정하지 말 것.**~~
  - 🆕 **[현재값 갱신 + 부분 해소 — 2026-09-15 PoC-(49), 근거유형 = 실측]** 종수가 **4종**인 이유는 **`noise_modes_test`가 PR #55(`94aa9d9`)로 합류**했기 때문이다((n) 참조). ~~**4종 전건 실행 OK**이며 checks 수(계수 단위 = **checks 수**) = `noise_modes_test` **46** / `noise_stats_test` **61** / `tof_judge_test` **196**이다.~~ → **[현재값 갱신 2026-09-18 PoC-(52), 근거유형 = 실측 + 문서 인용, 계수 단위 = checks 수]** **5종**이다 — **`firmware/tools/camera_probe_test.cpp`가 PR #63(`41cd6e2`)으로 합류**했다(상세 = **6.6**). ~~checks 수 = `camera_probe_test` **97** / `noise_modes_test` **46** / `noise_stats_test` **61** / `tof_judge_test` **196**이며 **5종 전건 실행 OK**다.~~ → **[현재값 갱신 2026-09-18 PoC-(53), 근거유형 = 실측 + 문서 인용, 계수 단위 = checks 수]** **6종**이다 — **`firmware/tools/enrich_wire_test.cpp`가 PR #64(`d093d70`)로 합류**했다(상세 = **6.7**). checks 수 = `enrich_wire_test` **90** / `camera_probe_test` **97** / `noise_modes_test` **46** / `noise_stats_test` **61** / `tof_judge_test` **196**. ⚠️ **`jsonpeek_test`는 checks 카운터를 출력하지 않는다**(정적 `assert` **13**) — 위 목록이 5개 이름만 드는 이유이며 **누락이 아니다**. ⚠️ 위 4종·5종 서술은 **각각 2026-09-15 · 2026-09-18 PoC-(52) 시점 이력**이라 값 자체가 틀린 것이 아니다.
  - 🟡 **[등재 — 2026-09-18 PoC-(53) 실측] `jsonpeek_test`만 검증 방식이 다르다 — 헤더 include가 아니라 「본문 복사」다**: 다른 5종은 보드가 쓰는 헤더를 **그대로 `#include`**한다(`enrich_wire.h` · `probe_modes.h`+`probe_stats.h` · `noise_modes.h` · `noise_stats.h` · `tof_common.h` — 실측 대조). 반면 `jsonpeek_test.cpp`는 **project 헤더를 하나도 include하지 않고**(`cstdio`/`cstring`/`cassert`뿐) `mic_uplink_main.cpp`의 **static 함수 본문을 복사해** 검사한다(파일 머리 주석이 그렇게 명시한다). ⇒ 🔴 **원본을 변형하는 negative control이 불가능하다** — 변형해도 테스트는 **복사본**을 보므로 검출되지 않는다(카테고리 20 「negative control 미검출의 판정」이 말하는 **「도달 불가」**의 한 형태). **해소책은 등재하지 않는다**(코드 변경 소관). 🆕 **[보강 — 발견 · 문서 반영 2026-09-19 PoC-(53), 근거유형 = 실측 + 논증] 컴파일 명령도 없다**: 호스트 테스트 6종 중 **5종은 파일 머리 주석에 컴파일 명령이 verbatim 있다**(`camera_probe_test` → `/tmp/cpt` 등 — 대조군). **`jsonpeek_test.cpp`만 없고**, `decisions.md` 전문 grep에서도 jsonpeek 언급 줄에 `c++ …` **0건**이다. 17.2 베이스라인에서 쓴 `c++ -std=c++17 -Wall -o /tmp/jpt firmware/tools/jsonpeek_test.cpp`는 **유도값(논증)**이지 실물 추출이 아니다 — 근거 = project 헤더를 하나도 include하지 않아(`cstdio` / `cstring` / `cassert`뿐) 옵션이 갈릴 자리가 없다. ⇒ 「본문 복사 → 원본 변형 NC 도달 불가」 축에 **「컴파일 명령 부재」가 하나 더 붙는다**. 해소책은 여기서도 등재하지 않는다(코드 변경 소관).
  - 🟡 **[등재 — 2026-09-18 PoC-(53) 실측] `uplink_common.h`는 호스트에서 컴파일되지 않는다 — 이것이 `enrich_wire.h`를 별도 순수 헤더로 분리한 근거다**: `c++ -fsyntax-only -I firmware/include` 실측 결과 **차단은 2중**이다 — ① **1차 = `uplink_common.h` 자신의 `#include <Arduino.h>`**(`fatal error: 'Arduino.h' file not found`) ② **2차 = `mic_common.h`의 `#include "driver/i2s.h"`**(가짜 `Arduino.h`를 공급해 ①을 넘긴 뒤에야 드러난다). 대조군 = 같은 명령에서 `enrich_wire.h` 단독 **통과**(순수 헤더). 🔴 **PR #64 본문과 본 세션 위임은 차단 사유를 「`mic_common.h` → `driver/i2s.h`」 하나로만 적었다** — 결론(호스트 컴파일 불가 ⇒ 순수 헤더 분리 필요)은 옳지만 **먼저 터지는 것은 `Arduino.h`**다(27.8(n)①). ⇒ 불변식은 유지되고 **메커니즘 서술만 정정**된다.
  - 🔴 **`jsonpeek_test`만 checks 수를 셀 수 없다 — 카운터 출력 자체가 없다.** 대신 **정적 `assert` 13개**로 병기하되 **계수 단위가 다르다**(assert 문 수 ≠ checks 수) — **두 수를 더하거나 비교하지 말 것.** ⚠️ **커버리지는 여전히 미측정**이다. **확정하지 말 것.**

**(p) ✅ PR #55 ④런타임 실측 — SD 내부 풀다운으로 클립이 소거되지 않는다 ((n)의 H1 하위 가설, 2026-09-15 PoC-(49) 신설, 발견일 = 반영일 = 2026-09-15, 근거유형 = 실측, 계수 단위 = 스냅샷 수 / 클립 수)**

> 랩실 ④런타임. 로그 원본 = repo 밖 `~/ddingdong-측정결과/2026-09-15/mic_noiseprobe_pr55_sdpd_runtime.log`(`.gitignore` 차단분 — SSoT엔 요약만). 머지 = **`94aa9d9`**(원격·로컬 브랜치 삭제 완료). 결과 코멘트 = `https://github.com/park-taegeun/ddingdong/pull/55#issuecomment-5676508085`.

- **측정 전제 (근거유형 = 실측)**: 펌웨어 **`dddde9b`** · **결선 무변경**(ToF 6가닥 + 마이크 6가닥, SCL J10 ↔ SD B10 같은 10번 열). 순서 **2 → 5 → 2 → 5 → 0 → 6**, 각 블록에서 `s` **3회** = **18 / 18 유효**(전 블록 `ok=1` · `sd_pd req == reg` · `gaps=0` · 스냅샷 **8줄 무손상**). 시야 = 측정 전 near **7~8/64**로 presence 깜빡임 → 치울 수 있는 물건 제거 후 **0~4/64**.

  | 블록 | 모드 | clip(스냅샷 3회) | `tz` |
  |---|---|---|---|
  | 1 | m2(현행 재현) | 1 · 4 · 5 | 6 · 6 · 5 |
  | 2 | m5(m2 + SD 내부 풀다운) | 3 · 5 · 5 | 7 · 7 · 7 |
  | 3 | m2(교대 대조군) | 2 · 1 · 5 | 5 · 5 · 5 |
  | 4 | m5(교대) | 0 · 1 · 5 | 7 · 7 · 6 |
  | 5 | m0(측정 OFF) | 0 · 0 · 0 | 6 · 6 · 6 |
  | 6 | m6(m0 + 풀다운) | 0 · 0 · 0 | 8 · 8 · 8 |

  - m0 `rms` **91~99** / m6 `rms` **88~97**. 클립은 **전건 + 방향**(`+32767`)이고 raw 예시는 **전건 `7F…` 시작**이다.
  - `low6nz`: **m5 6회 전건 0** / **m2 6회 중 4회 >0**.

- **[실측] 판정 전제 성립** — 교대 m2 대조군이 `clip>=1`을 **6 / 6 재현**했다. 이것이 없으면 아래 판정 자체를 적용할 수 없다.
- **[실측] m5 clip 범위 `0~5` = 교대 m2 범위 `1~5`** ⇒ **내부 풀다운으로 클립이 소거되지 않는다.**
- **[실측] m6 vs m0** — clip · `rms`는 **동자릿수**이고 **`tz`만 6 → 8**로 바뀐다. 풀다운 자체의 부작용 대조군이 낸 **유일한 차이**다.
- **[논증] 기전 분리 가설 — 미실증**: 내부 풀다운은 워드 **하위 비트(6 · 7, tri-state 구간 추정)** 만 0으로 고정하는데, 이는 **MSB 클립과 별개 기전**일 수 있다. 하위 비트는 `>>14` 변환에서 버려지므로 **int16 값에는 영향이 없을 가능성**이 있다. **입력 실측 = 위 표의 `low6nz` · `tz` 열.** **확정하지 말 것.**
- ⚠️ **판정표 자체는 Runbook 계층 서술이다 (근거유형 = 문서 인용)** — 「같은 범위」 행이 해결책 ① 검토를 가리킨다는 것은 `firmware/docs/MIC_NOISEPROBE_RUNBOOK.md` **6-1**의 내용이며 **(n) · 본 (p) 본문이 세운 기준이 아니다**. 🔴 **(n)의 해결책 ①②③은 여전히 사용자 판단 대기**이고 **본 실측이 그 판단을 대신하지 않는다.**
- **한계 (전건 명기)**
  - **내부 풀다운은 약 45kΩ급**(Runbook 서술, **미실측**)이고 데이터시트 권장 **외부 100kΩ과 다르다** ⇒ **「외부 저항도 무효」로 확대 해석 금지.**
  - 스냅샷 **#6의 `rms_x` 809**(타 스냅샷 **96~155**) = **실제 소리 오염 추정**이며 **음원 미확인**이다.
  - Runbook ①~⑦에 해당하는 **m1 · m3 · m4는 이번 세션 미수행**이다. 모드당 **n=6**(m0 · m6은 **n=3**).
  - **블록 4 직전 ToF near 최대 8/64**(PERSON 1회) 관측. 측정 전 **시리얼 줄 깨짐 1회**(USB CDC 추정). 공조음 상태·장소 **미기록**.
  - 보드는 **m6 상태로 종료**됐다(재부팅 시 m2로 복귀).

### 6.4 `/detect` ToF 메타 wire 확장 — G10 수신측 CLOSE (2026-09-04 PoC-(41) 신설, PR #43 `8827946`)

6.2 G10 미결("`/detect` 계약에 ToF 메타 필드 부재")의 **수신측 절반**을 실코드화했다. ~~⚠️ **G10 수신측 CLOSE ≠ G10 CLOSE** — 송신측(마이크 M5-d + 통합 펌웨어가 실제로 ToF 메타를 실어 보내는 코드)은 **0줄**이며, 본 절이 닫은 것은 "서버가 받을 준비를 마쳤다"까지다.~~ **✅ 송신측도 CLOSE (2026-09-11 PoC-(45) Set 1, PR #52·#53)** — 상세·단서는 **6.2** 참조. 본 절이 확립한 아래 (b) "서버는 `tof_presence`를 재판정하지 않는다"는 송신측 CLOSE 이후에도 무변경.

**(a) 산출물 (근거유형 = 실측, `git show 8827946 --stat` 대조)**
- 신설 `server/app/tof_meta.py` = 순수 함수 4개(`absent_meta` / `parse_tof_meta` / `telemetry_summary` / `evaluate_gate`).
- `constants.py` = wire 필드명 4(`TOF_PRESENCE_FIELD` / `TOF_NEAR_COUNT_FIELD` / `TOF_CENTER_MM_FIELD` / `TOF_MOTION_NDET_FIELD`) + 구조 상수 2(`TOF_ZONE_TOTAL=64` / `TOF_MOTION_AGGREGATE_TOTAL=16`).
- 수신 필드 4종 = 6.2 G10이 지정한 `tof_presence` / `tof_near_count` / `tof_center_mm` / `tof_motion_ndet` **그대로**(신규 필드 발명 0, 학습 16).

**(b) ★ 핵심 설계 — 서버는 `tof_presence`를 재판정하지 않는다 (근거유형 = 논증)**
- Stage A 디바운스 3프레임(9.2)과 Stage B-2 latch 75프레임(9.4)은 **시간축 판정**이라 단발 POST 스냅샷 하나로 재구성할 수 없다. 그래서 presence는 펌웨어가 판정한 결과를 **그대로 신뢰**하고, 나머지 3필드는 증거·표시용 telemetry로만 쓴다.
- 필드 표기 어휘(`near=n/64` / `center=NNNNmm` / `ndet=n/16`)를 9.3(b) 로그 필드 정의와 맞췄다 → 통합 후 **서버 기록 ↔ 펌웨어 시리얼 로그 대조 가능**.
- **✅ [등재] `tof_presence` ↔ 펌웨어 신호 매핑 확정 (2026-09-11 사용자 확정, PoC-(45) Set 1, 근거유형 = 논증)**: `tof_presence` = **Stage A `presence_state` ∧ Stage B-2 `motion_latch_active`**(fused — `tof_common.cpp tofJudgeFrame()` 반환값, 상세 9.4(f)). presence_state 단독은 latch를 거치지 않으므로 본 매핑과 다르다. 근거 = 본 (b) 문단의 "시간축 판정이라 단발 스냅샷으로 재구성 불가 → presence는 펌웨어 판정을 그대로 신뢰" 해석. ⚠️ 인용 출처 관련 단서 = **27.8(h)**.

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

**(f) ~~🟡 [신규 미결] 가짜 ToF 하드코딩 잔존 (발견 2026-09-04 / 문서 반영 2026-09-05, 근거유형 = 실측 grep)~~ → ✅ 해소 (2026-09-08 PoC-(42), PR #47 `846b342`)**: ~~`/detect` 경로에서는 소멸했으나 `server/seed.py`(시드 5건 중 **4건**) + `dashboard/src/lib/mock-data.ts`(5건 중 **4건**)에 `zone_count=… >= 8 + motion=true` 문자열이 **그대로 남아 있다**(나머지 1건씩은 `fire_alarm_bypass`). PR #43 범위 밖이었으나, **부스 데모에서 seed 데이터가 화면에 뜨면 가짜 ToF 문자열이 관람객에게 보인다**(카테고리 26 연동). 해소 = 데모 시나리오 소관.~~ **해소 내용 (근거유형 = 실측 grep)**: `seed.py` 4건 + `mock-data.ts` 4건을 **실 서버 어휘**(`tof_meta.telemetry_summary` = `presence=… near=n/64 center=NNNNmm ndet=n/16`)로 **교체**했다 — **삭제가 아니라 교체**다(지우면 화면이 비고 부스에서 "데이터 없는 시스템"으로 보인다). 사후 실측 = `zone_count=` **코드 전역 0건**. ⚠️ `docs/` **7건**은 **역사 기록이라 의도적 무변경**(본 절·6.2 G10의 증거 인용문). 상세 = **8.4(e)**.

**(g) ④런타임 실측 — 송신측 CLOSE 확인 (2026-09-11 11:35~12:00, 학교·아이폰 핫스팟, mock ML, PoC-(45) Set 1, PR #53)**
- (a) 4값 wire: 보드 `[tof][M5d]` 4값 = 서버 DB `tof_check.reason` **3건 전건 문자 일치**. doorbell/knock(presence=false) → `applied=True passed=False`(변경 전 항상 `tof_absent`였던 값이 바뀜).
- (b) 동시 구동: 11:37:28 → 11:44:06 **6분 38초**, 6회 전송 내내 `gaps=0` / age_ms 3~92 / stk_free 2296·tof_stk 4228~4456 안정 / psram 안정.
- (c) 회귀: 5초 내 재전송 `http=429` + 재시도 줄 없음 / 재플래시 후 nonce 신규(`520bc1d1`).
- (d) 승격 회귀: `tof_dummy` 재플래시 → 기존 로그 포맷 동일 + `NONE->DETECTED`·`fused NONE->PERSON` 전이 반복 관측.
- **G12 재확인**: fire_alarm 0.45 → `low_confidence`로 선차단(sent=False), 0.71·0.95만 발송 — 신뢰도 게이트 선행 정상.
- **미관측**: 신뢰도 ≥0.70 doorbell·knock + presence=false → `tof_rejected` 스킵 경로. 런타임 2건 모두 low_confidence 선차단이라 도달 못함 — 서버 회귀 102건으로 대체 커버.
  - ✅ **후속 — 실모델 경로로 관측됨 (실측·문서 반영 2026-09-14 PoC-(47), 근거유형 = 실측 curl + 화면 catch)**: `doorbell` **1.00** + `presence=false` → `tof_rejected` **1차 미발송**을 **서버 응답·대시보드 화면 양축**에서 확인했다(상세 = **26.10(d)**). ⚠️ **`knock`은 여전히 미관측**이다 — 관측한 클래스는 `doorbell` **하나뿐**. ⚠️ 본 (g)는 **2026-09-11 실기기 런타임**의 기록이고 후속 관측은 **노트북 curl + 실모델**이므로, **본 줄의 "런타임에서 도달 못함"이라는 이력 자체는 무변경**이며 **실기기 관통은 여전히 미수행**이다(취소선 대상 아님).
- 로그 원본 = repo 밖 `~/ddingdong-측정결과/2026-09-11/ToF_meta_uplink_runtime.log`.

**관련**: 6.2(G10 원 미결 / wire 계약) / 카테고리 3(클래스별 ToF 정책 · 신뢰도 임계값 · G12) / 9.2·9.3·9.4(Stage A / B-1 / B-2) / 7.6(A-2 2차 알림) / 카테고리 20(계측 → 실측 → 판정)

### 6.5 보드 2차 체인(`/enrich` 클라이언트) 설계 조사 — 계약 실측 + 미결 재판정 입력 (2026-09-17 PoC-(51) 신설, 발견일 = 반영일 = 2026-09-17, 근거유형 = 항목별 병기)

> **조사·설계 전용** 세션이다 — repo 쓰기 0 / 코드 0줄 / 보드 무접촉. 설계 원본 = repo 밖 `~/ddingdong-측정결과/2026-09-17/enrich_firmware_design/DESIGN.md`(`.gitignore` 차단분 — SSoT엔 요약만). 🔴 **타임아웃 값 · 녹음 길이 · 해상도는 확정하지 않는다.**

**(a) 🔴 「녹음 5초」는 결정으로 등재된 적이 없다 (근거유형 = 실측 grep, 학습 21 역방향)**

- `docs/` 전수 grep 결과 「5초」의 출처는 **셋뿐**이다 — 7.3 함의 줄의 「② ESP32 2차 페이로드 업로드(이미지+**5초 오디오**, 1차보다 큼, 미측정)」 취지 서술 · 카테고리 7 CSR 제품 확정 줄의 「우리 용도(**5초**/16kHz mono)와 정합」 · `server/app/routes.py` 주석.
- 🔴 **그 주석이 가리키는 「카테고리 6.2」에는 `/enrich` 오디오 길이 서술이 없다.** 6.2의 `/enrich` 계약 항목(2026-07-31 PoC-(30), PR #27)은 파트명 · 크기 상한 · 검증 방식만 적고 **길이를 정하지 않는다**. 대조군 = 같은 파일에서 `AUDIO_MAX_BYTES` · `IMAGE_MAX_BYTES` 서술 생존, `docs/`에서 「스티칭」 grep **0건**.
- ⇒ **판정: 「5초」는 확정된 적 없는 값이 확정처럼 유통된 경우다.** 학습 21(미결·차단 사유 자체가 유령일 수 있다)의 **역방향**이며, 코드 주석의 출처 오기는 **27.8(m)**.
- **[산술] 서버 상한과의 관계**: `AUDIO_MAX_BYTES = 320,000 B ÷ 2 B/sample ÷ 16,000 Hz = 10.0초`. 5초 = 160,000 B = 상한의 **50%**, 7초 = 224,000 B = **70%**. 현 1차 페이로드 65,536 B = **20.5%**. ⇒ 서버는 5초도 7초도 받는다.
- 🔴 **녹음 길이 N · pre:post 비율 = 사용자 판단 대기**(6.2 G29의 「비율 미확정」과 같은 축). **본 절은 값을 정하지 않는다.**

**(b) `/enrich` 계약 실물 (근거유형 = 실측 `server/app/routes.py` `enrich()` + `constants.py`)**

| 항목 | 실물 |
|---|---|
| 메서드·경로·인증 | `POST /api/v1/enrich`, `@device_auth`(Bearer `DEVICE_TOKEN`) |
| transport | `multipart/form-data`(1차 A안 동형) |
| 필수 form field | **`client_request_id` 1개뿐** — ★ **`device_id`는 불요**이며 `/detect`와 다르다 |
| 필수 파일 파트 | `image` + `audio` **둘 다 required**(`filename` 비면 400) |
| 크기 상한 | 이미지 512,000 B / 오디오 320,000 B |
| 검증 | 이미지 = 크기 가드 + **JPEG SOI `0xFFD8`** / 오디오 = 프로즌 `audio_decode.decode_pcm16` |
| 선행 레코드 | `Notification.client_request_id` 1건 조회, 없으면 **404** |
| 재처리 가드 | `enrich_status ∈ {completed, skipped, failed}` → **409**(파트를 읽기 **전** 검사) |
| rate limit | 🔴 **없다** — `rate_limit.check_and_register()`는 `detect()` 안에서만 호출된다 |

- ★ **파생 사실 3건**: ① `/enrich`는 `/detect`가 먼저 성공해 행을 만든 뒤에만 200이다 — **순서 역전 = 404** ② **`/detect` 응답 body에 `enrich_status`가 들어 있다**(`pending` / `skipped`) ⇒ **보드가 응답 한 필드만 읽으면 2차 발송 여부를 새 판정 어휘 0개로 알 수 있다** ③ `/enrich`에 rate limit이 없으므로 `/detect` 직후 곧바로 쏴도 **429가 나지 않는다**(429 표면은 `/detect` 연타뿐).
- ⚠️ **6.1의 「`device_id` 5초당 1회」는 `/enrich`에도 걸리는 것처럼 읽힌다** — 실물은 `/detect` 전용이다. 위 표가 그 경계를 적는다.
- 🔴 **[파생 사실 ② 보강 — 2026-09-18 PoC-(53), 근거유형 = 실측 `curl /api/v1/notifications`] `enrich_status`는 응답 최상위가 아니라 `notification_status` 하위 중첩이다**: 위 ②는 「`/detect` 응답 body에 들어 있다」까지만 적고 **계층을 명시하지 않았다**. 실물 최상위 키는 **11개**(`all_scores` · `client_request_id` · `confidence` · `detected_at` · `device_id` · `media` · `notification_status` · `predicted_class` · `request_id` · `stt` · `tof_check`)이며 `enrich_status`는 그중 없다. ⇒ **보드가 읽어야 할 것은 `notification_status.enrich_status`다**(PR #64 구현은 `enrichPeekJson`이 키 이름으로 훑는 방식이라 결과적으로 동작했다 — 6.7(c)). ★ **27.8(c)③이 같은 응답의 `skip_reason` · `primary_sent` · `primary_sent_at`에서 이미 잡은 「부재가 아니라 중첩」 패턴의 재발**이며, 새 오류가 아니라 **같은 자료구조의 미기재분**이다. 실측 상세 = **6.7(e)**.

**(c) 링버퍼 재사용 경계 (근거유형 = 실측 코드 대조 + 논증)**

- 실물 = `MIC_RING_SLOTS 32` × `MIC_DMA_BUF_LEN 1024` samples × 2 B = **65,536 B = 2.048초**이고 `uplink_common.h`에 `static_assert(UPLINK_AUDIO_BYTES == 65536)`가 박혀 있다.
- **재사용 가능** = 적재 루프 · 슬롯 산술 · `MicRingStatus` 관측 · torn-read 회피 지점. **재사용 불가 = 길이**(2차가 2.048초보다 길면 부족).
- 🔴 **[논증] `MIC_RING_SLOTS` 확장은 기각 후보**다 — 무변경 대상(`mic_common.*`, 6.3)이고 `UPLINK_AUDIO_BYTES`가 그 상수에서 파생되므로 **1차 wire 페이로드(64KB/2초 계약)까지 함께 바뀐다**. 권고 = **링버퍼는 pre-roll 공급원으로 두고 2차 녹음분만 별도 PSRAM 버퍼**(`mic_common.*` 무변경, G29 B안 구조와 정합). ⚠️ **채택 확정은 PR 작성 시점**이다.

**(d) PR 분할안 (카테고리 20 「계측 → 실측 → 판정」 적용, 근거유형 = 논증)**

| PR | 성격 | 내용 |
|---|---|---|
| **PR-A** | **방법론 자산** | 카메라 + 마이크 + ToF **동시 구동 관측**. 전송 0줄 · 판정 0줄 → **✅ 실행됨 = PR #63(`41cd6e2`), 상세 = 6.6** |
| **PR-B** | **배관(plumbing)** | 2차 전송 경로(`/detect` → `enrich_status` 게이트 → 캡처 + N초 녹음 → `/enrich`). 수동 트리거, 임계값 비교 0줄. `uplink_common.*`에 **형제 함수 additive** → **✅ 실행됨 = PR #64(`d093d70`), 상세 = 6.7** |
| **PR-C** | **판정 + 정합성 정정** | ④런타임 실측 **이후에만** 착수 — 타임아웃 · 녹음 길이 · 해상도 상수 확정 + decisions.md 등재 |

- ⚠️ **PR-B의 함정 예고 (카테고리 20 「변형과 무엇을 검사하는가를 짝지어라」)**: image ↔ audio 파트 **순서 뒤집기**는 서버 계약상 무해할 수 있으므로 negative control을 **그 변형이 깨는 불변식과 함께** 설계해야 한다.
- 🔴 **PR-B 실 업로드도 6.6의 ARP 함정을 공유한다** — `txerr=0`이 「무선으로 나갔다」를 보장하지 않는다.

**(e) 성분별 재실측 계획 (실행 금지 — 계획만, 근거유형 = 논증)**

- **M-1 ESP32 2차 구간**(캡처 ms + 녹음 N초 + multipart 조립 + POST rtt) = `esp_timer_get_time()` 4구간 스탬프 → 시리얼 1줄(**≤80B** — SSoT = **6.3(h) · 6.3(j)**) / **M-2 서버 자체 구간** = 기존 로그(`decode_ms` · `elapsed_ms`) 수집, 코드 추가 0 / **M-3 카카오 정상 왕복** = 서버 로그 시각 차, 7.3 p95 490ms와 대조 / **M-6 카메라 fb PSRAM 점유** = `logMemoryDiagnostics` pre/post delta → **✅ 6.6에서 실측됨(30,952 B)**.
- 🔴 **M-4 카카오 최악 경로(5회 × 1.5s) · M-5 CSR 타임아웃 만료 3.0초는 실측 불가·시도 금지**다 — 죽은 토큰 주입은 부스 계정 상태를 흔들고, CSR 3.0초 만료는 재현 수단이 없다. ⇒ **산술 상한으로 유지**하고 「실측 아님」을 명기한다.
- **공통 판정 규칙**: 시각 판정은 **서버 access log 기준**(6.3(m) 실측 교훈 — 시리얼은 USB CDC 지연으로 밀린다). **MCP는 로그 파일 해석만** 하고 보드 플래시 · 실발송은 학부생 로컬 몫이다.
- **과금 상한 제안** = 1세션 **≤12 이벤트**(= CSR 180초 = 일 한도 600초의 30%, 30.9의 「스위트 1회 = 12건 = 180초」와 같은 단위). ⚠️ **채택 여부 = 사용자 판단 대기.**

**(f) 🔴 사용자 판단 대기 (본 절은 어느 것도 확정하지 않는다)**

- ~~녹음 길이 N~~ → **✅ 5초 확정**이나 🔴 **pre:post 비율은 미결 유지**(1차 링버퍼 축 = 6.2 G29 · M5-c 보류) / ~~해상도(QVGA · VGA · SVGA)~~ → **✅ QVGA 기본 + VGA 컴파일 플래그 확정** / ~~2차 타임아웃 방식~~ → **✅ C1 전용 상수 신설 확정**이나 🔴 **값은 잠정 15,000ms — 미결 유지** / ~~`/detect`가 skip일 때 2차 발송 여부~~ → **✅ 미발송 + 로그만 확정** / ~~`presence=false`에서 촬영 여부~~ → **✅ 촬영 확정** / ~~`uplink_common.*` additive vs 복제 신설~~ → **✅ additive 확정** / 🔴 카메라 init 시점(상시 vs 이벤트마다) **— 미결 유지** / **6.3(n) 해결책 ①②③**(본 절이 **대신 판단하지 않는다**) **— 미결 유지** / ~~과금·실발송 세션 상한~~ → **✅ 세션당 2차 ≤12 이벤트 확정**.
- **[확정 등재 2026-09-18 PoC-(53), 결정 주체 = 사용자, 근거유형 = 사용자 결정]** 위 확정의 원문 8건 · 근거 · 구현 실물 = **6.7(a)**. 🔴 **닫힌 것과 열린 것의 경계**: **전부 닫힘 5항**(해상도 · skip 발송 · `presence=false` 촬영 · additive · 세션 상한) / **부분만 닫힘 2항**(녹음 길이 · 타임아웃) / **무접촉 2항**(카메라 init 시점 · 6.3(n) 해결책). ⚠️ **PR #64 구현이 카메라를 이벤트마다 init·deinit 한다는 사실((d) 표 `cam ms`)은 배관 구현 선택이지 「카메라 init 시점」 미결의 확정이 아니다** — 그 항목은 **열려 있다**.

**관련**: 6.1(`/enrich` 엔드포인트 · 토큰 소관 · rate limit 경계) / 6.2(G29 pre/post 비율 · `/enrich` 계약 서버 절반 · `AUDIO_MAX_BYTES`) / 6.3(h)(j)(m)(n)(링버퍼 · ≤80B · 시각 판정 · 클립 미결) / **6.6(PR-A 실행분)** / 7.6(i)(영구 포기 정책 재판단) / 7.7(l)(12.1초 재판정) / 카테고리 6 머리(2워커 409 경합) / 카테고리 20(계측 → 실측 → 판정 · 함정 예고) / 카테고리 7(CSR 15초 과금 · 일 한도)

---

### 6.6 `env:camera_probe` — 카메라·마이크·ToF 동시 구동 관측 하네스 + ④런타임 (2026-09-18 PoC-(52) 신설, PR #63 `41cd6e2`)

> **성격 = 방법론 자산**(6.3(o) `env:mic_noiseprobe` · 9.1(e) `tof_pinscan` · 8.4(f) 서문 선례와 같은 축). **제품 동작 불변 · 판정 0 · 임계값 0 · 서버 API 호출 0 · 신규 의존성 0 · 기존 env 무수정.** 6.5(d)의 **PR-A**가 이것이다. 로그 원본 = repo 밖 `~/ddingdong-측정결과/2026-09-18/camera_probe/camera_probe_runtime.log`(`.gitignore` 차단분 — SSoT엔 요약만).

**(a) 산출물과 검증 (근거유형 = 실측 + 문서 인용 = PR #63 본문)**

- 신설 6파일 = `probe_modes.h`(모드 사슬 불변식) · `probe_stats.h`(SOI 검사 + 창 통계) · `src/camera_probe_main.cpp` · `tools/camera_probe_test.cpp` · `CAMERA_PROBE_RUNBOOK.md` · `platformio.ini` **`[env:camera_probe]` 1블록 추가**(삭제 줄 0). `git diff --stat main` = **1250 insertions / 0 deletions**.
- **호스트 테스트 `camera_probe_test` 97 checks passed** — 기존 4종(`jsonpeek_test` · `noise_stats_test` 61 · `noise_modes_test` 46 · `tof_judge_test` 196) 전건 통과 유지(현재값 = **6.3(o)**).
- **negative control 6종 전건 통과**(NC-1 SOI 첫 바이트 비교 제거 / NC-2 길이 가드 제거 / NC-3 표본 0건 구분 제거 / NC-4 인접 모드 2변수 변형 / NC-5 첫 표본 min/max 세팅 제거 / NC-6 비인접 쌍 표 변형) — 전건 **앵커 매치 1 · 변형≠원본 · 재컴파일 확인 · 검출 · 복원 동일 · 자기검증** 통과.
- **빌드** = `camera_probe` SUCCESS(RAM 18.4% / Flash 26.0%) + 기존 11개 env **11/11 SUCCESS**, 컴파일 경고 0. **무접촉 바이너리 증명** = `mic_uplink` 클린 재빌드 md5 · 크기 **완전 동일**.
- **모드 사슬** = m0~m7이 **인접 쌍마다 한 변수만** 다르다(카메라 축 OFF → IDLE → PERIODIC → CONT / WiFi 축 m0↔m1 · m4↔m5 · m3↔m6 / 해상도 축 m6↔m7). **비인접 쌍 `m3↔m6`도 `PROBE_NONADJ_PAIRS`로 코드에 고정**해 호스트 테스트가 순회한다(79 → 97 checks).
- **주석 오기 정정**: `probe_modes.h` 상단이 「m6은 m2와 구성이 동일하다」라 적었으나 실물은 m2 = {IDLE, wifi=on, QVGA} / m6 = {PERIODIC, wifi=off, QVGA}로 **두 필드**가 다르다 — **m6은 m3에서 WiFi 송신만 뺀 구성**이다. Runbook은 원래 맞게 적혀 있어 **두 문서가 어긋나 있었다**. 등재 = **27.8(m)**.

**(b) ④런타임 실측 — 조용한 구간에서 카메라·WiFi ON이 기준선 범위를 벗어나지 않았다 (실측 2026-09-18 10:34~11:00, 랩실, 근거유형 = 실측, 계수 단위 = 창 수 / clip 수)**

> **★ 결론 강도 = 「관측」까지만이다.** 창 수가 적고 조용한 구간에 한정되며 세션 후반에 대화가 유입됐다. 🔴 **6.3(n) 미결을 닫지 않는다** — 해결책 ①②③은 **사용자 판단 대기 그대로**다.

- **프로토콜** = 모드당 창 1개를 버리고 기록, 창 10초. 구간 = m0(win#6~11) m1(12~19) m2(20~25) m3(26~31) m4(32~37) m5(38~43) m6(44~49) m7(50~54) m0복귀(55~56). **m5 후반(win#43 무렵)부터 세션 끝까지 주변 대화 유입**(학부생 확인).
- **조용한 구간 `clip`**(win#6~42):

  | 모드 | 구성 | 창 수 | clip 최소~최대 |
  |---|---|---|---|
  | m0 (기준선) | cam OFF · wifi off | 6 | **3 ~ 14** |
  | m1 | cam OFF · **wifi ON** | 8 | **2 ~ 6** |
  | m2 | cam IDLE · wifi ON | 6 | **1 ~ 6** |
  | m3 | cam PERIODIC · wifi ON | 6 | **0 ~ 4** |
  | m4 | cam CONT · wifi ON | 6 | **1 ~ 3** |
  | m5 | cam CONT · wifi off | 5 | **3 ~ 10** |

- ⇒ **[실측] 카메라·WiFi를 켠 m1~m4의 clip 범위가 기준선 m0(3~14)을 벗어나지 않았다.** ⚠️ **악화 없음을 「관측」한 것이지 「없다」로 판정한 것이 아니다** — 판정 임계가 없고 음향 조건이 통제되지 않았다.
- **대조군(감도 확인)** — 대화 유입 구간(win#43~57)의 clip은 **4 ~ 20**이고 m0 복귀 3창은 **15 · 20 · 16**이다. ⇒ **계측기가 실제 음향 변화는 검출한다.** 🔴 **끝 m0이 대화 구간이라 세션 드리프트는 확인 불가**하다(Runbook이 의도한 드리프트 판별이 이번 세션에서는 성립하지 않았다).
- 🔴 **[실측 — 단발 관측] m3 win#31에서 `pk=741` · `rms=97` · `clip=0`이 나왔다.** 같은 세션의 **다른 전 창은 `pk` 32767 또는 32768**이다(계수 단위 = 창 수, n=1). ⇒ **그 창에서만 마이크 워드가 풀스케일에 닿지 않았다.** ⚠️ **기전 미규명**이며 6.3(n)의 원인 후보를 가르는 단서일 수 있다 — **압축하지 말고 단발 사실로 보존한다. 확정하지 말 것.**

**(c) 카메라 실측 (근거유형 = 실측)**

- **JPEG 크기** = QVGA **5,353 ~ 5,438 B** / VGA **13,791 ~ 13,910 B**. ⇒ 32.2의 「QVGA JPEG ~6KB」와 **자릿수 정합**하며 본 값이 더 좁은 실측이다.
- **캡처 소요** = PERIODIC(1초 1장) **1 / 1 / 1 ms**(min/avg/max) · CONT **최대 71 ms**.
- **건전성** = 60창 누적 `try` **3,563** = `ok` **3,563**, **`nul` 0 · `soi` 0**(SOI 검사 실패 0). ⇒ **WiFi 연결 상태에서 `fb_get` NULL 0건** — 카테고리 17의 esp32-camera #620(WiFi join 후 fb_get fail) 관련 입력이다(상세 = 카테고리 17).
- **init / deinit** = `cam init ok=1 ms=383 psram_used=30,952` · `cam deinit err=0x0 ms=1 psram_back=30,952` ⇒ **프레임버퍼 PSRAM 실점유 = 30,952 B이고 deinit이 동일 바이트를 반환한다(누수 0)**. `[MEM:pre-init]` free 8,305,459 → `[MEM:post-init]` 8,274,507 → `[MEM:post-deinit]` **8,305,459**(pre-init과 동일)로 교차 확인됐다.

**(d) 🔴 WiFi 부하 축은 조용히 무효화될 수 있다 — 관측판 「조용한 가드」 (근거유형 = 실측 설치 파일 대조 + 논증)**

- 설치 `lwipopts.h`의 **`ARP_QUEUEING=1`** 때문에 lwIP는 ARP가 풀릴 때까지 패킷을 큐에 담고 `sendto()`에 **성공을 돌려준다** ⇒ `WiFiUDP::endPacket()`이 1을 반환하고 창 출력은 **`tx` 증가 · `txerr=0`으로 정상처럼 보이는데** 무선으로는 ARP 요청만 이따금 나간다.
- ⇒ 🔴 **`txerr=0`은 「무선으로 송신됐다」를 보장하지 않는다.** 그대로 재면 「WiFi를 켰는데 마이크가 안 흔들린다」는 **거짓 결론**이 가능하다. **PR-B의 실 업로드 경로도 같은 함정을 공유**한다(6.5(d)).
- **차단 = 부팅 줄에 UDP 대상 주소를 노출** + Runbook 2-1에 측정 전 ① 노트북 주소 확인 ② 부팅 줄 대조 ③ 수신 1회 도착 확인 절차. **본 ④런타임에서 m1 구간 수신 확인 2,800 B로 축 유효성이 실증**됐다(근거유형 = 실측).
- Runbook 1절의 「받는 쪽이 없어도 송신 부하는 동일하다」도 정정됐다 — 듣는 **소켓**은 없어도 되지만 그 주소의 **기기**는 살아 있어야 참이다.
- **실측 네트워크 상태** = 연결 `st=3` 57창, `rssi` **−53 ~ −14**(다수 구간 −37 ~ −49), 창당 `tx` 최대 **500**, **`txerr` 전건 0**.

**(e) ⚠️ 시리얼에 SSID가 찍힌다 — public 문서 반출 주의 (근거유형 = 실측 코드 대조)**

- `uplinkConnectWifi()`는 연결 성공 시 `[uplink] WiFi connected SSID=… RSSI=… IP=…`를 시리얼에 출력한다(`firmware/src/uplink_common.cpp`). 본 하네스는 **그 함수를 부르지 않는 경로를 택했다**.
- ⇒ **보드 시리얼 로그를 public repo 문서로 옮길 때는 SSID · IP를 지운다**(본 절도 실값 0건 기재). 🔗 32.6의 「시리얼 SSID/IP 마스킹 출력」 원칙의 재실증이다.

**(f) 한계 (전건 명기)**

- **디지털 관측만** — 전원 레일 전압 **미관측**. **판정 임계 없음.** 음향 조건 **미통제**.
- 끝 m0이 대화 구간이라 **세션 드리프트 확인 불가**. 모드당 창 **5~8개**뿐.
- ToF 시야 = 측정 전 near **0~2/64**로 정리(첫 시도는 9~11이라 물건을 치우고 재시작). 측정 중 near 최대 관측치는 로그에 남아 있다.
- **런타임 negative control은 도달 불가**로 분류됐다(「`fb_return` 제거 → fb 고갈 관측」은 보드 플래시가 필요하고 호스트에서는 `esp_camera_*`를 부를 수 없다) — Runbook 7-2에 사유 기록.

**관련**: **6.5(본 PR이 PR-A인 설계 조사)** / 6.3(n)(본 실측이 입력을 준 미결 — **닫지 않는다**) / 6.3(o)(호스트 테스트 종수 현재값) / 카테고리 2(카메라 핀 표 · I2C 포트 분리) / 카테고리 15(`CONFIG_CAMERA_CORE0` · `loopTask` 코어) / 카테고리 16(env 수 현재값) / 카테고리 17(#620 fb_get fail 입력) / 32.2(QVGA JPEG 크기 · fb_get NULL 0건) / 카테고리 20(계측 → 실측 → 판정 · negative control · 조용한 가드) / 27.8(m)(주석 오기 · 인용처 정정)


---

### 6.7 보드 2차 체인 배관 — `/detect` 게이트 → 캡처 + 5초 녹음 → `/enrich` (`env:enrich_uplink`) + ④런타임 (2026-09-18 PoC-(53) 신설, PR #64 `d093d70`, 발견일 = 반영일 = 2026-09-18, 근거유형 = 항목별 병기)

> 6.5(d)가 **PR-B**로 지목한 **배관(plumbing)** 계층이다. 새 판정 기준·임계·상태 어휘 **0** — 판정은 서버가 이미 끝냈고(`enrich_status`) 보드는 그 한 필드를 읽어 분기만 한다. 🔴 **본 절이 증명하는 것은 「배관이 관통했다」까지**이며 분류 정확도·인식률·15초 예산 달성은 **증명하지 않는다**((i) 한계).

**(a) 사용자 확정 8건 (결정 주체 = 사용자, 2026-09-18, 근거유형 = 사용자 결정)**

| # | 항목 | 확정 내용 |
|---|---|---|
| ① | 체인 순서 | **S1 직렬** — `/detect` 응답의 `enrich_status == "pending"`을 게이트로 쓴다. **새 판정 어휘 0** |
| ② | 2차 녹음 | **5초 · pre 0**(트리거 시점부터). 응답을 기다린 뒤 녹음을 시작하면 말 앞이 잘린다 |
| ③ | 해상도 | **QVGA 기본**, VGA는 **컴파일 플래그** |
| ④ | 타임아웃 | **C1 전용 상수 신설**. 1차 `UPLINK_HTTP_TIMEOUT_MS`는 **무변경** |
| ⑤ | skip 처리 | `/detect`가 skip이면 **2차 미발송 + 로그만**(409·404 생산 회피) |
| ⑥ | `presence=false` | **촬영한다**(보드 재판정 없음) |
| ⑦ | `uplink_common.*` | **additive 형제 함수** — 무변경 대상 예외 허가 |
| ⑧ | 세션 상한 | 2차 **≤12 이벤트** |

- **덤) 응답 파싱 실패** = 2차 **미발송 + 로그**(기본값 폴백 금지) ⇒ 구현은 `ENRICH_GATE_PARSE_FAIL`((c)).
- 🔴 **★ 1차 링버퍼 pre:post 비율(6.2 G29)은 이 8건에 들어 있지 않다 — M5-c 보류 유지**다. ②의 「pre 0」은 **2차 녹음 전용**이고 1차 2초 페이로드의 비율과 **다른 축**이다.
- 🔴 **6.5(f) 미결과의 대응 (근거유형 = 실측 대조)**: (f) 목록 9항 중 **전부 닫힌 것은 5항**(해상도 · skip 발송 · `presence=false` 촬영 · additive · 세션 상한), **부분만 닫힌 것은 2항**(녹음 길이 = N만 확정·비율 미결 / 타임아웃 = 방식만 확정·값 잠정), **손대지 않은 것은 2항**(카메라 init 시점 · 6.3(n) 해결책 ①②③)이다. ①은 (f) 목록에 **없던 항목**이라 신규 확정이다.

**(b) 산출물 (근거유형 = 실측, `git show d093d70 --stat`)**

- **7파일 1,225 insertions / 0 deletions.** 신설 4 = `firmware/include/enrich_wire.h` · `firmware/src/enrich_uplink_main.cpp` · `firmware/tools/enrich_wire_test.cpp` · `firmware/ENRICH_UPLINK_RUNBOOK.md`. 수정 3 = `uplink_common.h`(+43) · `uplink_common.cpp`(+39) · `platformio.ini`(+39).
- `[env:*]` **12개 → 13개**이며 **추가만**이고 삭제 줄 **0**, 기존 12 env 무수정(현재값 = 카테고리 16).

**(c) 구현 실물 (근거유형 = 실측 코드 대조)**

- `ENRICH_AUDIO_BUFFERS = 80` → 81,920 샘플 = **163,840 B = 5.120초** = 서버 `AUDIO_MAX_BYTES` 320,000 B의 **51.2%**. 5.000초는 **78.125 버퍼**라 정수배가 아니어서 **올렸다**(부분 버퍼 분기 회피, 6.3(h) 선례).
- **불변식 static_assert 2쌍** = **I-A** 실제 녹음 길이 ≥ 5.000초 / **I-B** 바이트 수 ≤ `ENRICH_SERVER_AUDIO_MAX_BYTES`. 별도로 `uplink_common.h`가 DMA 버퍼 길이·샘플레이트를 `mic_common.h`와 **묶는 static_assert 2건**을 건다 — 순수 헤더가 보지 못하는 **호스트↔보드 드리프트**를 보드 빌드에서 잡는 장치다.
- `UPLINK_ENRICH_HTTP_TIMEOUT_MS = 15000` — 🔴 **잠정값**이며 PR-C 재판정 트리거가 주석에 각인돼 있다(재계산 입력 = **7.7(l)**).
- `ENRICH_SESSION_MAX_EVENTS = 12`, 경계는 `<`(`enrichSessionAllows`).
- 게이트 3상태 = `ENRICH_GATE_PENDING` / `ENRICH_GATE_SKIP` / `ENRICH_GATE_PARSE_FAIL`.
- 호스트 테스트 `enrich_wire_test` **90 checks**(계수 단위 = checks 수, 현재값 = **6.3(o)**).

**(d) ④런타임 4건 (실측 2026-09-18 14:47~15:00 KST, 근거유형 = 실측, 계수 단위 = 이벤트 수, n=4)**

환경 = **랩실 아님 · 학부생 로컬 · 아이폰 핫스팟**. 실모델 확증 = RSS **462,608 KB** · TF 매핑 **54**(동일 입력 2회 일치는 보드 경로라 **미수행**). 🔴 **터널 미기동 · 대시보드 미기동**.

| # | 시각 | presence | gate | 1차 rtt | 2차 | cam ms | jpeg | body |
|---|---|---|---|---|---|---|---|---|
| 1 | 14:47:28 | false | skip | 683ms | 미발송 | — | — | — |
| 2 | 14:47:58 | true | pending | 4,902ms | 200 / 6,710ms | 382/131 | 4,604 B | 168,882 |
| 3 | 14:50:02 | true | pending | 4,301ms | 200 / 10,014ms | 383/130 | 4,619 B | 168,897 |
| 4 | 14:59:49 | true | pending | 5,814ms | **-11 / 15,474ms** | 382/131 | 4,572 B | 168,850 |

- 전건 `cls=knock`(conf 1.0 / 1.0 / 1.0 / 0.97) · `soi=1` · `gaps=0` · `stk_free=2440`.
- **PSRAM** = 캡처마다 7,332,595 → 7,301,643 → 7,332,595(**delta 30,952 B**, deinit이 동일 바이트 반환 = **누수 0**). 6.6(c)의 30,952 B와 **일치**한다. ⚠️ **캡처는 3회다** — #1은 `gate=skip`이라 카메라 init 자체가 없다(🔴 원 로그·위임의 「4/4 동일」은 **오기**, 27.8(n)②).
- 세션 카운터 `sent=0/12` → `1/12` → `2/12`(게이트 통과 시점 값). **⑧ 상한 미도달.**
- `-11` = `HTTPC_ERROR_READ_TIMEOUT`이며 **잠정 상수 15,000ms 직후**에 났다. 서버측 대응 = (e)#4.

**(e) 서버측 종결 상태 (근거유형 = 실측 — `curl /api/v1/notifications` 15:01 + 서버 access log)**

- ★ **`enrich_status`는 응답 최상위가 아니라 `notification_status` 하위 중첩**이다. 최상위 키는 **11개**(`all_scores` · `client_request_id` · `confidence` · `detected_at` · `device_id` · `media` · `notification_status` · `predicted_class` · `request_id` · `stt` · `tof_check`). ⇒ **6.5(b) 파생 사실 ②의 계층 보강**.
- #1 **`skipped`**(`skip_reason="tof_rejected"`) · `stt` null / #2 **`completed`**(primary 14:47:58.970 → secondary 14:48:06.321) · `stt` null / #3 **`completed`**(primary 14:50:02.849 → secondary 14:50:14.411) · `stt` null / #4 🔴 **`failed`**(`primary_sent=false` · `skip_reason="kakao_api_error"`)이나 **`stt`는 실존**((g)).
- **서버측 2차 소요**(`primary_sent_at` → `secondary_sent_at`) = #2 **7.351초** / #3 **11.562초**(7.7(g) 「2차 15초 예산」의 **49% / 77%**). #4는 `primary_sent_at`이 null이라 **산출 불가**다.
- 🔴 **#4 = 보드 타임아웃(-11) ↔ 서버 200 종결**이 같은 이벤트에서 났다 — 7.6(i) 재판단 입력.

**(f) 카카오톡 도착 (근거유형 = 실측 — PC 카카오톡 화면)**

- 14:47 1차 텍스트 / 14:48 2차 feed / 14:50 1차 + 2차 feed / 🔴 **15:00 이벤트는 도착 0건**(서버 `kakao_api_error`와 정합).
- 자막 text는 #2 #3 **모두 미도착** = `stt` null(말소리 없는 입력) ⇒ **7.6(e)가 규정한 「자막 부재」 경로가 실기기에서 처음 밟혔다**.
- ⚠️ 사진은 전부 **빈 박스**다 — **터널 미기동이라 정상 동작**(7.4)이며 **실렌더는 미확인**이다.
- 🔴 **캡처 화면에 실명·프로필이 들어 있어 대외 자료(발표·보고서·공개 저장소) 사용 금지**다. 본 문서에는 화면·실명·아이디 **0건** 기재(32.6 · 6.6(e) 선례).

**(g) 🔴 실 육성 STT — 첫 실기기 관통 (실측 2026-09-18 14:59:59, 근거유형 = 실측, 계수 단위 = 발화 건수, n=1)**

- 발화 원문(학부생 육성, 보드 INMP441 경유, **5.120초** 녹음) = 「계세요 택배입니다 문 앞에 놓고 갈게요」. CSR 인식 결과 = **원문과 완전 일치(오류 0자)**.
- 조건 = **실내 조용 / 화자 1 / 거리 미측정 / n=1**.
- 🔴 **7.7(m)의 CSR 소규모 실측(이어폰 근접 · CER 6.77% · 10문장)과 병치 금지**다 — 입력 경로(이어폰 재생 ↔ 보드 마이크 실 육성) · 건수 · 거리 조건이 **전부 다르다**. 경계 갱신 = **7.7(j)**.
- ⚠️ 이 건은 `notification_status`가 **`failed`**인 이벤트에서 났다((e)#4) — **STT 성공과 알림 성공은 다른 축**이라는 7.7(b) 설계가 실기기에서 재현된 것이다.

**(h) 기타 관측 (근거유형 = 실측)**

- `E (...) gdma: gdma_disconnect(299): no peripheral is connected to the channel`이 **카메라 deinit마다 3회** 출력됐다. PSRAM 반환·`soi=1` 정상이라 **기능 영향은 안 보이나 기전 미규명**이다. 🔴 **6.6(`env:camera_probe`) 세션에서는 이 줄이 없었고 `deinit err=0x0`였다** — 두 env의 차이가 무엇인지는 **미규명**이며 원인을 지정하지 않는다.
- 보드 WiFi = PRIMARY **1회 timeout 후 재연결**(RSSI **-46**). FALLBACK은 플레이스홀더라 **미연결**.
- 세션 종료 후 `lsof -nP -iTCP:5000 -sTCP:LISTEN` **빈 출력** 확인(카테고리 21 위생).

**(i) 🔴 한계 — 「관통 확인」과 「검증 완료」를 가른다**

- **관통 확인된 것** = 게이트 분기(skip 1 / pending 3) · 캡처 · 5.120초 녹음 · multipart 조립 · `/enrich` 도달 · 서버 종결 · 세션 카운터. **4/4 이벤트가 설계대로 분기**했다.
- **증명되지 않은 것** = ① **실 초인종 음원 미사용**(도어벨 4유닛 미도착 — 전건 `knock` 입력) ② **부스 소음 미재현** ③ **QVGA↔VGA 비교 미수행** ④ **1차 rtt 성분 분해 미수행**(6.5(e) M-1 미착수 — 6.2의 단서 참조) ⑤ **2차 이벤트 n=3, 정상 종결 n=2** ⑥ **터널 미기동으로 사진 실렌더 미확인** ⑦ **대시보드 미확인** ⑧ **각 수치 단발**(반복 측정 0).
- 🔴 따라서 **분류 정확도 · 실 육성 인식률 · 15초 예산 달성 · 2차 체인 신뢰성** 중 **어느 것도 본 절이 확정하지 않는다**. 타임아웃 값 확정은 **PR-C 소관**이며 재계산 입력은 **7.7(l)**이다.

**관련**: 6.5(d)(본 PR이 PR-B) / 6.5(f)(확정 8건이 닫은 범위) / 6.5(b)(`/enrich` 계약 · `enrich_status` 계층 보강) / 6.5(e)(M-1 성분 분해 미착수 · 세션 ≤12 상한의 출처) / 6.2(1차 rtt 단서 · G29 pre:post 미결) / 6.3(h)(링버퍼·정수 버퍼 선례) / 6.3(o)(호스트 테스트 5종 → 6종) / 6.6(카메라 PSRAM 30,952 B 대조 · gdma 줄 부재 대조 · ARP 함정) / 카테고리 16(env 12개 → 13개) / 7.6(e)(자막 부재 경로) / 7.6(i)(🔴 **미결 유지** — 재판단 입력 추가) / 7.7(b)(STT 실패 ≠ `enrich_status="failed"`) / 7.7(g)(2차 15초 예산) / 7.7(j)(실 육성 경계 갱신) / 7.7(l)(🔴 **미결 유지** — 12.1초 재판정 입력) / 7.7(m)(🔴 **병치 금지**) / 27.8(n)(본 세션 위임·자체 오류) / 카테고리 20(계측 → 실측 → 판정)

---

## 카테고리 7: STT + 알림

- **STT**: Naver Clova Speech (CSR) — ~~인터폰 노이즈~~ CER 6.49%
  - 🔴 **[정정 — 발견·반영 2026-09-16 PoC-(50), 근거유형 = 문서 인용(웹 원문 재확인)]** 위 「인터폰 노이즈」는 **우리가 붙인 해석**이었고, **6.49%는 우리가 쓰는 CSR의 수치가 아니다.** 제품 표기(`Naver Clova Speech (CSR)`)와 아래 CSR 유지 결정은 **본 항에서 건드리지 않는다.**
    - **출처** = 리턴제로 공개 벤치마크 `https://github.com/rtzr/Awesome-Korean-Speech-Recognition`(README 본문 표 원문 대조).
    - **6.49%가 있는 자리** = 열 「**저음질 전화망**」(AI-Hub, *"실제 상담 환경에서 발생하는 다양한 잡음을 포함한 저음질 전화망 데이터"*) × 행 「**Naver ClovaSpeech**」다. ⇒ **「인터폰」은 표 어디에도 없다.**
    - 🔴 **엔진이 다르다** — 벤치마크가 평가 대상으로 나열한 네이버 API는 **CLOVA Speech**이며, NCP 문서상 **CSR과 별개 서비스**다(위 2026-08-02 통합 발견 note와 같은 축). ⇒ **CSR의 실측 근거로 쓸 수 없다.**
    - 같은 열의 **Google api v2 = 14.11%**(SSoT **첫 등재**). 같은 열의 **리턴제로 = 4.40%** — ⚠️ **벤치마크 작성사가 곧 그 표의 상위 업체**라는 점을 근거 등급에 반영해 읽어야 한다. 규모 = **테스트셋당 3,000문장 샘플링**(README 명시).
    - **관찰(결정 아님)**: 벤치마크가 실제로 잰 엔진(**CLOVA Speech**)은 오히려 **우리 폴백 후보 제품 쪽**이다(아래 「폴백 = CLOVA Speech 단문인식」).
    - ⚠️ **압축 손실 사례** — 열(저음질 전화망)과 엔진(CLOVA Speech)이 **탈락한 요약이 CSR 근거로 굳었다**. 등재 = **27.8(l)⑥**.
    - 🔴 **사용자 판단 대기**: 본 정정으로 **아래 「STT 제품 = CSR 유지 확정」의 근거 하나가 약해졌다.** **결정 재검토 여부와 발표 문구는 사용자 판단 대기**이며, **본 항에서 결정을 바꾸지 않는다**(사용자 방침 = 발표 문구는 개발 종료 후 결정).
    - 🔗 **우리 엔진(CSR) 자체의 인식률 실측 = 7.7(m)** — ⚠️ **위 6.49%와 병치 금지**(엔진 · 데이터 · 규모가 전부 다르다).
  - **note (발견, 결정 아님, 2026-08-02)**: 콘솔 화면 catch + 공식 안내 확인 — 네이버가 CSR 기능을 CLOVA Speech로 통합 제공 안내. CSR 문서(User Guide 14 / FAQ 6)는 잔존하나 신규 이용이 CLOVA Speech로 유도되는지 불명. ∴ STT 제품 선택(CSR 유지 가능 여부 vs CLOVA Speech 전환) 재검토 필요 — 11주차 서버 연동 전 확정. A-1 STT 왕복 실측은 제품 결정 후 defer.
  - **✅ 결정: STT 제품 = CSR 유지 확정 (2026-08-03 PoC-(33))**: 위 2026-08-02 통합 발견 note의 재검토 결론. 근거 3 — ① NCP 콘솔 `AI·Application Service > AI·NAVER API > Application` 등록 화면에서 **CSR 신규 선택 가능 확인**(학부생 화면 catch, 2026-08-03 — 학습 13 화면 우선, 문서 결론보다 우선) ② CSR 스펙(최소 16kHz 이상 · 최대 60초 · REST 파일 업로드)이 우리 용도(5초/16kHz mono)와 정합 ③ 네이버 통합 배너는 종료 공지 아님(CSR 잔존). 폴백 = **CLOVA Speech 단문인식**(REST 60초, CSR과 동일 파일 업로드 패턴) — gRPC 스트리밍은 이질적 프로토콜이라 후순위. ~~⚠️ **A-1 STT 왕복 실측 = 미실측(defer, 학습 19)** — 제품 결정으로 언블록됐으나 실측 자체는 미수행. 선행 = CSR Application 생성 + Client ID/Secret 발급(학부생 몫, 30.9 참조).~~ **✅ 왕복 ④런타임 실증 완료 (실측 2026-09-05 / 문서 반영 2026-09-05, 근거유형 = 실측)**: 실 CSR 호출 왕복 **0.892초**(15초 예산의 5.9%) + 한국어 인식 성공. 15초 단위 과금도 콘솔 화면 숫자로 확증(상세 = 30.9). ~~⚠️ **왕복 실증 ≠ STT 서버 배선** — `server/`의 STT 호출 코드는 여전히 **0줄**이고 7.6 A-2 자막은 mock 문구(`_MOCK_TRANSCRIPTS`)다. 이 두 사실은 분리해 읽어야 한다.~~ **✅ 서버 배선 CLOSE (실측·문서 반영 2026-09-08 PoC-(42), PR #45 `9b3e3a2`, 근거유형 = 실측)**: `server/app/stt.py` 신설로 실 CSR 호출이 실코드화됐고 `/enrich` 자막 소스가 mock → 실 STT로 전환됐다. 위 "**0줄**"은 해소됐다(상세 = 신설 절 **7.7**). ⚠️ **STT 배선 CLOSE ≠ 2차 15초 체인 검증** — 7.7(g)의 1.755초는 **서버측 구간**이며 ESP32 캡처·업로드·2차 페이로드 전송이 **미포함**이다. ※ `_MOCK_TRANSCRIPTS`는 NCP 자격증명 미설정 시의 폴백으로 **코드에 잔존**한다(제거 아님). ⚠️ **요금 불일치 발견**: CSR 실요금 ≈ **15초당 4원**(2026 KR 요금표) ↔ 기존 SSoT(30.9) "초당 0.5원/분당 30원" 불일치 → 30.9에서 취소선+현행값 정정.
- **카카오톡**: '나에게 보내기' (memo) — 비즈 앱 심사 회피
- **이미지**: ~~카카오 이미지 업로드 API (S3 불필요)~~ **memo엔 이미지 업로드 API 부재 — image_url=서버 자체 public 호스팅 필수 (2026-07-31 PoC-(30) E 실사)**: 카카오톡 메시지 API(나에게 보내기)엔 이미지 파일 업로드 엔드포인트 부재. memo 3종(default/custom/scrap) 전부 이미지를 `content.image_url`(사전 호스팅된 public URL 문자열)로만 수신 — 이미지 바이트 미통과. mud-kage CDN을 뱉는 카카오 이미지 업로드 API는 **비즈메시지/친구톡** 계열(비즈채널+심사 필요)이라 memo 경로(비즈앱 심사 회피 목적, 본 카테고리)와 배치. ∴ 진실 = 서버(11주차 EC2)가 ESP32 캡처 이미지를 스스로 public URL로 호스팅(EC2 static route 등, "S3 제품"은 회피 가능하나 public 호스팅 자체는 필수) 후 그 URL을 `image_url`에 실어 `memo/default/send` 호출. 이미지 feed 스코프 = `talk_message` 단일(텍스트와 동일, 추가 동의 불필요). ⚠️ 11주차 2차 체인 아키텍처(이미지 호스팅 방식 = EC2 static route vs 오브젝트 스토리지) 확정 필요.
  - **✅ A-2 스켈레톤 완료 (2026-08-02 PoC-(32), PR #29 `c30e728`)**: 위 정정 후속으로 서버측 public 호스팅 **스켈레톤 실코드화**. 핵심 결정 = opaque capability URL(`secrets.token_urlsafe` 랜덤 키, `notification_id` 미유래 — 추측 불가) + 비인증 서빙 라우트(`GET /captures/<opaque_id>`, 카카오 lazy fetch가 비인증이라 인증 붙이면 깨짐 → 유일 게이트 = opaque 키 + 경로 화이트리스트로 traversal 차단) + TTL 72h(lazy fetch 특성상 짧게 못 잡음, cleanup 헬퍼는 미스케줄) + 로컬 파일시스템 단일 concrete 구현(`image_store.py`, 11주차 EC2 static route 또는 오브젝트 스토리지로 이 모듈만 교체 지점). 로컬 라운드트립 실증(enrich 저장 → image_url 발급 → GET 200 + 바이트 일치, curl 회귀 25종 0 fail). ★ 실 public 호스팅 제품(EC2 static vs 오브젝트 스토리지) 확정은 여전히 11주차 미결 — 스켈레톤 완료지 호스팅 방식 확정 아님.
- **토큰**: 액세스 6시간 + 리프레시 60일, SQLite 저장
  - **★ 재발급 (2026-09-02)**: 본 카테고리 7.2/7.3 실측일(2026-07-29·07-31)로부터 리프레시 토큰 만료를 추정하면 **2026-09-27~29**로, **발표 구간(9/21~9/30)과 겹치는 리스크**가 있었다(⚠️ 근거유형 = **논증** — 최초 발급일 기록이 코드·문서 어디에도 없어 7.2/7.3 실측일로부터의 **추정**이었음). 카카오 디벨로퍼스 REST API 테스트 도구에서 재발급(인증 앱 = Ddingdong(1456718) / 스코프 = **talk_message 단독** 확인) → 60일 리셋으로 발표 구간 리스크 소멸. 토큰 실값은 env 경유만, 본 문서 미기록. **재발경로 차단**: 본 재발급일(2026-09-02)을 SSoT로 남겨 다음 만료 추정이 다시 추정이 되지 않게 한다 — 다음 만료 예상 ≈ **2026-11-01 전후**(60일). ⚠️ **정정 (발견 2026-09-03 / 문서 반영 2026-09-03)**: 위 '재발급'은 REST API 테스트 도구가 수행한 **access 토큰 재발급**이었다 — 이 도구는 access 토큰만 발급하며, refresh 토큰 재발급은 인가 코드 흐름(OAuth)으로만 가능하다는 사실이 이후 확인됐다(상세 = 카테고리 7.5(e)). '60일 리셋'·'다음 만료 예상' 서술은 이 사실이 밝혀지기 전의 **추정**이었던 것으로 재해석한다. 2026-09-03 OAuth 인가 코드 흐름으로 refresh를 정식 재발급해 실측 완료 — `refresh_token_expires_in=5,183,999초(60일)`, 다음 만료 ≈ **2026-11-02**(이번엔 추정이 아니라 실측). ⚠️ **[2026-09-14 PoC-(47)]** 본 문단의 「다음 만료 ≈ 2026-11-02」는 **2026-09-03 시점 계산치**이며 **현재값이 아니다** — DB 실측 현재값 = **2026-11-10 01:41**, 정본 = **7.5(e)**.
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
- 🟡 **[신규 미결] 터널 미기동이 대시보드에서도 사진을 죽인다 — 리허설 체크리스트 항목 확정 (발견·문서 반영 2026-09-09 PoC-(44), 근거유형 = 실측 화면 catch)**: `/notifications` 화면에 **"사진을 불러올 수 없어요"**가 실제로 떴다. 원인 = `DDINGDONG_CAPTURE_URL_BASE`가 **9/08의 죽은 터널 주소**를 가리키고 있었고 터널이 기동돼 있지 않았다(위 확정 절차 미수행 상태).
  - ★ **2026-09-03에 카카오톡에서 같은 증상이 있었고, 대시보드에서도 같은 일이 난다는 것이 처음 확인됐다** — 소비처가 **카카오 lazy fetch 하나가 아니라 브라우저 `<img>`까지 둘**이며, 둘 다 **같은 env 한 줄에 매달려 있다**. 터널이 죽으면 **2차 체인의 시각 산출물이 전부** 사라진다.
  - ✅ **리허설 체크리스트 항목으로 확정**: 부스·리허설 기동 시 **터널 기동 → `.env` 교체 → 서버 재기동**을 **사진 관련 화면을 열기 전에** 끝낸다. **판정 방법** = 대시보드 `/notifications`에서 사진 카드가 렌더되는지 + 카카오톡 사진 카드가 도착하는지 **양쪽 모두** 확인한다(한쪽만 보면 나머지 소비처가 죽은 것을 놓친다).
  - ⚠️ **이것은 코드 결함이 아니라 운영 절차 누락**이다 — 화면 문구("사진을 불러올 수 없어요")는 **정상 동작**이며 고칠 대상이 아니다. 고칠 대상은 **기동 순서**다.
  - 🆕 **[실측 2026-09-16 14:00~14:08 PoC-(50)] 위 판정 방법(카톡 + 대시보드 양축)을 실제로 수행해 통과했다** — ★ **본 미결에 취소선을 긋지 않는다**: **리허설 1회 통과 ≠ 발표 당일 체크리스트 해소**이며, 절차는 **당일에 다시 수행**해야 하는 항목이다.
    - **기동**: quick tunnel 생성 → `.env`의 `DDINGDONG_CAPTURE_URL_BASE`를 `>>`로 추가(⚠️ 이로써 **키 중복 3줄** — 마지막 줄이 적용된다, 카테고리 21 「`>>` 추가가 키 중복을 누적시킨다」 미결 연동) → **실모델 서버**(`venv_real`, RSS **462,272 KB** / TF 매핑 **54**) → **터널 경유 401 관통** 확인(위 「관통 확인 = 변수격리 도구」 그대로).
    - **`/detect`**: P1(`presence=false`) `doorbell 1.0` → `tof_rejected`로 **미발송** / P2(`presence=true`) → **1차 발송**.
    - **`/enrich`**: HTTP **200**, curl 왕복 **2.29초**(15초 예산 내), `enrich_status=completed`, `secondary_sent=true`.
    - **카카오톡(PC 화면 catch)**: 1차 텍스트 → **사진 카드(실사진 렌더)** → **자막 text**(`transcript`와 **완전 일치**).
    - **대시보드 `/notifications`**: 사진 **렌더 · 크게 보기 정상** + 자막 표시 + 거리 센서 「사람 확인」, P1 카드는 **「발송 제외」**.
    - **access log `/captures` GET 2회**(14:03:12 카카오 fetch / 14:04:42 대시보드) ⇒ **소비처 2개**로, 위 ★ 서술(카카오 lazy fetch + 브라우저 `<img>`)과 **실물이 일치**했다.
    - ⚠️ **한계**: 사진은 **picsum 무작위 이미지**(카메라 실캡처 아님 — ESP32 `/enrich` 송신측 미구현)이고, **2차 모바일 렌더는 미캡처**다. 캡처 화면에 프로필 사진·실명이 포함돼 **대외 자료 사용 금지**.
    - 🔗 **같은 리허설의 다른 관측** = 7.7(h)(첫 어절 누락 재발) · 7.5(f)(2행 문구) · 8.5(d)(폴링 간격).
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
- 🟡 **[등재] 카카오 OAuth 에러 코드 3종 (PoC-(45) 문서 반영, 근거유형 = 문서 인용, 미실측)**: `KOE320` = 인가 코드 만료/재사용 / `KOE006` = redirect_uri 불일치 / `KOE010` = client_secret 불일치. 위 확정 절차 재실행 시 디버깅 참조용.
- ~~refresh 발급일 = 2026-09-03, `refresh_token_expires_in` = 5,183,999초(60일). 다음 만료 ≈ **2026-11-02**. 이제 추정이 아니라 실측이다(2026-09-02 재발급은 추정이었음).~~ → **정정 (발견·문서 반영 2026-09-14 PoC-(47), 근거유형 = 실측 DB 조회)**: refresh **발급일 2026-09-03** · `refresh_token_expires_in` **5,183,999초(60일)**는 **무변경**이나, **현재값은 DB가 정본**이다 — `kakao_tokens` SINGLETON `id=1` 실측: ~~`access_expires_at` **2026-09-12 10:40** / `refresh_expires_at` **2026-11-10 01:41**(naive UTC) / `updated_at` **2026-09-12 04:40**(조회 시각 = 2026-09-14 05:01).~~ → **[현재값 갱신 2026-09-15 PoC-(49), 근거유형 = 실측 DB 조회]** `access_expires_at` **2026-09-15 14:04:17** / `refresh_expires_at` **2026-11-10 01:41:19**(**불변**) / `updated_at` **2026-09-15 08:04:18**(전건 naive UTC, 조회 시각 = 2026-09-15 08:04:20 UTC). 갱신 경위 = 아래 「자동 갱신 ④런타임 재확인」. ⇒ **현재 refresh 만료 = 2026-11-10 01:41**이며, 위 「≈ 2026-11-02」는 **발급일 + 60일 계산치**였다.
- ⚠️ **[일정 영향 — 2026-09-17 PoC-(51) 등재, 근거유형 = 사용자 발언(2026-09-17) + 위 DB 실측]** 사용자가 **발표를 11월(날짜 미정)**로 정정했다. ⇒ **refresh 만료(2026-11-10 01:41, naive UTC)가 발표 구간과 겹칠 수 있다.** 2026-09-02 항목이 *"발표 구간(9/21~9/30)과 겹치는 리스크"*를 근거로 재발급했던 것과 **같은 축이 되살아난 것**이다.
- ⇒ **판정 방법**: 위 「자동 갱신 배선」이 실동작하면 만료는 구조적으로 리셋되지만, **「잔여 1개월 미만일 때만 refresh 재발급」은 여전히 문서 인용·미실측**이고 **`refresh_token` 값 변경 여부는 미비교**다. 🔴 **발표일이 확정되면 그 날짜 기준으로 만료 여유를 재확인**한다 — 본 항은 **값·대응을 확정하지 않는다**. 🔗 AWS 무료 기간(~2026-11-13)의 같은 축 = **30.1**.
  - ⚠️ **「refresh DB 생존」 ≠ 「자동 갱신 실제 작동」**: 본 세션은 **카카오톡 실발송 0건**이라 갱신 경로를 **타지 않았다**. 아래 *"잔여 1개월 미만일 때만 재발급"*의 **미실측 꼬리표와 판정 방법(2026-10월 초 `refresh_token` 값 변경 여부 로그 확인)은 그대로 유효**하다.
  - ⚠️ **`updated_at` 2026-09-12가 33.6(a)의 카카오톡 실발송 세션과 같은 날**이나 **인과는 미실증**이다(발송이 갱신을 돌렸는지 / refresh가 실제 재발급됐는지 **로그 미확인**). **확정하지 말 것.**
  - **토큰 값 미기록** — 길이만 확인했고 값은 화면에 출력하지 않았다(본 (e) 말미 "토큰·시크릿 실값은 본 문서에 미기록" 준수).
- 자동 갱신 배선 완료 — 잔여 1개월 미만 시 카카오가 refresh를 재발급해 내려주면 코드가 저장 → 서버가 주기적으로 돌면 만료가 구조적으로 계속 리셋된다. ⚠️ "잔여 1개월 미만일 때만 재발급"은 공식 문서 서술(근거유형 = **문서 인용, 미실측**). 판정 방법 = 2026-10월 초 갱신 시 `refresh_token` 값 변경 여부를 로그로 확인.
- ✅ **자동 갱신 배선 ④런타임 실증 (실측 2026-09-05 / 문서 반영 2026-09-05, 근거유형 = 실측)**: `.env`의 `KAKAO_ACCESS_TOKEN`이 만료(`ACCESS_TOKEN_EXPIRED`, code -401) 상태였는데도 카카오톡 발송이 성공했다. DB(`kakao_tokens` SINGLETON_ID=1)의 access 토큰으로 `/v1/user/access_token_info`를 조회하니 `expires_in 21083`초 — 6시간 TTL(21600) 대비 **약 8.6분 전 발급**이고, 그 시각이 그날 첫 `/detect` 호출 시점과 일치한다. → PR #40의 **401 자가 치유 + refresh 갱신 배선이 실동작함이 시계로 증명**됐다(위 "자동 갱신 배선 완료"의 미검증 꼬리표 해소). ⚠️ 단 **"잔여 1개월 미만일 때만 refresh 재발급"은 여전히 문서 인용·미실측**이며, 판정 방법(2026-10월 초 갱신 시 `refresh_token` 값 변경 여부 로그 확인)도 그대로 유효하다.
- ✅ **자동 갱신 ④런타임 재확인 — 만료 상태에서 실발송 1건이 access를 갱신했다 (실측·문서 반영 2026-09-15 PoC-(49), 근거유형 = 실측, 로그 원본 = repo 밖 `~/ddingdong-측정결과/2026-09-15/kakao_refresh_rehearsal_2.log`)**: access가 **3일 넘게 만료**된 상태에서 `POST /api/v1/detect`를 **2회**(P1 `presence=false` / P2 `presence=true`) 실호출했다. **실모델 확증 3축 충족** — RSS **464,576KB** / TF 라이브러리 매핑 **54개** / 두 호출 `all_scores` **완전 일치**.

  | 스냅샷 | `access_expires_at` | `refresh_expires_at` | `updated_at` |
  |---|---|---|---|
  | S0(착수 전) | 2026-09-12 10:40:16 | 2026-11-10 01:41:19 | 2026-09-12 04:40:17 |
  | S1(P1 직후) | **S0와 완전 동일** | 동일 | 동일 |
  | S2(P2 직후) | **2026-09-15 14:04:17** | **불변** | **2026-09-15 08:04:18** |

  (전건 **naive UTC**. 토큰 값은 **미출력** — 길이만 확인했다.)
  - **P1** = `doorbell` **1.0** · `tof_check.passed=false` · `skip_reason="tof_rejected"` · **`primary_sent=false`** ⇒ **발송을 시도하지 않은 호출은 갱신을 유발하지 않는다**(S0 = S1).
  - **P2** = **`primary_sent=true`** · `primary_sent_at` **2026-09-15T17:04:18.922+09:00** ⇒ **갱신은 P2 호출에서 일어났다.** 새 access의 TTL = **21,600초(6시간)**.
  - **P2 이후 첫 폴링에서 만료 WARNING이 사라졌다** — DB 상태와 **독립적인 경로**로 「만료 상태 탈출」이 재확인된다(8.5(d) 연동).
  - **도착 확인 (근거유형 = 실측 화면 catch)**: **PC 카카오톡과 모바일 카카오톡에서 동일하게 표시**됐다 — 1행 「🔔[띵동] 초인종이 울렸어요.」 + 2행 「모바일에서 확인해 주세요.」 + 앱 버튼 「Ddingdong」. 도착 시각 **17:04 KST**. 2행의 출처 = **(f)** 참조.
  - 🆕 **위 (e)의 「`updated_at`이 실발송 세션과 같은 날이나 인과는 미실증」이 본 회차에서 닫혔다** — **같은 호출(P2) 안에서 `primary_sent=true`와 `updated_at` 이동이 함께 관측**됐기 때문이다. ⚠️ **닫힌 것은 「발송이 갱신을 돌렸는가」뿐**이고 **「refresh가 재발급됐는가」는 여전히 미확인**이다.
  - ⚠️ **한계**: `refresh_token` **값 자체의 변경 여부는 미비교**다(만료 시각·길이 불변만 확인) ⇒ 위 *"잔여 1개월 미만일 때만 재발급"*의 **문서 인용·미실측 꼬리표와 판정 방법은 그대로 유효**하다. 갱신 **HTTP 왕복(kauth 요청·응답)은 기본 로그 레벨에서 미출력**이라 **직접 관측하지 못했고**, 갱신 사실은 **DB 상태 변화(S1 → S2)로만** 실측했다.
  - ⚠️ **1회차는 §9 정지였다 (근거유형 = 실측)**: 5000 포트에 **전날 2026-09-14 13:45 KST에 학부생이 로그인 셸에서 띄운 실모델 서버(PID 63755)** 가 약 **27시간** 잔존해 있어, *우리가 띄우지 않은 프로세스* 위에서는 3축 판정이 불가능했다. 학부생이 **17:02 KST에 Ctrl+C로 종료**한 뒤 2회차를 재개했다. 종료 직전 그 서버 로그에는 대시보드 폴링과 함께 「만료 **4162분** 경과」 WARNING이 반복되고 있었다(8.5(d) 연동).
- ⚠️ 조건: 만료 전 서버가 최소 1회 발송해야 갱신이 돈다. 장기 미가동 시 본 절차 재실행.
- 토큰·시크릿 실값은 본 문서에 미기록.

**(f) ★ 데스크톱 vs 모바일 렌더 차이 — 카피 조정 불요 판정 (근거유형 = 실측 화면 catch)**
- 데스크톱 카카오톡에서 확정 카피 ②의 어절이 줄 끝에서 분절되는 현상 관측(예: "천/으로", "음/성통화").
- 5060 노안 사용자 가독성 우려로 줄바꿈 조정을 검토했으나, 휴대폰 카카오톡 실화면 확인 결과 분절 미발생 → 조치 불요로 판정.
- 원칙: 렌더 결과는 클라이언트 폭에 종속된다. 실사용 환경(모바일)을 확인하지 않고 데스크톱 화면만 보고 카피를 손대면 7.1 검증본을 훼손하게 된다.
- 🆕 **[등재 — 관찰 2026-09-15 PoC-(49)] 1차 텍스트 알림 2행 「모바일에서 확인해 주세요.」의 출처**
  - **[실측]** 저장소 코드에 해당 문구 **0건**이다 — `server/` · `dashboard/src/` 전수 grep. **대조군**으로 같은 grep에서 「초인종이 울렸」 **2건**이 생존했다(도구 사망 아님).
  - **[실측]** `_post_memo`가 보내는 payload 실물 키 = `{object_type: "text", text, link: {web_url, mobile_web_url}}` — **`button_title` 키는 없다.**
  - **[가능성 — 미실증]** 2행과 앱 버튼 「Ddingdong」은 **카카오 클라이언트가 `link`로부터 만들어 내는 기본 렌더**일 가능성이 있다. **확정하지 말 것.**
  - ⚠️ **대외 카피 판단은 본 항에서 하지 않는다** — 문구를 바꿀지 그대로 둘지는 **본 등재의 범위 밖**이다.
  - 🆕 **[실측 — PC 카카오톡 화면 catch 2026-09-16 PoC-(50)]** 「모바일에서 확인해 주세요.」가 **2차 사진 카드와 자막 text에도** 붙었다. 본 항은 그동안 **1차 텍스트에서만** 관측 기록이 있었다.
  - ⚠️ **모바일 화면에서 2차 부착 여부는 미확인**이다. 위 **[가능성 — 미실증]**(카카오 클라이언트가 `link`로부터 만드는 기본 렌더) 서술과 **모순되지 않으며**, 이번 관측으로도 **확정하지 않는다** — 2차 발송 payload에도 `link`가 실린다면 같은 설명이 그대로 적용되기 때문이다(**미검증**).

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
- PR #40에서 `server/app/tests/test_detect_regression.py`로 자산화(stdlib unittest, ~~30 케이스~~ → ~~**60 케이스**(PR #43 +12 / PR #44 +18 누적, 2026-09-05 실측)~~ → ~~**99 케이스**(PR #45 +23 / PR #46 +6 / PR #49 +10 누적, 2026-09-09 실측)~~ → ~~**102 케이스**(PR #45 +23 / PR #46 +6 / PR #49 +10 / **PR #50 +3** 누적, 2026-09-09 PoC-(44) 실측 = `venv/bin/python3 -m unittest app.tests.test_detect_regression` → `Ran 102 tests` OK)~~ → ~~**104 케이스**(PR #45 +23 / PR #46 +6 / PR #49 +10 / PR #50 +3 / **PR #58 +2** 누적 — **[현재값 갱신 2026-09-15 PoC-(49), 근거유형 = 실측, 계수 단위 = 테스트 메서드 수]** 학부생 로컬 `venv/bin/python3 -m unittest app.tests.test_detect_regression` → `Ran 104 tests` OK(측정 시점 워킹트리 = PR #61 머지 이전 `main`). 같은 날 PR #61 세션이 **3회 반복해 동일** 결과를 재확인했다. PR #58 +2의 상세 = **33.8** — 본 항목은 **누적 현재값** 서술이라 갱신 대상이다. 각 절의 "기존 N → M" 서술(6.4(d) 30→42 / 7.6(g) 42→60 / 7.7(a) 60→83 / 카테고리 3 G12 83→89 / 8.5(g) 89→99 / 8.6(c) 99→102)은 **그 PR 시점의 이력**이므로 정정 대상이 아니다))~~ → **106 케이스**(PR #45 +23 / PR #46 +6 / PR #49 +10 / PR #50 +3 / PR #58 +2 / **PR #62 +2** 누적 — **[현재값 갱신 2026-09-16 PoC-(50), 근거유형 = 실측 + 문서 인용, 계수 단위 = 테스트 메서드 수]** `venv/bin/python3 -m unittest app.tests.test_detect_regression` → **`Ran 106 tests` OK**. 근거 = PR #62 본문의 「테스트 수 104 → **106**」 · 「복원 후 스위트 OK」 + **실물 정적 대조**(모듈의 `def test_` **107건** 중 1건은 가드 자기검증용 **중첩 `_Probe.test_probe`**라 수집 대상이 아니므로 **106**). 측정 시점 워킹트리 = **PR 브랜치 `eb06be3`**이며, 그 테스트 파일은 머지 후 `main` `bc0df74`와 **동일**하다(`git diff --quiet` 통과). **PR #62 +2 = `NetworkGuardSelfTest` 2건**(① 연결 시도 차단·기록 확인 / ② 예외를 삼켜도 테스트가 FAIL로 끝나는지 확인)이며 상세 = **30.9 부분 해소 블록**. **[실측 보강 2026-09-16 15:10 — 사후 로그]** 같은 브랜치 `eb06be3`를 **외부 가드 없이** 돌린 합격 시험도 **`Ran 106 tests in 0.242s` OK**였고 **콘솔 무변동**이었다(상세 = 같은 블록). ⚠️ 위 「각 절의 "기존 N → M" 서술은 그 PR 시점의 이력이므로 정정 대상이 아니다」는 **본 갱신에도 그대로 적용**된다). 실행 = `server/`에서 ~~`python3 -m unittest app.tests.test_detect_regression`~~ → **`venv/bin/python3 -m unittest app.tests.test_detect_regression`**(2026-09-05 정정 — 시스템 python3에는 flask가 없어 import 단계에서 실패한다). ⚠️ negative control 실행 시에는 여기에 `-B`를 더한다(카테고리 20 「negative control은 `python3 -B`로 실행」).

**관련**: 카테고리 6.2(G14/wire 계약/curl 회귀) / 7.1(확정 카피 ①②) / 7.4(터널 이미지 호스팅) / 카테고리 20(계측→실측→판정 원칙) / 카테고리 30.2(카카오 앱 셋업)

### 7.6 A-2 카카오톡 2차 알림 배선 — 사진 feed + 자막 text 2건 분할 발송 (2026-09-05 PoC-(41) 신설, PR #44 `a431961`)

카테고리 7 "2차 알림 = best-effort + 1회 재시도"와 7.5(g) feed 2줄 판정을 근거로 A-2 **발송 배선**을 실코드화했다. ~~⚠️ **A-2 발송 배선 CLOSE ≠ A-2 완료** — 자막이 아직 **mock 문구**(`server/app/utils.py` `_MOCK_TRANSCRIPTS`)이고 실 STT 소스 배선은 **0줄**이다(카테고리 7 STT 항목 참조). 발송 경로와 자막 소스는 분리해 읽어야 한다.~~ **✅ 미완 사유 해소 (2026-09-08 PoC-(42), PR #45 `9b3e3a2`, 근거유형 = 실측)**: 자막 소스가 **실 CSR로 전환**돼 위 "mock 문구 / 실 STT 소스 0줄"이라는 **미완 사유가 해소**됐다(상세 = 신설 절 **7.7**). ⚠️ 단 **미완 사유 해소 ≠ A-2 전 구간 검증** — ESP32 캡처·업로드는 여전히 미연동이고 (i) 2차 자막 실패의 영구 포기 정책도 **미결 유지**다.

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
정상 p95 ≈1초(15초 예산의 6.5%), 최악 ≈7.5초(50%) — 펌웨어 `HTTP_TIMEOUT_MS=10000` 안. 비동기 발송 아키텍처 불요(6.2의 1차 판정과 동형). ⚠️ **[역방향 stale, PoC-(45) 단서]** 이 "10000 안" 판정은 **STT 이전 수치**다 — 7.7(STT 배선)이 최악 경로에 3.0초를 더 얹으면서 상한 관계가 뒤집혔다. 최신 판정 = 7.7(l).

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
- 🔴 **[재판단 입력 — 2026-09-18 PoC-(53), 근거유형 = 실측] 트리거가 발생했다. 🔴 그러나 정책은 확정하지 않는다 — 미결 유지다.**
  - **실측(6.7(d)#4 · 6.7(e)#4)**: 같은 이벤트에서 **보드는 `-11`(`HTTPC_ERROR_READ_TIMEOUT`) / 15,474ms**로 끊겼고 **서버는 `/enrich` 200으로 종결**했다. 서버 상태는 **`enrich_status="failed"` · `skip_reason="kakao_api_error"`**이고 카카오톡 도착은 **0건**이다.
  - ★ **본 (i)가 기다리던 「네트워크 타임아웃 미재현」이 재현됐다** — 실패 원인이 **`URLError`(네트워크 도달 실패, 아이폰 핫스팟)**이므로 **일시적 실패**로 읽히는 첫 실측 사례다. ⇒ 「영구 포기」 정책이 **일시 실패에도 그대로 작동한다**는 것이 화면으로 확인됐다.
  - 🔴 **그럼에도 닫지 않는다**: n=1이고, **재시도 가능 여부를 가르는 신호가 서버에 남아 있는지**(현재 `skip_reason`은 `kakao_api_error` 한 값으로 뭉갠다)와 **2차 요청을 보드가 재전송해도 409에 막힌다는 사실**(6.5(b) 재처리 가드)을 함께 놓고 판단해야 한다. **대안 설계·재시도 정책을 여기서 신설하지 않는다.**
  - ⚠️ **보드 -11과 서버 200의 불일치는 별개 축**이다 — 보드 타임아웃 값(잠정 15,000ms) 재판정은 **7.7(l)** 소관이고 본 (i)는 **서버측 자막 실패 정책**만 다룬다.
  - 🆕 **[재판단 입력 — 2026-09-17 PoC-(51), 근거유형 = 논증, 입력 실측 = 6.5]** 보드 타임아웃 결정이 **본 미결의 선행 조건**이다. 현 `UPLINK_HTTP_TIMEOUT_MS = 10000`이 2차 최악 12.1초(7.7(l))보다 작은 동안에는 **「서버는 성공했는데 보드는 타임아웃」** 상태가 실재할 수 있고, 그 건은 `completed`/`failed`로 종결돼 **재시도해도 409**다 — 이것이 본 (i)가 말한 모호성 **바로 그 케이스**다. ⇒ 순서를 바꾸면 「일시적 실패」의 정의 자체가 흔들린다. ⚠️ **정책·값 확정 0** — 본 미결은 **유지**한다. 상세 = **6.5**.

**관련**: 카테고리 7(2차 알림 재시도 정책 / 이미지 public 호스팅 / STT) / 7.3(이미지 memo 왕복) / 7.4(터널) / 7.5(A-1 · feed 2줄 판정) / 6.4(ToF 메타 wire) / 8.3(뱃지 과소 표기 미결) / 카테고리 30.9(CSR 왕복·과금) **+ 2026-09-08 추가**: 7.7(실 STT 소스 배선 — 위 서문 미완 사유 해소) / 8.4(뱃지 과소 표기 · ToF 상세 표시 해소)


### 7.7 실 STT 소스 배선 — Naver CSR 클라이언트 신설 + `/enrich` 자막 소스 전환 (2026-09-08 PoC-(42) 신설, PR #45 `9b3e3a2`)

카테고리 7 STT 항목의 "왕복 실증 ≠ 서버 배선"과 7.6 서문의 "자막이 mock 문구"를 **동시에** 닫았다. 30.9의 CSR 왕복 실측(2026-09-05, 코드 밖 단발 호출)을 `server/`의 상시 경로로 옮긴 작업이다. ⚠️ **STT 배선 CLOSE ≠ 2차 15초 체인 검증** — 아래 (g)의 1.755초는 **서버측 구간**이며 ESP32 캡처·업로드·2차 페이로드 전송이 **미포함**이다.

**(a) 산출물 (근거유형 = 실측, `git show 9b3e3a2 --stat` 대조)**
- 신설 `server/app/stt.py`(**191줄**) = 예외 **2계층**(`SttAuthError` = 자격증명 계층(미설정·401·403) / `SttRequestError` = 그 외 API·네트워크·파싱) + 순수 함수 **3개**(`wav_from_pcm16` / `build_request` / `parse_transcript`) + `is_real_mode()` + **단일 진입점 `transcribe()`**.
- `constants.py` STT 상수 **5종**(`STT_CSR_URL` / `STT_CSR_LANG` / `STT_CLIENT_ID_HEADER` / `STT_CLIENT_SECRET_HEADER` / `STT_HTTP_TIMEOUT_SECONDS`).
- `config.py` = NCP 자격증명 노출 / `routes.py` = `/enrich` 자막 소스 전환.
- 회귀 케이스 기존 60 → **83**(신규 23).

**(b) 🔴 핵심 설계 — STT 실패는 `enrich_status="failed"`가 아니다 (근거유형 = 논증, 입력 = 7.6(d)(e))**
- 7.6(d)의 `"failed"`는 **자막 발송 실패**를 뜻하고, 7.6(e)는 이미 **"자막 없음 ≠ 실패"**를 규정했다.
- ∴ STT 실패 5종(타임아웃 / API 오류 / 인증 실패 / 빈 텍스트 / 계약 위반 응답)은 **전부 "자막 부재" 경로로 합류**한다 → **사진은 정상 발송**되고 `enrich_status="completed"`.
- 이 불변식을 깨면 PR #44가 세운 **4조합 상태 표현이 무너진다**(사진 성공·실패 × 자막 유무의 구분이 사라진다).

**(c) WAV 컨테이너 합성 (근거유형 = 논증, 입력 실측 = 30.9)**
raw PCM 직송이 아니라 **44바이트 RIFF 헤더**를 붙여 보낸다. 근거 = 30.9 CSR 왕복 실측이 **WAV로만** 수행됐고(16kHz mono 16bit PCM WAV 131,756 B → 왕복 0.892초), **raw 직송은 이 repo에서 한 번도 검증된 적 없는 경로**다. 검증된 경로를 고른다.

**(d) 재시도 없음 (근거유형 = 논증, 입력 실측 = 30.9 `usage=15`)**
- ① CSR은 **15초 단위 과금**(실측 `usage=15`) + 소프트 한도라, 재시도는 인식률이 아니라 **과금과 한도만 배가**시킨다.
- ② 카테고리 7 "1차 = 재시도 없음" 규약과 **동형**(7.6(c)의 "실패한 건만 개별 1회"는 **발송 계층** 규약이지 STT 계층이 아니다).
- ★ **백오프 상수를 신설하지 않았다** — 실측 근거 0인 상수는 죽은 상수다(6.4(c) `tof_center_mm` 상한 미설정과 동형).

**(e) env 게이트 (근거유형 = 실측)**
`NCP_CLIENT_ID` / `NCP_CLIENT_SECRET`이 **둘 다** 설정돼야 real. `model_serving.is_real_mode()` **동형**. 미설정이면 **호출 자체를 하지 않고** mock 자막을 유지한다 — 한쪽만 설정된 상태를 real로 보면 반드시 401을 받아 **과금 없는 실패 왕복만** 태우기 때문이다.

**(f) `STT_HTTP_TIMEOUT_SECONDS = 3.0` (근거유형 = 논증·산술, 입력 실측 = 30.9 왕복 0.892초)**
왕복 실측 0.892초 대비 약 3.4배 여유로 역산했다. ⚠️ **전제 = 서버측 구간 기준이며 ESP32 캡처·업로드는 미포함**이다 — 2차 15초 예산 전체를 이 상수 하나로 나눈 값이 아니다.

**(g) ④런타임 실측 (터널 + 실호출 + 카카오톡 화면, 실측·문서 반영 2026-09-08, 근거유형 = 실측)**
- 입력 = 16kHz mono WAV **131,756 B**에서 헤더 44 B를 뺀 **raw PCM 131,712 B**(macOS `say` TTS 생성).
- 응답 `transcript` = **"계세요 택배 왔습니다 문 앞에 두고 갈게요"** — **첫 어절 "계세요" 포함**((h) 연동).
- `stt.language="ko-KR"` / `stt.confidence=null`(**CSR 미제공** — 8.4(d) 연동).
- 2차 체인 전체 **1.755초**(15초 예산의 **11.7%**, **서버측 구간**).
- `enrich_status="completed"` + `secondary_sent=true` + `tof_check.applied/passed=true`.
- **카카오톡 3건 도착** — 1차 텍스트 → 사진 카드(정상 렌더) → **자막 text**. 자막 문구가 JSON `transcript`와 **완전 일치**. feed description `9월 8일 11:04 감지` **절단 없음**.
- ★ **자막이 2줄로 렌더됐으나 잘리지 않았다** — 7.5(g)의 **2줄 상한은 feed description에 걸리는 것**이고 **text 템플릿은 별개**다. A-2를 **2건 분할**로 설계한 7.6(b) 판단이 화면으로 정당화됐다.

**(h) ⚠️ 9/05 "첫 어절 계세요? 누락"이 재현되지 않았다 (근거유형 = 실측 2건 — 단정 금지)**
같은 macOS `say` 생성기·같은 CSR 경로인데 9/05에는 **누락**, 9/08에는 **포함**이었다. **TTS 어택 문제가 아니었던 쪽으로 기운다**는 정도까지만 말할 수 있다. ⚠️ **실측 2건이므로 원인은 여전히 미규명**이며 30.9의 "미규명" 서술은 **그대로 유효**하다. 실 육성 정확도는 별건이다.
- 🆕 **[관측 추가 2026-09-16 PoC-(50)]** 본 (h)의 서술은 **무변경**이며 아래는 관측 누적이다.
  - **[실측]** 2차 체인 리허설의 TTS 입력(macOS `say`, 음성 **Yuna**, PCM **100,392 B ≈ 3.1초**)에서 `/enrich` 자막이 **「택배 왔습니다 문 앞에 두고 갈게요」**로 나와 첫 어절 **「계세요」가 다시 누락**됐다(상세 = 7.4).
  - **[실측]** 같은 날 **실 육성**((m)) 중 「계세요」로 시작하는 **2건은 모두 첫 어절을 유지**했다. (m) 7번의 첫 어절 X는 **누락이 아니라 오인식**(`엄마 나야` → `본받아야`)이다.
  - **누적** (계수 단위 = 발화 건수) = **TTS 누락 2건**(09-05 · 09-16) / **TTS 포함 1건**(09-08) / **육성 포함 2건**(09-16).
  - ⚠️ 🔴 **원인 단정 금지** — n이 작고 **음성·길이 조건이 서로 다르다**(09-08은 131,712 B 약 4.1초이며 음성명 미기록, 09-16은 Yuna 약 3.1초). 30.9의 「미규명」 서술과 **모순 없다**.

**(i) 🔴 실패 폴백도 같은 세션에서 실증됐다 (근거유형 = 실측)**
동일 세션의 앞선 시도에서 CSR이 **HTTP 429**(한도 초과)를 반환했고, 서버는 `enrich_status="completed"` + `secondary_sent=true`로 **사진을 정상 발송**하고 `stt: null`만 남겼다 → **(b)의 "실패해도 사진은 간다" 불변식이 실물로 증명**됐다.
- 로그 = `WARNING in routes: enrich stt: mode=real result=failed elapsed_ms=94.68 cause=CSR 호출 실패: HTTP 429`
- ★ **`mode=real`이라는 한 단어가 진단 방향을 결정했다** — "안 불렀다"(mock)와 "불렀는데 실패"(real)를 가르는 로그 불변식이 실물에서 값을 했다. **관측 설계가 사후에 값을 하는 전형**이다(카테고리 20 연동).
- ⚠️ 이 429가 속한 **CSR 호출 301건의 출처는 미규명**이다 — 30.9 신규 미결 참조.

**(j) 경계 표기 (미검증을 확정으로 읽지 말 것)**
- **STT 배선 CLOSE ≠ 2차 15초 체인 검증**: 1.755초는 **서버측 구간**. ESP32 캡처·업로드·2차 페이로드 전송 **미포함**.
- **STT 배선 CLOSE ≠ 실 육성 인식률 검증**: 입력이 전부 **TTS 합성음**이다.
  - 🆕 **[경계 갱신 2026-09-18 PoC-(53), 근거유형 = 실측, 계수 단위 = 발화 건수, n=1]** **실 육성이 보드 마이크를 거쳐 CSR까지 처음 관통했다** — 학부생 육성이 보드 INMP441 → 5.120초 녹음 → `/enrich` → CSR을 통과해 「계세요 택배입니다 문 앞에 놓고 갈게요」가 **원문과 완전 일치(오류 0자)**로 돌아왔다(실측 본문 = **6.7(g)**).
  - 🔴 **그럼에도 「실 육성 인식률 미검증」 경계는 닫히지 않는다**: **n=1**이고 **거리 미측정**이며 **실내 조용 · 화자 1**이라 소음·거리·화자 변동이 **전부 미관측**이다. 1건의 완전 일치는 **관통 증명**이지 **인식률 측정이 아니다**.
  - 🔴 **(m)의 CER 6.77%와 병치 금지**: (m)은 **이어폰 근접 재생 10문장**이고 본 건은 **보드 마이크 실 육성 1문장**이다 — 입력 경로·건수·거리 조건이 전부 달라 **같은 축의 수치가 아니다**. 두 값을 한 표·한 문장에 나란히 두지 말 것.
- **STT 배선 CLOSE ≠ A-2 완료**: 7.6(i)(2차 자막 실패의 영구 포기 정책)는 **미결 유지**.

**(k) 역방향 stale docstring 정정 + ⚠️ 「폴백」 표현 부정확 (2026-09-09 PoC-(43), PR #48 `0d3b498`)**
- `kakao.send_secondary` docstring이 **"현 시점 자막 소스는 mock 이다 — 실 STT(G23)는 미구현"**이라고 적혀 있었다. 본 절(PR #45)로 배선이 끝난 뒤에도 남아 있던 **역방향 stale**이다 — 코드가 문서를 앞지른 게 아니라 **주석이 코드를 못 따라갔다**. 남은 defer(④런타임 미실증 = 실 육성 인식률·2차 15초 체인)는 **삭제하지 않고 명시적으로 유지**했다. 로직·시그니처·상수 무변경(diff 전건 docstring 내부).
- 🟡 **[신규 미결] 정정 문구의 「폴백한다」가 부정확하다 (발견·문서 반영 2026-09-09 PoC-(43), 근거유형 = 실측)**: 새 docstring은 "자격증명 미설정 시 mock 으로 **폴백한다**"라고 적혔으나, 실제 동작은 **호출을 시도했다가 실패해 되돌아가는 것이 아니라 (f) env 게이트에서 애초에 real 모드가 아니라 mock 경로가 유지되는 것**이다(`routes._caption_from_stt` 주석 = "자격증명 미설정이면 여전히 mock_enrichment 의 dict 가 들어온다"). **「안 불렀다」와 「불렀는데 실패했다」를 가르는 것이 (i)의 `mode=real` 로그 불변식**인데 "폴백"은 그 구분을 흐린다. ~~해소 = 다음 코드 PR에서 문구 교체(**본 세션은 코드 무접촉이라 기록만**).~~ → **✅ 해소 (2026-09-15 PoC-(49), PR #61 `b56da39` 내부 커밋 `8709ba8`, 근거유형 = 실측 `git show`)**: `server/app/kakao.py` `send_secondary` docstring의 「자격증명 미설정 시 mock 으로 폴백한다」가 **「자격증명 미설정이면 `stt.is_real_mode()` 게이트에서 애초에 real 모드가 아니므로 CSR 호출 자체를 하지 않고 mock 자막 경로가 유지된다(호출을 시도했다가 실패해 되돌아가는 폴백이 아니다)」**로 교체됐다. **로직 0줄 변경** — `ast.dump` 해시가 수정 전후 동일하며, **대조군 NC**로 같은 세션이 *코드 토큰 1개를 바꾸면 해시가 갈리고 docstring만 바꾸면 갈리지 않음*을 실측했다. ⚠️ **본 건이 닫은 것은 문구뿐**이다 — (i)의 `mode=real` 로그 불변식과 (j)의 경계 표기는 **무변경**이다.

**(l) 🔴 [신규 미결] 2차 최악 총합 12.1초 > 펌웨어 `HTTP_TIMEOUT_MS=10000` (발견 2026-09-08, 문서 반영 PoC-(45), 근거유형 = PR 본문 서술 · 미실측)**
- 출처 = PR #45 본문 "신규 미결 2건" ②(decisions.md엔 그동안 미등재 — `12.1` grep 0건). 카카오 최악 7.5초((f)) + 서버 자체 1.6초 + STT 3.0초 = **12.1초**가 `main.cpp`의 `HTTP_TIMEOUT_MS=10000`(10초)을 넘는다. 지배항 = **카카오 최악 7.5초** — STT 3.0초를 2.0초로 줄여도 11.1초로 여전히 초과한다.
- 2차 전체 예산 15초 **안에는 든다**(81%) — ESP32가 서버보다 먼저 타임아웃으로 끊는다는 뜻이며 예산 자체가 깨진 것은 아니다.
- ⚠️ **해결책·타임아웃 값 신설 금지** — 판정은 2차 클라이언트(M5-d 이후 ESP32 `/enrich` 호출부) 작성 시점으로 넘긴다. **12.1초 구성 성분별 실측 근거는 SSoT에서 추적 불가**(PR 본문 서술 1건뿐)이므로 재판정 시 각 성분을 다시 실측할 것.
- 🔴 **[재판정 입력 — 2026-09-18 PoC-(53), 근거유형 = 논증, 입력 실측 = 아래] 12.1초는 과소평가다. 🔴 그러나 새 값을 확정하지 않는다 — 미결 유지다.**
  - **입력 ① 카카오 실측(서버 로그 `pr64_server.log` 시각차, 2026-09-18 이벤트 #4)**: 상수 `KAKAO_HTTP_TIMEOUT_SECONDS = 1.5`인데 **로그로 양끝이 잡히는 구간 3건**이 사진 재시도 **4.180초**(15:00:02.610 → 15:00:06.790) · 자막 1차 **1.519초**(→ 15:00:08.309) · 자막 재시도 **1.517초**(→ 15:00:09.826)다. **3건 합 7.216초 ↔ 산술 4.5초 ⇒ 배율 ≈ 1.60.** 사진 1차는 **직전 로그 줄이 없어 하한이 잡히지 않고**, STT `processed_at` 14:59:59.770을 시작 상한으로 잡으면 **≤ 2.840초**다(위임 본문의 4구간 근사 = 합 ≈9.2초 · 배율 ≈1.53은 이 범위 안이다).
  - **입력 ② CSR 실측**: `TimeoutError`가 났는데 `elapsed_ms = 6,423.73`이다(상수 `STT_HTTP_TIMEOUT_SECONDS = 3.0`).
  - 🔴 **입력 ③ 코드 확인 (근거유형 = 실측 코드 대조, `d093d70` 읽기만)** — `server/app/stt.py`는 `urllib.request.urlopen(req, timeout=STT_HTTP_TIMEOUT_SECONDS)`로 **상수를 정상 전달한다**(`kakao.py` 3개 호출부도 동일). ⇒ **「상수 미작동」이 아니다.** `urlopen`의 `timeout`은 **소켓 연산 단위 상한**이고 **총 경과 상한이 아니다** — connect · TLS 왕복 · 131 KB 전송 · read가 **각각** 상수만큼을 받는다. ★ **7.7(l) 위 본문이 `HTTPClient::setTimeout`을 「마지막 수신 이후 무응답 한계」로 정정한 것과 같은 축이 파이썬 쪽에도 있었다.**
  - **파급(논증)**: 12.1초의 카카오 성분 **7.5초**(5회 × 1.5)에 배율을 적용하면 **≈ 11.5초**(1.53) ~ **≈ 12.0초**(1.60)이고, 여기에 서버 자체 **1.6초** + STT **실측 6.4초**를 더하면 **≈ 19.5 ~ 20.0초**다. ⇒ **어느 배율을 쓰든 2차 15초 예산(7.7(g))과 잠정 상수 `UPLINK_ENRICH_HTTP_TIMEOUT_MS = 15000`(6.7(c))을 모두 넘을 수 있다.** 실기기에서 이미 **보드 -11 / 15,474ms**가 났다(6.7(d)#4).
  - ⚠️ **경계**: 배율은 **1세션 4시도**에서 나온 값이고 측정된 실패는 **타임아웃이 아니라 `URLError`(네트워크 도달 실패)**다 — 정상 왕복(7.3 p95 490ms)과는 **다른 모집단**이다. 🔴 **배율도 새 타임아웃 값도 확정하지 말 것.** 성분별 재실측 계획 = **6.5(e) M-2 · M-3**.
- 🆕 **[재판정 시점 도래 + 성분 3/4 재추적 — 2026-09-17 PoC-(51), 근거유형 = 항목별 병기]** 2차 클라이언트 설계 조사에서 다음이 확인됐다(상세 = **6.5**).
  - **[실측 코드 대조] 관계되는 상수는 `main.cpp`가 아니다.** 같은 이름 `HTTP_TIMEOUT_MS`가 **3벌**(`main.cpp` = `env:poc` / `upload_spike_common.h` / `upload_spike_tls_common.h`), 같은 값 10000이 **4벌**이며, 2차 클라이언트가 실제로 상속할 값은 **`uplink_common.h`의 `UPLINK_HTTP_TIMEOUT_MS = 10000`**이다. ⇒ 본 (l) 본문의 「`main.cpp`의 `HTTP_TIMEOUT_MS`」는 **값은 맞고 주소가 좁다**(취소선 대상 아님 — 그 파일에도 같은 값이 실존한다).
  - **[산술 · 논증] 성분 3개는 코드에서 재추적된다** — 카카오 최악 **7.5초**(7.6(f) 5회 × `KAKAO_HTTP_TIMEOUT_SECONDS` 1.5) · 서버 자체 **1.6초**(`constants.py` 역산 주석) · STT **3.0초**(`STT_HTTP_TIMEOUT_SECONDS` 상수값). **4번째(ESP32 캡처·업로드 구간)는 존재하지 않는다** — `constants.py`가 스스로 「위 역산의 입력 2,610ms에는 ESP32 캡처·업로드 구간이 미포함」이라 적는다.
  - **[실측 설치 라이브러리 대조] `HTTPClient::setTimeout`은 「마지막 수신 이후 무응답 한계」**(`_tcpTimeout`)이지 총 경과 상한이 아니다. 인자는 `uint16_t`(상한 65,535ms)이고 내부에서 `_client->setTimeout((t+500)/1000)`으로 **초 단위 절삭**된다. ⚠️ 다만 2차는 서버가 **응답 헤더 첫 바이트 전에 카카오·STT를 전부 돌리므로** 무응답 구간이 곧 총 처리시간이다 ⇒ **사실상 총 경과 상한으로 동작**한다(근거유형 = 논증, 입력 = 위 실측).
  - 🔴 **값·방식 확정 0** — 본 미결은 **유지**한다. 해소 선택지와 재실측 계획(M-1~M-6)은 **6.5**에 있고, **권고는 재실측 선행**이다.
- 🆕 **[재판정 트리거 충족 — 발견일 = 반영일 2026-09-20 PoC-(54), 근거유형 = 실측 코드 대조] 「2차 클라이언트 작성 시점」은 이미 왔다.** 🔴 **취소선 없음 · 미결 유지 · 타임아웃 값과 해결책을 신설하지 않는다**(PR-C 소관).
  - **[실측] `/enrich` 호출부가 실재한다** — `firmware/src/uplink_common.cpp`의 2차 체인(형제 함수 additive, 2026-09-18 PR-B / 6.5(d))이 `String("http://") + host + ":" + String(port) + "/api/v1/enrich"`를 구성한다. 같은 파일에서 `WiFi.RSSI()`도 읽는다.
  - **[실측] `env:enrich_uplink`가 `platformio.ini`에 편입돼 있다**(PR #64, 6.7). ⇒ 본 (l)이 *「판정은 2차 클라이언트(M5-d 이후 ESP32 `/enrich` 호출부) 작성 시점으로 넘긴다」*로 지정한 **트리거 조건이 충족**됐다.
  - ⚠️ **본 항이 신규로 등재하는 것은 「트리거 충족」뿐이다** — 상수 주소 정정(「`main.cpp`의 `HTTP_TIMEOUT_MS`」는 **값은 맞고 주소가 좁다**, 실상속값 = `uplink_common.h`의 `UPLINK_HTTP_TIMEOUT_MS`)은 **위 2026-09-17 PoC-(51) 단서가 이미 등재**한 것이라 **신규가 아니다**. 두 축을 섞어 읽지 말 것.
  - 🔴 **미결 유지 근거**: 트리거가 충족된 것과 **재판정이 수행된 것은 다른 축**이다. 본 항은 성분 재실측(**6.5 M-1~M-6**)을 **수행하지 않았고**, 값 · 배율 · 방식 **확정 0건**이다.

**(m) CSR 소규모 인식률 실측 — 실 육성 10건 (실측·문서 반영 2026-09-16 PoC-(50), 근거유형 = 실측, 계수 단위 = 발화 건수 / 글자 수)**
- **방법**: 제품 코드 `app.stt.transcribe()`를 **직접 호출**했다 — 파일당 **1회**, **재시도 0**, **서버·카카오 미경유**, 총 **10건**.
- **조건**: 유선 이어폰 마이크(`avfoundation :2`) **입 근접** / **조용한 실내** / 화자 **1명**(학부생) / **16kHz mono PCM16 약 6.2초**(7초 녹음, 시작 지연으로 실측 6.15~6.27초) / 신호비 **27~80배** / **대본 낭독**.
- **CER 정의**: 영숫자·한글만 남긴 문자열(**공백·문장부호 제거**)의 **글자 레벤슈타인 거리 ÷ 원문 글자 수**.
- **결과**: 원 집계 **12 / 130 = 9.23%** → **학부생 청취 정정**(4번 녹음 끝 「하하하」는 **실제 웃음 = 대본 이탈**이지 CSR 오류가 아님, 재생으로 확인) → **확정 9 / 133 = 6.77%**. **완전 일치 7/10**, **RTT 0.75~1.11초**.
  - 오류 내역 = **1번 4자**(`문 앞에` → `아프다 표`) / **7번 3자**(`엄마 나야` → `본받아야`) / **9번 2자**(`맡겨` → `받기`).
- 🔴 **⚠️ 카테고리 7 머리의 6.49%와 병치 금지**: 그 값은 **CLOVA Speech · 저음질 전화망 · 테스트셋당 3,000문장**이고 **본 값은 최선 조건 소규모**다 — 엔진 · 데이터 · 규모가 전부 다르다. **두 숫자를 나란히 적는 순간 압축 손실이 재발한다**(27.8(l)⑥).
- **미측정**: 현관 **1m 거리** / 보드 **INMP441** 마이크 / **인터폰 잡음** / **다른 화자** / **자연 발화**. ⇒ 본 실측이 좁힌 것은 **(j)의 「실 육성 인식률 미검증」 중 근접 조건 소규모 구간뿐**이다.
- 🔗 **첫 어절 관측** = (h) / **CER 근거 정정** = 카테고리 7 머리 / **호출 10건의 과금** = 30.9(⚠️ 콘솔 대조는 **미실시**).

**관련**: 카테고리 7(STT 제품 CSR 확정 · 2차 알림 재시도) / 7.6(A-2 배선 · 상태 표현 · 자막 부재 정책) / 7.5(g)(feed 2줄 판정) / 7.4(터널) / 30.9(CSR 왕복 · 15초 과금 · 호출 한도 · 301건 미결) / 8.4(신뢰도 null 표시) / 카테고리 3(G12 확정) / 카테고리 20(관측 설계 · negative control)

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
  - 🟡 **[실증 갱신] 서버 로그로 3배 호출이 실측됐다 (발견·문서 반영 2026-09-09 PoC-(44), 근거유형 = 실측)**: 위 "3중"은 **프론트 코드 리뷰**로 센 값이었는데, 서버 로그에서 **같은 초에 `/stats`가 3회** 찍히는 것이 관측됐다(`19:00:58` 3회 / `19:01:01` 3회 — 3초 주기와 정합). ★ **코드 리뷰 추정이 서버측 실측으로 확증된 것**이며 통합 대상 건수는 **무변경**이다(3중 그대로).
  - ⚠️ **파급 — 로컬에서는 안 아프고 배포에서 아프다**: 현재는 GET이라 rate-limit 제외 + 로컬이라 무해하나, **EC2 배포 시 요청량이 그대로 3배**이고 **대시보드를 여러 대 띄우면 곱해진다**. 추가로 8.5(d)의 만료 WARNING이 **이 3배를 그대로 타고 로그를 오염**시킨다(같은 절의 신규 미결). → 폴러 통합은 **성능 항목이 아니라 11주차 배포 선행 항목**으로 읽는 것이 맞다. **판정 방법** = EC2 기동 후 `/stats` 초당 호출 수를 서버 로그로 재측정.

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
- ~~🟡 **뱃지 과소 표기**: `NotificationStatusBadge.derive()`가 (사진 실패 + 자막 성공) / (자막 없음 + 사진 실패) 조합을 "1차 발송"으로 렌더한다. 금지선인 "부분 성공 → 완전 성공" **오표기는 아니지만** 과소 표기다(7.6(d) 연동 — `derive()`가 `secondary_sent`를 `enrich_status`보다 먼저 보는 순서가 원인). 해소 = `derive()` 분기 1개 추가, K 대시보드 소액 PR 소관.~~ **✅ 해소 (2026-09-08 PoC-(42), PR #47 `846b342`)**: `enrich_status === "completed" && secondary_sent_at === null` 분기 추가로 정정. **서버 변경 0 / 새 뱃지 어휘 0.** ★★ **위 "원인 = 읽는 순서" 진단은 코드 재검증에서 뒤집혔다** — `derive()`의 읽는 순서는 **지켜야 할 결정**(7.6(d))이었고 근본원인은 **"분기가 좁다"**였다(학습 19). 순서는 **무변경**으로 두고 분기만 넓혔다. 상세 = **8.4(c)**.
- ~~🟡 **ToF 상세가 화면에 미표시**: `dashboard/src/components`·`pages`에서 `tof_check` 참조 **0건**(실측 grep). USP 2층의 1차가 ToF 융합 서사(카테고리 33 「USP 2층 재정립」 / 26.1)인데 **화면에 그 근거가 없다** — 6.4로 서버가 실 ToF 값을 내기 시작했으므로 표시 대상이 생겼다. 해소 = K 대시보드 소액 PR 소관.~~ **✅ 해소 (2026-09-08 PoC-(42), PR #47 `846b342`)**: `NotificationTof.tsx` 신설로 **ToF 3상태**(사람 확인 / 사람 없음 / 검증 안 함)를 알림 카드에 표시한다. `reason` **원문 보존** + **라벨·아이콘·색 3중 표기**(색 단독 의존 금지, 위 B-1a 규약). 6.4(c) "게이트 통과와 ToF 부재로 미적용이 **구분 가능해야 한다**"는 불변식의 **화면 판**이다. 상세 = **8.4(b)**.



### 8.4 대시보드 표시 결함 4종 정정 — ToF 상세 / 뱃지 과소 표기 / 가짜 ToF 문자열 / STT 신뢰도 null (2026-09-08 PoC-(42) 신설, PR #47 `846b342`)

8.3 신규 미결 2건(뱃지 과소 표기 / ToF 상세 미표시) + 6.4(f)(가짜 ToF 하드코딩 잔존) + 7.7(g)이 드러낸 신뢰도 null 표시 결함을 한 PR로 닫았다. **서버 응답 스키마 변경 0 / 새 뱃지 어휘 0.**

**(a) 산출물 7파일 (근거유형 = 실측, `git show 846b342 --stat` 대조)**
- 신설 `dashboard/src/components/notifications/NotificationTof.tsx` / 수정 `NotificationCard.tsx` · `NotificationStatusBadge.tsx` · `lib/format.ts` · `lib/mock-data.ts` · `types/notification.ts` · `server/seed.py`.
- 커밋 **4분리**(`✨ Feat` 1 + `🐛 Fix` 3) — 위임이 커밋 분리 판단을 느슨하게 줬으나 `docs/git-convention.md` 컨벤션을 **우선**했다(학습 16). **중간 상태 빌드 4/4 통과** 실측.

**(b) 🔴 ToF 3상태 표시 = 6.4(c) "구분 가능" 불변식의 화면 판 (근거유형 = 논증)**
- `applied=true, passed=true` → **사람 확인** / `applied=true, passed=false` → **사람 없음** / `applied=false, passed=null` → **검증 안 함**.
- ★ 미적용을 같은 자리에 **비워 두면 부재가 통과로 위장**된다 — 6.4(d) NC-3 함정("ToF 부재를 presence=true로 취급")이 화면 계층에서 재현되는 지점이다.
- `reason` **원문 보존**(가공 금지) — 9.3(b) 펌웨어 시리얼 로그 표기와 **대조 가능**해야 한다(6.4(b)).
- **라벨 + 아이콘 + 색 3중 표기** — 색 단독 의존 금지(8.3 B-1a, WCAG 1.4.1). **기존 토큰만 사용**(새 색 발명 0).

**(c) 뱃지 과소 표기 해소 — 서버 변경 0 / 새 뱃지 어휘 0 (근거유형 = 실측)**
- **결정적 실측**: 과소 표기 2조합(사진 실패 + 자막 성공 / 사진 실패 + 자막 없음)이 **`enrich_status === "completed" && secondary_sent_at === null`로 유일 식별**된다. 서버 코드 역추적 = `routes.py`의 `secondary_sent_at = utc_now() if photo_sent else None`.
- `enrich_status="skipped"`(화재경보 = 2차 미시도)는 이 조건에 **걸리지 않는다** → `"completed"`를 **명시 비교**한다.
- ★ **`derive()`의 읽는 순서는 무변경** — `secondary_sent`를 `enrich_status`보다 **먼저** 보는 **7.6(d)의 결정적 근거**를 지킨 채 **분기만 넓혔다**. 순서를 바꾸면 "부분 성공이 전송 완료로 렌더"되는 **금지 상태가 되살아난다**.
- ★★ **근본원인이 "순서가 틀렸다"가 아니라 "분기가 좁다"였다 (학습 19)**: 8.3 미결 서술은 원인을 "`derive()`가 `secondary_sent`를 먼저 보는 순서"로 적었으나, 그 순서는 **지켜야 할 결정**이었다. **등재된 미결의 진단조차 코드로 재검증해야 한다**는 사례.

**(d) STT confidence null 표시 (근거유형 = 실측, 입력 = 7.7(g) `confidence=null`)**
- `formatConfidence(value: number | null)` — `null` → **"정보 없음"**. 가드는 호출처가 아니라 **공유 함수 1곳**에 넣었다(ML confidence 경로 = `NotificationCard` / `TotalDetectionsCard`는 항상 number를 넘기므로 표시가 **바이트 단위로 동일**).
- ★ **`=== null` 엄격 비교** — `!value`로 완화하면 **실측 0.0이 "정보 없음"**이 된다. **0은 값이 없는 것이 아니다.**
- ★ **null을 숫자로 채우지 않았다** — 없는 값을 지어내 화면에 띄우는 것이 **결함의 본체**다(실측 없는 판정 금지, 카테고리 20). 실 CSR은 `{"text": ...}`만 주므로 신뢰도가 **존재하지 않는다**(30.9).
- 타입 확장 `number → number | null`의 근거 = **서버가 이미 null을 낸다는 실측**. `NotificationStt` 외 타입 정의는 미접촉.

**(e) 가짜 ToF 문자열 교체 (근거유형 = 실측 grep)**
- `server/seed.py` **4건** / `dashboard/src/lib/mock-data.ts` **4건**을 실 서버 어휘(`tof_meta.telemetry_summary` = `presence=<true|false> near=<n>/64 center=<n>mm ndet=<n>/16`)로 교체 → 9.3(b) 시리얼 로그 표기와 **동형**(6.4(b)).
- ★ **삭제가 아니라 교체** — 지우면 화면이 비고 부스에서 **"데이터 없는 시스템"**으로 보인다(카테고리 26 연동). 수치가 **픽스처지 실측값이 아님**은 주석에 명시했다.
- mock은 **3상태를 모두**(통과 3 / 거부 1 / 미적용 1) 담아 개발 중 `NotificationTof` 분기를 눈으로 확인할 수 있게 했다. 거부 건은 **G12 확정(PR #46)에 맞춰 신뢰도 부족 건에 얹었다** — 문서 확정과 mock이 어긋나지 않게 한 것.
- 사후 실측: `zone_count=` 잔존 = **코드 전역 0건**. ⚠️ `docs/` **7건**은 **역사 기록이라 의도적 무변경**.

**(f) ★ 프론트 negative control 하네스 신설 (방법론 자산, 근거유형 = 실측)**
- 방식 = **변형된 실제 소스**를 `vite build --ssr`로 재번들 → `react-dom/server` 렌더 → **텍스트 라벨 단언**. 대시보드에 **테스트 러너가 없는데도** NC를 돌린 방법이다(**신규 의존성 0**).
- 미검출 2건의 판정(NC-2b = 도달 불가)은 **카테고리 20 「negative control 미검출의 판정」**에 등재.
- ⚠️ **한계 2가지**: ~~① 하네스가 **scratchpad에만 있고 repo에 없어 CI 회귀 방지 효과 0**~~ → **⚠️ 부분 해소 (2026-09-09 PoC-(44), PR #51 `8d574dd`)**: repo 편입은 됐으나 **CI 회귀 방지 효과 0은 그대로 승계**된다(아래 미결 참조) ② **텍스트 라벨만** 검사하므로 **색·아이콘·레이아웃·대비비·터치 타깃은 미검증**((b)의 3중 표기 중 실제로 단언한 것은 **라벨뿐**이다) — **② 는 무손상 승계**.
- ~~🟡 **[신규 미결] 프론트 NC 하네스가 repo 밖 (발견·문서 반영 2026-09-08, 근거유형 = 실측)**: 자산화하려면 테스트 러너 도입이 필요하고 이는 **신규 의존성 금지**에 걸린다. **deferred 후보** — 11주차 또는 폴리시 구간 재판단.~~ **⚠️ 부분 해소 (실측·문서 반영 2026-09-09 PoC-(44), PR #51 `8d574dd`, 근거유형 = 실측)**
  - **무엇이 해소됐는가**: 하네스가 `dashboard/tools/ssr-nc/`(`entry.tsx` + `run.mjs`, +292줄)로 **repo 편입**됐고 `package.json` scripts에 `"ssr-nc": "node tools/ssr-nc/run.mjs"` **1줄**이 추가됐다. **신규 의존성 0.** NC 4종 이식(PR #49 2종 + PR #47 2종) + 자기 검증 **12행 전건 통과**.
  - 🔴 **무엇이 승계되는가 — 🟢로 닫지 말 것 (항목별 사유가 다르다)**:
    - **① CI 미연결(신규 한계)**: 사람이 `npm run ssr-nc`를 **직접 쳐야** 돈다. **repo 편입 ≠ 회귀 방지** — 위 원 미결이 노린 "CI 회귀 방지 효과 0"은 **그대로다**. 사유 = 자산화와 자동 실행은 별개 층.
    - **② 텍스트 전용 한계**: 색·아이콘·레이아웃·대비비·터치 타깃 미검증. 사유 = 단언 대상이 라벨 문자열이라 **repo 편입과 무관**하게 불변.
    - **③ SSR이라 실 브라우저 CSS 미검증**: `react-dom/server` 문자열 렌더라 CSS·레이아웃이 애초에 존재하지 않는다. 사유 = **실행 매체의 성질**이지 자산화 여부가 아니다.
  - **판정 방법(잔존 미결)** = CI 연결은 11주차 또는 폴리시 구간에 재판단한다. ①의 해소 판정 기준 = "사람이 치지 않아도 돌았고, 그 결과가 머지 게이트에 걸리는가".
  - 🔴 **★ 학습 21 — 미결을 막고 있던 「차단 사유」가 유령이었다 (발견·문서 반영 2026-09-09 PoC-(44), 근거유형 = 실측 `dashboard/package.json` 전문 대조)**
    - 위 원 미결은 *"자산화하려면 테스트 러너 도입이 필요하고 이는 신규 의존성 금지에 걸린다"*로 3주 이월됐다. 실측 결과 `react-dom` `^19.2.6`(dependencies) / `vite` `^8.0.12`(devDependencies)가 **이미 설치**돼 있었고, 하네스는 이 둘만으로 돈다. **신규 의존성 0으로 자산화가 가능했다.**
    - ★ **원인 = 「러너」의 의미 혼동**: 테스트 **프레임워크**(vitest / jest / RTL) 도입은 확실한 신규 의존성이지만, 본 하네스는 **프레임워크가 아니라 스크립트**다. 둘을 한 단어로 뭉갠 채 이월했다.
    - 🔴 **유령의 위치가 다르다 — 학습 21의 5번째 유형으로 신설한다**: 미결의 **존재**("하네스가 repo 밖")는 **실재했고 사실**이었다. 유령이었던 것은 **그것을 막고 있던 차단 사유**다. 기존 4분류(유령 / 트래킹 부재 / 트래킹 있으나 실물 부재 / 부재로 기록됐으나 실재)는 전부 **미결 자체의 실재 여부**를 가르는 축이라 이 사례를 담지 못한다. → **⑤ 미결은 실재하나 「차단 사유」가 유령인 유형**.
    - **재발 방지(학습 19의 확장)**: **"X를 하려면 Y가 필요하다" 형태의 차단 사유는 Y의 실존을 반드시 실측한다.** 학습 19가 "미결의 **근본원인 진단**을 코드로 재검증"이라면 본 건은 "미결의 **차단 사유**를 코드로 재검증"이다 — 진단이 아니라 **가로막은 이유**를 재검증하는 축이다.
    - 🟡 **[하위 단서 — 2026-09-15 PoC-(48) 추가] 부재 판정은 「감싸는 함수」 앞에서 멈출 수 있다 (근거유형 = 실측 grep 전수)**: 대화형 grep이 `DEFAULT_DATA_ROOT` · `resolve_data_root` **이름만** 훑고 「참조 0건」으로 판정했으나, 실제로는 `resolve_paths`가 한 겹 감싸고 그 위를 `ml/training/config.py`의 `resolve_final_dir`이 **또** 감쌌다. 최종 호출자 = `ml/pipeline/run_all.py` · `ml/training/train.py` · `ml/training/evaluate.py` **3곳이며 전부 인자 `None` 도달 가능**이었다. ⇒ **부재를 주장하기 전에 래퍼를 끝까지 따라간다.** ⚠️ 대조군 = 같은 grep이 테스트의 `resolve_paths(root)` 호출 **6건**을 살려냈으므로 **도구 사망은 아니었다** — 판정이 **한 겹 위에서 멈춘 것**이다. 상세 = 33.8(PR #60).
  - ★ **부분 문자열 단언을 주석이 아니라 구조로 제거 (근거유형 = 실측)**: 8.5(g)가 정직 기록한 "`"10분 전 만료" in out`이 `-10분 전 만료`를 통과시킨다"를, `segments()`로 렌더 출력을 **텍스트 노드 배열**로 쪼갠 뒤 **완전 일치 비교**해 원천 차단했다. 실증 = `.includes()` **true(❌)** ↔ `===` **false(✅)**. **무딘 단언은 경고 문구가 아니라 자료구조로 고친다.**
  - ★ **ESM 모듈 캐시 = `.pyc` 사건의 JS 판 (근거유형 = 실측, PR #51 자체검증 ①에서 발견)**: SSR 재빌드마다 같은 경로를 `import`하면 **ESM 모듈 캐시가 첫 번들을 반환**해 변형이 반영되지 않은 채 "미검출"이 나온다(**거짓 음성** — `.pyc` 사건이 경고한 "반대 방향 오염"과 정확히 같은 방향). 차단 = 캐시 버스팅 `import(`${url}?build=${++buildCount}`)`. **실행 환경 오염은 python `.pyc`에 국한되지 않는다** — 상세 = 카테고리 20 「negative control은 `python3 -B`로 실행」.
  - 🟡 **[등재] `String.replace` 치환 문자열의 `$` 특수 해석 차단 (PR #51 하네스, PoC-(45) 문서 반영, 근거유형 = 실측 `run.mjs`)**: 렌더 출력을 원본에 되돌려 끼우는 지점에서 치환 문자열에 `$&`/`$'`/`$1` 같은 패턴이 있으면 `String.replace`가 이를 **특수 치환자로 해석**해 패치를 오염시킬 수 있다. `dashboard/tools/ssr-nc/run.mjs`는 두 번째 인자에 **치환자 함수**(`() => c.patch`)를 써서 이 해석 경로 자체를 차단한다.
  - 🟡 **[등재] 하네스 한계 ④ — 렌더 대상 밖은 애초에 도달 불가 (2026-09-12 PoC-(46) 등재, 근거유형 = 실측)**: 위 ①②③에 더해, **하네스가 렌더하지 않는 화면은 단언 자체가 성립하지 않는다**. PR #57이 신설한 **랜딩 페이지(`/`)는 NC 이식 대상이 아니라**, 말풍선 문구가 `server/app/constants.py` 실물과 어긋나도 **자동 검출되지 않는다** — 이번엔 **사람이 grep 대조**로 확인했다(**8.7(d)**). 자동화하려면 하네스 수정이 필요하고 그건 **절대 수정 금지 대상**이라 본 Set에서 손대지 않았다. ★ ②(텍스트 전용)와 **다른 축**이다 — ②는 *"같은 화면의 다른 속성"*, ④는 *"화면 자체가 사정권 밖"*. ⚠️ **8.7(c) `twMerge` 토큰 소실도 본 하네스로는 도달 불가**다 — 단언 축이 **텍스트 노드뿐**이라 `className` 존속 여부는 ②의 사유로 잡히지 않는다. 🆕 **[2026-09-19 PoC-(53)]** `HelpPage`도 같은 사유(`entry.tsx` 모듈 그래프 밖)로 **도달 불가** — 상세 = **8.7(a)**.
  - 🟢 **[등재] 검증 도구 환경 사실 2건 (2026-09-12 PoC-(46) 등재, 근거유형 = 실측)**
    - **① `ssr-nc`는 커밋되지 않은 워킹트리 diff가 있으면 거부한다(exit 1).** 사유 = 하네스가 **자기가 넣는 임시 변형**과 **사람의 미커밋 변경**을 구분하지 못하기 때문이다. ⇒ 검증 순서는 **`tsc -b` / `eslint` / `build` → 커밋 → `ssr-nc`**다. 순서를 바꾸면 **설계대로 거부한 것**을 "도구가 죽었다"로 오진하게 된다.
    - **② `npm run build`가 `tsc -b && vite build` 포함형**이라, 검증 4종 중 `tsc -b` **단독 실행은 중복(무해)**이다. 줄이라는 뜻이 아니라 *"타입 검사를 돌렸다"의 근거가 두 곳*임을 적어 둔다.

**관련**: 8.3(뱃지 과소 표기 · ToF 미표시 원 미결 · 접근성 규약) / 6.4(ToF 메타 wire · (f) 가짜 ToF 잔존) / 7.6(d)(상태 표현 · `derive()` 순서) / 7.7(STT 배선 · confidence null) / 카테고리 3(G12 확정 — mock 거부 건 정합) / 카테고리 20(negative control · 학습 19) / 카테고리 26(부스 데모) / 카테고리 33(USP 2층)

### 8.5 SystemHealth 카카오 토큰 상태 실배선 — mock 제거 + 만료 표시 정정 (2026-09-09 PoC-(43) 신설, PR #49 `07742d9`)

`GET /api/v1/stats`의 `system_health.kakao_token_status` / `kakao_token_expires_in_minutes`가 **하드코딩 `"valid"` / `240`**이었다. 프론트 `SystemHealthCard.statusInfo()`는 `valid`/`expiring`/`expired` 3분기를 **이미** 렌더할 수 있었으므로 **화면은 준비돼 있었고 서버만 사실을 말하지 않았다** — 성격은 **배관(plumbing) PR**이다(새 판정 기준·새 임계·새 상태 어휘 신설 0). ⚠️ 소스 주석은 "외부 연동값은 11~14주차 전까지 mock"이었으나 카카오 실발송은 7.5(2026-09-03)에 이미 CLOSE였다 — **역방향 stale 주석**(7.7(k) PR #48 건과 같은 계열).

**(a) 결함의 성질 — 선언만 되고 발화된 적 없는 상태 (근거유형 = 실측)**
- `git log -S'"expiring"' -- server` = **커밋 0건**. `expiring`은 서버 트리에 **문자열로 존재한 적조차 없다** → 프론트 3분기는 **선언만 되고 서버가 발화한 적이 없었다**(학습 14 = 선언 ≠ 발화).
- ∴ 토큰이 만료돼도 대시보드는 **초록불 "유효"**를 표시했다. 8.4가 정정한 표시 결함 계열의 5번째이되, 8.4가 **프론트가 잘못 읽은** 유형이었다면 본 건은 **서버가 거짓을 낸** 유형이다.

**(b) 상태 파생 결정표 — 9행 → 3상태로 붕괴 (근거유형 = 실측, 축 = 토큰 행 부재 + 음수 구간 + 경계값 정확히 0)**

| # | `kakao_tokens` 행 | 잔여 | status | minutes | 화면 문구 |
|---|---|---|---|---|---|
| 1 | **부재** | 미상 | `expired` | `0` | 만료 — 재발급 필요 |
| 2 | 존재 | −3일 | `expired` | `-4320` | 3일 전 만료 |
| 3 | 존재 | −1초 | `expired` | `-1` | 1분 전 만료 |
| 4 | 존재 | **정확히 0** | `expired` | `0` | 만료 — 재발급 필요 |
| 5 | 존재 | +1초 | `expiring` | `0` | 0분 후 만료 |
| 6 | 존재 | 임계 −1초 | `expiring` | `9` | 9분 후 만료 |
| 7 | 존재 | **임계 정확히**(10분) | `expiring` | `10` | 10분 후 만료 |
| 8 | 존재 | 임계 +1초 | `valid` | `10` | 10분 후 만료 |
| 9 | 존재 | +6시간 | `valid` | `360` | 360분 후 만료 |

- **9행이 고유 3상태로 붕괴한다** — 축을 부재·음수까지 넓혀도 **4번째 어휘가 생기지 않는다**는 것이 (d) 합류 설계의 증명이다(회귀 `test_token_status_grid_collapses_to_three`가 9행 전체를 단언).
- **행 4가 `expired`** = 비교가 `<= 0`(non-strict)임을 고정. 갈리는 지점은 행 3/4가 아니라 **행 4와 행 5**다.
- **행 7이 `expiring` / 행 8이 `valid`** = 비교가 `<= MARGIN`(non-strict)임을 고정 — `needs_refresh()`와 **동일 부등호**.
- ⚠️ **행 6·7과 행 8의 `minutes`가 둘 다 `10`**이다(floor 때문에 겹친다). **숫자만으로는 임박/정상이 구분되지 않으며** 구분은 색·라벨(8.3 3중 표기)이 담당한다.

**(c) `KAKAO_REFRESH_MARGIN` 재사용 — 신규 상수 0 (근거유형 = 논증, 입력 실측 = `constants.py` 정의 주석 "access 토큰 '만료 임박' 판정 여유" + `models.KakaoToken.needs_refresh`)**
- "만료 임박" 임계를 새로 만들지 않고 **서버가 이미 갱신 판정에 쓰는 마진(10분)을 그대로** 썼다. 화면 표기만 다른 숫자를 쓰면 **"이 토큰은 그대로 못 쓴다"에 대한 진실이 두 개**가 된다.
- 카테고리 7.7(f) "실측 근거 0인 죽은 상수를 만들지 않는다"와 같은 원칙의 적용이다.

**(d) 🔴 토큰 행 부재를 `expired`로 합류 — 구분은 로그가 담당한다 (근거유형 = 논증, 입력 실측 = `SystemHealthCard.statusInfo()` `default` 분기)**
- 행이 없을 때 4번째 상태(`unknown` 등)를 만들지 않고 `expired`에 합류시켰다. 프론트 `statusInfo()`의 `default`는 **원시 문자열을 그대로 라벨에 넣으므로** 어휘를 늘리면 화면에 `unknown`이 노출된다.
- **화면이 알려야 할 것은 "지금 토큰을 못 쓴다" 하나**다. 단 **원인은 WARNING 로그로 구분**한다 — `행 부재(부트스트랩 전) → expired` vs `만료 %d분 경과`. 7.7(i)의 **`mode=real` 한 단어가 진단 방향을 갈랐다**는 로그 불변식과 같은 계열이다.
- ✅ **로그 구분이 실동작으로 확인됐다 (실측·문서 반영 2026-09-09 PoC-(44), 근거유형 = 실측)**: 서버 로그에 `WARNING in routes: kakao token status: 만료 1586분 경과`가 실출력됐다. 본 (d)가 **설계로만 적어 둔 "구분은 로그가 담당한다"가 실물 출력으로 확인**된 것이다. ⚠️ 동시에 (h)의 감수 근거("구분은 로그뿐")가 **로그가 실제로 찍힌다는 전제 위에** 서 있음도 함께 드러났다.
- 🟡 **[신규 미결] 만료 WARNING이 폴링마다 로그를 오염시킨다 (발견·문서 반영 2026-09-09 PoC-(44), 근거유형 = 실측)**: 만료 상태가 지속되는 동안 3초 주기 폴링마다 — 그것도 카테고리 8.1 follow-up의 **stats 3중** 때문에 **주기당 3회** — WARNING이 찍혀 다른 로그가 묻힌다. ⚠️ **양날이다**: 만료를 계속 알리는 것이 본 (d)의 **의도일 수도 있으므로 결함으로 단정하지 않는다**. **처리 방침 미확정(판단 사안)**. **판정 방법** = 폴러 통합(8.1 follow-up) 해소 후 잔존 빈도를 재측정하고, 그때도 과다하면 "상태 전이 시에만 로그" 게이트 도입을 검토한다 — 폴러 통합 전에 로그를 줄이면 **원인 두 개를 한 번에 건드려 무엇이 효과였는지 분리 불가**해진다.
    - 🆕 **[단서 — 2026-09-15 PoC-(49) 실측, 계수 단위 = 로그 줄 수] 실례와 주기당 빈도**: 만료 상태에서 폴링 **1회당 3줄**이 찍힌다 — 8.1 follow-up의 **stats 3중과 정합**이다. 실측 문구 = 「만료 **4162분** 경과」(학부생이 전날부터 띄워 둔 서버) · 「만료 **4164분** 경과」(같은 날 MCP가 띄운 서버). ⇒ 본 항이 설계로만 적어 둔 「주기당 3회」가 **실물 로그로 확인**됐다.
    - 🆕 **[단서 — 2026-09-15 PoC-(49) 실측] 관측된 폴링 간격이 본 항의 「3초 주기」와 다르다**: MCP가 띄운 서버 로그에서 `/stats` 접근 간격이 **약 60초**로 관측됐다. **[가설 — 미검증]** 대시보드 탭이 **백그라운드**여서 브라우저가 타이머를 제한했을 가능성이 있다. **판정 방법** = 탭을 **전면에 둔 상태**에서 access log 간격을 측정한다. ⚠️ **본 미결 자체는 유지**된다 — 빈도 값이 무엇이든 「폴링마다 찍힌다」는 성질은 바뀌지 않는다. **3초 주기 서술은 무변경**이다(본 관측은 **그 세션의 시점값**이며 8.1을 덮지 않는다 — 27.8(f-2) 「측정 시점값」 계열).
      - 🆕 **[실측 2026-09-16 PoC-(50), Chrome, 1회]** 위 **판정 방법을 실행**했다. **탭 백그라운드** 구간에서는 요청이 **약 60초 간격으로 몰려서** 발생했고(**14:02:44 / 14:03:44 / 14:04:41**), **탭을 전면으로 전환**한 뒤(14:04:44~)에는 **정확히 3초 주기**로 **주기당 `stats` 1회 + `notifications` 2회**가 나왔다.
      - ⇒ **백그라운드 스로틀 가설과 일치**한다. ⚠️ **Chrome 1회 관측이므로 단정하지 않는다**(브라우저·탭 상태 외의 변인 미통제). **본 미결과 「3초 주기」 서술은 그대로 무변경**이다.
      - **부스 운영 파급**: 대시보드 탭을 **전면에 유지**한다(백그라운드로 두면 화면 갱신이 약 60초까지 늘어진다).
      - **관찰(기록만)**: **주기당 `notifications` 2회**의 출처는 **미조사**다 — 원인 추정을 적지 않는다.

**(e) 🔴 잔여 분 음수 유지 — 0 클램프 기각 (결정 2026-09-09 / 결정 주체 = 사용자 / 근거유형 = 논증, 입력 실측 = (a)의 `git log -S` 0건)**
- MCP 초안은 만료 후 잔여 분을 **0으로 클램프**하고 경과 시간은 로그에만 남기는 안이었다. **기각**됐고 **음수(= 경과 분) 그대로 응답에 싣는 것**으로 확정됐다.
- **근거 3**: ① (a)에서 `expired`가 **서버 발화 이력 0건**으로 확정됐다 — 만료 화면은 실사용된 적이 없고, 부스에서 그 화면이 처음 뜰 때 **"얼마나 전에 죽었는지"가 대응을 가른다**(10분 전 = 재발송 / 3일 전 = refresh 체인 단절). ② **"로그로 보존"은 부스에서 접근 불가**다 — 로그를 볼 수 있는 상황이면 대시보드가 필요 없다. ③ 8.4(d)가 세운 **"실측 0 ≠ 값 없음"**(`formatConfidence`의 `=== null` 엄격 비교) 원칙과 충돌한다. 0 클램프는 "만료 3일 경과"를 "만료 0분"으로 뭉개는 것이며, **없는 값을 지어내는 것보다 있는 값을 지우는 쪽이라 더 나쁘다.**
- 파급: 프론트 작업의 성격이 "음수 방어 가드"에서 **"상태별 분기 렌더"**로 재규정됐다((f)).

**(f) 프론트 = 상태별 분기 렌더, 행 숨김 0 (근거유형 = 실측, SSR 렌더 출력 대조)**
- `tokenExtra(status, minutes)` 신설 — `valid`/`expiring`은 잔여 시간, `expired`는 **경과 시간을 분/시간/일로 환산**해 사람이 읽는 문구로 낸다. **어느 상태에서도 문구를 비우지 않는다**(비우면 행이 정상 상태와 구분되지 않는다).
- 실렌더 대조(SSR): `360분 후 만료 | 유효` / `5분 후 만료 | 곧 만료` / `만료 — 재발급 필요 | 만료됨` / `10분 전 만료 | 만료됨` / `3시간 전 만료 | 만료됨` / `3일 전 만료 | 만료됨`.
  - ★ **본 목록에 없던 경계를 ④런타임이 밟았다 (실측 2026-09-09 PoC-(44))**: 실응답 `-1561`분(= **26시간, 시간→일 경계**)이 `1일 전 만료`로 정상 환산됐다. SSR 대조는 **고른 6점**이었지 경계 전수가 아니었고, 그 빈틈을 실런타임이 메운 형태다(상세 = 아래 **(k)**).
- ★ **`statusInfo()` 색·라벨 매핑은 1바이트도 바꾸지 않았다**(diff grep `statusInfo|bg-status|label:` = **0줄**) — 8.3 3중 표기 규약 무훼손.
- 소비처는 **1곳뿐**이다 — `SystemHealthSummaryCard`는 `device_status`/`device_last_seen_at`/`signal_strength`만 읽고 토큰 필드를 렌더하지 않는다(위임의 "카드 2개" 전제가 실물과 달랐다, 27.8(e)).

**(g) 회귀 + negative control (근거유형 = 실측)**
- 회귀 케이스 89 → **99**(신규 10). 시각은 전건 **고정 주입**(`datetime(2026, 9, 9, 12, 0, 0)`) — 실 시계·실 카카오 API 미호출, DB 상태 주입만.
- **서버 NC 4종 전건 검출**: 만료 부등호 뒤집기 4건 / `expiring` 블록 제거 2건 / 행 부재 → `valid` 3건 / **0 클램프 도입 2건**(= (e) 결정이 회귀로 고정됐다).
- **프론트 NC 3종 전건 검출**(8.4(f) SSR 하네스 재사용): `expired` 분기 제거 10건(`-4320분 후 만료` 실렌더) / 부호 뒤집기 5건(`-4320분 전 만료`) / 만료 문구 공백화 1건(행에서 보조 문구 소실).
- ⚠️ **단언 한계 1건 정직 기록**: 부호 뒤집기의 `expired_10m` 픽스처가 F2(문구 존재 검사)를 통과했다 — `-10분 전 만료`가 `10분 전 만료`를 **부분 문자열로 포함**하기 때문이다. 가드 부재가 아니라 **F2 단언이 무딘 것**이며 F3(음수 부호 노출)이 잡았다. 카테고리 20 「미검출의 판정」의 자매 사례 = **"검출됐으나 특정 단언 하나가 무뎠다"**.
  - ✅ **해소 — 주석이 아니라 구조로 제거 (실측·문서 반영 2026-09-09 PoC-(44), PR #51 `8d574dd`, 근거유형 = 실측)**: 하네스가 `segments()`로 렌더 출력을 **텍스트 노드 배열**로 쪼갠 뒤 **배열 원소와 완전 일치**로 비교하도록 바뀌어, 부분 문자열 통과 경로 자체가 사라졌다. 실증 = `"-10분 전 만료".includes("10분 전 만료")` = **true(❌)** ↔ `"-10분 전 만료" === "10분 전 만료"` = **false(✅)**. ★ 요점은 **무딘 단언을 "주의하라"는 기록으로 남기지 않고 자료구조를 바꿔 원천 차단**한 것이다(상세 = 8.4(f)).
- ⚠️ **NC 드라이버가 실제로 값을 한 사례(3번째)**: `expiring` 블록 제거 변형의 최초 앵커가 **다른 NC의 앵커 문자열과 충돌**해 `count == 2`가 됐고 ③ 디스크 재독 assert가 이를 막았다. 카테고리 20 「4단계 보장」이 PR #46·#47에 이어 **세 번째로 거짓 결론을 차단**했다.

**(h) ⚠️ 경계 표기 — 무엇이 CLOSE되지 않았는가**
- 🔴 **토큰 상태 가시화 CLOSE ≠ 갱신 실패 자동 복구.** 본 PR은 **읽기 전용 관측**이며 토큰 갱신·재발급·무효화 코드는 **0줄**이다(`kakao.py`·`models.py` diff 부재로 증명). refresh 체인 자체가 끊기면 여전히 **사람이 7.5(e) 부트스트랩 절차를 재실행**해야 한다 — 화면이 알려줄 뿐 고치지 않는다.
- ⚠️ **행 1(행 부재)과 행 4(정확히 0)는 응답에서 동일**(`expired` / `0`)하고, 구분은 WARNING 로그뿐인데 **부스에서는 로그를 볼 수 없다**((e)②와 같은 논리). 현재 감수하는 근거 = 행 부재는 "부트스트랩 전" 상태라 부스 구간에서는 사실상 도달 불가.
- ⚠️ 프론트 NC는 **텍스트 라벨만** 검사한다 — 색·아이콘·레이아웃·대비비 미검증(8.4(f) 한계 동일 승계).

**(i) ⚠️ 조사 결과(결정 아님) — `system_health` 5필드 mock 잔여 실태 (근거유형 = 실측)**

본 PR 범위 밖이며 **처리 방침을 확정하지 않는다.** 실태만 기록한다.

| 필드 | 판정 | 근거 |
|---|---|---|
| `device_last_seen_at` | **부분 실데이터** | 오늘 알림이 있으면 최신 `detected_at` = 실데이터. ⚠️ **0건이면 `kst_now_iso()`로 떨어져 기기가 죽어도 "방금 전"**으로 보인다 — **본 절이 고친 결함과 동형** |
| `device_status` | mock | `"online"` 리터럴 |
| `signal_strength` | mock | `"strong"` 리터럴 |
| `clova_api_status` | ~~mock~~ → **✅ 실데이터** | ~~`"ok"` 리터럴. ⚠️ **7.7로 실 CSR이 배선됐는데도 이 필드만 리터럴로 잔존**~~ → **해소 (2026-09-09 PoC-(44), PR #50 `ca276a9`)**: `stt.is_real_mode()` 파생 2상태(`ok`/`degraded`). 상세 = **8.6** |
| `db_status` | mock | `"ok"` 리터럴 |

- ∴ `system_health` 7키 중 **실데이터는 본 PR의 토큰 2필드 + `device_last_seen_at` 절반**이다.
- 🟡 **[신규 미결] `system_health` mock 잔여 ~~4.5필드~~ → 3.5필드 (발견·문서 반영 2026-09-09 PoC-(43) / 부분 해소 2026-09-09 PoC-(44), 근거유형 = 실측)**: 조사 결과이지 결정이 아니다. **다음 후보 순서는 재료 유무로 갈린다** — ~~① `clova_api_status`(판정 재료가 7.7 코드에 이미 있다)~~ **✅ 해소 (PoC-(44), PR #50 `ca276a9` — 상세 = 8.6)** ② `device_last_seen_at` 0건 fallback ③ `device_status`/`signal_strength`(11주차 heartbeat 의존, **현시점 재료 부재**) ④ `db_status`. 처리 방침 미확정.
  - ⚠️ **부분 해소지 CLOSE가 아니다 — 계수 단위를 섞지 말 것**: 위 표는 **행** 단위로 **5행 중 1행** 해소(**4행 잔존**)이고, 본 미결 문구는 **필드** 단위로 `device_last_seen_at`을 0.5로 세어 **4.5 → 3.5필드**다. 같은 사실의 두 표기이며 **미결 자체는 유지**된다.
  - 🔴 **[신규 미결] `device_status`/`signal_strength`가 거짓을 낸다 — 배관이 아니라 판정 사안 (발견·문서 반영 2026-09-09 PoC-(44), 근거유형 = 실측 화면 catch)**: 보드가 USB에 연결되지 않은 상태에서 화면 3곳이 전부 **"온라인 / 강함 / 방금 전"**이었다. **8.5(a)가 고친 「서버가 거짓을 낸다」 유형의 재발**이다.
    - **소비처 실측 = 3곳 + 전역 훅 1개** (근거유형 = 실측 grep): `SystemHealthCard.tsx:47`(1개 참조) / `SystemHealthSummaryCard.tsx`(**5개 참조** — `device_status` L77·84·85 + `signal_strength` L95·96) / `hooks/useDevice.ts:13`의 `isOnline`(= `Header.tsx` 연결 뱃지의 출처). **PR #50이 손댄 소비처 1곳의 3배 이상**이므로 8.6의 배관 작업량으로 환산하면 안 된다.
    - 🔴 **`server/app/routes.py` 주석이 「의도된 UX 결정」임을 자백한다 (근거유형 = 실측, 코드 원문 인용)**: *"감지 0건(조용한 하루)에도 기기는 살아있으므로 detection 유무와 분리해 online mock 고정 (빈 상태 "시스템 정상" 안심 카드 전제)"*. ∴ `detected_at` 기반 임시 파생을 넣으면 **8.3이 세운 안심 카드 전제**(「빈 화면 에러카드 → "시스템 정상 작동" 안심 카드」)를 **정면으로 뒤집는다** → 성격이 **배관 PR이 아니라 판정 PR**이다. 8.5·8.6과 같은 줄에 세우면 안 된다.
    - ✅ **8.5(i)가 ③을 "11주차 heartbeat 의존, 현시점 재료 부재"로 분류한 것이 옳았다** — 본 세션 착수 시 "재료만 보고 UX 전제를 안 본 분류"로 의심됐으나 **대화 중 반증**됐다. 진짜 해법은 **M5-d 이후 heartbeat**이며, 지금 임시 파생을 넣으면 **두 번 고친다**.
    - **판정 방법** = 11주차 통합에서 ESP32 heartbeat wire가 선 뒤 `device_last_seen_at` 기준 임계로 `online`/`offline`을 파생하고, **그 시점에 8.3 안심 카드 전제를 명시적으로 재결정**한다(빈 상태 ≠ 기기 사망을 화면이 무엇으로 가를 것인가). 재결정 없이 파생만 넣으면 8.3 미결이 조용히 깨진다.
      - ⚠️ **[단서, PoC-(45) 문서 반영]** 위와 본 (i) 상단의 "11주차 heartbeat"는 **이미 지난 주차 표기**다(작성 시점 기준). 문면의 의미는 특정 주차 숫자가 아니라 **"M5-d 이후 heartbeat 통합 단계"** — 판정 트리거는 heartbeat wire 완료 여부이지 주차 번호가 아니다.
      - ✅ **[사용자 결정 2026-09-15 PoC-(49)] 현행 유지(수정 보류) — heartbeat 통합 전까지** (결정 주체 = **사용자**). 사유 = **heartbeat 미구현**이며, 이는 위 8.5(i)가 ③을 *"11주차 heartbeat 의존, 현시점 재료 부재"*로 분류한 **기존 판정과 동일**하다. 🔴 **미결 표기는 유지된다** — 결정된 것은 **「지금 고치지 않는다」는 처리 방침뿐**이고, 위 **판정 방법**(heartbeat wire 완료 후 8.3 안심 카드 전제를 명시적으로 재결정)은 **그대로 유효**하다.

**(j) 산출물 (근거유형 = 실측, `git show 07742d9 --stat`)**
- 3파일 **+290 / −6**: `server/app/routes.py`(순수 헬퍼 `_kakao_token_health` 신설 + `db.session.get` 읽기 전용 조회) / `server/app/tests/test_detect_regression.py`(+10) / `dashboard/src/components/stats/SystemHealthCard.tsx`(`tokenExtra` 신설).
- **`/stats` 응답 키 수 무변경** — 최상위 10키 / `system_health` 7키를 회귀가 정렬 비교로 고정(`stats.ts` `StatsResponse` 10필드 / `SystemHealth` 7필드와 1:1).
- **토큰 값은 응답·로그·테스트 어디에도 나가지 않는다** — 나가는 것은 **상태와 잔여 시간뿐**이며 회귀 `test_token_value_never_reaches_stats_response`가 고정한다(카테고리 21 `.env` 위생 동형).
- 커밋 **1개**(`🐛 Fix`) — `git-convention.md`의 분리 기준은 "여러 Type이 섞이면"인데 서버·프론트·테스트가 전부 **거짓 표시 정정 = 단일 Type**이라 8.4의 4분리와 달리 분리 트리거가 발동하지 않았다.

**(k) ✅ ④런타임 CLOSE — 실 `/stats` 응답 → 실 화면 (실측·문서 반영 2026-09-09 PoC-(44), 근거유형 = 실측 대화형 curl + 화면 catch)**

(g)의 회귀·NC는 **시각 고정 주입 + SSR 문자열 렌더**였고 (j)까지 어디에도 **실 서버 + 실 브라우저**를 통과한 기록이 없었다 — 8.5(g)가 *"실 시계·실 카카오 API 미호출, DB 상태 주입만"*으로 정직하게 적어 둔 그 구간이다. 본 항목이 그 구간을 닫는다.

- **실측 경로**: 실 `/stats` 응답 `kakao_token_status="expired"` / `kakao_token_expires_in_minutes=-1561` → 대시보드 화면 **"1일 전 만료" + 빨간 점**.
- ★ **(f) SSR 대조 목록에 없던 경계를 밟았다 — 시간→일 경계(26시간)**. `-1561`분 = 26.0시간이고 `tokenExtra()`가 `1일 전 만료`로 정상 환산했다. (f)의 6점은 **고른 표본**이었지 경계 전수가 아니었으므로, 이는 SSR이 못 본 지점을 실런타임이 메운 사례다.
- ⚠️ **24~47시간이 전부 "1일 전"으로 뭉개진다 — 감수 가능으로 판정 (근거유형 = 논증, 입력 실측 = 위 실렌더)**: `expired` 상태에서 사람이 하는 행동은 **재발급 하나**이고, 판정 자체는 `status` 필드가 이미 `expired`로 확정하므로 **표시 해상도가 판정을 오염시키지 않는다**. (e)가 음수를 살린 목적("10분 전 = 재발송 / 3일 전 = 체인 단절")은 **일 단위 해상도로도 달성**된다. → **정정 대상 아님.**
  - ⚠️ **[단서 — 2026-09-15 PoC-(49), 근거유형 = 실측 grep] 이 문장은 두 형태로 인용된다**: 본 (k)의 **실물은 「표시 해상도가 판정을 오염시키지 않는다」**이고, **27.8(j)①과 33.6(e) 제목**은 **「표시가 판정을 오염시키지 않는다」**라는 **요약형**을 쓴다. ⇒ **요약형으로 8.5를 grep하면 0건**이 나와 **「8.5에 그런 문장이 없다」는 유령 부재 판정**에 빠진다(학습 21 계열 · 27.8(j)① 동형). **원문은 무변경**이고 **요약형 인용도 정정 대상이 아니다** — 갈리는 것은 **검색어뿐**이다.
- ★ **본 항목은 (g)의 NC를 대체하지 않는다** — NC는 "가드가 있는가"를, ④런타임은 "실물 경로가 실제로 이어지는가"를 본다. 두 층은 서로를 증명하지 않는다.

**관련**: 8.4(표시 결함 계열 · SSR NC 하네스 · `=== null` 엄격 비교) / 8.3(3중 표기) / 7.5(e)(토큰 부트스트랩 절차 — 본 절이 관측만 하고 고치지 않는 대상) / 7.7(k)(역방향 stale 주석 계열) / 6.1(`StatsResponse` 키 계약) / 카테고리 20(NC 4단계 보장 3번째 작동) / 카테고리 26(부스 대응 판단)

### 8.6 SystemHealth Clova STT 상태 실배선 — mock 제거 + `is_real_mode()` 파생 (2026-09-09 PoC-(44) 신설, PR #50 `ca276a9`)

8.5(i)가 *"다음 후보 순서는 재료 유무로 갈린다"*로 1순위 지목한 `clova_api_status`를 닫았다. `"ok"` 하드코딩 리터럴 → `stt.is_real_mode()` 파생. 성격은 **8.5와 같은 배관(plumbing) PR**이다(새 판정 기준·새 임계 신설 0). ⚠️ 단 8.5와 달리 **새 상태 어휘 `degraded`가 화면에 처음 도달**했다 — 아래 (b) 참조.

**(a) 🔴 `error`를 기각하고 `degraded`를 쓴 근거 — 「안 불렀다」와 「불렀는데 실패」의 구분 (근거유형 = 논증, 입력 실측 = 7.7(i) `mode=real` 로그 불변식 + `routes.py` 주석 원문)**
- 판정 재료는 **env 게이트(`stt.is_real_mode()`)뿐**이다. env가 비어 있다는 것은 **"CSR을 아직 한 번도 부르지 않았다"**를 뜻하지 **"불렀는데 실패했다"**가 아니다. `error`는 후자를 함의하므로 **사실을 넘어선다**.
- ★ **실 CSR 핑을 금지한 근거도 같다** — 상태 표시를 위해 핑을 때리면 30.9의 **미규명 301건** 위에 원인 불명 호출을 더 얹는다. `routes.py` 주석이 이를 명문화했다: *"env 게이트(stt.is_real_mode)만 본다 — 실 CSR 핑 금지"*.
- ∴ **2상태만 발화한다**: `ok`(env 양쪽 설정) / `degraded`(그 외). 7.7(e) env 게이트의 **`NCP_CLIENT_ID`·`NCP_CLIENT_SECRET` 둘 다** 조건을 그대로 재사용했다 — 판정 기준이 두 개가 되지 않게.
- ★ **7.7(k)의 「폴백」 미결과 같은 축이다**: 그 미결이 *"「안 불렀다」와 「불렀는데 실패했다」를 가르는 것이 `mode=real` 로그 불변식인데 「폴백」이 그 구분을 흐린다"*고 적었고, 본 절은 **같은 구분을 상태 어휘 선택에 적용**했다. 문구 교체(7.7(k) 미결)는 여전히 **미해소**다.

**(b) ★ ④런타임 CLOSE = 대조 실험 — 같은 코드가 조건에 따라 다른 값을 낸다 (실측·문서 반영 2026-09-09 PoC-(44), 근거유형 = 실측 대화형 curl + 화면 catch)**

| 조건 | `/stats` 실응답 | 화면 |
|---|---|---|
| NCP 키 **있음** | `"ok"` | ● **정상**(초록) |
| NCP 키 **빈 문자열** | `"degraded"` | ● **지연**(주황) |

- ★ **`git log -S'"degraded"' -- server`가 PR #50 이전 0건이던 값이 처음 화면에 도달했다** — 8.5(a)의 `expiring` 건과 **같은 유형**(선언만 되고 발화된 적 없는 상태)이나, 이번엔 **발화와 도달을 같은 세션에서 확인**했다.
- 🔴 **빈 문자열이 falsy로 처리됨이 실증됐다 → 8.5(b) 계열의 「결정표」 서술이 논증에서 실측으로 승격**: 7.7(e) env 게이트에서 `None`과 `""`가 **같은 값으로 붕괴**한다는 것이 화면 값의 차이로 확인됐다. ⚠️ 승격된 것은 **이 붕괴 사실 하나**이며, env 게이트의 나머지 서술(한쪽만 설정 시 401 회피)은 **여전히 논증**이다 — 섞어 읽지 말 것.
- ★ **단일 값 확인이 아니라 대조 실험이었다** — `ok`만 봤다면 "리터럴을 안 지운 것"과 구별되지 않는다. **두 조건이 다른 값을 냈다는 것이 배선의 증거**다(카테고리 20 「negative control 미검출의 판정」과 같은 사고).

**(c) 회귀 + negative control (근거유형 = 실측)**
- 회귀 케이스 **99 → 102**(신규 3). 누적 현재값 서술은 **7.5(i)** 소관.
- **NC 3종 전건 검출**: ① `is_real_mode()` 호출을 `True` 고정 ② 삼항 분기를 `"ok"` 리터럴로 되돌림 ③ `degraded` → `error` 어휘 교체. ③이 걸린다는 것은 **(a)의 어휘 결정이 회귀로 고정됐다**는 뜻이다(회귀 `assertNotEqual(health["clova_api_status"], "error")`).
- 실행 = `python3 -B`(카테고리 20 `.pyc` 절).

**(d) 🔗 파급 — 7.7(e)의 fail-silent 성질이 사라졌다 (근거유형 = 논증, 입력 실측 = (b) 화면 대조)**
- 7.7(e) env 게이트의 실물 문언은 *"미설정이면 **호출 자체를 하지 않고** mock 자막을 유지한다"*이다. 이는 설계상 옳은 동작이나, **화면·응답 어디에도 그 사실이 드러나지 않아** NCP env가 빠진 채 배포되면 **가짜 자막이 소리 없이 카카오톡으로 나갔다**.
- ✅ **본 절 이후 그 침묵이 깨졌다** — 대시보드가 `● 지연(주황)`으로 알린다. ⚠️ 단 **자막 자체는 여전히 mock으로 나간다**(본 PR은 **읽기 전용 관측**이며 mock 폴백을 막지 않는다). **화면이 알려줄 뿐 고치지 않는다** — 8.5(h)와 동일한 경계다.
- ⚠️ 이 파급은 **대시보드를 보고 있을 때만** 성립한다. 부스 운영자가 화면을 안 보면 침묵과 다름없으므로, **기동 체크리스트에 편입**하는 것이 실효 조건이다(7.4 신규 미결의 리허설 체크리스트와 같은 층).

**(e) 산출물 (근거유형 = 실측, `git show ca276a9 --stat`)**
- **2파일 +52 / −3**: `server/app/routes.py`(9줄 — 삼항 1줄 + 근거 주석) / `server/app/tests/test_detect_regression.py`(+46).
- **프론트 0줄** — `SystemHealthCard.tsx:56`이 `health.clova_api_status`를 그대로 라벨에 넘기고 `statusInfo()`가 `degraded`를 이미 렌더할 수 있었다. **소비처 1곳**이라 8.5(f)와 같은 구조다.
- **`/stats` 응답 키 수 무변경**(최상위 10 / `system_health` 7). 커밋 **1개 `🐛 Fix`** — 단일 Type이라 8.4의 4분리 트리거 미발동(8.5(j)와 동일 판단).
- **NCP 자격증명은 응답·로그·테스트 어디에도 나가지 않는다** — 나가는 것은 **`ok`/`degraded` 두 어휘뿐**이다(8.5(j) 토큰 원칙 동형).

**(f) ⚠️ 경계 표기 — 무엇이 CLOSE되지 않았는가**
- 🔴 **STT 상태 가시화 CLOSE ≠ STT 건강성 판정.** 본 절이 보는 것은 **env 설정 여부**뿐이다. 자격증명이 **설정돼 있으나 틀렸거나**, CSR이 **429·5xx를 내는 중**이면 화면은 여전히 **`ok`(초록)**다 — 7.7(i)가 실증한 HTTP 429 상황이 화면에 **드러나지 않는다**. 이를 잡으려면 **실 호출 결과를 상태로 승격**해야 하고 그것은 (a)가 기각한 핑과 다른 설계(최근 호출 결과 캐시)이므로 **별건**이다.
- ⚠️ **`degraded` = 자막이 mock이라는 뜻이지 시스템이 느리다는 뜻이 아니다.** 화면 라벨 "지연"은 `statusInfo()`가 이미 갖고 있던 어휘를 재사용한 것이라 **의미가 정확히 맞지 않는다**. 새 어휘를 만들면 8.5(d)가 막은 `default` 분기 원시 문자열 노출 문제로 되돌아가므로 **감수**한다.
- 🟡 **[신규 미결] `degraded` 라벨 "지연"의 의미 불일치 (발견·문서 반영 2026-09-09 PoC-(44), 근거유형 = 실측 `SystemHealthCard.statusInfo()` 매핑)**: 위 감수 사항의 등재다. **처리 방침 미확정** — 어휘를 늘리는 대신 `SystemHealthCard`에 필드별 라벨 오버라이드를 두는 방향이 후보다. **판정 방법** = 부스 리허설에서 이 라벨을 본 사람이 "자막이 mock이다"로 읽는지 확인(읽히지 않으면 실결함).

**관련**: 8.5(같은 계열 배관 PR · `statusInfo()` 3분기 · mock 잔여 실태 (i)) / 8.4(표시 결함 계열) / 8.3(3중 표기 · 안심 카드 전제) / 7.7(e)(env 게이트 — 본 절이 가시화한 대상) / 7.7(i)(`mode=real` 로그 불변식) / 7.7(k)(「폴백」 문구 미결 — **미해소**) / 30.9(CSR 요금 · 미규명 301건 — 핑 금지 근거) / 6.1(`StatsResponse` 키 계약) / 카테고리 20(NC `python3 -B` · 미검출 판정)

---

### 8.7 도움말 카피 ↔ 실제 동작 정합성 정정 + 랜딩 페이지 신설 (2026-09-12 PoC-(46) 신설, PR #56 `fb9155f` · PR #57 `9b32183`)

**(a) PR #56 — 도움말 doorbell·knock 카피 2라운드 정정 (근거유형 = 실측 코드 대조)**

- **1차**: `dashboard/src/pages/HelpPage.tsx` doorbell 안내가 *"등록된 초인종 소리가 울리면 알려드려요."*로 **제품에 없는 등록 기능을 화면이 사용자에게 약속**하고 있었다(등록 기능 부재 실측 = **26.10(a)**). → *"초인종이 울리면 알려드려요."*
- **2차**: 1차 결과가 **반대 방향 불일치**를 낳았다 — doorbell·knock은 `presence=false`면 `tof_rejected`로 **1차 알림이 가지 않는데**(`utils.py` `_tof_decision` + `tof_meta.py` `evaluate_gate` 실물 확인) 새 카피는 **무조건 알림을 약속**한다. → 현행 = *"문 앞에 사람이 있을 때 초인종이 울리면 알려드려요."* / knock도 동일 조건 반영(*"문 앞에 사람이 있을 때 현관문을 두드리는 노크 소리가 나면 알려드려요."*).
- **fire_alarm 카피 무변경**: `fire_alarm_bypass`로 ToF를 **우회**하므로 *"화재경보음을 감지하면 가장 먼저, 가장 크게 알려요."*라는 **무조건 알림 약속이 정확하다**(G12 · 카테고리 3 정합). ⚠️ **[근거 문구 경계 — 발견 · 문서 반영 2026-09-19 PoC-(53), 근거유형 = 실측 코드 대조]** 「무조건」은 **ToF 문맥에 한해** 정확하다 — `server/app/utils.py`의 신뢰도 게이트는 **「신뢰도 < 임계값 → 1차 알림 skip, 클래스 무관」**이라 **`fire_alarm`도 신뢰도 게이트는 받는다**(우회하는 것은 ToF뿐, G12). 본문 카드 카피는 ToF 문맥이라 **무변경이 맞고**, 어긋난 것은 「무조건 알림 약속이 정확하다」는 **근거 문구의 범위**다(27.8(m)④ 「결론은 옳고 근거 문구가 어긋남」 계열 — **27.8(o)⑤**).
- ★ **한 번의 정정이 다음 불일치를 만든다.** *"없는 기능을 지우는 것"*과 *"있는 조건을 적는 것"*은 **별개 작업**이다 — 1차에서 닫았으면 카피는 방향만 바뀐 채 여전히 틀렸다. 8.3(뱃지 과소 표기) → 8.4(c)와 같은 계열의 재실증.
- ~~⚠️ **미수정으로 남긴 것 (사용자 판단 대기)**: 같은 파일 FAQ 1번 *"소리가 감지되면 보통 5초 이내에 1차 알림이, 15초 이내에 사진·자막이 담긴 2차 알림이 도착해요."*는 **클래스 구분 없이 도착을 암시**한다(doorbell·knock에는 ToF 게이트가 앞에 있다). **처리 방침 미확정 — 방향 확정 금지.**~~ → ✅ **해소 (사용자 확정 2026-09-19 → PR #66 `765624b` 2026-09-19 머지, 내부 커밋 `e1df298`, 근거유형 = 실측 `git show` + 사용자 결정)**: FAQ 1번 a를 **「알림이 갈 때는 보통 5초 이내에 1차 알림이, 15초 이내에 사진·자막이 담긴 2차 알림이 도착해요.」**로 교체했다(**57자 → 57자**, diff 1파일 +1 −1). **결정 = 최소 개입안**(3안 중 2안) — 근거 ① 같은 화면 본문 카드는 이미 조건을 명시(위 2차 정정)하는데 FAQ만 무조건 도착을 약속해 **화면 내부 자기모순** ② **사용자 대면 약속**이라 신뢰 문제 ③ 게이트 설명을 FAQ에 넣으면 **5060 페르소나(8.3) 가독성**을 해친다 — FAQ는 「얼마나 빨리 오나」를 답하는 자리. 채택안은 「도착할 때는 … 도착해요」 동어 반복이 없고 조건절이 **게이트 종류를 특정하지 않아** ToF · 신뢰도 양쪽을 덮는다. **검증** = 앵커 count == 1 / 구조 무변경 기계 증명(문자열 리터럴 내용 블랭킹 대조 → JSX · 속성 · className · import · 타입 변경 0, 리터럴 중 정확히 1개만 상이) / lint · build · ssr-nc 전건 / 회귀 106 무변동. 커밋 Type = **🐛 Fix**(SSoT와 어긋난 카피를 바로잡는 결함 수정 — `🎨 Design`은 CSS/UI 디자인 변경용이라 미해당).
  - 🔴 **`ssr-nc` 도달 불가 정식 판정 (근거유형 = 실측)**: `entry.tsx`가 렌더하는 것은 `SystemHealthCard` · `NotificationTof` · `NotificationSTT` **3종뿐**, `run.mjs`의 SRC도 3개, ssr-nc 전체에 `HelpPage` 언급 **0건**, `HelpPage`의 유일한 importer는 `App.tsx`인데 `entry.tsx`는 `App.tsx`를 거치지 않는다 ⇒ **SSR 모듈 그래프 밖**. **「가드 부재」가 아니라 8.4(f) 한계 ④ 「도달 불가」**이며 **하네스 무수정**.
  - 🟡 **[신규 미결] ~~같은 계열 미정정 2건~~ → 1건 (발견 · 문서 반영 2026-09-19 PoC-(53), 근거유형 = 실측 코드 대조)** — 안 적으면 다음 세션이 하나씩 재발견한다: **① FAQ 2번** 「…자막이 알림 카드에 함께 표시돼요」는 2차 알림 도착을 전제하나 `fire_alarm`은 `enrich_status="skipped"`라 **2차가 아예 없다** / **② `SystemHealthSummaryCard`** 「현관에서 소리가 감지되면 바로 알려드릴게요.」 — 동일한 무조건 단언. 🔴 **처리 방침 미확정 — 방향 확정 금지**(스코프 제외 · §9 대상).
    - ✅ **① 해소 (사용자 확정 2026-09-20 → PR #67 `5868c71` 2026-09-20 머지, 내부 커밋 `9ecdff3`, 근거유형 = 실측 `git show` + 사용자 결정)**: FAQ 2번 `a` 앞머리에 조건절 **「2차 알림이 갈 때는」**을 붙여 **「2차 알림이 갈 때는 현관 카메라가 찍은 사진과, 방문자가 한 말을 글자로 바꾼 자막이 알림 카드에 함께 표시돼요.」**로 교체했다(**52자 → 64자**, diff **1파일 +1 / −1**, Type = **🐛 Fix**). **게이트 종류 비특정.**
      - **결정 = 최소 개입안**(PR #66과 동형, 결정 주체 = **사용자**, 결정일 = **2026-09-20**, 근거유형 = **사용자 결정**). 근거 3 = ① 같은 화면 본문 카드가 이미 조건을 명시하는데 FAQ만 무조건 약속하면 **화면 내부 자기모순** ② **사용자 대면 약속**이라 신뢰 문제 ③ 게이트 설명을 FAQ에 넣으면 **5060 페르소나(8.3) 가독성**을 해친다.
      - **검증**: 구조 무변경 기계 증명 **2축**(리터럴 블랭킹 구조본 차이 **0** + 리터럴 목록 상이 **정확히 1**) / **negative control 3단**(기준값 → `const FAQS` → `FAQS_NC` **검출 1** → `space-y-6` → `space-y-7`이 **구조본 0인데 리터럴 2로 검출** → 복원 후 기준값 복귀) / `lint` · `build` · `ssr-nc` **전건 exit 0**.
      - ★ **NC 2축이 위임보다 정밀했다** — 위임은 블랭킹 **1축**만 지정했으나 **블랭킹만으로는 `className` 변경이 가려진다**는 것을 MCP가 발견해 **리터럴 목록을 두 번째 축으로 추가**했고 NC-b가 그 축의 검출력을 실증했다. **무딘 단언이 될 뻔한 자리**다(5-9 「불변식 설계는 MCP에 맡기되 부족하면 보강」).
      - 🔴 **`ssr-nc` 도달 불가**: `entry.tsx`가 렌더하는 것은 **3종뿐**(`SystemHealthCard` · `NotificationTof` · `NotificationSTT`)이고 하네스 전체에 `HelpPage` 참조 **0건**이다 ⇒ **「가드 부재」가 아니라 8.4(f) 한계 ④ 「도달 불가」**이며 **하네스 무수정**이다(위 PR #66 정식 판정과 동일 축).
    - 🔴 **② 미해소 — `SystemHealthSummaryCard.tsx`는 손대지 않았다 (사용자 결정 2026-09-20, 근거유형 = 사용자 결정)**: 같은 계열 「무조건 도착」 단언이나, 그 카드는 **8.5(i)의 `device_status`/`signal_strength` 거짓 표시 미결과 같은 카드** 위에 있다. 8.5(i)가 *「heartbeat wire가 선 뒤 8.3 안심 카드 전제를 명시적으로 재결정하라, 재결정 없이 파생만 넣으면 8.3 미결이 조용히 깨진다」*고 적었으므로 **카피만 먼저 고치면 그 재결정을 앞당겨 버린다.** ⇒ **처리 시점 = 8.5(i) heartbeat 통합과 동시**(한 번에 한 변수). 🔴 **미결 유지 — 카피 문안도 방향도 확정하지 않는다.**
    - 🔴 **[근거 보강 — 발견일 = 반영일 2026-09-20 PoC-(54), 근거유형 = 실측 코드 대조, 계수 단위 = 판정 분기 수] 2차 알림 부재 경로는 1개가 아니라 3개다.** `server/app/utils.py`의 판정 함수 `_apply_prediction_policy()`에서 `enrich_status="skipped"`로 가는 분기는 **3개**이며(같은 리터럴이 `server/seed.py`에 2줄 더 있으나 그것은 **시드 픽스처**이지 판정 경로가 아니다), 위 ①이 등재한 것은 그중 `fire_alarm` 축 **1개뿐**이었다.

      | # | 조건 | `primary_sent` | `skip_reason` |
      |---|---|---|---|
      | 1 | `confidence < CONFIDENCE_THRESHOLD` | **False** | `"low_confidence"` |
      | 2 | `predicted_class == "fire_alarm"` | **True** | `None` |
      | 3 | `tof["applied"] and not tof["passed"]` | **False** | `"tof_rejected"` |

      - ⚠️ **`fire_alarm` 경로만 `primary_sent: True`다** — 1차는 가고 2차만 없다. 나머지 둘은 **1차도 가지 않는다**. 🔴 **세 경로를 섞어 읽지 말 것** — 「2차가 없다」와 「알림 자체가 없다」는 다른 사실이다.
      - ★ **이 사실이 위 ①의 「게이트 비특정」 제약을 코드 쪽에서 뒷받침한다** — 조건절이 게이트 종류를 특정했다면 **나머지 2경로를 빠뜨렸을 것**이다. PR #66의 채택 근거(*조건절이 게이트 종류를 특정하지 않아 ToF · 신뢰도 양쪽을 덮는다*)와 **같은 축**이며, 본 항은 그 「양쪽」이 실제로는 **3분기**임을 실측으로 좁힌 것이다.
      - 🔴 **본 항은 카피를 더 고치라고 적지 않는다** — 등재는 **경로 수와 경계**까지다.
  - **인접 판정 1건 (근거유형 = 실측 + 한계)**: `NotificationList.tsx`의 「현관에서 소리가 감지되면 여기에 표시됩니다.」는 **정정 대상이 아니다** — `routes.py`가 게이트 통과 여부와 무관하게 `Notification` 행을 생성한다(skip 건도 `skip_reason`과 함께 저장). ⚠️ **목록 조회 API가 skip 건을 필터링하는지는 미확인**이며, 필터가 있다면 이 판정은 뒤집힌다.

**(b) PR #57 — 랜딩 페이지 신설(`/`) + 대시보드 진입 연출 + 모션 접근성 게이트 (근거유형 = 실측 `git show 9b32183 --stat` · `App.tsx` 라우트 대조)**

- **라우트** = **`/` 랜딩**(AppShell 밖 전체 화면) / **`/home` 대시보드**. 기존 4개 경로(`notifications` `stats` `settings` `help`) + `*` **무변경** — `App.tsx` 실물 전수 대조. **신규 의존성 0**(CSS `transform`/`opacity` + 인라인 SVG뿐).
- **모션 게이트** `useReducedMotion` = OS `prefers-reduced-motion` **OR** 앱 「움직임 줄이기」 토글. 켜져 있으면 애니메이션 클래스를 **아예 붙이지 않아** 최종 상태로 즉시 렌더된다(**빈 화면 없음**). `index.css`의 기존 전역 감속 규칙은 **2중 방어로 잔존** — 8.3 B-1a 계열 접근성 규약의 연장.
- **진입 연출**은 AppShell 래퍼 `.page-enter` **한 곳**에서만 얹는다 — 각 페이지의 데이터 렌더 로직 **무변경**. 3초 폴링 리렌더는 DOM을 교체하지 않아 **재생되지 않고**, 라우트 전환 때만 다시 돈다.
- ★ **리디자인 1회 — 근거유형 = 사용자 육안 판정**: 1차 **다크 네온** 안을 학부생이 **"AI 티"**로 판정해 **라이트 톤 + 카카오톡 대화 CSS 재현**으로 전환했다. **자동 검출 수단이 없는 축**이며, 본 절은 판정의 존재만 기록한다(미적 기준 등재 아님).
- ⚠️ **PR 성격 어휘 신설 여부 = 사용자 판단 대기**: 본 PR이 기존에 각 절이 그때그때 명명해 온 어휘(「배관 PR」 8.5 서문 / 「방법론 자산」 8.4(f))에 안 맞는다는 관찰이 있으나, **"PR 성격 분류 체계"라는 것 자체가 등재된 적이 없다**(2026-09-09 PoC-(44) §9 판단 요청과 **동형**). ⇒ **본 절은 새 성격 어휘를 신설하지 않는다.**

**(c) 🟡 [신규 미결] `tailwind-merge`가 Tailwind v4 커스텀 `--text-*` 토큰을 색 그룹으로 오분류한다 (발견·문서 반영 2026-09-12, 근거유형 = 실측 — 본 세션 in-session 재현)**

- **실측**(`dashboard/`에서 `tailwind-merge` **3.6.0** 직접 호출):

  | 입력 | 출력 | 판정 |
  |---|---|---|
  | `cn("text-h3 font-bold", "text-danger-deep")` | `"font-bold text-danger-deep"` | `text-h3` **소실** |
  | `cn("text-h3 font-bold")` (대조군) | `"text-h3 font-bold"` | **유지** |
  | `cn("text-(length:--text-caption) font-bold", "text-danger-deep")` | `"text-(length:--text-caption) font-bold text-danger-deep"` | **둘 다 보존** |

- ⇒ 소실은 **병합이 일어날 때만** 발생한다. 원인 = `text-h3` 같은 **커스텀 토큰 클래스명이 `text-<color>`와 형태가 같아** twMerge가 **같은 그룹(색)으로 보고 뒤쪽을 남기기** 때문.
- **브라우저 실측**: 화재 알림 제목 **16px → 18px**, 사이드바 탭 **5개 16px → 17px**(수정 **후** 값 = 의도값 복원).
- **해법** = **`text-(length:--text-*)` 형태 치환**(임의 값 문법이라 색 그룹과 충돌하지 않는다). PR #57에서 **랜딩 4곳 + `NotificationCard` + `Sidebar`** 해소 — 사후 실측 `grep -rn "length:--text-" dashboard/src` = **6곳**(계수 단위 = ~~**출현 줄 수**~~ → **실사용 줄 수**). 🔴 **[계수 단위 오기 정정 — 발견일 = 반영일 = 2026-09-21 PoC-(55), 근거유형 = 실측 `git grep`]** 같은 grep을 PR #57 머지 시점 `9b32183`에서 다시 돌리면 **7줄**이며 그중 **1줄은 `LandingPage.tsx`의 주석**이다 ⇒ **실사용 6 · 출현 줄 7**. 🔴 **값 6이 틀린 것이 아니라 단위 이름이 틀렸다.** ⚠️ 현재 HEAD에서는 `lib/utils.ts` 주석이 하나 더 늘어 **출현 줄 8 · 실사용 6**이다(아래 **(c-1)**).
- 🟡 **잔존**: `dashboard/src/components/notifications/NotificationTof.tsx`의 `cn("… text-caption font-bold", info.className)` **~~1개 병합 지점~~ / 분기 3종**(`text-foreground-secondary` · `text-success` · `text-danger-deep`)에서 **3분기 전부 `text-caption` 소실**을 in-session 재현했다. **8.4의 무변경 대상**이라 본 Set에서 수정하지 않았다. ~~심각도 낮음~~ — caption 15px가 브라우저 기본 16px로 **의도보다 커지는** 방향이다. ~~**수정 여부 = 사용자 판단 대기**(8.4 무변경 대상의 예외 허가 사안).~~ → ✅ **해소 = 아래 (c-1)**.
  - 🔴 **위 서술의 정정 3건 (발견일 = 반영일 = 2026-09-21 PoC-(55), 근거유형 = 실측, 계수 단위 = 정정 건수)**: **①** 잔존은 **1곳이 아니라 4곳 + 변종 2곳**이다(전수는 **(c-1)**). **②** 인용 `info.className`은 **실물과 다르다** — 같은 파일이 `const { label, className, Icon } = derive(tof)`로 **구조분해**한 뒤 `cn(…, className)`을 넘긴다(**값은 같고 이름만 틀린** 인용 오기 — 27.8 인용 계층 계열). **③** **「심각도 낮음」은 4곳 전수 기준에서 성립하지 않는다** — 아래 **C4 · C6은 작아지는 방향**이라 **5060 페르소나(8.3) 기준 등급이 올라간다**. 🔴 **위 「3분기 전부 소실」 실측 자체는 무변경**이며 **취소선 대상이 아니다** — 그 관측은 참이고, 좁았던 것은 **범위**다.
- 🔴 **★ 「≠」 — 클래스가 코드에 있음 ≠ 화면에 적용됨.** `npx tsc -b` / `npx eslint .` / `npm run build` **전부 통과**하고 `ssr-nc`는 **텍스트 노드만** 단언하므로(8.4(f) 한계 ②·④) **검증 4종 중 어느 것도 이 소실을 잡지 못한다**. 현재 검출 수단 = **브라우저 실측** 또는 **`twMerge` 직접 호출** 둘뿐이다.

**(c-1) ✅ (c) 해소 — 근본 원인은 「설정 공백 1곳」이었다 (2026-09-21 PoC-(55) 신설, PR #68 `704dded`, 발견일 = 반영일 = 2026-09-21, 근거유형 = 항목별 병기 — 사용자 결정 / 실측 / 논증, 계수 단위 = 지점 수 / 행 수 / 토큰 종수 / 바이트 — 항목별 병기)**

- **결정 경위 — A안 철회 → B안 (근거유형 = 사용자 결정)**: 먼저 **A안**(위 잔존 1곳만 `text-(length:--text-caption)`으로 치환 — **8.4 무변경 대상의 1토큰 예외**)이 채택됐다. 그러나 착수 전 전수 조사에서 **잔존이 1곳이 아니라 4곳 + 변종 2곳**으로 나와 **A안의 전제가 깨졌고**(§9 정지 1건), 사용자가 **A안을 철회하고 B안**(근본 원인 = **설정 공백 1곳**을 고친다)을 **확정**했다(2026-09-21).
- 🔴 **[실측] 소실·오작동 지점 전수 (계수 단위 = 지점 수)** — `twMerge`를 직접 호출해 `dashboard/src`를 훑었다. **grep으로는 보이지 않는다** — 래퍼 컴포넌트를 거쳐 **다른 파일의 베이스 클래스와 합쳐지는** 형태이기 때문이다.

  | ID | 지점 | 증상 | 방향 |
  |---|---|---|---|
  | C1 | `NotificationTof` 뱃지 **3분기** | `text-caption` 소실 | 커짐 |
  | C2 | `HelpPage` 화재 카드 `CardTitle` | `text-h3` 소실 | 커짐 |
  | C4 | `OnboardingModal` `DialogDescription` | 베이스 `text-sm`(14px)이 이겨 `text-body`(17px)가 짐 | 🔴 **작아짐** |
  | C6 | `NotificationImage` `Badge` | 베이스 `text-xs`(12px)가 이겨 `text-caption`(15px)이 짐 | 🔴 **작아짐** |
  | 변종 C3 | `OnboardingModal` `DialogTitle` | `text-lg` + `text-h2` **동거**(충돌 미해소) | — |
  | 변종 C5 | `HelpTooltip` `PopoverContent` | 베이스 **색** `text-popover-foreground` 소실 | — |

- **[실측] 구현 = `dashboard/src/lib/utils.ts` 1파일 / +24 −1, 호출부 0줄**: `twMerge`를 `extendTailwindMerge` 인스턴스(**모듈 레벨 1회 생성** — 호출마다 만들면 내부 LRU 캐시가 무력화된다)로 바꾸고, 전용 클래스 그룹 `text-size-token`에 `index.css`의 `--text-*` **6토큰**(`display` · `h1` · `h2` · `h3` · `body` · `caption`)을 등록해 stock `font-size`와 **양방향 충돌**로 묶었다(뒤에 온 쪽이 이긴다).
- 🔴 **[실측 + 논증] 기본 `font-size` 그룹에 넣지 않은 이유** — 그 방식(= `theme.text` 편입)은 **악화 방향 차이 10건**을 냈다. 원인 = `conflictingClassGroups`의 **`'font-size': ['leading']`**. Tailwind v4의 stock `text-lg` 류는 line-height를 함께 내보내므로 앞선 `leading-*`을 덮는 것이 맞지만, **우리 토큰은 `--text-*--line-height` 부속 변수가 0개**라 line-height를 내보내지 않는다 ⇒ **거짓 충돌**이고 `CardTitle`의 `leading-none`이 **10곳에서 지워진다**. ★ **위임이 지정한 방식 그대로 넣었으면 악화 10건**이었다 — **학습 16 「불변식 유지 + 메커니즘 등가 치환」**(불변식 = 커스텀 토큰 존속 · 호출부 0줄 · 악화 0).
- **[실측] 검증 (계수 단위 = 행 수 / 토큰 종수 / 바이트)**: 전역 차이표 **28행 중 차이 8 · 악화 0** / `dashboard/src` 문자열 리터럴에서 뽑은 클래스 토큰 **677종**을 stock 색 · 크기 · 굵기 · 자간 클래스와 짝지어 before · after 분류를 대조한 결과 **바뀐 토큰은 위 커스텀 6개뿐**이다 ⇒ **표 밖의 모든 병합 지점은 구성적으로 차이 0** / negative control **NC-1**(등록 목록에서 `caption`만 제거 → 차이 **8 → 4**로 되돌아감) · **NC-2**(같은 토큰을 `font-size`가 아닌 **색 그룹**에 등록 → 차이 **0**, 결함 그대로) **전건 검출** / `lint` · `build` · `ssr-nc` **전건 exit 0** / `dist/assets/*.css` **55,828 B로 전후 동일**(해시까지 동일 — `tailwind-merge`는 런타임 전용이라 기대한 결과).
- ⚠️ **[실측 catch] 주석도 CSS 산출에 영향을 준다**: 초고에서 CSS가 **+23 B** 늘었다. 주석에 쓴 낱말 `inline`을 Tailwind 스캐너가 유틸리티 후보로 잡아 `.inline{display:inline}` 한 줄이 생긴 것이며 **주석 어휘를 바꿔 해소**했다.
- ⚠️ **[실측 — 학부생 브라우저, 계수 단위 = 측정 지점 수] 브라우저 실측은 C2 1곳뿐이다**: DevTools Computed `font-size` = **18px**(도움말 화재 카드 제목). 🔴 **C1 · C3 · C4 · C6은 미측정**이다 — **「4곳 전부 브라우저에서 확인됐다」로 읽지 말 것.**
- 🟡 **[신규 미결] 커스텀 토큰 목록이 두 곳에 있고 자동 가드가 없다 (발견일 = 반영일 = 2026-09-21, 근거유형 = 실측, 계수 단위 = 토큰 수)**: `dashboard/src/index.css`의 `--text-*` **6개**와 `dashboard/src/lib/utils.ts`의 `TEXT_SIZE_TOKENS` **6개**가 **따로 존재**하고, 어긋나도 경고하는 **자동 가드가 없다**(주석에 명시했을 뿐). 토큰을 추가·삭제하면 **두 곳을 같이** 고쳐야 한다 ⇒ **드리프트 위험**(27.8(m)⑤ 계열). 🔴 **처리 방침 미확정 — 해소책을 적지 않는다.**
- **[실측] 잔존 한계 (전건 명기)**: **①** `ssr-nc`는 `className`을 검증하지 않는다(**8.4(f) 한계 ②** — 텍스트 노드만 단언) ⇒ **이 결함 계열은 이 하네스로 도달 불가**다 **②** 검출 수단은 여전히 **브라우저 실측** 또는 **`twMerge` 직접 호출** 둘뿐이다(위 「≠」 **무변경**) **③** 🔴 **PR #57의 `text-(length:--text-*)` 우회 6곳은 그대로 둔다** — 이 설정과 무관하게 동작하며 **정리 대상이 아니다**(한 번에 한 변수).

**(d) 🟢 랜딩 카카오톡 재현의 연출 고지 (근거유형 = 실측 grep 대조)**

- **말풍선 문구는 실물 인용이다** — `LandingPage.tsx`의 `🔔[띵동] 초인종이 울렸어요.` / `🔔[띵동] 초인종 — 방문자 사진`이 `server/app/constants.py`의 `PRIMARY_MESSAGES["doorbell"]` / `SECONDARY_FEED_TITLES["doorbell"]`과 **문자 일치**(grep 대조). ⚠️ 단 이 두 카피는 constants.py 주석이 밝히듯 **확정 카피가 아니다**(7.1은 화재경보만 확정) — 랜딩은 **현재 잠정값을 인용**한 것이다.
- ⚠️ **정렬만 연출이다**: 실제 카카오 memo(나에게 보내기) 경로는 **본인 발신 = 오른쪽 정렬**인데 랜딩은 **수신형 = 왼쪽 정렬**로 그렸다. 화면에 고지 문구를 넣어 두었다 — *"말풍선 문구는 서버가 실제로 보낸 것입니다. 사진 자리만 그림으로 대신했고, 실제 카카오톡에서는 「나와의 채팅」 오른쪽에 붙어 옵니다."*(실물 인용). 카카오 로고·브랜드 자산은 **미사용**(상표).
- 🔴 **★ 향후 이 화면을 「실물 근거」로 인용하지 말 것.** 문구는 실물이나 **레이아웃은 재현**이다 — 27.8 「출처 계층 착각」이 노리는 함정을 **우리가 스스로 하나 더 만든 셈**이라, 인용할 때는 계층(문구 = 실물 / 배치 = 연출)을 반드시 밝힌다.

**관련**: 8.3(접근성 규약 · 모션 · 페르소나) / 8.4((f) 하네스 한계 ②④ · 무변경 대상 목록 · 표시 결함 계열) / 8.6(f)(어휘 재사용 감수 — 같은 축) / 7.1·7.6(확정 카피 · 2차 사진 feed) / 26.10((a) 등록 기능 부재 = (a) 1차 정정의 입력) / 33.5(USP 2층 — 랜딩 콘텐츠 순서 근거) / 카테고리 3(G12 · 클래스별 ToF 정책) / 카테고리 29.5(용어 컨벤션 「초인종」)


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
  - ⚠️ **Stage B 미결 유지**: ~~Motion Indicator(`vl53l5cx_motion_indicator_init` 등) 실구현·④런타임 미착수.~~ ~~`VL53L5CX_DISABLE_MOTION_INDICATOR` 매크로가 `.pio/libdeps/` 내부라 클린 빌드 시 원복되는 문제(재현 방법 확정 선행)는 `tof_test.cpp` 주석에 각인된 상태로 존치.~~
    - ✅ **무효 확정 (2026-08-12 PoC-(36)) — 매크로 원복 문제는 유령이었음**: Motion Indicator는 라이브러리 기본값으로 활성이며 매크로 패치는 불필요. 클린 빌드로 원복될 대상 자체가 없음. 본 미결 항목은 무효.
      - 근거 (전체 3개 ref 전수 확인 — 학습 13): ① `sparkfun/SparkFun_VL53L5CX_Arduino_Library`의 **v1.0.3 / main / master 3개 ref 모두** `src/platform.h:121`이 `// #define VL53L5CX_DISABLE_MOTION_INDICATOR`(주석 상태)로 배포 ② 로컬 파일 sha256 = `c061451cdd498746659cbb8e5519a930b5ab77a00298295d4e83f0ac63ce09d9` → 업스트림과 바이트 동일 = 무수정 확인 ③ `platform.h:118~121`은 옵션 disable 매크로 4종이 **전부 주석 상태**인 블록 = SparkFun 기본값이 전 기능 활성.
      - ★ **발원 ≠ 반영 분리**: 발원 = 2026-07-09 판정 B의 "매크로 주석처리로 컴파일 활성" 표현이 **관찰 서술**(이미 주석돼 있어 활성)인데 **행위 서술**(우리가 주석처리함)로 오독되어 2026-08-08에 "클린 빌드 원복 리스크"로 파생 / 반증·문서 반영 = 2026-08-12.
      - ★ **학습 21 신설 (2026-08-12)**: **미결 항목 자체가 유령일 수 있다 — 등재된 미결도 실물(코드·라이브러리·ref) 검증 대상**. 등재된 ⚠️ 미결이라고 존재를 전제하지 말고, 취소선 처리 전 실물로 재현 가능한지 먼저 확인. (SSoT 학습 번호: 18=PR 웹 머지 후 로컬 main pull / 19=근본원인 진단 재검증 / 20=원격 브랜치 `git ls-remote`(카테고리 20) / **21=미결도 유령일 수 있다**)
    - ✅ **실구현 착수 (2026-08-12 PoC-(36), PR #36 `84f2272`, 브랜치 `feat/firmware-tof-stage-b-1`, 3파일 +97줄)**: Stage B-1 **계측 계층**(관측 전용) 실코드화 + ④런타임 실측 완료 — 상세 = **9.3**. presence 판정 무융합·임계값 미하드코딩. (판정 융합·임계값 확정 = B-2 소관 미결)
    - 🆕 **[차단 사유 stale 판정 — 발견일 = 반영일 2026-09-20 PoC-(54), 근거유형 = 실측 코드 대조] 위 취소선 문장은 실물보다 낡았다.** 🔴 **미결 자체는 유지된다 — 닫지 않았다.**
      - **[실측] `initToFMotionIndicator()`는 완전 구현돼 있다** — `firmware/src/tof_common.cpp`(선언 = `firmware/include/tof_common.h`). `vl53l5cx_motion_indicator_init(tofImager.Dev, &motionConfig, VL53L5CX_RESOLUTION_8X8)` → `vl53l5cx_motion_indicator_set_distance_motion(..., TOF_MOTION_DIST_MIN_MM, TOF_MOTION_DIST_MAX_MM)` → `status == VL53L5CX_STATUS_OK` 분기 → **실패해도 Stage A는 계속**(반환값은 로깅용, `initToF()`를 죽이지 않음). 호출부는 같은 파일 `initToF()` 내부다.
      - **[실측, 계수 단위 = env 수] `platformio.ini`에서 `+<tof_common.cpp>`를 편입한 env는 5개**다 — `tof_dummy` · `mic_uplink` · `mic_noiseprobe` · `camera_probe` · `enrich_uplink`. ⇒ **빌드 대상 밖 코드가 아니다.**
      - **[실측] 대조군 = 같은 grep이 제품 코드와 다른 2계층을 별개로 잡았다** — 라이브러리 원본(`firmware/.pio/libdeps/*/SparkFun VL53L5CX Arduino Library/src/vl53l5cx_plugin_motion_indicator.{h,cpp}` 등)과 호스트 테스트 스텁(`firmware/tools/host_stubs/vl53l5cx_plugin_motion_indicator.h`). ⇒ **도구 생존이며 제품 코드 · 라이브러리 · 스텁을 혼동하지 않았다.**
      - 🔴 **★ 같은 절이 스스로 반증하고 있었다** — 바로 위 `✅ 실구현 착수 (2026-08-12 PoC-(36))` 줄이 **B-1 계측 계층 ④런타임 실측 완료**를 이미 적는다. ⇒ **2026-08-12에 반증된 문장이 문장만 그대로 남았다**. 27.8(m)⑤ 「같은 사실을 두 문서가 다르게 적는 드리프트」의 **절 내부 판**이다(계수 단위 = 드리프트 건수 1).
      - 🔴 **[위임 전제 오류 catch — 학습 19, 근거유형 = 문서 인용]** 본 갱신을 지시한 위임은 *「실제 잔존 축 = Stage B-2 판정 융합·임계값 확정이며 그중 임계값은 사용자 판단」*이라 적었으나 **실물 SSoT와 어긋난다** — **9.4**가 **2026-09-02 PoC-(38) PR #39 `a0953fb`**로 B-2 판정 계층을 실코드화하며 `TOF_MOTION_NDET_MIN = 1` · `TOF_MOTION_LATCH_FRAMES = 75`를 **채택 확정**했고 **④런타임 실측(9.4(d))까지 마쳤다**. ⇒ **「B-2 판정 융합·임계값 미확정」은 현재 사실이 아니다.**
      - ⇒ **[논증, 입력 = 9.4(e) · 9.3(G)] 실제 잔존 축은 검증 축이다** — ① **9.4(e) 프로토콜 ②(정지 사물 대조) 미수행**(n=1 부분 데이터만 존재, 「프로토콜 ② 미수행」 표기 유지) ② **9.3(G) 벽면 실사용 정확도 미측정**. 둘 다 **보드 · 현장 의존**이다. 🔴 **본 항은 두 축의 대응 방향을 적지 않는다.**

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

**(e) ⚠️ 미충족 항목 — 프로토콜 ②(정지 사물 대조) 미수행**: 9.3(H) 하위 원칙("동일 위치 대조")이 요구하는 3종 프로토콜 중 ②를 이번 ④런타임 세션에서 수행하지 못했다. 사유 = 센서 시야 가장자리 오염(near가 2~8/64로 상시 낮게 뜨고 center는 대부분 `n/a`)으로 유효한 대조군(정지 사물)을 확보하지 못함. → **본 절은 부분 충족**. Stage B-2 **구현·③컴파일·④런타임(사람 자극 경로) 완료 ≠ Stage B 검증 완료.** **[단서, PoC-(45) 문서 반영] 프로토콜 ② 첫 데이터 (n=1, 2026-09-11 PR #53 댓글)**: 정지 사물(책 ≈440mm) 정지 약 8초간 fused **PERSON 유지**. 정지 중 `ndet` 1~2/16 간헐 → `TOF_MOTION_NDET_MIN=1`이 latch를 재충전하는 것으로 **추정(가능성 높음, 논증)**. ⚠️ **판정 변경 없음** — n=1 부분 데이터라 향후 판정 PR 후보로만 남긴다. 프로토콜 ② **미수행** 표기는 유지.

**(f) ★ 위임 전제 오류 2건 (학습 19, 실코드 대조로 catch)**:
① `presence_state`는 `tof_common.cpp`가 아니라 `tof_test.cpp`의 `tofTask` 내부 `static bool`이다(`firmware/src/tof_test.cpp:67`).
② `motion_indicator`는 (B-1 로그 블록의) 15프레임 게이트 안에서만 읽히므로, B-2는 그 값을 재사용하지 않고 **매 프레임 독립적으로 다시 참조**한다(`firmware/src/tof_test.cpp:188`, B-1 블록 이동 없이 우회).
③ **판정 로직 `tof_common.cpp tofJudgeFrame()`로 승격 (2026-09-11 PoC-(45) Set 1, PR #53, 근거유형 = 실측)**: ①이 지적한 위치(`tof_test.cpp` 내부)에서 함수로 순수 이동 — 정규화 후 코드 줄 diff **0**(주석만 9줄 교체). 호스트 테스트 `tofJudgeFrame: 196 checks OK`(9 groups). negative control 4종(디바운스 프레임 수 / latch 프레임 수 / 대조존 개수 / AND→OR 치환) **전건 검출**. `tof_dummy` RAM 20,124→20,132B(+8) / Flash +120B.

**관련**: 9.3(d)-3(산술 오기 정정) / 9.3(F)(방향 예고) / 9.3(H)(동일 위치 대조 원칙, 본 절 (e)가 부분 충족 사례) / 학습 19(위임 전제 재검증)

---

## 카테고리 10: Git Convention

- 모든 commit 메시지는 **한국어**로 작성
- 형식: `{이모지} {Type}: {한국어 설명}`
- 사용 가능한 Type 14종은 `docs/git-convention.md` 참조
- 예시: `✨ Feat: camera_test.cpp 골격 추가`
- ~~🟡 **[신규 미결] 커밋 이력에 규약 14종 이탈 2건 (발견·문서 반영 2026-09-08 PoC-(42), 근거유형 = 실측 `git log`)**~~ → **✅ 해소 (결정 2026-09-19 PoC-(54), 근거유형 = 사용자 결정)**: `🧪 Spike`(`086c6da`, PR #23) 1건 / `🎨 Style`(`3544db4`, PR #8) 1건 — 둘 다 `docs/git-convention.md` **14종에 없는 타입**이다. **과거 이력이라 소급 정정 대상은 아니다**(이력 훼손 금지). ~~판단 필요 = 이 2종을 `git-convention.md`에 **추가할지**, 이탈로 남길지.~~ **→ 확정: 규약 14종에 추가하지 않고 이탈로 남긴다**(결정 주체 = **사용자**, 결정일 = **2026-09-19**, 근거유형 = **사용자 결정**). 근거 3 = ① 14종도 이미 많아 분류 비용이 이득을 넘는다. ② `Spike`는 `Feat`으로, `Style`은 **이미 존재하는 `Design`**으로 흡수된다 — 규약 부족이 아니라 오용이었다. ③ 과거 이탈에 맞춰 규약을 넓히면 "이탈하면 규약이 따라온다"는 선례가 생긴다. **소급 정정 없음**(이력 훼손 금지 — 과거 커밋 메시지 무접촉). **파생 확정: UI 시각 변경의 Type은 `Design`이다**(`Style` 아님). ⇒ 추가하지 않기로 한 결정이므로 `docs/git-convention.md`는 **무변경**(본 회차 무접촉).
  - ※ 실물 14종 = 🎉 Start / ✨ Feat / 🐛 Fix / 🎨 Design / ♻️ Refactor / 🔧 Settings / 🗃️ Comment / ➕ Dependency / 📝 Docs / 🔀 Merge / 🚀 Deploy / 🚚 Rename / 🔥 Remove / ⏪ Revert. ⚠️ **`✅ Test`는 규약에 없다.**

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

🆕 **[잠정안과 어긋나는 물리 사실 2건 — 2026-09-18 PoC-(52) 등재, 근거유형 = 실측 설치 파일 대조]** 위 잠정안은 **2026-05-12 시점의 안(案)**이며 값 자체가 틀린 것이 아니다(취소선 대상 아님). 다만 통합 전에 아래를 **입력으로 받아야** 한다.

- 🔴 **카메라 DMA 태스크는 Core 0에 붙는다** — 설치 sdkconfig에 **`CONFIG_CAMERA_CORE0=y`**가 박혀 있다. ⇒ 위 잠정안의 「Core 1: cameraTask」와 **어긋난다**. 본 값은 **프레임워크 기본 설정**이지 우리 코드의 선택이 아니다. ⚠️ **코어 분배 재확정은 본 Set 범위 밖**이며, 여기서는 **물리 사실만** 등재한다.
- **Arduino `loopTask`는 Core 1 · priority 1 · stack 8192 B로 생성된다**(`cores/esp32/main.cpp` + sdkconfig `CONFIG_ARDUINO_RUNNING_CORE=1`). ⇒ 6.3(m)의 「POST는 loop 태스크에서」와 6.5의 「신규 태스크 0개」 권고는 위 잠정안의 **「Core 1 = camera + wifi」를 태스크 이름 없이 이미 만족**한다(근거유형 = 논증, 입력은 위 실측).
- ⇒ 두 사실을 합치면 **카메라(Core 0) ↔ 업로드(Core 1)가 갈려 있고**, 마이크·ToF의 코어 배치(6.3(n) m4 실측에서 Core 0 ↔ Core 1 대조)와 함께 읽어야 한다. 관측 실물 = **6.6**.

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
- **⚠️ env:poc `build_src_filter` blacklist 회귀 (2026-06-22 PoC-(17) catch)**: `[env:poc]`는 blacklist 방식(`+<*>` 후 camera만 제외)이라, **5/10 mic_test / 5/11 tof_test 추가 후 각자의 `setup()`/`loop()`가 poc 빌드에 흡수 → multiple definition 링크 충돌**. 5/8 이후 poc 미재빌드로 잠복하다 6/22 부팅 검증에서 발현. 1차 검증은 `PLATFORMIO_BUILD_SRC_FILTER` 환경변수 override로 mic/tof 제외 후 우회 빌드(파일 0 수정). ~~**근본 수정 = whitelist 통일 별도 위임 (카테고리 27.6 / DB3 등록 예정)**~~ → **✅ 정정 (해소 PR #4 `c4c8f47` / 발견 2026-09-02 세션 / 문서 반영 2026-09-02)**: 근본 수정은 **이미 완료돼 있었다**. 2026-09-02 `firmware/platformio.ini` 실물 조회 결과 **실존 env 9개 전부 whitelist**(`-<*>` 선행) — `poc` / `camera_v1` / `camera_v2` / `mic_dummy` / `tof_dummy` / `upload_spike` / `upload_spike_tls` / `tof_pinscan` / `tof_lineprobe`. "별도 위임 예정" 서술은 3개월간 잔존한 **stale**(27.6은 6/22 시점에 이미 ✅ 완료 기록). ★ **학습 21 3회차**(등재된 미결도 실물 검증 대상 — 8/12 매크로 유령 → 9/02 poc blacklist). **[단서, PoC-(45) 문서 반영] 위 "9개"는 2026-09-02 시점 이력값** — ~~현재값(2026-09-11)은 `mic_uplink`(PR #52) + `mic_noiseprobe`(PR #54) 추가로 **11개**(`grep -c '^\[env:' firmware/platformio.ini` 실측).~~ → ~~**[현재값 갱신 2026-09-18 PoC-(52), 근거유형 = 실측 + 문서 인용]** `camera_probe`(PR #63 `41cd6e2`) 추가로 **12개**이며, 신설 블록은 **추가만**이고 `platformio.ini` **삭제 줄 0**·기존 11개 env 무수정이다(상세 = **6.6**).~~ → **[현재값 갱신 2026-09-18 PoC-(53), 근거유형 = 실측 + 문서 인용]** `enrich_uplink`(PR #64 `d093d70`) 추가로 **13개**(`grep -c '^\[env:' firmware/platformio.ini` 실측)이며, 신설 블록은 **추가만**이고 `platformio.ini` **삭제 줄 0**·기존 12개 env 무수정이다(상세 = **6.7**). 위 2026-09-11 「11개」·2026-09-18 PoC-(52) 「12개」는 **각각 그 시점 이력**이다. 이력 서술("9개 전부 whitelist") 자체는 그 시점 사실이라 무변경.

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
  - 🆕 **[입력 확보 — 2026-09-18 PoC-(52), 근거유형 = 실측, 계수 단위 = 캡처 시도 수]** `env:camera_probe` ④런타임에서 **WiFi 연결(`st=3`) 상태로 카메라를 연속·주기 구동**해 **60창 누적 `try` 3,563 = `ok` 3,563**, **`nul` 0건**이었다. ⇒ **본 환경·본 조건에서는 「WiFi join 후 `fb_get` fail」이 재현되지 않았다.** ⚠️ **「issue가 없다」가 아니다** — 조건(해상도 QVGA·VGA / `fb_count=2` / PSRAM fb / 핫스팟 1대)이 한정돼 있고 **전원 레일 미관측**이다. 32.2의 「카메라 단독에선 미발현」에 **WiFi 동시 구동 축이 추가**된 것까지가 본 관측이다. 상세 = **6.6(c)**.
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

### 17.2 검증 자산 전건 베이스라인 — HEAD `601e7a2` (2026-09-19 PoC-(53) 신설, 발견일 = 반영일 = 2026-09-19, 근거유형 = 실측 전건 — 일부 논증은 항목별 병기)

> **용도** = 다음에 무언가 깨졌을 때 「언제부터」를 이분 탐색하지 않기 위한 기준점. 노트북 단독 · **보드 무접촉(`-t upload` 0회)** · repo 쓰기 0 · 데이터셋 쓰기 0 · 외부 API 0 · 서버 기동 0. 로그 원본 = repo 밖 `~/ddingdong-측정결과/2026-09-19/baseline_601e7a2.log`(`.gitignore` 차단분 — SSoT엔 요약만, 본 등재 시 **전문 대조**). 17.1이 2026-05의 **정적 budget** 검증이라면 본 절은 2026-09의 **검증 자산 전건 실행** 기록이다.

**결과 = 실패 0 / SSoT 불일치 0 / 데이터셋 무변경.** 기준값 대조 = 7.5(i) **106** / 6.3(o) **90 · 97 · 46 · 61 · 196** + assert **13** / 카테고리 16 env **13** — **전건 일치, 갱신 대상 없음.**

- **서버 (계수 단위 = 테스트 메서드 수)**: `venv/bin/python3 -m unittest app.tests.test_detect_regression` → **`Ran 106 tests in 0.302s` OK**(7.5(i) 일치). 소켓 가드 코드 확인 = `setUpModule`이 `connect` / `connect_ex` / `create_connection` **3개 교체** + `_NoNetworkTestCase` 상속 전수 검사 + `NetworkGuardSelfTest` **2건 실존**(30.9 부분 해소 블록). ⚠️ **「테스트 OK ≠ 외부 호출 0」** — 패킷 계측 미수행, 실제 송신 0은 **논증**.
- **대시보드 4종 한 세션 전건 = 첫 기록**: `npm run lint` exit 0 / 1.63s / 경고 0 · `npm run build` exit 0 / 1.87s / 경고 0(= `tsc -b && vite build`, **2460 모듈**) · `npm run ssr-nc` exit 0 / 1.71s / **baseline 통과 + NC 4종 전건 검출**(계수 단위 = **NC 케이스 수 4** — 실패 단언 8건은 **다른 단위, 더하지 말 것**). ⚠️ **`tsc` 단독 스크립트 키는 없다**(`scripts` = dev / build / lint / preview / ssr-nc **5키**) — build가 포함형이라 생략(8.4(f) 환경 사실 ②). `ssr-nc` 실행 전 `git status --porcelain` 빈 출력 확인(8.4(f) 환경 사실 ①).
- **펌웨어 호스트 테스트 6종 동시 실행 = 첫 기록 (계수 단위 = checks 수)**: `enrich_wire_test` **90** / `camera_probe_test` **97** / `noise_modes_test` **46** / `noise_stats_test` **61** / `tof_judge_test` **196**(9 groups) — **6.3(o) 전건 일치**. `jsonpeek_test` = **5 groups OK, checks 카운터 없음, 정적 `assert` 13**(🔴 **계수 단위가 다르다 — 위 5종과 더하거나 비교하지 말 것**). 컴파일 경고 0(전건 `-Wall`) / 산출물 `/tmp` = repo 밖. 🔴 `jsonpeek_test`는 **컴파일 명령이 파일에 없어 유도값(논증)으로 돌렸다** — 6.3(o) 보강 참조.
- **firmware 13 env 동시 빌드 = 첫 기록 (계수 단위 = env 수)**: **13 / 13 SUCCESS · 경고 0 · `-t upload` 0회**. RAM% · Flash% = `poc` 13.8 · 25.8 / `camera_v1` 7.0 · 9.4 / `camera_v2` 7.0 · 9.4 / `mic_dummy` 8.1 · 8.2 / `tof_dummy` 6.1 · 11.2 / `upload_spike` 13.5 · 22.2 / `upload_spike_tls` 13.8 · 25.9 / `tof_pinscan` 5.8 · 8.1 / `tof_lineprobe` 5.7 · 7.7 / `mic_uplink` 16.6 · 26.1 / `mic_noiseprobe` 9.8 · 11.8 / `camera_probe` 18.4 · 26.0 / `enrich_uplink` 17.9 · 27.7(카테고리 16의 env 13개와 일치 — 16.1 표는 2026-05 시점 이력이라 무변경).
  - 🔴 **경계 2건 (반드시 병기)**: ① **「빌드 SUCCESS ≠ 동작 검증」** — 컴파일 · 링크 · 메모리 점유만 증명, 보드 런타임 0 ② **13건 전부 증분 빌드**(0.55~2.52초, `.pio/build` 캐시 재사용) — **clean 빌드 관통은 미검증**.
- **ml**: PR #60 fail-fast 관측 = `env -u DDINGDONG_DATA_ROOT` → **`ValueError`**(「데이터 루트가 지정되지 않았습니다 — 기본값 fallback 은 의도적으로 없습니다.」, 5.2(a) · 33.8 일치) / `test_dtw_contract` **`Ran 19 tests` OK**(skip 1 = librosa 부재 시 skip 설계) / `test_export_smoke` 전체 통과(serving out=(1,3) sum≈1.0000, classes=`['doorbell','knock','fire_alarm']`) / `test_pipeline` **5 / 5** / `test_training_smoke` **1 / 1**.
  - ⚠️ 뒤 2건은 1차에서 **§9 정지**했다가 **사용자 확정(2026-09-19) 후 실행**했다. 판정 근거 = 두 테스트 모두 `TemporaryDirectory` + `make_dummy_dataset`로 루트를 만들고 `resolve_paths(root)`에 **명시 인자**를 전달하며, 우선순위 = **명시 인자 > env** ⇒ **실데이터셋 도달 경로가 코드상 없다**. `env -u`로 `DDINGDONG_DATA_ROOT`를 걷어낸 상태로 실행(이중 안전장치). 🔴 위임의 「`run_all` 금지」는 **대상을 안 적어 과잉**이었다 — 불변식은 「실데이터셋 무변경」이고 `run_all` 금지는 그 **수단**이었다(**27.8(o)④**).
- 🔴 **데이터셋 무변경 증명 (학부생 직접 재확인 2026-09-19 13:23, 근거유형 = 실측)**: `02_preprocessed` files=**2793** mtime=**Jul 1 12:34:21 2026** / `03_augmented` files=**9656** mtime=**Jul 1 12:34:33** / `05_final_dataset` files=**12447** mtime=**Jul 1 12:34:46** — **실행 전후 동일 + mtime이 7월 1일 그대로** = 파이프라인 재실행 흔적 0. ※ `02` · `03`의 파일 수는 `.DS_Store` 포함이라 SSoT(33.7)의 2792 / 9655와 **1씩 다르고**, `05`는 12447로 **일치**한다(계수 단위 차이, 결함 아님 — 로그 요약줄의 「1씩 다르다」는 `05`에는 해당하지 않는다).
- **이번이 첫 기록인 것 (계수 단위 = 자산)**: firmware 12 env(`mic_dummy` 제외) / 13 env 동시 빌드 / 호스트 6종 동시 실행 / 대시보드 4종 한 세션 전건 / ml 4종 PR #60 이후. ⚠️ **학습 21** — 「첫 기록」은 **「SSoT에 실행 기록이 없다」**는 뜻이지 **「아무도 돌린 적 없다」가 아니다**. 본 절은 기록을 만든 것이지 과거를 판정한 것이 아니다.
- 🔴 **이 베이스라인이 증명하지 않는 것 (한계 전건)**: ① 빌드 SUCCESS ≠ 동작 검증(보드 런타임 0) ② 증분 빌드만 — clean 빌드 관통 미검증 ③ 테스트 OK ≠ 외부 호출 0(패킷 계측 미수행, 논증) ④ ssr-nc 한계 4가지 승계(8.4(f) — CI 미연결 · 텍스트 라벨 전용 · 실 브라우저 CSS 미검증 · 렌더 대상 밖 도달 불가) ⑤ `jsonpeek_test`는 NC 불가(6.3(o), 본문 복사) — exit 0은 복사본이 통과했다는 뜻 ⑥ 실모델 미검증(`gate_axis_sweep` 실스윕 · `--self-test` 모두 미실행, `venv_real` 미사용) ⑦ ml 파이프라인 **실데이터 관통 미검증**(전처리 결정성 · 33.7 md5 기준값 · `05` test 424 구성은 여전히 논증) ⑧ 외부 API · 서버 기동 · 터널 0 — end-to-end 체인 미검증 ⑨ `jsonpeek_test` 컴파일 명령은 유도값(논증).

**관련**: 7.5(i)(회귀 106 — 기준값) / 6.3(o)(호스트 테스트 6종 — 기준값 · `jsonpeek` 컴파일 명령 부재) / 카테고리 16 · 16.1(env 13개 · 2026-05 RAM/Flash 이력표) / 8.4(f)(ssr-nc 한계 · 환경 사실 2건) / 33.8(PR #60 fail-fast) / 33.7(데이터셋 파일 수 기준값) / 30.9(소켓 가드 · `NetworkGuardSelfTest`) / 17.1(정적 budget 검증 — 선행 성격) / 카테고리 20(계측 → 실측 → 판정 · 학습 21) / 27.8(o)④(위임 「`run_all` 금지」 과잉)

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

**⚠️ 한계 + 보강 (발견·문서 반영 2026-09-08 PoC-(42), PR #46·#47, 근거유형 = 실측)**
- 🔴 **`-B`는 `__pycache__` 쓰기를 막을 뿐, 이미 디스크에 있는 `.pyc`를 무효화하지 않는다.** `-B`만 믿으면 **오염된 캐시가 이미 남아 있는 상황**은 여전히 못 막는다 — 위 자산화 문장은 필요조건이지 충분조건이 아니다.
- → **보강 자산화: 변형이 실제로 반영됐음을 `assert 변형본 != 원본`으로 별도 보장한다.** PR #46에서 **NC-6 최초 시도가 바로 이 assert에 걸렸다**(lambda 오작성으로 파일이 실제로는 무변경) → **"무해 변형이 통과했다"는 거짓 결론을 막았다.** 이 assert가 없었다면 위 절이 경고한 **"반대 방향 오염"**(변형 미적용 → 검출 X)을 그대로 밟았을 것이다.
- PR #47은 이를 **4단계로 확장**했다: ① 앵커 매치가 **정확히 1건**인지 확인 → ② 치환 후 **디스크 재독** → ③ `assert 변형본 != 원본` → ④ 복원 후 `assert 복원본 == 원본`.
- ★ **계보 4층 (층을 섞으면 대책이 어긋난다)**: **관측률**(관측 설계) → **불변식 부족**(검증 설계) → **실행 환경**(`.pyc` 캐시) → **변형 적용 자체의 검증**. 네 번째 층은 앞 셋과 달리 "테스트가 무엇을 보는가"가 아니라 **"테스트가 무엇을 보고 있기는 한가"**의 문제다.
- 🔴 **3층(실행 환경)에 언어가 하나 추가됐다 — ESM 모듈 캐시 (발견·문서 반영 2026-09-09 PoC-(44), PR #51 `8d574dd`, 근거유형 = 실측)**: 프론트 SSR NC에서 **재빌드한 같은 경로를 다시 `import`하면 ESM 모듈 캐시가 첫 번들을 반환**해 변형이 미적용된 채 "미검출"이 나온다. `.pyc`가 mtime+size로 무효화를 놓친 것과 **기전은 다르지만 결과는 동형**이고, 방향은 `.pyc` 절이 경고한 **거짓 음성**(= 근거 없이 "가드가 없다"고 결론짓게 만드는 쪽)이다. 차단 = 캐시 버스팅 `import(`${url}?build=${++buildCount}`)`(`dashboard/tools/ssr-nc/run.mjs`).
  - ★ **자산화: 「실행 환경 오염」은 python 전용 현상이 아니다.** NC 하네스를 새 언어·새 런타임으로 옮길 때는 **그 런타임의 모듈/바이트코드 캐시가 변형을 삼키지 않는지**를 먼저 확인한다 — 위 4단계 보장 중 ③(`assert 변형본 != 원본`)은 **디스크**를 보므로 **메모리 캐시는 잡지 못한다**. 디스크가 바뀌어도 로드된 모듈이 옛것이면 ③은 통과한다.

### negative control 함정 예고 = 2회 연속 적중 (발견 2026-09-05 / 문서 반영 2026-09-05, 근거유형 = 실측)

PR #43 NC-3(ToF 부재를 통과로 위장, 6.4(d))과 PR #44 NC-4(발송 순서 뒤집기, 7.6(g)) 둘 다 **실재**했다. 두 경우 모두 **결과만 검사하는 케이스로는 무해**했고, 전용 불변식(응답 3키 동시 고정 / wire 요청 시퀀스 검사)을 설계해야 잡혔다. PR #41·#42의 "지정 변형이 무해했다" 실패 이후 위임에 **"그 변형이 어떤 불변식을 깨는지 함께 적으라"**를 넣은 것이 효과를 냈다. → negative control 설계 시 변형과 **"무엇을 검사하는가"를 짝지어** 명시할 것.

### negative control 미검출의 판정 — 「가드 부재」가 아니라 「도달 불가」일 수 있다 (발견·문서 반영 2026-09-08 PoC-(42), 근거유형 = 실측)

negative control이 **미검출**로 나왔을 때 곧바로 "스위트에 가드가 없다"로 결론짓지 않는다. 2026-09-08 세션에서 미검출 2건이 나왔고 **둘 다 결함이 아니었다**.

- **PR #46 NC-6 (판정 = 스위트 무죄)**: `fire_alarm` 분기를 ToF 거부 분기 **뒤로** 옮기는 변형이 **무해**했다 → **스위트가 필요 이상으로 구속하지 않는다는 증거**로 판정. 그 순서는 결과에 영향이 없는 **자유도**다.
- **PR #47 NC-2b (판정 = 변형이 애초에 결함이 될 수 없었다)**: `derive()`의 완료 분기와 실패 분기를 **순수 뒤집는** 변형이 무해했다. 이유 = 서버 데이터에서 **`secondary_sent=true ⟹ photo_sent=true ⟹ secondary_sent_at ≠ null`**이므로 **"완료 분기"와 "실패 분기"가 동시에 참이 되는 상태가 존재하지 않는다** → 순서를 바꿔도 **도달 가능한 입력이 없다**.
- ★★ **#47이 한 층 더 깊다**: #46은 **"스위트가 과잉 구속하지 않는다"**까지였고, #47은 **"위임이 지정한 변형이 도달 가능 입력에서 결함이 될 수 없었다"**를 **도달 가능성으로 증명**했다. 그래서 **금지 상태를 실제로 만드는 변형을 NC-2로 재규정**하고, 순수 순서 뒤집기는 **NC-2b로 분리**했다 — 위임 지정 변형을 그대로 세지 않고 **다시 설계한 것**이 판정을 가능하게 했다.
- ★ **원칙**: negative control이 미검출일 때 "가드가 없다"로 결론짓기 전에 **(1) 도구가 살아 있는가**(변형이 실제로 적용됐는가 — 위 `python3 -B` 절의 4단계) **(2) 그 변형이 도달 가능 입력에서 결함이 되는가**를 **먼저** 확인한다. 둘 다 통과한 뒤에야 "가드 부재"다.
- ※ 프론트(TS/React)에도 같은 판정을 적용한 **NC 하네스를 신설**했다 — 방식·한계·미결은 **8.4(f)**에 단일 등재(중복 기술 회피).

### Squash 머지된 브랜치는 `git branch -d`가 거부한다 — `-D` 필요 (발견·문서 반영 2026-09-09 PoC-(44), 근거유형 = 실측)

Squash merge는 원본 커밋들을 **새 커밋 하나로 압축**하므로 git 입장에서 원본 브랜치의 커밋은 main에 **도달 불가**다 → `git branch -d`(안전 삭제)가 "머지 안 됨"으로 **거부**한다. 본 repo는 카테고리 20 「Squash merge 기본」을 쓰므로 **로컬 브랜치 정리에는 `-D`(강제)가 정상 절차**다.
- 실태 = 로컬 브랜치가 **PR #2 시절부터 26개** 누적돼 있었고 2026-09-09 PoC-(44)에서 정리했다. **원격은 GitHub 자동 삭제로 이미 깨끗**했다(`git ls-remote origin | grep -v refs/pull/` = `refs/heads/main` 단일 — 학습 20).
  - 🔗 **[병기 — 2026-09-16 PoC-(50) Set 1 후속]** 위 서술은 **2026-09-09 시점의 실물**이다(취소선 대상 아님). **2026-09-16 PR #62는 머지 후 원격 브랜치가 잔존**했고 **학부생이 PR 화면에서 수동 삭제**했다(타임라인 `head_ref_deleted` **`06:26:03Z`** = 15:26 KST). ⚠️ **repo 설정(Automatically delete head branches) 상태는 미확인**(확인하지 않기로 함)이므로 **「자동 삭제된다」를 전제로 두지 않는다**. ⇒ 운영 = **머지 후 `git ls-remote origin | grep -v refs/pull/`로 확인하고, 남아 있으면 PR 화면에서 삭제**한다. 상세 = **27.8(l)④**.
- ⚠️ **`-D`는 "머지 여부를 확인하지 않는다"는 뜻**이므로, 치는 순간 **미머지 작업도 같이 사라진다**. 안전 절차 = 삭제 전 해당 브랜치의 PR이 **실제로 머지됐는지 PR 번호로 확인**한다(브랜치명만 보고 치지 않는다).
- 🔗 **파급**: 원격 브랜치가 자동 삭제되면 **브랜치 명명 이력이 사라진다** — 카테고리 29.6이 기록한 "브랜치명 관행을 원격에서 사후 검증할 수 없다"의 물리적 원인이 이것이다.

### 외부 과금 API 누출은 「결과 OK」로 검출되지 않는다 — 조용한 가드 금지 (2026-09-16 PoC-(50) 신설, 근거유형 = 실측)

본 절은 **원칙만** 적는다. 사례 본문은 **30.9 부분 해소 블록에 단일 등재**돼 있다(중복 서술 금지).

- **원칙 1 — 조용한 가드 금지**: 제품 코드가 **예외를 삼키는 경로**에서는 **차단(예외)만으로는 검출되지 않는다**. 막은 뒤에도 테스트는 그대로 OK로 끝난다. ⇒ **시도 자체를 기록하고, 기록 1건 이상이면 그 테스트를 FAIL로 승격**해야 한다. **PR #62의 NC-2가 이것을 실물로 재현**했다(실패 판정만 무력화하니 누출 9건이 **조용히 OK**).
- **원칙 2 — 결과(OK)만 보는 검증은 외부 호출 누출을 못 본다**: 단언이 통과했다는 사실은 **무엇을 호출하지 않았는지에 대해 아무것도 말하지 않는다**. ⇒ **외부 과금 API는 한도·콘솔을 관측 장치로 삼은 대조 실험**으로 판정한다 — **서버·터널·클라이언트를 전부 종료**하고 **한 번에 한 변수**만 움직인다(본 카테고리 「계측 → 실측 → 판정」의 적용형).
- **원칙 3 — 코드 읽기로 내린 「무죄」는 호출 수 실측이 아니다**: 가짜 자격증명·스텁을 **읽어서** 내린 판정에 **근거유형을 「실측」으로 적지 말 것**(학습 19). 근거유형은 **코드 확인**이며, 그 판정이 **코드의 어느 범위까지 성립하는지**(예: 어느 절의 테스트에만) 함께 적어야 한다. 범위를 안 적으면 **다음 세션이 전 범위로 읽는다**.
- **정황 (원인 확정 아님)**: **negative control 절차는 baseline + 변형마다 스위트를 재실행**하므로, 누출이 있으면 **NC를 성실히 돌릴수록 증폭된다**. 관측 장치를 세우는 절차가 동시에 **비용을 키우는 경로**일 수 있다는 뜻이다.
- 🆕 **원칙 4 — 관측 축 자체도 조용히 무효화된다 (2026-09-18 PoC-(52) 추가, 근거유형 = 실측 설치 파일 대조, 사례 본문 = 6.6(d) 단일 등재)**: 「부하를 걸었다」는 쪽도 성공처럼 보일 수 있다. 실물 = lwIP `ARP_QUEUEING=1`이 **대상 기기가 없어도 `sendto()`에 성공을 돌려주어** 창 출력이 `tx` 증가 · `txerr=0`으로 정상처럼 보인다. ⇒ **「오류 0」은 「실제로 나갔다」가 아니다.** 원칙 1·2가 *"막았는데 조용하다"*를 다룬다면 본 원칙은 ***"걸었는데 실제로는 안 걸렸다"***를 다룬다 — **거짓 음성 방향**이고, 대조 실험의 **처치군이 비어 있는** 사고다. ⇒ **관측 축을 쓰기 전에 그 축이 실제로 작동하는지 1회 도착 확인**을 절차로 둔다.

### 포렌식 실행 채널은 5개다 — 출력 계수만으로는 캡처형 하네스를 놓친다 (2026-09-17 PoC-(51) 신설, 근거유형 = 실측)

본 절은 **방법만** 적는다. 사례 본문은 **30.9 잔존분 조사 블록에 단일 등재**돼 있다(중복 서술 금지).

「우리가 몇 번 돌렸는가」를 세려면 **아래 5채널을 합산**해야 한다. 어느 하나만 세면 과소 집계가 난다.

| # | 채널 | 무엇을 세는가 | 놓치는 것 |
|---|---|---|---|
| 1 | **명령(CMD)** | 도구 호출 명령문의 실행 문자열 | 스크립트 파일 실행 · 리스트 인자 형태 |
| 2 | **출력(OUT)** | 결과에 남은 `Ran N tests in Ts` | 🔴 **출력 캡처형 하네스** · 읽기 명령의 메아리 |
| 3 | **간접(INDIRECT)** | `subprocess` + `capture_output`으로 **출력을 삼키는 NC 하네스** | 실행 횟수는 스크립트 구조에서 **논증**해야 한다 |
| 4 | **사이드체인(SIDE)** | 같은 기록 안의 사이드체인 줄 **+ 서브에이전트 별도 파일** | 최상위 파일만 훑는 스캔 |
| 5 | **학부생 터미널** | 사람이 직접 친 실행 | 🔴 **셸 히스토리가 담지 못할 수 있다** |

- ★ **원칙: `Ran N tests` 출력 계수는 하한이다.** 2026-09-17 실측에서 채널 2만 셌을 때 09-09는 **부족 12**(채널 4로 해소), 09-08은 **숨은 24~28런**(채널 3)이 더 있었다.
- ★ **부재 판정은 대조군과 함께**(학습 13): 셸 히스토리 `unittest` 0건은 같은 파일의 `python3 -m` 11~20건과 함께 읽어야 「기록 방식의 한계」로 읽힌다 — **「안 돌렸다」가 아니다**.
- ★ **붙여넣기는 독립 실행이 아니다** — 사람 메시지 안의 `Ran` 줄은 같은 날 도구 결과와 `(N, 초)` 쌍이 일치하면 **메아리**로 판정한다.
- ⚠️ **채널을 늘려도 안 덮이는 구간이 남을 수 있다** — 그때는 **「기록 없는 우리 실행」과 「외부」를 가르지 못한다**고 적고 **배제하지 않는다**(30.9 09-15 사례).

### NC 변형 적용 증명에 바이너리 md5를 쓸 수 없다 — macOS clang은 비결정적이다 (2026-09-18 PoC-(52) 신설, 근거유형 = 실측)

- **실측**: **동일 소스를 두 번 컴파일해도 바이너리 md5가 달라진다**(같은 입력 2회 → 서로 다른 해시). ⇒ **md5 상이는 「캐시된 옛 바이너리를 쓰지 않았다」의 증거가 못 된다.**
- **교체 수단** = **전처리 출력(`c++ -E`)의 md5 대조**. 결정적 텍스트이고, **컴파일러가 변형된 헤더를 실제로 읽었는지**를 직접 증명한다.
- ★ **계보상 위치**: 「negative control은 `python3 -B`로 실행」 절이 세운 **4층(변형 적용 자체의 검증)**의 **컴파일 언어 판**이다. 그 절의 4단계 보장 중 ③(`assert 변형본 != 원본`)은 **디스크**를 보므로, 빌드 산출물 캐시는 **또 다른 축**이다.
- ⚠️ **일반화**: NC 하네스를 새 툴체인으로 옮길 때 **「산출물이 결정적인가」를 먼저 확인**한다 — 결정적이지 않으면 산출물 해시는 **판정 근거가 아니라 잡음**이다. 사례 본문 = **6.6(a)**.
- 🆕 **[툴체인 확장 — 2026-09-18 PoC-(53), 근거유형 = 실측] ESP32 크로스 빌드도 비결정적이다 — 다만 「크기」는 유효 신호로 남는다**: `camera_probe` **클린 재빌드 3회**에 바이너리 md5가 **3번 다 달랐고**, 크기는 **867,888 B로 3회 동일**했다. ⇒ 본 절의 macOS clang(호스트) 판정이 **xtensa 크로스 툴체인에도 그대로 적용**되며, **md5는 무효이나 크기·심볼·섹션은 여전히 판정에 쓸 수 있다**. 6.6(a)가 `mic_uplink` 무접촉 증명에 **「md5 · 크기 완전 동일」**을 든 것은 **같은 빌드 산출물을 비교한 경우**(재빌드 아님)라 유효하며, **재빌드를 끼면 md5 항은 떨어져 나간다**. ⚠️ 본 항은 **PoC-(53) 세션의 실측 기록**이고 문서 반영 시점에 `.pio/` 산출물이 남아 있지 않아 **재실행 대조는 하지 않았다**(근거 = 세션 원본 측정).

### 🟡 [관측] MCP 격리 워크트리(`.claude/worktrees/<브랜치>`) 작업 방식 — 최초 관측 + 잔재 (발견 · 문서 반영 2026-09-19 PoC-(53), 근거유형 = 실측, 판정 없음)

- **관측**: 2026-09-19 PR #66에서 MCP가 본 체크아웃이 아니라 `.claude/worktrees/feat+dashboard-faq-copy`에 **격리 워크트리**를 만들고 `dashboard/node_modules` · `server/venv`를 **심볼릭 링크**해 작업했다. 결과는 정상 — 본 체크아웃 `601e7a2` **무변경**, 링크 대상 둘 다 `.gitignore` 차단분, `package.json` 무변경.
- 🔴 **잔재**: 세션이 살아 있는 동안 워크트리가 **lock**되어 `git worktree remove` · `git branch -D`가 **거부**된다(락 사유 = `claude session <브랜치> (pid …)`). 또 **`.claude/`가 `.gitignore`에 없어** `git status`에 **`?? .claude/`**로 뜬다(2026-09-19 Set 1 착수 시점에도 잔존 — `git worktree list` = 본 체크아웃 + `feat+dashboard-faq-copy` `e1df298` **locked**).
- **파급**: **`ssr-nc`는 워킹트리 clean을 요구하므로(8.4(f) 환경 사실 ①) 다음 실행에서 걸릴 수 있다.**
- ⚠️ **이 작업 방식은 SSoT에 등재된 적이 없다** — 지금까지 PR은 본 체크아웃에서 브랜치 전환으로 했다. **본 절은 좋다/나쁘다를 판정하지 않고 관측만 적는다.**
- 🔴 **처리 방침 미확정 = 사용자 판단 대기**(`.gitignore`에 `.claude/` 추가 여부 · 워크트리 정리 시점 포함). 스코프 제외 · §9 대상. 같은 점검의 프로세스 관측 = 카테고리 21 「프로세스 위생」 절.

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
- 🆕 **[점검 기록 — 2026-09-19 PoC-(53), 근거유형 = 실측 `ps`, 계수 단위 = 프로세스 수]** `ps` **21건** 내역 = 데스크톱 앱(`~/Downloads/Claude.app`) 8 + 그 부속 3(`ShipIt` 1 · 고아 렌더러 2) + 당일 Claude Code 세션 9 + 미상 1 — **좀비 아님.** ⚠️ **경계**: 위 「'전부 죽었다'는 계통 원인의 신호」는 **장애 시 의심 항목이지 상시 점검값이 아니다** — 프로세스 수가 많다는 것만으로 좀비를 단정하지 않는다. 같은 점검의 워크트리 관측 = 카테고리 20 「MCP 격리 워크트리」 절.

### 시크릿 파일(`.env`) 편집 위생 (발견 2026-09-05 / 문서 반영 2026-09-05, 근거유형 = 실측)

`echo 'KEY=값' >> .env`를 **파일 끝 개행 확인 없이** 실행해 `KAKAO_REFRESH_TOKEN` 값 뒤에 URL이 이어붙어 **토큰이 무효화**됐다(복구 후 정상 동작 확인). 실측 실행 환경이 파손되면 그 위에서 낸 측정값이 전부 무효가 되므로, 위 「프로세스 위생」과 같은 층의 검증 유효성 문제다.
- **재발 방지 ①**: `.env`에 `>>` 하기 전 `tail -c 1 .env | xxd`로 마지막 바이트가 `0a`인지 확인한다.
- **재발 방지 ②**: `.env` 내용 확인은 `grep -oE '^[A-Z_][A-Z0-9_]*' .env`(키 이름만) 또는 키별 길이 출력으로 한다. **값을 찍는 grep은 시크릿을 화면에 노출한다** — 이 사고에서 리프레시 토큰이 실제로 화면에 노출됐다(값 자체는 본 문서 미기록, 카테고리 7 토큰 항목 원칙 동일).
- 🟡 **[신규 미결] `>>` 추가가 키 중복을 누적시킨다 (발견·문서 반영 2026-09-09 PoC-(44), 근거유형 = 실측 — 키 이름만 확인, 값 미출력)**: `server/.env`의 `DDINGDONG_CAPTURE_URL_BASE`가 **2줄 중복**이다(`grep -c '^DDINGDONG_CAPTURE_URL_BASE' server/.env` = **2**). 원인 = 7.4의 확정 절차상 **터널 재기동마다 새 주소를 `>>`로 덧붙여** 왔기 때문. **동작상 무해**하다 — python-dotenv는 **나중 줄이 이긴다**. ⚠️ 단 **누적되고, "지금 유효한 값이 어느 줄인지"가 눈으로 안 보인다** → 위 재발 방지 ①(개행 확인)과 같은 층의 위생 문제다.
  - **판정 방법** = `grep -c '^<KEY>' .env`가 **모든 키에 대해 1**인지 확인한다(값은 출력하지 않는다 — 재발 방지 ②). **해소 방침 미확정** — 중복 정리는 `.env` 직접 편집이라 위 ① 사고와 같은 위험 구간이므로 **별도 소관**으로 둔다.
  - **[재확인 단서, 2026-09-12 PoC-(46), 근거유형 = 실측 — 키 이름만, 값 미출력]** `grep -c '^DDINGDONG_CAPTURE_URL_BASE' server/.env` = **여전히 2**(3일 경과, 미해소). 동작은 정상(나중 줄이 이김)이며 **본 단서는 값·방침을 바꾸지 않는다** — **해소 방침은 그대로 미확정**이다. ⚠️ 본 세션의 실모델 투입(**33.6(c)**)은 `DDINGDONG_MODEL_PATH`를 **셸 앞 변수로만** 주입해 **`.env`를 건드리지 않았다** — 중복을 더 쌓지 않기 위한 선택이다.
  - 🔴 **[현재값 갱신 — 발견일 = 반영일 2026-09-20 PoC-(54), 근거유형 = 실측(학부생 로컬 셸) — 키 이름만, 값 미출력, 계수 단위 = 줄 수] `grep -c '^DDINGDONG_CAPTURE_URL_BASE' server/.env` = 3.** ⇒ **미결이 정지 상태가 아니라 증가 중**이다(2 → 3).
    - **대조군**: 같은 명령이 나머지 키(`NCP_CLIENT_SECRET` · `NCP_CLIENT_ID` · `KAKAO_REST_API_KEY` · `KAKAO_REFRESH_TOKEN` · `KAKAO_CLIENT_SECRET` 등)에 **전부 1**을 반환했다 ⇒ **「3」은 도구 오작동이 아니다.**
    - 🔴 **값은 출력하지 않았다 — 키 이름만 집계**했다(본 카테고리 위생 규약).
    - ⚠️ **위 2026-09-12 「여전히 2」에 취소선을 걸지 않았다 (MCP 판정, 학습 16 = 기존 컨벤션 우선)** — 그 줄은 **날짜가 박힌 실측 단서**이고 **2026-09-12 시점에는 참**이었다. 이 파일은 **사실인 서술에 취소선을 걸지 않는다**(33.7(d) · 33.6(b) 선례). 바뀐 것은 **현재값**이며 본 항이 그 현재값이다. ⇒ **「2」를 현재값으로 읽지 말 것.**
    - 🔴 **해소 방침은 그대로 미확정**이다 — 본 항은 **현재값만** 갱신하며 **대응 방향 · 정리 방식 신설 0건**이다. 동작은 여전히 정상(나중 줄이 이김)이다.
    - 🔴 **본 repo 밖 · 비추적 파일이라 MCP는 재실행하지 않았다** — 위 실측은 **학부생 로컬 셸 실측분**이며 **33.11이 그 원본**이다.
- ~~🟡 **[신규 미결] `.gitignore` 패턴 폭**: 실측 결과 `.gitignore`는 `.env`와 `.env.local`만 잡고 **`.env.bak`은 잡지 않는다**(백업 파일이 `??`로 추적 시도됨을 확인). 패턴을 `.env*`로 넓히는 것이 안전하나, **본 등재는 기록만이며 `.gitignore` 수정은 별도 소관**이다.~~ **✅ 해소 (2026-09-09 PoC-(43), PR #48 `0d3b498`)**: `.env` / `.env.local` 2줄을 **`.env*` 1줄로 확대**하고 **`!.env.example` 예외 1줄**을 뒀다. ★ **negative control로 양방향 확인** — 더미 `server/.env.bak`이 `.gitignore:38:.env*`로 차단되고, 템플릿 3종(`.env.example` / `server/.env.example` / `dashboard/.env.example`)은 `git check-ignore -v` **미매치 유지**(= commit 대상으로 남는다). 예외를 3줄 쓰지 않은 근거 = gitignore 패턴은 경로 어느 층에서도 매치하므로 1줄이 3파일을 전부 덮는다.

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
- ~~**등록 액션**: 학생이 4개 도어벨 중 1개 선택 → 3~5회 누름 → 시스템이 우리집 초인종 템플릿 저장 (SP/DTW + cosine, 카테고리 4 참조)~~
- ~~**분리 액션**: 미등록 초인종 → 알림 X / 등록 초인종 → 1차 + 2차 알림~~
- ~~**해제 액션**: 대시보드에서 등록 해제 + 다른 초인종 재등록 가능~~
- **★ 축소 확정 — 「ToF presence 단독 시연」 (2026-09-12 PoC-(46) 사용자 결정)**: 위 3개 액션 중 **등록·해제는 시연 범위에서 제외**한다. 진입점 2가 보여주는 것은 **ToF presence에 의한 옆집 초인종 억제**뿐이다.
  - **분리 액션 (현행)**: 우리집 = **소리 + 문 앞 사람 있음**(ToF presence=true) → 1차 + 2차 알림 / 옆집 = **소리만 벽 타고 새어듦, 문 앞 사람 없음**(presence=false) → `tof_rejected`로 **억제**.
  - **근거 3**: ① 33.5 「USP 2층 재정립」이 이미 **"SP/DTW 4종 라이브 단독 시연 = NO"**를 확정했다 ② USP **1층이 ToF presence**라 축소해도 *"옆집 초인종 구분"* 메시지가 **유지**된다 ③ 등록 기능 구현은 **D-18 잔여 일정에서 비현실적**이다.
  - ⚠️ **본문과 하위 note가 반대 방향이던 자기모순의 해소다** — 본문은 여전히 *"SP/DTW + cosine 템플릿 저장"*을 시연 액션으로 서술하고, 바로 아래 note는 *"SP/DTW 단독 시연 NO"*를 가리키고 있었다(발견 2026-09-12). **note가 이긴다.**
  - 🔴 **선행 조건 있음 = 실모델 서버 투입.** 축소된 시연이 성립하려면 **「신뢰도 ≥0.70 doorbell + presence=false → `tof_rejected`」** 경로를 실제로 타야 하는데, 이 경로는 **6.4(g) ④런타임에서 미관측**이고 **현재 서버 기본 기동은 mock ML**이다. 상세 = **26.10(d)**.
  - **감사·미결 상세** = **26.10**(등록 기능 제품 코드 0줄 실측 · Gap 5분류 · fused 시간축 미반영).
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

### 26.10 시연 요구사항 ↔ repo 실물 전수 감사 + 진입점 2 축소 결정 (2026-09-12 PoC-(46) 신설)

**(a) 🔴 진입점 2 「초인종 등록」의 제품 코드가 0줄이다 (근거유형 = 실측 grep, 부재 증명에 대조군 동반)**

- **등록 라우트 0**: `server/app/routes.py`에 등록·해제 엔드포인트 **0건**. **대조군** = 같은 파일의 `rate_limit.check_and_register(device_id)` **1건**이 잡히므로 **grep 자체는 살아 있다**(부재 증명의 도구 생존 확인 — 카테고리 20 negative control 계열).
- **DB 테이블 0**: `server/app/models.py`의 `__tablename__` **전수 = `notifications` / `idempotency_keys` / `kakao_tokens` 3개뿐**. 초인종 등록 테이블 없음.
- **등록·해제 UI 0**: `dashboard/src/App.tsx` 라우트 **전수 = `/` · `home` · `notifications` · `stats` · `settings` · `help` · `*`**. 등록 화면 없음.
- **등록 여부 분기 0**: `server/app/utils.py` `_apply_prediction_policy()` 판정 분기 **전수 = 신뢰도(`low_confidence`) / `fire_alarm` / ToF 3개뿐**. *"등록된 초인종인가"*를 보는 분기는 **없다**. ⚠️ **[2026-09-15 PoC-(48) 추가] 계수 단위 = 조건 분기 수**다 — 같은 함수를 **`return` 문 기준**으로 세면 **4개**(fallthrough 포함)가 나온다. 🔴 **위 숫자는 정정 대상이 아니며 무변경**이다: 본 항의 논지는 *"등록된 초인종인가를 보는 분기가 없다"*는 **부재 증명**이라 계수 단위만 다르면 **둘 다 참**이고, 숫자를 바꾸면 논지가 흐려진다.
- **스파이크는 제품과 연결되지 않는다**: `grep -rn "dtw_doorbell" server/ dashboard/src firmware/src` = **0건**. `ml/experiments/dtw_doorbell/`(프로즌 스파이크, 33.5(B))는 제품 경로와 **연결 0건**이다.
- ⚠️ **한계 = repo 기준 감사다.** 26.8이 *"Gap 카드 누적 위치 = 노션 DB3"*라 적었으므로 **노션 DB3 대조는 본 Set 범위 밖**이다. 여기서 말하는 "부재"는 **repo 실물 부재**이지 **트래킹 부재가 아니다**(27.8(f)의 3층 구분).

**(b) 26.9 Gap + 26.6 디벨롭 표 5분류 판정 (학습 21, 근거유형 = 실측 grep)**

| 분류 | 건수 | 내역 (개별 요구사항 단위) |
|---|---|---|
| ③ 트래킹 있으나 **실물 부재** | **5** | 26.9 **G3**(등록 응답 시간) · **G4**(초인종 4종 분리 정확도) · **G5**(등록 해제 UI) / 26.3 진입점 2 **등록 액션**(SP/DTW + cosine 템플릿 저장) / 26.6 **「대시보드 등록 해제 UI」** |
| ④ **부재로 기록됐으나 실재** | **3** | 26.9 **G1**(ToF 통과 표시 UI) = `NotificationTof.tsx` 실존(8.4(b)) / 26.9 **G2**(자막 형태 — 메시지 vs 이미지) = 7.6이 **사진 feed + 자막 text 2건 분할 발송**으로 확정·실물화 / 26.6 **「화재 대응 수칙 메시지 템플릿 · 정부 출처 검증」**(처리 시점을 13~14주차로 기록) = 7.1 확정 + `constants.py` 실물(소방청 출처 포함) |

- ⚠️ **계수 단위 = 개별 요구사항 수**(26.9 표의 **행 수가 아니다**). 26.9 Gap 5건은 **③ 3건 + ④ 2건**으로 갈리고, ③의 나머지 **2건**과 ④의 나머지 **1건**은 **26.3 본문·26.6 표**에서 온 항목이다.
- 🔴 **G3·G4·G5는 전부 「🔴 시연 필수」로 기록돼 있는데 repo 실물이 0줄이다.** 동시에 **26.9 표는 2026-05-09 이후 갱신되지 않아** G1·G2가 **이미 실물화됐는데도 미해결처럼 읽힌다** — 표가 양방향으로 stale이다.
- **26.9 표 자체의 갱신은 Set 3 소관**으로 둔다(Gap 카드 실물이 노션 DB3에 있으므로 — 26.8). 본 절은 **repo 기준 판정까지**다.

**(c) ★ 사용자 결정 — 진입점 2를 「ToF presence 단독 시연」으로 축소 (2026-09-12 확정)**

- **등록·해제 액션은 시연 범위에서 제외.** 결정 전문과 근거 3은 **26.3 진입점 2** 본문에 in-place 반영했다(취소선 + 신규 서술).
- ⇒ 본 결정으로 **(b)의 ③ 5건 중 등록 계열 4건**(G3·G5 · 26.3 등록 액션 · 26.6 등록 해제 UI)은 **시연 필수 위상에서 내려온다**. **G4**(초인종 4종 분리 정확도)는 33.5의 **직접녹음 재검증 경로**로 남으며 **시연 요구사항이 아니게 된다**.
- ⚠️ **위 위상 변경은 repo 기준 서술이다** — 26.9 표의 「🔴 시연 필수」 라벨 자체는 **무변경**(Set 3 소관, 위 (b) 참조).

**(d) 🔴 [신규 미결] 축소된 진입점 2의 선행 조건 = 실모델 서버 투입 (발견·문서 반영 2026-09-12, 근거유형 = 논증, 입력 실측 = 33.6 · 6.4(g))**

- 축소된 진입점 2가 성립하려면 **「신뢰도 ≥0.70 doorbell + `presence=false` → `tof_rejected`」** 경로를 **실제로 타야 한다**.
- 그런데 이 경로는 **6.4(g) ④런타임에서 미관측**이다 — 런타임 2건 **모두 `low_confidence` 선차단**이라 도달하지 못했고, **서버 회귀 102건으로 대체 커버**됐을 뿐 **실기기에서 본 적이 없다**.
- 그리고 **현재 서버 기본 기동은 mock ML**이다(33.6(c)). mock은 클래스·신뢰도를 **난수**로 내므로 *"doorbell을 0.70 이상으로"*를 **재현할 수 없다**.
- ⇒ **실모델 없이는 이 시연이 성립하지 않는다.**
- **판정 방법** = 실모델 기동 상태에서 **실 초인종 음원 + `presence=false`**(문 앞 사람 없음)로 `tof_rejected` **1차 미발송**을 **화면과 서버 로그 양쪽에서** 확인한다.
- ⚠️ **같은 세션에 33.6(a)의 OOD 수렴이 함께 걸린다** — 분포 밖 입력이 `fire_alarm`으로 쏠리므로 부스 대화 소리가 화재 알림을 낼 수 있다. **두 문제를 한 번에 건드리지 말 것**(원인 분리 불가). ~~**대응 방향 = 사용자 판단 대기.**~~ → 🆕 **확정 (사용자 결정 D4 — 2026-09-21 PoC-(55), 상세 = 33.13)**: **4번째 클래스 `other` 신설**이다. 🔴 **부스 대화 소리 축의 실제 해소는 재학습 후**이며 **본 줄의 「두 문제를 한 번에 건드리지 말 것」은 무변경**이다.
  - 🆕 **[2026-09-15 PoC-(49) 실측 포인터, 계수 단위 = 행 수]** 위 「쏠린다」의 **부스 파급을 조건 축으로 넓혀 측정**했다 — 유효 **126행** 중 **`presence=true`에서 발송 102 / 126**이고, **`presence=false`에서도 발송 20 / 126**이다(20행 전건이 `fire_alarm` ≥0.70이라 **G12로 ToF를 우회**한다). 상세 · 한계 · 대응(**사용자 판단 대기**) = **33.6(f)**.
- ✅ **판정 방법 충족 — 서버·화면 양축 관통 관측 (실측·문서 반영 2026-09-14 PoC-(47), 근거유형 = 실측 curl + 화면 catch)**: 위 **판정 방법**이 지정한 *"실모델 기동 + `presence=false` → `tof_rejected` 1차 미발송을 화면과 서버 로그 양쪽에서 확인"*이 **양축 모두 충족**됐다. 🔴 **단 CLOSE가 아니다** — 아래 경계 3건 참조.
  - **입력 클립** = `05_final_dataset/test/doorbell/125967_0000000.wav`(33.6(d) 사전 스윕에서 `doorbell` **1.00** 확인 후 선별). `POST /api/v1/detect`에 `tof_presence=false` / `near=0` / `center=1200` / `ndet=0` 주입.
  - **서버 응답** = `predicted_class=doorbell` / `confidence=1.0` / `skip_reason="tof_rejected"` / `primary_sent=false` / `primary_sent_at=null` / `tof_check applied=true passed=false` / `reason="presence=false near=0/64 center=1200mm ndet=0/16"`.
  - **화면**(`/notifications`) = 뱃지 「발송 제외」 + 「사람 없음」, 문구 *"사람 감지 실패 때문에 알림을 보내지 않았어요."*, 거리 센서 `presence=false near=0/64 center=1200mm ndet=0/16` — **서버 `reason`과 문자 일치**. `zone_count=` 가짜 문자열 **미출현**(6.4(f) 해소 유지 확인).
  - ⚠️ **경계 ① 실기기 미관통**: 본 건은 **실모델 + curl 경로**이며 **보드(M5-d + ToF) 관통은 미수행**이다. ⇒ **본 (d)는 CLOSE되지 않는다.**
  - ⚠️ **경계 ② ToF 4필드는 curl 주입 하드코딩**이며 **실센서 값이 아니다**. 6.4(b)의 fused 판정(Stage A ∧ Stage B-2)을 거친 값이 아니므로 **(e)의 latch 쟁점은 본 관측으로 해소되지 않는다**.
  - ⚠️ **경계 ③ 실모델 첫 관측**: 6.4(e)의 동일 경로 기존 관측은 **mock ML**이었다. 본 건이 이 경로의 **실모델 첫 관측**이다.

**(e) ⚠️ 6.4(b) fused 확정이 진입점 1·2 서술에 미반영 (근거유형 = 실측 grep, 입력 = 6.4(b) · 9.4(b)(e))**

- 6.4(b)가 2026-09-11에 **`tof_presence` = Stage A `presence_state` ∧ Stage B-2 `motion_latch_active`**(fused)로 확정했고, 9.4(b) latch = **`TOF_MOTION_LATCH_FRAMES = 75`(15Hz × 5초)**다. ⇒ 설계상 **"문 앞에 정지한 채 5초가 지나면 presence가 false로 떨어진다"**가 된다.
- **26.3 진입점 1·2의 "ToF 사람 검증" 서술은 이 시간축 성질을 담지 않는다.** 부스에서 관람객이 **가만히 서 있다가** 초인종을 누르면 억제될 수 있다.
- ⚠️ **단 실측은 반대 방향 n=1이다** — 9.4(e)의 프로토콜 ② 첫 데이터에서 **정지 사물(책 ≈440mm)이 약 8초간 fused PERSON 유지**됐고, `TOF_MOTION_NDET_MIN=1`이 latch를 **재충전**한 것으로 **추정(논증)**된다. ⇒ **실제 부스에서 어느 쪽이 나올지는 미확정**이다.
- **본 절은 「26.3 서술과 6.4(b) 확정 사이의 불일치」 등재까지**다. **시연 각본 조정·판정 상수 재검토 = 사용자 판단 대기**(방향 확정 금지).

**관련**: 26.3(진입점 2 축소 in-place 반영) / 26.6(디벨롭 표 — ③④ 판정 입력) / 26.8·26.9(Gap 카드 · 노션 DB3 = Set 3 소관) / 33.5(USP 2층 · SP/DTW 단독 시연 NO · dtw_doorbell 스파이크) / 33.6(실모델 OOD · 게이트 축) / 6.4(b)(g)(fused 매핑 · ④런타임 미관측) / 9.4(b)(e)(latch 75프레임 · 정지 사물 n=1) / 8.7(a)(도움말 카피 정정 — 본 (a) 감사의 첫 산출) / 학습 21(유령 미결 5분류)

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

### 27.8 위임 프롬프트 절 번호·인용 오기 누적 — grep 후 인용 강제 (2026-09-08 PoC-(42) 신설, 근거유형 = 실측)

**★ Claude 자신의 실수도 프로젝트 아티팩트다.** 2026-09-08 세션에서 잡힌 **위임 작성자(Claude) 오류**를 기록한다 — 숨기면 같은 오류가 다음 위임에서 반복된다.

**(a) PR #45 위임 오류 2건**
- §4-3(f)가 "종결 상태 3종의 SSoT = 카테고리 6.1"로 지목했으나 **실물은 7.6(d) + `routes.py`**였다 — 인용 **위치** 오류(값은 맞고 주소가 틀렸다).
- §5 Step 4-b "자격증명 미설정 → 자막 부재"가 Step 3-d "기존 mock/real 패턴 준수"와 **양립 불가**였다. 게이트 정의상 **"real 모드 + 자격증명 없음"은 도달 불가 상태**이기 때문이다 → **위임 내부 자기모순**(학습 16 = 위임 작성자의 자기모순도 catch 대상).

**(b) PR #47 위임 오류 2건 + 컨벤션 충돌 1건**
- §5 5-c의 N2 축에 `stt`를 넣었으나 **`derive()`는 `stt`를 읽지 않는다**(형제 필드다).
- NC-2 규정("순서 뒤집기")이 **금지 상태를 만들지 못했다** → MCP가 금지 상태를 실제로 만드는 변형을 **NC-2로 재규정**하고 순수 순서 뒤집기를 **NC-2b로 분리**(카테고리 20 「negative control 미검출의 판정」).
- 커밋 분리 판단을 느슨하게 줬으나 MCP가 **`docs/git-convention.md` 컨벤션을 우선**해 4분리 + 중간 상태 빌드 4/4 실측 → **학습 16 정상 작동**.

**(c) 대화형 지시 오류 3건**
- `picsum.photos` 다운로드에 **`-L`(리다이렉트 추적) 누락** → **0바이트 JPEG 생성**. `file` 명령이 잡았다 — 2026-09-05 "133바이트 사고"와 **같은 계열**이다(다운로드 산출물을 **크기·타입으로 검증**하지 않으면 빈 파일이 실측 입력으로 들어간다).
- `/enrich` 대상 지정을 `request_id`로 줬으나 실제 필드는 **`client_request_id`**.
- `/detect` 호출에 **`device_id` 누락**.

**(d) ★ 누적 패턴 = 절 번호 오기가 계속 나온다**
~~PoC-(41) **3건** → PR #45 **1건** → PR #47 **2건**. 전부 **위임 작성 시점에 기억으로 절 번호를 박아서** 생긴 오류다.~~ ~~**[누적 갱신 2026-09-09 PoC-(43)]** PoC-(41) **3건** → PR #45 **1건** → PR #47 **2건** → PR #48 **2건** → PR #49 **3건** → 본 Set 1 **2건** = **누적 13건**.~~ ~~**[누적 갱신 2026-09-09 PoC-(44)]** PoC-(41) **3건** → PR #45 **1건** → PR #47 **2건** → PR #48 **2건** → PR #49 **3건** → PoC-(43) Set 1 **2건** → **PR #51 + PoC-(44) Set 1 6건**((g)) = **누적 19건**.~~ **[누적 갱신 2026-09-11 PoC-(45) Set 1]** PoC-(41) **3건** → PR #45 **1건** → PR #47 **2건** → PR #48 **2건** → PR #49 **3건** → PoC-(43) Set 1 **2건** → PR #51 + PoC-(44) Set 1 **6건**((g)) → PR #52·53·54 **2건**((h)) = **누적 21건**. 대부분 **위임 작성 시점에 기억으로 절 번호를 박아서** 생긴 오류이나, PR #49 ①은 유형이 다르다((e) 참조).
- **작성 측 강제 규칙**: 위임 프롬프트에 절 번호·인용값을 적을 때는 **`git show HEAD:docs/decisions.md | grep -nE "^## 카테고리|^### "`를 먼저 실행하고 그 결과에서 인용**한다. **기억으로 박지 않는다.**
- **수행 측 강제 규칙**: **위임이 준 절 번호·인용값도 실물 대조 대상**이다(학습 13 — 본 위임에 옮겨 적은 인용값도 catch 대상). 불일치 시 **실물을 택하고 보고**한다.
- ※ 본 절은 카테고리 27(위임 프롬프트 **가정** 검증)의 **인용 계층** 사례다 — 27.7(경로 가정)과 같은 층위.

**(e) PR #48 · PR #49 · 본 Set 1 인용 오기 7건 (2026-09-09 PoC-(43) 추가, 근거유형 = 실측 grep)**

- **PR #48 2건**: 브랜치 규칙 출처를 `docs/git-convention.md`로 지목했으나 실물은 **decisions.md 카테고리 20**(`feat/{domain}-{task}`) / `FIRE_ALARM_PRIMARY_MESSAGE` 소속을 `kakao.py`로 지목했으나 실물은 **`constants.py`**. 둘 다 **값은 맞고 주소가 틀린** (a) 동형.
- **PR #49 3건**:
  - ★★ ① **"decisions.md 7.5에 '갱신 자체가 실패하는 구간은 자동 복구 불가 — 코드로 못 푼다'가 등재돼 있다"** → `grep "자동 복구\|코드로 못 푸\|갱신 자체가 실패"` **0건**. 실물과 가장 가까운 문장은 **decisions.md가 아니라 `server/app/tests/test_detect_regression.py`의 docstring**이었다.
  - ② "`_build_stats` 10키 = `StatsResponse` 10필드 정합이 **등재돼 있다**" → 그런 등재 문구 부재(실물 등재는 6.1의 **TimingMetrics 6키**). ⚠️ **키 수 자체는 실측 10:10 일치**라 제약은 그대로 준수했다 — **주장은 맞고 출처가 없는** 경우다.
  - ③ "토큰 SSoT = DB `kakao_tokens` / env 4키는 부트스트랩용"이 **문장 형태로는 부재**(절차·`SINGLETON_ID` 언급은 7.5(e)에 실존, 코드로는 확증) → 파급 없음.
- **본 Set 1 2건**: G14 등재 위치를 **6.2**로 지목했으나 실물은 **6.1**((f)) / "회귀 케이스 수가 **89**로 적힌 곳"을 정정 대상으로 지목했으나 실물에서 89는 **카테고리 3 G12 이력 서술 1건뿐**이고 stale한 것은 **7.5(i)의 「60 케이스」**(누적 현재값)였다 — **지시된 대상과 실제 대상이 어긋난** 경우.
- ★★ **①은 (a)~(d)의 6건과 유형이 다르다 — 절 번호 오기가 아니라 「출처 계층 착각」이다.** 코드 주석·테스트 docstring에서 읽은 문장을 **SSoT 문서에 등재된 것으로 기억**했다. **재발 방지책도 다르다**: 절 번호 grep(`^### `)으로는 **잡히지 않는다**. 인용문을 적을 때는 **"그 문장이 어느 파일에 있는지"를 `grep -rn "<문장 일부>" docs/ server/ dashboard/`로 확인**해야 한다. 인용 계층 = ① SSoT 문서 / ② 코드 주석·docstring / ③ PR 본문·대화 — **세 층은 권위가 다르다.**
- ★ **①의 실질 피해는 0이었다** — 수행 측이 grep 0건을 확인하고 **근거를 문서 인용에서 코드 실측(`routes.py` 하드코딩 리터럴 + `SystemHealthCard` 초록불 매핑)으로 교체**해 진행했기 때문이다. 이것이 (d) 「수행 측 강제 규칙」이 값을 한 사례다.

**(g) PR #51 · 본 Set 1(PoC-(44)) 인용 오기 6건 — 누적 ~~13건~~ → 19건 (2026-09-09 PoC-(44) 추가, 근거유형 = 실측 grep)**

- 🔴 **① 압축 손실 — 이번엔 위임 작성자 자신이다**: PR #51 위임 §2가 "프론트 SSR 하네스를 PR #47·#49·#50 **3연속 사용**"이라 적었으나, 실측 결과 **PR #50은 SSR 하네스를 쓰지 않았다**(`git show ca276a9 --stat` = `server/` 2파일뿐이고 NC는 전부 `python3 -B` 서버 NC). 실제는 **2연속**이다. ★ **위임 작성자가 같은 세션에서 직접 본 것을 압축하며 틀렸다** — 기억으로 박은 절 번호 오기((d))와 달리 **본 것을 요약하는 단계에서 손실**됐다. 착수 근거는 무손상(막고 있던 것은 "3연속"이 아니라 8.4(f)의 「의존성 금지」였다).
- 🔴 **② 「압축 손실」이라는 개념 자체가 decisions.md 미등재였다 — 「출처 계층 착각」 2호**: 본 Set 1 위임이 "9/09에 **신설한** 「압축 손실」이 하루 만에 재발"이라 적었으나 `grep -rn "압축 손실" docs/` = **0건**. 해당 개념은 **프로젝트 지침 계층에만** 있고 SSoT 문서에는 등재된 적이 없다. (e) ①과 **같은 유형**(코드·지침에서 읽은 것을 SSoT 등재로 기억)이며, 본 (g)가 **decisions.md에 최초 등재**한다.
- 🔴 **③ 「정합성 정정」 PR 성격 선례도 미등재였다 — 「출처 계층 착각」 3호**: 본 Set 1 위임이 "PR #48의 「정합성 정정」이 **제3의 성격으로 신설된 선례**"를 근거로 새 PR 성격 신설을 제안했으나, `grep -n "정합성 정정"` = **decisions.md 0건**. 실물에 등재된 PR 성격 어휘는 **「배관(plumbing) PR」**(8.5 서문)과 **「방법론 자산」**(8.4(f) 소제목)뿐이다. ⚠️ **제안의 근거가 무너졌으므로 신설하지 않고 사용자 판단으로 올렸다**(§9-d).
- **④ "8.5에 「④런타임 미수행」 미결이 실존한다"** → 8.5 구간 전수 grep에서 `④런타임`·`미수행` **둘 다 0건**. 실물의 대응 서술은 8.5(g)의 *"시각은 전건 고정 주입 — 실 시계·실 카카오 API 미호출, DB 상태 주입만"*이며 이는 **한계 서술이지 등재된 미결이 아니다**. → 처리를 **취소선 → 신규 등재(8.5(k))로 pivot**했다(§9-c).
- **⑤ "7.7(e)의 fail-silent 서술"** → `grep -rn "fail-silent\|가짜 자막\|소리 없이" docs/ server/ dashboard/` = **repo 전역 0건**. **소절 번호 (e)는 맞다** — 7.7(e) 「env 게이트」의 실물 문언은 *"미설정이면 **호출 자체를 하지 않고** mock 자막을 유지한다"*이며, "fail-silent"는 위임 작성자의 **조어**다. 값은 맞고 **문언이 창작된** 경우라 (a)의 "값은 맞고 주소가 틀림"과 또 다른 축이다.
  - 🔴 **[단서, PoC-(45) 문서 반영] 위 "0건"은 8.6(d) 작성 전 측정값이었다 — (f-2)와 같은 패턴의 즉시 재발**: **같은 PoC-(44) 세션**이 이 문장을 쓴 직후 8.6(d)에서 "fail-silent"·"가짜 자막"·"소리 없이" 세 표현을 **그대로** 등재했다(8.6(d) 참조). 같은 grep을 지금 재실행하면 **0건이 아니다**(8.6(d) + `decisions-log.md` 매치 포함 5건). (f-2)가 지적한 "측정 시점값에 단서가 없으면 즉시 stale해진다"는 원칙이 **다음 소절이 아니라 같은 절 안에서** 재현된 사례다.
- **⑥ "27.8은 누적 **14건**임을 기록한다"** → 실물 (d)는 **누적 13건**. **자기 참조 오기**(본 절의 누적 숫자를 본 절을 인용하며 틀렸다).
- ★ **유형 분포가 바뀌었다**: (a)~(d)의 주류는 **절 번호 오기**였으나 본 6건 중 절 번호 오기는 **0건**이다. ①은 **압축 손실**, ②③은 **출처 계층 착각**, ⑤는 **문언 창작**, ⑥은 **자기 참조 오기**다. → **(d)의 재발 방지책(`^### ` grep)은 본 6건 중 단 1건도 잡지 못한다.** 잡는 것은 (e) ①이 세운 **`grep -rn "<문장 일부>" docs/ server/ dashboard/`**(②③⑤)와 **실물 재실행**(①⑥)이다.

**(f) 🔴 G-ID 등재 여부 오독 — 「트래킹 부재」는 3층으로 갈린다 (2026-09-09 PoC-(43) 신설, 근거유형 = 실측 grep 전수)**

본 Set 1 위임이 **"G14 등재 여부 모순"**을 최우선 정정 대상으로 지목했다. 실측 결과 **모순은 decisions.md에 없었다.**

- **`grep -n "G14" docs/decisions.md` = 2건** — 카테고리 **6.1** 본문에 `~~[신규 미결] primary_sent_at…~~` **취소선 + ✅ 해소 (2026-09-03 PoC-(39), PR #40 `70aea1d`)** 형태로 **실등재**돼 있고, 7.5 「관련」 줄에서 한 번 더 참조된다.
- **`grep -n "미등재"`로 전수 확인한 결과 "G14가 미등재"라는 취지의 서술은 문서 어디에도 없다.** 7.5(a)의 미등재 서술이 지목하는 것은 **G18/G21/G24**이며 거기에 G14는 들어 있지 않다.
- ∴ **모순의 소재는 decisions.md가 아니라 위임·인계 계층**이다. 따라서 처리는 문서 정정(취소선)이 아니라 **등재 사실을 명시적으로 못 박아 다음 세션의 재오독을 막는 것**이다(6.1 해당 항목에 앵커 문장 추가).
- 🔴 **「트래킹 부재」로 뭉뚱그리면 안 되는 ~~3층 구분 (실측 grep 건수)~~ → 4층 구분 (실측 매치 문맥)**:

🔴 **「grep 건수」 열은 2026-09-09 PoC-(44)에서 폐기됐다 (사유 = 아래 (f-2)).** 2026-09-09 PoC-(43) 원 표는 이력 보존을 위해 취소선으로 남긴다 — **삭제하지 않는다**:

> ~~| 층 | ID | grep 건수 | 실태 |~~
> ~~|---|---|---|---|~~
> ~~| ① **본문 실등재** | **G14** | **2** | 6.1에 취소선 + ✅ 해소로 등재. **부재가 아니다** |~~
> ~~| ② **「미등재」 서술 안에서만 등장** | **G18 / G21 / G24** | 각 **1** | 본문 항목이 아니라 7.5(a)의 *"본 3건은 decisions.md 미등재"* 문장 자체가 유일한 매치. **Notion DB3 전용 감사 ID** |~~
> ~~| ③ **진짜 부재** | **G23 / G34** | **0** | G23 = STT 미구현 defer 표기(7.7로 해소되며 절 본문에 흡수) / G34 = PoC-(39)에서 **위임 전제가 실물과 불일치해 판단불가 각하** |~~

정정 후 표는 다음과 같다.

| 층 | ID | 매치가 서 있는 **문맥** | 실태 |
|---|---|---|---|
| ① **본문 실등재** | **G14** | 6.1 본문 항목(취소선 + ✅ 해소) + 7.5 「관련」 참조 + 6.1 재오독 방지 앵커 | **부재가 아니다** |
| ② **「미등재」 서술 안에서만 등장** | **G18 / G21 / G24** | 7.5(a) *"본 3건은 decisions.md 미등재"* 문장 + 6.1 재오독 방지 앵커(같은 취지) | 본문 항목 아님. **Notion DB3 전용 감사 ID** |
| ③ **진짜 부재** | **G34** | 본 절 목록 외 매치 없음 | PoC-(39)에서 **위임 전제가 실물과 불일치해 판단불가 각하** |
| ④ **부재하나 코드 원문 인용 안에 등장** | **G23** | 7.7(k)가 인용한 `kakao.send_secondary` **구 docstring 원문**(*"실 STT(G23)는 미구현"*) | STT 미구현 defer 표기. 7.7로 해소되며 절 본문에 흡수. **본문 항목으로는 부재**지만 **인용문 안에서는 실재**한다 |

- 🔴 **(f-2) ★ 본 표가 자기지시적으로 깨졌다 — 「현재값 서술 vs 이력 서술」의 첫 자기 적용 사례 (발견·문서 반영 2026-09-09 PoC-(44), 근거유형 = 실측 재실행)**
  - 본 절이 명시한 재현 명령 `grep -oE '\bG[0-9]{1,2}\b' docs/decisions.md | sort -u`가 **명시 결과 10개와 다른 12개**를 반환한다(`G23`·`G34` 포함). **원인 = 본 절 본문이 G23/G34를 스스로 언급하기 때문**이다. 표 건수도 전건 어긋났다(줄 수 기준 G14 2→8 / G18·G21·G24 각 1→5 / G23 0→3 / G34 0→2).
  - ⚠️ **본 27.8 절을 제외해도 어긋나는 것이 2건 있고, 둘 다 원인이 같다**: (i) G18/G21/G24가 **각 2줄** — 2번째 매치는 **카테고리 6.1의 G14 재오독 방지 앵커**(*"미등재인 감사 ID는 G18/G21/G24뿐"*) (ii) G23이 **1줄** — **7.7(k)가 인용한 docstring 원문**. **둘 다 같은 PoC-(43) Set 1이 만든 매치**다. 즉 표를 쓴 세션이 **같은 세션에 새 매치를 만들어 놓고 그 전 숫자를 적었다.**
  - 🔴 **성격 = 표의 숫자가 「측정 시점값(이력)」인데 그 단서가 없었다.** 7.5(i)가 「누적 현재값 vs 그 PR 시점 이력」을 문장으로 갈라 둔 것과 **같은 구분**이며, 본 표는 그 구분을 **자기 자신에게 적용하지 않았다**.
  - ✅ **처리 = 건수 정정이 아니라 열 자체를 바꿨다 (판단 근거)**: 건수를 12로 고쳐도 **다음 세션이 G-ID를 한 번만 더 언급하면 즉시 stale**이 된다. 본 표는 이미 *"매치 문맥을 실독해야 한다"*고 써 놓고 정작 SSoT로 삼은 값은 **문맥이 아니라 숫자**였다 — 자기 원칙과 어긋난 열이다. → **「grep 건수」 열을 「매치가 서 있는 문맥」 열로 교체**했다. 문맥은 **G-ID를 한 번 더 쓴다고 바뀌지 않으므로 stale이 되지 않는다.**
  - ⚠️ **재현 명령은 남기되 용도를 좁힌다**: `grep -oE '\bG[0-9]{1,2}\b'`는 **"어떤 ID가 문서에 등장하는가"**를 훑는 용도로만 쓰고, **"등재 여부"의 근거로 쓰지 않는다**. 등재 여부는 **매치 문맥 실독**으로만 판정한다.
  - ★ **④층은 「부재 ID를 본문에 쓰지 말 것」 원칙과 형식상 충돌하나 정당하다** — 7.7(k)의 G23은 **정정 대상이 된 구 docstring의 원문 인용**이며, 원문을 바꾸면 무엇을 고쳤는지가 사라진다. **인용은 사용이 아니다.**

- ★ **이 3층을 구분하지 않으면 "grep N건"이라는 서술 자체가 다음 위임의 인용 오기가 된다** — ②는 건수만 보면 "등재돼 있다"로, ①은 맥락을 안 보면 "미등재"로 오독된다. **매치 문맥을 실독해야 한다**(29.5의 "도어벨" 오탐 주의와 같은 층위).
- **실존 G-ID 전수 (2026-09-09 실측, `grep -oE '\bG[0-9]{1,2}\b' docs/decisions.md | sort -u`)**: **G10 · G12 · G14 · G18 · G21 · G22 · G24 · G27 · G28 · G29** — 10개. 이 중 **본문 항목으로 실등재된 것은 G10 / G12 / G14 / G22 / G27 / G28 / G29** 7개이고, **G18 / G21 / G24는 ② 층**이다. 부재 ID(G23 / G34)는 본 표 밖이며 **본 절 이외의 본문·커밋 메시지에는 쓰지 않는다**(부재 ID 사용 금지 원칙 — 본 절만 예외, 목록 자체가 기록 대상이므로).
- 🟡 **[등재] `G07`·`G15`·`G16`·`G17`·`G19`·`G20` — decisions.md 0건인 추가 미확인 ID군 (PoC-(45) 문서 반영, 근거유형 = 문서 인용, 미실측)**: 위 전수 목록에 없는 이 6개 ID는 **이전 지침·인계 계층에서만 사용**돼 왔다(9/02 감사 ID로 추정 — 확정 아님). `decisions.md` grep = **전부 0건**(위 ①~④ 어느 층에도 없다). **Notion DB3 등재 여부도 미확인**이다. ⚠️ 실재하는 감사 ID로 단정하지 말 것 — 다음 세션이 노션 DB3 대조 전까지는 **③ 지침·인계 계층 서술**로만 취급한다.

**(h) PR #52·53·54 인용 오기 2건 — 누적 19건 → 21건 (2026-09-11 PoC-(45) Set 1 추가, 근거유형 = 실측 grep)**

- 🔴 **① 「출처 계층 착각」 4호**: PR #53 위임 보고서가 A5 판정 근거로 `server/app/tof_meta.py` docstring 문구 "디바운스와 latch를 거쳐 확정한 값"을 **decisions.md 6.4(b)와 나란히** 인용해 SSoT 등재 문구처럼 제시했으나, `grep -n "디바운스와 latch를 거쳐 확정한 값" docs/decisions.md` = **0건**. 실물 소재는 **코드 docstring(② 계층)뿐**이며 decisions.md(① 계층)엔 없었다. (e)①·(g)②③과 같은 유형(코드에서 읽은 것을 SSoT 등재로 착각) — 재발 4호.
- **② PoC-(44) 인계 문구 대조**: "C-0로 학습용 녹음도 한 번에" 취지 서술을 인계 계층 근거로 삼은 관행이 있었으나, M5-a2(6.3(i))는 **윈도우 진폭 통계 줄만 출력**하며 **오디오 원본은 저장하지 않는다**(코드 실독 확인, 판정 로직·저장 경로 0줄). 값·주소 모두 틀린 것이 아니라 **기능 범위 과대 서술** — (a)류(주소 오기)·(e)①류(출처 착각)와 다른 축이라 별도 기록.
- ★ **실질 피해**: ①은 6.4(b) 자체 해석(시간축 판정 → presence 그대로 신뢰)이 이미 fused 결론을 뒷받침해 **판정 결과는 무변경**(피해 0, 27.8(e)①과 동형). ②는 본 세션이 코드로 재확인 후 진행해 **파급 없음**.

**(i) PoC-(46) 인용 오기 2건 — 전부 라인 번호 (2026-09-12 PoC-(46) 추가, 근거유형 = 실측 grep)**

- **① `decisions.md:345`** — 카테고리 26 감사 보고가 쓴 인용 좌표. **실제 349행**이었다(3행 드리프트).
- **② `decisions.md:1979`** — 같은 보고. **실제 1981행**이었다(2행 드리프트).
- ★ **실질 피해 0** — 인용한 **내용·문구는 정확**했고 판정도 무변경이다. 틀린 것은 값이 아니라 **형식**이다: **라인 번호를 인용 좌표로 쓴 것 자체**가 「인용은 절 번호 + 문구 전문으로, 편집 앵커는 패턴 매칭으로」 규칙 위반이다.
- 🔴 **왜 라인 번호가 특히 나쁜가**: 라인 번호는 **앞줄이 한 줄만 늘어도 틀린다**. (f-2) 「grep 건수 = 측정 시점값」과 **같은 축**이며 — **라인 번호도 측정 시점값**이다 — 오히려 더 빨리 썩는다. 본 건 2건 모두 **문구는 그대로인데 좌표만** 어긋났다.
- **재발 방지**: 인용 좌표는 **절 번호 + 문구 전문**으로 적고, **편집 앵커에도 라인 번호를 쓰지 않는다**(본 Set의 편집 앵커 전건 = `grep -cF` 패턴 매칭, 라인 번호 0건).
- ⚠️ **누적 카운트((d))에 합산하지 않았다 — 사용자 판단 대기.** **PoC-(44) Set 3 4건**과 **본 2건**을 (d)의 **누적 21건**에 넣을지가 미확정이라, 본 항목은 **등재만** 하고 **(d)는 무변경**으로 두었다. ⇒ **(d)의 「누적 21건」은 본 (i)를 포함하지 않는 값**이다(현재값 서술의 경계 표기).

**(j) PoC-(48) 위임 인용 오기 2건 + 라인 번호 재발 1건 (2026-09-15 PoC-(48) 추가, 근거유형 = 실측 grep)**

- **① 「판정과 표시의 자료형 분리」(2026-09-14 위임)** — SSoT 문구인 줄 알고 grep을 지시했으나 실물은 8.5(k)의 *"표시가 판정을 오염시키지 않는다"*였다. ⚠️ **이 사실 자체는 33.6(e)에 이미 등재**돼 있다 — 본 (j)는 **중복 서술하지 않는다.** 여기에 남기는 것은 **패턴**뿐이다.
- ★ **패턴 = 「출처 계층 착각」의 ③ → ① 역방향**: 위임(**③ 계층**)이 만든 요약 문구를 **SSoT(① 계층) 원문인 것처럼 되돌려 인용**하는 방향이다. 27.8이 지금까지 누적한 오기가 *"어느 절인지"*를 틀리는 축이라면, 본 축은 *"어느 계층의 문장인지"*를 틀린다. ⇒ **인용부호를 칠 때는 절 번호보다 먼저 계층을 확인한다.**
- **② 「라벨 순서 = `labels.json`」(2026-09-15 위임)** — SSoT 문구로 옮겨 적었으나 실물 33.2는 **「라벨 순서 = `CLASSES` 상속」**이다. MCP가 실물 근거로 기각하고 negative control의 비교 대상을 **실제 의존 지점(`app.constants.PREDICTED_CLASSES`)** 으로 교체했다 — 그대로 갔다면 하네스가 **판정에 쓰지도 않는 파일**을 단언 대상으로 삼을 뻔했다. ★ ①과 **같은 계층 착각**이되 피해 방향이 다르다: ①은 인용이 틀렸고, ②는 **검증 대상 자체가 틀릴 뻔했다.**
- **③ 라인 번호 인용 재발** — 2026-09-14 **3건** → 2026-09-15 **1건**(계수 단위 = 인용 건수). **(i)가 닫은 축**이며 **3세션 연속 재발** 중이다. ⚠️ 본 (j)와 본 세션 `decisions-log.md` 엔트리·편집 앵커는 **라인 번호 0건** 사용이다.
- ⚠️ **(d)의 누적 숫자는 본 항에서 건드리지 않았다** — 합산 여부가 **(i)에 사용자 판단 대기**로 등재돼 있다. ⇒ **(d)의 「누적 21건」은 (i)도 본 (j)도 포함하지 않는 값**이다(현재값 서술의 경계 표기).

**(k) PoC-(49) 위임·인계 인용 오기 5건 (2026-09-15 PoC-(49) 추가, 근거유형 = 실측 grep + 실물 대조)**

- 🔴 **① 「m2/m5 교대 18스냅샷」 — 압축 손실 ((g)① 재발)**: 인계 계층 문구가 18스냅샷을 **m2 / m5 두 모드로만** 적었으나, 실물은 **6블록 = 2 → 5 → 2 → 5 → 0 → 6**이고 **m0 · m6 블록이 누락**됐다. m6는 **풀다운 자체의 부작용 대조군**이라, 빠지면 6.3(p)의 「m6 vs m0에서 `tz`만 6 → 8」 판정이 **성립하지 않는다**. ★ **본 것을 요약하는 단계에서 원소가 사라진** (g)① 동형이며, **"A / B" 묶음은 원소별로 확인**해야 한다는 규칙이 값을 한 자리다.
- 🔴 **② 해소된 사실을 미결로 되돌릴 뻔했다 — 학습 21의 역방향**: Claude가 대화에서 *"카카오 자동 갱신은 한 번도 확인 못 했다"*고 말했으나, **7.5(e)에 2026-09-05 ④런타임 실증이 이미 등재**돼 있다(실측 grep = 「자동 갱신 배선 ④런타임 실증」 **1건**). ⚠️ 학습 21이 지금까지 잡아 온 축은 *"해소된 줄 알았는데 미결이었다"*인데, 본 건은 **반대 방향** — **등재된 해소를 미결로 날조**하는 축이다. **미결을 세기 전에 해소 표기부터 grep한다.**
- **③ 응답 구조 오기 — 평면 필드로 적었으나 실물은 중첩**: 카카오 리허설 위임이 `skip_reason` · `primary_sent` · `primary_sent_at`을 `/detect` 응답 **최상위 필드**로 적었으나, 실물은 **`notification_status` 하위**다(`models.Notification.to_dict`). **부재가 아니라 중첩**이며, 수행 측이 실물로 정정하고 진행해 **피해 0**이다. ⇒ (a)류(주소 오기)의 **자료구조 판**이다.
- **④ 위임이 6.3(o) 문구를 grep 없이 인용했다**: 「3종」이라고만 옮겼으나 실물 문언은 *"🟡 **[등재 — 2026-09-15 PoC-(48) 실측] 호스트 테스트는 3종이다**"*이고, **같은 줄이 checks 수 · 커버리지 · 최종 실행 결과의 「미측정」까지 함께 규정**한다. ⇒ **문구 전문을 보지 않으면 「무엇이 미측정인지」가 같이 딸려 오지 않는다.** 본 세션은 그 전문을 확인한 뒤 (o)를 **부분 해소**로 처리했다.
- **⑤ MCP 보고서 본문의 라인 번호 인용 3건 — (i)가 닫은 축의 4세션 연속 재발** (계수 단위 = 인용 건수): 2026-09-12 **2건**((i)) → 2026-09-14 **3건** → 2026-09-15 PoC-(48) **1건**((j)③) → **2026-09-15 PoC-(49) 3건**. ⚠️ 본 (k)와 본 세션 `decisions-log.md` 엔트리 · 편집 앵커는 **라인 번호 0건** 사용이다.
- ⚠️ **(d)의 누적 숫자는 본 항에서 건드리지 않았다** — 합산 여부가 **(i)에 사용자 판단 대기**로 등재돼 있다. ⇒ **(d)의 「누적 21건」은 (i) · (j) · 본 (k) 어느 것도 포함하지 않는 값**이다(현재값 서술의 경계 표기).
**(l) PoC-(50) AI catch 사례 ~~6건~~ → 8건 — 근거유형 · 외삽 · 자기모순 · 압축 손실 · 기록 누락 · 사유 오판 (2026-09-16 PoC-(50) 추가 · 같은 날 Set 1 후속 ⑦ ⑧ 추가, 근거유형 = 실측 + 실물 대조)**

- 🔴 **① 근거유형 오표기 — 「무죄 (실측)」의 실제 근거는 코드 확인이었다**: 30.9 반증 가설 ①이 회귀 테스트를 **「무죄 (실측)」**으로 적었으나, 당시 근거는 **가짜 자격증명 문자열 + `app.stt` urlopen 스텁을 읽은 것**이지 **호출 수 대조 실험이 아니었다**. 게다가 그 두 조건은 **T절 테스트에만** 있었고 실제 누출 경로인 **S절 9개 케이스에는 없었다** ⇒ **판정 범위까지 틀렸다**. **2026-09-16 실측으로 뒤집힘**(상세 = 30.9, 원칙 = 카테고리 20). ⚠️ **당시 판정 주체는 문서에 미기록**이다.
- 🔴 **② Claude 속도 외삽 오류 — 입력 길이를 확인하지 않고 왕복 시간을 적용했다**: 스위트가 **2.158초**에 끝난 것을 보고 *"CSR 호출 가능성이 낮다"*고 논증했으나, 근거로 쓴 **왕복 0.9초는 약 4초 음성 기준**이었고 **테스트 입력의 길이를 확인하지 않은 채 외삽**한 것이었다. **콘솔 +12건으로 반증**됐다. ⇒ ★ **판정은 콘솔(관측 장치)로만 한다** — 시간 산술은 가설까지다.
- 🔴 **③ Claude 위임 자기모순 2건 — 같은 문서 안에서 기대값이 충돌했다**: PR #62 위임의 **NC-2 기대값 「스위트 OK」**가 **같은 위임이 요구한 가드 자기검증 요건과 모순**이었고(자기검증이 있으면 OK로 끝날 수 없다), **외부 가드 delta 기대값 「헤더만」**은 **기록 전용 층의 존재를 무시**했다. 수행 측(MCP)이 **★판정 규칙으로 옳게 판단**해 진행했다. ⇒ **위임 본문도 catch 대상**(학습 17)이며, **기대값은 같은 문서 안에서 상호 검산**해야 한다.
- **④ Claude 서술 오류 — 「원격 브랜치 자동 삭제」 단정**: 머지 후 원격 브랜치가 **자동 삭제된다**고 단정했으나, PR #62 실물 타임라인은 **머지 `06:17:48Z` → `head_ref_deleted` `06:26:03Z`(약 8분 뒤, 학부생 계정 동작)**로 **잔존 후 수동 삭제**였다. ⚠️ **repo 설정(Automatically delete head branches) 상태는 미확인**이므로 *"설정이 꺼져 있다"*로도 단정하지 않는다. 🔗 카테고리 20 「Squash 머지된 브랜치는 `git branch -d`가 거부한다」 절의 **「원격은 GitHub 자동 삭제로 이미 깨끗했다」 서술과 상충**한다 — ⚠️ ~~**그 서술의 정정 여부는 본 Set 범위 밖**이며 **여기서는 충돌 사실만 등재**한다.~~ → **병기로 처리했다**(사용자 방침 2026-09-16, Set 1 후속). 카테고리 20의 09-09 서술은 **당시 사실이라 취소선 없이** 오늘 사실을 **병기**했다.
- **⑤ Claude 장치 지정 오류 — 사용 중인 장치를 확인하지 않고 인덱스를 박았다**: 학부생이 **이어폰을 쓰는 중**인데 시험 녹음에 **내장 마이크 `:0`**을 지정해, **첫 시험값(peak 1404)이 이어폰 값이 아니었다**. ⇒ **장치를 확정한 뒤 지정**했어야 한다(학습 13 화면·실물 우선의 하드웨어 판). 최종 실측 = **`:2`**(7.7(m)).
- 🔴 **⑥ 압축 손실 — 「인터폰 노이즈 CER 6.49%」**: 벤치마크 원문의 **열(저음질 전화망)**과 **엔진(CLOVA Speech)**이 **탈락한 요약**이 SSoT에 **CSR 근거로 굳었다**. 정정 = **카테고리 7 머리**. ⇒ (g)① · (k)① 계열의 **세 번째 압축 손실**이며, 이번 건은 **탈락한 것이 수치가 아니라 「그 수치가 무엇의 값인지」**였다.
- 🔴 **⑦ Claude 로그 누락 — 대화형 실측을 heredoc 로그로 남기라고 지시하지 않았다**: PR #62 수정 코드의 **가드 없는 합격 시험**(`Ran 106 tests in 0.242s` OK)과 **콘솔 확인**(15:09 · 15:15)은 **채팅 안에서만** 오갔고 **로그 파일이 없었다**. ⇒ Set 1(`519d802`)이 **근거 로그를 찾지 못해 등재하지 못했다**. **사후 로그 작성 후 본 Set 1 후속으로 등재**했다(상세 = **30.9 부분 해소 블록**). ⇒ ★ **실측은 실행 직후 로그로 굳힌다** — 채팅 기록은 다음 세션으로 넘어가지 않는다.
- 🔴 **⑧ MCP 사유 오판 — 「상충」이라고 쓰기 전에 실행 주체 · 시점을 대조하지 않았다**: Set 1이 위 수치를 **옮기지 않은 절차 자체는 옳았다**(근거 로그 부재). 다만 사유로 든 *「PR #62 본문 "스위트 실행 총 6회 … 전부 가드 아래"와 정면 상충」*은 **틀렸다** — 그 **6회는 PR 작성 세션(MCP) 자신의 실행**이고 **학부생 실행은 그 이후**라 **상충이 아니라 별개 실행**이다. ⇒ ★ **「상충」 판정 전에 두 서술의 실행 주체 · 시점부터 대조**한다(학습 19 「판정의 근거유형까지 재검증」의 시점 판).
- ⚠️ **(d)의 누적 숫자는 본 항에서도 건드리지 않았다** — 합산 여부가 **(i)에 사용자 판단 대기**로 등재돼 있다. 또한 본 (l)은 **인용 오기 계열이 아니라 판정·근거유형 계열**이라 **(d)의 「인용 오기 누적」과 계수 단위가 다르다**(계수 단위 = catch 사례 건수).

**(m) PoC-(51) · PoC-(52) 인용 오기 · 문서-코드 드리프트 5건 (2026-09-18 PoC-(52) 추가, 근거유형 = 실측 grep + 실물 대조)**

- 🔴 **① 「≤80B」의 SSoT 인용처가 어긋났다 — 위임·설계 문서가 6.3(m)을 지목했다**: 실물에서 그 값을 **낸** 자리는 **6.3(j)**(「M5a(80B) 0% / MEM(78B) 0% — ≤80B 62줄에서 손상 0건」, 입력 로그 = **6.3(h)**)이고, **6.3(m)은 그것을 인용해 「시리얼 절단 80B 상한」이라 적는 자리**다. ⚠️ **`decisions.md` 본문에는 6.3(m)을 ≤80B의 출처로 지목한 서술이 0건**이므로 **취소선 대상이 없다** — 오기는 **위임·설계 계층**에서 났다(대조군 = 같은 문서에서 6.3(m)을 **6.4(g)·PR #52 ④런타임**의 출처로 지목한 매치는 생존). ⇒ **값은 맞고 주소가 한 겹 아래였던** (a)류의 변형이다. **값 「≤80B」 자체는 맞다.**
- 🔴 **② 코드 주석의 절 번호 오기 — `routes.py`가 「카테고리 6.2」를 지목한다**: `server/app/routes.py` 주석이 `/enrich` 오디오 구간 근거로 **카테고리 6.2**를 가리키지만, **6.2에는 `/enrich` 오디오 길이 서술이 없다**(대조군 = 같은 절에 `AUDIO_MAX_BYTES`·`IMAGE_MAX_BYTES` 서술 생존, `docs/`에서 「스티칭」 grep **0건**). ⇒ **(a)류(값은 맞고 주소가 틀림)의 코드 주석 판**이며 6.3(k-2) `mic_common.h` 선례와 같은 축이다. ~~⚠️ **코드 무접촉이라 주석 수정은 별도 PR 소관**이고 본 항은 사실만 기록한다.~~ → ✅ **해소 (PR #65 `601e7a2`, 내부 커밋 `fe2b9f9`)**: 인용처를 **「카테고리 6.2」 → 「6.5(a) · 6.7(c)」**로 교체했다(6.5(a) = 「5초」 출처 규명, 6.7(c) = `ENRICH_AUDIO_BUFFERS = 80` → 5.120초). ⚠️ 같은 파일의 나머지 「6.2」 인용 **5건은 실제로 6.2 소관이라 무변경**(계수 단위 = 출현 건수). 상세 = **6.5(a)**.
- **③ MCP 보고서의 SSoT 반영 제안 1건 기각 — 「누출 주체가 SSoT와 다르다」는 오판이었다**: 후속 포렌식 리포트가 *「누출 주체 서술을 분리하라」*고 제안했으나, **30.9와 27.8(l)①이 이미 「T절 `_run_enrich_real`이 아니라 S절 `_run_enrich` 9개 케이스가 누출」로 적고 있다**(grep 확인). ⇒ **제안 ③ 기각.** 유효한 추가분은 **「12 = 단건 8 + 루프 4」 내역**뿐이며 그것만 등재했다(30.9 잔존분 조사 블록). ★ **MCP 보고서의 「SSoT가 틀렸다」도 실물 대조 대상**이다 — 학습 19의 **보고서 판**.
- **④ 코드 주석의 근거 문구 오기 — `mic_common.h`의 「카메라(I2S0)와 페리페럴 분리」**: ESP32-S3의 카메라는 **LCD_CAM 페리페럴**이므로 그 문구는 **ESP32(원조) 프레이밍**이다. ⚠️ **결론(분리됨)은 옳고 근거 문구만 어긋난다** — 실제 분리 근거는 **핀 교집합 ∅ + I2C 포트 분리**다(카테고리 2 · 6.6). ⇒ 그 문장을 그대로 인용하면 오독이 생긴다. ~~**코드 무접촉이라 사실만 기록**한다.~~ → ✅ **해소 (PR #65 `601e7a2` — 코드 + SSoT 쌍, 내부 커밋 `fe2b9f9` · `4e9e942`)**: `firmware/include/mic_common.h` **2곳** + `docs/decisions.md` **카테고리 1 머리**의 프레이밍을 **핀 교집합 ∅ + I2C 포트 분리**(카테고리 2 · 6.6) 근거로 교체했다. 카테고리 1 머리는 **현재값 서술이라 취소선 아닌 교체**로 처리됐다(결론 「분리됨」 무변경).
- **⑤ 문서-코드 드리프트 — 같은 사실을 두 문서가 다르게 적고 있었다**: PR #63의 `probe_modes.h` 상단 주석이 **「m6은 m2와 구성이 동일」**이라 적었으나 실물은 **두 필드**가 다르고, 같은 PR의 Runbook은 **「m6은 m3과 WiFi만 다르다」로 맞게** 적혀 있었다. ⇒ **리뷰에서 잡혀 코드 주석을 실물대로 고쳤다**(모드 테이블 값 변경 0). ★ **드리프트는 「두 문서가 같은 사실을 적는 곳」에서 난다** — 이후 **비인접 쌍 표를 `PROBE_NONADJ_PAIRS` 단일 원천으로 두고 호스트 테스트가 순회**하도록 코드에 고정했다(79 → 97 checks). ⇒ **문서-코드 드리프트의 차단은 「문서를 고치는 것」이 아니라 「코드가 단일 원천을 갖게 하는 것」**이다. 상세 = **6.6(a)**.
- ⚠️ **본 (m)은 (d)의 「인용 오기 누적」 숫자에 합산하지 않는다** — 합산 여부가 **(i)에 사용자 판단 대기**로 등재돼 있다(계수 단위 = 오기·드리프트 건수).
- ✅ **[PR #65 `601e7a2` 정정 요약 — 2026-09-19 머지, 문서 반영 2026-09-19 PoC-(53), 근거유형 = 실측 `git show`]** 위 ② · ④와 6.2 G29 stale(세트 A) · 33.9 클래스 수 오기(세트 D)를 **한 PR 4세트**로 정정했다 — **세트 A** `server/app/constants.py` G29 주석 / **세트 B** `server/app/routes.py` `/enrich` 인용처 / **세트 C** `mic_common.h` 2곳 + 카테고리 1 머리 / **세트 D** 33.9 「4클래스」 → **3클래스**(`other`는 33.6(a)의 선택지일 뿐 구현이 아니다 — 33.2 `Dense(3)` · `CLASSES` 3종 · `PREDICTED_CLASSES` 3종). **커밋 2개 1PR** = `4e9e942` 📝 Docs(SSoT) / `fe2b9f9` 🗃️ Comment(코드 3파일) — 분리 근거 = Type 2종 + `git diff c48779a 4e9e942 -- server/ firmware/ ml/` **빈 출력**(중간 커밋이 main과 코드 바이트 동일이라 빌드 · 회귀가 깨질 수 없다 — stash 실측보다 강한 증명). **검증** = AST 해시 전후 동일(대조군 = 코드 토큰 1개 변경 시 갈림, 복원 증명) / 전처리 출력 md5 동일 / 회귀 106 / `mic_dummy` 빌드 SUCCESS. 추가분 = 6.3(k-2) 헤드룸 주석 쌍(`a918173` · `8200669`). ⚠️ **PR #65가 SSoT에 남긴 회차 라벨 오기 1건**(33.9 「(54)」)은 **27.8(o)①**에서 정정.

**(n) PoC-(53) 오류 4건 — 메커니즘 오기 2 · 위임 자기모순 1 · 근거유형 오진 1 (2026-09-18 PoC-(53) 추가, 근거유형 = 실측 + 실물 대조, 계수 단위 = 오류 건수)**

- **① 🔴 차단 메커니즘 오기 — 「`driver/i2s.h` 때문」이 아니라 먼저 터지는 것은 `Arduino.h`다 (출처 계층 = ③ PR 본문 + ③ 위임 본문)**: PR #64 본문과 본 세션 위임 (L4)가 `uplink_common.h`의 호스트 컴파일 불가 사유를 **`mic_common.h` → `driver/i2s.h` 하나로만** 적었다. 실측(`c++ -fsyntax-only -I firmware/include`)은 **1차 차단이 `uplink_common.h` 자신의 `#include <Arduino.h>`**이고, 가짜 `Arduino.h`를 공급해 그것을 넘긴 뒤에야 `driver/i2s.h`가 드러난다. ⇒ **결론(순수 헤더 분리 필요)은 옳고 메커니즘 서술만 틀렸다** — 학습 16 ★판정 규칙대로 **불변식 유지 + 메커니즘 등가 치환**으로 처리했다(등재 = **6.3(o)**). ★ **27.8(m)④(「카메라(I2S0)와 페리페럴 분리」가 ESP32 원조 프레이밍)와 같은 축** — *"결론은 맞는데 근거 문구가 실물과 다르다"* 계열의 **연속 2회차**다.
- **② 계수 오기 — PSRAM 「4/4 동일」이 실물은 3/3이다 (출처 계층 = ③ 위임 본문 + 로그 원본 요약줄)**: 위임 (E)와 `pr64_interactive.log` 요약줄이 캡처 PSRAM delta를 **「4/4 동일」**로 적었으나, 이벤트 #1은 **`gate=skip`이라 카메라 init 자체가 없다** — `pr64_e2_runtime.log`에 `[MEM:e2-pre-init]` · `cam ms=` 줄이 **#2 #3 #4에만** 있다. ⇒ 실물은 **3/3**이다(등재 = **6.7(d)**). ★ 성격 = **분모 오기**이며, 27.8(l)⑤(기록 누락) 계열이 아니라 **「요약이 원본보다 먼저 굳은」** 경우다 — 요약줄은 사후 정리분이고 원본 로그가 SSoT다.
- **③ 🔴 위임 자기모순 — PR-B 위임 §2-1 ⑦과 §5 Step 9가 양립 불가였다 (출처 계층 = ③ 위임 본문, 발견 = PR #64 작업 중)**: ⑦(「`uplink_common.*`는 additive」)과 Step 9(「`mic_uplink` 바이너리가 변경 전과 동일」)가 **동시에 성립할 수 없다** — additive 대상 TU를 `mic_uplink`가 링크하기 때문이다(실측 **+32 B**). MCP가 지적했고 **불변식(기존 함수·상수 1바이트 무변경)은 유지한 채 증명 메커니즘만 등가 치환**했다(실행 섹션 diff 0 / `nm` 2차 심볼 0 / 문자열 집합 동일). ⇒ **27.8(a) PR #45 §5 Step 4-b와 동형**이며 **학습 16 ★판정 규칙이 작동한 사례**다.
- **④ 🔴 근거유형 오진 — 「상수 미작동」으로 확정했으나 원인은 `urlopen` timeout의 성질이었다 (출처 계층 = 세션 중 Claude 판정, 자기 catch)**: CSR `elapsed_ms = 6,423.73`(상수 3.0초)을 보고 Claude가 **「`STT_HTTP_TIMEOUT_SECONDS`가 작동하지 않는다」**로 판정했으나, 코드 확인 결과 **상수는 `urlopen`에 정상 전달**되고 원인은 `timeout`이 **소켓 연산 단위 상한이지 총 경과 상한이 아니라는 것**이었다(등재 = **7.7(l)**). ⇒ 33.6(e) 계열의 **「설명 안 되는 값을 만나면 도구를 의심하되, 의심 자체도 과잉일 수 있다」**의 재실증이며, 성격은 **원값·코드를 보기 전에 판정을 확정한 것**이다. ★ **①과 ④는 방향이 반대다** — ①은 *"남이 쓴 메커니즘을 그대로 믿었다"*, ④는 *"내가 세운 메커니즘을 코드 없이 확정했다"*. 둘 다 **실물 확인이 판정보다 늦었다**는 한 축이다.
- ⚠️ **(d)의 누적 숫자는 본 항에서 건드리지 않았다** — 합산 여부가 **(i)에 사용자 판단 대기**로 등재돼 있다. ⇒ **(d)의 「누적 21건」은 (i) · (j) · (k) · (l) · (m) · 본 (n) 어느 것도 포함하지 않는 값**이다(현재값 서술의 경계 표기).

**(o) PoC-(53) 2일차(2026-09-18~19) 오류 5건 — 회차 라벨 오기 1 · 위임 범주 불일치 1 · 위임 범위 과소 1 · 위임 수단-불변식 치환 1 · 근거 문구 범위 과대 1 (2026-09-19 PoC-(53) 추가, 근거유형 = 실측 + 실물 대조, 계수 단위 = 오류 건수)**

- **① 🔴 회차 라벨 오기 — 「(54)」는 다음 회차 예고였다 (출처 계층 = ① 인계 패키지 제목 → ③ 위임 본문 · MCP 보고서 → SSoT 1건 유입)**: 인계 패키지 제목 「[PoC-(53) → (54)]」의 (54)는 **다음 회차 예고**였는데 2026-09-18 저녁~2026-09-19 세션이 **현재 회차로 오독**했다 — 채팅방이 갈리지 않아 **같은 회차 PoC-(53)이 이틀에 걸쳤다**. 위임 · MCP 보고서의 (54) 표기는 전부 오기이며, **SSoT에는 PR #65 `4e9e942`로 33.9에 1건 유입**됐다(2026-09-19 정정 — 33.9 참조). repo 밖 로그 3건에는 회차 표기가 없어 실해 없음. ★ 성격 = **6.3(n) 「C-0 라벨 오기」와 동형**(값은 맞고 주체 라벨이 틀림). **오늘 회차 = PoC-(53).**
- **② 위임의 3분법이 실물과 맞지 않았다 — 제4범주가 필요했다 (출처 계층 = ③ 위임 본문)**: 원천 귀속 감사(33.7(h)) 위임이 판정 범주를 「원천 동일 / 조각 후 동일 / 귀속 불가」 **셋으로 지정**했으나, G01~G10(10그룹 / 176파일)은 **셋 어디에도 들어가지 않는다** — 원천이 **전체가 아니라 선두 구간(또는 창)만** 동일하다. MCP가 **제4범주(원천 선두 구간 바이트 동일)를 만들어** 보고했고 불변식(「우리 단계가 새로 만든 동일성 = 0 / 15」)은 유지됐다. ⇒ **학습 16 「불변식 유지 + 메커니즘 등가 치환」 사례**. 대조군 = G11~G15(전체 동일)는 범주 ①에 그대로 들어간다.
- **③ 위임의 「단일 파일」 지정이 드리프트를 남겼다 (출처 계층 = ③ 위임 본문)**: 6.3(k-2) 헤드룸 주석 정정 위임이 대상을 **`mic_common.h` 단일 파일**로 못박아 `a918173`이 그것만 고쳤고, **`mic_test.cpp`에 같은 반증 서술이 잔존**했다(전수 grep 잔여 **1건**, 계수 단위 = 줄 수). MCP가 catch해 같은 PR에 `8200669`로 얹었다. ★ **27.8(m)⑤ 「같은 사실을 두 문서가 다르게 적는 드리프트」의 재발 실증**이며, 교훈은 (m)⑤와 같다 — **정정 대상은 파일이 아니라 「같은 사실을 적는 모든 자리」**다. 상세 = **6.3(k-2)**.
- **④ 위임의 「`run_all` 금지」가 대상을 안 적어 과잉이었다 (출처 계층 = ③ 위임 본문, 발견 = 17.2 베이스라인 1차 §9 정지)**: 불변식은 **「실데이터셋 무변경」**이고 `run_all` 금지는 그 **수단**이었는데, 수단이 불변식처럼 적혀 `test_pipeline` · `test_training_smoke`(둘 다 `TemporaryDirectory` + `make_dummy_dataset` + `resolve_paths(root)` **명시 인자**, 우선순위 = 명시 인자 > env ⇒ 실데이터셋 도달 경로 **코드상 없음**)까지 §9 정지가 걸렸다. 사용자 확정 후 실행했고 **데이터셋 mtime 무변경으로 불변식 충족**을 증명했다(17.2). ⇒ **학습 16 메커니즘 치환의 역방향** — 위임이 **수단을 불변식으로** 적었다.
- **⑤ 근거 문구 범위 과대 — 「`fire_alarm`은 ToF 우회라 무조건 도착 약속이 정확하다」 (출처 계층 = ③ 위임 본문 + SSoT 8.7(a) 동일 문구, 자기 catch)**: PR #66 위임 §2가 그렇게 적었고 **8.7(a)도 같은 문구**로 등재돼 있었으나, `utils.py` 신뢰도 게이트는 **「클래스 무관」**이라 **`fire_alarm`도 신뢰도 게이트는 받는다**(우회는 ToF뿐). 본문 카드 카피는 ToF 문맥이라 **무변경이 맞고** 어긋난 것은 **근거 문구의 범위**다 — 8.7(a)에 경계 병기. ★ **(m)④ · (n)① 「결론은 옳고 근거 문구가 어긋남」 계열의 연속 3회차.**
- ⚠️ **(d)의 누적 숫자는 본 항에서 건드리지 않았다** — 합산 여부가 **(i)에 사용자 판단 대기**로 등재돼 있다. ⇒ **(d)의 「누적 21건」은 (i) ~ (n) · 본 (o) 어느 것도 포함하지 않는 값**이다.

**(p) PoC-(55) 위임 · 판단 오류 7건 — 위임 자기모순 1 · 전제 붕괴 1 · 기호 관례 충돌 1 · 원인 추정 오류 1 · 미확인 가정 1 · MCP 보고서 오기 1 · MCP 보고서 출력 깨짐 1 (2026-09-21 PoC-(55) 추가, 근거유형 = 실측 + 실물 대조, 계수 단위 = 오류 건수)**

- **① 위임 자기모순 — 제외 기준과 hard negative 목록이 충돌했다 (출처 계층 = ③ 위임 본문)**: 네거티브 선별 위임이 제외 ①을 「**`Alarm` 계열 전부**」로 적어 놓고, 같은 위임의 ⓓ hard negative 목록에 **`Telephone` · `Ringtone`**(dev.csv 동시출현상 `Alarm`의 자식)을 넣었다 — **둘을 같이 지키면 겨냥한 hard negative가 통째로 사라진다**. MCP가 **「target 자신과 그 자식만 제외하고 부모는 제외 기준으로 쓰지 않는다 — 미분화 `Alarm`과 `Siren`만 제외」**로 **등가 치환**해 불변식(인터폰 전자음 hard negative 확보)을 지켰다. ⇒ **학습 16** 계열이며 **(o)②와 동형**이다. 상세 = **33.14(b)**.
- **② 🔴 전제 붕괴 — A안의 전제 「잔존 1곳」은 SSoT 서술을 그대로 옮긴 것이었고, 그 SSoT 서술 자체가 좁았다 (출처 계층 = ② SSoT 8.7(c) → ③ 위임 본문)**: `tailwind-merge` 정정 위임의 A안은 **「잔존 = `NotificationTof` 1곳」**을 전제로 세워졌는데, 그 문장은 **8.7(c)를 그대로 옮긴 것**이었고 8.7(c)의 근거는 **전수 조사가 아닌 관측 1건**이었다. 전수 조사에서 **4곳 + 변종 2곳**이 나와 A안이 철회됐다. ★ **「SSoT에 있으니 맞다」가 성립하지 않는 자리** — 등재된 문장에도 **관측 범위**가 붙어 있고 위임은 그 범위를 **떼고 옮겼다**. ⇒ **학습 19**(위임 전제 재검증) 계열. 상세 = **8.7(c-1)**.
- **③ 청취 판정 기호가 한국어 O / X 관례와 충돌했다 (출처 계층 = ③ 위임 본문 → 학부생 입력)**: 스크립트가 `x = target 있음`으로 정의했는데 학부생은 **한국어 O / X 관례대로 `x = 없음`**으로 입력했다(메모 *「없어」* 2건이 단서). 학부생 확인 후 `verdict`를 **뒤집었고 원 입력은 `raw_input` 열에 보존**했다. ⇒ **판정 기호는 도구 쪽 정의가 아니라 사람 쪽 관례를 따라야 한다**는 기록이며, 되돌릴 수 있었던 것은 **원 입력을 지우지 않았기 때문**이다. 상세 = **33.14(e)**.
- **④ 원인 추정 오류 — `curl` 실패를 「봇 차단」으로 추정했으나 실물은 504다 (출처 계층 = ③ 위임 본문)**: Zenodo 메타데이터 1차 내려받기 실패를 위임이 **봇 차단으로 추정**했으나 실물은 **504 Gateway Time-out**(과부하)이었고 `-f --retry`로 성공했다. 🔴 **추정한 원인에 맞춰 우회책을 짰으면 헛수고**였다 — **92 B짜리 에러 응답이 zip 파일명으로 저장**돼 있었던 것이 단서다. ⇒ **학습 19**(근본원인 재검증) 계열. 상세 = **33.14(a)**.
- **⑤ 미확인 가정 — 「로컬 덤프 = 리드타임 0」이 메타데이터 존재를 확인하지 않았다 (출처 계층 = ③ 위임 본문)**: E3이 **로컬 FSD50K 덤프 우선**을 고른 근거는 *「이미 받아 뒀으니 리드타임 0」*이었는데, 덤프에는 **wav 40,966개와 오디오 zip만 있고 라벨 메타데이터가 없었다** ⇒ **§9 정지 1건**. ⇒ **27.7 · 카테고리 27 「repo 구조 가정 검증」의 데이터셋 판**이다 — **「있다」가 「쓸 수 있다」가 아니다.**
- **⑥ MCP 보고서 오기 — `lib/utils.ts`를 8.4 무변경 대상으로 적었다 (출처 계층 = ④ MCP 보고서)**: 보고서가 *「`lib/utils` 변경 = 8.4 무변경 대상을 더 넓게 건드린다」*고 적었으나 **8.4의 무변경 대상 목록에 `lib/utils`는 없다**(실물 대조). 🔴 **결론(B안 채택)은 무변경**이며 어긋난 것은 **근거 문구의 대상 지목**이다 — **(m)④ · (n)① · (o)⑤ 「결론은 옳고 근거 문구가 어긋남」 계열의 연속 4회차.**
- **⑦ MCP 보고서 출력 깨짐 — diff 블록 중복 출력 (출처 계층 = ④ MCP 보고서)**: 보고서 안의 diff 블록이 **중복 출력**됐다. **실물 파일은 정상**임을 **GitHub 원본 대조**로 확인했다. ⇒ **보고서 렌더링 사고이지 산출물 결함이 아니다** — 둘을 섞어 읽지 말 것.
- ⚠️ **(d)의 누적 숫자는 본 항에서도 건드리지 않았다** — 합산 여부가 **(i)에 사용자 판단 대기**로 등재돼 있다((o) 말미와 같은 판정). ⇒ **(d)의 「누적 21건」은 (i) ~ (o) · 본 (p) 어느 것도 포함하지 않는 값**이다.



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
- ~~🟡 **[신규 미결] "도어벨" 표기 잔존 2건 (발견·문서 반영 2026-09-08 PoC-(42), 근거유형 = 실측 grep)**: `dashboard/src/lib/notification-meta.ts:1`(주석) / **`dashboard/index.html:8`(`<meta name="description">` — 브라우저 탭·검색엔진에 노출되는 사용자 가시 문자열)**. 해소 = 대시보드 소액 PR 소관.~~ **✅ 해소 (2026-09-09 PoC-(43), PR #48 `0d3b498`)**: 2건 모두 "초인종"으로 치환. ★ **로직 참조 0건을 치환 전에 확인**했다 — `notification-meta.ts`의 "도어벨"은 분기 주석이고 표현식이 아니다(문자열 비교에 쓰였다면 치환이 분기를 깬다). `server/app/constants.py` **3건은 위 오탐 주의대로 무변경**.
  - ⚠️ **오탐 주의**: `server/app/constants.py` **3건**은 **「"도어벨" 미사용」이라는 컨벤션 서술 자체**라 **정상**이다. grep 결과를 건수로만 세면 이 3건을 위반으로 오독한다 — **매치 문맥을 실독**해야 한다(학습 13).

### 29.6 🔴 학습 16 반대 방향 1호 — MCP가 SSoT를 「관행 추정」으로 덮었다 (2026-09-09 PoC-(44) 신설, 근거유형 = 실측)

카테고리 29는 지금까지 **위임이 틀리고 MCP가 SSoT를 지킨** 사례만 기록해 왔다(29.2 / 29.5, 학습 16). 본 절은 **방향이 반대인 첫 사례**다 — **MCP가 위임 지정을 기각했는데, 그 기각 근거가 SSoT가 아니라 검증 불가능한 관행 추정이었다.**

**(a) 사실관계 (근거유형 = 실측)**
- PR #50에서 MCP가 위임 지정 브랜치 `feat/server-clova-status`를 **`fix/server-clova-status`로 변경**했다. 근거로 "PR #48·#49의 실제 관행"을 들었으나, 그 브랜치들은 **GitHub 자동 삭제로 이미 원격에 없었다** → **검증 불가능한 근거**였다.
- **SSoT 실물은 카테고리 20**: 브랜치 명명 = `feat/{domain}-{task}` **(firmware/ml/server/dashboard/fix)**. ★ **`fix`는 `{domain}` 자리의 값**이지 `feat` 자리를 대체하는 접두가 아니다. 즉 `fix/server-...`는 `{domain}` 값을 접두 자리에 올린 형태로, **SSoT 문법과 어긋난다**.
- **로컬 브랜치 실측으로 확인된 이탈 = 3건**: `fix/ssot-consistency-3`(PR #48) / `fix/server-kakao-token-status`(PR #49) / `fix/server-clova-status`(PR #50). PR #51은 `feat/dashboard-ssr-nc-harness`로 **복귀**했다.

**(b) 🔴 왜 이것이 기록 대상인가 (근거유형 = 논증, 입력 실측 = (a))**
- **MCP의 위임 기각은 지금까지 7회 전부 옳았다**(27.8(a)(b)의 자기모순 catch·NC-2 재규정·커밋 4분리 등). **이번이 첫 오적용**이다. 성공률이 높은 판단 경로일수록 **틀린 1회가 검증 없이 통과**하므로 기록한다.
- ★ **결함의 본체는 "브랜치명이 틀렸다"가 아니라 「출처 계층」이다** — 관행 추정(**③ PR 본문·대화** 계층)이 **① SSoT 문서** 계층을 덮었다. 27.8(e)가 세운 인용 계층 3층(① SSoT / ② 코드 주석·docstring / ③ PR·대화)이 **수행 측 판단에도 그대로 적용**된다는 사례다.

**(c) 재발 방지**
- 🔴 **SSoT 문서와 충돌하는 「관행 추정」은 §9 정지 대상**이다. 위임 지정을 기각하려면 근거가 **① 계층(SSoT 문서 실물)**이어야 하고, ③ 계층(관행·기억)이면 **기각하지 말고 사용자 판단으로 올린다.**
- ⚠️ **관행을 근거로 쓰려면 먼저 실존을 확인한다** — 원격 브랜치는 자동 삭제되고 Squash 머지는 브랜치명을 히스토리에 남기지 않으므로, **"과거 PR이 이렇게 했다"는 사후 검증이 원천적으로 불가능**한 경우가 많다(카테고리 20 「Squash 머지된 브랜치는 `git branch -d`가 거부한다」 참조).

**(d) ⚠️ 소급 정정 불가 — 기록만 남긴다**
- 브랜치 3건은 **이미 원격 삭제**됐고 **Squash 머지라 브랜치명이 커밋 히스토리에 남지 않는다** → 되돌릴 대상 자체가 없다. **실질 피해 0**(브랜치명은 머지 후 어디에도 참조되지 않는다). 그럼에도 등재하는 이유 = **다음 세션이 이 3건을 "관행"으로 다시 인용할 수 있기 때문**이다. 본 절이 그 인용을 차단한다.
- ✅ **PR #51이 `feat/dashboard-ssr-nc-harness`로 복귀**해 이탈은 3건에서 멈췄다.

**관련**: 카테고리 20(브랜치 명명 SSoT · Squash 머지와 브랜치 소멸) / 27.8(e)(인용 계층 3층) / 29.3(정책 — 기존 컨벤션 우선) / 학습 16 · 학습 17

---

## 카테고리 30: 외부 계정 셋업 SSoT (2026-05-13 신설, 2026-05-16 NCP 추가)

> Day 7 (5/13~5/14 오전 통합) AWS + 카카오 디벨로퍼스 + Day 8 (5/16) NCP 셋업 결과 SSoT. 카테고리 22.6의 "5/9~5/14 외부 계정 셋업 전진 활용" 실제 완료 결과.
> **자격증명(액세스 키 / 시크릿 / 토큰 / 카드번호 / 휴대폰번호)은 본 문서 절대 미기록** — `firmware/include/secrets.h` (.gitignore) / 환경변수로만 관리.

### 30.1 AWS (2026-05-13 23:06~23:41, 35분)

- **계정**: 메일 `bagtaegeun278@gmail.com` / Account ID `953926452053` / 별칭 `xorms` / 리전 `ap-northeast-2` (서울)
- **요금제**: 무료 (6개월, 200 USD 크레딧) — 유효 기간 ~2026-11-13. ~~졸작 9/30 종료가 무료 기간 안에 자연 수렴 (30.4 정책 변경 catch 근거)~~ → ⚠️ **[전제 stale — 2026-09-17 PoC-(51) 등재, 근거유형 = 사용자 발언(2026-09-17)]** 위 「자연 수렴」은 **종료일 2026-09-30 전제**에서 성립했다. 사용자가 **발표를 11월(날짜 미정)** · **개발 완료 목표를 10월 중**으로 정정했으므로 **발표 구간이 무료 기간 만료일(2026-11-13)에 근접**한다. ⇒ **「자연 수렴」을 전제로 두지 않는다.** 🔴 **일정 자체의 SSoT는 프로젝트 지침 계층 소관**이며 본 문서는 **기술 영향만** 적는다. ⚠️ **유료 전환 여부 · 대응 방식 = 사용자 판단 대기**(아래 의사결정 트리거 항목과 동일 건).
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
- ~~⚠️ **왕복 실증 ≠ 서버 배선**: `server/`의 STT 호출 코드는 여전히 **0줄**이고 7.6 A-2 자막은 mock 문구다(카테고리 7 STT 항목 동반 등재).~~ **✅ 서버 배선 CLOSE (2026-09-08 PoC-(42), PR #45 `9b3e3a2`)**: 위 왕복 실측 경로가 `server/app/stt.py`로 실코드화됐다(상세 = **7.7**). ⚠️ **배선 CLOSE ≠ 2차 15초 체인 검증**(7.7(j)).

**✅ NCP 호출 한도 문서 내부 모순 해소 + 통보대상 등록 + 일별 한도 상향 (2026-09-08 PoC-(42), 콘솔 화면 catch)**

- 🔴 **판정 — 위 두 숫자는 서로 다른 것을 가리키고 있었다** (8/12 "당일 30,000초 / 당월 300,000초" ↔ 9/02 "시스템 상한 일 10,000,000 / 월 30,000,000"이 자릿수로 충돌해 보였던 건).
  - **실측 1 (화면 catch)**: 한도 **설정 입력 안내**에 월 `1~30,000,000` / 일 `1~10,000,000`이 명기돼 있다 = **이것이 시스템 상한**이다.
  - **실측 2 (화면 catch)**: **한도 변경 이력** 탭의 기록은 **`2026-08-20 10:56:44` 1건뿐**이며, `30,000(Day) / 300,000(Month)` → `500(Day) / 5,000(Month)`으로 적혀 있다.
  - ∴ **판정: 8/12 catch의 "당일 30,000 / 당월 300,000"은 틀린 값이 아니라 그 시점의 「기본 설정값」이었다** — 변경 이력의 "이전 한도"와 **정확히 일치**한다. 9/02의 "일 10,000,000 / 월 30,000,000"이 **시스템 상한**이다. **두 서술은 모순이 아니라 서로 다른 층(설정값 vs 상한)**이었다.
  - ★ **8/12 서술에 취소선을 긋지 않는다** — 그때 화면에 실제로 그렇게 떠 있었고 **잘못 본 것이 아니다**. 여기서는 **두 값이 각각 무엇이었는지 판정만 추가**한다(학습 13 화면 catch 우선 원칙과 정합).
- ★ **소프트 한도 문구 = 원문 실측**: 화면에 **"설정이 적용되는 동안 수 초 내에 한도를 초과하여 호출할 수 있습니다"**라고 명기돼 있다. 아래 **510초 / 설정 500초**의 **초과분이 이 문구 그대로**다 → 위 (3)의 "하드 스톱이 아니다"가 **원문과 실측치 양쪽으로 확증**됐다.
- 🔴 **통보대상 = 담당자 0명이었다 (실측)**: 위 (3)에 "통보대상 등록"으로 적혀 있었으나, 실화면 확인 결과 **임계 70% 알림 체크는 켜져 있었지만 수신자가 0명**이라 **경고가 오지 않았다**. 한도를 넘겼는데도 알림이 없던 이유가 이것이다. → **2026-09-08 통보대상 등록 완료.** ★ **"설정했다"와 "설정이 작동한다"는 다르다** — 체크박스만 보고 넘어간 catch 누락 사례(학습 13 계열).
- **일별 한도 500 → 600초 상향 (2026-09-08 설정, 근거유형 = 논증)**: ★ 무제한이 아니라 **600만 올린 것은 한도 자체를 관측 도구로 쓰기 위함**이다. 폭주 경로가 실재하면 600도 소진될 것이고, **소진 여부 자체가 진단**이 된다(아래 301건 미결의 판정 방법).

**🔴 [신규 미결] CSR 호출 301건 출처 미규명 (발견 2026-09-08 PoC-(42), 근거유형 = 실측)**

- **관측 사실 (콘솔 Usage Statistics 화면 실측)**: `success 34 / failed 267` = 총 **301건**, `usage` **510초**. **510 ÷ 15 = 34**로 success 건수와 **정확히 일치** → **과금은 성공분에만 붙었고 failed 267건은 과금 0**이다. 당월 누적 **525초** = 2026-09-05의 15초 + 2026-09-08의 510초.
- **우리가 낸 것으로 확인된 호출 (서버 로그·화면 실측)**: 본 세션의 `/enrich` 경유 호출 — **HTTP 429 실패 1건**(7.7(i) 로그) + **성공 1건**(7.7(g) ④런타임). **나머지 대다수의 출처는 미규명이다.**
- **반증된 가설 2개 (기록 보존 — 다시 세우지 말 것)**:
  - ① ~~**회귀 테스트가 실 API를 호출했다 → 무죄 (실측)**: 테스트 자격증명이 `"test-ncp-client-id-not-real"`이라는 **가짜 문자열**이고 `app.stt.urllib.request.urlopen`을 **스텁**한다. 가짜 키로는 `success`가 날 수 없다(failed조차 나지 않는다).~~ → 🔴 **❌ 뒤집힘 (실측 2026-09-16 PoC-(50))**: 회귀 스위트 1회가 **실 CSR 12건(+180초)**을 낸다는 것이 콘솔 대조 실험으로 **2회 재현**됐다(아래 부분 해소 블록). ⚠️ **근거유형 오표기 정정** — 당시 「(실측)」으로 적힌 근거는 **코드 확인**(가짜 문자열 · `app.stt` urlopen 스텁)이었고 **호출 수 대조 실험이 아니었다**. 게다가 그 두 조건은 **PR #45가 추가한 T절 테스트(`transcribe` 단위 · `_run_enrich_real`)에만 성립**했고, 실제로 누출한 **S절 `_run_enrich` 경로 9개 케이스에는 둘 다 없었다**. ★ 원 서술은 **삭제하지 않고 취소선으로 보존**한다 — 무엇을 근거로 무죄를 선고했는지가 **27.8(l)①의 사례 본문**이다.
  - ② **다른 Application이 같은 키를 쓴다 → 무죄 (실측)**: Application 목록이 **1개뿐**(`ddingdong-stt`)이다.
- ⚠️ 🔴 **원인 추정을 적지 않는다.** 오늘 세운 가설이 **전부 반증**됐다. 상태는 **「미규명」으로 못 박는다** — 추정을 적으면 다음 세션이 그것을 전제로 읽는다(학습 19). → **[2026-09-16 PoC-(50)] 원인 경로는 실측으로 규명됐다(아래 부분 해소 블록). 단 09-08 구성분은 여전히 미규명**이며, 위 원칙은 **그 잔존분에 대해 그대로 유효**하다.
- **판정 방법 (다음 세션 액션)**: **일별 한도 600 + 통보대상 등록** 상태에서 **재발 여부를 관측**한다. 재발하면 한도 소진과 70% 알림이 **동시에** 신호를 준다 — 관측 장치를 먼저 세우고 원인을 나중에 본다(카테고리 20 「계측 → 실측 → 판정」 동형).
- ⚠️ **보안 이슈 가능성을 배제하지 않았다** — 다만 **근거가 없으므로 단정하지 않는다.** 현재까지 자격증명은 `.env` 경유이며 본 문서·커밋 미기록 상태가 유지되고 있다(30.7·본 절 원칙). → **[2026-09-16 PoC-(50)] 재발분(09-09~09-16)은 회귀 테스트로 설명됐다 — 외부 도용 정황 없음(⚠️ 실측이 덮은 범위 한정)**. **09-08 구성분은 미조사**이므로 본 항의 「배제하지 않았다」는 **그 잔존분에 대해 유지**한다.


**🆕 [부분 해소 — 2026-09-16 PoC-(50)] 위 301건 미결의 원인 경로 규명 + 재발 방지 (PR #62 `bc0df74`)**

> ★ **미결 제목에 취소선을 긋지 않는다** — 규명·차단된 것은 **재발분(09-09~09-16)의 원인 경로**이고, **발견 당일인 09-08 301건의 구성은 여전히 미조사**다. 아래는 해소분과 잔존분을 분리해 적는다.

- **[실측 — 콘솔 화면 catch 2026-09-16 13:47~13:50]** 일별 사용량(Application `ddingdong-stt` / CSR, `success` / `failed` / `usage`초):
  - 09-09 **40 / 212 / 600** · 09-10 **12 / 0 / 180** · 09-11 **36 / 0 / 540** · 09-15 **40 / 128 / 600** — 이상 **툴팁 값**.
  - 09-12 · 09-13 · 09-14 = **0 / 0 / 0** — ⚠️ 이 3일은 **그래프 판독**(0선 위 점, 툴팁 미확인)이라 **근거 등급이 위와 다르다**.
  - 전 날짜에서 `usage = success × 15`가 **정확히 일치**한다(15초 단위 과금 — 위 301건 관측과 동형).
- **[실측 — 대조 실험 2026-09-16]** 서버 · 터널 · 대시보드를 **전부 종료**하고(실행 전 5000 · 5173 **LISTEN 0** · `cloudflared` 프로세스 **0** 확인) **한 번에 한 변수**로 측정했다. 계수 단위 = **CSR 호출 건수 / 초**.
  - 기준값(14:08 확인, 리허설 `/enrich` 1건 반영) = 09-16 **1 / 0 / 15초**.
  - 1회차 실행 **14:11** `Ran 104 tests in 2.158s OK` → 14:18 확인 **13 / 0 / 195초** (**+12 / +180초**).
  - 2회차 실행 → 14:35 확인 **25 / 0 / 375초** (**+12 / +180초**).
  - 두 실행 모두 **카카오톡 도착 0건**(학부생 확인) ⇒ 외부로 나간 것은 **STT(CSR)뿐**이다.
  - ⇒ **스위트 1회 = 실 CSR 12건 = +180초**(**n=2 재현**). 일 한도 600초의 **30%**다.
- **[실측 + 논증 — 읽기 전용 진단, 소켓 가드 아래 스위트 1회]** 원인 체인:
  - ① `server/app/config.py`가 import 시 `load_dotenv(server/.env)` → `Config` 클래스 본문이 `NCP_CLIENT_ID` · `NCP_CLIENT_SECRET` **실값**을 읽는다.
  - ② `_TestConfig(Config)`가 **카카오 4항목만** 빈 문자열로 덮고 **NCP 2항목은 덮지 않는다** → `current_app.config`에 **실값이 남는다**.
  - ③ `stt.is_real_mode()`가 **True** → `/enrich` 경로 **9개 테스트**가 `stt.transcribe`로 **실 CSR을 호출**한다.
  - ④ STT 성공·실패가 **모두 `None` 자막으로 흡수**돼 단언에 영향이 없다 → **`Ran 104 tests` OK인 채로 누출**된다.
  - **대조** = 정적 추적 **12건** = 가드 기록 **12건**(카카오 **0** · 우회 **0**) = 콘솔 **+12건** ⇒ **세 경로가 같은 수**다. 가드 실행 후 콘솔은 **무변동**(14:53 확인 = **25 / 0 / 375초**)이었다 ⇒ 가드 차단이 유효했다.
- **[실측 — 수정 후 가드 없는 합격 시험 2026-09-16 15:10]** PR 브랜치 **`eb06be3`**에서 **외부 가드 없이** 스위트를 **1회** 실행했다(`PYTHONPATH` 미지정 = `/tmp/netguard` **미적용** · `HTTPS_PROXY`/`HTTP_PROXY` **미지정** · 서버 · 터널 · 대시보드 **종료 상태 유지**). 계수 단위 = **CSR 호출 건수 / 초**.
  - 실행 **15:10:12 ~ 15:10:13** → **`Ran 106 tests in 0.242s` OK**.
  - 콘솔: 실행 전 **15:09 = 25 / 0 / 375초** → 실행 후 **15:15 = 25 / 0 / 375초** ⇒ **변동 0**.
  - ⇒ **수정 코드는 외부 가드 없이도 실 CSR 호출 0건**(**n=1**). ⚠️ 콘솔은 **일 단위 집계**라 15:10 실행분만 분리 관측한 것이 아니라 **직전값 대비 무변동으로 판정**한 것이다.
  - 참고치(**판정 근거 아님**) = 스위트 시간 **2.158초**(104 케이스) → **0.242초**(106 케이스). ★ **판정은 콘솔(관측 장치)로만 한다**(27.8(l)②).
  - ⚠️ **머지 후 `main` `bc0df74`에서의 재실행은 하지 않았다** — 테스트 파일 동일성(`git diff --quiet`)으로 갈음했다.
  - ⚠️ **사후 기록**: 실행 직후 로그를 남기지 않아 Set 1(`519d802`)이 등재하지 못했고, **누락 발견 후 대화 기록에서 옮겨 적은 로그**(repo 밖 `~/ddingdong-측정결과/2026-09-16/pr62_postfix_unguarded_run.log`)가 근거다. **발견일 = 반영일 = 2026-09-16**이며 **실측 시각은 15:10**이다. 누락 경위 = **27.8(l)⑦ · ⑧**.
- **[논증 + `git` 실측] 발생 시점**: 누출 테스트는 **PR #44(2026-09-05)**가 작성한 것이고, **PR #45(2026-09-08)**가 NCP 키와 real 분기를 추가하면서 **테스트 코드 변경 0줄로 실 호출자로 전환**됐다. ⇒ ★ **"그날 그 테스트 파일을 건드리지 않았다"가 무죄의 근거가 되지 않는다.**
- **[수정 — PR #62 `bc0df74`]** 변경 = `server/app/tests/test_detect_regression.py` **1파일**(`git show --stat` = **118 insertions / 3 deletions**), **제품 코드 0줄**.
  - **A · NCP 자격증명 격리**: `_TestConfig`에 `NCP_CLIENT_ID = ""` / `NCP_CLIENT_SECRET = ""`(카카오 4항목과 **동형**). real 모드 케이스는 `_FAKE_NCP_CREDS`를 `patch.dict`로 덮으므로 **영향 없다**.
  - **B · 외부 연결 시도 즉시 실패 가드**(stdlib만, 같은 파일 안): `setUpModule`이 `socket.socket.connect` · `connect_ex` · `socket.create_connection`을 감싸 **루프백 포함 모든 연결 시도**를 거절하고 `host:port`를 **기록**하며, `_NoNetworkTestCase`의 `addCleanup`이 **기록 1건 이상이면 그 테스트를 FAIL**로 끝낸다. 모듈의 **모든 `TestCase`가 이 베이스를 상속하는지** `setUpModule`이 검사한다. **가드 자기검증 2건** 포함.
  - **negative control 3종 [문서 인용 — PR #62 본문]** (계수 단위 = **테스트 메서드 수**): **NC-1** A 되돌림 · B 유지 → **누출 9건 FAIL**(메시지에 `127.0.0.1:9`, 외부 가드 소켓 층 delta **0** = B가 먼저 막았다) / **NC-2** A 되돌림 + **실패 판정만** 무력화 → **9건이 조용히 OK**(= 기각 설계가 그대로 재현) + **자기검증 1건만 FAIL** / **NC-3** A 되돌림 + B 전체 무력화 → **원 상태 재현**(외부 가드 소켓 층 **12건**) + **자기검증 2건 FAIL**.
- **[실측 + 문서 인용] 수정 후**: 테스트 수 **104 → 106**(`NetworkGuardSelfTest` 2건 — 현재값 서술 = **7.5(i)**). 소켓 가드 아래 스위트 1회에서 **NCP host 시도 12건 전부 차단 · 콘솔 무변동**이었다(PR #62 본문). 머지 후 `main`의 테스트 파일은 **PR 브랜치 `eb06be3`와 동일**하다(`git diff --quiet bc0df74 eb06be3 -- server/app/tests/test_detect_regression.py` **통과**, 근거유형 = 실측).
- **[정황 — 산술, 원인 확정 아님]** `success + failed`가 **12의 배수**인 날이 있다: 09-10 = **12**(1회분) · 09-11 = **36**(3회분) · 09-15 = **168**(14회분) · 09-09 = **252**(21회분). 09-09 · 09-15는 **PR 다수 머지일**이고, **NC 절차가 baseline + 변형마다 스위트를 재실행**하는 구조라 코드 PR 날에는 실행 횟수가 많아진다. ⚠️ **이것은 정황이지 원인 확정이 아니다** — ~~누가 몇 회 돌렸는지의 **실행 기록 자체는 없다**.~~ → **정정 (2026-09-17 PoC-(51), 근거유형 = 실측)**: **실행 기록은 있었다** — 로컬 트랜스크립트를 4채널로 확장해 세션 ID · 시각 단위로 복원했다(아래 잔존분 조사 블록). 「정황이지 원인 확정이 아니다」는 **그대로 유효**하다.
- **[설계 작동] 일 한도 600초가 관측 장치로 값을 했다**: 위 「일별 한도 500 → 600초 상향」의 **설계 의도 그대로**, 09-09 · 09-15에 `success` **40**(= 600 ÷ 15)에서 멈추고 이후가 `failed`로 누적되는 **모양 자체가 신호**였다. ⚠️ 단 `failed`의 **오류 코드(429 여부)는 콘솔에서 미확인**이므로 「한도 소진 후 거절」은 **논증**이다.
- 🔴 **[잔존 — 미조사]** **09-08의 301건(`success 34` / `failed 267`)은 12의 배수가 아니다** → 위 스위트 누출만으로는 설명되지 않는다(그날은 **테스트가 추가되던 날**이라 스위트당 호출 수 자체가 달랐을 수 있다 — **논증, 미검증**). ~~**09-10 · 09-11에 누가 스위트를 돌렸는지**도 문서에 기록이 없다.~~ → **정정 (2026-09-17 PoC-(51), 근거유형 = 실측)**: **기록이 있었다** — **09-10 = 1런 · 09-11 = 3런**이 MCP 세션 트랜스크립트에서 시각과 함께 복원됐고 **콘솔 값 12 · 36과 정확히 일치**한다(아래 블록). ⇒ **본 미결은 부분 해소이며 제목은 유지**한다.
- ⚠️ **진단용 소켓 가드(`/tmp/netguard` — `sitecustomize.py` · `nc_a.py` · `log.jsonl`)는 repo 밖 · `/tmp`라 재부팅 시 소실**된다. repo 안에 남은 자산은 **PR #62의 B(같은 파일 안 stdlib 가드)뿐**이다.
- 🔗 **방법론 등재** = 카테고리 20 「조용한 가드 금지 · 결과만 보는 검증 · 코드 읽기 ≠ 호출 수 실측」 / **AI catch 사례** = **27.8(l)** / **첫 어절 누락 관측** = **7.7(h)**.


**🆕 [잔존분 조사 종료 — 2026-09-17 PoC-(51)] 실행 채널 확장 재집계 + 09-08 판정 = 부분 설명(배분 불가)**

> 읽기 전용 조사다 — repo 쓰기 0 · 테스트 실행 0 · **실 API 호출 0** · 콘솔 원자료 미열람. 리포트 원본 = repo 밖 `~/ddingdong-측정결과/2026-09-17/csr_0908_forensics/` 및 `csr_0908_forensics_followup/`(`.gitignore` 차단분 — SSoT엔 요약만). **방법론(5채널) 등재 = 카테고리 20.**

- **[실측] 1회당 12건의 커밋 범위 재확인**: `9b3e3a2` ~ `d30b640`의 14개 커밋에서 누출 케이스 **9개 / 12건**이 동일하고, `a431961`(STT 배선 없음) = 0, `bc0df74`(`_TestConfig`가 NCP를 덮음) = 0이다. **내역 = 12 = 단건 8 + 루프 4**(정적 추적기 3판이 PR #62 NC-3 소켓 계측 12건과 일치). ⚠️ 정적 추적기는 **두 판이 틀렸고**(주석 문자열 오인 · 클래스 레벨 문장 흡수) 코드로 원인을 규명해 교정했다 — 학습 19 적용.
- **[실측] 09-10 · 09-11 교정**(계수 단위 = 스위트 실행 수 / CSR 호출 건수):

  | 날짜 | 가시 `Ran` 출력 | × 12 | 콘솔 | 판정 |
  |---|---|---|---|---|
  | 09-10 | **1회**(09:34 KST, `Ran 102`) | 12 | 12 | **일치** |
  | 09-11 | **3회**(09:49 · 11:01 · 11:11 KST, 각 `Ran 102`) | 36 | 36 | **일치** |

- **[실측] 09-09 = 252 정확 일치**: 부모 트랜스크립트의 전체 스위트 **20회** + **서브에이전트 1회**(11:05 KST, `Ran 89`) = **21회 × 12 = 252**. ★ 직전 방법(top-level glob만 읽음)은 서브에이전트 파일을 **놓쳐 부족 12**였다 — 채널을 늘려 메워졌다.
- 🔴 **[실측] 09-15 = 부족 24~48이 남는다**: 전체 스위트 **10회 = 120**(+ 출력 없는 하네스 0~2회 = 0~24) vs 콘솔 **168** ⇒ **부족 24~48(2~4회분)**. **로컬 기록이 덮지 못하는 실행이 09-15에 있었다.**
  - **[논증] 후보 = 학부생 터미널 실행.** **7.5(i)에 「2026-09-15 학부생 로컬 `venv/bin/python3 -m unittest …` → `Ran 104 tests` OK」 기록이 실존**하는데, 포렌식이 훑은 셸 히스토리 12파일에서는 `unittest` **0건**이었다(대조군 = 같은 파일에서 `python3 -m` **11~20건** 생존). ⇒ **셸 히스토리가 터미널 실행을 담지 못할 수 있다**는 뜻이며, **최소 12건**이 그 경로로 설명될 수 있다. ⚠️ **잔여를 「12 단위 2~4회분」으로만 읽는 것도 가정**이다 — **확정하지 말 것.**
- 🔴 **[실측 + 논증] 09-08 재집계 — 판정 = 부분 설명(배분 불가)**:
  - 가시 채널 = 배선 전 1런(0) + 배선 판정 불가 1런(0~12) + 배선 후 11런(132) + 확인된 `/enrich` 경유 2건 ⇒ **134 ~ 146**.
  - 🆕 **숨은 채널 = 출력 캡처형 NC 하네스 24~28런**(`subprocess`로 전체 모듈을 변형마다 돌리고 `capture_output=True`로 삼켜 `Ran` 줄이 결과에 남지 않는다) ⇒ **288 ~ 336**.
  - **재집계 범위 = 422 ~ 482**이고 하한까지 합치면 **134 ~ 482**다. **콘솔 301은 이 범위 안**이다.
  - ⚠️ **그럼에도 배분이 불가능하다**: 「매 실행 = 12」는 그 시각 `server/.env`의 NCP 2항목이 실값이었을 때만 성립하는데, 09-08 트랜스크립트에서 값이 보이는 결과는 **0건**(이름 언급만)이고 `.env`는 열람 금지다. NC-2(재시도 루프 추가) 변형은 1건당 호출이 2회 이상일 수 있어 상한이 더 오를 수 있다. ⇒ **어느 실행이 실 호출을 냈는지 배분할 수 없다.**
  - ⇒ **판정 = 부분 설명.** 🔴 **미규명 상태를 유지**하며 **원인을 지정하지 않는다**(위 「원인 추정을 적지 않는다」 원칙이 잔존분에 그대로 유효).
- **[실측] 외부 도용 배제 여부 — 날짜별로 다르다**: 09-09는 로컬 기록 21회 × 12 = 252로 **정확히 맞아** 실측이 덮은 범위(로컬 트랜스크립트 3디렉터리 + 셸 히스토리 12파일 + 측정결과 폴더) 안에서는 제3자 호출이 섞였을 여지가 좁다. 🔴 **09-08 · 09-15는 배제하지 않는다** — 09-08은 배분 불가, 09-15는 24~48건이 로컬 기록 밖이다.
- **[실측] 타 프로젝트 디렉터리는 대상일 0건**이다(대조군 = 같은 스캔에서 **09-16** 타 디렉터리 세션이 repo 절대경로 28줄 · `Ran` 7회로 생존). ⇒ 「다른 폴더에서 켜진 세션」 현상은 실재하나 **대상일(09-08 · 09-09 · 09-15)에는 없다**.
- ✅ **조사 종료 방침 (2026-09-17)**: **301건 출처 추적을 여기서 종료**한다. 이후 감시는 **NCP 콘솔 일별 값**으로 한다 — 원인 추적이 아니라 **재발 관측**이 판정 장치다(위 「판정 방법」과 동형).

**🆕 [감시 기준점 — 2026-09-17 PoC-(51), 근거유형 = 실측 툴팁 값]** 콘솔 일별 사용량(`ddingdong-stt` / CSR, `success` / `failed` / `usage`초, 확인 시각 **2026-09-17 14:49 KST**):

- **09-16 = 35 / 0 / 525** — 15:15 확인값 25 / 0 / 375 + **CSR 소규모 실측 10건(+150초, 7.7(m))** = 35 / 0 / 525로 **예상과 일치**한다. ⇒ 15:15 이후 추가 호출은 **그 10건뿐**이다. ⚠️ 7.7(m)이 「콘솔 대조 미실시」로 남긴 꼬리표가 **여기서 해소**됐다.
- **09-17 = 0 / 0 / 0**(하루 중간값). 같은 날 돌린 위임 3건의 「실 API 호출 0」 보고와 정합한다.
- `usage = success × 15`가 **전 날짜에서 정확히 일치**한다(35 × 15 = 525).
- ⇒ **PR #62 이후의 감시 기준점 = 0이다. 0이 아니면 설명이 필요한 신호로 본다.**
- **한계**: 09-17은 **하루가 끝나지 않은 값** / 콘솔 반영 지연 **최대 약 5분**(2026-09-16 관측) / **일 단위 집계라 호출 시각 분리 불가** / 09-12 ~ 09-14는 이번에도 **툴팁 미확인**(그래프상 0).
- 🆕 **[감시 기준점 갱신 — 발견 2026-09-18 / 문서 반영 2026-09-19 PoC-(53), 근거유형 = 실측 툴팁 값, 확인 시각 2026-09-18 18:35 KST]** **09-18 = 3 / 0 / 45**. **예상값과 정확히 일치** — 산출 근거 = PR #64 ④런타임 4이벤트(6.7(d)) 중 #1은 `gate=skip`이라 `/enrich` 미호출, #2 · #3 · #4가 CSR 경유(#4는 보드 `-11`이나 서버는 STT 완료 — 6.7(e)에 `stt` 실존). 3건 × 15초 = 45초, `usage = success × 15` 성립. ⇒ **PR #62 이후 기준점(0 외 추가분은 우리가 낸 호출만) 유지 확인. 설명이 필요한 신호 0건.** 확인 시점 서버 · 터널 · 대시보드 **전부 미기동**(`lsof` 5000 CLEAN, 18:31). 로그 원본 = repo 밖 `~/ddingdong-측정결과/2026-09-18/ncp_console_0918_check.log`(본 등재 시 전문 대조).
  - ⚠️ **한계**: 09-18은 **18:35 시점의 하루 미종료 값** / 콘솔 반영 지연 **최대 약 5분** / **일 단위 집계라 호출 시각 분리 불가** — 「이 3건이 14:47~15:00분」임은 **서버 로그 근거이지 콘솔 근거가 아니다**.
  - ⚠️ 같은 화면에서 **09-11 540 / 09-12~14 0 / 09-15 600 / 09-16 525 / 09-17 0**(usage초)이 **그래프 판독**으로 관측됐다(**툴팁 미확인**) — 위 기재값(09-11 36 / 0 / 540 · 09-15 40 / 128 / 600 · 09-16 35 / 0 / 525 · 09-17 0 / 0 / 0)과 정합하나 **근거 등급이 다르다**(자릿수·모양 수준).

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
  - 🆕 **[실측 보강 — 2026-09-18 PoC-(52), 근거유형 = 실측]** 위 「~6KB」는 **2026-06-22 단독 검증 시점 값**이며 무변경이다. 더 좁은 실측 = **QVGA 5,353 ~ 5,438 B** / **VGA 13,791 ~ 13,910 B**(마이크·ToF·WiFi 동시 구동 조건). 캡처 소요 = 주기 캡처 **1 ms** · 연속 캡처 **최대 71 ms**. **프레임버퍼 PSRAM 실점유 = 30,952 B**이고 `esp_camera_deinit`이 **동일 바이트를 반환**한다(누수 0). 상세 = **6.6(c)**.
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
  - 🔴 **[2026-09-15 PoC-(48) 추가 — 위 수치는 무변경, 청정값 병기]** 본 424건에 **train/val과 바이트 동일한 클립 79건**이 섞여 있음이 실측됐다(계수 단위 = 클립 수). **누수 제외 청정 345건 기준 = accuracy 0.8609 / macro_f1 0.8367**이며 차이는 **accuracy −0.026 / macro_f1 −0.011**, **영향은 `fire_alarm` 한 클래스에 국한**된다. ⇒ 위 **macro_f1 0.848은 실질적으로 방어된다.** ⚠️ **대응 방향 = 사용자 판단 대기**. 상세·경계·한계 = **33.7**.

  | class | precision | recall | f1 | support |
  |-------|-----------|--------|-----|---------|
  | doorbell | 0.730 | 0.742 | 0.736 | 62 |
  | knock | 0.873 | 0.889 | 0.881 | 108 |
  | fire_alarm | 0.932 | 0.921 | 0.927 | 254 |

- **의의**: 사전테스트 pre-trained Top-1(초인종 30 / 노크 40 / 화재 20%) 대비 **대폭 상승** → 카테고리 4 fine-tuning 필요성 수치 확정.
- **confusion 특이점**: `doorbell → fire_alarm` 오분류 **10건(최다)**. doorbell이 최소 클래스(support 62) → **8주차 직접 녹음(초인종 90 필수, 카테고리 5)** 으로 보강 예정. ※ **안전 방향 편향**: 역방향 `fire → doorbell` 놓침은 8건뿐 = 덜 위험한 쪽으로 편향(화재 누락 최소화).
- **체크포인트**: `ml/models/yamnet/best.keras` 저장(git 미커밋, `.gitignore`).
- **SavedModel export ✅ 완료 (2026-07-01 PoC-(22), PR #15)**: `ml/training/export.py` 독립 엔트리포인트(`python -m ml.training.export`)로 **재학습 없이** `best.keras`(head) + frozen YAMNet 합성 → 서빙 SavedModel 산출. 서빙 시그니처 = 입력 `waveform (1, None) float32`(배치 1 고정·단일 클립) → 출력 `(1, 3) float32`(라벨 순서 = `CLASSES` 상속 doorbell=0/knock=1/fire_alarm=2). 산출 아티팩트 = `ml/models/yamnet/inference_savedmodel/`(git 미커밋, `.gitignore`). 방식 = `tf.saved_model.save` → **Keras 3 `model.export()`** 로 전환하여 미추적 리소스 해소. ※ **근본원인 정정**: 당초 전제("frozen hub backbone 변수 미추적")는 방향은 맞았으나 정확한 메커니즘은 **`build_inference_model`(model.py)이 raw `hub.load()` 객체를 Keras `Lambda`(`yamnet_backbone`) 클로저로 캡처 → Lambda가 클로저 trackable을 객체 그래프에 미등록** → `.export()`의 `ExportArchive`가 서빙 `tf.function` 트레이스로 캡처 리소스를 함께 추적·직렬화해 해소(학습 19 정합 — 진단 재검증 후 실측 메커니즘 반영). 학부생 로컬 실 YAMNet export + reload 추론 검증 통과.
  - 🟡 **[등재 — 2026-09-15 PoC-(48) 실측] `labels.json`의 위상**: export 산출 폴더에 `ml/models/yamnet/labels.json`이 **실존**한다(구조 = `{"classes": [...], "index": {...}}`, 순서 **doorbell / knock / fire_alarm**, **git 미추적**). 🔴 **정본 문구는 위의 「라벨 순서 = `CLASSES` 상속」이며 무변경**이다 — `labels.json`은 그 상속의 **배포 스냅샷**이지 **출처가 아니다**. ⚠️ 이 파일은 그동안 decisions.md **0건**이었다(2026-09-15 실측, 대조군 = 같은 파일에서 `export` **3건** 생존). 🆕 **PR #60이 이 파일을 검증 대상으로 승격**시켰다 — 게이트 축 하네스가 **실행 시점**에 `labels.json` ↔ `app.constants.PREDICTED_CLASSES` 순서를 대조하고 어긋나면 **종료 코드 4**로 죽는다(상세 = 33.8). ⚠️ **git 미추적**이므로 clone 직후에는 `python -m ml.training.export` 선행이 필요하다.

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

### 33.6 실모델 첫 서버 투입 — OOD 스윕 + held-out 재현 + 게이트 축 실측 (2026-09-12 PoC-(46) 신설)

> 2026-07-01에 산출한 서빙 SavedModel(33.2)을 **서버에 처음 실제로 물린** 세션이다. 지금까지의 ④런타임(6.4(g) 등)은 **전부 mock ML**이었다. 로그 원본 = repo 밖 `~/ddingdong-측정결과/2026-09-12/`(`realmodel_ood_sweep.log` · `realmodel_holdout_eval.log`, `.gitignore` 차단분 — SSoT엔 요약만).

**(a) 🔴 OOD 스윕 — 학습 분포 밖 입력이 `fire_alarm`으로 수렴한다 (근거유형 = 실측, 각 조건 n=1)**

- **실모델 확증 3축**(mock 반증): 프로세스 **RSS 475,920KB** / TF 라이브러리 매핑 **54개** / **동일 입력 2회 `all_scores` 완전 일치**(mock은 난수라 불가능).
- **입력** = 합성 PCM16 **16kHz mono**(voicelong 2.5초 / voiceshort 0.7초 / 나머지 2초). **게이트** = `CONFIDENCE_THRESHOLD=0.7` strict `<`.

  | 입력 | 예측 | 신뢰도 | 발송 |
  |---|---|---|---|
  | silence | `fire_alarm` | 0.62 | False |
  | whitequiet | `knock` | 0.80 | **True** |
  | whiteloud | `fire_alarm` | 0.61 | False |
  | sine1k | `doorbell` | 1.00 | **True** |
  | knocklike | `knock` | 0.65 | False |
  | voiceshort (*"안녕"*) | `fire_alarm` | 0.87 | 🔴 **True** |
  | voicelong (*"안녕하세요 택배입니다"*) | `fire_alarm` | 0.99 | 🔴 **True** |

- **판정**: 모델은 **입력을 구분한다**(sine1k → doorbell 1.00 / knocklike → knock 0.65). 그러나 **학습 분포 밖 입력**(목소리·무음·고에너지 잡음)은 **`fire_alarm`으로 수렴**한다. 🔴 **사람 목소리 2건이 게이트를 넘어 실제 카카오톡이 발송됐다** — 길수록 신뢰도가 **오른다**(0.87 → 0.99).
- ⚠️ **진폭만으로 클래스가 바뀐다 (n=1)**: whitequiet / whiteloud는 `random.seed(42)` **동일 파형**이고 **진폭만 0.05 vs 0.9**인데 **knock(0.80, 발송) ↔ fire_alarm(0.61, 차단)**으로 갈렸다.
- ⚠️ **서버 게이트는 설계대로 작동했다** — 0.62 · 0.61 · 0.65를 **정확히 차단**했다. ⇒ **게이트 결함이 아니라 모델의 분포 밖 거동**이다. 이 둘을 섞어 읽지 말 것.
- ⚠️ **한계**: 합성음이라 **실 초인종·노크·화재경보 음원이 아니고**, 부스 소음 환경 미재현 · 실 인터폰 음색 미반영 · **ToF 미결합**이다. **각 조건 n=1.**
- 🔴 **대응 방향 = 사용자 판단 대기** (임계 재검토 / 4번째 클래스 / 재학습 / 시연 각본 조정). **n=1 실측 위에 임계·정책을 확정하지 말 것.** 파급 = **26.10(d)**(부스에서 대화 소리가 화재 알림을 낼 수 있다). 🆕 **[2026-09-15 PoC-(49)] 조건 축을 넓힌 확장 스윕 = (f)** — **「각 조건 n=1」 제약은 (f)로 완화되나 대응 방향은 여전히 미확정**이다. 🆕 **[2026-09-17 PoC-(51)] 판단 입력 추가 = (g)** — **실제 한국 초인종·인터폰 음원**(전자음 인터폰 · 새소리 차임)에서도 `presence` 무관 발송이 관측됐다. ⇒ 본 미결의 입력이 **합성 OOD에서 실음원으로 넓어졌다**. 🔴 **대응 방향은 여전히 미확정**이다. 🆕 **[2026-09-20 PoC-(54)] 「4번째 클래스」 선택지의 판단 입력 = 33.10(g)** (근거유형 = 실측, 계수 단위 = 세그먼트 수) — 별개 pretest repo `audioset_filter.py`의 `TARGET`에 **`smoke_detector`(`/m/01g50p`)가 4번째로 이미 있었고**, 세그먼트 목록 **349건**(balanced_train **183** / eval **166**)이 csv로 남아 있다. 🔴 **그러나 오디오는 0이다**(긁기는 실행됐고 다운로드는 안 됐다) — 목록만으로 클래스가 서지 않으며, csv의 YouTube 링크 **생존률도 미확인**이다. ⚠️ **`smoke_detector`는 `fire_alarm`과 같은 계열 경보음**이라 본 (a)의 OOD 축(목소리·잡음이 `fire_alarm`으로 수렴)이 **완화되는지는 미실증**이다 — **두 축을 섞어 읽지 말 것.** ~~🔴 **대응 방향은 여전히 미확정**이다.~~ → 🆕 **✅ 대응 방향 확정 (사용자 결정 D4 · E1~E4 — 2026-09-21 PoC-(55), 근거유형 = 사용자 결정, 상세 = 33.13)**: **4번째 클래스 `other` 신설**로 확정됐다(D4). 임계 재검토 · 시연 각본 조정은 **채택되지 않았고**, **재학습이 실행 축**이다. 🔴 **합격 수치는 재학습 후**이며(E4) **본 (a)의 n=1 실측 위에 임계를 확정한 것이 아니다.** ⚠️ **`smoke_detector` 축은 보류**다 — `fire_alarm`과 같은 계열 경보음이라 **본 (a)의 OOD 축 해결책이 아니라는 판정**(사용자 결정 2026-09-21)이며, 위 🆕 2026-09-20 단서는 **무변경**이다.

**(b) ✅ held-out 재현 + 🆕 게이트 축 측정 — (a)의 대조군 (근거유형 = 실측, n=424 전수)**

- **입력** = `05_final_dataset/test` **424개 전수**(62 / 108 / 254). `split_manifest.csv`의 test split과 **개수 일치 = 7월 split 동일**(`source_key` 기반 원본그룹 분리 = 누수 방지 기존 설계).
- 🔴 **[2026-09-15 PoC-(48) 추가] 위 「누수 방지 기존 설계」의 범위 경계**: `source_key`는 **파일명 기준 그룹화**라 **내용이 동일한 파일은 애초에 방어 범위 밖**이었다. 본 424건 중 **79건이 train/val과 바이트 동일**임이 실측됐다(계수 단위 = 클립 수). ⚠️ 위 서술은 **틀린 것이 아니라 범위가 좁았다** — **취소선 대상이 아니다.** ⇒ 아래 재현·게이트 축 수치는 전부 **누수 포함 값**이다. 상세·경계·대응(사용자 판단 대기) = **33.7**.
- **경로** = **HTTP 미경유**, `tf.saved_model.load` 직접 호출. 전처리 = **서버와 동일한 프로즌 `inference/audio_decode.decode_pcm16`**. 424건 **2.2초**, `errors=0`.
- **재현 결과**: **overall accuracy = 0.8868**(376/424) — `eval_report.json`의 **0.8867924528301887**과 **일치**. recall **0.742 / 0.889 / 0.921** 일치. **`doorbell → fire_alarm` 오분류 10건**(33.2 「최다」) **재현**.
- ⇒ **전처리~추론 경로가 7월 학습 파이프라인과 동일함이 실증**됐다. ⇒ **(a)의 대조군 성립** — **"입력 무관 쏠림" 가설은 기각**이다. 모델은 **분포 안 입력을 정상 구분**한다.
- 🆕 **7월 평가에 없던 축 — 게이트 0.70 strict `<` 통과 후 실제 동작**:

  | true | pass_ok | pass_NG | blocked | pass% |
  |---|---|---|---|---|
  | doorbell | 44 | **9** | 9 | 85.5% |
  | knock | 92 | 5 | 11 | 89.8% |
  | fire_alarm | 231 | 13 | 10 | 96.1% |

- ⇒ **doorbell `pass_NG` 9건 = 게이트를 넘은 오알림**이다(62건 중). 게이트는 **틀린 예측을 걸러 주지 않는다** — 신뢰도가 높은 오분류는 그대로 통과한다.
- ~~⚠️ **미측정**: `pass_NG`의 **오분류 대상 클래스 내역**(`fire_alarm` 행인지 `doorbell ↔ knock` 혼동인지). 위 confusion 표와 **직접 대응시키지 말 것**.~~ → **✅ 해소 (2026-09-14 PoC-(47), 상세 = 아래 (d))**
- **대응 방향 = 사용자 판단 대기**((a)와 동일 건).

**(c) 🟢 실모델 기동 환경·스크립트 사실 (근거유형 = 실측)**

- **`server/venv_real` 필요**(py **3.11.15** / TF **2.16.2**). 기존 `server/venv`는 **py3.14라 TF wheel이 없다**. ⇒ 카테고리 9-1 계열의 **평소 기동 명령(`venv/bin/flask run`)으로는 real 모드가 불가**하다. **현재 서버 기본 기동은 mock ML**이며 본 세션이 그 전제를 처음 깼다.
- **`DDINGDONG_MODEL_PATH`는 셸 앞 변수로만 주입**했다 — **`.env` 무변경**(카테고리 21 `.env` 위생 · 키 중복 미결을 더 쌓지 않기 위한 선택).
- ⚠️ **스크립트 버그 실측 — 서버 경로는 정상이었다**: `decode_pcm16` 반환은 **(1, N) 2차원**으로 **배치 차원을 이미 포함**한다. 초기 평가 스크립트가 `[None, :]`로 배치를 **재추가**해 (1, 1, N)이 되었고 **yamnet Pad 에러로 424건 전건 실패**했다. 🔴 **`routes.py`는 반환값을 그대로 전달**하므로 **제품 서버 경로에는 영향이 없다** — **검증 스크립트만의 결함**이다. ★ 「도구가 낸 실패 ≠ 제품 결함」 — 6.3(o)·8.4(f) 계열의 **하네스 자기검증** 사례로 남긴다.

**(d) 🆕 게이트 축 전수 재현 + `pass_NG` 오분류 대상 내역 — (b)의 「미측정」 해소 (2026-09-14 PoC-(47) 신설, 근거유형 = 실측, n=424 전수)**

> 학교 밖·노트북 단독(**보드 미사용**) 세션. 로그 원본 = repo 밖 `~/ddingdong-측정결과/2026-09-14/realmodel_gate_axis_sweep.log`(`.gitignore` 차단분 — SSoT엔 요약만). 🆕 **[2026-09-15 PoC-(48)] 재현 수단 확보** = `server/tools/gate_axis_sweep.py`(PR #59, 상세 = 33.8) — 본 축은 이제 **repo 안 하네스로 재현 가능**하다.

- **측정 조건**: 경로 = **HTTP 미경유** `tf.saved_model.load` 직접 + **프로즌 `inference/audio_decode.decode_pcm16`**((b)와 동일 경로). **실모델 확증 3축** = 프로세스 **RSS 461,280KB** / TF 라이브러리 매핑 **54개** / 동일 입력 2회 `all_scores` **완전 일치**. **입력 위생** = `wave` 모듈로 **16kHz / mono / 16bit**를 파일마다 assert하고 `decoded shape (1, 48000)`을 확인했다((c)의 `[None, :]` 배치 재추가 함정 재발 방지).

- **대조군 재현 (3회차)** — (b) 표와 **전건 일치**. **값 갱신이 아니라 재현**이다(무변경 서술).

  | true | n | ok | NG | blocked | pass% |
  |---|---|---|---|---|---|
  | doorbell | 62 | 44 | 9 | 9 | 85.5% |
  | knock | 108 | 92 | 5 | 11 | 89.8% |
  | fire_alarm | 254 | 231 | 13 | 10 | 96.1% |

  합계 **n 424 / ok 367 / NG 27 / blocked 30**(367+27+30=424).

- 🆕 **4회차 재현 (2026-09-15 PoC-(48), 근거유형 = 실측, n=424 전수)**: PR #59 하네스로 **전건 일치** — **424 / 367 / 27 / 30**, accuracy **0.8867924528**. **값 갱신이 아니라 재현**이다(무변경 서술). **실모델 확증 3축** = 프로세스 **RSS 471,120KB** / TF 라이브러리 매핑 **54개** / 동일 입력 2회 **완전 일치**. ⚠️ RSS는 **세션별 실측치**다 — PoC-(46) **475,920KB** · PoC-(47) **461,280KB**와 **자릿수만 정합**하며 **덮어쓰지 않는다**.

- 🆕 **`pass_NG` 27건의 오분류 대상 내역** — (b)가 「미측정」으로 남긴 바로 그 축이다.

  | true | → doorbell | → knock | → fire_alarm | NG 중 `fire_alarm` 최대 신뢰도 |
  |---|---|---|---|---|
  | doorbell | — | 3 | **6** | **1.00** |
  | knock | 1 | — | **4** | **0.96** |
  | fire_alarm | 9 | 4 | — | — |

- 🔴 **위험 방향 10건**(타클래스 → `fire_alarm`): **G12로 ToF를 우회**하므로 presence와 **무관하게 발송**되고 **화재 대응 수칙이 렌더**된다. ★ **분포 「안」 입력에서 발생**했다 — (a)의 OOD 수렴과 달리 **held-out 실음원이 원인**이다. 두 경로를 섞어 읽지 말 것.
- 🟢 **안전 방향 13건**(`fire_alarm` → 타클래스): ToF 게이트를 **경유**한다. 33.2 「안전 방향 편향」이 **게이트 축에서도 유지**됨이 확인됐다.
- **`fire_alarm` 유출 0건**: `fire_alarm` true의 오분류는 전부 타클래스로 나갔다 — 위험 방향을 만드는 것은 **반대 방향(타클래스 → `fire_alarm`) 뿐**이다.
- ⚠️ **「`fire_alarm`이 흡인 클래스」는 논증이다** — (a)의 OOD 수렴과 본 내역을 합친 **해석**이며, support **254 최다**와의 **인과는 미실증**이다. **확정하지 말 것.**
- ⚠️ **계수 단위 = 클립 수(파일 수)**다. ~~**개별 파일명은 미기록**이라 특정 원본을 지목할 수 없다.~~ → **✅ 해소 (2026-09-15 PoC-(48))**: PR #59 하네스가 `stem` 열을 출력하므로 **개별 원본을 지목할 수 있다**. ★ 이 해소 **직후** 그 `stem` 열에서 **데이터셋 내용 중복 → train/test 누수**가 발견됐다 — 상세 = **33.7**.
- **대응 방향 = 사용자 판단 대기**((a)와 동일 건). **임계·정책을 확정하지 말 것.**

**(e) 🔴 [신규 미결] `confidence` 반올림이 게이트 앞에 있다 — 8.5(k) 「표시가 판정을 오염시키지 않는다」의 역방향 사례 (발견·문서 반영 2026-09-14 PoC-(47), 근거유형 = 실측 코드 대조 + 전수 스윕)**

- `server/app/model_serving.py`의 `confidence = round(float(row[idx]), 2)`가 `routes.py`의 `scores_to_prediction()` → `_apply_prediction_policy()` **호출 순서상 게이트 앞**에 있다. 실물 = `routes.py`가 `scores_to_prediction`의 반환 `confidence`를 **그대로** `_apply_prediction_policy`에 넘기고, strict `<` 비교는 `utils.py`의 후자 **안에서** 일어난다.
- ⇒ `CONFIDENCE_THRESHOLD=0.7` strict `<` 비교가 **원값이 아니라 2자리 반올림된 값**을 받는다. ~~원값 **0.695~0.69999** 구간이 **0.7로 올라가 게이트를 통과**한다.~~ → 🔴 **정정 (2026-09-15 PoC-(48), 근거유형 = 실측 f32 전수 스윕 503,317개 = 구간 [0.68, 0.71], 계수 단위 = f32 값 개수)**: 위 구간 서술은 **양끝 모두 부정확**했다.

  | 입력(f32) | raw(f64 정확값) | `round(·,2)` | raw 게이트 | rounded 게이트 |
  |---|---|---|---|---|
  | f32(0.695) | 0.6949999928474426 | 0.69 | 차단 | 차단 |
  | 한 ULP ↑ | 0.6950000524520874 | 0.7 | 차단 | **발송** ← 실측 **하한** |
  | f32(0.7) | 0.699999988079071 | 0.7 | 차단 | **발송** ← 실측 **상한** |
  | 한 ULP ↑ | 0.7000000476837158 | 0.7 | 발송 | 발송 |

  - **하한 정정**: f32 `0.695`는 실제 **0.6949999928…**이라 `round(·,2)`가 **0.69로 내려간다** ⇒ **갈리지 않는다**(f64에서도 `round(0.695, 2) == 0.69`). 실제 하한은 **한 ULP 위 0.6950000524520874**다.
  - **상한 정정**: `0.69999`가 아니라 **f32 `0.7` 자체**다. f32의 0.7은 f64로 **0.699999988…**이라 🔴 *"모델이 0.7을 뱉어도 원값 비교였다면 차단됐다"* — 본 (e)가 놓친 **가장 강한 사례**다.
  - **4조합 도달성**: (차단,차단) ✓ / (차단,발송) ✓ / (발송,발송) ✓ / **(발송,차단) = 도달 불가**(`round`의 단조성).
  - ⚠️ **입력 도메인이 f32**임을 함께 읽어야 한다 — 33.2 서빙 출력이 `(1, 3)` **f32**이고 `float()`로 f64 승격되므로, 갈림은 **f32로 표현 가능한 값에서만** 일어난다.
  - ✅ **「실사례 0건」은 유지된다** — 2026-09-15 전수 스윕에서 `[raw vs rounded]` 갈림 **0건** 재확인(계수 단위 = 클립 수, n=424).
- ★ **8.5(k)가 세운 원칙의 역방향 사례**다 — 8.5(k)는 *"판정 자체는 `status` 필드가 이미 `expired`로 확정하므로 **표시 해상도가 판정을 오염시키지 않는다**"*를 근거로 표시 손실을 감수했는데, 본 건은 **표시용 반올림이 판정 입력 자체를 덮어쓴다**. ⚠️ 8.5에 **「자료형 분리」라는 어휘는 없다** — 위 인용이 8.5(k)의 실물 문구다.
- ✅ **실사례 0건 — 심각도 낮음**: test **424건 전수**에서 raw confidence가 `[0.695, 0.70)`에 든 건 **0건**이다.
- 🆕 **[2026-09-15 PoC-(48) 추가] 파급 누락 — `all_scores`도 같은 자리에서 반올림된다 (근거유형 = 실측 코드 대조)**: `scores_to_prediction`은 `confidence`뿐 아니라 **전 클래스 `all_scores`를 2자리로 반올림**한다. 게이트는 top만 보므로 **판정 영향은 위 축에 갇히지만**, **대시보드 표시·집계는 `all_scores`를 쓴다** ⇒ **8.5(k) 축과 정면으로 맞닿는다**. ⚠️ 본 (e)에 `all_scores` 서술은 **0건**이었다(2026-09-15 실측, 대조군 = 같은 파일에서 `all_scores` **3건** 생존 — 전부 33.6(c)(d) 계열의 *"2회 완전 일치"* 확증 축) ⇒ **신규 서술**이다. ⚠️ **`model_serving.py`는 프로즌 파일** — **수정 여부·방식 = 사용자 판단 대기**.
- ⚠️ (a)·(d)에 기록된 소수 **둘째** 자리 값(0.62 · 0.61 · 0.65 · 0.87 · 0.99 · 0.96 · 1.00 등)은 **round 2자리를 거친 뒤의 값**이므로 **본 건의 영향을 받지 않는다**.
- ⚠️ **`model_serving.py`는 프로즌 파일**이다(코드 작성 원칙). **수정 여부 = 사용자 판단 대기** — 방식(round 제거 / 판정용 raw 별도 전달 / 현행 유지)도 수치도 **확정하지 말 것**.
- **판정 방법** = raw confidence가 `[0.695, 0.70)`에 드는 입력을 실제로 만들어 `primary_sent` 전이가 갈리는지 확인한다. 현재는 **전수 424건에 재현 입력이 없다**.

**(f) 🆕 OOD 스윕 확장 — 조건 축(문장 · 음성 · 음량 · 배경 · 비음성 소리)으로 (a)의 n=1을 넓혔다 (2026-09-15 PoC-(49) 신설, 발견일 = 반영일 = 2026-09-15, 근거유형 = 실측, 계수 단위 = 행 수)**

> 학교 밖·노트북 단독(**보드 미사용**) 세션. 로그 원본 = repo 밖 `~/ddingdong-측정결과/2026-09-15/ood_sweep_ext/`(`summary.md` · `results.csv` · `ood_sweep_ext_runtime.log`, `.gitignore` 차단분 — SSoT엔 요약만). **측정 전용**이며 임계·정책·대응 방향 신설 **0건**이다.

- **방법 (근거유형 = 실측)**: **HTTP 미경유 · 서버 미기동 · `/detect` 미호출 · 카카오 경로 없음 · repo 쓰기 0**. **경로 A**(`app.model_serving.predict` + `scores_to_prediction` = 서버와 동일, 2자리 반올림 포함) = **경로 B**(`tf.saved_model.load` `serving_default` 직접, raw)의 **동등성 확인**. 전처리는 양쪽 모두 프로즌 `inference.audio_decode.decode_pcm16`. 입력 = **PCM16 LE mono 16kHz 32,768샘플**. 총 **130행 / 유효 126행 / 제외 4행**(제외 사유 = **클리핑**, peak 32767 초과). **2회 실행 전 열 완전 일치** · 앵커 `doorbell` **1.00** · 라벨 순서 `PREDICTED_CLASSES == CLASSES` 단언 · **raw ↔ rounded 게이트 갈림 0행**(33.6(e) 축의 재확인).
- **발송 판정은 프로즌 `app.utils._apply_prediction_policy`를 실제로 호출**했다 — 임계·분기 **재구현 0줄**.

  | 축 | 실측 |
  |---|---|
  | 음성 **72행** | `fire_alarm` ≥0.70 **12행** — **전건 한 음성(Yuna)** |
  | 나머지 두 음성(Eddy · Grandma) **48행** | **전건 `knock`이고 ≥0.70 전건** |
  | 같은 음성 RMS 300의 `fire_alarm` 행 **5행** | 신뢰도 **0.46 ~ 0.59** — **전건 게이트 미달** |
  | 배경 바닥 **95 → 0**(동일 음성·문장·RMS1000 **8문장**) | ≥0.70 **4 / 8 → 8 / 8**(전건 `fire_alarm`) |
  | 시스템 알림음 **24행** + 합성 잡음 **11행** | `fire_alarm` ≥0.70 **0행** / `doorbell`·`knock` ≥0.70 **27 / 35** |
  | 박수형 버스트 | `knock` **1.00**(RMS1000 · RMS3000 **2행 모두**) |
  | 완전 무음 | `fire_alarm` **0.62** |
  | 배경 바닥(white RMS 95)만 | `knock` **0.78** |
  | **발송 판정 (n=126)** | `presence=true` **102 / 126** · `presence=false` **20 / 126**(= `fire_alarm` ≥0.70 **20행**이 G12로 ToF를 우회) |

- ⚠️ **[실측 — 런타임 주입 NC] 가정 임계 0.99에서의 값**: `app.utils`의 임계를 **0.99로 주입**해도 발송이 **(14, 5)** 남는다(`presence=true` 14 / `presence=false` 5). 🔴 **이는 「가정 임계 0.99에서의 값」이며 정책 시사로 쓰지 말 것** — 본 주입의 목적은 **임계 변경이 검출되는가**(NC)이지 임계 후보 평가가 아니다. **함정 대조군** = `app.constants`만 0.99로 패치하면 **(102, 20) 무변화**(`utils`가 from-import 바인딩이라 기대대로 미검출), **복원 후 재실행 (102, 20)** 으로 기준 복귀.
- **9/12 재현 시도 (원 스크립트 부재 — 진폭 · RNG 가정 포함)**: `silence`(`fire_alarm` **0.62**) · `sine1k`(`doorbell` **1.00**)는 **(a)와 일치**. `whitequiet`는 **(a) 0.80 vs 본 재현 0.74**로 어긋나며 원인은 **진폭 · RNG 가정 차이**로 **추정**된다(**미확정**). `voiceshort` · `voicelong` · `knocklike`는 **원 스크립트 부재로 재현 불가**다.
- **한계 (전건 명기)**: **TTS ≠ 실제 사람 목소리** / **보드 미경유**라 마이크·실내 음향 전달 **미반영** / 보드 레벨과 서버 정규화 **정합 미검증**(6.3 G28) / **부스 실소음 미재현** / **배경 바닥 파형 n=1**(white RMS 95 — 근거 = 같은 날 6.3(p)의 m0 `rms` 91~99 · m6 88~97 실측).
- **[논증] 현재 트리거는 수동 `s` 키**라 판정 기회가 **사람 입력에 한정**된다 — **자동 트리거(M5-c) 도입 시 노출이 늘어날 가능성**이 있다. **입력 실측 = 위 표.** **미실증이며 확정하지 말 것.**
- 🔴 **대응 방향 = (a)의 사용자 판단 대기 그대로**다. **n을 늘렸을 뿐 임계 · 정책 · 시연 각본을 확정하지 않는다.**


**(g) 🆕 웹 음원 파일럿 — 실제 한국 초인종·인터폰 음원에서도 `presence` 무관 발송이 난다 (2026-09-17 PoC-(51) 신설, 발견일 = 반영일 = 2026-09-17, 근거유형 = 실측, 계수 단위 = 행 수 / 음원 수)**

> 노트북 단독 · 보드 미사용 · **repo 쓰기 0**. 로그 원본 = repo 밖 `~/ddingdong-측정결과/2026-09-17/web_audio_pilot/`(`REPORT.md` · `listening_qa.log` · `results.csv` · `metadata.csv` · `dup_check.csv`, `.gitignore` 차단분 — SSoT엔 요약만). 조사 계열 절 = **5.2**. **임계 · 정책 · 대응 방향 신설 0건.**

- **입력** = 공유마당 **CC BY 음원 5개**(16kHz mono 변환). 조건 = 창 위치 3 × 음량 4 = **2초 창 12개** + **전체 길이 1개** ⇒ 음원당 13행, 총 **65행**. 2초 창 길이는 서빙 경로(`/detect` 2초 스냅샷)와 같다.
- **청취 검수 (실측, 학부생 1인)**: 딩동 **3** / 인터폰 전자음 **1** / 새소리 **1**. 🔴 **제목 ≠ 실제 소리** — 「인터폰벨19」로 이름 붙은 파일이 실제로는 **딩동**이었다 ⇒ **웹 수집 확대 시 청취 검수는 필수**다.
- 🔴 **`fire_alarm` ≥0.70 → `presence` 무관 발송 = 23행 / 65행**(프로즌 `app.utils._apply_prediction_policy` **실호출**, 임계·분기 재구현 0줄). 23행 전건이 `presence=false`에서도 `primary_sent=True` · `skip_reason=None`이고 `fire_alarm_bypass`로 ToF를 우회한다(카테고리 3 G12대로 신뢰도 게이트는 **먼저** 받았다).
- **유형별 재집계 (계수 단위 = 2초 창 수)**:

  | 유형 | 음원 수 | 2초 창 | `fire_alarm` 발송 | 전체 길이 조건 |
  |---|---|---|---|---|
  | 딩동 | 3 | 36 | **0** | 2건 `doorbell` 1.000 / 1건 `fire_alarm` **0.765 발송** |
  | 인터폰 전자음 | 1 | 12 | **9** | `doorbell` 0.504 미달 |
  | 새소리 | 1 | 12 | **12(전건)** | 발송 |

  - 검산 = 2초 창 21 + 전체 길이 2 = **23** = 위 23행.
  - 🔴 **「5개 중 3개에서 `presence=false` 발송」은 전체 길이 조건을 포함한 수치**다 — **2초 창만 보면 2개**(인터폰 전자음 · 새소리)다. ⚠️ 서빙 경로는 2초 창이므로 **두 수를 섞어 읽지 말 것.**
  - 🟢 **딩동 계열에서 2초 창 오발송 0건**은 5.1 부스 소품 요건(「딩동」 계열)과 **방향이 일치**한다. ⚠️ **실물 차임 확인은 별도**이며 n=3이다.
- ⚠️ **창 위치 하나가 클래스를 뒤집는다 (실측)**: 인터폰 전자음 음원은 `onset−0.512` 위치에서 (최대 음량을 뺀) 3개 음량이 **전부 `doorbell`**인데, `onset−0.000` · `onset−1.000`에서는 4개 음량이 **전부 `fire_alarm`**이다. ⇒ **0.512초 이동이 「초인종 알림」과 「화재 대피 알림」을 가른다.** 이 값은 6.2 G29의 「32슬롯 = 8(0.512s) + 24(1.536s)」 pre-roll과 같은 값이다(근거유형 = 문서 인용) — 🔴 **pre:post 비율은 여전히 미확정이며 본 관측이 확정하지 않는다.**
- ⚠️ **2초 창 vs 전체 길이 (실측 + 경계 표기)**: 리포트는 「5개 중 3개가 갈렸다」로 적었으나, **클래스가 실제로 갈린 것으로 확인된 음원은 2개**(인터폰 전자음 · 딩동 1건)다. **3번째의 근거는 미확인**이다 — **확정하지 말 것.**
- ⚠️ **음량 축의 한계 (반드시 병기)**: 음량 4단계는 **깨끗한 음원의 디지털 스케일링**이며 **보드 잡음 바닥이 미반영**이다. 🔴 **「음량이 작을수록 낫다」를 보드에 옮기지 말 것** — 6.3의 헤드룸 · 클립 축과 **다른 축**이다. 관련 = **5.2(d)** 학습 ↔ 서빙 음량 처리 비대칭.
- **근접 중복 검사 (실측)**: 임계 **0.706**(양성 대조 최소 0.9694 · 음성 대조 최대 0.4427의 중점, 분포 겹침 없음). 파일럿 5 × `01_clips/doorbell` 전수 436 대조에서 **1개가 임계를 넘었다(0.7251)**. ⚠️ 그 값은 **양성 대조 대역 0.9694~0.9872와 0.24 이상 벌어져** 있어 **재인코딩본이라기보다 음색이 닮은 별개 음원**으로 읽는 편이 실측에 부합한다(논증). ⇒ **학습 투입 시 우선 배제 후보**로만 남긴다 — **확정은 사용자 판단.**
- 🟢 **대조 확인**: `knock` 오분류 **0행 / 65행** / raw ↔ rounded 게이트 갈림 **0행 / 65행**(33.6(e) 축의 재확인 — 위험 자체는 유효하나 **본 입력 집합에서 발현하지 않았다**) / 앵커 양성 대조 `doorbell` **1.00**.
- **한계 (전건 명기)**: 음원 **5개 · 1인 청취**라 **비율로 일반화 금지** / 전부 **스튜디오 효과음**이며 실제 월패드 원음 · 실 현관 녹음이 아니다 / **보드 미경유**(마이크 · 실내 음향 전달 미반영) / 부스 실소음 미재현.
- 🔴 **대응 방향 = (a)의 사용자 판단 대기 그대로**다. 본 항이 더한 것은 **「합성 OOD가 아니라 실제 한국 초인종 음원에서도 난다」는 입력**뿐이며 **임계 · 정책 · 시연 각본을 확정하지 않는다.**

**관련**: 33.2(예비 학습 성적 · confusion `doorbell → fire_alarm` 10건 · SavedModel export) / 33.3(미결 항목) / 33.5(USP 2층 · 개체 구분 미검증) / 카테고리 3(신뢰도 임계값 · G12 · 클래스별 ToF 정책) / 6.2(ML 추론 서빙) / 6.4(g)(mock ML ④런타임 — 본 절이 깬 전제) / 8.6(`is_real_mode()` 파생 · mock 가시화) / 26.10(d)(시연 선행 조건) / 카테고리 21(`.env` 위생 — 셸 앞 변수 선택 근거) / 카테고리 5(직접녹음 보강 — doorbell 최소 클래스) / **33.7(본 (b)(d)의 424건에 섞인 train/test 누수)** / **33.8(본 절 재현 수단 = PR #59 하네스 · 외부 세트 사용 주의)** / **5.2(웹 음원 조사 — (g)의 상위 조사)**

---

### 33.7 🔴 [신규 미결] 데이터셋 내용 중복 → train/test 누수 (2026-09-15 PoC-(48) 신설, 발견일 = 반영일 = 2026-09-15, 근거유형 = 실측 md5 전수 + 매니페스트 대조, 계수 단위 = 클립 수(파일 수))

> 학교 밖·노트북 단독(**보드 미사용**) 세션. 로그 원본 = repo 밖 `~/ddingdong-측정결과/2026-09-15/leak_audit_2026-09-15.md`(`.gitignore` 차단분 — SSoT엔 요약만). **데이터셋은 읽기만 했다** — 이동·삭제·수정 **0건**.

- **발견 경로**: `server/tools/gate_axis_sweep.py`(PR #59, 상세 = 33.8) 출력의 `conf_raw` 열에서 **서로 다른 `stem`이 소수 16자리까지 동일한 값**을 내는 것을 관찰 → md5 대조로 확인했다. ★ **33.6(d)의 「개별 파일명은 미기록이라 특정 원본을 지목할 수 없다」 한계가 하네스의 `stem` 열로 풀리자마자 나온 첫 산출**이다 — 계측 자산이 먼저 있었기에 관측이 가능했다(카테고리 20 「계측/판정 계층 분리」 계열).

**(a) 실측 1 — `02_preprocessed` 내용 중복 (md5 전수, 계수 단위 = 클립 수)**

- 전체 **2792** / 고유 내용 **2305** / 중복 그룹 **15** / 중복에 속한 파일 **502** / **순수 잉여 487(전체의 17.4%)**.
- 상위 그룹 = **108×3 · 56×2 · 30** ⇒ ~~**454파일이 단 6개 내용**이다.~~ → **466파일이 단 6개 내용**이다 — **[산술 오기 정정 2026-09-15 PoC-(49), 근거유형 = 실측 재계산]** 108 + 108 + 108 + 56 + 56 + 30 = **466**이다. 그룹 크기 목록을 포함한 (a)의 **다른 수치는 전건 재현**됐으므로 **계측값이 틀린 것이 아니라 합산 표기가 틀렸다**(상세 = **(g)**).

**(b) 실측 2 — split 교차 (매니페스트 × md5, 계수 단위 = 행 수 / 클립 수)**

- `split_manifest.csv` **2792행**, **경로 미존재 0**(전수 확인).
- 중복 **15그룹 = split 교차 10 + split 내부 갇힘 5**.
- 교차 상위: n=108 `{train 71, val 20, test 17}` **3그룹** / n=56 `{train 38, val 9, test 9}` **2그룹** / n=30 `{train 19, val 4, test 7}`.
- **갇힘 5그룹은 전부 n=2, 전부 `train` 내부, 잉여 5파일**이다 ⇒ 「유효 데이터량 축소」 축은 **실질 무의미**하며, 문제는 **전적으로 교차분**이다.
- 🔴 **train/val과 내용이 겹치는 test 행 = 79 / 424**.
- **79건 전부 `fire_alarm`**이다. `doorbell` · `knock`은 **0건**(대조군 = 같은 대조에서 `fire_alarm` 79건 검출).

**(c) 실측 3 — 성적 영향 분해 (재추론 0회 — 기존 스윕 로그 + 매니페스트만 사용)**

  | 지표 | 전체 424 | 청정 345 | 차이 |
  |---|---|---|---|
  | doorbell f1 | 0.736 | 0.736 | 0 |
  | knock f1 | 0.881 | 0.881 | 0 |
  | fire_alarm f1 | 0.927 | 0.893 | **−0.034** |
  | accuracy | 0.8868 | **0.8609** | **−0.026** |
  | macro_f1 | 0.8478 | **0.8367** | **−0.011** |

- 누수 **79건** = correct **79**, **accuracy 1.0000**(전건 정답). 청정 **345건** = correct **297**, accuracy **0.8609**.
- `fire_alarm` support **254 → 175**(누수 79 제외).
- `doorbell` · `knock`의 f1이 **소수점까지 완전 동일**한 것은 두 클래스의 누수가 **0건**이므로 **정합**이며, **계산 자체의 검산**도 된다.

**(d) 판정 — 경계를 정확히 적는다**

- [실측] **바이트 동일 파일이 train/test에 걸쳐 존재한다.**
- [실측] 누수분 accuracy **1.0000**과 청정분 **0.8609**가 확연히 갈린다.
- [실측] **성적 영향은 `fire_alarm` 한 클래스에 국한**되며 **macro_f1 기준 0.011**이다. ⇒ **33.2가 등재한 macro_f1 0.848은 실질적으로 방어된다**(청정값 **0.8367** 병기, 기존 수치 **무변경**).
- 🔴 **[경계] `source_key` 기반 원본그룹 분리는 고장난 것이 아니다.** **파일명 기준 그룹화**라 **내용이 동일한 파일은 애초에 방어 범위 밖**이었다. ⇒ **「설계 결함」이 아니라 「범위 밖」**으로 기록한다. 33.6(b)의 「`source_key` 기반 원본그룹 분리 = 누수 방지 기존 설계」 서술은 **틀린 것이 아니라 범위가 좁았다** — **취소선 대상이 아니다.**
- [논증] 누수 79건이 **전건 정답**인 기전은 **암기 추정**이다. **입력 실측 = correct 79 / 79, accuracy 1.0000**이며, *"왜 전건 정답인가"*는 **미실증**이다 — **확정하지 말 것.**

**(e) 🔴 대응 방향 = 사용자 판단 대기**

- **선택지 열거까지만**: ① 중복 제거 후 재split·재학습 / ② 현 성적 유지 + 누수 고지 병기 / ③ 청정값을 정본으로 교체.
- **어느 것도 확정하지 않는다.** 본 절은 **임계·정책·수치·재학습 방향 신설 0건**이다.
- ~~⚠️ 그럼에도 **train/test 누수의 존재 자체가 재학습 전 해소 대상**이라는 점은 유지된다(방향은 위 ①②③ 미확정).~~ → ✅ **대응 방향 확정 = ① (사용자 결정 2026-09-21 PoC-(55), 근거유형 = 사용자 결정, 상세 = 33.12)**
- 🆕 **위 선택지 ①(중복 제거 후 재split · 재학습)이 채택**됐다. **②**(현 성적 유지 + 누수 고지 병기) · **③**(청정값 정본 교체)는 **채택되지 않았다**. 🔴 **확정된 것은 방향이고 실행은 재학습 소관**이다 — 33.2 · 33.6 · 33.7의 등재 수치와 (c)의 청정값은 **재학습 전까지 전건 무변경**이다. ⚠️ **본 회차에 머지된 것은 split 단계 구현분뿐**이며(PR #69 `0461a94`) **파이프라인 실데이터 재실행 0회 · 데이터셋 무변경**이다. 🔴 **「누수의 존재 자체가 재학습 전 해소 대상」이라는 위 문장은 지금도 참**이며, 취소선은 **「방향 미확정」이라는 클로즈에만** 걸었다.

**(f) 한계 (전건 명기)**

- ~~`01_clips` / `03_augmented` / `05_final_dataset`의 중복 여부 **미확인**이다 — 본 감사는 **`02_preprocessed`만** 봤다.~~ → 🆕 **부분 해소 (2026-09-15 PoC-(49), 상세 = (g))**: `01_clips` · `03_augmented` · `05_final_dataset` · `01_extracted` **전부 실측**됐다. 🔴 **잔존** = `00_source_raw` **미감사**(41,450파일) / **파형은 같고 바이트가 다른** 쌍 **미검출**(본 감사는 전건 **md5 바이트 기준**) / **부분 중복(구간 겹침) 미감사** / **두 클래스 동시 배치 경위 미실증**. → 🆕 **부분 해소 2 (발견 2026-09-18 / 문서 반영 2026-09-19 PoC-(53), 상세 = (h))**: `00_source_raw`는 **15그룹의 원천 178키 = 180파일만 골라** 감사했다(**전수 md5 미수행** — 41,450파일 중 180, 계수 단위 = 파일 수). 「두 클래스 동시 배치 경위」는 **dump 내 경위가 실측**됐다(양쪽 폴더 실존 + csv 교집합 = 정확히 그 2세그먼트) — 단 **AudioSet 원본 다중 라벨인지 우리 필터링인지는 미확정**. 「파형 동일·바이트 상이」 · 「부분 중복」은 **그대로 잔존**.
- ~~중복 발생 **원인 미규명** — 수집 단계인지 전처리 단계인지 **미확정**.~~ → 🆕 **부분 해소 (2026-09-15 PoC-(49), 상세 = (g))**: **전처리 단계에서 새로 같아진 그룹 = 0 / 15**이고 **15 / 15가 `01_clips` 단계에서 이미 바이트 동일**했다 ⇒ **전처리 쪽은 닫혔다.** ~~🔴 **`01_clips` 이전(수집·원천) 어디에서 발생했는지는 여전히 미규명**이다 — `00_source_raw` 미감사.~~ → ✅ **해소 (발견 2026-09-18 / 문서 반영 2026-09-19 PoC-(53), 근거유형 = 실측 + 논증, 상세 = (h))**: **15 / 15 그룹의 동일성이 `00_source_raw` 바이트에 이미 존재**한다 — 우리 수집·조각내기 단계가 **새로 만든 동일성 = 0 / 15**(계수 단위 = 그룹 수). ⚠️ **원천이 왜 그런지(AI Hub 측 경위)는 미확정**이며, 닫힌 것은 「발생 지점 = 원천」까지다.
- 직접 녹음분(카테고리 5, 8주차 4유닛 프로토콜)이 합류하면 **영향 방향을 예측할 수 없다**.
- 계수 단위 혼동 금지 — **(a)(b)는 클립 수 / 행 수**, **(c)는 지표값**이다.

**(g) 🆕 감사 확장 — `02` 밖 폴더 전수 + 중복 그룹의 성격 (2026-09-15 PoC-(49) 신설, 발견일 = 반영일 = 2026-09-15, 근거유형 = 실측 md5 전수, 계수 단위 = 파일 수 / 그룹 수 / 키 수 — 항목별 병기)**

> 로그 원본 = repo 밖 `~/ddingdong-측정결과/2026-09-15/leak_audit_ext_2026-09-15.md`(`.gitignore` 차단분 — SSoT엔 요약만). **데이터셋은 읽기만 했다** — 이동·삭제·수정 **0건**이고 열기는 전부 `'rb'`다. 인덱싱 총계 **28,240 파일**. 표준 라이브러리만 사용.

- **재현 — 계측 도구 검증 (근거유형 = 실측)**: (a)(b)의 **12항목이 재측정과 일치**했다 — 2792 / 2305 / 15 / 502 / 487(17.4%) / 그룹 크기 목록 / 매니페스트 2792행 · 경로 미존재 0 / 교차 10 · 갇힘 5 / 교차 상위 배분 / 갇힘 5그룹 성질 / test 누수 79 · 424 / 누수 전건 `fire_alarm`. ⇒ **도구 신뢰를 먼저 확인한 뒤** 아래를 진행했다. 유일한 불일치는 **(a)의 합산 표기 454**였고 **위에서 466으로 정정**했다.
- **`01_clips` (계수 단위 = 파일 수 / 그룹 수)**: 전체 **2798** / 고유 **2306** / 중복 그룹 **16** / 중복 소속 **508** / 순수 잉여 **492**.
  - **`01` 전용 중복 그룹 n=6** = **카테고리 5.1의 AI Hub `S_103` length-0 wav 6개 preprocess skip** 대상과 **동일**하다(6건이 서로 **바이트 동일**, 각 **78 B**). 이것이 **01 그룹 16 − 02 그룹 15 = 1**의 전부다.
  - **`01` ↔ `02` 동일 relpath md5 일치 = 0 / 2792** ⇒ **전처리가 전 파일의 바이트를 바꾼다**(피크 정규화). ∴ 「01에서 이미 같았다」는 **단순 복사 때문이 아니라** 전처리가 결정적이라 **같은 입력이 같은 출력을 낸** 결과다.
- 🔴 **발생 단계 (계수 단위 = 그룹 수)**: 02의 중복 **15그룹 전부**가 **`01_clips` 단계에서 이미 바이트 동일**했다(**15 / 15**). **전처리 단계 발생 = 0 / 15.** ⇒ (f)의 「수집 단계인지 전처리 단계인지 미확정」 중 **전처리 쪽이 닫혔다.**
- **`03_augmented` (계수 단위 = 파일 수 / 그룹 수)**: 9655 / 고유 **8678** / 그룹 **45** / 소속 **1022** / 잉여 **977**. **`03` ∩ `02` = 6**이며 **전건 디지털 무음**이다(무음에 게인·SNR 믹싱을 해도 무음이 유지된 결과).
- **`05_final_dataset` (계수 단위 = 파일 수 / 그룹 수)**: 12447 / 고유 **10982** / 그룹 **59** / 소속 **1524** / 잉여 **1465**. **split 교차 10그룹** / **클래스 교차 23그룹**. split별 = train **11586**(doorbell 1842 / knock 2940 / fire_alarm 6804) · val **437**(67 / 116 / 254) · test **424**(62 / 108 / **254**).
  - 🔴 **`05`의 test 424 중 train ∪ val(증강 포함 전량)과 바이트 동일 = 79** — **(b)의 `02` 기준 79와 동일**하다. ⇒ **증강 단계가 test 누수를 늘리지 않았다**(증가 **0**). 내역 = test ∩ train **79** / test ∩ val **76**(val 쪽이 train 쪽의 **부분집합**).
- **`01_extracted` (계수 단위 = 파일 수 / 그룹 수)**: 548 = **wav 377** + **mp3 171**. `01_clips`와 바이트 동일 **0** · `02_preprocessed`와 바이트 동일 **0**. ⚠️ **이 「0건」은 wav 377건에 한해 유효**하다 — **mp3 171건은 wav와 바이트 비교가 원리상 불가능**하고, **디코딩 파형 수준의 동일성은 본 감사 범위 밖**이다. 내부 중복 **1그룹 n=30**은 **전부 0바이트 빈 파일**(doorbell 10 / knock 20)이다. 🆕 **[원인 — 발견일 = 반영일 = 2026-09-21 PoC-(55), 근거유형 = 실측 이름 대조, 계수 단위 = 파일 수, 상세 = 33.14(c)]** 이 **30개**는 FSD50K 로컬 덤프의 **0바이트 wav 2,414개 집합에 30 / 30 전건 포함**되며 `00_source_raw`에서 **이미 0바이트**였다 ⇒ **조각내기 단계의 결함이 아니다**(5.2(f) 정합).
- **중복 그룹의 성격 — `02`의 15그룹**

  | 성격 | 그룹 수 | 파일 수 |
  |---|---|---|
  | **서로 다른 원본이 같은 내용**(`source_key` 수 = n) | **10** | **491** |
  | **같은 원본에서 나온 조각이 같음**(`source_key` 수 = 1) | **5** | **10** |

  - 대형 그룹은 **같은 키 집합 × 오프셋 `0000000` / `0003000` / `0006000`** 구조다 — 108키 × 3종 / 56키 × 2종 / 30키는 **56키의 부분집합**(오프셋 `0006000`) / 7키 × 3종.
  - **전량이 중복인 원본 = 0 / 108**(계수 단위 = 키 수) — 108개 원본 **모두 일부 조각만** 중복이다. 원본당 클립 수 = **4 ~ 8**.
  - 전건 **3.00초 / 16kHz / mono / 16bit**. 비무음 그룹 peak **31129 ~ 31130**(피크 정규화 흔적). 정규화 자기상관 최대 피크 **0.109 ~ 0.249**.
- 🔴 **클래스 교차 — (a)(b)에 없던 신규 사실 (계수 단위 = 그룹 수)**: `02`의 중복 그룹 중 **클래스가 2개 이상 섞인 그룹 = 6**이다.
  - **디지털 무음 3.00초 클립 5파일**이 `doorbell` **2** / `fire_alarm` **2** / `knock` **1**로 **3클래스에 걸쳐** 동일하다.
  - 나머지 **5그룹** = **두 `source_key`**(`9OqtuFGCCR8_30.0_40.0` · `uA3bpAQV_hE_0.0_8.0`)가 **`doorbell/`과 `fire_alarm/` 두 클래스 폴더에 같은 파일명으로 동시에 존재**한다. **전부 `train` 내부**라 **split 교차는 아니다.**
- **[논증·가능성 — 전건 미실증]**
  - `S_103` 계열에서 **서로 다른 녹음의 선두 약 9초 구간만 공통**일 가능성이 있다 — **앞 3조각만 동일하고 뒤 조각은 각기 다르다**는 실측과 부합한다. ⇒ **발생 지점이 `00_source_raw` 원천 데이터셋일 가능성**이 있으나 ~~**`00_source_raw` 미감사**라 **미확정**이다. **확정하지 말 것.**~~ → 🆕 **[입력 실측 확인 — 발견 2026-09-18 / 문서 반영 2026-09-19 PoC-(53), 상세 = (h)]** 원천 mp3 171파일의 **최장 공통 접두 바이트가 실측**됐다(G01 108파일 ≈10.0초 · G04 56파일 ≈8.95초 — 초 환산은 **헤더 산술**). 🔴 **이 [논증]이 실측으로 승격된 것이 아니라, 그 논증의 입력(선두 구간 공통)이 원천 바이트에서 확인된 것**이다 — 「왜 그렇게 만들어졌는가」(공통 안내음 등)는 **여전히 미확정**.
  - 위 **클래스 교차 파일**과 **33.2의 `doorbell → fire_alarm` 오분류**의 관련은 **미검증 가능성**으로만 적는다 — **인과를 확정하지 말 것.**
  - 자기상관이 낮은 점은 「경보음의 단순 반복 때문에 우연히 같아졌다」는 설명과 **잘 맞지 않는다** — 다만 **반증 한 조각일 뿐 확정 근거가 아니다.**
- 🔴 **대응 방향 = (e) 그대로 사용자 판단 대기.** 본 항은 **감사 범위를 넓혔을 뿐** 방향·수치·정책 신설 **0건**이다. **성적 영향 재계산도 0회**이며 (c)의 청정값은 **무변경**이다.

**(h) 🆕 원천 귀속 감사 — `02` 중복 15그룹의 동일성은 `00_source_raw`에 이미 있었다 (발견 2026-09-18 / 문서 반영 2026-09-19 PoC-(53), 근거유형 = 항목별 병기 — 실측 / 논증 / 미확정, 계수 단위 = 그룹 수 / 원천 파일 수 / 키 수 — 항목별 병기)**

> 노트북 단독 · 보드 미사용. 로그 원본 = repo 밖 `~/ddingdong-측정결과/2026-09-18/source_raw_provenance_audit.log`(`.gitignore` 차단분 — SSoT엔 요약만, 본 등재 시 **전문 대조**). **repo 쓰기 0 / 데이터셋 쓰기 0 / zip 미해제.** 🔴 **`00_source_raw` 전수 md5는 하지 않았다** — 대상만 골랐다(아래).

- **대상 특정 방법**: `02`의 중복 15그룹 → `split_manifest.csv`의 `source_key` **역추적** → 원천 **178키**. 실제 md5 = `02` 2792파일(재현용) + `00_source_raw` **180파일 / 71,417,755 B**. `fsd50k` 40,966 wav는 **미접촉**(15그룹과 무관 — 「중복 없음」을 뜻하지 않는다).
- **재현 (계측 도구 검증, 근거유형 = 실측)**: (a)의 2792 / 2305 / 15 / 502 / 487 **전건 재현** + (g) 구조(108×3 · 56×2 · 30⊂56 · 7×3 · 무음 5 · 2키 클래스 교차 5그룹) **전건 재현**. **도구 신뢰를 먼저 확인한 뒤** 아래를 진행했다.
- **원천 귀속 (근거유형 = 실측, 계수 단위 = 키 수)**: G01~G09 **171키** = `aihub_alarm` mp3 **171 / 171 파일명 완전 일치** / G10 **5키** = `audioset` wav **5 / 5 실존 + csv 등재 확인** / G11~G15 **2키** = `audioset`의 `doorbell/` · `fire_alarm/` **양쪽 폴더에 실존** / `fsd50k` = 15그룹과 무관 / **귀속 불가 0**. ⚠️ **`00` ↔ `01_clips` 키 매핑 테이블은 없다**(csv 9개 전부 열어 확인) — 귀속은 **파일명 완전 일치** 기준이다.
- 🔴 **핵심 판정 (근거유형 = 실측 + 논증, 계수 단위 = 그룹 수 / 원천 파일 수)**: **15 / 15 그룹의 동일성이 `00_source_raw` 바이트에 이미 존재한다. 우리 수집·조각내기 단계가 새로 만든 동일성 = 0 / 15.**

  | 성격 | 그룹 수 | 원천 파일 수 |
  |---|---|---|
  | 원천 **전체 바이트** 동일 | **5** (G11~G15) | **4** |
  | 원천 **선두 구간 바이트** 동일 | **9** (G01~G09) | **171** |
  | 원천 **창(window) 무음** | **1** (G10) | **5** |

  - ⚠️ *"조각내기가 새로 같게 만든 것이 아니라 동일 입력이 동일 출력을 낸 것"*은 **디코딩 결정성에 기댄 논증**이다 — **입력 실측 = 위 표**. 🆕 **[도구 특정 — 발견일 = 반영일 = 2026-09-20 PoC-(54), 근거유형 = 논증, 상세 = 33.10(c)]** 그 결정성의 **주체가 특정**됐다 = **ffmpeg**(`-ss {start} -t 3.0 -ar 16000 -ac 1 -sample_fmt s16`, 조각 경계 `start = i * 3.0`). 선두 ≈10.0초 → **3조각 동일**(G01~G03) · ≈8.95초 → **2조각 동일**(G04~G05)이라는 **산술이 코드와 맞는다**. 🔴 **ffmpeg 버전이 코드에 박혀 있지 않아 재실행 결정성은 여전히 논증**이다 — **논증 등급은 무변경**이며 실측으로 승격되지 않는다.
  - ★ **위임의 3분법(원천 동일 / 조각 후 동일 / 귀속 불가)이 실물과 맞지 않았다** — G01~G10이 어디에도 들어가지 않아 MCP가 **제4범주(선두 구간 동일)를 만들어** 보고했다. 학습 16 「불변식 유지 + 메커니즘 등가 치환」 사례이며 **27.8(o)②**에 기록.
- **선두 구간 공통 실측 (바이트 = 실측 / 초 = 산술)**: ID3v2 태그 제거(171파일 **전부 태그 0바이트**, 첫 프레임 헤더 `ff fb 90 c4` 공통) 후 첫 파일 대비 **최장 공통 접두 바이트**를 쟀다 — G01 108파일 = **160,083 ~ 160,085 B**(≈10.0초) / G04 56파일 = **142,944 ~ 142,948 B**(≈8.95초) / G07 7파일 = **154,646 ~ 155,386 B**(≈9.7초) / G01↔G04↔G07 교차 3대표 = **21,201 B**(≈1.3초). 🔴 **초 환산은 MPEG-1 Layer III · 128 kbps · 44.1 kHz · 417 B/프레임 헤더 산술이며 파형 실측이 아니다.**
  - **`02` 구조와 정합**: 접두 ≈10.0초 → 3조각 동일(G01~G03) / ≈8.95초 → 2조각 동일(G04~G05) + 그중 30키만 3조각째까지(G06). ⚠️ **G06 30키 부분집합 내부의 접두 길이는 미계측.**
  - ⇒ (g)의 [논증] 「선두 약 9초 구간만 공통」의 **입력이 원천 mp3 바이트 수준에서 확인됐다**. 🔴 **논증이 실측으로 승격된 것이 아니라 그 논증의 입력이 원천에서 확인된 것**이다. ⚠️ **AI Hub 측이 왜 그렇게 만들었는지(공통 안내음 등)는 미확정.**
- **G10 무음 (근거유형 = 실측)**: 원천 wav 5개는 **파일 단위로는 상이**하나, 각 조각의 해당 3초 창(오프셋 6000ms ×4 / 0ms ×1)이 원천에서 **이미 전 바이트 0**(5 / 5). **파일 전체는 무음이 아니다** ⇒ 무음은 원천에 있었고 조각내기가 그 창을 잘라냈다.
- **G11~G15 클래스 교차 — dump 내 경위 (근거유형 = 실측 + 미확정)**: 같은 세그먼트 wav가 `audioset/doorbell/`과 `audioset/fire_alarm/` **양쪽에 저장**돼 있고(md5 동일) `eval_doorbell.csv` ∩ `eval_fire_alarm.csv` = **정확히 이 2세그먼트**(대조군 = 나머지 csv 쌍 교집합 **전부 0**). ⇒ (f)의 「두 클래스 동시 배치 경위 미실증」 중 **dump 내 경위가 실측됐다**. 🔴 **csv 8개는 3열(`ytid,start,end`) 가공본이고** ~~**생성 코드가 repo에 없어**~~, 이중 등재가 **AudioSet 원본 다중 라벨에서 온 것인지 우리 필터링에서 온 것인지 미확정**이다 — 추측을 적지 않는다. → 🆕 **부분 해소 (발견일 = 반영일 = 2026-09-20 PoC-(54), 근거유형 = 항목별 병기 — 실측 / 논증, 상세 = 33.10(e)(f))**: [실측] **생성 코드 = 별개 pretest repo의 `audioset_filter.py`**이며, `00_source_raw/audioset/`의 csv 8개는 그 산출물 `data/filtered/{split}_{name}.csv`의 **복사본**이다(**8쌍 전건 행 수 동일**, 계수 단위 = 행 수). [논증] 그 `TARGET` 순회에 **`break`가 없어** 한 세그먼트가 두 클래스 리스트에 **동시에 들어갈 수 있다** ⇒ 이중 등재는 **원본 다중 라벨 쪽으로 기운다**. 🔴 **그러나 해당 2세그먼트의 실제 `label_list`는 미확인**(`balanced_train_segments.csv` 원본 미열람)이라 **위 미확정은 그대로다 — 확정하지 말 것.** ⚠️ 닫힌 것은 **「생성 코드 부재」 한 축뿐**이며, 「3열 가공본」은 **지금도 사실**이라 취소선 대상이 아니다.
- **산술 정합 (근거유형 = 논증)**: aihub mp3 171 → `fire_alarm` 1648클립 = 171 × 약 9.6조각 ≈ 1642 = 5.1의 「빈 클립 6개 skip 후 1642」와 정합. 모순 없음.
- **한계 (전건)**: ① 바이트 기준 — 파형 동일·바이트 상이는 여전히 미검출 ② `02` 내부 부분 중복(구간 겹침) 전수 감사 미수행 ③ zip·z01~z05 미해제분 미감사 ④ G06 30키 내부 접두 길이 미계측 ⑤ 초 단위는 헤더 산술 ⑥ csv 생성 경위·조각내기 코드 부재로 **발생 지점의 코드 특정 불가**((i)) ⑦ (g) [논증] 3건 중 「오분류 관련」·「자기상관」 2건은 본 조사 무관 — **미실증 유지** ⑧ ~~`fsd50k` 40,966 wav 미감사~~ → 🆕 **부분 해소 (발견일 = 반영일 = 2026-09-21 PoC-(55), 근거유형 = 실측, 계수 단위 = 파일 수, 상세 = 33.14(c))**: **0바이트 감사만** 수행됐다 — **40,966 중 2,414개가 0바이트**이고 **실가용은 38,552**다. 🔴 **md5 내용 중복 감사는 여전히 미수행**이며, 이 부분 해소는 **「0바이트」 축 하나뿐**이다.
- 🔴 **대응 방향 = (e) 그대로 사용자 판단 대기.** 본 항은 **입력만 더했고** 방향·수치·정책 신설 **0건**이다. 발표 서사의 「원천 데이터셋 특성」 계열 서술은 실측 근거를 얻었으나 **문구 확정은 개발 종료 후**(사용자 방침).

**(i) 🔴 [신규 미결] `00_source_raw` · `01_extracted` → `01_clips` 조각내기 코드가 repo에 없다 (발견 2026-09-18 / 문서 반영 2026-09-19 PoC-(53), 근거유형 = 실측 + 경계)**

- **실측**: 대조군 = `ml/pipeline/` **5스테이지 코드 실존**, README · `config.py`가 「`00` / `01_extracted`는 건드리지 않음」 · 「`01_clips`가 입력」으로 **명시**한다. 그 앞 단계(원천 → 조각)의 스크립트는 **repo 어디에도 없다**.
- 🔴 **「repo에 없다」이지 「잃었다」가 아니다** — 스크래치패드 · 타 폴더 소재 **미확인**.
  - → 🆕 **✅ 소재 확인 (발견일 = 반영일 = 2026-09-20 PoC-(54), 근거유형 = 실측, 상세 = 33.10)**: 별개 로컬 repo `~/Desktop/xorms/프로젝트/ddingdong/pretest/scripts/`(33.5가 인용한 pretest repo `park-taegeun/ddingdong-pretest`의 클론, HEAD `7d93743`, 파일 mtime **2026-04-28**)에 **전처리·분할 스크립트 7개가 실재**한다. 🔴 **위 미결 제목은 취소선 대상이 아니다** — 「본 repo에 없다」는 **지금도 사실**이며, 바뀐 것은 **소재가 미확인에서 확인으로** 옮겨간 것뿐이다. [논증] mtime이 본 repo 최초 셋업(**2026-05-07**, 카테고리 16)보다 **9일 앞서므로** 본 repo에 0줄인 것은 **결함이 아니라 이력**이다. ⚠️ 위 **파급**의 「발생 지점을 지목할 수단이 없다」도 **입력을 얻었다** — 선두 구간 공통이 3조각 / 2조각 동일로 이어지는 산술(**33.10(c)**, 논증) · 클래스 교차의 `break` 부재 구조(**33.10(e)**, 논증). 🔴 **소재 확인 ≠ 처리 방침 확정** — 아래 「처리 방침 미확정 = 사용자 판단 대기」는 **무변경**이다.
- **파급**: 재발 방지 지점을 **코드로 특정할 수 없다** — 어디서 108키가 선두 10초를 공유하게 됐는지, 왜 2세그먼트가 두 클래스에 들어갔는지의 **발생 지점을 지목할 수단이 없다**. **5.2(a)의 「`04_direct_recording` → `01_clips` 유입 경로가 코드에 0건」과 같은 축** — 파이프라인 **입구가 통째로 repo 밖**이다.
- **(e) 대응 ①(중복 제거 후 재split · 재학습)을 고르면 `01_clips`를 손으로 고치는 것 말고 방법이 없다** — 조각내기 단계를 재실행할 코드가 없기 때문이다.
- 🔴 **처리 방침 미확정 = 사용자 판단 대기.** 해소책을 적지 않는다(스코프 제외 · §9 대상).
  - 🆕 **[판정 — 발견일 = 반영일 = 2026-09-21 PoC-(55), 근거유형 = 논증 + 실측, 계수 단위 = 미결 축 수] 2축 중 1축만 닫힌다**: 사용자 결정 **D1**이 중복을 **split 단계에서** 걸러내므로(`split.select_clips()` — `02_preprocessed` 파일은 **지우지 않고 대상에서만 제외**) **`01_clips`를 다시 만들 필요가 없다.** ⇒ 위 **「(e) 대응 ①을 고르면 `01_clips`를 손으로 고치는 것 말고 방법이 없다」는 무효**가 됐다(그 **파급 축 닫힘**). 🔴 **그러나 본 미결의 「처리 방침」 = 조각내기 코드를 본 repo에 둘지 · 재발 방지를 코드로 어디에 걸지이며 그 축은 여전히 미확정**이다 ⇒ **미결 유지**. 🔴 **「본 repo에 코드가 없다」는 사실 서술도 무변경**(취소선 대상 아님)이다. 상세 = **33.12(e)**.

**관련**: 33.2(test 성적 0.887 · macro_f1 0.848 — 청정값 병기) / 33.6(b)(`source_key` 누수 방지 설계 = 「범위 밖」 경계 · 424건이 누수 포함 값) / 33.6(d)(`stem` 열 = 본 절의 관측 수단 · 「개별 파일명 미기록」 해소) / 33.8(PR #59 하네스 = 발견 수단) / 카테고리 5(데이터셋 저장 위치 · 05 실측 배분 · 원본단위 group split · `manifests`) / 카테고리 20(계측/판정 계층 분리) / 5.2(a)(파이프라인 입구 repo 밖 — (i)와 같은 축) / 5.2(f)((h)가 실측으로 닫은 논증)

---

### 33.8 PoC-(48) 세션 코드 PR 3건 — 방법론 자산 2 + 정합성 정정 1 (2026-09-15 PoC-(48) 신설, 근거유형 = 실측)

> 33.6·33.7이 **측정 결과**의 절이라면 본 절은 그 **수단·자산**의 절이다(6.3(o) 「방법론 자산」 · 9.1(e) `tof_pinscan` 선례와 같은 성격 구분). 전건 **노트북 단독·보드 미사용** 세션 산출이며 **④런타임 미수행**이다.

  | PR | 커밋 | 성격 | 내용 |
  |---|---|---|---|
  | **#58** | `01f5796` | **방법론 자산** | `confidence` 2자리 반올림 ↔ 신뢰도 게이트 **순서를 회귀로 고정**(계측 계층). 서버 테스트 **102 → 104**(계수 단위 = 테스트 메서드 수) |
  | **#59** | `4d79aa7` | **방법론 자산** | 게이트 축 전수 스윕 하네스 `server/tools/gate_axis_sweep.py` **신설**(581줄) |
  | **#60** | `00f43f8` | **정합성 정정** | 데이터 루트 fallback 제거(fail-fast) + **라벨 순서 일치 확인 신설** |

- **#59 종료 코드 값 도메인** = `{0 전건 일치 / 1 재현 불일치 / 2 raw↔rounded 불일치 / 3 환경·입력 오류}`이며 **#60이 `4`(라벨 순서 불일치)를 추가**했다. `--self-test` **9 → 13 PASS**(계수 단위 = NC 체크 수). ⚠️ `4`를 `1`과 **가른 이유** = 라벨이 어긋나면 집계가 **통째로 오라벨링**인데 `1`로 나오면 *"모델이 달라졌나"*로 **오독**된다.
- 🆕 **[등재 — 2026-09-17 PoC-(51), 근거유형 = 실측 코드 읽기(실행 0)] #59는 「기준 데이터 전용 재현기」다 — 외부 세트에 그대로 쓰면 항상 `1`로 끝난다**: `BASELINE_AXIS`(doorbell 62 / knock 108 / fire_alarm 254) · `BASELINE_NG_CONFUSION` · `BASELINE_CORRECT 376` · `BASELINE_TOTAL 424`가 33.6(b)(d) 인용 상수로 **하드코딩**돼 있고 `compare_baseline()`이 **전 칸 정확 일치**를 요구한다(느슨한 비교를 주석이 금지한다 — 그래야 NC-2가 통과하지 못한다). ⇒ 기준 세트가 아닌 입력에서는 **총 건수부터 어긋나 `1`(기준값 불일치)로 끝난다.** 🔴 **그 `1`은 「모델이 나쁘다」가 아니라 「입력이 기준 세트가 아니다」**이며, **재현 불일치의 증거로 읽으면 오독**이다. ⇒ **외부 평가에 쓸 때는 `--rows-out`의 행 단위 출력만 읽고 종료 코드와 재현 대조 줄은 무시**한다. 세트 교체 시 읽는 문서는 `manifests/split_manifest.csv`의 `test` split이며 **같은 폴더의 `final_manifest.csv`는 split 정의가 아니다**(카테고리 5.1 정합). 외부 세트 경로 = **5.2(c)**.
- **#60 fail-fast 실측**: 인자·env **둘 다 없음 / 빈 문자열 / 공백** **3분기 전부 `ValueError`**, env 주입 시 `~` 확장 **유지**, **인자 우선 유지** — **5분기 학부생 실측 확인**.
- 🔴 **#60이 해소한 것**: `ml/pipeline/config.py`의 `DEFAULT_DATA_ROOT`가 **카테고리 5가 「OS TCC(EPERM) 차단 → 학부생 홈 `~/ML 학습 데이터/ddingdong_dataset` 로 이동 확정」이라 등재한 옛 경로**를 **약 3개월간** 가리키고 있었다. **fallback이 있었기 때문에 아무도 걸리지 않았다** — 「틀린 값을 조용히 계속 쓴」 사고 유형이다. ⇒ 본 PR은 **새 정책 신설이 아니라 등재된 카테고리 5 정책에 코드를 맞춘 정합성 정정**이며, 정본 관용구(`DDINGDONG_DATA_ROOT="…" python -m ml.pipeline.run_all`)는 **무변경**이다.
- ★ **학습 21 사례 — 부재 판정이 한 겹 위에서 멈췄다**: 상세·대조군 = 학습 21 5분류 자리의 하위 단서. 최종 호출자 **3곳(`run_all.py` · `train.py` · `evaluate.py`) 전부 인자 `None` 도달 가능**이었다.
- 🟡 **[등재 — 2026-09-15 실측] PR #60이 남긴 문서 stale (본 Set 범위 밖 — 수정 0건)**: `ml/pipeline/README.md`의 실행 예시가 **제거된 옛 절대경로**를 그대로 싣고 있고, `ml/training/README.md` · `ml/training/train.py` · `ml/training/evaluate.py`의 docstring은 **env가 이제 필수**임을 적지 않는다. ~~⇒ **등재만 한다** — 코드·README 수정은 **별건**이다.~~ → **✅ 해소 (2026-09-15 PoC-(49), PR #61 `b56da39`, 근거유형 = 실측 `git show`)**: 「별건」이 **같은 날 처리**됐다.
  - **커밋 2개** — `0f50281` **📝 Docs**(`ml/pipeline/README.md`의 제거된 옛 절대경로 예시를 `DDINGDONG_DATA_ROOT="~/ML 학습 데이터/ddingdong_dataset"` 형태로 교체 / `ml/training/README.md`에 env가 **이제 필수이며 없으면 `ValueError`로 즉시 실패**(PR #60)임을 명기) · `8709ba8` **🗃️ Comment**(`ml/training/train.py` · `ml/training/evaluate.py` docstring에 같은 사실 명기).
  - 🆕 **같은 PR이 함께 정정한 것 — 본 절이 등재하지 않았던 stale 2건 (근거유형 = 실측)**: `firmware/docs/MIC_NOISEPROBE_RUNBOOK.md`의 **「모드 5개」(0절·3절) → 실물 7모드(m0~m6)**(PR #55 머지분 반영) / **「ToF 판정은 로그하지 않지만」(1절) → `tofJudgeFrame` 내부가 호출부와 무관하게 `[tof]` 줄을 출력한다**로 실측대로 교체. ⇒ 본 절의 stale 등재는 **ML 계열만** 담고 있었고 **펌웨어 문서 계열은 빠져 있었다.**
  - 같은 PR이 `server/app/kakao.py` docstring의 **「폴백」 표현**도 정정했다 — 상세 = **7.7(k)**.
  - **PR #61 성격 = 정합성 정정**(MCP 자기 판정 — 위 표의 #60과 같은 축). **로직·코드 토큰 0줄 변경**(`ast.dump` 해시 수정 전후 동일). **원격·로컬 브랜치 삭제 완료.**

**관련**: 33.6(d)(#59 하네스 = 재현 수단 · 4회차 재현) / 33.6(e)(#58 회귀가 고정한 축 · `all_scores` 파급) / 33.7(#59가 누수 발견의 수단) / 33.2(라벨 순서 = `CLASSES` 상속 — #60 확인의 비교 대상 · `labels.json` 위상) / 카테고리 5(#60이 맞춘 정책 · 데이터셋 저장 위치) / 27.8(j)(본 세션 위임 인용 오기) / 학습 21(부재 판정이 감싸는 함수 앞에서 멈춘 사례) / 카테고리 20(negative control · 계측/판정 계층 분리) / 29.6(커밋 컨벤션 — Type 분리 커밋)

---

### 33.9 선행 논문 서지 등재 — MANSHIP(도시 소리 분류) (2026-09-18 PoC-(53) 신설, 근거유형 = 웹 서지 확인(2026-09-16), 발견일 2026-09-16 / 반영일 2026-09-18)

- **서지**: Njimbouom · Lee · Kim, *Technology and Health Care* **2025, 33(4) 1787–1799**, 선문대.
- **내용**: **VGG16 + ResNet-50** 구성으로 **도시 소리 데이터에서 97.14%**를 보고한다.
- 🔴 **우리 수치와 병치 금지**: **데이터셋과 클래스 구성이 다르다** — 우리 **3클래스**(`doorbell` · `knock` · `fire_alarm`) YAMNet 파인튜닝 성적(33.2 · 33.6(b)(d))과 **같은 축의 수치가 아니다**. 한 표·한 문장에 나란히 두지 말 것이며, **발표 자료에서 「97.14% 대비」류 비교 서술을 만들지 말 것**이다.
  - ⚠️ **[정정 2026-09-18 PoC-(53) — PR #65 `601e7a2`, 내부 커밋 `4e9e942`] 위 문구는 등재 시 「우리 4클래스(… · `other`)」로 적혀 있었다 — 실물은 3클래스다**: 33.2 `Dense(3)` · `ml.pipeline.config.CLASSES` 3종 · `app.constants.PREDICTED_CLASSES` 3종. **`other`는 구현이 아니라 33.6(a) 「대응 방향 = 사용자 판단 대기」의 선택지(「4번째 클래스」)** 다. ⇒ **미결 상태는 무변경**이며 본 정정은 클래스 수 오기만 되돌린다. ※ **회차 라벨 정정 (2026-09-19)**: 본 항은 등재 시 회차를 「(54)」로 적었다 — **(54)는 인계 패키지 제목의 다음 회차 예고를 현재 회차로 오독한 것**이고 2026-09-18~19는 **PoC-(53)**이다(채팅방 미분리로 한 회차가 이틀에 걸침). 값은 맞고 라벨만 틀린 6.3(n) C-0 계열 — 상세 = **27.8(o)①**.
- **위상**: **선행 연구 서지**일 뿐 우리 설계·성적의 근거가 아니다. 인용 논문 위상 관리 선례 = 33.5 「인용 논문 위상 재검토」(Meliza 2013을 **보조층 근거**로 내린 건).
- ⚠️ **등재 경위**: 2026-09-17 · 2026-09-18 PoC-(52) Set 1에서 **연속 2회 누락**됐던 항목이다(프로젝트 지침 8항 등재 대기분). 본 절로 **해소**되며, `decisions.md` 사전 grep은 `MANSHIP` · `Njimbouom` · `Technology and Health Care` · `97.14` · `선문대` · `ResNet-50` **전건 0건**이었다.

**관련**: 33.2(YAMNet 예비 학습 성적 — **병치 금지 대상**) / 33.6(b)(d)(held-out 재현 · 게이트 축 — **병치 금지 대상**) / 33.5(인용 논문 위상 관리 선례) / 26.7(발표 스크립트 출처)

---

### 33.10 파이프라인 입구 코드 소재 규명 — 조각내기 스크립트는 별개 pretest repo에 실재한다 + 4번째 `TARGET` `smoke_detector` 실측 (2026-09-20 PoC-(54) 신설, 발견일 = 반영일 = 2026-09-20, 근거유형 = 항목별 병기 — 실측 / 논증 / 문서 인용, 계수 단위 = 파일 수 / 세그먼트 수 / 행 수 / 클래스 수 — 항목별 병기)

> 전건 **학부생 로컬 셸 실측분**이며 본 절이 그 원본이다. 🔴 **읽기 전용 조사** — pretest repo **수정 · 실행 · 복사 0** / 데이터셋 **무접촉** / 본 repo 코드 **무수정**. 본 절은 **33.7(i)가 「미확인」으로 남긴 소재**를 채우고, 그 코드가 **33.7(h)의 미확정 2건 중 csv 출처 쪽**을 닫는다. 🔴 **대응 방향 · 정책 · 수치 신설 0건**이다.

**(a) 소재 — 본 repo와 다른 별개 로컬 repo다 (근거유형 = 실측, 계수 단위 = 파일 수)**

- 조각내기 코드 소재 = `~/Desktop/xorms/프로젝트/ddingdong/pretest/scripts/`. **본 repo와 다른 별개 로컬 repo**이며, **33.5가 인용한 pretest repo**(`park-taegeun/ddingdong-pretest`)의 **클론**이다. HEAD `7d93743` *"feat: add preprocessing pipeline and train/val/test split"*, 파일 mtime **2026-04-28**.
- **스크립트 7개**: `aihub_preprocess.py` · `audioset_download.py` · `audioset_filter.py` · `audioset_preprocess.py` · `dataset_split.py` · `fsd50k_download.sh` · `fsd50k_preprocess.py`.
- 🔴 **[논증 — 입력 실측 = 위 날짜 2건]** 위 mtime **2026-04-28**은 **본 repo 최초 셋업(2026-05-07, 카테고리 16)보다 9일 앞선다.** ⇒ 본 repo에 조각내기 코드가 **0줄인 것은 결함이 아니라 이력**이다 — 코드가 먼저 다른 repo에서 쓰였고 본 repo는 그 산출물(`01_clips`)부터 시작했다. ⚠️ 이는 **33.7(i)의 「repo에 없다」를 뒤집지 않는다** — 그 서술은 지금도 사실이고, 여기서 바뀐 것은 **그 사실의 해석**이다.

**(b) 조각내기 규칙 — 3개 전처리 스크립트가 완전 동형이다 (근거유형 = 실측 코드 대조, 계수 단위 = 파일 수 / 클래스 수)**

- `01_clips`의 **3클래스를 전부** 만드는 전처리 스크립트는 **3개**이고 **규칙이 완전 동형**이다: `CLIP_SEC = 3.0` / `start = i * CLIP_SEC` / `start_ms = int(start*1000)` / 출력명 `{stem}_{start_ms:07d}.wav` / ffmpeg `-ss {start} -t 3.0 -ar 16000 -ac 1 -sample_fmt s16` / `n_clips = int(duration // CLIP_SEC)`(**마지막 불완전 조각 버림**) / `if out_path.exists(): skipped`(**멱등**).
- **담당 분담**: `aihub_preprocess` → `fire_alarm` / `audioset_preprocess` → `01_clips/{class}` / `fsd50k_preprocess` → `doorbell` · `knock`.
- **유일한 분기**: `fsd50k_preprocess`만 `duration < CLIP_SEC`일 때 `{stem}_0000000.wav` **단일 클립**을 만든다.

**(c) 🔴 33.7(h)의 「선두 구간 동일」이 코드로 설명된다 (근거유형 = 논증, 입력 실측 = (b) + 33.7(h))**

- ffmpeg가 **선두부터 고정 간격**으로 자르므로, 원천 앞 ≈**10.0초**가 공통이면 `0000000` · `0003000` · `0006000` **3조각이 동일**하고, ≈**8.95초**면 **2조각이 동일**하다 — 33.7(h)가 실측한 **G01(3조각) · G04(2조각)** 구조와 **산술이 맞는다**.
- ⚠️ 33.7(h)가 *"디코딩 결정성에 기댄 논증"*이라 적은 그 **결정성의 주체가 특정**됐다 = **ffmpeg + (b)의 인자**. 「어떤 도구의 결정성인가」가 미상이던 자리가 채워졌다.
- 🔴 **ffmpeg 버전이 코드에 박혀 있지 않다** — **재실행 결정성은 여전히 논증**이며 본 항으로 실측 승격되지 않는다. **논증 등급 무변경.**

**(d) `PIECE_SUFFIX_PATTERN`의 발원 (근거유형 = 문서 인용(코드 주석) + 논증)**

- [문서 인용] `dataset_split.py` 머리 주석이 *"파일명 규칙: {source_stem}_{start_ms:07d}.wav → source_stem이 그룹키"* · *"마지막 _XXXXXXX 제거"*를 적는다.
- [논증] ⇒ 본 repo `ml/pipeline/config.py`의 `PIECE_SUFFIX_PATTERN = r"_\d{7}$"`와 **동일 규칙이며 그 발원**이다. ⇒ **33.7(d)가 적은 「파일명 기준이라 내용 동일 파일은 방어 범위 밖」이라는 경계도 여기서 상속**된 것이다 — 본 repo가 새로 만든 한계가 아니다. ⚠️ 33.7(d)의 **「설계 결함이 아니라 범위 밖」 판정은 무변경**이다(취소선 대상 아님).

**(e) 클래스 교차 — 33.7(h) 미확정이 한쪽으로 기운다 (근거유형 = 논증, 코드 구조)**

- `audioset_filter.py`의 `TARGET` 순회에 **`break`가 없다** — 한 세그먼트의 `label_list`에 **두 클래스 mid가 있으면 두 결과 리스트에 각각 들어간다**.
- ⇒ 33.7(h)가 *"AudioSet 원본 다중 라벨인지 우리 필터링인지 미확정"*이라 한 것이 **원본 다중 라벨 쪽으로 기운다** — 우리 필터가 **없던 교차를 만들어 낸 것이 아니라, 원본에 두 라벨이 있으면 그대로 두 곳에 넣는 구조**이기 때문이다.
- 🔴 **해당 2세그먼트의 실제 `label_list`는 미확인**이다 — `balanced_train_segments.csv` **원본 미열람**. **확정하지 말 것.**

**(f) ✅ csv 출처 — 33.7(h)의 「생성 코드가 repo에 없어」가 닫힌다 (근거유형 = 실측, 계수 단위 = 파일 수 / 행 수)**

- `00_source_raw/audioset/`의 **csv 8개**는 pretest `data/filtered/`의 **복사본**이다 — **8쌍 전건 행 수 동일**(실측 `wc -l`).
- **생성 코드 = `audioset_filter.py`**로 확정됐고, 산출 경로(`data/filtered/{split}_{name}.csv`)도 **코드와 일치**한다.
- ⇒ 33.7(h)의 *"csv 8개는 3열 가공본이고 생성 코드가 repo에 없어"* 중 **생성 코드 부재 축이 해소**된다. ⚠️ **(e)의 미확정(원본 라벨 vs 우리 필터링)은 별개 축이며 그대로 남는다** — 한 문장으로 묶어 읽지 말 것.

**(g) 🆕 신규 사실 — 4번째 `TARGET` `smoke_detector` (근거유형 = 실측, 계수 단위 = 세그먼트 수(헤더 1줄 제외) / 클래스 수 / 파일 수)**

- `audioset_filter.py`의 `TARGET`은 **4개**다: `doorbell`(`/m/03wwcy`) · `knock`(`/m/0dxrf`) · **`smoke_detector`(`/m/01g50p`)** · `fire_alarm`(`/m/07pp_mv`). 최종 `CLASSES`는 **3종**이라 **`smoke_detector`는 파이프라인 어디에도 없다**.
- **세그먼트 수 실측**:

  | 클래스 | balanced_train | eval | 합계 |
  |---|---|---|---|
  | doorbell | 60 | 60 | 120 |
  | knock | 60 | 60 | 120 |
  | fire_alarm | 60 | **61** | 121 |
  | **smoke_detector** | **183** | **166** | **349** |

- 🔴 **오디오는 0이다** — `00_source_raw/` 직하는 `aihub_alarm` · `audioset` · `fsd50k` **3폴더뿐**이고, 데이터셋 전역 `find -iname "*smoke*"` 결과는 **위 csv 2건뿐**이며, 본 repo `docs/` · `ml/` · `server/` grep도 **0건**이다. ⇒ **긁기는 실행됐고 다운로드는 안 됐다.**
- ⚠️ **`fire_alarm` eval만 61(+1)** — 33.7(h)가 실측한 `eval_doorbell.csv ∩ eval_fire_alarm.csv = 2세그먼트`와 **맞물릴 수 있으나 수가 정확히 대응하지 않는다**. 🔴 **확정하지 말 것.**
- **[논증]** 3클래스가 **60 / 60으로 고르게 잘린 것**은 `audioset_filter.py`에 **상한 코드가 없고 전수 순회**이기 때문이므로 **AudioSet 원본 분포로 읽는다** — 우리 측 절단이 아니다.

**(h) 한계 (전건 명기)**

- **ffmpeg 버전 미기록** — (c)의 재실행 결정성은 **논증**이다.
- (e)의 **2세그먼트 실제 `label_list` 미확인** — 원본 csv 미열람.
- 🔴 **경로 stale 3건 (근거유형 = 실측)**: 세 전처리 스크립트의 `SOURCE_DIR` / `OUTPUT_BASE`가 **Desktop 옛 경로**를 가리킨다. **카테고리 5.1이 TCC(EPERM) 차단으로 `~/ML 학습 데이터/` 이동을 확정**한 것과 **어긋난다** ⇒ **이대로 재실행하면 다른 위치에 쓴다.** **PR #60이 본 repo `ml/pipeline/config.py`의 `DEFAULT_DATA_ROOT`에서 고친 것과 같은 종류의 stale**이다(33.8). ⚠️ 본 절은 **등재만 한다** — pretest repo는 **범위 OUT**이라 수정 0건이다.
- `smoke_detector` **오디오 0** · csv에 실린 **YouTube 링크 생존률 미확인**.
- 🔴 **`smoke_detector`는 `fire_alarm`과 같은 계열 경보음**이다 — **33.6(a)의 OOD 축**(목소리 · 잡음이 `fire_alarm`으로 수렴)이 **완화되는지는 미실증**이다. **두 축을 섞어 읽지 말 것.**
- 본 조사는 **읽기 전용**이다 — pretest repo · 데이터셋 **무접촉**(수정 · 실행 · 복사 0). 실행 재현이나 바이트 재계측은 **하지 않았다**.

**(i) 파급 — 사실까지만 (근거유형 = 논증)**

- 33.7(i)는 *"(e) 대응 ①(중복 제거 후 재split · 재학습)을 고르면 `01_clips`를 손으로 고치는 것 말고 방법이 없다"*고 적었다. 조각내기 코드가 확보됐으므로 **재생성 경로가 생겼다**는 **사실까지만** 적는다.
- 🔴 **33.7(e) · 33.6(a)의 대응 방향 선택은 사용자 판단 대기 그대로다.** 본 절은 **선택지를 평가하지도 권고하지도 않으며**, 방향 · 임계 · 정책 · 수치 신설 **0건**이다.

**관련**: 33.7(h)(원천 귀속 감사 — csv 출처 부분 해소 · 선두 구간 논증의 도구 특정) / 33.7(i)(소재 「미확인」 → 본 절이 채움 · 미결 자체는 유지) / 33.6(a)(「4번째 클래스」 선택지의 판단 입력 — 대응 방향 미확정 유지) / 5.2(a)(파이프라인 입구가 repo 밖 — 같은 축 · 유입 경로 부재는 무변경) / 33.5(pretest repo 인용 선례 — 같은 repo) / 5.1(TCC 차단 → 데이터 루트 이동 확정 — (h) 경로 stale의 대조 기준) / 33.8(PR #60 = 같은 종류 stale의 본 repo 선례) / 카테고리 16(본 repo 최초 셋업 2026-05-07 — (a) 논증의 입력) / 카테고리 20(계측 / 판정 계층 분리) / 학습 21(「repo에 없다」가 「존재하지 않는다」는 아니었다 — 부재 판정의 경계)

---

### 33.11 열린 미결의 차단 사유 실물 검증 — 전수 발굴 조사 (2026-09-20 PoC-(54) 신설, 발견일 = 반영일 = 2026-09-20, 근거유형 = 항목별 병기 — 실측 / 논증 / 문서 인용, 계수 단위 = 문형 매치 인스턴스 수 / 매치 줄 수 / 절 수 / 고유 미결 수 / 선별 건수 — 항목별 병기)

> 🔴 **읽기 전용 조사**다 — 본 repo 코드 **무수정 · commit 0**(본 문서 커밋 제외) / **repo 밖 무접촉** / 노션 무접촉. 🔴 **본 절은 「차단 사유 문장이 실물보다 낡았다」는 사실 판정이지 「지금 하라」는 권고가 아니다.** **어떤 미결도 닫지 않으며 대응 방향 · 해소책 · 권고 · 임계 · 수치 신설 0건**이다.

**(a) 조사 방법 (근거유형 = 실측, 계수 단위 = 항목별 병기)**

- **문형 전수 스캔** — `docs/decisions.md`에서 열린 미결을 표지하는 문형 3종(`[신규 미결]` / `판단 대기` / `미결 유지`)을 전수 매치했다.

  | 계수 단위 | 값 | 재현 |
  |---|---|---|
  | 문형 매치 인스턴스 수 | **88** | ⚠️ **MCP 재현값 = 86**(Δ2, 아래 (e) 참조) |
  | 매치 줄 수 | **80** | ✅ MCP 재현 **일치** |
  | 매치가 걸린 절 수 | **33** | ✅ MCP 재현 **일치** |
  | 고유 미결 수 | **30** | 판단 집계 — MCP 미재현 |
  | 그중 이미 닫힌 것 | **2** | 판단 집계 — MCP 미재현 |
  | **열린 고유 미결** | **28** | 판단 집계 — MCP 미재현 |

- **선별 후 실물 검증 = 16건**(계수 단위 = 선별 건수). 각 건의 **차단 사유 문장**을 코드 · 라이브러리 · 설치 패키지 · 워킹트리 실물과 대조했다.
- **방법론 3종**:
  - **부재 판정에 대조군 동반** — 「없다」를 적기 전에 **같은 명령이 무엇을 잡는지** 보여 **도구 생존을 증명**한다(예: Motion Indicator grep이 제품 코드 · 라이브러리 원본 · 호스트 스텁을 **별개로** 잡았다 / `.env` 키 중복 집계에서 나머지 키가 **전부 1**을 반환했다).
  - **래퍼 추적** — 상수 · 심볼이 여러 벌일 때 **실제로 상속되는 벌**까지 따라간다(7.7(l) `UPLINK_HTTP_TIMEOUT_MS` 선례).
  - **범위 경계 명시** — 부재는 **「본 repo 부재, 범위 밖 미확인」**으로 적는다. ★ **「repo에 없다」는 본 repo 범위 위에서만 유효하다**(33.10 교훈 · 학습 21).

**(b) 분류 결과 (근거유형 = 논증, 입력 = (a)의 16건 실물 대조, 계수 단위 = 선별 건수)**

| 분류 | 건수 | 뜻 |
|---|---|---|
| **A — 차단 사유 유효** | **5** | 문장이 지금도 실물과 맞는다 |
| **B — 차단 사유 유령** | **6** | 문장이 실물과 어긋나거나 사유의 성격이 문장과 다르다 |
| **C — 하드웨어** | **3** | 보드 · 현장 의존이라 적힌 건 |
| **판정 불가** | **2** | 실물로 갈리지 않는다(정책 · 범위 밖) |

**(c) 🔴 B 6건은 한 덩어리가 아니다 — 「문장이 실물보다 낡은 것」은 2건뿐이다 (근거유형 = 항목별 병기)**

🔴 **B 6건을 「전부 지금 가능」으로 읽지 말 것.** 나머지 4건은 성격이 전혀 다르다.

- **B-① 9.1 Stage B 차단 사유 (근거유형 = 실측 코드 대조) — 문장이 낡았다.** `initToFMotionIndicator()`가 `firmware/src/tof_common.cpp`에 **완전 구현**돼 있고 `platformio.ini`의 **env 5개**에 편입돼 있는데 문장은 *「실구현·④런타임 미착수」*로 남아 있었다. 게다가 **같은 절 아래가 2026-08-12에 이미 반증**하고 있었다. 상세 · 취소선 처리 = **9.1(h)**. 🔴 **미결 자체는 유지**이며, 실제 잔존 축은 **9.4(e) 프로토콜 ② 미수행** · **9.3(G) 벽면 실사용 정확도 미측정**이다(둘 다 보드 · 현장 의존).
- **B-② 7.7(l) 재판정 트리거 (근거유형 = 실측 + 논증) — 문장이 낡았다.** *「2차 클라이언트 작성 시점으로 넘긴다」*가 지정한 시점이 **이미 왔다** — `firmware/src/uplink_common.cpp`에 `/enrich` 호출부가 있고 `env:enrich_uplink`가 PR #64로 편입됐다(6.7). 상세 = **7.7(l)**. 🔴 **값 · 해결책 신설 0 · 미결 유지.**
- **B-③ 「코드 작성 원칙」 문서 — 유령이 아니다.** 본 repo `docs/` 직하는 `decisions.md` · `decisions-log.md` · `git-convention.md` · `poc-week1-plan.md` + `hardware/` · `presentation/` · `research/`뿐이고 「코드 작성 원칙」 문서는 **본 repo에 없다**(실측). 그러나 그 규범은 **프로젝트 지침 계층**에 있을 수 있고 **본 조사는 repo 밖 무접촉**이다 ⇒ **「본 repo 부재 · 범위 밖 미확인」**이 정확한 표기다. **유령 판정 불가.**
- **B-④ 7.6(i) 네트워크 타임아웃 — 차단 사유가 낡은 것이 아니다.** 「네트워크 타임아웃 미재현」은 **재현됐고**, 그 절이 *「본 (i)가 기다리던 「네트워크 타임아웃 미재현」이 재현됐다 — 실패 원인이 `URLError`(네트워크 도달 실패)」*로 **축 전환을 이미 문서에 적어 두었다**(문서 인용). ⇒ **문서가 낡지 않았다.**
- **B-⑤ 8.7(c) `tailwind-merge` — 실물이 아니라 정책이라 판정 불가 쪽이다.** `dashboard/package.json`이 `tailwind-merge ^3.6.0`을 싣고 설치본이 `extendTailwindMerge`를 **export**한다(실측). 그러나 8.7(c)가 적은 차단은 **「8.4 무변경 대상이라 수정하지 않았다 · 예외 허가는 사용자 판단 대기」**라는 **정책**이다 ⇒ **실물로 갈리지 않는다.**
- **B-⑥ 33.7(i) — 유령이 아니라 방금 채운 것이다.** **33.10이 같은 날(2026-09-20) 소재를 채웠다.** ⚠️ 33.10 본문이 명기했듯 **미결 제목 「본 repo에 없다」는 지금도 사실**이고 **미결 자체는 유지**다 — **소재 확인 ≠ 처리 방침 확정.**

**(d) 🔴 C 3건은 전부 「마지막 ④런타임 단계」만 하드웨어다 (근거유형 = 실측 + 논증, 계수 단위 = 선별 건수)**

- **26.10(d) 진입점 2 (실측)**: 실모델 산출물과 구동 재료가 **전부 워킹트리에 실재**한다 — `ml/models/yamnet/best.keras` · `ml/models/yamnet/inference_savedmodel/` · `server/venv_real` · `server/app/model_serving.py` · `server/tools/gate_axis_sweep.py`. 노트북 구동 이력은 SSoT에 있다(**33.6(c)**). 보드가 필요한 것은 **④런타임에서 그 경로를 타는 것**뿐이다.
  - ⚠️ **「≠」 실증**: `.gitignore`가 `ml/models/`와 `*.keras`를 차단하므로 **`git ls-files ml/models` = 0**이고 **워킹트리에는 있다** ⇒ **「repo에 없다」로 오판하기 쉬운 자리**다(33.10 · 학습 21과 같은 축, 이번에는 **같은 repo 안**에서 났다).
- **8.5 `device_status` / `signal_strength` (실측 + 논증)**: 펌웨어측 `WiFi.RSSI()` 취득은 **이미 5파일 · 9줄**에 있다(계수 단위 = 파일 수 / 출현 줄 수) — `upload_spike_common.cpp`(2) · `upload_spike_tls_common.cpp`(2) · `uplink_common.cpp`(1) · `camera_probe_main.cpp`(2) · `main.cpp`(2). ⚠️ **위임이 적은 「시리얼 로그 한정」은 실물보다 좁다 (학습 19 catch)** — `main.cpp`의 `buildJsonPayload()`는 `doc["rssi"] = (int)WiFi.RSSI();`로 **JSON 본문에 실어 POST까지 한다**. 🔴 **다만 그 대상은 `HTTP_TARGET_URL = "https://httpbin.org/post"` = 에코 스파이크이지 우리 서버가 아니다.** `server/app/` 전역 `rssi` grep **0건**이고 `routes.py`는 `"device_status": "online"` · `"signal_strength": "strong"` **리터럴**이다. ⇒ **부재한 것은 우리 서버와의 전송 · 수신 계약**이며 이는 **노트북 코딩 층**이다.
- **9.1 Stage B-2 (논증, 입력 = 9.3 · 9.4)**: B-1 계측 계층은 ④런타임 실측 완료(**9.3**)이고 B-2 판정 계층 · 임계값도 **확정 + ④런타임 실측 완료**(**9.4**)다. 잔존은 **검증**(9.4(e) 프로토콜 ② · 9.3(G))뿐이다.
- ⇒ **[논증] 「하드웨어 필요」로 뭉뚱그려진 3건 중 전면 차단은 0건이었다(3/3).** 🔴 **이는 「지금 하라」가 아니라 「차단의 위치가 마지막 단계다」라는 사실 판정이다.**

**(e) 한계 (전건 명기)**

- 🔴 **전수가 아니다** — 열린 고유 미결 **28** 중 **16건만** 실물 검증했다(계수 단위 = 고유 미결 수 / 선별 건수). **나머지 12건은 미검증**이다.
- 🔴 **인스턴스 수 88은 MCP가 재현하지 못했다** — 동일 문형 3종으로 MCP가 재계수하면 **86**이다(Δ2). **위임 본문에 문형 정의가 미기재**라 동일 재현이 불가능하다. ⚠️ **매치 줄 80 · 매치 절 33은 일치**하므로 차이는 **줄 안 중복 계수 규칙**에 있을 가능성이 높으나 **확정하지 말 것**. **고유 미결 30 / 닫힌 2 / 열린 28 / 선별 16 / A5 · B6 · C3 · 판정 불가 2**는 **판단이 들어간 집계**라 MCP 재현 대상이 아니며 **위임 본문이 원본**이다.
- 🔴 **정책 성격 미결은 실물로 안 갈린다** — B-⑤ · 「판정 불가 2」가 그 예다. 코드를 아무리 봐도 **「고칠지 말지」는 사용자 판단**이다.
- 🔴 **repo 밖 무접촉이라 범위 밖은 미확인**이다 — B-③이 그 예다. `server/.env` 재실측도 **MCP는 수행하지 않았다**(카테고리 21의 현재값 3은 **학부생 로컬 셸 실측분**이며 본 절이 그 원본이다).
- ⚠️ **본 절은 대응 방향을 적지 않는다** — B 2건이 「문장이 낡았다」로 판정됐다고 해서 **지금 착수하라는 뜻이 아니다**. 두 건 다 **미결 표기가 유지**된다.

**(f) 방법론 자산 — 「미결 감사」와 「미결 해소」의 분리 (근거유형 = 논증)**

- 본 조사는 **미결을 하나도 닫지 않고** **차단 사유 문장의 신선도만** 감사했다. 학습 21(「미결도 유령일 수 있다」)이 **개별 건**에서 발견한 실패 양식을 **문서 전역 스캔**으로 확장한 것이다.
- ★ **드리프트의 절 내부 판이 실재한다** — 9.1처럼 **같은 절이 스스로 반증하면서도 반증된 문장을 그대로 두는** 사례가 나왔다(27.8(m)⑤의 절 내부 판). ⇒ **문서 간 대조뿐 아니라 절 내부 대조도 감사 대상**이다.
- ⚠️ **감사 결과를 해소 계획으로 읽으면 본 절의 전제가 깨진다** — 분류 A / B / C는 **차단 사유 문장의 상태 라벨**이지 **우선순위**가 아니다.

**관련**: 9.1(h)(Stage B 차단 사유 취소선 + 정정 — B-①) / 9.3(B-1 ④런타임 실측 · (G) 벽면 정확도 미측정) / 9.4(B-2 판정 · 임계값 확정 + (e) 프로토콜 ② 미수행) / 7.7(l)(재판정 트리거 충족 — B-②) / 6.5(2차 클라이언트 설계 조사 · 성분 재실측 M-1~M-6) / 6.7(PR #64 `env:enrich_uplink` 편입) / 7.6(i)(네트워크 타임아웃 재현 — B-④) / 8.5(i)(`device_status`/`signal_strength` 거짓 표시 · heartbeat 트리거 — C) / 8.7(a)(PR #67 등재 · `enrich_status="skipped"` 3경로) / 8.7(c)(`tailwind-merge` — B-⑤ · 정책 성격) / 26.10(d)(진입점 2 — C) / 27.8(m)(드리프트 계열 — 절 내부 판) / 33.6(c)(실모델 노트북 구동 이력) / 33.7(i)(소재 축 — B-⑥) / 33.10(「repo에 없다」의 범위 경계 · 같은 날 소재 확인) / 카테고리 21(`.env` 키 중복 현재값 3) / 학습 19(위임 전제 재검증) / 학습 21(미결 · 차단 사유가 유령일 수 있음)

---

### 33.12 split 정책 정비 — 내용 중복 제거 · 해시 고정 배정 · 직접녹음 유닛 키 · 내용 누수 가드 (2026-09-21 PoC-(55) 신설, PR #69 `0461a94`, 발견일 = 반영일 = 2026-09-21, 근거유형 = 항목별 병기 — 사용자 결정 / 실측 / 논증, 계수 단위 = 클립 수 / source 수 / 그룹 수 — 항목별 병기)

> **33.7(e)가 「사용자 판단 대기」로 남긴 대응 방향이 ①(중복 제거 후 재split · 재학습)으로 확정된 회차**다. 본 절은 그 ①의 **split 단계 구현분**까지이며 **재학습은 범위 밖**이다. 🔴 **실데이터셋은 1바이트도 바뀌지 않았다** — 읽기 전용(`'rb'`)이고 파일 수 · mtime을 **3회 대조**(착수 전 ≡ 시뮬레이션 후 ≡ 최종)해 전 구간 동일함을 증명했다(17.2 베이스라인 축).

**(a) 사용자 결정 D1 · D2 · D3 · D5 · D6 (2026-09-21, 근거유형 = 사용자 결정)**

| # | 결정 | 구현 |
|---|---|---|
| **D1** | 내용 동일 파일은 **1개만 유지** · **디지털 무음 제거** · **클래스 교차는 양쪽 모두 제거** | `split.select_clips()` + `manifests/dedup_manifest.csv` |
| **D2** | **그룹 해시 기반 고정 배정**(셔플 · 개수 맞춤 배분 폐지) | `split.assign_split()` — 순수 함수 |
| **D3** | 직접녹음은 **유닛**까지를 그룹 키로 | `config.source_key()`의 `direct_` 분기 |
| **D5** | **웹 음원은 외부 평가 전용** | 코드 변경 없음(5.2(g) 「사용 순서」 축 확정) |
| **D6** | `SAMPLE_WEIGHT_RANGE` **서술을 실물에 맞춘다** | `config.py` 주석(**값 · 존재 무변경**) |

- 🔴 **`02_preprocessed`의 파일은 지우지 않는다** — **split 대상에서만** 제외한다(원본 보존 · 재현 가능). 이것이 **33.7(i)의 파급 축을 닫은 이유**다(아래 (e)).
- **D2 메커니즘 등가 치환 (사용자 공지 완료, 근거유형 = 논증 + 실측)**: 중복을 먼저 제거하면 위임이 지정한 「내용 해시 union」은 **대상이 사라져 무의미**하다. 그래서 불변식 **「같은 내용은 두 split에 없다」**를 `guards.assert_no_content_leakage()`(같은 md5가 **2개 이상 split**에 있으면 `ContentLeakageError`, 예외 메시지에 **해시 · stem · split** 동봉)로 보장한다. **기존 stem 가드는 유지**(2층 이중 검사). ⇒ **학습 16 「불변식 유지 + 메커니즘 등가 치환」** 계열.
- **D6 경계**: 확정된 것은 **「서술을 실물에 맞춘다」**이고 **「구현할지」는 미확정**이다 — `config.py` 주석이 지금도 그렇게 적는다(실측). **카테고리 5 머리** 참조.

**(b) 실측 — 제거 내역과 제거 순서 (근거유형 = 실측 시뮬레이션, 읽기 전용, 계수 단위 = 클립 수 / 그룹 수)**

- **재현 선행**: 고유 내용 해시 **2305 / 2792**로 **33.7(a) 값과 일치**하고 중복 그룹 **15** · 소속 **502** · 순수 잉여 **487**도 전건 재현됐다. ⇒ **도구 신뢰를 먼저 확인한 뒤** 아래를 쟀다(33.7(g)(h)와 같은 절차).

  | 사유 | 계 | doorbell | knock | fire_alarm |
  |---|---|---|---|---|
  | `digital_silence` | 5 | 2 | 1 | 2 |
  | `class_cross` | 10 | 5 | 0 | 5 |
  | `same_class_dup` | 478 | 0 | 0 | 478 |
  | **합계** | **493** | 7 | 1 | 485 |

- 잔존 **2299** 클립이고 **잔존 고유 해시도 2299**(= 잔존 클립 수, **중복 0**)다. 산술 = 잉여 487 = 478 + 무음 잉여 4 + 교차 잉여 5, 제거 493 = 487 + 무음 마지막 1 + 교차 첫 5.
- 🔴 **[실측] 제거 순서가 규칙의 일부다 (계수 단위 = 클립 수)**: **중복 제거를 먼저** 돌리면 교차 그룹에 **한 클래스만 남아 교차 규칙이 무력화**되어 잔존이 **2299 → 2304**가 된다. 무음 · 교차는 서로 순서를 바꿔도 **잔존 집합이 같고 사유 라벨만** 달라진다. ⇒ **순서(무음 → 교차 → 중복)를 코드에 고정**했다. ★ **「같은 규칙 집합도 적용 순서에 따라 다른 데이터셋을 낳는다」**는 기록이다.

**(c) 실측 — 새 배정과 현 매니페스트 대비 변경 규모 (근거유형 = 실측, 계수 단위 = source 수 / 클립 수)**

- **해시 배정 결과**: 합계 **2299 클립 = train 1606 / val 358 / test 335**(비율 .699 / .156 / .146), source 합계 **809**. 클래스별 클립 = `doorbell` **429**(313 / 58 / 58) · `knock` **713**(500 / 120 / 93) · `fire_alarm` **1157**(793 / 180 / 184).
- **새 배정에서 내용 누수 = 0 그룹.**
- 🔴 **현 `split_manifest.csv` 대비 split이 바뀌는 source (계수 단위 = source 수)**: `doorbell` **87** / `knock` **170** / `fire_alarm` **130**. 「신에서 사라진 source」 **4개** = 클래스 교차 **2 `source_key`**(`9OqtuFGCCR8_30.0_40.0` · `uA3bpAQV_hE_0.0_8.0`)가 **양쪽 폴더에서 제거된 결과**다(33.7(g) 정합).
- 🔴 **test 클립 424 → 335.** ⇒ **33.2 · 33.6의 성적과 게이트 축, 33.7의 누수 수치는 전부 「옛 test set 위의 값」이 된다**(5.2(c)가 예고한 얽힘의 실측판). **갱신은 재학습 소관**이다.

**(d) 검증 (근거유형 = 실측)**

- `ml` 테스트 **4종 전건 통과** — `test_pipeline` **12 / 12**(기존 5 + 신규 T1~T7) · `test_dtw_contract` · `test_training_smoke` · `test_export_smoke`.
- 🔴 **기존 케이스 삭제 0 · 수치 갱신 0** — 조사 결과 **분할 결과 수치를 하드코딩한 단언이 0건**이라 갱신 대상 자체가 없었고, 기존 5종이 새 규칙에서 **그대로** 통과했다.
- **negative control**: `NC-1`(배정을 기각된 설계 = 공유 `random.Random(SEED)` + shuffle로) · `NC-2a`(내용 가드만 제거) · `NC-2c`(두 층 모두 제거) · `NC-3`(교차 규칙을 「첫 클래스 유지」로) · `NC-4`(`direct_` 분기 제거) **전건 검출**, 복원 후 **전건 PASS 복귀**.
- 🔴 **[실측] NC-2 함정 — 파이프라인 관통으로 층을 갈랐다**: *「가드만 빼면 dedup이 먼저 막아 통과할 수 있다」*를 확인하려고 같은 내용을 서로 다른 split으로 갈리는 두 `source_key`로 심어 **02 → 05 전관통**했다.

  | 조합 | 결과 |
  |---|---|
  | dedup ✅ / 가드 ✅ | `NO_LEAK`(dedup이 제거) |
  | **dedup ✅ / 가드 ❌** | **`NO_LEAK`** — 🔴 **가드 제거가 관통 경로에서 보이지 않는다** |
  | dedup ❌ / 가드 ✅ | `GUARD_RAISED` — 가드 단독으로 잡는다 |
  | dedup ❌ / 가드 ❌ | `LEAK_UNDETECTED` — 불변식이 실제로 **두 층에 의존**한다 |

  - ⇒ 그래서 내용 누수 테스트(T6)를 **관통이 아니라 가드 단위 테스트**로 두었고 `NC-2a`가 그 층을 직접 검증한다. ★ **카테고리 20 「NC 미검출은 「가드 부재」가 아니라 「도달 불가」일 수 있다」의 재실증**이며, 이번에는 **도달 불가를 설계로 인정하고 테스트 층을 옮긴** 사례다.

**(e) 🔴 운영 규칙 신설 — 파이프라인 실데이터 재실행은 재학습과 한 세트다 (2026-09-21 사용자 확정, 근거유형 = 사용자 결정 + 논증, 입력 실측 = 위 (c))**

- **재학습 전에 `run_all`을 실데이터로 돌리면 안 된다.** 새 test(**335**)에는 **현 모델이 학습한 클립이 섞여** 성적이 부푼다 — **새 누수**다.
- 재실행 시점에는 **33.2 · 33.6 · 33.7의 수치**와 **`server/tools/gate_axis_sweep.py`의 기준값 갱신**이 함께 필요하며, 🔴 **그 갱신은 재학습 소관**이다.
- ⇒ **본 절이 등재하는 유일한 규칙**이며, **임계 · 수치 · 합격선은 신설하지 않는다**.
- **33.7(i) 파급 축 닫힘**: D1이 **split 단계에서** 걸러내므로 **`01_clips`를 손으로 고칠 필요가 없다** ⇒ 33.7(i)가 적은 *「(e) 대응 ①을 고르면 `01_clips`를 손으로 고치는 것 말고 방법이 없다」*는 **무효**다. 🔴 **미결 자체는 유지**된다 — 「조각내기 코드를 본 repo에 둘지」라는 **처리 방침 축은 그대로**다.

**(f) 한계 (전건 명기)**

- **직접녹음 4유닛 = 4그룹**이라 해시 배정이 거칠다 — 🔴 **test 유닛 0이 나올 수 있다.** **유닛 배정 정책은 녹음 도착 시 결정**한다(비율은 기대값이며, 개수를 맞춰 자르던 `_allocate`와의 맞바꿈이다).
- **유닛 표기가 없는 옛 명명**(`direct_doorbell_001`)은 `_\d+$` 제거 규칙상 **한 그룹으로 뭉친다**.
- **근접 중복(파형 동일 · 바이트 상이)은 여전히 미방어**다 — 방어 기준은 **바이트 md5 하나**뿐이다(33.7(f) 잔존 한계와 같은 축).
- `split_manifest.csv` **컬럼 무변경**(`filepath,class,split,stem,source_key`)이고 dedup 내역은 **별도 CSV**로 분리해 하류 계약을 건드리지 않았다 — 하류 전수(`augment.py` · `assemble.py` · `gate_axis_sweep.py`)에 `source_key`를 읽는 곳은 **0건**이다.

**관련**: 33.7((e) 대응 방향 ① 확정 · (g) 클래스 교차 · (i) 파급 축) / 33.2 · 33.6((c)의 재실행 파급 대상) / 5.2((b) 직접녹음 명명 · (c) split 파급 메커니즘 · (g) 대기 항목 분해) / 카테고리 5(머리 `SAMPLE_WEIGHT_RANGE` · 5.1 4유닛 프로토콜) / 33.13(같은 날 결정 — OOD 대응) / 17.2(검증 자산 베이스라인) / 카테고리 20(negative control 도달 불가 판정) / 학습 16 · 19

---

### 33.13 OOD 대응 방향 확정 — 4번째 클래스 `other` 신설 (2026-09-21 PoC-(55) 신설, 발견일 = 반영일 = 2026-09-21, 근거유형 = 항목별 병기 — 사용자 결정 / 논증, 계수 단위 = 결정 건수)

> **33.6(a)가 2026-09-12부터 「사용자 판단 대기」로 달고 있던 OOD 대응 방향이 확정된 회차**다. 🔴 **본 절은 결정과 그 경계까지이며 코드는 0줄 바뀌지 않았다** — 계약 코드는 **재학습 모델 산출 후 별도 PR**이다. **합격 수치 · 임계 신설 0건.**

**(a) 사용자 결정 D4 · E1 ~ E4 (2026-09-21, 근거유형 = 사용자 결정)**

| # | 결정 | 경계 |
|---|---|---|
| **D4** | **4번째 클래스 `other` 신설** | 33.6(a)의 「4번째 클래스」 선택지 채택 |
| **E1** | `predicted_class="other"`로 **DB에 기록**하고 **1차 · 2차 모두 미발송**, `skip_reason="not_target"` | **`not_target`은 신규 어휘** — **계약 PR에서 확정**한다 |
| **E2** | **`other` 판정을 게이트 맨 앞**에 둔다(`other` → 신뢰도 → `fire_alarm` 우회 → ToF) | **펌웨어 변경 0** |
| **E3** | 네거티브 출처 = **로컬 FSD50K 우선 + AudioSet 보충** | 1단계 산출 = **33.14** |
| **E4** | 지표 = **① 기존 OOD 자산의 `fire_alarm` 발송 수** · **② 청정 test target recall 하락폭** | 🔴 **지표만 확정. 합격 수치는 재학습 후** |

- 🔴 **E1의 `skip_reason="not_target"`은 아직 코드에 없다** — 8.7(a)가 실측한 `enrich_status="skipped"` **3분기**(`low_confidence` · `fire_alarm` · `tof_rejected`)와 **별개 축의 신규 어휘**이며 **계약 PR에서 확정**한다. **지금 3분기 표를 고치지 말 것.**
- 🔴 **E2는 순서만 정했다** — 임계값 · 판정식은 **신설하지 않았다**.

**(b) 보류 3건 (근거유형 = 사용자 결정)**

- **`smoke_detector` 클래스**(33.10(g)의 4번째 `TARGET` 349세그먼트) — 🔴 **`fire_alarm`과 같은 계열 경보음이라 OOD 해결책이 아니다.** 33.6(a)의 OOD 축(목소리 · 잡음이 `fire_alarm`으로 수렴)과 **섞어 읽지 말 것.**
- **`fire_alarm` 연속 감지 확인** — 수치가 필요하며 **보드 실측 후**로 미룬다.
- **장치 설치 위치(문 안 / 밖)** — **SSoT 미등재이며 사용자 판단 대기**다(5.2(g) 동일 항목).

**(c) 착수 전 비용 — 계약 PR Step 0에서 실측할 대상 (근거유형 = 논증, 본 절에서 실측하지 않았다)**

- `server/app/model_serving.py`가 **프로즌 예외**를 필요로 할 가능성.
- `server/inference/*`가 **3클래스를 가정**하는지 여부.
- 파급 후보 = **`PREDICTED_CLASSES`** · 대시보드 **`PredictedClass`** · 통계 **클래스 분포 내부 키** · **`labels.json`** · **`gate_axis_sweep`의 라벨 검사**.
- 🔴 **위 5건은 전부 「확인할 자리」이지 실측 결과가 아니다** — **계약 PR Step 0에서 실물 대조**한다. **여기에 수치를 적지 않는다.**
- **계약 PR은 재학습 모델 산출 후 머지**한다(순서 고정).

**관련**: 33.6((a) OOD 수렴 — 본 절이 그 대응 방향 · (f)(g) 확장 스윕과 실음원 입력) / 33.14(E3 1단계 산출 — 네거티브 후보) / 33.10(g)(`smoke_detector` 판단 입력 — 보류 근거) / 26.10(d)(부스 대화 소리 파급) / 8.7(a)(`enrich_status="skipped"` 3분기 — `not_target`과 별개 축) / 33.12(같은 날 결정 — split 정책) / 카테고리 3(G12 게이트 순서)

---

### 33.14 `other` 네거티브 후보 선별 — FSD50K dev 덤프에서 1,100 후보 (2026-09-21 PoC-(55) 신설, PR #70 `a06599d`, 발견일 = 반영일 = 2026-09-21, 근거유형 = 항목별 병기 — 실측 / 논증 / 사용자 결정, 계수 단위 = 클립 수 / 라벨 종수 / 파일 수 — 항목별 병기)

> **33.13의 E3 1단계**다 — **읽기 전용**으로 후보 목록만 만든다. 🔴 **오디오 복사 · 변환 · 3초 조각내기 · 파이프라인 투입은 전부 재학습 소관**이며 본 회차 범위 밖이다. 산출 원본 = repo 밖 `~/ddingdong-측정결과/2026-09-21/negatives/`(`candidates.csv` · `summary.md` · `listen_sample.csv` · `listen_qa.csv` · `listen_qa_note.md` — `.gitignore` 차단분, SSoT엔 요약만). **데이터셋 · 메타데이터 쓰기 0.**

**(a) 1차 §9 정지 — 로컬 덤프에 라벨 메타데이터가 없었다 (근거유형 = 실측)**

- E3의 전제 *「로컬 덤프 = 리드타임 0」*이 깨졌다 — 덤프에는 **wav 40,966개와 오디오 zip만** 있고 **라벨 메타데이터가 없었다**.
- 학부생이 **Zenodo record 4060432**에서 반입해 **`~/ML 학습 데이터/fsd50k_meta/`**(**데이터셋 밖 · 읽기 전용**)에 두었다. md5 = `ground_truth.zip` **`ca27382c195e37d2269c4c866dd73485`** / `metadata.zip` **`b9ea0c829a411c1d42adb9da539ed237`**.
- ⚠️ **1차 `curl`은 504 Gateway Time-out**(Zenodo 과부하)이었고 **92 B짜리 에러 응답이 zip 파일명으로 저장**돼 있었다 — `-f --retry`로 성공했다. 🔴 **위임은 원인을 「봇 차단」으로 추정했으나 실물은 504**다(27.8(p)④).

**(b) 선별 규칙 — 부모 라벨을 제외 기준으로 쓰지 않는다 (근거유형 = 논증 + 사용자 결정)**

- **온톨로지는 `dev.csv` 동시출현으로 추정**했다(로컬에 `ontology.json` 부재 ⇒ **근거유형 = 논증**). `Doorbell` ⊂ `Alarm` ∩ `Door`, `Knock` ⊂ `Door`, `Siren` ⊂ `Alarm`.
- 🔴 **`Door`로 제외하면 문 형제(`Slam` · `Sliding_door`)가, `Alarm`으로 제외하면 경보 형제(`Telephone` · `Ringtone`)가 통째로 사라진다** — 그런데 그 둘이야말로 **33.6(a)(f)(g)의 실패 모드(인터폰 전자음 → `fire_alarm`)를 겨냥한 핵심 hard negative**다. ⇒ **target 자신과 그 자식만 제외하고 부모는 제외 기준으로 쓰지 않는다.** 부모는 **「미분화」**(부모만 붙고 하위 라벨 0)일 때만 본다 — 미분화 `Alarm`은 **제외**, 미분화 `Door` · `Bell`은 **보류**.
- **target(제외)** = `Doorbell` · `Knock` · `Siren` + **미분화 `Alarm`**.
- **hold(보류)** = `Tap` · `Chime` · `Church_bell` · `Bicycle_bell` · `Wind_chime` · **미분화 `Door` / `Bell`** + **사용자 결정 보정 5건**(`Glockenspiel` · `Marimba_and_xylophone` · `Mallet_percussion` = **doorbell 차임과 음색 인접** / `Thump_and_thud` · `Wood` = **knock 둔탁음과 인접**).
- **`Speech_synthesizer`는 판단 보류**(ⓐ 유지) — **AI Hub 화재경보 안내 음성일 가능성**이 있어 **청취 전에는 정하지 않는다**.
- ⚠️ **`Beep` · `Timer`는 FSD50K 어휘에 없다** — **부재이지 보류가 아니다**. `Buzz` · `Tick` · `Tick-tock` · `Clock` · `Printer` · `Camera` · `Microwave_oven` 같은 **대체 라벨로 흡수**했다.

**(c) 🔴 발견 2건 — 0바이트 wav (근거유형 = 실측, 계수 단위 = 파일 수)**

- **발견 ①**: 로컬 덤프에 **0바이트 wav 2,414개**가 섞여 있다 ⇒ **실가용은 40,966이 아니라 38,552**다. **33.7(h) 한계 ⑧ 「fsd50k 40,966 wav 미감사」의 0바이트 축 보강**이며, 🔴 **md5 내용 중복 감사는 여전히 미수행**이다.
- **발견 ②**: `01_extracted`의 **0바이트 30개**(doorbell 10 / knock 20)가 **30 / 30 전건** 이 2,414 집합에 포함된다 — **30건 모두 `00_source_raw`에 파일은 있고 크기가 0**이다. ⇒ **`01_extracted`의 0바이트는 조각내기 단계의 결함이 아니라 원천 0바이트가 그대로 흘러내려 온 것**이다(**5.2(f)** · **33.7(g)** 관련 서술의 원인 규명). ⚠️ **이름 대조 기준**이며 바이트 귀속 실측은 아니다.

**(d) 결과 (근거유형 = 실측, 계수 단위 = 클립 수 / 라벨 종수)**

- **후보 1,100**(선택 라벨 **179종**) = ⓐ 음성 · 대화 **213** · ⓑ 방송 · 음악 **200** · ⓒ 생활음 **544** · ⓓ hard negative **143(13.0%)**.
- **PP 1,053 · PNP 3 · NA 44** / dev 내부 split 보존 **train 997 · val 103**.
- **제외 ① target 842** / **사용 불가(0바이트) 2,193** / **보류 2,324** / **적격 풀 35,607**. **합계 검산 = 842 + 2,193 + 2,324 + 35,607 = 40,966** ✅.
- **0바이트 2,414의 분해** = 제외 ① 안의 **59** + 사용 불가 **2,193** + 보류 안의 **162** ✅. ⚠️ **앞 단계에서 이미 걸린 0바이트는 「사용 불가」로 세지 않는다** — **사라진 것이 아니라 다른 칸에 있다.**
- 🔴 **ⓓ 13.0%는 라벨당 균등 상한의 결과**다(ⓓ 라벨이 **24종**뿐). **가중 조정은 하지 않는다 — E4 재학습 결과로 판단**(사용자 결정).

**(e) 결함 수정 2건 + 청취 검수 (근거유형 = 실측)**

- **결함 ①**: 선택 라벨 tie-break가 **부모 라벨(예: `Animal`)을 고르던 것** → **희소도 우선**(번짐으로 올라붙은 상위 노드가 아니라 **잎에 가까운 쪽**)으로 고쳤다. ⚠️ **본 건은 위임 본문이 원본**이다 — **PR 본문에 별도 기재가 없고** 코드 주석 · 구현으로 확인했다.
- **결함 ②**: `classify()`가 **라벨 나열 순서대로** 판정해서 hold 라벨이 target보다 앞에 오면 **제외 ① 이 보류로 샜다**(보정 5라벨 추가로 **실제 2건 발생**). **target 계열은 확정 제외, 보류는 재검토 대상**이라 뒤집히면 **청취 검수에서 target이 다시 들어올 수 있다** ⇒ **target을 전 라벨에서 먼저 훑도록** 고정했고 **미분화 `Alarm`(부모 규칙 target)도 hold보다 앞세웠다**. 순서 뒤집기 단언 **4건 추가**.
- **청취 검수 (학부생 1인, 층화 무작위 30건)**: **target 오염 0 / 30**.
- ⚠️ 🔴 **기호 반전 정정**: 스크립트는 `x = target 있음`으로 정의했으나 학부생이 **한국어 O / X 관례대로 `x = 없음`**으로 입력했다(메모 *「없어」* 2건이 단서). **학부생 확인 후 `verdict`를 뒤집었고 원 입력은 `raw_input` 열에 보존**했다. 🔴 **원 입력을 지웠으면 되돌릴 수 없었다**(27.8(p)③).

**(f) 한계 (전건 명기)**

- **FSD50K 음성은 대부분 영어**다 ⇒ **한국어 대화 네거티브가 없다**(아파트 안내방송 같은 한국 생활음도 없다 — AudioSet 보충 또는 직접 녹음 소관).
- **eval 오디오가 로컬에 없다** — 후보는 **dev에서만** 골랐다.
- **ⓓ 13.0% 가중은 E4 이후 판단**이다.
- **3초 조각내기 · 파이프라인 투입은 재학습 소관**이다 — 본 절은 **목록까지**다.
- **온톨로지 관계는 동시출현 추정**(논증)이며 **실측이 아니다**.
- **청취 검수는 n=30 · 1인**이며, 둔탁음 2건(서랍 · 불꽃놀이)은 **노크 언급 없음으로 처리**한 판정이다.
- **방송 계열 라벨이 FSD50K 어휘에 없어**(`Television` · `Radio` 부재) `Speech_synthesizer` · `Music`으로 **근사**했다.

**관련**: 33.13(E3 1단계 — 본 절이 그 산출) / 33.6(a)(f)(g)(겨냥한 실패 모드) / 33.7((g) `01_extracted` 0바이트 30건 원인 · (h) 한계 ⑧ 부분 해소) / 5.2(f)(0바이트 30건 = 짝 없는 30건과 같은 집합 — 그 원인) / 33.10(b)(`01_clips` FSD50K 유래 원본 347건 — 제외 ②의 대조) / 27.8(p)(①③④⑤ 본 회차 오류) / 카테고리 5(데이터셋 저장 위치 · 덤프 = 입력 아님)

---
