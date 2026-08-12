// 띵동 PoC firmware - ToF 더미 테스트 (5/11, PoC Day 5)
//
// tofTask 단독: isDataReady 폴링 + 64 zone 거리 추출 + Stage A 사람 존재 판정.
// 2026-08-07 브레드보드 브링업 성공(카테고리 9.1)으로 실측 단계 진입.
// 2026-08-08 ④런타임 실측에서 임계 경계 플리커 확인 → presence에 N=3 대칭 디바운스 도입.
// Stage B-1(Motion Indicator 계측 계층): motion 값을 관측·로그로만 노출(presence 판정 무변경).
//   B-2(임계값 확정 + presence 융합)는 실측 곡선 확보 후 별도 태스크 — 본 파일 하단 defer 주석 참조.
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

  // presence 디바운스 상태는 tofTask 내 static (BSS) — 전역 변수 신설 없이 유지.
  //   presence_state  = 디바운스 통과한 "확정" 상태 (로그·요약이 참조하는 값)
  //   presence_streak = 확정 상태와 다른 raw 판정이 몇 프레임 연속됐는지 카운터
  // 초기값: NONE(false) / 0. 부팅 직후 물체가 있으면 3프레임 뒤 DETECTED로 전환됨(정상).
  static bool    presence_state  = false;
  static uint8_t presence_streak = 0;

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
        // valid zone 0개 프레임(센서 시야 전체 무효)이어도 near_count=0 → raw=false로 정상 처리.
        // ★ raw 판정 로직은 PR #34 원형 그대로(변경 금지). 아래 디바운스는 그 위에 얹는 안정화 계층.
        const bool raw_presence = (near_count >= TOF_PRESENCE_MIN_ZONES);

        // ── 디바운스: raw가 확정 상태와 "다른" 프레임이 N회 연속돼야 확정 상태를 전환(진입/이탈 대칭) ──
        // 오버플로 안전: presence_streak는 이 if 분기에서만 +1 되고, N에 "도달"하는 즉시 0으로 리셋.
        //   → 프레임 종료 시 값은 항상 {0,1,2} 중 하나(N=3). else 분기도 0으로 리셋. uint8_t 상한과 무관.
        bool transitioned = false;
        if (raw_presence != presence_state) {
          if (++presence_streak >= TOF_PRESENCE_DEBOUNCE_FRAMES) {
            presence_state  = raw_presence;   // 확정 상태 전환
            presence_streak = 0;              // 전환 즉시 리셋
            transitioned    = true;
          }
        } else {
          presence_streak = 0;                // 확정 상태 유지 프레임 → 카운터 리셋
        }

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

        // 로그 정책: 확정 상태가 "실제로 전환"될 때만 1줄(raw 변동으로는 출력 안 함),
        //            그 외엔 30프레임 주기 요약(확정 상태 표시, 매 프레임 출력 금지).
        // streak=N은 전환을 성립시킨 연속 프레임 수(전환 직후 카운터는 0으로 리셋됨).
        if (transitioned) {
          Serial.printf("[tof][StageA] presence: %s -> %s (near=%u/%u, center=%s, streak=%u)\n",
                        presence_state ? "NONE" : "DETECTED",   // 전환 전 = !presence_state
                        presence_state ? "DETECTED" : "NONE",
                        (unsigned)near_count, (unsigned)TOF_ZONE_COUNT, center_str,
                        (unsigned)TOF_PRESENCE_DEBOUNCE_FRAMES);
        } else if ((frame_count % TOF_LOG_EVERY_N_FRAMES) == 1) {
          Serial.printf("[tof][StageA] frame #%u near=%u/%u presence=%s center=%s\n",
                        (unsigned)frame_count, (unsigned)near_count, (unsigned)TOF_ZONE_COUNT,
                        presence_state ? "DETECTED" : "NONE", center_str);
        }

        // ── Stage B-1 계측 계층: Motion Indicator 관측 (★ presence 판정 무변경, 관측 전용) ──
        // motion 초기화 = tof_common.cpp initToFMotionIndicator()가 begin 직후 프로그래밍.
        //   VL53L5CX_DISABLE_MOTION_INDICATOR 매크로는 platform.h에서 주석 상태(=활성)로 배포되어
        //   .motion_indicator 필드가 상주한다(2026-08-12 sha256 확인, 매크로 패치 불필요).
        // ★ 관측 통계 선정 근거: device-native 전역값(global_indicator_1 = 전역 motion 크기,
        //   nb_of_detected_aggregates = device 자체 공간 검출 수, status = 결과 유효성)이 B-2 임계값의
        //   1차 후보이고, 여기에 활성 aggregate 16개의 피크(aggmax)를 더해 공간 국소성을 본다.
        //   로그에 near_count·center를 반드시 동반시켜 측정 조건이 수치와 함께 이동한다(9.2(d) 8→20 교훈).
        // serial flood 방지: 매 프레임이 아니라 TOF_MOTION_LOG_EVERY_N_FRAMES 주기로만 출력.
        if ((frame_count % TOF_MOTION_LOG_EVERY_N_FRAMES) == 0) {
          const auto& mi = measurementData.motion_indicator;
          // motion[]은 aggregate 단위(8x8 = 16개, motion[16..31] 미사용). max는 합이 아니라 피크라 오버플로 불가.
          uint32_t agg_motion_max = 0;
          for (uint8_t a = 0; a < TOF_MOTION_AGG_COUNT_8X8; a++) {
            if (mi.motion[a] > agg_motion_max) agg_motion_max = mi.motion[a];
          }
          Serial.printf("[tof][StageB-1] mi: g1=%lu ndet=%u/%u st=%u aggmax=%lu | near=%u/%u center=%s\n",
                        (unsigned long)mi.global_indicator_1,
                        (unsigned)mi.nb_of_detected_aggregates, (unsigned)mi.nb_of_aggregates,
                        (unsigned)mi.status, (unsigned long)agg_motion_max,
                        (unsigned)near_count, (unsigned)TOF_ZONE_COUNT, center_str);
        }

        // ── Stage B-2 (임계값 확정 + presence 융합) — 본 PR 범위 밖, ④런타임 실측 대기 ──
        // B-1은 위처럼 motion을 관측·로그로만 노출한다. presence 상태 전환(Stage A)에 motion을 넣지 않는다.
        // 임계값(global_indicator_1 / nb_of_detected_aggregates / aggmax 중 무엇을, 경계값 얼마)은
        //   아래 4종 대조 실험으로 곡선을 확보한 뒤 B-2에서 확정한다(★ 하드코딩 금지 — 9.2(d) 8→20 오판 재발 방지):
        //   ① 무자극 기준선            : 시야 비움 → motion noise floor 분포
        //   ② 정지 사물(택배상자) 1m    : near는 뜨지만 motion은 낮아야 함 → 오탐 억제 근거
        //   ③ 정지한 사람 1m           : ★ motion이 뜨지 않으면 Stage B 설계 재검토(호흡/미동만으로 분리 가능한지)
        //   ④ 사람 스윕 접근(2.9m→5.6cm): near_count 곡선과 motion 곡선의 동반 상승 구간 확인
        // 판정: ② < 임계 ≤ ③④ 를 만족하는 경계가 존재하면 그 값으로 B-2 확정.
        //       ③에서 motion ≈ ② 이면 Stage C(NanoEdge AI) 승격 검토.
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
