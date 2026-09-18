// enrich_wire.h 호스트 검산 — 실제 firmware/include/enrich_wire.h 를 그대로 include 한다(복사 아님).
//   c++ -std=c++17 -Wall -I firmware/include -o /tmp/ewt firmware/tools/enrich_wire_test.cpp && /tmp/ewt
//
// 이 하네스가 지켜야 할 불변식 5개에 단언을 건다.
//   I1 multipart 파트 **이름**이 계약과 1:1 이고, 각 이름 뒤에 **그 파트의 바이트**가 온다  (NC-1)
//   I2 enrich_status 가 pending 이 아니면 **보내지 않는다**                                (NC-2)
//   I3 파싱 실패는 **기본값으로 떨어지지 않는다**(pending 폴백 금지)                        (NC-3)
//   I4 세션 상한 경계 = sent < 12 (12건을 이미 보냈으면 더 못 보낸다)                        (NC-4)
//   I5 2차 녹음 ≥ 5.000초 이고 서버 상한 이하                                              (NC-5)
//
// ⚠️ 단언 무딤 함정 (negative control 설계와 짝지어 둔다):
//   - I1 은 "이름만" 보면 image↔audio 스왑을 통과시킨다 → **이름 뒤의 바이트까지** 대조한다.
//     (파트 **순서**만 뒤집는 변형은 서버 계약상 무해할 수 있어 불변식으로 세우지 않는다 — 6.5(d).)
//   - I3 은 "부재"만 보면 **깨진 JSON**을 놓친다 → 잘린 바디·값 없는 키도 케이스로 둔다.
//   - I4 는 한 점만 보면 경계 뒤집기(<= vs <)를 통과시킨다 → 11·12·13 세 점을 본다.
//
// negative control 5종은 ENRICH_UPLINK_RUNBOOK.md 7절 참조 — 각각 반드시 실패해야 한다.
#include <cassert>
#include <cstdio>
#include <cstring>

#include "enrich_wire.h"

static int checks = 0;
#define CHECK(x) do { assert(x); checks++; } while (0)

static uint8_t g_dest[ENRICH_AUDIO_BYTES + 16384];

// 파트 헤더(`name="X"` 로 시작하는 파트)의 **본문 시작 오프셋**을 찾는다. 없으면 -1.
// 본문 = 파트 헤더 끝의 빈 줄(\r\n\r\n) 직후.
static long partBodyOffset(const uint8_t* buf, size_t len, const char* name) {
  char pat[64];
  snprintf(pat, sizeof(pat), "name=\"%s\"", name);
  for (size_t i = 0; i + strlen(pat) <= len; ++i) {
    if (memcmp(buf + i, pat, strlen(pat)) != 0) { continue; }
    for (size_t j = i; j + 4 <= len; ++j) {
      if (memcmp(buf + j, "\r\n\r\n", 4) == 0) { return (long)(j + 4); }
    }
    return -1;
  }
  return -1;
}

static size_t countOccurrences(const uint8_t* buf, size_t len, const char* needle) {
  const size_t n = strlen(needle);
  size_t       c = 0;
  for (size_t i = 0; i + n <= len; ++i) {
    if (memcmp(buf + i, needle, n) == 0) { ++c; }
  }
  return c;
}

// ── I1: multipart 조립 ───────────────────────────────────────────────────────
static void test_multipart() {
  // image / audio 의 바이트열을 **서로 구분 가능하게** 만든다 — 그래야 스왑이 검출된다.
  const uint8_t image[6] = {0xFF, 0xD8, 0xAA, 0xAA, 0xAA, 0xAA};
  const uint8_t audio[8] = {0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88};

  const size_t n = enrichBuildMultipart(g_dest, sizeof(g_dest), "e2-deadbeef-1", image,
                                        sizeof(image), audio, sizeof(audio));
  CHECK(n > 0);

  // 경계: 파트 3개 + 종결 = "--boundary" 4회 등장(종결은 "--boundary--")
  char bnd[64];
  snprintf(bnd, sizeof(bnd), "--%s", ENRICH_BOUNDARY);
  CHECK(countOccurrences(g_dest, n, bnd) == 4);
  char closing[72];
  snprintf(closing, sizeof(closing), "--%s--\r\n", ENRICH_BOUNDARY);
  CHECK(countOccurrences(g_dest, n, closing) == 1);
  // 종결 경계는 **맨 끝**에 있어야 한다
  CHECK(n >= strlen(closing));
  CHECK(memcmp(g_dest + n - strlen(closing), closing, strlen(closing)) == 0);

  // 파트 이름 3종이 각각 정확히 1회
  CHECK(countOccurrences(g_dest, n, "name=\"client_request_id\"") == 1);
  CHECK(countOccurrences(g_dest, n, "name=\"image\"") == 1);
  CHECK(countOccurrences(g_dest, n, "name=\"audio\"") == 1);
  // /enrich 계약상 device_id 는 **싣지 않는다**(6.5(b))
  CHECK(countOccurrences(g_dest, n, "name=\"device_id\"") == 0);

  // ★ I1 핵심: 이름 뒤에 **그 파트의 바이트**가 온다 (이름만 보면 스왑을 통과시킨다)
  const long idOff  = partBodyOffset(g_dest, n, "client_request_id");
  const long imgOff = partBodyOffset(g_dest, n, "image");
  const long audOff = partBodyOffset(g_dest, n, "audio");
  CHECK(idOff >= 0 && imgOff >= 0 && audOff >= 0);
  CHECK(memcmp(g_dest + idOff, "e2-deadbeef-1", 13) == 0);
  CHECK(memcmp(g_dest + imgOff, image, sizeof(image)) == 0);
  CHECK(memcmp(g_dest + audOff, audio, sizeof(audio)) == 0);
  // 스왑되면 이 두 단언이 깨진다(서로 다른 바이트열이라 교차 매치가 불가능하다)
  CHECK(memcmp(g_dest + imgOff, audio, sizeof(audio)) != 0);
  CHECK(memcmp(g_dest + audOff, image, sizeof(image)) != 0);

  // filename / Content-Type 도 계약분
  CHECK(countOccurrences(g_dest, n, "filename=\"shot.jpg\"") == 1);
  CHECK(countOccurrences(g_dest, n, "filename=\"audio.pcm\"") == 1);
  CHECK(countOccurrences(g_dest, n, "Content-Type: image/jpeg") == 1);
  CHECK(countOccurrences(g_dest, n, "Content-Type: application/octet-stream") == 1);

  // 길이: 총 바이트에 두 페이로드가 모두 들어 있다(둘 중 하나라도 빠지면 길이가 준다)
  CHECK(n > sizeof(image) + sizeof(audio));
  CHECK((size_t)imgOff + sizeof(image) <= n);
  CHECK((size_t)audOff + sizeof(audio) <= n);

  // ★ 용량 부족은 **자르지 않고 실패**한다 (잘린 바디 전송 금지)
  CHECK(enrichBuildMultipart(g_dest, n - 1, "e2-deadbeef-1", image, sizeof(image), audio,
                             sizeof(audio)) == 0);
  CHECK(enrichBuildMultipart(g_dest, 1, "e2-deadbeef-1", image, sizeof(image), audio,
                             sizeof(audio)) == 0);
  // 정확히 n 바이트면 성공한다(경계 off-by-one 확인)
  CHECK(enrichBuildMultipart(g_dest, n, "e2-deadbeef-1", image, sizeof(image), audio,
                             sizeof(audio)) == n);

  // null·빈 인자 거절
  CHECK(enrichBuildMultipart(nullptr, sizeof(g_dest), "x", image, sizeof(image), audio,
                             sizeof(audio)) == 0);
  CHECK(enrichBuildMultipart(g_dest, sizeof(g_dest), nullptr, image, sizeof(image), audio,
                             sizeof(audio)) == 0);
  CHECK(enrichBuildMultipart(g_dest, sizeof(g_dest), "x", nullptr, 4, audio, sizeof(audio)) == 0);
  CHECK(enrichBuildMultipart(g_dest, sizeof(g_dest), "x", image, 0, audio, sizeof(audio)) == 0);
  CHECK(enrichBuildMultipart(g_dest, sizeof(g_dest), "x", image, sizeof(image), nullptr, 8) == 0);
  CHECK(enrichBuildMultipart(g_dest, sizeof(g_dest), "x", image, sizeof(image), audio, 0) == 0);

  // 실제 크기(QVGA 5,438B 최대 + 5.120초 오디오)로도 조립된다
  static uint8_t big_audio[ENRICH_AUDIO_BYTES];
  static uint8_t big_image[5438];
  big_image[0] = 0xFF;
  big_image[1] = 0xD8;
  const size_t nb = enrichBuildMultipart(g_dest, sizeof(g_dest), "e2-deadbeef-2", big_image,
                                         sizeof(big_image), big_audio, sizeof(big_audio));
  CHECK(nb > ENRICH_AUDIO_BYTES);
  // 조립 오버헤드(경계·헤더)는 UPLINK_MULTIPART_OVERHEAD_BYTES(1024) 여유폭 안이다
  CHECK(nb - sizeof(big_image) - sizeof(big_audio) < 1024);
  const long imgOff2 = partBodyOffset(g_dest, nb, "image");
  const long audOff2 = partBodyOffset(g_dest, nb, "audio");
  CHECK(imgOff2 >= 0 && audOff2 >= 0);
  CHECK(memcmp(g_dest + imgOff2, big_image, sizeof(big_image)) == 0);
  CHECK(memcmp(g_dest + audOff2, big_audio, sizeof(big_audio)) == 0);
}

// ── I2 · I3: enrich_status 게이트 ────────────────────────────────────────────
// 입력 = server/app/models.py to_dict() 의 실제 형태. enrich_status 는 **notification_status
// 하위 중첩**이다(2026-09-18 실측) — 게이트가 계층에 무관하게 잡는지 여기서 확인한다.
static const char* kDetectPending =
    "{\"all_scores\":{\"doorbell\":0.97,\"fire_alarm\":0.02,\"knock\":0.01},"
    "\"client_request_id\":\"e2-89abcdef-1\",\"confidence\":0.97,"
    "\"detected_at\":\"2026-09-18T09:50:00.768+09:00\","
    "\"device_id\":\"ddingdong-mic-uplink-001\",\"media\":{\"audio_url\":null,"
    "\"image_thumbnail_url\":null,\"image_url\":null},\"notification_status\":"
    "{\"enrich_status\":\"pending\",\"primary_sent\":true,\"primary_sent_at\":null,"
    "\"secondary_sent\":false,\"secondary_sent_at\":null},"
    "\"predicted_class\":\"doorbell\",\"request_id\":\"req_01M26Z2QE24SFZJCMA3P2R7204\","
    "\"stt\":null,\"tof_check\":{\"applied\":true,\"passed\":true,\"reason\":\"tof_passed\"}}";

static const char* kDetectSkipped =
    "{\"client_request_id\":\"e2-89abcdef-2\",\"confidence\":0.51,\"notification_status\":"
    "{\"enrich_status\":\"skipped\",\"primary_sent\":false,\"primary_sent_at\":null,"
    "\"secondary_sent\":false,\"secondary_sent_at\":null,\"skip_reason\":\"low_confidence\"},"
    "\"predicted_class\":\"knock\"}";

static void test_gate() {
  CHECK(enrichGateFromDetectBody(kDetectPending) == ENRICH_GATE_PENDING);
  CHECK(enrichGateFromDetectBody(kDetectSkipped) == ENRICH_GATE_SKIP);

  // 서버가 낼 수 있는 나머지 어휘도 전부 skip 쪽이다 (routes.py: completed/failed/skipped)
  CHECK(enrichGateFromDetectBody("{\"enrich_status\":\"completed\"}") == ENRICH_GATE_SKIP);
  CHECK(enrichGateFromDetectBody("{\"enrich_status\":\"failed\"}") == ENRICH_GATE_SKIP);
  // 처음 보는 값도 **보내지 않는다**(모르는 값을 pending 으로 읽지 않는다)
  CHECK(enrichGateFromDetectBody("{\"enrich_status\":\"whatever\"}") == ENRICH_GATE_SKIP);
  // 접두·접미가 다른 값은 pending 이 아니다(부분일치 금지)
  CHECK(enrichGateFromDetectBody("{\"enrich_status\":\"pending_x\"}") == ENRICH_GATE_SKIP);
  CHECK(enrichGateFromDetectBody("{\"enrich_status\":\"unpending\"}") == ENRICH_GATE_SKIP);

  // ★ I3: 파싱 실패는 **그 자체 상태**다. pending 도 skip 도 아니다.
  const EnrichGate missing = enrichGateFromDetectBody("{\"predicted_class\":\"knock\"}");
  CHECK(missing == ENRICH_GATE_PARSE_FAIL);
  CHECK(missing != ENRICH_GATE_PENDING);   // pending 폴백 금지 (NC-3)
  CHECK(enrichGateFromDetectBody("") == ENRICH_GATE_PARSE_FAIL);
  CHECK(enrichGateFromDetectBody(nullptr) == ENRICH_GATE_PARSE_FAIL);
  // 깨진 JSON: 키 이름이 잘렸다
  CHECK(enrichGateFromDetectBody("{\"notification_status\":{\"enrich_stat") ==
        ENRICH_GATE_PARSE_FAIL);
  // 깨진 JSON: 키는 있으나 값이 비었다
  CHECK(enrichGateFromDetectBody("{\"enrich_status\":\"\"}") == ENRICH_GATE_PARSE_FAIL);
  CHECK(enrichGateFromDetectBody("{\"enrich_status\":") == ENRICH_GATE_PARSE_FAIL);
  // 에러 바디(4xx/5xx)에도 이 키가 없다 → 미발송
  CHECK(enrichGateFromDetectBody("{\"error\":\"rate_limited\",\"retry_after\":5}") ==
        ENRICH_GATE_PARSE_FAIL);

  // 게이트 이름 3종이 서로 구분된다(로그가 세 상태를 갈라 적을 수 있어야 한다)
  CHECK(strcmp(enrichGateName(ENRICH_GATE_PENDING), "pending") == 0);
  CHECK(strcmp(enrichGateName(ENRICH_GATE_SKIP), "skip") == 0);
  CHECK(strcmp(enrichGateName(ENRICH_GATE_PARSE_FAIL), "parsefail") == 0);
}

static void test_json_peek() {
  char v[16];
  CHECK(enrichPeekJson(kDetectPending, "predicted_class", v, sizeof(v)));
  CHECK(strcmp(v, "doorbell") == 0);
  CHECK(enrichPeekJson(kDetectPending, "confidence", v, sizeof(v)));
  CHECK(strcmp(v, "0.97") == 0);
  // "skip_reason" 이 "enrich_status" 를 오매치하지 않는다
  CHECK(enrichPeekJson(kDetectSkipped, "enrich_status", v, sizeof(v)));
  CHECK(strcmp(v, "skipped") == 0);
  CHECK(!enrichPeekJson(kDetectPending, "no_such_key", v, sizeof(v)));
  CHECK(!enrichPeekJson(nullptr, "confidence", v, sizeof(v)));
  CHECK(!enrichPeekJson(kDetectPending, "confidence", nullptr, sizeof(v)));
  CHECK(!enrichPeekJson(kDetectPending, "confidence", v, 0));
  // 버퍼가 작으면 잘려서 들어오되 NUL 종료는 지킨다(넘어 쓰지 않는다)
  char tiny[4];
  CHECK(enrichPeekJson(kDetectPending, "predicted_class", tiny, sizeof(tiny)));
  CHECK(strlen(tiny) == 3);
  CHECK(strcmp(tiny, "doo") == 0);
}

// ── I4: 세션 상한 ────────────────────────────────────────────────────────────
static void test_session_cap() {
  CHECK(ENRICH_SESSION_MAX_EVENTS == 12);
  CHECK(enrichSessionAllows(0));
  CHECK(enrichSessionAllows(11));            // 11건 보냈다 → 12번째 허용
  CHECK(!enrichSessionAllows(12));           // 12건 보냈다 → 더 못 보낸다 (경계, NC-4)
  CHECK(!enrichSessionAllows(13));
  CHECK(!enrichSessionAllows(0xFFFFFFFFu));
  // 상한까지 실제로 세어 본다: 정확히 12번만 통과해야 한다
  uint32_t sent = 0, passed = 0;
  for (int i = 0; i < 50; ++i) {
    if (enrichSessionAllows(sent)) { passed++; sent++; }
  }
  CHECK(passed == 12);
  CHECK(sent == 12);
}

// ── I5: 2차 녹음 길이 불변식 ─────────────────────────────────────────────────
// ⚠️ enrich_wire.h 에 같은 불변식이 static_assert 로도 박혀 있다 — 그쪽은 **컴파일 단계**에서
//    잡고, 여기는 static_assert 를 지운 변형까지 잡는다(가드 2중화).
static void test_audio_len() {
  CHECK(ENRICH_AUDIO_BUFFERS == 80);
  CHECK(ENRICH_AUDIO_SAMPLES == 81920);
  CHECK(ENRICH_AUDIO_BYTES == 163840);
  CHECK(ENRICH_AUDIO_MS == 5120);
  CHECK(ENRICH_AUDIO_MS >= 5000);                              // I-A (NC-5)
  CHECK(ENRICH_AUDIO_BYTES <= ENRICH_SERVER_AUDIO_MAX_BYTES);  // I-B
  // 산술 재검산: 버퍼 수 × DMA 버퍼 길이 × 2B 가 바이트 수이고, 샘플/레이트가 시간이다
  CHECK(ENRICH_AUDIO_SAMPLES == (size_t)ENRICH_AUDIO_BUFFERS * ENRICH_AUDIO_DMA_BUF_LEN);
  CHECK(ENRICH_AUDIO_BYTES == ENRICH_AUDIO_SAMPLES * 2);
  CHECK(ENRICH_AUDIO_MS == ENRICH_AUDIO_SAMPLES * 1000 / ENRICH_AUDIO_SAMPLE_RATE);
  // 정수 버퍼 수다 = 부분 버퍼 처리 분기가 필요 없다(6.3(h) 선례)
  CHECK(ENRICH_AUDIO_SAMPLES % ENRICH_AUDIO_DMA_BUF_LEN == 0);
  // 서버 상한 대비 점유율 = 51.2%. (⚠️ 2배는 상한을 넘는다 — PR-C 가 길이를 늘릴 여지는
  // 5.120 → 최대 10.0초 구간이지 "두 배"가 아니다. 6.5(a) 산술과 일치.)
  CHECK(ENRICH_AUDIO_BYTES * 100 / ENRICH_SERVER_AUDIO_MAX_BYTES == 51);
  // 파트 크기 상수가 서버 constants.py 실값과 같다
  CHECK(ENRICH_SERVER_AUDIO_MAX_BYTES == 320000);
  CHECK(ENRICH_SERVER_IMAGE_MAX_BYTES == 512000);
  // 파트 이름이 서버 필드명과 1:1
  CHECK(strcmp(ENRICH_IMAGE_FIELD, "image") == 0);
  CHECK(strcmp(ENRICH_AUDIO_FIELD, "audio") == 0);
}

int main() {
  test_multipart();
  test_gate();
  test_json_peek();
  test_session_cap();
  test_audio_len();
  printf("enrich_wire_test: %d checks passed\n", checks);
  return 0;
}
