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
