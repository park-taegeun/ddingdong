// jsonPeek 호스트 검증 — mic_uplink_main.cpp 의 함수 본문을 그대로 복사해 실행한다.
// 입력 = server/app/routes.py 가 실제로 반환한 201 응답 바디(test_client 실측 캡처).
#include <cstdio>
#include <cstring>
#include <cassert>

static bool jsonPeek(const char* body, const char* key, char* out, size_t cap) {
  char pat[32];
  snprintf(pat, sizeof(pat), "\"%s\":", key);
  const char* p = strstr(body, pat);
  if (p == nullptr) { return false; }
  p += strlen(pat);
  while (*p == ' ') { ++p; }
  const bool quoted = (*p == '"');
  if (quoted) { ++p; }
  size_t i = 0;
  while (*p != '\0' && i + 1 < cap) {
    if (quoted ? (*p == '"') : (*p == ',' || *p == '}' || *p == ' ')) { break; }
    out[i++] = *p++;
  }
  out[i] = '\0';
  return i > 0;
}

int main() {
  // ① 실측 캡처 (Flask compact separators = 콜론 뒤 공백 없음)
  const char* real =
    "{\"all_scores\":{\"doorbell\":0.05,\"fire_alarm\":0.44,\"knock\":0.51},"
    "\"client_request_id\":\"m5d-89abcdef-1\",\"confidence\":0.51,"
    "\"detected_at\":\"2026-09-11T09:50:00.768+09:00\","
    "\"device_id\":\"ddingdong-mic-uplink-001\",\"media\":{\"audio_url\":null,"
    "\"image_thumbnail_url\":null,\"image_url\":null},\"notification_status\":"
    "{\"enrich_status\":\"skipped\",\"primary_sent\":false,\"primary_sent_at\":null,"
    "\"secondary_sent\":false,\"secondary_sent_at\":null,\"skip_reason\":\"low_confidence\"},"
    "\"predicted_class\":\"knock\",\"request_id\":\"req_01M26Z2QE24SFZJCMA3P2R7204\","
    "\"stt\":null,\"tof_check\":{\"applied\":false,\"passed\":null,\"reason\":\"tof_absent\"}}";
  char cls[16] = "?", conf[8] = "?", tof[24] = "?";
  assert(jsonPeek(real, "predicted_class", cls, sizeof(cls)));
  assert(jsonPeek(real, "confidence", conf, sizeof(conf)));
  assert(jsonPeek(real, "reason", tof, sizeof(tof)));
  assert(strcmp(cls, "knock") == 0);
  assert(strcmp(conf, "0.51") == 0);
  // ★ 핵심: "skip_reason":"low_confidence" 가 "reason" 보다 **앞에** 있는데도
  //   선행 큰따옴표가 달라 오매치되지 않는다.
  assert(strcmp(tof, "tof_absent") == 0);

  // ② 콜론 뒤 공백이 있는 변형(jsonify 설정이 바뀌어도 견디는지)
  const char* spaced = "{\"confidence\": 0.97, \"tof_check\": {\"reason\": \"presence=true\"}}";
  assert(jsonPeek(spaced, "confidence", conf, sizeof(conf)) && strcmp(conf, "0.97") == 0);
  assert(jsonPeek(spaced, "reason", tof, sizeof(tof)) && strcmp(tof, "presence=true") == 0);

  // ③ negative control — 키 부재 시 false, out 미오염("?" 유지 → 로그에 물음표로 드러남)
  char miss[8] = "?";
  assert(!jsonPeek(real, "nonexistent_key", miss, sizeof(miss)));
  assert(strcmp(miss, "?") == 0);

  // ④ negative control — 429/401 에러 바디(errors.py 형태)에는 3필드가 없다
  const char* err = "{\"error\":{\"code\":\"rate_limited\",\"message\":\"5초당 1회만 허용됩니다.\"}}";
  char c2[16] = "?";
  assert(!jsonPeek(err, "predicted_class", c2, sizeof(c2)) && strcmp(c2, "?") == 0);

  // ⑤ negative control — cap 초과 시 잘리되 NUL 종료는 보장(버퍼 오버런 없음)
  char tiny[4] = "?";
  assert(jsonPeek(real, "predicted_class", tiny, sizeof(tiny)));
  assert(strcmp(tiny, "kno") == 0);

  printf("jsonPeek: 5 groups OK (cls=%s conf=%s tof=%s)\n", cls, conf, tof);
  return 0;
}
