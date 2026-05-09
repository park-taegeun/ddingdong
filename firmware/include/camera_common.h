// 띵동 PoC firmware - 카메라 더미 테스트 공통 헤더 (5/9, PoC-(6) Day 3)
//
// Version A (cameraTask 단독), Version B (writerTask 분리) 양 버전 공통 코드.
// 부품 부재 상태 (자성리얼 5/15~5/28 도착) → 컴파일 + 메모리 진단까지만 검증.
// 카테고리 13 사전 반영 사항 (xclk_freq_hz, fb_count, fb_location, grab_mode 등) 일괄 적용.
//
// 출처:
//   - 공식 esp32-camera README (context7 /espressif/esp32-camera)
//   - Manjot Khangura "Getting ESP32-S3 Sense + OV3660 Camera Working" (Medium, 2026-02-09)
//     함정 #1 OCTAL PSRAM, #2 fb_count=2, #4 vTaskDelay(30ms) + xclk 20MHz 적용.
//   - Arduino-ESP32 core 3.x examples/Camera/CameraWebServer/camera_pins.h (XIAO 핀 매핑)

#pragma once

#include <Arduino.h>
#include "esp_camera.h"

// === XIAO ESP32-S3 Sense 카메라 핀 매핑 (Arduino-ESP32 CAMERA_MODEL_XIAO_ESP32S3과 동일) ===
#if defined(CAMERA_MODEL_XIAO_ESP32S3)
  #define PWDN_GPIO_NUM     -1
  #define RESET_GPIO_NUM    -1
  #define XCLK_GPIO_NUM     10
  #define SIOD_GPIO_NUM     40
  #define SIOC_GPIO_NUM     39
  #define Y9_GPIO_NUM       48
  #define Y8_GPIO_NUM       11
  #define Y7_GPIO_NUM       12
  #define Y6_GPIO_NUM       14
  #define Y5_GPIO_NUM       16
  #define Y4_GPIO_NUM       18
  #define Y3_GPIO_NUM       17
  #define Y2_GPIO_NUM       15
  #define VSYNC_GPIO_NUM    38
  #define HREF_GPIO_NUM     47
  #define PCLK_GPIO_NUM     13
#else
  #error "CAMERA_MODEL_XIAO_ESP32S3 not defined — check platformio.ini build_flags"
#endif

// === 카메라 설정 상수 (카테고리 13 사전 반영 사항) ===
constexpr uint32_t      CAMERA_XCLK_FREQ_HZ    = 20000000;        // OV2640 기본, OV3660 호환
constexpr int           CAMERA_JPEG_QUALITY    = 12;              // 0-63, 낮을수록 고품질 (Medium)
constexpr int           CAMERA_FB_COUNT        = 2;               // dual buffer 필수 (Khangura #2)
constexpr framesize_t   CAMERA_DEFAULT_FRAMESIZE = FRAMESIZE_QVGA; // 320x240, PSRAM budget 우선

// === FreeRTOS 태스크 설정 (카테고리 15 5/21 PoC 분배 잠정안) ===
constexpr uint32_t      CAMERA_TASK_STACK_SIZE     = 4096;
constexpr UBaseType_t   CAMERA_TASK_PRIORITY       = 4;
constexpr UBaseType_t   WRITER_TASK_PRIORITY       = 3;
constexpr BaseType_t    CAMERA_TASK_CORE           = 1;
constexpr uint32_t      CAMERA_FRAME_INTERVAL_MS   = 30;           // fb_return 후 vTaskDelay (Khangura #4)
constexpr uint32_t      CAMERA_INIT_RETRY_DELAY_MS = 5000;         // 부품 부재 시 graceful 대기
constexpr uint32_t      CAMERA_LOOP_IDLE_LOG_MS    = 5000;
constexpr uint32_t      SERIAL_BOOT_DELAY_MS       = 200;
constexpr UBaseType_t   FB_QUEUE_LENGTH            = 4;            // Version B writerTask queue
constexpr uint32_t      LOG_EVERY_N_FRAMES         = 30;
constexpr uint32_t      LOG_EVERY_N_NULLS          = 10;

// === API ===
camera_config_t buildCameraConfig();
bool            initCameraWithDiagnostics();
void            logMemoryDiagnostics(const char* tag);
const char*     sensorIdToName(int pid);
