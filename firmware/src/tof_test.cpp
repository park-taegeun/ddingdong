// 띵동 PoC firmware - ToF 더미 테스트 (5/11, PoC Day 5)
//
// tofTask 단독: isDataReady 폴링 + 64 zone 거리 추출 + Stage A 사람 존재 판정.
// 2026-08-07 브레드보드 브링업 성공(카테고리 9.1)으로 실측 단계 진입.
// Stage B(Motion Indicator)는 본 파일 범위 밖 — 별도 태스크.
// 5/21 PoC 통합 시 cameraTask(Core 1) + micTask(Core 0, prio 4) + tofTask(Core 0, prio 3)
// 병행 검증 (decisions.md 카테고리 14).

#include "tof_common.h"

extern SparkFun_VL53L5CX tofImager;

// target_status가 valid(5 또는 9)인지 판정 — Stage A near-count/center 공통 술어.
// VL53L5CX datasheet: 5 = range valid, 9 = range valid(large pulse). 그 외는 폐기.
static inline bool tofStatusValid(uint8_t status) {
  return status == TOF_STATUS_VALID || status == TOF_STATUS_VALID_LARGE;
}

static void tofTask(void* parameter) {
  (void)parameter;
  logToFMemoryDiagnostics("tofTask-entry");

  // ResultsData ~1356B (SparkFun 주석 인용). task 스택(6KiB) 폭주 방지로 static (BSS).
  static VL53L5CX_ResultsData measurementData;
  uint32_t frame_count = 0;
  uint32_t err_count   = 0;

  // presence 상태는 tofTask 내 static (BSS) — 전역 변수 신설 없이 상태 전환 검출.
  static bool presence_prev = false;

  for (;;) {
    if (tofImager.isDataReady()) {
      if (tofImager.getRangingData(&measurementData)) {
        frame_count++;

        // ── Stage A 사람 존재 판정 (decisions.md 카테고리 9 Stage A: "1m 이내 ≥8 zone") ──
        // 64 zone을 프레임당 단일 패스로 순회. NB_TARGET_PER_ZONE=1이라 zone i = 배열 인덱스 i.
        uint8_t  near_count   = 0;   // 최대 64 → uint8_t(255)로 오버플로 불가
        uint32_t center_sum   = 0;   // 최대 4 × ~4000mm = 16000 → uint32_t 여유
        uint8_t  center_valid = 0;

        for (uint16_t i = 0; i < TOF_ZONE_COUNT; i++) {
          if (!tofStatusValid(measurementData.target_status[i])) continue;
          const int16_t mm = measurementData.distance_mm[i];  // 라이브러리가 음수 0 클램프 완료
          // 1m(1000mm) 이내 且 0 초과만 근접 zone으로 채택.
          if (mm > 0 && mm <= TOF_PRESENCE_DIST_MM) {
            near_count++;
          }
        }
        // valid zone 0개 프레임(센서 시야 전체 무효)이어도 near_count=0 → presence=false로 정상 처리.
        const bool presence = (near_count >= TOF_PRESENCE_MIN_ZONES);

        // center 4 zones: valid(status 5/9) 且 거리 유효(>0)한 것만 평균 → 침입자 거리 메트릭.
        for (uint8_t k = 0; k < 4; k++) {
          const uint16_t z = TOF_CENTER_ZONES[k];
          if (!tofStatusValid(measurementData.target_status[z])) continue;
          const int16_t mm = measurementData.distance_mm[z];
          if (mm > 0) {
            center_sum += (uint32_t)mm;
            center_valid++;
          }
        }
        // ★ division by zero 가드: valid center zone 0개면 평균 생략하고 "n/a" 표기.
        char center_str[12];
        if (center_valid > 0) {
          snprintf(center_str, sizeof(center_str), "%umm",
                   (unsigned)(center_sum / center_valid));
        } else {
          snprintf(center_str, sizeof(center_str), "n/a");
        }

        // 로그 정책: presence 전환 시 즉시 1줄(우선), 그 외엔 30프레임 주기 요약(매 프레임 출력 금지).
        if (presence != presence_prev) {
          Serial.printf("[tof][StageA] presence: %s -> %s (near=%u/%u, center=%s)\n",
                        presence_prev ? "DETECTED" : "NONE",
                        presence ? "DETECTED" : "NONE",
                        (unsigned)near_count, (unsigned)TOF_ZONE_COUNT, center_str);
          presence_prev = presence;
        } else if ((frame_count % TOF_LOG_EVERY_N_FRAMES) == 1) {
          Serial.printf("[tof][StageA] frame #%u near=%u/%u presence=%s center=%s\n",
                        (unsigned)frame_count, (unsigned)near_count, (unsigned)TOF_ZONE_COUNT,
                        presence ? "DETECTED" : "NONE", center_str);
        }

        // ── Stage B (별도 태스크, 본 PR 범위 밖) ──
        // Motion Indicator = SparkFun 번들 ULD 함수(vl53l5cx_motion_indicator_init /
        //   _set_distance_motion / _set_resolution)를 imager.Dev public 핸들로 직접 호출.
        //   Adafruit 경유 아님 (decisions.md 카테고리 9 Stage B 판정 B, 2026-07-09).
        //   VL53L5CX_DISABLE_MOTION_INDICATOR 매크로는 .pio/libdeps/ 내부라 클린 빌드 시 원복 —
        //   재현 방법 확정이 선행 결정 사안.
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
  Serial.printf("\n[BOOT] ddingdong tof test (VL53L5CX %ux%u, %uHz, I2C %lukHz)\n",
                (unsigned)TOF_GRID_SIZE, (unsigned)TOF_GRID_SIZE,
                (unsigned)TOF_RANGING_FREQ_HZ,
                (unsigned long)(TOF_I2C_FREQ_HZ / 1000));

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
