// heartbeat_wire.h 호스트 검산 — 실제 firmware/include/heartbeat_wire.h 를 그대로 include 한다(복사 아님).
//   c++ -std=c++17 -Wall -I firmware/include -o /tmp/hbt firmware/tools/heartbeat_wire_test.cpp && /tmp/hbt
// (repo 루트에서 실행해야 한다 — 관계 대조가 server/app/routes.py · constants.py · firmware/include/uplink_common.h 를
//  상대경로로 읽는다.)
//
// 이 하네스가 지켜야 할 불변식:
//   I1 본문 바이트가 서버 계약과 정확히 같다(필드 이름 · 순서 · 압축 JSON)
//   I2 잘리거나 위험 문자가 있으면 0 — 부분 본문을 내보내지 않고 cap 너머를 쓰지 않는다
//   I3 마이크가 진행하지 않으면 보내지 않는다(「모르면 정상」 금지)
//   I4 판정 순서 = WiFi → RSSI → 마이크(사유 로그가 가장 앞선 원인을 가리킨다)
//   I5 RSSI 0 은 보내지 않는다(서버는 받지만 대시보드에 「강함」으로 보인다 — 서버 검증으로 못 잡는 축)
//   I6 서버 꺼짐 판정(DEVICE_OFFLINE_AFTER) ≥ 보고 3회분 · fw 규칙 · 필드 이름이 서버 실물과 맞다
//
// ⚠️ 단언 무딤 함정:
//   - I3 는 WiFi 끊김 케이스만 보면 「항상 SEND」 변형을 통과시킨다 → WiFi · RSSI 정상 + 마이크 정지 케이스를 둔다.
//   - I2 는 cap 이 넉넉한 케이스만 보면 부분 길이 반환을 못 잡는다 → 정확히 n · n+1 경계를 본다.
//   - I5 는 0 만 보면 범위 검사 통째 제거와 상한 경계 뒤집기(-1 거부)를 가르지 못한다 → 0 · −1 · −127 · −128 을 본다.
// negative control(원본 헤더 변형 → 반드시 실패) 은 ENRICH_UPLINK_RUNBOOK.md 10-4 표 참조.
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <regex>
#include <sstream>
#include <string>

#include "heartbeat_wire.h"

static int checks = 0;
#define CHECK(x) do { assert(x); checks++; } while (0)

static std::string readFile(const char* rel) {
  std::ifstream f(rel);
  if (!f) {
    fprintf(stderr, "%s 를 못 읽음 — repo 루트에서 실행할 것\n", rel);
    exit(1);
  }
  std::stringstream ss;
  ss << f.rdbuf();
  return ss.str();
}

int main() {
  // T1 (I1) 정확 바이트 — 대표 값 1벌
  {
    char out[HB_JSON_BUF_BYTES];
    const size_t n = hbBuildJson(out, sizeof(out), "ddingdong-mic-uplink-001", -55, 123, HB_FW_ENRICH_AUTOTRIG, 3);
    const char* want =
        "{\"device_id\":\"ddingdong-mic-uplink-001\",\"rssi\":-55,\"uptime_s\":123,"
        "\"fw\":\"enrich_autotrig\",\"enrich_sent\":3}";
    CHECK(n == strlen(want));
    CHECK(strcmp(out, want) == 0);
  }

  // T2 (I1) 경계 값 — rssi 음수 최소 · uptime 0 / UINT32_MAX · enrich_sent 큰 값
  {
    char out[HB_JSON_BUF_BYTES];
    CHECK(hbBuildJson(out, sizeof(out), "d", -127, 0, "f", 0) > 0);
    CHECK(strcmp(out, "{\"device_id\":\"d\",\"rssi\":-127,\"uptime_s\":0,\"fw\":\"f\",\"enrich_sent\":0}") == 0);
    CHECK(hbBuildJson(out, sizeof(out), "d", -1, UINT32_MAX, "f", UINT32_MAX) > 0);
    CHECK(strcmp(out, "{\"device_id\":\"d\",\"rssi\":-1,\"uptime_s\":4294967295,\"fw\":\"f\","
                      "\"enrich_sent\":4294967295}") == 0);
  }

  // T3 (I2) 잘림 → 0 + NUL + cap 너머 무기록(카나리아). 경계 = 정확히 n+1 이면 성공, n 이면 0.
  {
    char ref[HB_JSON_BUF_BYTES];
    const size_t n = hbBuildJson(ref, sizeof(ref), "ddingdong-mic-uplink-001", -55, 123, HB_FW_ENRICH_UPLINK, 3);
    CHECK(n > 0);
    for (size_t cap = 1; cap <= n + 1; ++cap) {
      char buf[HB_JSON_BUF_BYTES + 8];
      memset(buf, 'Z', sizeof(buf));
      const size_t got = hbBuildJson(buf, cap, "ddingdong-mic-uplink-001", -55, 123, HB_FW_ENRICH_UPLINK, 3);
      if (cap == n + 1) {
        CHECK(got == n);
        CHECK(strcmp(buf, ref) == 0);
      } else {
        CHECK(got == 0);
        CHECK(buf[0] == '\0');
      }
      for (size_t i = cap; i < sizeof(buf); ++i) CHECK(buf[i] == 'Z');
    }
    CHECK(hbBuildJson(nullptr, 64, "d", -1, 0, "f", 0) == 0);
    char one[1] = {'Z'};
    CHECK(hbBuildJson(one, 0, "d", -1, 0, "f", 0) == 0 && one[0] == 'Z');   // cap 0 = 한 바이트도 안 쓴다
  }

  // T4 (I2) 따옴표 · 역슬래시 · 제어문자 · nullptr → 0 (이스케이프를 발명하지 않는다)
  {
    char out[HB_JSON_BUF_BYTES];
    const char* bad[] = {"a\"b", "a\\b", "a\nb", "\x01", "a\x1f"};
    for (const char* b : bad) {
      memset(out, 'Z', sizeof(out));
      CHECK(hbBuildJson(out, sizeof(out), b, -55, 1, "f", 0) == 0 && out[0] == '\0');
      memset(out, 'Z', sizeof(out));
      CHECK(hbBuildJson(out, sizeof(out), "d", -55, 1, b, 0) == 0 && out[0] == '\0');
    }
    CHECK(hbBuildJson(out, sizeof(out), nullptr, -55, 1, "f", 0) == 0);
    CHECK(hbBuildJson(out, sizeof(out), "d", -55, 1, nullptr, 0) == 0);
  }

  // T5 (I3 · I4 · I5) hbDecide 전 조합 — 순서 WiFi → RSSI → 마이크
  {
    const int32_t rssis[] = {1, 0, -1, -55, -127, -128};
    const uint32_t mics[][2] = {{5, 5}, {6, 5}, {0, UINT32_MAX}};   // 정지 · 진행 · 랩어라운드 진행
    for (int w = 0; w <= 1; ++w) {
      for (int32_t r : rssis) {
        for (const auto& m : mics) {
          const HbVerdict v = hbDecide(w == 1, r, m[0], m[1]);
          const bool rssiOk = (r >= -127 && r <= -1);
          HbVerdict want;
          if (w == 0) want = HB_SKIP_WIFI;
          else if (!rssiOk) want = HB_SKIP_RSSI;
          else if (m[0] == m[1]) want = HB_SKIP_MIC;
          else want = HB_SEND;
          CHECK(v == want);
        }
      }
    }
    // 함정 고정: WiFi · RSSI 정상 + 마이크 정지 = 보내지 않는다
    CHECK(hbDecide(true, -55, 7, 7) == HB_SKIP_MIC);
    // 순서 고정: 둘 다 나쁘면 앞선 원인
    CHECK(hbDecide(false, 0, 7, 7) == HB_SKIP_WIFI);
    CHECK(hbDecide(true, 0, 7, 7) == HB_SKIP_RSSI);
    // RSSI 경계 4점
    CHECK(hbDecide(true, 0, 1, 0) == HB_SKIP_RSSI);
    CHECK(hbDecide(true, -1, 1, 0) == HB_SEND);
    CHECK(hbDecide(true, -127, 1, 0) == HB_SEND);
    CHECK(hbDecide(true, -128, 1, 0) == HB_SKIP_RSSI);
    CHECK(strcmp(hbVerdictName(HB_SEND), "send") == 0);
    CHECK(strcmp(hbVerdictName(HB_SKIP_WIFI), "wifi") == 0);
    CHECK(strcmp(hbVerdictName(HB_SKIP_RSSI), "rssi") == 0);
    CHECK(strcmp(hbVerdictName(HB_SKIP_MIC), "mic") == 0);
  }

  // T6 (I6) fw 규칙 — 상수 2개 + 경계
  {
    CHECK(hbFwValid(HB_FW_ENRICH_UPLINK));
    CHECK(hbFwValid(HB_FW_ENRICH_AUTOTRIG));
    CHECK(strcmp(HB_FW_ENRICH_UPLINK, "enrich_uplink") == 0);
    CHECK(strcmp(HB_FW_ENRICH_AUTOTRIG, "enrich_autotrig") == 0);
    CHECK(hbFwValid("aZ09_"));
    CHECK(hbFwValid("abcdefghijklmnopqrstuvwxyz012345"));     // 32자
    CHECK(!hbFwValid("abcdefghijklmnopqrstuvwxyz0123456"));   // 33자
    CHECK(!hbFwValid(""));
    CHECK(!hbFwValid(nullptr));
    CHECK(!hbFwValid("a-b"));
    CHECK(!hbFwValid("a b"));
    CHECK(!hbFwValid("\xea\xb0\x80"));   // 유니코드 글자(서버가 \w 대신 클래스를 명시한 이유)
  }

  // T7 (I6) 관계 대조 — 서버 실물을 텍스트로 읽는다(auto_trig_test T10 선례)
  {
    const std::string cs = readFile("server/app/constants.py");
    std::smatch m;
    CHECK(std::regex_search(cs, m, std::regex("(^|\\n)DEVICE_OFFLINE_AFTER = timedelta\\(seconds=(\\d+)\\)")));
    const long offlineS = std::stol(m[2]);
    CHECK(offlineS * 1000L >= 3L * (long)HB_PERIOD_MS);   // 연속 2회 유실까지 켜짐 유지
    CHECK(HB_WORST_CASE_MS < HB_PERIOD_MS);

    const std::string rs = readFile("server/app/routes.py");
    CHECK(std::regex_search(rs, m, std::regex("_FW_PATTERN = re\\.compile\\(r\"([^\"]+)\"\\)")));
    CHECK(m[1] == "[A-Za-z0-9_]{1,32}");
    CHECK(rs.find("_FW_PATTERN.fullmatch(fw)") != std::string::npos);
    CHECK(rs.find("_heartbeat_int(body, \"rssi\", -127, 0)") != std::string::npos);
    CHECK(HB_RSSI_MIN == -127 && HB_RSSI_MAX < 0);
    // 본문 필드 이름 5개가 서버가 읽는 이름과 같다
    CHECK(rs.find("body.get(\"device_id\")") != std::string::npos);
    CHECK(rs.find("_heartbeat_int(body, \"uptime_s\", 0)") != std::string::npos);
    CHECK(rs.find("_heartbeat_int(body, \"enrich_sent\", 0)") != std::string::npos);
    CHECK(rs.find("body.get(\"fw\")") != std::string::npos);
    char out[HB_JSON_BUF_BYTES];
    CHECK(hbBuildJson(out, sizeof(out), "d", -1, 0, "f", 0) > 0);
    for (const char* k : {"\"device_id\":", "\"rssi\":", "\"uptime_s\":", "\"fw\":", "\"enrich_sent\":"}) {
      CHECK(strstr(out, k) != nullptr);
    }

    // 보드가 싣는 device_id(UPLINK_DEVICE_ID — /detect 와 같은 값)가 조립을 통과한다
    const std::string uh = readFile("firmware/include/uplink_common.h");
    CHECK(std::regex_search(uh, m, std::regex("UPLINK_DEVICE_ID = \"([^\"]*)\";")));
    const std::string dev = m[1];
    CHECK(!dev.empty());
    CHECK(hbBuildJson(out, sizeof(out), dev.c_str(), -127, UINT32_MAX, HB_FW_ENRICH_AUTOTRIG, UINT32_MAX) > 0);
  }

  printf("heartbeat_wire_test: %d checks OK\n", checks);
  return 0;
}
