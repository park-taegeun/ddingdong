// 띵동 PoC firmware - ToF 더미 테스트 (5/11, PoC Day 5)
//
// tofTask 단독: isDataReady 폴링 + (placeholder) 64 zone 거리 추출.
// 본 작업은 컴파일 통과 + 메모리 진단까지만 — 실제 캡처 검증은 부품 도착 후 별도 작업.
// 5/21 PoC 통합 시 cameraTask(Core 1) + micTask(Core 0, prio 4) + tofTask(Core 0, prio 3)
// 병행 검증 (decisions.md 카테고리 14).

#include "tof_common.h"

extern SparkFun_VL53L5CX tofImager;

static void tofTask(void* parameter) {
  (void)parameter;
  logToFMemoryDiagnostics("tofTask-entry");

  // ResultsData ~1356B (SparkFun 주석 인용). task 스택(6KiB) 폭주 방지로 static (BSS).
  static VL53L5CX_ResultsData measurementData;
  uint32_t frame_count = 0;
  uint32_t err_count   = 0;

  for (;;) {
    if (tofImager.isDataReady()) {
      if (tofImager.getRangingData(&measurementData)) {
        if ((++frame_count % TOF_LOG_EVERY_N_FRAMES) == 1) {
          // 부품 도착 전이라 실측 없음 — 메타 로그만.
          Serial.printf("[tof] frame #%u (8x8, 64 zones)\n", (unsigned)frame_count);
        }
        // ── 부품 도착 후 (자성리얼 5/15~5/28) 실측 단계에서 추가 작업 ──
        // (1) 64 zone 순회 — measurementData.distance_mm[i] (int16_t mm)
        //     for (int i = 0; i < TOF_ZONE_COUNT; i++) { int16_t mm = measurementData.distance_mm[i]; }
        // (2) target_status[i] == 5 || 9 zone만 valid (datasheet)
        // (3) center 4 zones (27/28/35/36) 평균 → 침입자 거리 메트릭 (OnlyFeet 패턴)
        // (4) Motion Indicator (Adafruit lib 추가 API) — 5주차 사람 검증 단계
      } else {
        if ((++err_count % 10) == 1) {
          Serial.printf("[tof] getRangingData failed #%u\n", (unsigned)err_count);
        }
      }
    }
    // 67ms (15Hz). datasheet 권장 폴링 간격. OnlyFeet은 5ms 폴링이지만 본 작업은 정확한 주기.
    vTaskDelay(pdMS_TO_TICKS(TOF_PERIOD_MS));
  }
}

void setup() {
  Serial.begin(115200);
  delay(TOF_SERIAL_BOOT_DELAY_MS);
  Serial.println("\n[BOOT] ddingdong tof test (VL53L5CX 8x8, 15Hz, I2C 1MHz)");

  if (!initToF()) {
    Serial.println("[BOOT] tof init failed — task spawn 생략, loop()에서 idle 진단만 출력");
    return;  // graceful: 무한 루프 X. loop()에서 주기적 메모리 로그.
  }

  xTaskCreatePinnedToCore(tofTask, "tofTask",
                          TOF_TASK_STACK_SIZE, nullptr,
                          TOF_TASK_PRIORITY, nullptr,
                          TOF_TASK_CORE);
  Serial.println("[BOOT] tofTask started on Core 0 priority 3");
}

void loop() {
  // 정상 부팅 시 task가 모든 작업 수행 → loop는 idle.
  // init 실패 시 (부품 부재) 메모리 진단만 주기 출력.
  static uint32_t last_log = 0;
  const uint32_t now = millis();
  if ((now - last_log) >= TOF_LOOP_IDLE_LOG_MS) {
    last_log = now;
    logToFMemoryDiagnostics("loop-idle");
  }
  delay(100);
}
