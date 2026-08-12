// 띵동 PoC firmware - ToF 공통 구현 (5/11, PoC Day 5)

#include "tof_common.h"
// Stage B-1: SparkFun 래퍼는 motion 전용 메서드 0건 → 번들 ULD 함수를 직접 include하여
//   tofImager.Dev(public VL53L5CX_Configuration*) 핸들로 호출(decisions.md 카테고리 9 판정 B).
#include <vl53l5cx_plugin_motion_indicator.h>

// 외부에서 tofTask가 접근하는 imager 인스턴스. mic_common의 i2s 핸들과 동일 패턴.
SparkFun_VL53L5CX tofImager;

// Stage B-1: Motion Indicator를 센서에 프로그래밍. begin() 성공(=Dev 할당) 이후에만 호출.
//   VL53L5CX_Motion_Configuration(~156B)은 프로그래밍 시점에만 필요하고 set_distance_motion이
//   device로 write하면(motion_indicator.cpp:124) 이후 결과는 ResultsData.motion_indicator로 들어온다.
//   → 영구 BSS로 상주시킬 필요가 없어 함수 로컬(전이 스택)로 둔다. 런타임 RAM 순증 0 목표.
bool initToFMotionIndicator() {
  if (tofImager.Dev == nullptr) {
    Serial.println("[tof][StageB-1] motion init skipped — Dev 미할당(begin 미완)");
    return false;
  }

  VL53L5CX_Motion_Configuration motionConfig;

  // init: 기본 config + 8x8 aggregate map 구성(내부적으로 set_resolution 호출). resolution은 센서와 정합.
  uint8_t status = vl53l5cx_motion_indicator_init(
      tofImager.Dev, &motionConfig, VL53L5CX_RESOLUTION_8X8);

  // set_distance_motion: 감시 거리창을 확정하며 config 전체를 device로 write(=실제 활성화 지점).
  //   400~1500mm = ST ULD 문서화 기본값(판정 임계값 아님, 근거 = tof_common.h TOF_MOTION_DIST_* 주석).
  status |= vl53l5cx_motion_indicator_set_distance_motion(
      tofImager.Dev, &motionConfig, TOF_MOTION_DIST_MIN_MM, TOF_MOTION_DIST_MAX_MM);

  if (status == VL53L5CX_STATUS_OK) {
    Serial.printf("[tof][StageB-1] motion indicator ready (8x8, %u~%umm, %u aggregates)\n",
                  (unsigned)TOF_MOTION_DIST_MIN_MM, (unsigned)TOF_MOTION_DIST_MAX_MM,
                  (unsigned)TOF_MOTION_AGG_COUNT_8X8);
    return true;
  }
  // 실패해도 Stage A는 계속 — 여기서 return false는 로깅용이며 initToF() 반환을 죽이지 않는다.
  Serial.printf("[tof][StageB-1] motion init failed (status=%u) — Stage A는 계속 동작\n",
                (unsigned)status);
  return false;
}

void logToFMemoryDiagnostics(const char* tag) {
  // 5/12 메모리 self-checkpoint 입력 데이터 (decisions.md 카테고리 17.1.1).
  Serial.printf("[MEM:%s] PSRAM total=%u free=%u | Heap free=%u min=%u\n",
                tag,
                (unsigned)ESP.getPsramSize(),
                (unsigned)ESP.getFreePsram(),
                (unsigned)ESP.getFreeHeap(),
                (unsigned)ESP.getMinFreeHeap());
}

bool initToF() {
  logToFMemoryDiagnostics("pre-init");

  // ESP32-S3 GPIO 매핑 + I2C 클럭(TOF_I2C_FREQ_HZ = 400kHz, 2026-08-07 실측 정식 채택).
  // 정정: 구 "1MHz 워크어라운드" 주석은 8/07 브링업 실측(카테고리 9.1)으로 무효 — 상수 단일 출처 참조.
  Wire.begin(TOF_SDA_PIN, TOF_SCL_PIN);
  Wire.setClock(TOF_I2C_FREQ_HZ);
  Serial.printf("[tof] I2C ready (SDA=GPIO%d/SCL=GPIO%d, clock=%uHz)\n",
                TOF_SDA_PIN, TOF_SCL_PIN, (unsigned)TOF_I2C_FREQ_HZ);

  // OnlyFeet 패턴: 2회 retry. SparkFun begin()이 내부적으로 ~86KB FW upload 수행 (수 초 소요).
  // SparkFun begin()은 8-bit 주소(0x52) → 7-bit shift (DEFAULT_I2C_ADDR >> 1 = 0x29) 기본값.
  for (int attempt = 0; attempt < TOF_INIT_RETRY_MAX; attempt++) {
    if (attempt > 0) {
      Serial.printf("[tof] retry init (%d/%d)...\n", attempt + 1, TOF_INIT_RETRY_MAX);
    }
    if (tofImager.begin()) {
      // 8x8 mode (datasheet RESOLUTION_8X8 = 64).
      tofImager.setResolution(TOF_ZONE_COUNT);
      // 15Hz @ 8x8 (datasheet limit, SparkFun Example3 패턴).
      tofImager.setRangingFrequency(TOF_RANGING_FREQ_HZ);
      // Stage B-1: motion 설정은 startRanging 이전에(ST 시퀀스). best-effort — 실패해도 아래로 계속.
      initToFMotionIndicator();
      tofImager.startRanging();
      Serial.printf("[tof] VL53L5CX ready (%dx%d, %uHz, continuous)\n",
                    TOF_GRID_SIZE, TOF_GRID_SIZE, TOF_RANGING_FREQ_HZ);
      logToFMemoryDiagnostics("post-init");
      return true;
    }
    Serial.printf("[tof] init failed (attempt %d/%d)\n", attempt + 1, TOF_INIT_RETRY_MAX);
  }

  // OnlyFeet 진단 패턴: 실패 시 I2C scan으로 부품 부재/배선 오류 구분.
  Serial.println("[tof] I2C bus scan:");
  bool anyDevice = false;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.printf("[tof]   device at 0x%02X\n", addr);
      anyDevice = true;
    }
  }
  if (!anyDevice) {
    Serial.println("[tof]   no devices on bus (부품 부재 상태 추정)");
  }
  return false;
}
