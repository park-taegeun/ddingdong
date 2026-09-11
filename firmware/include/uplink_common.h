// 띵동 firmware - 마이크 2초 스냅샷 업로드 공통 헤더 (2026-09-11, M5-d)
//
// 성격 = **배관(plumbing)**. 새 판정 기준·임계값·상태 어휘 0개.
// 마이크 링버퍼(M5-a, 프로즌 mic_common)와 서버 `/detect`(PR #24 수신 배선) 사이에
// 송신 코드가 0줄이던 구간(decisions.md 6.2/6.4 "G10 수신측 CLOSE ≠ G10 CLOSE")을 잇는다.
//
// ★ 복제 신설 근거 (decisions.md 6.3(l) ②를 그대로 이행)
//   "POST 실코드는 현재 프로즌 upload_spike_common.cpp에만 존재 — M5-d는 이를 복제해
//    신설 uplink_common.cpp로 옮긴다(원본 무수정 원칙, §7 동형)."
//   → 원본 firmware/src/upload_spike_common.cpp / include/upload_spike_common.h 는
//     본 PR에서 **1바이트도 수정하지 않는다**. 복제 출처는 각 함수 구현부 주석에 명시.
//
// ★ 복제하지 않은 것 (하네스 전용 = 본 PR 범위 밖)
//   - synthesizeSineInt16()        합성 사인톤 = 마이크가 없던 시절의 대역물. 이제 실음원 사용.
//   - SpikeResult.connectMs / measureConnectSeparately  지연 성분 분리 측정용 계측 장치.
//   - SPIKE_ITERATIONS / SPIKE_INTERVAL_MS / AUDIO_SWEEP_* / printStats()  통계 스윕 하네스.
//
// ★ 본 PR이 **확정하지 않는 것**
//   - HTTP_TIMEOUT_MS: 복제 원본(upload_spike_common.h)의 10000ms를 그대로 들고 온다.
//     decisions.md 7.7(l)(2차 12.1초 vs 타임아웃)은 **정책 미확정**이며 판정 시점은
//     I2(/enrich 2차 클라이언트) 설계 시점이다. 여기서 값을 바꾸거나 근거를 만들지 않는다.
//   - RMS 트리거 임계값 / pre-post 비율(M5-c): 본 PR의 트리거는 **시리얼 수동 키**다.
//   - ~~ToF 메타 4필드: 전송하지 않는다~~ → 2026-09-11 PoC-(45) 송신 배선(아래 tof 인자).
//     ToF 부재·init 실패 시에는 tof=nullptr 로 종전 동작(4필드 미전송 = 서버 tof_absent) 유지.

#pragma once

#include <Arduino.h>

#include "mic_common.h"
#include "tof_common.h"   // TofFrameResult (PoC-(45): ToF 4필드 wire 값의 출처)

// === 페이로드 크기 (mic_common.h 슬롯 산술에서 유도 — 새 상수 신설이 아니라 파생) ===
// MIC_RING_SLOTS(32) × MIC_DMA_BUF_LEN(1024) 샘플 × 2 bytes(int16) = 65,536 bytes = 2.048초.
// 서버 AUDIO_MAX_BYTES = 320,000 (server/app/constants.py) 의 20.5% → 413 불가.
constexpr size_t UPLINK_AUDIO_BYTES =
    (size_t)MIC_RING_SLOTS * (size_t)MIC_DMA_BUF_LEN * sizeof(int16_t);
static_assert(UPLINK_AUDIO_BYTES == 65536, "링버퍼 2초 스냅샷은 65536 bytes 여야 한다");

// === multipart 계약 (transport A안, decisions.md 카테고리 6.2 2026-07-09 PoC-(26)) ===
// "multipart/form-data + int16 PCM raw bytes(64KB/2초) + 메타(client_request_id/device_id)
//  form field 동봉". 파트명 audio = 서버 AUDIO_FILE_FIELD(constants.py:29) 와 1:1.
constexpr const char* UPLINK_BOUNDARY          = "ddingdongMicUplinkBoundary5C1E7";
constexpr const char* UPLINK_AUDIO_FIELD       = "audio";
constexpr const char* UPLINK_AUDIO_CONTENT_TYPE = "application/octet-stream";

// device_id 는 rate limit 키다(5초당 1회, decisions.md 6.3(l) ④). upload_spike 하네스와
// 같은 값을 쓰면 두 env가 서로의 429를 유발하므로 분리한다(하네스가 분리한 것과 동형).
constexpr const char* UPLINK_DEVICE_ID = "ddingdong-mic-uplink-001";

// head(필드 boilerplate) + tail 여유폭. 원본 MULTIPART_OVERHEAD_BYTES 는 640(필드 3개 ≈ 370B).
// PoC-(45) ToF 4필드 추가 = 파트당 ≈ 100B(경계 35 + 헤더 ~55 + 값 ≤5 + CRLF) × 4 ≈ 400B → 합 ≈ 770B
// 가 640 을 넘으므로 1024 로 상향(head 버퍼도 동일 상향). 값은 여유폭이지 판정 상수가 아니다.
constexpr size_t UPLINK_MULTIPART_OVERHEAD_BYTES = 1024;

// === 타임아웃·WiFi 상수 (원본 upload_spike_common.h 값 그대로 복제) ===
// ⚠️ HTTP_TIMEOUT_MS 는 **정책 확정이 아니다** — 상단 주석의 7.7(l) 참조.
constexpr uint32_t UPLINK_HTTP_TIMEOUT_MS        = 10000;
constexpr uint32_t UPLINK_WIFI_PRIMARY_TIMEOUT_MS  = 15000;
constexpr uint32_t UPLINK_WIFI_FALLBACK_TIMEOUT_MS = 15000;
constexpr uint32_t UPLINK_WIFI_POLL_INTERVAL_MS    = 250;

// 응답 바디 보관 상한. /detect 201 본문(notif.to_dict)은 실측 약 550~650B 규모이고,
// 로그에 뽑는 건 predicted_class/confidence/tof_check.reason 3개뿐이라 앞부분만 있으면 된다.
// 넘치면 잘린 채 파싱 실패 → 로그에 "?" 로 드러난다(조용히 틀린 값을 만들지 않는다).
constexpr size_t UPLINK_RESP_BUF_BYTES = 768;

struct UplinkResult {
  int      httpStatus;   // HTTPClient 반환값 (음수 = 전송 실패, errorToString 참조)
  uint32_t roundTripMs;  // POST 직전 ~ 응답 수신까지
};

// === API ===

// PSRAM 할당(실패 시 nullptr + 로그). 원본 allocPsramBuffer 복제.
uint8_t* uplinkAllocPsram(size_t bytes, const char* tag);

// WiFi STA 블로킹 연결(primary → fallback). 원본 connectWifiBlocking 복제.
bool uplinkConnectWifi();

// multipart 바디 조립. 반환 = 조립된 총 바이트(0 = 실패). 원본 buildMultipartBody 복제.
// tof: nullptr 이면 ToF 4필드를 싣지 않는다(PR #52 바이트열과 동일 = 서버 tof_absent).
//      non-null 이면 decisions.md 6.2 G10/6.4 의 4필드를 device_id 파트 뒤에 form field 로 싣는다
//      (파트명 = server/app/constants.py TOF_*_FIELD 실grep 값). center_valid=false 면
//      tof_center_mm 파트를 **생략**한다 — 서버 계약(tof_meta.py parse_tof_meta)에서 "필드 부재 =
//      telemetry n/a" 이고, 빈 문자열은 invalid 로 떨어진다(2026-09-11 서버 함수 직접 호출로 확인).
size_t uplinkBuildMultipart(uint8_t* dest, size_t destCapacity,
                            const char* clientRequestId, const char* deviceId,
                            const uint8_t* audioBytes, size_t audioLen,
                            const TofFrameResult* tof);

// POST /api/v1/detect. respOut 에 응답 바디 앞부분을 NUL 종료로 담는다(nullptr 허용).
// ★ 재시도하지 않는다 — 429/401/타임아웃/끊김 모두 호출부가 로그만 남긴다(1차 재시도 없음).
// tof 는 uplinkBuildMultipart 로 그대로 전달(nullptr 허용).
UplinkResult uplinkPostAudio(const char* host, uint16_t port,
                             const char* clientRequestId,
                             const uint8_t* audioBytes, size_t audioLen,
                             uint8_t* bodyBuf, size_t bodyBufCapacity,
                             char* respOut, size_t respCapacity,
                             const TofFrameResult* tof);
