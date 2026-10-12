// 호스트 스텁 — SparkFun VL53L5CX 라이브러리 v1.0.3 의 표면 중 tof_common.* 가 참조하는 것만.
// VL53L5CX_ResultsData 는 번들 ULD vl53l5cx_api.h:337~398 의 필드 중 tofJudgeFrame 이 읽는 것만
// 같은 타입·같은 이름으로 재현한다(motion_indicator 하위 구조체는 원본 레이아웃 그대로).
#pragma once
#include <cstdint>
#include "Arduino.h"  // hostMillis (원본 라이브러리도 Arduino.h 포함)

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

// v1.0.3 SparkFun_VL53L5CX_Library_Constants.h 의 enum 앞부분(정수값 동일) + lastError 구조.
enum class SF_VL53L5CX_ERROR_TYPE : uint8_t {
  NO_ERROR,                     // 0 — ★ begin() 의 주소 ping NACK 경로도 이 값(lastError 미기록)
  I2C_INITIALIZATION_ERROR,     // 1 (콜백 전용)
  I2C_NOT_RESPONDING,           // 2
  DEVICE_INITIALIZATION_ERROR,  // 3 — value = ULD vl53l5cx_init status
  INVALID_DEVICE,               // 4
};
struct SparkFun_VL53L5CX_Error {
  SF_VL53L5CX_ERROR_TYPE lastErrorCode = SF_VL53L5CX_ERROR_TYPE::NO_ERROR;
  uint32_t lastErrorValue = 0;
};

// begin() 결과 대본(tof_initdiag_test): 호출마다 다음 단계를 소비. 대본이 없으면 종전처럼 false.
struct HostBeginStep {
  bool ok;
  SF_VL53L5CX_ERROR_TYPE code;
  uint32_t value;
  unsigned long ms;  // 이 시도에 걸린 시간(hostMillis 전진)
};
inline const HostBeginStep* hostBeginScript = nullptr;
inline int hostBeginScriptLen = 0;
inline int hostBeginCalls = 0;

class SparkFun_VL53L5CX {
 public:
  VL53L5CX_Configuration* Dev = nullptr;
  SparkFun_VL53L5CX_Error lastError;
  bool begin() {
    lastError = SparkFun_VL53L5CX_Error();  // 원본 clearErrorStruct()
    if (hostBeginCalls >= hostBeginScriptLen) { hostBeginCalls++; return false; }
    const HostBeginStep& st = hostBeginScript[hostBeginCalls++];
    hostMillis += st.ms;
    lastError.lastErrorCode = st.code;
    lastError.lastErrorValue = st.value;
    return st.ok;
  }
  bool setResolution(uint8_t) { return true; }
  bool setRangingFrequency(uint8_t) { return true; }
  bool startRanging() { return true; }
  bool isDataReady() { return false; }
  bool getRangingData(VL53L5CX_ResultsData*) { return false; }
};
