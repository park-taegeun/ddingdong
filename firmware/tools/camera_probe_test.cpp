// probe_stats.h / probe_modes.h 호스트 검산 — 실제 헤더를 그대로 include 한다(복사 아님).
//   c++ -std=c++17 -Wall -I firmware/include -o /tmp/cpt firmware/tools/camera_probe_test.cpp && /tmp/cpt
//
// 이 하네스가 지켜야 할 불변식 4개에 단언을 건다.
//   I1 SOI 는 **선두 2바이트 모두** 확인한다            (NC-1)
//   I2 길이 가드가 비교보다 먼저다 = 버퍼 너머를 읽지 않는다 (NC-2)
//   I3 표본 0건 창은 최소값을 갖지 않는다 = 센티넬 없음   (NC-3)
//   I4 인접 모드는 정확히 한 변수만 다르다              (NC-4)
//
// ⚠️ 단언 무딤 함정 (negative control 설계와 짝지어 둔다):
//   - I1 은 "첫 바이트만 다른" 케이스가 없으면 첫 바이트 비교를 지워도 통과한다.
//   - I2 는 "길이 1 + 뒤 바이트가 0xD8" 케이스가 없으면 길이 가드를 지워도 통과한다.
//   - I4 는 인접 쌍을 **전부** 순회하지 않으면 한 쌍만 깨진 표를 통과시킨다.
//   각각 아래 soi_first_byte_only / soi_len1_with_d8_behind / chain 루프가 그 케이스다.
//
// negative control 4종은 CAMERA_PROBE_RUNBOOK.md 7절 참조 — 각각 반드시 실패해야 한다.
#include <cassert>
#include <cstdio>
#include <cstring>

#include "probe_modes.h"
#include "probe_stats.h"

static int checks = 0;
#define CHECK(x) do { assert(x); checks++; } while (0)

// ── I1 · I2: JPEG SOI ────────────────────────────────────────────────────────
static void test_soi() {
  const uint8_t good[3]  = {0xFF, 0xD8, 0xFF};
  const uint8_t first[2] = {0x00, 0xD8};   // 첫 바이트만 다름 → NC-1 검출용
  const uint8_t second[2] = {0xFF, 0x00};  // 둘째 바이트만 다름
  const uint8_t both[2]  = {0x12, 0x34};

  CHECK(probeIsJpegSoi(good, 2) == true);
  CHECK(probeIsJpegSoi(good, 3) == true);          // 뒤에 더 있어도 참
  CHECK(probeIsJpegSoi(first, 2) == false);        // ★ soi_first_byte_only (NC-1)
  CHECK(probeIsJpegSoi(second, 2) == false);
  CHECK(probeIsJpegSoi(both, 2) == false);

  // 길이 경계 0·1·2
  CHECK(probeIsJpegSoi(good, 0) == false);
  CHECK(probeIsJpegSoi(good, 1) == false);         // ★ soi_len1_with_d8_behind (NC-2)
                                                    //   good[1] == 0xD8 이 **뒤에 있다** —
                                                    //   길이 가드가 없으면 여기서 참이 된다.
  CHECK(probeIsJpegSoi(good, 2) == true);

  // nullptr 은 길이와 무관하게 거짓
  CHECK(probeIsJpegSoi(nullptr, 0) == false);
  CHECK(probeIsJpegSoi(nullptr, 2) == false);
  CHECK(probeIsJpegSoi(nullptr, 4096) == false);
}

// ── I3: 카메라 창 통계 ───────────────────────────────────────────────────────
static void test_cam_window() {
  ProbeCamWin w;
  probeCamReset(&w);

  // 빈 창 = 표본 없음. 최소/최대/평균은 의미가 없고, 그것이 드러나야 한다.
  CHECK(w.attempt == 0 && w.ok == 0 && w.fb_null == 0 && w.soi_bad == 0);
  CHECK(probeCamHasSample(&w) == false);
  CHECK(probeCamAvgMs(&w) == 0);
  CHECK(probeCamHasSample(nullptr) == false);

  // 실패만 있는 창 — attempt 는 늘지만 여전히 표본 0건이다(조용한 실패 금지의 요지).
  probeCamRecordNull(&w);
  probeCamRecordNull(&w);
  probeCamRecordSoiBad(&w);
  CHECK(w.attempt == 3 && w.fb_null == 2 && w.soi_bad == 1 && w.ok == 0);
  CHECK(probeCamHasSample(&w) == false);           // ★ NC-3 검출 지점 1

  // 첫 성공 표본 = min·max 를 동시에 세운다(센티넬 없음).
  probeCamRecordOk(&w, 6000, 20);
  CHECK(probeCamHasSample(&w) == true);
  CHECK(w.len_min == 6000 && w.len_max == 6000);   // ★ NC-3 검출 지점 2 (0 이면 안 된다)
  CHECK(w.ms_min == 20 && w.ms_max == 20);
  CHECK(probeCamAvgMs(&w) == 20);

  probeCamRecordOk(&w, 7000, 15);
  CHECK(w.len_min == 6000 && w.len_max == 7000);
  CHECK(w.ms_min == 15 && w.ms_max == 20);
  CHECK(probeCamAvgMs(&w) == 17);                  // (20+15)/2 = 17 (정수 절삭)

  // 불변식: attempt == ok + fb_null + soi_bad (모든 경로가 카운터로 드러난다)
  CHECK(w.attempt == w.ok + w.fb_null + w.soi_bad);
  CHECK(w.attempt == 5 && w.ok == 2);

  // 리셋은 전 필드를 지운다 = 다음 창이 이전 창을 물려받지 않는다.
  probeCamReset(&w);
  CHECK(w.attempt == 0 && w.ok == 0 && w.len_min == 0 && w.ms_sum == 0);
  CHECK(probeCamHasSample(&w) == false);

  // 길이 0 인 성공 프레임(있을 수 없지만 값 도메인 경계) — 표본으로는 잡힌다.
  probeCamRecordOk(&w, 0, 0);
  CHECK(probeCamHasSample(&w) == true && w.len_min == 0 && w.ms_max == 0);

  // nullptr 방어
  probeCamRecordOk(nullptr, 1, 1);
  probeCamRecordNull(nullptr);
  probeCamRecordSoiBad(nullptr);
  CHECK(probeCamAvgMs(nullptr) == 0);
}

// ── 마이크 창 통계 ───────────────────────────────────────────────────────────
static void test_mic_window() {
  ProbeMicWin w;
  probeMicReset(&w);

  // 표본 0건 창: RMS 는 0 이지만, 호출부는 n == 0 으로 "무음"과 구분한다.
  CHECK(w.n == 0 && probeMicRmsAll(&w) == 0 && probeMicRmsExcl(&w) == 0);
  CHECK(probeMicRmsAll(nullptr) == 0 && probeMicRmsExcl(nullptr) == 0);

  // 상수 진폭 100 × 1000 샘플 → rms = 100 (클램프 0건이므로 rms_x 도 같다)
  int16_t buf[1000];
  for (size_t i = 0; i < 1000; ++i) buf[i] = 100;
  probeMicAccumulate(&w, buf, 1000);
  CHECK(w.n == 1000 && w.n_ok == 1000 && w.clip == 0);
  CHECK(w.peak == 100);
  CHECK(probeMicRmsAll(&w) == 100);
  CHECK(probeMicRmsExcl(&w) == 100);

  // 클램프 샘플을 섞는다: +32767 10개, -32768 10개.
  int16_t clip_buf[20];
  for (int i = 0; i < 10; ++i) { clip_buf[i] = 32767; clip_buf[10 + i] = -32768; }
  probeMicAccumulate(&w, clip_buf, 20);
  CHECK(w.clip == 20);
  CHECK(w.n == 1020 && w.n_ok == 1000);            // 클램프는 n 에는 들고 n_ok 에는 안 든다
  CHECK(w.peak == 32768);                          // |INT16_MIN| = 32768
  CHECK(probeMicRmsExcl(&w) == 100);               // 제외 RMS 는 클램프에 흔들리지 않는다
  CHECK(probeMicRmsAll(&w) > 100);                 // 전체 RMS 는 끌려 올라간다

  // 경계: 32766 은 클램프가 아니다(noise_stats.h 의 정의를 그대로 쓴다)
  ProbeMicWin w2;
  probeMicReset(&w2);
  int16_t edge[2] = {32766, -32767};
  probeMicAccumulate(&w2, edge, 2);
  CHECK(w2.clip == 0 && w2.n_ok == 2);

  // nullptr / 길이 0 방어
  probeMicAccumulate(&w2, nullptr, 10);
  probeMicAccumulate(nullptr, edge, 2);
  probeMicAccumulate(&w2, edge, 0);
  CHECK(w2.n == 2);

  probeMicReset(&w2);
  CHECK(w2.n == 0 && w2.peak == 0 && w2.sq_all == 0);
}

// ── I4: 모드 사슬 ────────────────────────────────────────────────────────────
static void test_mode_chain() {
  // 전 인접 쌍을 **빠짐없이** 순회한다 — 한 쌍만 검사하면 깨진 표가 통과한다.
  for (int m = 0; m + 1 < PROBE_MODE_N; ++m) {
    const ProbeModeCfg a = probeModeCfg(m);
    const ProbeModeCfg b = probeModeCfg(m + 1);
    CHECK(probeModeDiffCount(a, b) == 1);          // ★ NC-4 검출 지점
    CHECK(probeModeAdjacentOk(m) == true);
  }
  CHECK(probeModeChainOk() == true);

  // 사슬 밖 인덱스
  CHECK(probeModeAdjacentOk(-1) == false);
  CHECK(probeModeAdjacentOk(PROBE_MODE_N - 1) == false);
  CHECK(probeModeAdjacentOk(PROBE_MODE_N) == false);

  // diffCount 가 세 필드를 전부 본다 (한 필드라도 빠뜨리면 사슬 검사가 무의미해진다)
  const ProbeModeCfg base = {PROBE_CAM_OFF, false, PROBE_RES_QVGA};
  CHECK(probeModeDiffCount(base, base) == 0);
  CHECK(probeModeDiffCount(base, {PROBE_CAM_IDLE, false, PROBE_RES_QVGA}) == 1);
  CHECK(probeModeDiffCount(base, {PROBE_CAM_OFF, true, PROBE_RES_QVGA}) == 1);
  CHECK(probeModeDiffCount(base, {PROBE_CAM_OFF, false, PROBE_RES_VGA}) == 1);
  CHECK(probeModeDiffCount(base, {PROBE_CAM_IDLE, true, PROBE_RES_VGA}) == 3);

  // 사슬의 양 끝과 축 커버리지
  CHECK(probeModeCfg(0).cam == PROBE_CAM_OFF && probeModeCfg(0).wifi_tx == false);
  CHECK(probeModeCfg(0).res == PROBE_RES_QVGA);
  CHECK(probeModeCfg(4).cam == PROBE_CAM_CONTINUOUS && probeModeCfg(4).wifi_tx == true);
  CHECK(probeModeCfg(7).res == PROBE_RES_VGA);

  // 축이 전부 실제로 등장하는가 (한 축이라도 빠지면 실험 설계가 비어 있다)
  bool seen_cam[4] = {false, false, false, false};
  bool seen_wifi[2] = {false, false};
  bool seen_res[2] = {false, false};
  for (int m = 0; m < PROBE_MODE_N; ++m) {
    const ProbeModeCfg c = probeModeCfg(m);
    seen_cam[c.cam] = true;
    seen_wifi[c.wifi_tx ? 1 : 0] = true;
    seen_res[c.res] = true;
  }
  for (int i = 0; i < 4; ++i) CHECK(seen_cam[i] == true);
  CHECK(seen_wifi[0] && seen_wifi[1]);
  CHECK(seen_res[0] && seen_res[1]);

  // 범위 밖 모드는 m0 와 같은 안전값
  const ProbeModeCfg oob = probeModeCfg(PROBE_MODE_N);
  CHECK(probeModeDiffCount(oob, probeModeCfg(0)) == 0);
  CHECK(probeModeDiffCount(probeModeCfg(-1), probeModeCfg(0)) == 0);
}

int main() {
  test_soi();
  test_cam_window();
  test_mic_window();
  test_mode_chain();
  printf("camera_probe_test: %d checks passed\n", checks);
  return 0;
}
