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

size_t uplinkBuildMultipart(uint8_t* dest, size_t destCapacity,
                            const char* clientRequestId, const char* deviceId,
                            const uint8_t* audioBytes, size_t audioLen) {
  char head[512];
  const int headLen = snprintf(
      head, sizeof(head),
      "--%s\r\n"
      "Content-Disposition: form-data; name=\"client_request_id\"\r\n\r\n"
      "%s\r\n"
      "--%s\r\n"
      "Content-Disposition: form-data; name=\"device_id\"\r\n\r\n"
      "%s\r\n"
      "--%s\r\n"
      "Content-Disposition: form-data; name=\"%s\"; filename=\"audio.pcm\"\r\n"
      "Content-Type: %s\r\n\r\n",
      UPLINK_BOUNDARY, clientRequestId, UPLINK_BOUNDARY, deviceId, UPLINK_BOUNDARY,
      UPLINK_AUDIO_FIELD, UPLINK_AUDIO_CONTENT_TYPE);

  // ── [uplink][defer] ToF 메타 4필드 전송: 미구현 (통합 env:prod 소관) ──
  //   현 상태 : 본 env는 마이크 단독이라 ToF 센서 상태 자체가 없다 → 4필드를 보내지 않는다.
  //             서버는 "4필드 전부 부재 = absent = 게이트 미적용(fail-open)"으로 처리하고
  //             응답 tof_check.reason 에 "tof_absent" 를 넣는다
  //             (server/app/tof_meta.py absent_meta()/evaluate_gate(), PR #43).
  //   붙일 자리: 위 snprintf 의 form field 블록 — client_request_id/device_id 와 **동형**으로
  //             tof_presence / tof_near_count / tof_center_mm / tof_motion_ndet 4개를 추가한다
  //             (파트명은 server/app/constants.py 의 TOF_*_FIELD 를 실grep 해 맞출 것).
  //   판정 방법: 통합 env 에서 4필드를 실어 보낸 뒤 **응답의 tof_check.reason 이 더 이상
  //             "tof_absent" 가 아니게 되는지**를 본다. 그대로 tof_absent 면 필드명 불일치나
  //             form field 미첨부이고, "presence=... near=.../64 ..." 텔레메트리 요약이 나오면
  //             수신 성공이다. "tof_invalid(...)" 면 값 표기가 서버 허용표 밖이다.
  //   ⚠️ 부분 전송 금지: tof_presence 없이 나머지만 보내면 서버가 invalid 로 떨어뜨린다.

  char tail[64];
  const int tailLen = snprintf(tail, sizeof(tail), "\r\n--%s--\r\n", UPLINK_BOUNDARY);

  if (headLen < 0 || static_cast<size_t>(headLen) >= sizeof(head) || tailLen < 0 ||
      static_cast<size_t>(tailLen) >= sizeof(tail)) {
    Serial.println("[uplink] multipart head/tail snprintf 잘림");
    return 0;
  }

  const size_t total = static_cast<size_t>(headLen) + audioLen + static_cast<size_t>(tailLen);
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
                             char* respOut, size_t respCapacity) {
  UplinkResult result{-1, 0};
  if (respOut != nullptr && respCapacity > 0) {
    respOut[0] = '\0';
  }

  const size_t bodyLen = uplinkBuildMultipart(bodyBuf, bodyBufCapacity, clientRequestId,
                                              UPLINK_DEVICE_ID, audioBytes, audioLen);
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
