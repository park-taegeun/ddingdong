// 띵동 PoC firmware - 마이크 더미 테스트 (5/10, PoC Day 4)
//
// micTask 단독: i2s_read 폴링 + M2 계측(raw int32 통계) + M4 변환(int16 PCM).
// ★ 계층 이력 (decisions.md §9.3 ToF Stage B-1 "계측 → 실측 → 판정" 패턴 준용):
//   M2 = 계측(or_acc/tz 관측 전용) → M3 = ④런타임 실측(2026-08-20) → M4 = 판정 = 본 단계.
//   M4는 실측으로 확정된 shift(=14)로 int16 변환만 수행한다.
//   트리거 판정 / DC 오프셋 보정 / 버퍼링 / 업로드는 여전히 0줄 (하단 defer 주석 참조).
// 5/21 PoC 통합 시 cameraTask(Core 1) + micTask(Core 0) 병행 검증 (decisions.md 카테고리 14).

#include "mic_common.h"

static void micTask(void* parameter) {
  (void)parameter;
  logMicMemoryDiagnostics("micTask-entry");

  // 32-bit mono × DMA_BUF_LEN 프레임 = 4 KiB. task 스택(4KiB) 폭주 방지로 static (BSS).
  // ★ union = 같은 4 KiB를 raw(int32 DMA 수신) / i16(M4 변환 결과) 두 뷰로 재사용.
  //   int16 목적지를 따로 잡으면 +2 KiB BSS 순증이므로 union으로 흡수 (RAM 순증 0).
  //   sizeof = max(4096, 2048) = 4096 → 16.1 기준선(audio_buffer + scratch = 8 KiB) 불변.
  //   변환 후 raw 앞부분은 무효화되나 다음 i2s_read가 전량 덮어쓰므로 무해하다.
  static union {
    int32_t raw[MIC_DMA_BUF_LEN];
    int16_t i16[MIC_DMA_BUF_LEN];
  } audio_buffer;
  size_t   bytes_read  = 0;
  uint32_t buf_count   = 0;
  uint32_t err_count   = 0;
  uint32_t window_idx  = 0;

  for (;;) {
    const esp_err_t err = i2s_read(MIC_I2S_PORT, audio_buffer.raw, sizeof(audio_buffer.raw),
                                   &bytes_read, portMAX_DELAY);
    if (err != ESP_OK) {
      if ((++err_count % 10) == 1) {
        Serial.printf("[mic] read failed: 0x%x (%s) #%u\n",
                      err, esp_err_to_name(err), (unsigned)err_count);
      }
      continue;
    }

    // ── M2 계측: 윈도우(MIC_LOG_EVERY_N_BUFFERS 버퍼)마다 raw int32 통계 1줄 출력 ──
    // ★ 측정 조건(uptime / warmup 상태)이 로그에 자동 동반 → 사후 판별 가능
    //   (ToF가 near·center를 강제 동반시킨 것과 동형, decisions.md §9.3(b)).
    if ((++buf_count % MIC_LOG_EVERY_N_BUFFERS) == 1) {
      const size_t      n   = bytes_read / sizeof(int32_t);
      const MicRawStats st  = computeMicRawStats(audio_buffer.raw, n);
      const uint32_t    up  = millis();
      const char*       warm = (up >= MIC_WARMUP_DELAY_MS) ? "done" : "pending";
      window_idx++;

      Serial.printf("[mic][M2] w=%u n=%d err=%u | min=%d max=%d mean=%lld pp=%lld rms=%lld"
                    " | or=0x%08X tz=%d nz=%d | up=%ums warm=%s\n",
                    (unsigned)window_idx, (int)st.n, (unsigned)err_count,
                    (int)st.min, (int)st.max,
                    (long long)st.mean, (long long)st.pp, (long long)st.rms,
                    (unsigned)st.or_acc, st.tz, (int)st.nz,
                    (unsigned)up, warm);

      // K 윈도우마다 raw 샘플 8개 hex 덤프 (MSB 정렬 육안 확인용).
      if (n >= 8 && (window_idx % MIC_RAW_DUMP_EVERY_N_WINDOWS) == 1) {
        Serial.printf("[mic][M2] raw[0..7]= 0x%08X 0x%08X 0x%08X 0x%08X"
                      " 0x%08X 0x%08X 0x%08X 0x%08X\n",
                      (unsigned)(uint32_t)audio_buffer.raw[0], (unsigned)(uint32_t)audio_buffer.raw[1],
                      (unsigned)(uint32_t)audio_buffer.raw[2], (unsigned)(uint32_t)audio_buffer.raw[3],
                      (unsigned)(uint32_t)audio_buffer.raw[4], (unsigned)(uint32_t)audio_buffer.raw[5],
                      (unsigned)(uint32_t)audio_buffer.raw[6], (unsigned)(uint32_t)audio_buffer.raw[7]);
      }

      // ── M4 변환: raw int32 → int16 PCM (>>14 + saturation) ──
      // ★ 반드시 위 raw 덤프 뒤에 온다 — 변환이 raw 앞부분을 덮어쓰기 때문.
      // ★ M2 로그 줄에 덧붙이지 말고 별도 줄로 출력한다: 2026-08-20 M3 실측에서
      //   줄이 길어 시리얼 전송 중 깨진 라인([PARTIAL])이 6건 발생했다.
      const MicI16Stats i16 = convertMicRawToInt16(audio_buffer.raw, audio_buffer.i16, n);

      // ★ 변환 검증 방법(④런타임 M4 검증 절차):
      //   raw rms ÷ i16 rms 가 2^14 = 16384 에 수렴하면 shift가 정상 적용된 것이다.
      //   예) 배경 raw rms 2,400,000 / 16384 ≈ 146 | 박수 118,992,347 / 16384 ≈ 7,262
      //   아래 raw/i16 열이 그 비를 on-device로 산출한다 (수동 나눗셈 불필요).
      //   벗어나면: 16384의 4배 = >>16 오적용 / 1/4배 = >>12 오적용을 의심하라.
      //   clip > 0 이면 헤드룸(실측 1.8배) 소진 신호 = 더 큰 음압 유입.
      const long long ratio = (i16.rms > 0) ? ((long long)st.rms / (long long)i16.rms) : -1;

      Serial.printf("[mic][M4] w=%u i16: min=%d max=%d rms=%d clip=%u | raw/i16=%lld (기대 16384)\n",
                    (unsigned)window_idx,
                    (int)i16.min, (int)i16.max, (int)i16.rms,
                    (unsigned)i16.clip, ratio);
    }

    // ── [mic][해소] 24→16bit 정렬 변환: M4에서 구현 완료 (2026-08-20 실측 확정) ──
    //   ★ 이력 보존 — 삭제하지 않고 갱신한다.
    //   M2 상태: raw int32 통계만 관측, shift 미확정 ("④런타임 tz 실측이 유일한 물증").
    //   판정 근거: or_acc의 tz(trailing zeros) = 전 샘플 OR의 하위 항상-0 비트 수
    //             = INMP441 데이터가 실린 적 없는 하위 폭 = 실제 정렬 폭의 직접 물증.
    //   M3 실측 프로토콜 충족 결과 (2026-08-20 / env:mic_dummy / HEAD 17ce212 / 랩실):
    //     ① 무자극 기준선 30초 → w=233~248 (16윈도우 ≈ 51초) 충족
    //     ② 근접 박수 10회     → w=249~266 (18윈도우) 충족, max 296542208 = 클리핑 없음
    //     ③ 초인종/육성 10초   → w=267~271 (5윈도우 ≈ 16초) 육성으로 충족
    //   확정: ①②③ 전 구간에서 tz=6 / or=0xFFFFFFC0 불변(진폭 60배 변동에도 무변화)
    //        → 정렬 폭 6 확정 → **int16 = raw >> 14** (근거표: mic_common.h "M4 변환 계층").
    //        불일치 없었으므로 decisions.md §9 정지 사유 없음.

    // ── [mic][defer] DC 오프셋 보정: 미구현 (M5 소관) ──
    //   현 상태 : 변환은 shift만 한다. 오프셋 제거 0줄.
    //   실측 사실: M3에서 mean이 -1,210,351 ~ +1,045,075 로 **부호까지 변동**했다.
    //             고정 오프셋이 아니라 저주파 드리프트 → 단순 뺄셈으로 해결 불가.
    //   판정 방법: M5에서 조용한 환경 장시간 로그로 드리프트 주기·진폭을 먼저 측정한다.
    //             주기가 신호 대역(초인종 수백 Hz~)보다 충분히 낮으면 HPF 도입,
    //             진폭이 int16 풀스케일 대비 무시 가능하면 미도입으로 확정.
    //   ⚠️ 측정 전 필터 설계 금지 (계수 근거가 없으면 8→20 오판 재발, decisions.md 9.2(d)).

    // ── [mic][defer] RMS 트리거 임계값: 미구현 (M5 소관) ──
    //   현 상태 : i16 rms를 로그로 관측만 한다. 임계값·판정·상태머신 0줄.
    //   미결 사유: 카테고리 3 "80% 지점"의 기준선이 미확정이다.
    //   ⚠️ M3 배경 rms 2,104,135 ~ 2,646,435 를 무음 기준선으로 쓰지 말 것 —
    //      랩실 사람 대화가 포함된 값이라 무음이 아니다. 이 값으로 임계값을 정하면
    //      실제 무음 환경에서 트리거가 상시 발화한다.
    //   판정 방법: ① 조용한 환경(야간/무인) 무음 기준선 재측정 →
    //             ② 초인종·노크 실측 진폭 확보 → ③ 두 분포의 분리점에서 80% 지점 도출.
    //             ①②의 마진이 불충분하면 임계값 대신 다른 특징량으로 pivot 후 §9 보고.
  }
}

void setup() {
  Serial.begin(115200);
  delay(MIC_SERIAL_BOOT_DELAY_MS);
  Serial.println("\n[BOOT] ddingdong mic test (INMP441 + I2S1, 16kHz mono)");

  if (!initMicI2S()) {
    Serial.println("[BOOT] mic init failed — task spawn 생략, loop()에서 idle 진단만 출력");
    return;  // graceful: 무한 루프 X. loop()에서 주기적 메모리 로그.
  }
  discardMicWarmup();

  xTaskCreatePinnedToCore(micTask, "micTask",
                          MIC_TASK_STACK_SIZE, nullptr,
                          MIC_TASK_PRIORITY, nullptr,
                          MIC_TASK_CORE);
  Serial.println("[BOOT] micTask started on Core 0 priority 4");
}

void loop() {
  // 정상 부팅 시 task가 모든 작업 수행 → loop는 idle.
  // init 실패 시 (부품 부재) 메모리 진단만 주기 출력.
  static uint32_t last_log = 0;
  const uint32_t now = millis();
  if ((now - last_log) >= MIC_LOOP_IDLE_LOG_MS) {
    last_log = now;
    logMicMemoryDiagnostics("loop-idle");
  }
  delay(100);
}
