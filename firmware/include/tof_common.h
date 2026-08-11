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
void logToFMemoryDiagnostics(const char* tag);
