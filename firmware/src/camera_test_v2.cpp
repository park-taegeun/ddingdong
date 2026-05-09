// 띵동 PoC firmware - 카메라 더미 테스트 Version B (5/9, PoC-(6) Day 3)
//
// writerTask 분리: cameraTask는 fb_get만, writerTask가 처리 + fb_return.
// queue 통신으로 fb_get blocking을 처리 시간과 격리.
// 5/21 PoC 통합 시 Core 1 cameraTask + Core 0 wifiTask 분리 예비 (카테고리 15).
// 부품 도착 후 (자성리얼 5/15~5/28) Version A와 fb_get 안정성 비교 예정 (카테고리 17.1.2).

#include "camera_common.h"

static QueueHandle_t g_fb_queue = nullptr;

static void cameraTask(void* parameter) {
  (void)parameter;
  logMemoryDiagnostics("cameraTask-entry");
  uint32_t null_count = 0;
  uint32_t drop_count = 0;
  for (;;) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (fb == nullptr) {
      if ((++null_count % LOG_EVERY_N_NULLS) == 1) {
        Serial.printf("[CAMERA-V2] fb_get NULL #%u\n", (unsigned)null_count);
      }
      vTaskDelay(pdMS_TO_TICKS(CAMERA_FRAME_INTERVAL_MS));
      continue;
    }
    // queue full 시 즉시 fb_return → 처리량 자연 제한 + 메모리 누수 방지.
    if (xQueueSend(g_fb_queue, &fb, 0) != pdTRUE) {
      esp_camera_fb_return(fb);
      if ((++drop_count % LOG_EVERY_N_NULLS) == 1) {
        Serial.printf("[CAMERA-V2] queue full → drop #%u\n", (unsigned)drop_count);
      }
    }
    vTaskDelay(pdMS_TO_TICKS(CAMERA_FRAME_INTERVAL_MS));
  }
}

static void writerTask(void* parameter) {
  (void)parameter;
  Serial.println("[WRITER-V2] writerTask running");
  uint32_t frame_count = 0;
  for (;;) {
    camera_fb_t* fb = nullptr;
    if (xQueueReceive(g_fb_queue, &fb, portMAX_DELAY) != pdTRUE || fb == nullptr) {
      continue;
    }
    if ((++frame_count % LOG_EVERY_N_FRAMES) == 1) {
      Serial.printf("[WRITER-V2] frame #%u %ux%u %u bytes\n",
                    (unsigned)frame_count,
                    (unsigned)fb->width, (unsigned)fb->height,
                    (unsigned)fb->len);
    }
    esp_camera_fb_return(fb);  // 반드시 반환 (메모리 누수 방지)
  }
}

void setup() {
  Serial.begin(115200);
  delay(SERIAL_BOOT_DELAY_MS);
  Serial.println("\n[BOOT] ddingdong camera test v2 (writerTask 분리)");

  if (!initCameraWithDiagnostics()) {
    Serial.println("[BOOT] camera init failed — task spawn 생략, loop()에서 idle 진단만 출력");
    return;
  }

  g_fb_queue = xQueueCreate(FB_QUEUE_LENGTH, sizeof(camera_fb_t*));
  if (g_fb_queue == nullptr) {
    Serial.println("[BOOT] FATAL: queue 생성 실패 — task spawn 중단");
    return;
  }

  xTaskCreatePinnedToCore(cameraTask, "cameraTask",
                          CAMERA_TASK_STACK_SIZE, nullptr,
                          CAMERA_TASK_PRIORITY, nullptr,
                          CAMERA_TASK_CORE);
  xTaskCreatePinnedToCore(writerTask, "writerTask",
                          CAMERA_TASK_STACK_SIZE, nullptr,
                          WRITER_TASK_PRIORITY, nullptr,
                          CAMERA_TASK_CORE);
  Serial.println("[BOOT] cameraTask(P4) + writerTask(P3) started on Core 1");
}

void loop() {
  static uint32_t last_log = 0;
  const uint32_t now = millis();
  if ((now - last_log) >= CAMERA_LOOP_IDLE_LOG_MS) {
    last_log = now;
    logMemoryDiagnostics("loop-idle");
  }
  delay(100);
}
