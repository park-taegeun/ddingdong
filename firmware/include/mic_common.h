// 띵동 PoC firmware - 마이크 더미 테스트 공통 헤더 (5/10, PoC Day 4)
//
// INMP441 + ESP32-S3 I2S1. 카메라 (I2S0)와 페리페럴 분리 (decisions.md 카테고리 1).
// 부품 부재 상태 (자성리얼 5/15~5/28 도착) → 컴파일 + 메모리 진단까지만 검증.
// 16kHz mono raw waveform 캡처 코드 골격 + 250ms 파워업 노이즈 폐기.
//
// 출처:
//   - INMP441 datasheet (Mouser PDF rev 1.1 2014-05-21, TDK InvenSense):
//       VDD 1.62~3.63V (권장 1.8~3.3V) / SNR 61dBA / SCK 0.5~3.2MHz / WS 7.8~50kHz
//       startup 2^18 SCK cycles → 16kHz × 64 = 1.024MHz BCLK 시 256ms ≈ 250ms 일치
//       L/R=GND → 좌채널 / 64 SCK per stereo frame 강제 (mono도 stereo frame 사용)
//       Philips I²S 포맷 (MSB delayed 1 SCK from start of half-frame)
//   - Espressif ESP-IDF 5.5 docs (context7 /websites/espressif_projects_esp-idf):
//       legacy driver/i2s.h는 deprecated, 새 driver/i2s_std.h 권장
//       BUT — arduino-esp32 v3.20017 SDK 패키지는 legacy driver/i2s.h만 노출
//       (find ~/.platformio/packages/.../include/driver/ → i2s.h만, i2s_std.h 부재)
//       → 본 작업은 legacy API 채택 (deprecation warning 무시 가능, 동작 확인됨)

#pragma once

#include <Arduino.h>
#include "driver/i2s.h"

// === INMP441 핀 매핑 (decisions.md 카테고리 2 핀 표 그대로) ===
constexpr int        MIC_SCK_PIN  = 2;          // XIAO D1, INMP441 SCK (BCLK)
constexpr int        MIC_WS_PIN   = 3;          // XIAO D2, INMP441 WS  (LRCL)
constexpr int        MIC_SD_PIN   = 7;          // XIAO D8, INMP441 SD  (DOUT → ESP32 입력)
constexpr i2s_port_t MIC_I2S_PORT = I2S_NUM_1;  // 카메라 I2S0과 분리

// === I2S 설정 상수 ===
// 16kHz × 64 SCK = 1.024 MHz BCLK (INMP441 spec 0.5~3.2 MHz 범위 내)
// 32-bit slot에 24-bit MSB align (INMP441 24-bit 데이터, Philips I²S)
// channel_format = ONLY_LEFT: L/R=GND이므로 좌 슬롯 데이터만 추출
constexpr uint32_t MIC_SAMPLE_RATE_HZ  = 16000;
constexpr int      MIC_DMA_BUF_COUNT   = 8;     // 8 DMA descriptors
constexpr int      MIC_DMA_BUF_LEN     = 1024;  // frames per buffer (1 frame = 4 bytes @ 32-bit mono)

// === 250ms 파워업 노이즈 처리 (userMemories 상수, datasheet 2^18 cycles 근거) ===
constexpr uint32_t MIC_WARMUP_DELAY_MS        = 250;
constexpr int      MIC_WARMUP_BUFFERS_DISCARD = 14;  // 보수적 14 (12~14 범위)

// === FreeRTOS 태스크 설정 (decisions.md 카테고리 14 5/21 PoC 분배 잠정안) ===
constexpr uint32_t      MIC_TASK_STACK_SIZE  = 4096;
constexpr UBaseType_t   MIC_TASK_PRIORITY    = 4;
constexpr BaseType_t    MIC_TASK_CORE        = 0;     // Core 0 (cameraTask는 Core 1)
constexpr uint32_t      MIC_LOOP_IDLE_LOG_MS = 5000;
constexpr uint32_t      MIC_SERIAL_BOOT_DELAY_MS = 200;
constexpr uint32_t      MIC_LOG_EVERY_N_BUFFERS  = 50;

// === API ===
bool initMicI2S();
void discardMicWarmup();
void logMicMemoryDiagnostics(const char* tag);
