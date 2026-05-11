// 띵동 PoC firmware - ToF 더미 테스트 공통 헤더 (5/11, PoC Day 5)
//
// VL53L5CX-SATEL + ESP32-S3 I2C0. 카메라 (I2S0) / 마이크 (I2S1)와 페리페럴 분리.
// 부품 부재 상태 (자성리얼 5/15~5/28 도착) → 컴파일 + 메모리 진단까지만 검증.
// 8x8 multi-zone (64 zones) × 15Hz (datasheet limit) 캡처 코드 골격.
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
//       동일 API + Motion Indicator (initMotionIndicator/setMotionDistance) 추가
//   - susesKaninchen/OnlyFeet (XIAO Sense + 8x8/15Hz 매칭 80%):
//       SparkFun lib 사용 / Wire.setClock(400000) (1MHz가 아님)
//       2회 retry init / 실패 시 I2C scan 진단 / hasTOF flag graceful
//       center 4 zones (27,28,35,36) 거리 메트릭 / target_status==5||9 valid
//   - arduino-esp32 Wire / ESP-IDF I2C (core 3.x v3.20017):
//       Wire.begin(SDA, SCL) ESP32-S3 GPIO 매핑 지원
//       Wire.setClock() 최대 1MHz 지원 (사전 검증 ① 워크어라운드)

#pragma once

#include <Arduino.h>
#include <Wire.h>
#include <SparkFun_VL53L5CX_Library.h>

// === VL53L5CX 핀 매핑 (decisions.md 카테고리 2 핀 표 그대로) ===
constexpr int TOF_SDA_PIN = 5;          // XIAO D4, VL53L5CX SDA
constexpr int TOF_SCL_PIN = 6;          // XIAO D5, VL53L5CX SCL

// === I2C 설정 상수 ===
// VL53L5CX datasheet I2C max 1Mbits/s. 사전 검증 ① 워크어라운드: 1MHz 권장.
// SparkFun Example3_SetFrequency.ino도 8x8/15Hz 시 1MHz 사용 (Wire.setClock(1000000)).
// (참고: OnlyFeet은 400kHz 사용했으나 본 프로젝트는 1MHz 채택.)
constexpr uint32_t TOF_I2C_FREQ_HZ = 1000000;
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
