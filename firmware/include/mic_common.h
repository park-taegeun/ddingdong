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
//       BUT — 설치된 arduino-esp32 packaging은 legacy driver/i2s.h만 노출
//       (find ~/.platformio/packages/.../include/driver/ → i2s.h만, i2s_std.h 부재)
//       → 본 작업은 legacy API 채택 (deprecation warning 무시 가능, 동작 확인됨)
//       ※ 정정(decisions.md SSoT): "v3.20017"은 PIO 패키지 버전 문자열
//         (framework-arduinoespressif32@3.20017.241212)이며 core 3.x 아님.
//         설치 core = Arduino-ESP32 2.0.17 (legacy driver/i2s.h 의존이 그 방증).
//         레거시 헤더 채택 로직 자체는 정당 → 무변경 (학습 15 ②단계 모범 수행분,
//         PR #34 tof_common.h 동형 오독 정정 선례 준용).

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
constexpr uint32_t      MIC_LOG_EVERY_N_BUFFERS  = 50;   // 계측 윈도우 크기 (재사용, 신설 X)

// === M2 계측 계층 (관측 전용, 판정·변환 무접촉 — decisions.md §9.3 ToF Stage B-1 패턴 준용) ===
// raw int32 통계를 로깅해 실제 비트 정렬을 드러낸다. shift/트리거/변환은 M4 소관.
// K 윈도우마다 1회 raw 샘플 8개를 hex 덤프 (MSB 정렬 육안 확인용).
constexpr uint32_t      MIC_RAW_DUMP_EVERY_N_WINDOWS = 5;

// raw int32 한 버퍼의 진폭 통계. 호출부 지역변수로 사용 (static/전역 신설 금지 = RAM 순증 0).
struct MicRawStats {
  int32_t  n;       // 샘플 수         ∈ [0, MIC_DMA_BUF_LEN]
  int32_t  min;     // 최소 진폭       ∈ [INT32_MIN, INT32_MAX]
  int32_t  max;     // 최대 진폭       ∈ [INT32_MIN, INT32_MAX]
  int64_t  mean;    // DC 오프셋       ∈ [INT32_MIN, INT32_MAX]
  int64_t  pp;      // peak-to-peak    ∈ [0, 2^32-1]  (int32 초과 → int64 필수)
  int64_t  rms;     // int32 도메인 RMS ∈ [0, 2^31]
  uint32_t or_acc;  // 전 샘플 비트 OR 누적
  int      tz;      // or_acc trailing zeros ∈ [0, 32] (하위 항상-0 비트 폭 = 실제 정렬 폭 물증)
  int32_t  nz;      // 0이 아닌 샘플 수 ∈ [0, n]
};

// === M4 변환 계층 (int32 raw → int16 PCM, 2026-08-20 ④런타임 실측으로 확정) ===
//
// ★ 측정 조건: 2026-08-20 / env:mic_dummy / HEAD 17ce212 / 랩실(사람 대화 있음)
//   39윈도우(w=233~271) — w=233~248 무자극 / w=249~266 근접 박수 / w=267~271 말하기
//   = M2 defer 주석이 요구한 실측 프로토콜 ①무자극 ②근접 박수 ③육성 전부 충족.
//
// ★ 정렬 폭 물증 — 전 39윈도우 불변 (진폭이 60배 변동해도 무변화)
//     or_acc = 0xFFFFFFC0 | tz = 6 | err = 0 | nz = 1024 (w=257만 1023)
//
//   도출식:  raw_int32    = sample_24bit << 6      ← tz=6 = 하위 6비트 항상 0
//            sample_24bit = raw >> 6
//            int16        = sample_24bit >> 8
//            ───────────────────────────────────
//            int16        = raw >> 14              ← MIC_RAW_TO_INT16_SHIFT
//
//   검산:      8388607 (24bit 최대) << 6 = 536870848 → >> 14 = 32767 = INT16_MAX 정확 일치
//   실측 대입: 박수 max 296542208 >> 14 = 18099 = int16 풀스케일의 55%
//              → 클리핑 없음, 헤드룸 약 1.8배. 단 더 큰 소리는 미측정 → saturation 가드 필수.
//
// ★ 폐기된 안: >>16 (M2 이전의 ">>8 두 번" 주석 계획). tz=6 실측과 불일치하며 유효
//   비트를 2비트 더 버려 약 12dB(4배) 손실. 치명적이진 않으나 정확도 저하.
//   계측 PR(#37)로 쪼개 tz를 먼저 잰 덕에 착수 전 발견 → 폐기.
//
// ⚠️ 배경 rms 2,104,135 ~ 2,646,435 은 **랩실 소음 포함 = 무음 기준선이 아니다.**
//   RMS 트리거 임계값 근거로 사용 금지 (카테고리 3 "80% 지점"은 M5에서 조용한 환경
//   재측정 후 확정). 본 표는 정렬 폭(shift) 근거로만 유효하다.
constexpr int MIC_RAW_TO_INT16_SHIFT = 14;

// int16 변환 결과 통계. 호출부 지역변수로 사용 (static/전역 신설 금지 = RAM 순증 0).
struct MicI16Stats {
  int32_t  n;     // 변환 샘플 수      ∈ [0, MIC_DMA_BUF_LEN]
  int16_t  min;   // 최소 진폭         ∈ [INT16_MIN, INT16_MAX]
  int16_t  max;   // 최대 진폭         ∈ [INT16_MIN, INT16_MAX]
  int32_t  rms;   // int16 도메인 RMS  ∈ [0, 32768]
  uint32_t clip;  // saturation clamp 발생 샘플 수 ∈ [0, n] (④런타임 클리핑 관측 수단)
};

// === API ===
bool initMicI2S();
void discardMicWarmup();
void logMicMemoryDiagnostics(const char* tag);
MicRawStats computeMicRawStats(const int32_t* samples, size_t count);

// int32 raw 버퍼 → int16 PCM 버퍼 변환(산술 시프트 + saturation) + 통계를 1-pass로 산출.
// dst는 호출부가 제공한다 — M4는 DMA 버퍼의 int16 union 뷰, M5는 2초 PSRAM 버퍼.
// 내부 저장소를 신설하지 않는다 (RAM 순증 0). src/dst 겹침 허용 조건은 .cpp 주석 참조.
MicI16Stats convertMicRawToInt16(const int32_t* src, int16_t* dst, size_t count);
