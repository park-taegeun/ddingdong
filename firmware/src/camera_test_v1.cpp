// 띵동 PoC firmware - 카메라 더미 테스트 Version A (5/9, PoC-(6) Day 3)
//
// cameraTask 단독: fb_get → 처리 placeholder → fb_return → vTaskDelay
// 단순 구조. fb_get blocking 시 task 전체 stall.
// 부품 도착 후 (자성리얼 5/15~5/28) Version B와 fb_get 안정성 비교 예정 (카테고리 17.1.2).
//
// 본 작업은 컴파일 통과 + 메모리 진단까지만 — 실제 캡처 검증은 부품 도착 후 별도 작업.

#include "camera_common.h"

static void cameraTask(void* parameter) {
  (void)parameter;
  logMemoryDiagnostics("cameraTask-entry");
  uint32_t frame_count = 0;
  uint32_t null_count  = 0;
  for (;;) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (fb == nullptr) {
      if ((++null_count % LOG_EVERY_N_NULLS) == 1) {
        Serial.printf("[CAMERA-V1] fb_get NULL #%u\n", (unsigned)null_count);
        logMemoryDiagnostics("fb_null");
      }
      vTaskDelay(pdMS_TO_TICKS(CAMERA_FRAME_INTERVAL_MS));
      continue;
    }
    if ((++frame_count % LOG_EVERY_N_FRAMES) == 1) {
      Serial.printf("[CAMERA-V1] frame #%u %ux%u %u bytes\n",
                    (unsigned)frame_count,
                    (unsigned)fb->width, (unsigned)fb->height,
                    (unsigned)fb->len);
    }
    esp_camera_fb_return(fb);                                 // 반드시 반환 (메모리 누수 방지)
    vTaskDelay(pdMS_TO_TICKS(CAMERA_FRAME_INTERVAL_MS));     // Khangura 함정 #4
  }
}

void setup() {
  Serial.begin(115200);
  delay(SERIAL_BOOT_DELAY_MS);
  Serial.println("\n[BOOT] ddingdong camera test v1 (cameraTask 단독)");

  if (!initCameraWithDiagnostics()) {
    Serial.println("[BOOT] camera init failed — task spawn 생략, loop()에서 idle 진단만 출력");
    return;  // graceful: 무한 루프 X. loop()에서 주기적 메모리 로그.
  }
  xTaskCreatePinnedToCore(cameraTask, "cameraTask",
                          CAMERA_TASK_STACK_SIZE, nullptr,
                          CAMERA_TASK_PRIORITY, nullptr,
                          CAMERA_TASK_CORE);
  Serial.println("[BOOT] cameraTask started on Core 1 priority 4");
}

void loop() {
  // 정상 부팅 시 task가 모든 작업 수행 → loop는 idle.
  // init 실패 시 (부품 부재) 메모리 진단만 주기 출력.
  static uint32_t last_log = 0;
  const uint32_t now = millis();
  if ((now - last_log) >= CAMERA_LOOP_IDLE_LOG_MS) {
    last_log = now;
    logMemoryDiagnostics("loop-idle");
  }
  delay(100);
}
