// 호스트 단위 테스트용 Arduino.h 스텁 — tof_common.cpp 를 c++ 로 컴파일하기 위한 최소 표면.
// 실보드 코드 0변경. 테스트가 호출하지 않는 함수는 no-op / 0 반환.
#pragma once
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstring>

typedef unsigned UBaseType_t;
typedef int      BaseType_t;

// Serial.printf 캡처: 마지막 줄 보관 + 총 줄 수(로그 포맷 회귀 단언용). TOF_HOST_ECHO=1 이면 stdout 에도 출력.
struct HostSerial {
  char     last[256] = {0};
  unsigned lines     = 0;
  bool     echo      = false;
  int printf(const char* fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    const int n = vsnprintf(last, sizeof(last), fmt, ap);
    va_end(ap);
    lines++;
    if (echo) fputs(last, stdout);
    return n;
  }
  void println(const char* s) { snprintf(last, sizeof(last), "%s\n", s); lines++; if (echo) fputs(last, stdout); }
  void begin(unsigned long) {}
};
extern HostSerial Serial;

struct HostEsp {
  uint32_t getPsramSize() { return 0; }
  uint32_t getFreePsram() { return 0; }
  uint32_t getFreeHeap() { return 0; }
  uint32_t getMinFreeHeap() { return 0; }
};
extern HostEsp ESP;
