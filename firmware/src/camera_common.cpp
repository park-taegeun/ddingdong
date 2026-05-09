// 띵동 PoC firmware - 카메라 공통 구현 (5/9, PoC-(6) Day 3)

#include "camera_common.h"

camera_config_t buildCameraConfig() {
  camera_config_t config = {};
  config.pin_pwdn        = PWDN_GPIO_NUM;
  config.pin_reset       = RESET_GPIO_NUM;
  config.pin_xclk        = XCLK_GPIO_NUM;
  config.pin_sccb_sda    = SIOD_GPIO_NUM;
  config.pin_sccb_scl    = SIOC_GPIO_NUM;
  config.pin_d7          = Y9_GPIO_NUM;
  config.pin_d6          = Y8_GPIO_NUM;
  config.pin_d5          = Y7_GPIO_NUM;
  config.pin_d4          = Y6_GPIO_NUM;
  config.pin_d3          = Y5_GPIO_NUM;
  config.pin_d2          = Y4_GPIO_NUM;
  config.pin_d1          = Y3_GPIO_NUM;
  config.pin_d0          = Y2_GPIO_NUM;
  config.pin_vsync       = VSYNC_GPIO_NUM;
  config.pin_href        = HREF_GPIO_NUM;
  config.pin_pclk        = PCLK_GPIO_NUM;

  config.xclk_freq_hz    = CAMERA_XCLK_FREQ_HZ;
  config.ledc_timer      = LEDC_TIMER_0;
  config.ledc_channel    = LEDC_CHANNEL_0;
  config.pixel_format    = PIXFORMAT_JPEG;
  config.frame_size      = CAMERA_DEFAULT_FRAMESIZE;
  config.jpeg_quality    = CAMERA_JPEG_QUALITY;
  config.fb_count        = CAMERA_FB_COUNT;
  config.fb_location     = CAMERA_FB_IN_PSRAM;
  config.grab_mode       = CAMERA_GRAB_LATEST;
  return config;
}

void logMemoryDiagnostics(const char* tag) {
  // PSRAM/heap 모두 측정. 5/12 메모리 self-checkpoint 입력 데이터 (카테고리 17.1.1).
  Serial.printf("[MEM:%s] PSRAM total=%u free=%u | Heap free=%u min=%u\n",
                tag,
                (unsigned)ESP.getPsramSize(),
                (unsigned)ESP.getFreePsram(),
                (unsigned)ESP.getFreeHeap(),
                (unsigned)ESP.getMinFreeHeap());
}

const char* sensorIdToName(int pid) {
  switch (pid) {
    case 0x26: return "OV2640";
    case 0x36: return "OV3660";
    case 0x76: return "OV7670";
    case 0x77: return "OV7725";
    default:   return "UNKNOWN";
  }
}

bool initCameraWithDiagnostics() {
  // Khangura 함정 #1: XIAO는 OCTAL PSRAM이라 sdkconfig CONFIG_SPIRAM_MODE_OCT=y 필요.
  // PlatformIO seeed_xiao_esp32s3 board.json이 설정하나, runtime 검증으로 안전망.
  if (!psramFound()) {
    Serial.println("[CAMERA] FATAL: PSRAM not found — board flag/sdkconfig 점검 필요");
    return false;
  }
  logMemoryDiagnostics("pre-init");

  camera_config_t cfg = buildCameraConfig();
  const esp_err_t err = esp_camera_init(&cfg);
  if (err != ESP_OK) {
    // 부품 부재 (카메라 미연결) 시 대표 코드: ESP_ERR_CAMERA_NOT_DETECTED (0x105).
    Serial.printf("[CAMERA] esp_camera_init failed: 0x%x (%s)\n",
                  err, esp_err_to_name(err));
    return false;
  }

  // OV2640 / OV3660 분기 (런타임 sensor 감지). decisions.md 카테고리 1: OV2640 기본.
  sensor_t* sensor = esp_camera_sensor_get();
  if (sensor != nullptr) {
    Serial.printf("[CAMERA] Sensor PID=0x%02x (%s)\n",
                  sensor->id.PID, sensorIdToName(sensor->id.PID));
    if (sensor->id.PID == 0x36) {
      // Khangura 함정 #6 보정 (OV3660 한정).
      sensor->set_brightness(sensor, 1);
      sensor->set_saturation(sensor, -2);
      Serial.println("[CAMERA] OV3660 brightness/saturation 보정 적용");
    }
  }
  logMemoryDiagnostics("post-init");
  return true;
}
