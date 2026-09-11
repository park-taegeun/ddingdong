// 호스트 스텁 — ST ULD motion indicator 플러그인 표면(initToFMotionIndicator 가 참조). 테스트 미호출.
#pragma once
#include <cstdint>
#include "SparkFun_VL53L5CX_Library.h"

struct VL53L5CX_Motion_Configuration {};

inline uint8_t vl53l5cx_motion_indicator_init(VL53L5CX_Configuration*, VL53L5CX_Motion_Configuration*,
                                              uint8_t) {
  return 0;
}
inline uint8_t vl53l5cx_motion_indicator_set_distance_motion(VL53L5CX_Configuration*,
                                                             VL53L5CX_Motion_Configuration*,
                                                             uint16_t, uint16_t) {
  return 0;
}
