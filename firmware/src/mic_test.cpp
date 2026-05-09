// 띵동 PoC firmware - 마이크 더미 테스트 (5/10, PoC Day 4)
//
// micTask 단독: i2s_read 폴링 + (placeholder) 32→16bit downcast + RMS 계산.
// 본 작업은 컴파일 통과 + 메모리 진단까지만 — 실제 캡처 검증은 부품 도착 후 별도 작업.
// 5/21 PoC 통합 시 cameraTask(Core 1) + micTask(Core 0) 병행 검증 (decisions.md 카테고리 14).

#include "mic_common.h"

static void micTask(void* parameter) {
  (void)parameter;
  logMicMemoryDiagnostics("micTask-entry");

  // 32-bit mono × DMA_BUF_LEN 프레임 = 4 KiB. task 스택(4KiB) 폭주 방지로 static (BSS).
  static int32_t audio_buffer[MIC_DMA_BUF_LEN];
  size_t   bytes_read = 0;
  uint32_t buf_count  = 0;
  uint32_t err_count  = 0;

  for (;;) {
    const esp_err_t err = i2s_read(MIC_I2S_PORT, audio_buffer, sizeof(audio_buffer),
                                   &bytes_read, portMAX_DELAY);
    if (err != ESP_OK) {
      if ((++err_count % 10) == 1) {
        Serial.printf("[mic] read failed: 0x%x (%s) #%u\n",
                      err, esp_err_to_name(err), (unsigned)err_count);
      }
      continue;
    }
    if ((++buf_count % MIC_LOG_EVERY_N_BUFFERS) == 1) {
      Serial.printf("[mic] DMA buffer #%u %u bytes\n",
                    (unsigned)buf_count, (unsigned)bytes_read);
    }
    // ── 부품 도착 후 (자성리얼 5/15~5/28) 실측 단계에서 추가 작업 ──
    // (1) 32-bit MSB-align → 24-bit 유효 데이터 추출 (sign-extension 유지: arithmetic shift right by 8)
    //     int32_t s24 = audio_buffer[i] >> 8;  // arithmetic shift, sign 유지
    // (2) 24-bit → 16-bit downcast (>>8) — YAMNet 입력용 16kHz mono raw waveform
    // (3) RMS 계산 / 임계값 트리거 → wakeWord 검증
  }
}

void setup() {
  Serial.begin(115200);
  delay(MIC_SERIAL_BOOT_DELAY_MS);
  Serial.println("\n[BOOT] ddingdong mic test (INMP441 + I2S1, 16kHz mono)");

  if (!initMicI2S()) {
    Serial.println("[BOOT] mic init failed — task spawn 생략, loop()에서 idle 진단만 출력");
    return;  // graceful: 무한 루프 X. loop()에서 주기적 메모리 로그.
  }
  discardMicWarmup();

  xTaskCreatePinnedToCore(micTask, "micTask",
                          MIC_TASK_STACK_SIZE, nullptr,
                          MIC_TASK_PRIORITY, nullptr,
                          MIC_TASK_CORE);
  Serial.println("[BOOT] micTask started on Core 0 priority 4");
}

void loop() {
  // 정상 부팅 시 task가 모든 작업 수행 → loop는 idle.
  // init 실패 시 (부품 부재) 메모리 진단만 주기 출력.
  static uint32_t last_log = 0;
  const uint32_t now = millis();
  if ((now - last_log) >= MIC_LOOP_IDLE_LOG_MS) {
    last_log = now;
    logMicMemoryDiagnostics("loop-idle");
  }
  delay(100);
}
