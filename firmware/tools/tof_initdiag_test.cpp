// initToF() 진단 로그(D1 부팅 버스 · D2/D3 실패 시도별 코드 · 선 레벨) 호스트 검증 — 실제
// firmware/src/tof_common.cpp 를 그대로 링크한다(복사 아님).
//   c++ -std=c++17 -Wall -I firmware/include -I firmware/tools/host_stubs \
//       -o /tmp/tidt firmware/tools/tof_initdiag_test.cpp firmware/src/tof_common.cpp && /tmp/tidt
// 불변식: I1 반환·begin 호출 수 무변경 / I2 기존 로그 줄 바이트 동일("[tof] diag" 줄 걸러 낸 뒤)
//        / I3 SDA·SCL 에 OUTPUT pinMode·digitalWrite 0 / I4 재시도·I2C·판정 상수 고정.
// -DTOF_INITDIAG_BASELINE = diag 줄 단언을 끄고 I1~I4 만 — 변경 전 tof_common.cpp(HEAD)에 걸어
//   골든 문자열이 「변경 전 출력」과 같음을 증명할 때 쓴다.
#include <cassert>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "tof_common.h"

HostSerial Serial;
HostEsp    ESP;
TwoWire    Wire;

static std::string logbuf;
static void tap(const char* s) { logbuf += s; }

static int checks = 0;
#define CHECK(x) do { assert(x); checks++; } while (0)

struct Run {
  bool ret;
  int calls;
  std::string legacy;              // diag 줄 뺀 나머지(이어 붙임)
  std::vector<std::string> diag;   // "[tof] diag" 줄(개행 제외)
};

static Run run(const HostBeginStep* script, int n, int sdaLevel) {
  logbuf.clear();
  hostBeginScript = script; hostBeginScriptLen = n; hostBeginCalls = 0; hostMillis = 1000;
  memset(hostPinOutSets, 0, sizeof(hostPinOutSets));
  memset(hostPinWrites, 0, sizeof(hostPinWrites));
  hostPinLevel[TOF_SDA_PIN] = sdaLevel;
  Run r;
  r.ret = initToF();
  r.calls = hostBeginCalls;
  size_t pos = 0;
  while (pos < logbuf.size()) {
    size_t nl = logbuf.find('\n', pos);
    std::string line = logbuf.substr(pos, nl - pos);
    if (line.rfind("[tof] diag", 0) == 0) r.diag.push_back(line);
    else r.legacy += line + "\n";
    pos = nl + 1;
  }
  // I3: 진단이 버스를 몰지 않는다
  CHECK(hostPinOutSets[TOF_SDA_PIN] == 0 && hostPinOutSets[TOF_SCL_PIN] == 0);
  CHECK(hostPinWrites[TOF_SDA_PIN] == 0 && hostPinWrites[TOF_SCL_PIN] == 0);
  return r;
}

// 변경 전(HEAD f69ad96) initToF 가 호스트 스텁에서 내는 줄 그대로.
static const char* MEM_PRE  = "[MEM:pre-init] PSRAM total=0 free=0 | Heap free=0 min=0\n";
static const char* I2C_RDY  = "[tof] I2C ready (SDA=GPIO5/SCL=GPIO6, clock=400000Hz)\n";
static const char* READY    = "[tof][StageB-1] motion init skipped — Dev 미할당(begin 미완)\n"
                              "[tof] VL53L5CX ready (8x8, 15Hz, continuous)\n"
                              "[MEM:post-init] PSRAM total=0 free=0 | Heap free=0 min=0\n";
static const char* FAIL1    = "[tof] init failed (attempt 1/2)\n[tof] retry init (2/2)...\n";
static const char* FAIL2    = "[tof] init failed (attempt 2/2)\n";
static const char* SCAN     = "[tof] I2C bus scan:\n[tof]   no devices on bus (부품 부재 상태 추정)\n";

using E = SF_VL53L5CX_ERROR_TYPE;

int main() {
  Serial.tap = tap;

  // I4: 이 PR 이 건드리면 안 되는 상수
  static_assert(TOF_INIT_RETRY_MAX == 2, "재시도 2회");
  static_assert(TOF_I2C_FREQ_HZ == 400000, "I2C 400kHz");
  static_assert(TOF_SDA_PIN == 5 && TOF_SCL_PIN == 6, "지침 10항 SDA=GPIO5 SCL=GPIO6");
  static_assert(TOF_PRESENCE_MIN_ZONES == 8 && TOF_PRESENCE_DEBOUNCE_FRAMES == 3, "9.2");
  static_assert(TOF_MOTION_DIST_MIN_MM == 400 && TOF_MOTION_DIST_MAX_MM == 1500, "9.3");
  static_assert(TOF_MOTION_NDET_MIN == 1 && TOF_MOTION_LATCH_FRAMES == 75, "9.4");

  // S1 성공
  const HostBeginStep ok[] = {{true, E::NO_ERROR, 0, 2500}};
  Run a = run(ok, 1, HIGH);
  CHECK(a.ret == true && a.calls == 1);                                       // I1
  CHECK(a.legacy == std::string(MEM_PRE) + I2C_RDY + READY);                  // I2

  // S2 실패(init 순서 중 ULD status 66) → 성공
  const HostBeginStep fs[] = {{false, E::DEVICE_INITIALIZATION_ERROR, 66, 1200},
                              {true, E::NO_ERROR, 0, 2500}};
  Run b = run(fs, 2, HIGH);
  CHECK(b.ret == true && b.calls == 2);
  CHECK(b.legacy == std::string(MEM_PRE) + I2C_RDY + FAIL1 + READY);

  // S3 실패(ping NACK — 원본은 lastError 미기록 = code 0) → 실패, SDA LOW 고착
  const HostBeginStep ff[] = {{false, E::NO_ERROR, 0, 3},
                              {false, E::NO_ERROR, 0, 4}};
  Run c = run(ff, 2, LOW);
  CHECK(c.ret == false && c.calls == 2);
  CHECK(c.legacy == std::string(MEM_PRE) + I2C_RDY + FAIL1 + FAIL2 + SCAN);

#ifndef TOF_INITDIAG_BASELINE
  // D1 부팅 버스 줄 / D2·D3 실패 시도별 줄 — 실패 수만큼, 기존 init failed 줄 바로 뒤
  CHECK(a.diag.size() == 1 && a.diag[0] == "[tof] diag boot bus: SDA low 0/32, SCL low 0/32");
  CHECK(b.diag.size() == 2 && b.diag[1] == "[tof] diag attempt 1: code=3 value=66 1200ms SDA=1 SCL=1");
  CHECK(c.diag.size() == 3 && c.diag[0] == "[tof] diag boot bus: SDA low 32/32, SCL low 0/32");
  CHECK(c.diag[1] == "[tof] diag attempt 1: code=0 value=0 3ms SDA=0 SCL=1");
  CHECK(c.diag[2] == "[tof] diag attempt 2: code=0 value=0 4ms SDA=0 SCL=1");
  CHECK(logbuf.find("(attempt 1/2)\n[tof] diag attempt 1:") != std::string::npos);
  for (const Run* r : {&a, &b, &c})
    for (const std::string& d : r->diag) CHECK(d.size() + 1 <= 80);  // 줄 길이 ≤ 80B
  for (const Run* r : {&a, &b, &c})
    for (const std::string& d : r->diag) printf("  %s\n", d.c_str());
#endif

  printf("tof_initdiag_test: %d checks OK\n", checks);
  return 0;
}
