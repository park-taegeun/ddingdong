// 띵동 PoC firmware - ToF 더미 테스트 공통 헤더 (5/11, PoC Day 5)
//
// VL53L5CX-SATEL + ESP32-S3 I2C0. 카메라 (I2S0) / 마이크 (I2S1)와 페리페럴 분리.
// 2026-08-07 브레드보드 브링업 성공 (decisions.md 카테고리 9.1) — 8x8/15Hz 프레임 실동작 확정.
// PWREN/LPn을 3V3로 구동하지 않으면 센서가 셧다운 상태로 SDA를 LOW 고착시켜 I2C 전면 불통.
// 8x8 multi-zone (64 zones) × 15Hz (datasheet limit) 캡처.
//
// 출처:
//   - VL53L5CX datasheet (ST):
//       I2C 7-bit addr 0x29 (8-bit 0x52) / I2C max 1Mbits/s
//       FW upload ~86KB (RAM-based, init 시 자동 로드)
//       8x8 mode max 15Hz, 4x4 mode max 60Hz
//       Power modes: SLEEP / WAKEUP, default WAKEUP
//       Ranging modes: CONTINUOUS / AUTONOMOUS, default AUTONOMOUS
//   - SparkFun_VL53L5CX_Arduino_Library v1.0.3:
//       SparkFun_VL53L5CX class, begin() / setResolution(64) / setRangingFrequency(15)
//       startRanging() / isDataReady() / getRangingData(&VL53L5CX_ResultsData)
//       ResultsData.distance_mm[64] / target_status[64]
//   - Adafruit_VL53L5 v1.0.1 (폴백):
//       Adafruit_VL53L5CX class, begin(addr=0x29, *wire=&Wire, i2c_clock=400000)
//       ※ Motion Indicator는 Adafruit 경유 아님 — SparkFun 번들 ULD 함수
//         (vl53l5cx_motion_indicator_init 등)를 imager.Dev public 핸들로 직접 호출.
//         decisions.md 카테고리 9 Stage B 판정 B(2026-07-09) 실측 확정.
//   - susesKaninchen/OnlyFeet (XIAO Sense + 8x8/15Hz 매칭 80%):
//       SparkFun lib 사용 / Wire.setClock(400000) (1MHz가 아님)
//       2회 retry init / 실패 시 I2C scan 진단 / hasTOF flag graceful
//       center 4 zones (27,28,35,36) 거리 메트릭 / target_status==5||9 valid
//   - arduino-esp32 Wire / ESP-IDF I2C (core 2.0.17, PIO 패키지 문자열 "3.20017"):
//       ※ 선두 "3."은 PlatformIO 버전 규약이며 core 메이저 3.x가 아님(실측 2.0.17).
//         core 3.x 전제로 API 선택 시 legacy driver 비호환 발생.
//       Wire.begin(SDA, SCL) ESP32-S3 GPIO 매핑 지원
//       Wire.setClock() 최대 1MHz 지원 (사전 검증 ① 워크어라운드)

#pragma once

#include <Arduino.h>
#include <Wire.h>
#include <SparkFun_VL53L5CX_Library.h>

// === VL53L5CX 핀 매핑 (decisions.md 카테고리 2 핀 표 그대로) ===
// ★ PWREN / LPn = 3V3 직결 (GPIO 상수 없음 — 소프트웨어 제어 대상 아님).
//   두 핀이 HIGH가 아니면 센서가 셧다운 상태로 SDA를 LOW 고착 → I2C START 성립 불가.
//   2026-08-06~07 이틀 블로커의 단일 근본원인. 재현 결선표 = decisions.md 카테고리 9.1(d).
constexpr int TOF_SDA_PIN = 5;          // XIAO D4, VL53L5CX SDA
constexpr int TOF_SCL_PIN = 6;          // XIAO D5, VL53L5CX SCL

// === I2C 설정 상수 ===
// VL53L5CX datasheet I2C max 1Mbits/s (규격 상한, 무효화 아님).
// ★ 2026-08-07 실측: 브레드보드 + 20cm 점퍼 환경에서 400kHz로 8x8/15Hz 프레임 정상 동작.
//   15Hz는 datasheet 8x8 mode 상한이므로 1MHz로 올려도 프레임레이트 이득 0 → 400kHz 정식 채택.
//   참조 구현 OnlyFeet(매칭 80%)도 400kHz 사용. 1MHz 실환경 검증은 실익 부재로 미수행.
constexpr uint32_t TOF_I2C_FREQ_HZ = 400000;
constexpr uint8_t  TOF_I2C_ADDR_7BIT = 0x29;    // datasheet default 7-bit (8-bit 0x52)

// === ToF 캡처 설정 ===
// 8x8 = 64 zones (datasheet RESOLUTION_8X8 macro 값과 일치).
// 15Hz = datasheet 8x8 mode max 주파수 (4x4는 60Hz).
constexpr uint8_t  TOF_GRID_SIZE      = 8;
constexpr uint16_t TOF_ZONE_COUNT     = 64;     // 8x8
constexpr uint8_t  TOF_RANGING_FREQ_HZ = 15;
constexpr uint32_t TOF_PERIOD_MS      = 1000 / TOF_RANGING_FREQ_HZ;  // ~67ms

// === init retry (OnlyFeet 패턴: 2회 시도 후 실패 graceful) ===
constexpr int TOF_INIT_RETRY_MAX = 2;

// === Stage A 사람 존재 판정 (decisions.md 카테고리 9 Stage A) ===
// SSoT 규정 = "1m 이내 ≥8 zone". 아래 두 값이 그 규정의 코드 표현.
//
// ★ 2026-08-08 ④런타임 실측 — 임계값 8의 타당성 근거 (사람 1명 접근, 8x8/15Hz/400kHz)
//   center 2953mm → near 0   | center 869mm → near 29
//   center 1240mm → near 0   | center 756mm → near 30
//   center 1196mm → near 0   | center 634mm → near 40
//   center 1011mm → near 10 ★| center 529mm → near 51
//   center  995mm → near 9   | center 431mm → near 56
//   center  972mm → near 13
//   무인 기준선 = near 0~2 (시야 내 물체 제거 상태)
//   ∴ 1m 지점 사람 = 9~13 / 무인 = 0~2 → 임계값 8이 양측에서 분리됨. 상향 시 1m 사람 미검출 위험.
//   ※ 세션 중 제기된 "8→20 상향" 안은 근거 수치(near 37~55)가 실제로는 center 410~562mm
//     (0.4~0.6m) 값이었음이 판명되어 폐기됨(학습 19).
constexpr uint16_t TOF_PRESENCE_DIST_MM = 1000;
constexpr uint8_t TOF_PRESENCE_MIN_ZONES = 8;

// target_status valid 판정 (VL53L5CX datasheet / OnlyFeet 패턴)
// 5 = range valid / 9 = range valid, large pulse. 그 외는 신뢰 불가로 폐기.
constexpr uint8_t TOF_STATUS_VALID = 5;
constexpr uint8_t TOF_STATUS_VALID_LARGE = 9;

// center 4 zones (8x8 그리드 중앙) — 침입자 거리 메트릭용. OnlyFeet 패턴.
constexpr uint16_t TOF_CENTER_ZONES[4] = {27, 28, 35, 36};

// === 디바운스 (2026-08-08 ④런타임 실측 기반 도입) ===
// PR #34 실측에서 임계 경계 플리커 확인 — 1~2프레임 단위로 near가 7↔8을 왕복하며
// presence가 반전됨(center 722→727mm, 5mm 변화로 전환). 원인 = 1m 부근에서
// near_count가 임계값(8) 언저리를 오르내리는 물리적 특성.
// N=3 근거: 15Hz이므로 3프레임 = 약 200ms. 실측 플리커는 전부 1~2프레임 폭이라
//   3프레임 연속 조건으로 소거되고, 200ms는 사람 인지 지연으로 무시 가능.
// 진입/이탈 대칭 적용 — 비대칭은 실측 근거가 없어 도입하지 않음.
constexpr uint8_t TOF_PRESENCE_DEBOUNCE_FRAMES = 3;

// === Stage B-1 계측 계층 (Motion Indicator 관측 전용, decisions.md 카테고리 9 Stage B 판정 B) ===
// ★ 본 계층은 motion 값을 "관측·로그로만" 노출한다. presence 판정(Stage A)에 융합하지 않는다.
//   ✅ [해소] 판정 임계값은 아래 "Stage B-2 판정 계층" 블록에서 확정(2026-09-02, 9.3(c) 실측표 근거).
//      B-1 자신은 여전히 관측 전용 — 아래 상수·로직은 B-1 계측을 소비할 뿐 B-1을 바꾸지 않는다.
//
// motion 감시 거리창(sensor 설정값, 판정 임계값 아님).
//   출처 = ST ULD vl53l5cx_plugin_motion_indicator.h:96,112-119 문서화 기본값(400~1500mm).
//   근거 = 기본값이 Stage A presence 거리(≤1000mm)를 마진 포함 전부 감싼다. 하드웨어 하한 400mm,
//          span(max-min) ≤ 1500mm 제약(motion_indicator.cpp:107-109)을 기본값이 이미 만족.
constexpr uint16_t TOF_MOTION_DIST_MIN_MM = 400;
constexpr uint16_t TOF_MOTION_DIST_MAX_MM = 1500;

// 8x8 활성 aggregate 개수. motion[]은 zone(64)당이 아니라 aggregate 단위.
//   출처 = map_id 매핑식 vl53l5cx_plugin_motion_indicator.cpp:150-155
//          8x8: map_id[i] = (i%8)/2 + 4*(i/16) → aggregate id 0..15 (각 2x2 super-zone), motion[16..31] 미사용.
constexpr uint8_t TOF_MOTION_AGG_COUNT_8X8 = 16;

// motion 관측 로그 주기(프레임). 판정 임계값 아님 — serial flood 방지용 cadence.
//   근거 = 15Hz에서 15프레임 ≈ 1초. Stage A 요약(2초, TOF_LOG_EVERY_N_FRAMES=30)보다 촘촘한 것은
//          B-1 목적이 곡선 측정이라 시간 해상도가 더 필요하기 때문.
constexpr uint32_t TOF_MOTION_LOG_EVERY_N_FRAMES = 15;

// ============================================================================
// === Stage B-2 판정 계층 (motion latch + presence 융합, 2026-09-02 PoC-(38)) ===
// ============================================================================
// B-1이 관측만 하던 motion을 "판정"으로 승격하고 Stage A presence와 융합한다.
// ★ Stage A 디바운스와 방향이 정반대다 — 혼동 금지:
//     Stage A 디바운스 = "연속 N프레임 충족해야 인정"  (노이즈 억제, 이벤트를 죽인다)
//     Stage B-2 latch  = "최근 N프레임 중 1회라도 검출되면 유지" (이벤트 보존, 이벤트를 살린다)
//   같은 "N프레임"이라는 표현을 쓰지만 부호가 반대다. 상수도 파라미터도 공유하지 않는다.
//
// ── (1) motion 판정 임계값 ─────────────────────────────────────────────────
// ★ 2026-08-12 ④런타임 실측표(decisions.md 9.3(c), 실내 책상 / 8x8 / 15Hz / I2C 400kHz)
//   후보는 9.3(d)-3 등재분 2종뿐이며, 아래 표로 (a)를 채택하고 (b)를 기각했다.
//
//   | 상황                          | near/64 | ndet/16 | aggmax | (a) ndet>=1 | (b) aggmax>=50 |
//   |-------------------------------|---------|---------|--------|-------------|----------------|
//   | ① 무자극 기준선 (25프레임)     |   0     |   0     | 12~24  |  false ✔    |  false ✔       |
//   |    └ 스파이크 1회             |   -     |   0     |   37   |  false ✔    |  false ✔       |
//   | ② 정지 사물 1m                | 10~11   |   0     | 14~22  |  false ✔    |  false ✔       |
//   | ③ 사람 1m 정지(체감)           |  9~42   |   0     | 18~42  |  false △    |  false △       |
//   | ④ 사람 접근 스윕 (1144→264mm) | 10~64   |  1~5    | 45~544 |  true  ✔    |  ★일부 false✘  |
//   | ⑤ 근접 자극 (249~253mm)       | 31~34   |   6     |  114   |  true  ✔    |  true  ✔       |
//
//   ✔=정탐 / ✘=미탐 / △=원리적 한계(9.3(d)-2, latch가 보정할 대상이지 임계값의 결함이 아님)
//
//   ▸ 오탐(정지 사물을 사람으로) : (a) 0건 — ①②가 전부 ndet=0. (b)도 0건.
//   ▸ 미탐(접근하는 사람을 놓침) : (a) 0건 — ④⑤가 전부 ndet>=1.
//                                 (b) ★발생 — ④의 aggmax 하한이 45라 45~49 구간 프레임이 임계 50 미달.
//   ▸ (b) 기각 사유 ①: 자기모순. 등재 근거가 "노이즈 상한 37 / 사람 하한 45 사이"인데
//        50은 45보다 크다. 사이가 아니라 바깥(위)이며, 그 결과가 위 ④ 미탐이다.
//   ▸ (b) 기각 사유 ②: 실측표가 실제로 허용하는 창은 (③상한 42) < 경계 <= (④하한 45) = 폭 3.
//        마진이 사실상 없다. 게다가 43·44 같은 값은 9.3(d)-3 미등재 = 신규 창작이라 채택 금지(§7-3).
//   ▸ (b) 기각 사유 ③: aggmax는 우리가 16개 aggregate에서 뽑은 파생 피크라 경계를 사람이 박아야 한다.
//        ndet는 device(ST 펌웨어)가 자체 공간 알고리즘으로 낸 판정이라 사람이 경계를 정할 여지가 없다.
//        9.2(d) "8→20 상향" 오판이 발생한 지점이 정확히 "사람이 경계를 박는" 자리였다.
//   ▸ 조합안 기각: AND(a&&b)는 ④에서 (b)의 미탐을 그대로 물려받아 (a)보다 열등.
//        OR(a||b)가 (a)보다 추가로 잡는 프레임 = "ndet=0 且 aggmax>=50"인데, 실측표 ①②③의
//        aggmax 최댓값이 42라 그런 행이 0건 → 이득 0. 상수만 늘고 판정은 동일하므로 기각.
//   ∴ 채택 = ndet >= 1 단독. 부수 이득: 매 프레임 motion[16] 순회가 불필요(피크 계산 0회).
constexpr uint8_t TOF_MOTION_NDET_MIN = 1;

// ── (2) latch 유지 길이 ────────────────────────────────────────────────────
// ★ 근거유형 = **논증** (실측 아님). 9.3(c) 실측표에는 시간축 데이터가 없다 —
//   ①~⑤ 어느 행도 "정지 지속 시간"을 기록하지 않으며, 9.3(d)-2의 "체감 30초"는
//   motion이 안 떴다는 사실의 서술이지 latch 길이의 근거가 아니다. 따라서 아래는 도출이지 측정이 아니다.
//
//   [도출]
//   - 프레임레이트 15Hz(8x8 mode 상한, 9.1) → 1프레임 = 66.7ms.
//   - latch가 덮어야 하는 구간 = "마지막 motion 검출" ~ "초인종을 누르는 시점"의 **정지 구간**이다.
//     접근 구간 자체가 아니다(접근 중에는 매 프레임 재충전되므로 길이가 무의미).
//   - 현관 앞 현실 시퀀스: 도착 → 멈춤 → 초인종 위치 확인 → 누름 ≈ 1~3초.
//     택배기사가 물건을 내려놓고 누르는 경우 ~5초까지 늘어난다. → 하한 요구 = 5초.
//   - 상한 위험은 작다: 융합이 (presence && latch)의 AND이므로 사람이 떠나면 Stage A presence가
//     3프레임(200ms) 뒤 NONE으로 떨어져 융합 결과도 즉시 false가 된다. latch 단독으로는 오탐이 안 난다.
//     남는 위험은 "사람이 지나간 직후 그 자리에 정지 사물이 있는" 좁은 경우뿐이라 유한하기만 하면 된다.
//   ∴ 5초 = 15Hz × 75프레임. 보수적(하한 요구를 정확히 충족, 상한은 유한)이라는 뜻으로 5초다.
//   - Stage A 디바운스 3프레임(200ms)의 25배 = 두 계층의 시간 스케일이 명확히 분리된다.
//
//   [재조정 판정 방법] — ④런타임 프로토콜 ③④(접근 후 정지 / latch 만료)에서:
//     · [StageB-2] fused 전이 로그의 frame# 차 ÷ 15 = latch 실지속 초.
//     · 학부생이 "문 앞 도착 → 초인종 누름"에 실제로 걸린 시간을 초시계로 병기 측정한다.
//     · 누름 시점 **이전에** fused가 NONE으로 만료되면 → 상향(미탐).
//     · 사람 퇴장 후에도 fused가 오래 남으면(정지 사물 잔존 오탐) → 하향.
//     · 두 수치가 확보되면 근거유형이 "논증" → "실측"으로 승격되며 본 주석을 갱신한다.
constexpr uint8_t TOF_MOTION_LATCH_FRAMES = 75;   // 15Hz × 5초
// ※ uint8_t 선택 근거 (타입 2안 footprint 실측 대조, 2026-09-02):
//    uint16_t안 = RAM 20,132B (변경 전 20,124B 대비 순증 +8B) / uint8_t안 = RAM 20,124B (순증 **0**).
//    Flash는 양안 373,013B로 동일. 즉 타입 축소가 순증을 실제로 0으로 만든다
//    (PR #36 motionConfig 전이 스택 배치 / PR #38 union과 같은 "순증 0" 선례).
//    대가 = 재조정 천장이 255프레임(17초)로 제한된다. 도출값 5초의 3.4배 헤드룸이며,
//    17초를 넘는 latch는 "사람이 지나간 뒤 상자만 남은" 오탐 창을 과도하게 넓힌다 — 상향보다
//    아래 defer (1)의 hold-while-present 규칙이 먼저 검토될 자리라 천장이 실질 제약이 아니다.

// === FreeRTOS 태스크 설정 (decisions.md 카테고리 14 5/21 PoC 분배 잠정안) ===
// micTask priority 4 (Core 0)와 분리: tofTask priority 3 (Core 0).
// Stack 6144 (OnlyFeet 참고치, ResultsData ~1356B + 64 zone 처리 여유).
constexpr uint32_t    TOF_TASK_STACK_SIZE = 6144;
constexpr UBaseType_t TOF_TASK_PRIORITY   = 3;
constexpr BaseType_t  TOF_TASK_CORE       = 0;
constexpr uint32_t    TOF_LOOP_IDLE_LOG_MS    = 5000;
constexpr uint32_t    TOF_SERIAL_BOOT_DELAY_MS = 200;
constexpr uint32_t    TOF_LOG_EVERY_N_FRAMES  = 30;     // 15Hz × 2초

// === API ===
bool initToF();
// Stage B-1: Motion Indicator 초기화(번들 ULD 함수 imager.Dev 직접 호출). best-effort —
//   실패해도 Stage A(presence)는 계속 동작해야 하므로 initToF()의 반환을 게이트하지 않는다.
bool initToFMotionIndicator();
void logToFMemoryDiagnostics(const char* tag);
