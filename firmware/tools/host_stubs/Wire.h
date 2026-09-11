// 호스트 스텁 — initToF() 가 참조하는 TwoWire 표면만. 테스트는 호출하지 않는다.
#pragma once
#include <cstdint>
class TwoWire {
 public:
  void    begin(int, int) {}
  void    setClock(uint32_t) {}
  void    beginTransmission(uint8_t) {}
  uint8_t endTransmission() { return 1; }
};
extern TwoWire Wire;
