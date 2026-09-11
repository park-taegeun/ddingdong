// 띵동 PoC firmware - ToF 더미 테스트 (5/11, PoC Day 5)
//
// tofTask 단독: isDataReady 폴링 + 64 zone 거리 추출 + Stage A 사람 존재 판정.
// 2026-08-07 브레드보드 브링업 성공(카테고리 9.1)으로 실측 단계 진입.
// 2026-08-08 ④런타임 실측에서 임계 경계 플리커 확인 → presence에 N=3 대칭 디바운스 도입.
// Stage B-1(Motion Indicator 계측 계층): motion 값을 관측·로그로만 노출(presence 판정 무변경).
// 2026-09-02 Stage B-2(판정 계층) 추가: B-1이 관측하던 ndet를 임계 판정으로 승격하고,
//   motion latch(이벤트 보존)와 Stage A presence를 프레임 단위 AND로 융합한다.
//   ★ B-1 계측 로직·감시창·로그 포맷은 0라인 변경 — B-2는 그 출력을 소비만 한다.
// 2026-09-11 PoC-(45) 승격: Stage A/B-1/B-2 판정·로그 본문을 tof_common.cpp tofJudgeFrame() 로
//   **순수 이동**(로직·상수·로그 포맷 0변경). 본 파일은 폴링 + 호출만 남는다. 상태는 종전
//   tofTask 내 static 4개 + 지역 frame_count 를 TofJudgeState 로 묶어 그대로 static 소유.
//   이동 사유 = env:mic_uplink 가 같은 판정을 /detect ToF 4필드로 송신(복제 금지, D2).
// 5/21 PoC 통합 시 cameraTask(Core 1) + micTask(Core 0, prio 4) + tofTask(Core 0, prio 3)
// 병행 검증 (decisions.md 카테고리 14).

#include "tof_common.h"

extern SparkFun_VL53L5CX tofImager;

static void tofTask(void* parameter) {
  (void)parameter;
  logToFMemoryDiagnostics("tofTask-entry");

  // ResultsData ~1356B (SparkFun 주석 인용). task 스택(6KiB) 폭주 방지로 static (BSS).
  static VL53L5CX_ResultsData measurementData;
  // 판정 상태는 tofTask 내 static (BSS) — 전역 변수 신설 없이 유지(종전 static 4개와 동일 배치).
  static TofJudgeState judge;
  uint32_t err_count = 0;

  for (;;) {
    if (tofImager.isDataReady()) {
      if (tofImager.getRangingData(&measurementData)) {
        // Stage A → center → B-1 로그 → B-2 latch/융합 (+ 전이·주기 로그). 반환값은 본 env 미사용
        //   (mic_uplink 가 /detect 4필드로 소비) — 여기서는 로그 포맷 회귀 대상만 유지한다.
        (void)tofJudgeFrame(&judge, measurementData);
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
