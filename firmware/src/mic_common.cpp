// 띵동 PoC firmware - 마이크 공통 구현 (5/10, PoC Day 4)

#include "mic_common.h"

void logMicMemoryDiagnostics(const char* tag) {
  // 5/12 메모리 self-checkpoint 입력 데이터 (decisions.md 카테고리 17.1.1).
  Serial.printf("[MEM:%s] PSRAM total=%u free=%u | Heap free=%u min=%u\n",
                tag,
                (unsigned)ESP.getPsramSize(),
                (unsigned)ESP.getFreePsram(),
                (unsigned)ESP.getFreeHeap(),
                (unsigned)ESP.getMinFreeHeap());
}

bool initMicI2S() {
  logMicMemoryDiagnostics("pre-init");

  // INMP441은 I²S Philips (MSB delayed 1 SCK), 32-bit slot에 24-bit MSB align.
  // ONLY_LEFT 채널 포맷 — L/R 핀이 GND라 microphone이 좌 슬롯에만 데이터 출력.
  i2s_config_t i2s_cfg = {};
  i2s_cfg.mode                 = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX);
  i2s_cfg.sample_rate          = MIC_SAMPLE_RATE_HZ;
  i2s_cfg.bits_per_sample      = I2S_BITS_PER_SAMPLE_32BIT;
  i2s_cfg.channel_format       = I2S_CHANNEL_FMT_ONLY_LEFT;
  i2s_cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;  // Philips 표준
  i2s_cfg.intr_alloc_flags     = ESP_INTR_FLAG_LEVEL1;
  i2s_cfg.dma_buf_count        = MIC_DMA_BUF_COUNT;
  i2s_cfg.dma_buf_len          = MIC_DMA_BUF_LEN;
  i2s_cfg.use_apll             = false;
  i2s_cfg.tx_desc_auto_clear   = false;
  i2s_cfg.fixed_mclk           = 0;

  esp_err_t err = i2s_driver_install(MIC_I2S_PORT, &i2s_cfg, 0, nullptr);
  if (err != ESP_OK) {
    Serial.printf("[mic] i2s_driver_install failed: 0x%x (%s)\n",
                  err, esp_err_to_name(err));
    return false;
  }

  i2s_pin_config_t pin_cfg = {};
  pin_cfg.mck_io_num   = I2S_PIN_NO_CHANGE;  // INMP441은 MCLK 미사용
  pin_cfg.bck_io_num   = MIC_SCK_PIN;
  pin_cfg.ws_io_num    = MIC_WS_PIN;
  pin_cfg.data_out_num = I2S_PIN_NO_CHANGE;
  pin_cfg.data_in_num  = MIC_SD_PIN;

  err = i2s_set_pin(MIC_I2S_PORT, &pin_cfg);
  if (err != ESP_OK) {
    Serial.printf("[mic] i2s_set_pin failed: 0x%x (%s)\n",
                  err, esp_err_to_name(err));
    i2s_driver_uninstall(MIC_I2S_PORT);
    return false;
  }

  i2s_zero_dma_buffer(MIC_I2S_PORT);
  Serial.printf("[mic] I2S%d RX installed (sr=%uHz, 32-bit, left only, BCLK=GPIO%d/WS=GPIO%d/SD=GPIO%d)\n",
                (int)MIC_I2S_PORT,
                (unsigned)MIC_SAMPLE_RATE_HZ,
                MIC_SCK_PIN, MIC_WS_PIN, MIC_SD_PIN);
  logMicMemoryDiagnostics("post-init");
  return true;
}

void discardMicWarmup() {
  // datasheet: VDD 인가 후 2^18 SCK cycles 동안 출력 0 → 16kHz × 64 = 1.024MHz 시 약 256ms.
  // userMemories 250ms 상수와 일치. 첫 14개 DMA 버퍼는 추가 안전망으로 폐기.
  vTaskDelay(pdMS_TO_TICKS(MIC_WARMUP_DELAY_MS));

  // 32-bit mono × DMA_BUF_LEN 프레임 = 4 KiB. 스택 폭주 방지 위해 static.
  static int32_t scratch[MIC_DMA_BUF_LEN];
  size_t bytes_read = 0;
  int    discarded  = 0;
  for (int i = 0; i < MIC_WARMUP_BUFFERS_DISCARD; i++) {
    esp_err_t err = i2s_read(MIC_I2S_PORT, scratch, sizeof(scratch),
                             &bytes_read, portMAX_DELAY);
    if (err == ESP_OK) {
      discarded++;
    }
  }
  Serial.printf("[mic] warmup: %ums wait + %d/%d DMA buffers discarded\n",
                (unsigned)MIC_WARMUP_DELAY_MS,
                discarded, MIC_WARMUP_BUFFERS_DISCARD);
}

// M2 계측: raw int32 버퍼의 진폭 통계를 산출 (관측 전용, 변환·판정 무접촉).
// 누산은 전부 지역변수 — 새 static/전역 저장소 신설 없음 (RAM 순증 0).
//
// ★ 오버플로 가드 (전 분기 값 도메인 열거로 불가 증명):
//   - samples[i]  ∈ [INT32_MIN, INT32_MAX],  count ∈ [0, MIC_DMA_BUF_LEN=1024]
//   - sum(Σs)     : |Σs| ≤ 1024·2^31 = 2^41 < INT64_MAX(2^63) → int64 안전
//   - sumsq(Σs²)  : 최대 1024·(2^31)² = 2^72 > INT64_MAX(2^63) → int64/uint64 전부 오버플로.
//                   Xtensa 32-bit엔 __int128 부재 → double 누산 채택(위임의 "int64 누산" pivot).
//                   double 지수부는 2^72 ≫ 초과 여유, 정밀 손실은 2^(72-52)=2^20 미만
//                   = 진폭 지표에 무관. (근본원인 재검증: 학습 19 — 위임 전제도 재확인)
//   - pp = max-min : max≤2^31-1, min≥-2^31 → 최대 2^32-1, int32 초과 → int64 캐스팅 후 산출
//   - or_acc      : uint32 OR 누적, 값역 = 전체 uint32, 오버플로 개념 무 (포화 아님)
//   - tz          : __builtin_ctz(0) 미정의 → or_acc==0 분기에서 32로 명시 (하위 전부 0)
//   - mean/rms 산출 시 count>0 보장(count==0 조기 반환) → 0 나눗셈 불가
MicRawStats computeMicRawStats(const int32_t* samples, size_t count) {
  MicRawStats st = {};
  st.n = (int32_t)count;
  if (count == 0) {
    st.tz = 32;                  // 데이터 없음 → 전 비트 0 취급 (ctz 미정의 회피)
    return st;
  }

  int32_t  smin  = INT32_MAX;
  int32_t  smax  = INT32_MIN;
  int64_t  sum   = 0;            // Σs,  |·| ≤ 2^41
  double   sumsq = 0.0;          // Σs², 최대 2^72 → double (int64 오버플로 회피)
  uint32_t oracc = 0;
  int32_t  nz    = 0;

  for (size_t i = 0; i < count; i++) {
    const int32_t s = samples[i];
    if (s < smin) smin = s;
    if (s > smax) smax = s;
    sum   += (int64_t)s;
    sumsq += (double)s * (double)s;
    oracc |= (uint32_t)s;
    if (s != 0) nz++;
  }

  st.min    = smin;
  st.max    = smax;
  st.mean   = sum / (int64_t)count;                        // ∈ [INT32_MIN, INT32_MAX]
  st.pp     = (int64_t)smax - (int64_t)smin;               // ∈ [0, 2^32-1]
  st.rms    = (int64_t)sqrt(sumsq / (double)count);        // ∈ [0, 2^31]
  st.or_acc = oracc;
  st.tz     = (oracc == 0) ? 32 : __builtin_ctz(oracc);    // 하위 항상-0 비트 폭 = 실제 정렬 폭
  st.nz     = nz;
  return st;
}
