// 호스트 스텁 — SparkFun VL53L5CX 라이브러리 v1.0.3 의 표면 중 tof_common.* 가 참조하는 것만.
// VL53L5CX_ResultsData 는 번들 ULD vl53l5cx_api.h:337~398 의 필드 중 tofJudgeFrame 이 읽는 것만
// 같은 타입·같은 이름으로 재현한다(motion_indicator 하위 구조체는 원본 레이아웃 그대로).
#pragma once
#include <cstdint>

#define VL53L5CX_RESOLUTION_8X8 ((uint8_t)64U)
#define VL53L5CX_STATUS_OK ((uint8_t)0U)

struct VL53L5CX_ResultsData {
  int16_t distance_mm[64];
  uint8_t target_status[64];
  struct {
    uint32_t global_indicator_1;
    uint32_t global_indicator_2;
    uint8_t  status;
    uint8_t  nb_of_detected_aggregates;
    uint8_t  nb_of_aggregates;
    uint8_t  spare;
    uint32_t motion[32];
  } motion_indicator;
};

struct VL53L5CX_Configuration {};

class SparkFun_VL53L5CX {
 public:
  VL53L5CX_Configuration* Dev = nullptr;
  bool begin() { return false; }
  bool setResolution(uint8_t) { return true; }
  bool setRangingFrequency(uint8_t) { return true; }
  bool startRanging() { return true; }
  bool isDataReady() { return false; }
  bool getRangingData(VL53L5CX_ResultsData*) { return false; }
};
