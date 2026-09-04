// 띵동 PoC firmware - 마이크 더미 테스트 (5/10, PoC Day 4)
//
// micTask 단독: i2s_read 폴링 + M2 계측(raw int32 통계) + M4 변환(int16 PCM)
//              + M5-a 링버퍼 적재(2초 PSRAM 상시 보유).
// ★ 계층 이력 (decisions.md 카테고리 20 "계측 → 실측 → 판정" 패턴 준용):
//   M2 = 계측(or_acc/tz 관측 전용) → M3 = ④런타임 실측(2026-08-20) → M4 = 판정 = shift 확정.
//   M4는 실측으로 확정된 shift(=14)로 int16 변환만 수행한다.
//   M5-a = 다시 계측 계층. 매 버퍼 int16 변환 → PSRAM 링버퍼 적재 + 적재 상태 관측.
//   M5-a2 = 본 단계 = **여전히 계측 계층**. M5-a ④런타임(2026-09-03)이 드러낸 관측
//   설계 결함(로그 게이트가 시간의 2%만 관측 → 과도 이벤트 미검출)을 윈도우 진폭
//   누적으로 해소한다. 임계값·트리거·상태머신·스냅샷 추출은 M5-c 소관으로 여전히 0줄.
//   트리거 판정 / DC 오프셋 보정 / 업로드는 여전히 0줄 (하단 defer 주석 참조).
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

  // ── M5-a: 2초(32슬롯) int16 링버퍼를 PSRAM에 확보 ──
  // ★ 지역변수로 받는다 — micTask는 반환하지 않으므로 수명 = 태스크 수명이고,
  //   static/전역을 신설하지 않아 내부 SRAM 순증이 0으로 유지된다(mic_common.h 주석).
  // ★ 할당 실패(nullptr) 시 링버퍼만 비활성이고 M2 계측 / M4 변환은 기존 그대로 계속된다
  //   = graceful degradation. 부팅 실패로 만들지 않는다(initMicI2S 실패 처리와 동형).
  int16_t* const ring_base = initMicRingBuffer();
  MicRingStatus  ring      = {};   // write_idx=0 / wraps=0 / gaps=0 / slots_filled=0

  // ── M5-a2: 윈도우(MIC_LOG_EVERY_N_BUFFERS 버퍼) 진폭 누적 ──
  // ★ 왜 필요한가 (2026-09-03 M5-a ④런타임 실측이 드러낸 **관측 설계 결함**)
  //   로그 게이트가 50버퍼당 1버퍼만 출력한다 = 64ms / 3.2s = **시간의 2%만 관측**이다.
  //   그 세션에서 의도적으로 친 박수가 42윈도우 전부에서 미검출됐다(i16 rms 60~97 평탄,
  //   max 251). 8/20 M3의 박수 max 18,099(int16 풀스케일 55%)와 72배 차이 = 마이크가
  //   아니라 관측이 이벤트를 지나친 것이다(박수 약 100ms가 2% 창에 들 확률 ≈ 2%,
  //   10회 쳐도 기대 검출 0.2회). 8/20에 잡힌 것이 오히려 우연이었다.
  //   → convertMicRawToInt16이 이미 **매 버퍼** 산출하고 있으나 게이트 밖에서 버려지던
  //     MicI16Stats를 윈도우 단위로 누적해 실질 관측률을 100%로 올린다.
  //     여전히 관측 전용 — 임계값·트리거·판정·상태머신은 0줄(M5-c 소관, decisions.md 20).
  //
  // ★ rms를 최댓값과 최솟값 둘 다 잡는 이유
  //   최댓값만으로는 이벤트는 잡히나 **무음 바닥**이 안 잡힌다. M5-c 임계값은 "바닥과
  //   이벤트의 분리점"이므로 양쪽이 다 필요하다(카테고리 3 "80% 지점" 근거 산출용).
  //
  // ★ 자료형 근거 (전 분기 값 도메인 열거)
  //   - i16.max / i16.min ∈ [INT16_MIN, INT16_MAX] = [-32768, 32767] (convert가 clamp 보장)
  //   - ⚠️ |INT16_MIN| = 32768 은 int16으로 표현 불가하다. 절댓값을 int16에 담으면
  //     wrap-around로 -32768이 되어 **최대 진폭이 최소값으로 부호 반전**한다 = 본 계층의
  //     유일한 진짜 함정. 그래서 절댓값 계산도 보관도 전부 int32로 한다.
  //     → win_peak ∈ [0, 32768] 안전 (int32 상한 대비 여유 2^16배).
  //   - i16.rms  ∈ [0, 32768]                                   → int32 안전
  //   - i16.clip ∈ [0, n] ≤ MIC_DMA_BUF_LEN = 1024
  //     윈도우 합 ≤ MIC_LOG_EVERY_N_BUFFERS × 1024 = 50 × 1024 = 51,200 → uint32 안전
  //   - win_nbuf ∈ [0, MIC_LOG_EVERY_N_BUFFERS] = [0, 50]
  //
  // ★ 센티넬 상수를 두지 않는다
  //   최솟값 추적에 INT32_MAX 같은 매직 초기값을 쓰지 않고 win_nbuf == 0(= 이번 윈도우의
  //   첫 표본인가)으로 판정한다. **센티넬 자체가 존재하지 않으므로 센티넬이 로그로 새어나갈
  //   경로도 없다.** 표본이 0건인 윈도우는 아래 출력이 별도 분기로 갈린다(전 분기 열거).
  //
  // ★ RAM: 전부 micTask 지역변수 = 이미 할당된 4KiB 태스크 스택 내부.
  //   static/전역 신설 0 → 내부 SRAM 순증 0 (mic_common.h 컨벤션, PR #36/#38/#39/#41 연속).
  int32_t  win_peak    = 0;   // max(|min|,|max|)의 윈도우 최댓값 ∈ [0, 32768]
  int32_t  win_rms_max = 0;   // rms 윈도우 최댓값                ∈ [0, 32768]
  int32_t  win_rms_min = 0;   // rms 윈도우 최솟값                ∈ [0, 32768] (nbuf>0에서만 유효)
  uint32_t win_clip    = 0;   // clip 윈도우 합계                 ∈ [0, 51200]
  uint32_t win_nbuf    = 0;   // 누적 버퍼 수 = 이 윈도우의 실제 관측 표본 수 ∈ [0, 50]

  size_t   bytes_read  = 0;
  uint32_t buf_count   = 0;
  uint32_t err_count   = 0;
  uint32_t window_idx  = 0;

  for (;;) {
    const esp_err_t err = i2s_read(MIC_I2S_PORT, audio_buffer.raw, sizeof(audio_buffer.raw),
                                   &bytes_read, portMAX_DELAY);
    if (err != ESP_OK) {
      // ★ 이 반복은 적재가 통째로 누락된다 = 링버퍼 시간축에 64ms 구멍이 생긴다.
      //   buf_count를 올리지 않으므로 로그 윈도우 위상도 어긋나지 않는다(기존 거동 유지).
      ring.gaps++;
      if ((++err_count % 10) == 1) {
        Serial.printf("[mic] read failed: 0x%x (%s) #%u\n",
                      err, esp_err_to_name(err), (unsigned)err_count);
      }
      continue;
    }

    // ── M5-a 적재: **매 버퍼** int16 변환 → PSRAM 링버퍼 슬롯에 직접 기록 ──
    // ★ 매 버퍼로 뺀 것은 convertMicRawToInt16 하나뿐이다. computeMicRawStats는 아래
    //   로그 게이트 안에 그대로 둔다 — raw 도메인 Σs²가 최대 2^72라 double 누산이
    //   불가피한데, ESP32-S3의 FPU는 single-precision 전용이라 double은 소프트웨어
    //   에뮬레이션이다. 버퍼당 1024회 × 15.625버퍼/초 ≈ 초당 16,000회 에뮬레이션 곱셈이
    //   상시 CPU 예산을 잠식한다. 반면 convertMicRawToInt16의 누산은 int64 정수(Σv² 최대
    //   2^40)라 매 버퍼 실행이 안전하다(mic_common.cpp 오버플로 가드 주석).
    // ★ n 상한: i2s_read는 요청 크기(sizeof(audio_buffer.raw)=4096B)를 넘겨 쓰지 않으므로
    //   n ≤ 1024 = MIC_DMA_BUF_LEN = 슬롯 용량이다. 그래도 슬롯 경계 초과 쓰기는 유일한
    //   메모리 손상 벡터라 방어적으로 한 번 더 접는다(비용 = 비교 1회).
    size_t n = bytes_read / sizeof(int32_t);
    if (n > (size_t)MIC_DMA_BUF_LEN) {
      n = (size_t)MIC_DMA_BUF_LEN;
    }

    MicI16Stats i16       = {};
    bool        i16_valid = false;

    int16_t* const slot = micRingSlot(ring_base, ring.write_idx);
    if (slot != nullptr) {
      // ★ dst가 PSRAM 슬롯이라 src(DMA 4KiB, 내부 SRAM)와 **물리적으로 분리**된다 →
      //   convertMicRawToInt16의 in-place 겹침 조건 자체가 불성립한다(겹칠 주소가 없다).
      //   union의 i16 뷰를 경유하지 않으므로 복사 단계도 사라진다.
      // ★ 부수 효과: audio_buffer.raw가 이번 반복 내내 원본 그대로 남는다 → 아래 raw hex
      //   덤프는 M4 때와 동일하게 **변환 전 값**을 출력한다(덤프 값 회귀 0).
      i16       = convertMicRawToInt16(audio_buffer.raw, slot, n);
      i16_valid = true;
      micRingAdvance(&ring);

      // ── M5-a2 윈도우 누적 (관측 전용 — 최대/최소/합계만. 비교·판정 임계값 0개) ──
      // ★ 절댓값은 int32에서만 계산한다: -(int32_t)(int16_t)(-32768) = +32768 로 안전.
      //   int16 중간 변수를 두면 그 지점에서 -32768로 되접힌다(위 자료형 근거).
      // ★ win_nbuf == 0 검사를 rms **최솟값에만** 붙인 이유 (전 분기 열거):
      //   pk, i16.rms ∈ [0, 32768]이고 리셋값도 0이다.
      //   - 최댓값 계열: 첫 표본이 0보다 크면 `>`가 참이라 갱신되고, 0이면 리셋값 0이
      //     이미 정답이라 갱신이 불필요하다 → 두 분기 모두 결과가 옳다. 가드 불필요.
      //   - 최솟값: 리셋값 0이 하한이라 `<`가 영원히 거짓이 된다 → 가드가 없으면
      //     **항상 0이 출력**되어 무음 기준선이 통째로 무의미해진다. 그래서 여기만 붙인다.
      const int32_t a_max = (i16.max >= 0) ? (int32_t)i16.max : -(int32_t)i16.max;
      const int32_t a_min = (i16.min >= 0) ? (int32_t)i16.min : -(int32_t)i16.min;
      const int32_t pk    = (a_max >= a_min) ? a_max : a_min;

      if (pk      > win_peak)                     win_peak    = pk;
      if (i16.rms > win_rms_max)                  win_rms_max = i16.rms;
      if (win_nbuf == 0 || i16.rms < win_rms_min) win_rms_min = i16.rms;
      win_clip += i16.clip;
      win_nbuf++;
    }

    // ── M2 계측: 윈도우(MIC_LOG_EVERY_N_BUFFERS 버퍼)마다 raw int32 통계 1줄 출력 ──
    // ★ 측정 조건(uptime / warmup 상태)이 로그에 자동 동반 → 사후 판별 가능
    //   (ToF가 near·center를 강제 동반시킨 것과 동형, decisions.md §9.3(b)).
    if ((++buf_count % MIC_LOG_EVERY_N_BUFFERS) == 1) {
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
      //   ※ M5-a 갱신: 링버퍼가 살아 있으면 변환 dst가 PSRAM이라 raw를 덮어쓰지 않는다
      //     → 그 경로에선 이 순서 제약이 애초에 성립하지 않는다. 아래 폴백(링버퍼 미가용)
      //     경로만 union 뷰에 쓰므로, 그 경우를 위해 이 자리와 순서를 그대로 보존한다.
      // ★ M2 로그 줄에 덧붙이지 말고 별도 줄로 출력한다: 2026-08-20 M3 실측에서
      //   줄이 길어 시리얼 전송 중 깨진 라인([PARTIAL])이 6건 발생했다.
      if (!i16_valid) {
        i16 = convertMicRawToInt16(audio_buffer.raw, audio_buffer.i16, n);
      }

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

      // ── M5-a 관측: 링버퍼 적재 상태 (별도 줄 — 위 [PARTIAL] 선례로 줄 병합 금지) ──
      //   ring=on/OFF = PSRAM 할당 성공 여부 / idx = 다음 적재 슬롯 / wraps = 한 바퀴 횟수
      //   gaps = i2s_read 실패로 비어버린 슬롯 수(시간축 구멍) / filled = 채워진 슬롯 수
      Serial.printf("[mic][M5a] w=%u ring=%s idx=%u wraps=%u gaps=%u filled=%u/%u"
                    " | psram_free=%u\n",
                    (unsigned)window_idx,
                    (ring_base != nullptr) ? "on" : "OFF",
                    (unsigned)ring.write_idx, (unsigned)ring.wraps,
                    (unsigned)ring.gaps, (unsigned)ring.slots_filled,
                    (unsigned)MIC_RING_SLOTS,
                    (unsigned)ESP.getFreePsram());

      // ── M5-a2 관측: 윈도우 진폭 누적 (별도 줄 — 아래 줄 길이 근거) ──
      //   nbuf = 이 윈도우가 실제로 누적한 버퍼 수. 정상 = 50.
      //          ★ 첫 윈도우(w=1)만 1이다 — 게이트가 (++buf_count % 50) == 1 이라
      //            buf_count = 1, 51, 101 … 에서 열린다. w=1은 buf_count=1 한 건만
      //            누적된 상태이고, w=2는 buf_count 2~51 = 정확히 50건이다.
      //            (2026-09-03 실측 교차검증: w=5에서 ring idx=9 wraps=6 → 전진 201회
      //             = 6×32+9, 그리고 buf_count(w=5) = 1+4×50 = 201 로 정확히 일치.)
      //          ★ i2s_read 실패분은 buf_count도 누적도 올리지 않으므로 nbuf < 50 이면
      //            그 자체가 관측 손실 신호가 아니라 첫 윈도우이거나 링 미가용이다.
      //   peak = max(|min|, |max|) 윈도우 최댓값 / rms=[최솟값..최댓값] / clip = 윈도우 합.
      // ★ 줄 길이 상한 설계 (근거유형 = 실측, ~/ddingdong-측정결과/mic_m5a_2026-09-03):
      //   손상률이 줄 길이에 단조 증가했다 — 141B 57.9% / 108B 12.5% / 81B 16.7% /
      //   80B 0% / 78B 0%. 80B 이하 62줄에서 손상 0건. 본 줄은 모든 필드가 uint32/int32
      //   최대 자릿수인 최악값(호스트 snprintf 실측)에서도 74B라 그 구간 안에 든다
      //   (전형값 54B). M5a 줄에 얹으면 약 148B = 손상률 57.9% 구간으로 들어간다.
      // ⚠️ 단 이 상관은 실측 상관일 뿐 인과 규명이 아니다 — 근본 원인 판단은 PR 본문 참조.
      if (win_nbuf > 0) {
        Serial.printf("[mic][M5a2] w=%u nbuf=%u peak=%d rms=[%d..%d] clip=%u\n",
                      (unsigned)window_idx, (unsigned)win_nbuf,
                      (int)win_peak, (int)win_rms_min, (int)win_rms_max,
                      (unsigned)win_clip);
      } else {
        // 링버퍼 미가용(ps_malloc 실패) 경로 = 매 버퍼 변환 자체가 없어 표본이 0건이다.
        // 0을 찍으면 "무음"으로 오독되므로 상태를 그대로 밝힌다. 이 분기가 존재하는 한
        // win_rms_min의 리셋값 0이 유효값처럼 출력될 경로는 없다.
        Serial.printf("[mic][M5a2] w=%u nbuf=0 peak=n/a rms=[n/a] clip=n/a (ring OFF)\n",
                      (unsigned)window_idx);
      }

      // 윈도우 리셋 — 출력 직후에 둔다. 다음 윈도우는 이 반복 **이후**의 버퍼부터 담는다.
      win_peak    = 0;
      win_rms_max = 0;
      win_rms_min = 0;
      win_clip    = 0;
      win_nbuf    = 0;
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

    // ── [mic][defer] RMS 트리거 임계값: 미구현 (M5-c 소관) ──
    //   ★ 이력 보존 — 삭제하지 않고 갱신한다.
    //   M5-a 현황: **링버퍼는 확보됐으나 판정은 여전히 0줄이다.** 2초 스냅샷을 항상 들고
    //             있게 됐을 뿐, 언제 그것을 뽑을지(임계값·트리거)는 실측 전이라 미정이다.
    //             적재와 판정을 한 PR에 섞지 않는 이유 = decisions.md 카테고리 20.
    //   M5-a2 현황: **관측 수단이 확보됐다. 판정은 여전히 0줄이다.**
    //             2026-09-03 ④런타임에서 드러난 사실 = 로그 게이트가 시간의 2%만 관측해
    //             **과도 이벤트 관측이 구조적으로 불가능**했다(의도적으로 친 박수 미검출).
    //             8/20 M3에서 박수 max 296,542,208이 잡힌 것은 **우연이었다**.
    //             그 2% 샘플링 위에서 산출한 배경 rms는 "스냅샷 42개"일 뿐 바닥이 아니다.
    //             → 아래 판정 방법 ①의 "무음 기준선"은 M5-a2의 rms 최솟값(win_rms_min)으로
    //               재야 하며, ②의 이벤트 진폭은 peak / rms 최댓값으로 잰다.
    //   현 상태 : i16 rms를 로그로 관측만 한다. 임계값·판정·상태머신 0줄.
    //   미결 사유: 카테고리 3 "80% 지점"의 기준선이 미확정이다.
    //   ⚠️ M3 배경 rms 2,104,135 ~ 2,646,435 를 무음 기준선으로 쓰지 말 것 —
    //      랩실 사람 대화가 포함된 값이라 무음이 아니다. 이 값으로 임계값을 정하면
    //      실제 무음 환경에서 트리거가 상시 발화한다.
    //   판정 방법: ① 조용한 환경(야간/무인) 무음 기준선 재측정 →
    //             ② 초인종·노크 실측 진폭 확보 → ③ 두 분포의 분리점에서 80% 지점 도출.
    //             ①②의 마진이 불충분하면 임계값 대신 다른 특징량으로 pivot 후 §9 보고.

    // ── [mic][defer] 스냅샷 추출 + pre/post 비율: 미구현 (M5-c 소관) ──
    //   현 상태 : 링버퍼는 최근 32슬롯(2.048초)을 **항상** 보유한다. 그 안에서 어느 구간을
    //             잘라 페이로드로 만들지는 0줄이다(추출 함수 자체가 없다).
    //   확정된 것: G29 = **B안 하이브리드** — 트리거 시점 기준 pre-roll 일부 + post 일부를
    //             합쳐 2초를 구성한다. 근거 = 트리거는 소리가 이미 시작된 뒤에 걸리므로
    //             전량 pre-roll이면 소리 본체가, 전량 post면 어택이 빠진다.
    //   미확정  : **pre/post 비율.** 그래서 본 계층은 비율 상수를 신설하지 않았다 —
    //             실측 전에 박으면 죽은 상수가 되고, 되돌릴 때 적재 코드까지 흔들린다.
    //   판정 방법: ① M5-b 실측에서 초인종·노크의 **어택 길이**(상승 구간 지속시간)와
    //             ② RMS 트리거가 걸리는 **지연**(소리 시작 → 임계 초과까지 몇 슬롯인지)을
    //                로그 윈도우 단위로 측정한다.
    //             ③ pre ≥ (어택 길이 + 트리거 지연)이 되도록 비율을 산출하고, 남는 몫을
    //                post에 배분한다. pre + post = 32슬롯을 넘으면 MIC_RING_SLOTS를 재산출.
    //   ⚠️ 링버퍼는 "최근 N슬롯 상시 보유" 구조라 비율과 무관하게 성립한다 — 비율이
    //      바뀌어도 본 적재 코드는 손댈 필요가 없다.
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
