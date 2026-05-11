// 띵동 PoC firmware - ToF 공통 구현 (5/11, PoC Day 5)

#include "tof_common.h"

// 외부에서 tofTask가 접근하는 imager 인스턴스. mic_common의 i2s 핸들과 동일 패턴.
SparkFun_VL53L5CX tofImager;

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

  // ESP32-S3 GPIO 매핑 + 1MHz 워크어라운드 (사전 검증 ①).
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
