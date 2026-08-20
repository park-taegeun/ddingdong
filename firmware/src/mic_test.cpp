// 띵동 PoC firmware - 마이크 더미 테스트 (5/10, PoC Day 4)
//
// micTask 단독: i2s_read 폴링 + M2 계측(raw int32 통계 관측 전용).
// ★ 본 단계 = 계측 계층 (decisions.md §9.3 ToF Stage B-1 패턴 준용): 관측만 하고
//   변환/shift/트리거는 전혀 하지 않는다. or_acc의 tz로 실제 비트 정렬을 드러내는 것이 목표.
// 5/21 PoC 통합 시 cameraTask(Core 1) + micTask(Core 0) 병행 검증 (decisions.md 카테고리 14).

#include "mic_common.h"

static void micTask(void* parameter) {
  (void)parameter;
  logMicMemoryDiagnostics("micTask-entry");

  // 32-bit mono × DMA_BUF_LEN 프레임 = 4 KiB. task 스택(4KiB) 폭주 방지로 static (BSS).
  static int32_t audio_buffer[MIC_DMA_BUF_LEN];
  size_t   bytes_read  = 0;
  uint32_t buf_count   = 0;
  uint32_t err_count   = 0;
  uint32_t window_idx  = 0;

  for (;;) {
    const esp_err_t err = i2s_read(MIC_I2S_PORT, audio_buffer, sizeof(audio_buffer),
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
      const MicRawStats st  = computeMicRawStats(audio_buffer, n);
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
                      (unsigned)(uint32_t)audio_buffer[0], (unsigned)(uint32_t)audio_buffer[1],
                      (unsigned)(uint32_t)audio_buffer[2], (unsigned)(uint32_t)audio_buffer[3],
                      (unsigned)(uint32_t)audio_buffer[4], (unsigned)(uint32_t)audio_buffer[5],
                      (unsigned)(uint32_t)audio_buffer[6], (unsigned)(uint32_t)audio_buffer[7]);
      }
    }

    // ── [mic][defer] 24→16bit 정렬 변환: 본 단계 미구현 (계측 전용) ──
    //   현 상태 : raw int32 통계만 관측(위 M2 로그). 변환/shift/int16/트리거 = 0줄.
    //   판정 근거: or_acc의 tz(trailing zeros) = 전 샘플 OR의 하위 항상-0 비트 수
    //             = INMP441 데이터가 실린 적 없는 하위 폭 = 실제 정렬 폭의 직접 물증.
    //   M3 실측 프로토콜 (각 항목 = 무엇을 왜 재는가):
    //     ① 무자극 기준선 30초 — 노이즈 플로어 + DC 오프셋(mean) 확보.
    //                            조용해진 뒤라야 이후 측정이 유효 (환경 오염 분리, §9.3(H)).
    //     ② 근접 박수 10회     — 상한 진폭. max 도달점·클리핑 여부 확인.
    //     ③ 초인종/육성 10초   — 실사용 대역 전형 진폭 확보.
    //   확정 절차: ①②③ 전부에서 tz가 일관되면 그 값을 정렬 폭으로 확정 →
    //             M4(판정 PR)에서 shift 결정. 불일치 시 decisions.md §9 정지.
    //   ⚠️ 본 단계에서 shift 값 확정 금지 (④런타임 tz 실측이 유일한 물증).
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
