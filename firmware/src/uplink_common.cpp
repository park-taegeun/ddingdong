// 띵동 firmware - 마이크 2초 스냅샷 업로드 공통 구현 (2026-09-11, M5-d)
//
// ★ 복제 출처 (decisions.md 6.3(l) ② "복제해 신설 uplink_common.cpp로 옮긴다")
//   firmware/src/upload_spike_common.cpp (프로즌, 본 PR 무수정) 의 다음 4개 함수:
//     allocPsramBuffer   → uplinkAllocPsram      (로그 태그만 [uplink] 로 교체)
//     tryConnect         → tryConnect            (static, 상수 이름만 UPLINK_* 로 교체)
//     connectWifiBlocking→ uplinkConnectWifi     (동일)
//     buildMultipartBody → uplinkBuildMultipart  (동일 — 서버 계약이 같으므로 구조 동일)
//     postAudioSpike     → uplinkPostAudio       (연결 분리 계측 제거 + 응답 바디 반환 추가)
//
// ★ 하네스 전용이라 복제하지 않은 것: synthesizeSineInt16 / connectMs 분리 계측 /
//   SpikeResult.ok(201 고정 판정 — 본 PR은 상태 코드를 그대로 로그에 흘린다).

#include "uplink_common.h"

#include <string.h>

#include <HTTPClient.h>
#include <WiFi.h>

#include "esp_heap_caps.h"
#include "esp_timer.h"
#include "secrets.h"

uint8_t* uplinkAllocPsram(size_t bytes, const char* tag) {
  uint8_t* buf = static_cast<uint8_t*>(heap_caps_malloc(bytes, MALLOC_CAP_SPIRAM));
  if (buf == nullptr) {
    Serial.printf("[uplink] PSRAM alloc FAILED tag=%s bytes=%u\n", tag,
                  static_cast<unsigned>(bytes));
  } else {
    Serial.printf("[uplink] PSRAM alloc OK tag=%s bytes=%u\n", tag,
                  static_cast<unsigned>(bytes));
  }
  return buf;
}

// env:poc(main.cpp)의 이벤트 기반 재연결/backoff 를 흡수하지 않는다 — §7 리팩토링 금지
// 제약이 원본과 동일하게 걸려 있어, 원본이 택한 "최소 블로킹 연결 자체 구현"을 그대로 복제.
static bool tryConnect(const char* ssid, const char* password, uint32_t timeoutMs) {
  Serial.printf("[uplink] WiFi trying SSID=%s (timeout=%ums)\n", ssid,
                static_cast<unsigned>(timeoutMs));
  WiFi.begin(ssid, password);
  const uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - start) < timeoutMs) {
    delay(UPLINK_WIFI_POLL_INTERVAL_MS);
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.printf("[uplink] WiFi timeout SSID=%s\n", ssid);
    return false;
  }
  return true;
}

bool uplinkConnectWifi() {
  WiFi.mode(WIFI_STA);
  if (tryConnect(WIFI_PRIMARY_SSID, WIFI_PRIMARY_PASSWORD, UPLINK_WIFI_PRIMARY_TIMEOUT_MS) ||
      tryConnect(WIFI_FALLBACK_SSID, WIFI_FALLBACK_PASSWORD, UPLINK_WIFI_FALLBACK_TIMEOUT_MS)) {
    Serial.printf("[uplink] WiFi connected SSID=%s RSSI=%d IP=%s\n", WiFi.SSID().c_str(),
                  static_cast<int>(WiFi.RSSI()), WiFi.localIP().toString().c_str());
    return true;
  }
  Serial.println("[uplink] WiFi both SSIDs failed (u.FL 외장 안테나 확인, 카테고리 32)");
  return false;
}

// form field 파트 1개를 head 끝에 이어 쓴다. 반환 = 누적 길이(잘림·오류 시 cap 이상 → 호출부 가드).
static size_t appendField(char* head, size_t cap, size_t len, const char* name, const char* value) {
  if (len >= cap) {
    return cap;
  }
  const int n = snprintf(head + len, cap - len,
                         "--%s\r\n"
                         "Content-Disposition: form-data; name=\"%s\"\r\n\r\n"
                         "%s\r\n",
                         UPLINK_BOUNDARY, name, value);
  return (n < 0) ? cap : len + static_cast<size_t>(n);
}

size_t uplinkBuildMultipart(uint8_t* dest, size_t destCapacity,
                            const char* clientRequestId, const char* deviceId,
                            const uint8_t* audioBytes, size_t audioLen,
                            const TofFrameResult* tof) {
  // head 조립 순서 = client_request_id / device_id / [ToF 4필드] / audio 파트 헤더.
  // tof==nullptr 이면 PR #52 의 단일 snprintf 와 **같은 바이트열**이 나온다(파트 문자열 동일, 순서 동일).
  char   head[1024];
  size_t headLen = 0;
  headLen = appendField(head, sizeof(head), headLen, "client_request_id", clientRequestId);
  headLen = appendField(head, sizeof(head), headLen, "device_id", deviceId);

  // ── ToF 메타 4필드 (decisions.md 6.2 G10 / 6.4, PoC-(45) 송신측) ──
  //   파트명 = server/app/constants.py:151~154 TOF_*_FIELD 실grep 값 그대로(신규 필드 0).
  //   값 표기 = tof_meta.py 허용표: presence "true"/"false" / 정수는 십진 문자열.
  //   ★ tof_presence ↔ 펌웨어 신호 매핑 = **fused**(presence_state && motion latch). 근거 =
  //     6.4(b) "Stage A 디바운스 3프레임(9.2)과 Stage B-2 latch 75프레임(9.4)은 시간축 판정이라
  //     … presence는 펌웨어가 판정한 결과를 그대로 신뢰" — 두 계층을 모두 거친 값이 presence 다.
  //   ★ 부분 전송 금지(tof_presence 없이 나머지만 = invalid): presence 는 항상 싣는다.
  //     center 만 예외 — center 4 zone 전부 무효(로그 "n/a")면 파트를 생략 → 서버 telemetry n/a.
  if (tof != nullptr) {
    char num[8];
    headLen = appendField(head, sizeof(head), headLen, "tof_presence", tof->fused ? "true" : "false");
    snprintf(num, sizeof(num), "%u", static_cast<unsigned>(tof->near_count));
    headLen = appendField(head, sizeof(head), headLen, "tof_near_count", num);
    if (tof->center_valid) {
      snprintf(num, sizeof(num), "%u", static_cast<unsigned>(tof->center_mm));
      headLen = appendField(head, sizeof(head), headLen, "tof_center_mm", num);
    }
    snprintf(num, sizeof(num), "%u", static_cast<unsigned>(tof->motion_ndet));
    headLen = appendField(head, sizeof(head), headLen, "tof_motion_ndet", num);
  }

  if (headLen < sizeof(head)) {
    const int n = snprintf(head + headLen, sizeof(head) - headLen,
                           "--%s\r\n"
                           "Content-Disposition: form-data; name=\"%s\"; filename=\"audio.pcm\"\r\n"
                           "Content-Type: %s\r\n\r\n",
                           UPLINK_BOUNDARY, UPLINK_AUDIO_FIELD, UPLINK_AUDIO_CONTENT_TYPE);
    headLen = (n < 0) ? sizeof(head) : headLen + static_cast<size_t>(n);
  }

  char tail[64];
  const int tailLen = snprintf(tail, sizeof(tail), "\r\n--%s--\r\n", UPLINK_BOUNDARY);

  if (headLen >= sizeof(head) || tailLen < 0 || static_cast<size_t>(tailLen) >= sizeof(tail)) {
    Serial.println("[uplink] multipart head/tail snprintf 잘림");
    return 0;
  }

  const size_t total = headLen + audioLen + static_cast<size_t>(tailLen);
  if (total > destCapacity) {
    Serial.printf("[uplink] multipart build FAILED (need=%u cap=%u)\n",
                  static_cast<unsigned>(total), static_cast<unsigned>(destCapacity));
    return 0;
  }

  size_t cursor = 0;
  memcpy(dest + cursor, head, headLen);
  cursor += headLen;
  memcpy(dest + cursor, audioBytes, audioLen);
  cursor += audioLen;
  memcpy(dest + cursor, tail, tailLen);
  cursor += tailLen;
  return cursor;
}

UplinkResult uplinkPostAudio(const char* host, uint16_t port,
                             const char* clientRequestId,
                             const uint8_t* audioBytes, size_t audioLen,
                             uint8_t* bodyBuf, size_t bodyBufCapacity,
                             char* respOut, size_t respCapacity,
                             const TofFrameResult* tof) {
  UplinkResult result{-1, 0};
  if (respOut != nullptr && respCapacity > 0) {
    respOut[0] = '\0';
  }

  const size_t bodyLen = uplinkBuildMultipart(bodyBuf, bodyBufCapacity, clientRequestId,
                                              UPLINK_DEVICE_ID, audioBytes, audioLen, tof);
  if (bodyLen == 0) {
    return result;
  }

  WiFiClient client;
  HTTPClient http;
  http.setTimeout(UPLINK_HTTP_TIMEOUT_MS);
  const String url = String("http://") + host + ":" + String(port) + "/api/v1/detect";
  if (!http.begin(client, url)) {
    Serial.println("[uplink] HTTPClient begin() failed");
    return result;
  }
  http.addHeader("Content-Type", String("multipart/form-data; boundary=") + UPLINK_BOUNDARY);
  // 카테고리 6.1 Device Bearer Token. secrets.h 매크로 재사용(실값 커밋 금지).
  http.addHeader("Authorization", String("Bearer ") + SPIKE_DEVICE_TOKEN);

  const int64_t t0 = esp_timer_get_time();
  const int status = http.POST(bodyBuf, bodyLen);
  const int64_t tEnd = esp_timer_get_time();

  result.httpStatus = status;
  result.roundTripMs = static_cast<uint32_t>((tEnd - t0) / 1000);

  if (status > 0) {
    const String body = http.getString();  // 드레인 겸 요약 추출 원본
    if (respOut != nullptr && respCapacity > 0) {
      strlcpy(respOut, body.c_str(), respCapacity);
    }
  }
  http.end();
  return result;
}
