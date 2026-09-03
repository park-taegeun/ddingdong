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

// === M5-a 링버퍼 계층 (관측 전용 — 적재·상태 로그만. 트리거·임계값·판정 0줄) ===
//
// decisions.md 카테고리 20 "계측 → 실측 → 판정" 분리 원칙의 4회차 적용.
// M5-a = 본 계층(적재·관측) / M5-b = ④런타임 실측 / M5-c = 판정(임계값·스냅샷 추출).
//
// ★ 슬롯 산술 (근거유형 = 논증)
//   슬롯 1개 = i2s_read 한 버퍼 = MIC_DMA_BUF_LEN(1024) 샘플
//            = 1024 / MIC_SAMPLE_RATE_HZ(16000) = 64ms = 2,048 bytes(int16)
//   32 슬롯  = 2.048초 = 32,768 샘플 = 65,536 bytes
//
// ★ 왜 31.25가 아니라 32인가
//   2.000초 = 16000 × 2 = 32,000 샘플 = 31.25 슬롯 — 버퍼 정수배가 아니다.
//   0.25슬롯(256 샘플)을 맞추려면 슬롯 경계를 쪼개는 부분 버퍼 적재 로직이 필요하고,
//   그 로직이 wrap-around 산술과 곱해지면 경계 버그 표면이 커진다. 2.048초는 2초
//   하한을 만족하는 상위 근사(+2.4%)라 부분 버퍼 처리를 통째로 회피할 수 있다.
//
// ★ 서버 수용 근거 (근거유형 = 문서인용·미실측)
//   - 서빙 시그니처 waveform (1, None) f32 = 가변 길이 수용 (decisions.md 6.2)
//   - AUDIO_MAX_BYTES = 320,000 (server/app/constants.py:29 실측 grep)
//     65,536 bytes = 상한의 20.5% → 크기 초과(413) 불가, 여유 충분
//   - transport 계약 A안 = multipart/form-data + int16 PCM raw bytes (decisions.md 6.2)
//
// ★ 근거유형 = 논증 (④런타임 미검증). PSRAM 할당 성공 여부·실 가용 용량은 M5-b 실측 소관.
//
// ★ 재조정 방법
//   G29는 B안(하이브리드 = pre-roll 일부 + post 일부)으로 확정됐으나 pre/post 비율은
//   미확정이다(M5-b 실측 → M5-c에서 어택 길이·트리거 지연 측정 후 산출). 링버퍼는
//   "최근 N슬롯을 항상 보유하는" 구조라 비율과 무관하게 성립하므로, 비율이 확정되면
//   필요 슬롯 수를 재산출해 본 상수만 갱신한다.
//   ⚠️ 본 계층은 pre/post 비율 상수를 신설하지 않는다 — 실측 전에 박으면 죽은 상수가
//      되고, 되돌릴 때 적재 코드까지 흔들려 원인 분리가 불가해진다(카테고리 20 근거).
constexpr uint32_t MIC_RING_SLOTS = 32;

// 링버퍼 적재 상태(관측 전용).
// ★ 저장 위치 판단: MicRawStats / MicI16Stats와 동일하게 **호출부 지역변수** 원칙을 따른다.
//   링버퍼 상태는 태스크 수명 내내 유지돼야 하지만, 유일한 호출부 micTask()는 반환하지
//   않는 무한 루프라 그 지역변수의 수명 = 태스크 수명이다. buf_count / err_count /
//   window_idx가 이미 같은 방식으로 살아 있다 → static/전역을 신설할 이유가 없고,
//   신설하면 .bss 순증이 발생한다(PR #36/#38/#39가 3회 연속 지킨 RAM 순증 0 위반).
//   링버퍼 본체 포인터도 같은 이유로 전역이 아니라 initMicRingBuffer() 반환값으로 넘긴다.
struct MicRingStatus {
  uint32_t write_idx;     // 다음 적재 슬롯       ∈ [0, MIC_RING_SLOTS)  = [0, 31]
  uint32_t wraps;         // wrap-around 횟수     ∈ [0, UINT32_MAX] (2.048초당 +1)
  uint32_t gaps;          // i2s_read 실패로 적재를 건너뛴 횟수 ∈ [0, UINT32_MAX]
  uint32_t slots_filled;  // 부팅 후 채워진 슬롯 수 ∈ [0, MIC_RING_SLOTS] (포화 후 고정)
};

// 2초(=MIC_RING_SLOTS 슬롯) int16 링버퍼를 PSRAM에 할당한다.
// 반환 = 링버퍼 선두 포인터 / 실패 시 nullptr(호출부는 링버퍼 없이 계속 진행 = graceful).
// ※ 위임 원안은 `bool initMicRingBuffer()` + 내부 전역 보관이었으나, 본 파일이 세 곳에서
//   명문화한 "static/전역 신설 금지 = RAM 순증 0" 컨벤션과 충돌해 포인터 반환으로 채택
//   (decisions.md 카테고리 29 = 위임과 실제 컨벤션 충돌 시 기존 컨벤션 우선).
int16_t* initMicRingBuffer();

// idx번째 슬롯의 선두 포인터.
// - base == nullptr(할당 실패)이면 nullptr을 그대로 전파한다 → 호출부 널 가드 1곳으로 수렴.
// - idx는 모듈러로 접으므로 어떤 입력이 와도 [0, MIC_RING_SLOTS) 밖 슬롯을 가리키지 않는다
//   (micRingAdvance가 이미 범위를 지키므로 이중 방어).
inline int16_t* micRingSlot(int16_t* base, uint32_t idx) {
  return (base == nullptr)
             ? nullptr
             : base + (size_t)(idx % MIC_RING_SLOTS) * MIC_DMA_BUF_LEN;
}

// 슬롯 1칸 전진 + wrap-around. **적재에 성공한 뒤에만** 호출한다.
void micRingAdvance(MicRingStatus* st);
