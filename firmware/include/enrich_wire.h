// 띵동 firmware - 2차 체인(`/enrich`) wire 순수 계층 (2026-09-18, env:enrich_uplink)
//
// ★ 성격 = **배관(plumbing)**. 새 판정 기준·임계값·상태 어휘 0개다.
//   `enrich_status` 는 서버(`server/app/models.py` to_dict)가 이미 내는 값이고, 본 헤더는
//   그것을 **읽어서 분기만** 한다. 보드가 새로 판정하는 것은 하나도 없다.
//
// ★ 왜 Arduino 무의존 순수 헤더인가 (probe_stats.h 선례와 같은 축)
//   호스트 테스트(firmware/tools/enrich_wire_test.cpp)가 **같은 파일을 그대로** 컴파일해
//   검산한다(복사 아님). `uplink_common.h` 에 넣을 수 없는 이유는 실측이다 —
//   그 헤더는 mic_common.h → "driver/i2s.h" 를 끌어와 **호스트에서 컴파일되지 않는다**
//   (2026-09-18 실측: fatal error: 'driver/i2s.h' file not found). 전송 코드(HTTPClient·WiFi·
//   secrets)는 uplink_common.cpp 에 남기고, **바이트열을 만드는 함수만** 여기로 분리했다.
//
// ★ 여기에 없는 것
//   - 재시도 로직 (1차와 동일하게 **재시도 0**)
//   - 기본값 폴백 (파싱 실패 = 미발송. "아무도 안 줬을 때 조용히 뭔가를 고르는" 구조 금지)
//   - RMS·임계 비교 (트리거는 수동 's' 키 — M5-c 소관 미접촉)
#pragma once

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

// ── multipart 계약 (server/app/routes.py enrich() + constants.py 실측, 6.5(b) 표) ─────
//   필수 form field = client_request_id **1개뿐**. device_id 는 /enrich 에 **불요**다
//   (/detect 와 다르다 — 6.5(b) "★ device_id는 불요"). 파일 파트 image + audio 둘 다 required.
constexpr const char* ENRICH_BOUNDARY           = "ddingdongEnrichUplinkBoundary7A3F1";
constexpr const char* ENRICH_IMAGE_FIELD        = "image";   // = server IMAGE_FILE_FIELD
constexpr const char* ENRICH_AUDIO_FIELD        = "audio";   // = server AUDIO_FILE_FIELD
constexpr const char* ENRICH_IMAGE_CONTENT_TYPE = "image/jpeg";
constexpr const char* ENRICH_AUDIO_CONTENT_TYPE = "application/octet-stream";

// 서버 크기 상한 (server/app/constants.py 실grep 값 — 보드가 새로 정하는 값이 아니다).
constexpr size_t ENRICH_SERVER_AUDIO_MAX_BYTES = 320000;
constexpr size_t ENRICH_SERVER_IMAGE_MAX_BYTES = 512000;

// ── 2차 오디오 버퍼 길이 (§2-2(b): 값이 아니라 **불변식**이 먼저다) ────────────────
// 불변식 I-A: 실제 녹음 길이 **≥ 5.000초**
// 불변식 I-B: 바이트 수 **≤ ENRICH_SERVER_AUDIO_MAX_BYTES**
//
// ★ 왜 정수 버퍼 수인가: 5.000초 = 80,000 샘플 = MIC_DMA_BUF_LEN(1024) 의 **78.125 버퍼**로
//   정수배가 아니다. 부분 버퍼를 처리하는 분기를 만들면 그 분기 자체가 새 결함면이 된다 —
//   `MIC_RING_SLOTS=32` 가 2.000초(31.25버퍼) 대신 2.048초를 택한 이유와 같다(6.3(h)).
//   ⇒ 80 버퍼로 **올린다**. 79(5.056초)도 불변식을 만족하나 80 이 160 KiB 정수이고 여유가 크다.
//
// 산술: 80 버퍼 × 1,024 샘플 = 81,920 샘플 = 163,840 B = 5.120초 = 상한의 **51.2%**.
//
// ⚠️ 아래 1024·16000 은 mic_common.h 의 MIC_DMA_BUF_LEN · MIC_SAMPLE_RATE_HZ 와 **같은 값**이어야
//   한다. 이 헤더는 호스트 컴파일을 위해 그 헤더를 include 하지 않으므로, 두 값이 갈라지면
//   여기서는 드러나지 않는다 → **묶는 static_assert 는 uplink_common.h 가 건다**(보드 빌드에서 강제).
constexpr uint32_t ENRICH_AUDIO_BUFFERS       = 80;
constexpr uint32_t ENRICH_AUDIO_DMA_BUF_LEN   = 1024;   // ↔ MIC_DMA_BUF_LEN
constexpr uint32_t ENRICH_AUDIO_SAMPLE_RATE   = 16000;  // ↔ MIC_SAMPLE_RATE_HZ
constexpr size_t   ENRICH_AUDIO_SAMPLES =
    (size_t)ENRICH_AUDIO_BUFFERS * (size_t)ENRICH_AUDIO_DMA_BUF_LEN;
constexpr size_t   ENRICH_AUDIO_BYTES = ENRICH_AUDIO_SAMPLES * sizeof(int16_t);
constexpr uint32_t ENRICH_AUDIO_MS =
    (uint32_t)(ENRICH_AUDIO_SAMPLES * 1000u / ENRICH_AUDIO_SAMPLE_RATE);

static_assert(ENRICH_AUDIO_MS >= 5000, "I-A: 2차 녹음은 5.000초 이상이어야 한다");
static_assert(ENRICH_AUDIO_BYTES <= ENRICH_SERVER_AUDIO_MAX_BYTES,
              "I-B: 2차 오디오는 서버 AUDIO_MAX_BYTES 를 넘을 수 없다");

// ── 세션 과금 상한 (§2-1 ⑧ / 6.5(e) 「1세션 ≤12 이벤트」) ──────────────────────────
// 근거 = CSR 180초 = 일 한도 600초의 30%(30.9 「스위트 1회 = 12건 = 180초」와 같은 단위).
// 카톡 ≤36건은 12×3 **파생값**이라 상수를 따로 두지 않는다(죽은 상수 금지).
constexpr uint32_t ENRICH_SESSION_MAX_EVENTS = 12;

// sent = 이번 세션에 **이미 보낸** 2차 이벤트 수. 상한에 닿으면 false.
// ⚠️ 경계: sent == MAX 면 이미 12건을 보냈으므로 **보내면 안 된다**(< 이지 <= 가 아니다).
inline bool enrichSessionAllows(uint32_t sent) { return sent < ENRICH_SESSION_MAX_EVENTS; }

// ── /detect 응답 JSON 얕은 추출 ──────────────────────────────────────────────────
// mic_uplink_main.cpp 의 static jsonPeek 와 같은 방식이다. 공용화하지 않은 이유 = 그 파일이
// **무변경 대상**(§3)이라 심볼을 옮기면 회귀 증명이 필요해진다. 여기서는 호스트 검산이 가능한
// 순수 형태로 다시 둔다(§3 무변경 제약 > 중복 제거).
// ★ 계층 무관: `"key":` 를 strstr 로 찾으므로 `enrich_status` 가 `notification_status` **하위**
//   여도 잡힌다(2026-09-18 models.py to_dict 실측 = 하위 중첩). jsonpeek_test.cpp 의 실측
//   캡처 바디가 정확히 그 중첩 형태이고 거기서 동작이 이미 증명돼 있다.
// 못 찾으면 false — 호출부가 **조용히 틀린 값을 만들지 않는다**.
inline bool enrichPeekJson(const char* body, const char* key, char* out, size_t cap) {
  if (body == nullptr || key == nullptr || out == nullptr || cap == 0) { return false; }
  char pat[40];
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

// ── 2차 게이트 (§2-1 ① S1 직렬 / ⑤ skip = 미발송 / 덤) 파싱 실패 = 미발송) ────────
// 서버 어휘("pending" / "skipped" / …)를 **그대로** 읽는다. 보드가 만드는 상태 어휘 0개.
enum EnrichGate {
  ENRICH_GATE_PENDING,     // 2차 진행
  ENRICH_GATE_SKIP,        // enrich_status 가 pending 이 아님 → 미발송(409·404 생산 회피)
  ENRICH_GATE_PARSE_FAIL,  // 키 부재·잘린 바디·깨진 JSON → 미발송
};

// ★ 기본값 폴백을 두지 않는다. 「모르면 보낸다」도 「모르면 pending 으로 친다」도 금지다 —
//   기본값 fallback 은 이 프로젝트의 반복 사고 원형이다(NC-3 가 이 불변식을 본다).
inline EnrichGate enrichGateFromDetectBody(const char* body) {
  char v[16];
  if (!enrichPeekJson(body, "enrich_status", v, sizeof(v))) { return ENRICH_GATE_PARSE_FAIL; }
  return (strcmp(v, "pending") == 0) ? ENRICH_GATE_PENDING : ENRICH_GATE_SKIP;
}

inline const char* enrichGateName(EnrichGate g) {
  switch (g) {
    case ENRICH_GATE_PENDING: return "pending";
    case ENRICH_GATE_SKIP:    return "skip";
    default:                  return "parsefail";
  }
}

// ── multipart 바디 조립 (순수 — 호스트 검산 대상) ────────────────────────────────
// 파트 순서 = client_request_id(form field) → image(file) → audio(file).
// 반환 = 조립된 총 바이트. **0 = 실패**이며 호출부가 전송을 중단한다(잘린 바디 전송 금지).
//
// ⚠️ 파트 **이름**이 뒤바뀌면 서버는 image 파트에서 SOI 를 검사하다 400 을 낸다(NC-1).
//    파트 **순서**만 뒤집는 것은 서버 계약상 무해할 수 있다(6.5(d) 함정 예고) — 그래서 순서는
//    불변식으로 세우지 않고, 이름·길이·경계만 단언한다.
inline size_t enrichBuildMultipart(uint8_t* dest, size_t destCapacity,
                                   const char* clientRequestId,
                                   const uint8_t* imageBytes, size_t imageLen,
                                   const uint8_t* audioBytes, size_t audioLen) {
  if (dest == nullptr || clientRequestId == nullptr || imageBytes == nullptr ||
      audioBytes == nullptr || imageLen == 0 || audioLen == 0) {
    return 0;
  }

  char         head[512];
  const int    headN = snprintf(head, sizeof(head),
                             "--%s\r\n"
                             "Content-Disposition: form-data; name=\"client_request_id\"\r\n\r\n"
                             "%s\r\n"
                             "--%s\r\n"
                             "Content-Disposition: form-data; name=\"%s\"; filename=\"shot.jpg\"\r\n"
                             "Content-Type: %s\r\n\r\n",
                             ENRICH_BOUNDARY, clientRequestId, ENRICH_BOUNDARY,
                             ENRICH_IMAGE_FIELD, ENRICH_IMAGE_CONTENT_TYPE);
  if (headN < 0 || (size_t)headN >= sizeof(head)) { return 0; }  // 잘림 = 실패

  char      mid[256];
  const int midN = snprintf(mid, sizeof(mid),
                            "\r\n--%s\r\n"
                            "Content-Disposition: form-data; name=\"%s\"; filename=\"audio.pcm\"\r\n"
                            "Content-Type: %s\r\n\r\n",
                            ENRICH_BOUNDARY, ENRICH_AUDIO_FIELD, ENRICH_AUDIO_CONTENT_TYPE);
  if (midN < 0 || (size_t)midN >= sizeof(mid)) { return 0; }

  char      tail[64];
  const int tailN = snprintf(tail, sizeof(tail), "\r\n--%s--\r\n", ENRICH_BOUNDARY);
  if (tailN < 0 || (size_t)tailN >= sizeof(tail)) { return 0; }

  const size_t total = (size_t)headN + imageLen + (size_t)midN + audioLen + (size_t)tailN;
  if (total > destCapacity) { return 0; }  // ★ 넘치면 **자르지 않고** 실패시킨다

  size_t cursor = 0;
  memcpy(dest + cursor, head, (size_t)headN);       cursor += (size_t)headN;
  memcpy(dest + cursor, imageBytes, imageLen);      cursor += imageLen;
  memcpy(dest + cursor, mid, (size_t)midN);         cursor += (size_t)midN;
  memcpy(dest + cursor, audioBytes, audioLen);      cursor += audioLen;
  memcpy(dest + cursor, tail, (size_t)tailN);       cursor += (size_t)tailN;
  return cursor;
}
