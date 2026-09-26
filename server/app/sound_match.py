"""초인종 등록용 소리 비교 — power-mel 템플릿 + DTW-cosine 거리 (numpy 전용).

왜 복제인가: 비교 시제품 ml/experiments/dtw_doorbell 은 프로즌이고 특징 추출에
librosa · soundfile 을 쓰는데, 서버 venv(venv · venv_real)에는 둘 다 없다. 새 의존성
없이 같은 값을 내도록 STFT · 멜 필터뱅크를 numpy 로 다시 쓰고, DTW 는 dtw_doorbell
distance.py 의 exact 경로를 그대로 옮겼다. 서버 코드는 ml 패키지를 import 하지 않는다.

동등성 기준 = dtw_doorbell experiment.py 가 실제로 계산하는 경로 전체:
  wav(int16) → load_mono(float32 = int16 / 32768) → waveform_to_template
  (librosa melspectrogram) → dtw_cosine 안의 프레임 크롭 → cosine 비용행렬 → exact DTW.
서버 입력은 inference.audio_decode.decode_pcm16 이 낸 int16 / NORM_DIVISOR(32768.0)
이며 soundfile float32 읽기와 비트 단위로 같다(픽스처 테스트가 이 경로로 확인).
★ experiment.py 는 반드시 `--backend exact` 로 돌려야 여기서 잰 거리와 맞는다
  (기본값 auto 는 fastdtw 가 설치되면 근사 백엔드로 바뀐다).

librosa 재현 대상(librosa 0.11.0 설치 소스 기준): stft = periodic hann 창,
center=True, pad_mode="constant"(양끝 n_fft//2 영 패딩) / 멜 필터 = Slaney 멜 척도
(htk=False) + norm="slaney" 면적 정규화, float32 가중치.

호출처 = 테스트뿐. 제품 배선(/detect 계측)은 다음 PR.
기대값 픽스처 = app/tests/fixtures/make_sound_match_fixture.py (librosa 환경에서
프로즌 모듈을 import 해 생성).
"""

from __future__ import annotations

import numpy as np

# ── 상수: ml/experiments/dtw_doorbell/constants.py 복제 (값을 바꾸면 기준값 이식이 깨진다) ──
SAMPLE_RATE: int = 16000  # 카테고리 4 (16k mono)
# ★ 가정(원본 표기 유지) — 카테고리 4는 "멜스펙 2D 템플릿"만 명시, 세부값은 YAMNet 관례.
N_MELS: int = 64  # 가정: YAMNet 64-mel 관례
N_FFT: int = 400  # 가정: 25ms @ 16kHz
HOP_LENGTH: int = 160  # 가정: 10ms @ 16kHz
FMIN_HZ: float = 0.0
FMAX_HZ: float = 8000.0  # Nyquist
MEL_POWER: float = 2.0  # power 멜(에너지), dB 미변환
COSINE_EPS: float = 1e-8  # 근사-무음 프레임 0-division 가드
MAX_TEMPLATE_FRAMES: int = 400  # 가정(런타임 가드): ≈4초, 초과 시 중앙 크롭


def _hz_to_mel(hz: np.ndarray) -> np.ndarray:
    """Slaney 멜 척도 (1 kHz 아래 선형, 위 로그)."""
    hz = np.asarray(hz, dtype=np.float64)
    f_sp = 200.0 / 3
    mels = hz / f_sp
    min_log_mel = 1000.0 / f_sp
    logstep = np.log(6.4) / 27.0
    log_t = hz >= 1000.0
    mels[log_t] = min_log_mel + np.log(hz[log_t] / 1000.0) / logstep
    return mels


def _mel_to_hz(mels: np.ndarray) -> np.ndarray:
    f_sp = 200.0 / 3
    freqs = f_sp * mels
    min_log_mel = 1000.0 / f_sp
    logstep = np.log(6.4) / 27.0
    log_t = mels >= min_log_mel
    freqs[log_t] = 1000.0 * np.exp(logstep * (mels[log_t] - min_log_mel))
    return freqs


def _mel_filterbank() -> np.ndarray:
    """(N_MELS, 1 + N_FFT//2) float32 삼각 필터, Slaney 면적 정규화."""
    fftfreqs = np.fft.rfftfreq(N_FFT, d=1.0 / SAMPLE_RATE)
    mel_f = _mel_to_hz(
        np.linspace(_hz_to_mel(np.array([FMIN_HZ]))[0], _hz_to_mel(np.array([FMAX_HZ]))[0], N_MELS + 2)
    )
    fdiff = np.diff(mel_f)
    ramps = np.subtract.outer(mel_f, fftfreqs)
    weights = np.zeros((N_MELS, 1 + N_FFT // 2), dtype=np.float32)
    for i in range(N_MELS):
        lower = -ramps[i] / fdiff[i]
        upper = ramps[i + 2] / fdiff[i + 1]
        weights[i] = np.maximum(0, np.minimum(lower, upper))
    weights *= (2.0 / (mel_f[2 : N_MELS + 2] - mel_f[:N_MELS]))[:, np.newaxis]
    return weights


_MEL_BASIS = _mel_filterbank()
# periodic hann (scipy get_window(fftbins=True) 과 같은 식)
_WINDOW = 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(N_FFT) / N_FFT)


def waveform_to_template(waveform: np.ndarray, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """1D float32 mono waveform(16 kHz, [-1, 1]) → power-mel 템플릿 (T, N_MELS) float32.

    T = 1 + len // HOP_LENGTH (center 패딩). 프레임(행)이 DTW 정렬 단위.
    """
    if sample_rate != SAMPLE_RATE:
        raise ValueError(f"샘플레이트 불일치: {sample_rate} != {SAMPLE_RATE} (리샘플 미지원)")
    waveform = np.asarray(waveform)
    if waveform.ndim != 1:
        raise ValueError(f"waveform은 1D여야 함 (mono), got shape={waveform.shape}")
    if waveform.size == 0:
        raise ValueError("빈 waveform")

    y = np.pad(waveform.astype(np.float32), N_FFT // 2, mode="constant")
    frames = np.lib.stride_tricks.sliding_window_view(y, N_FFT)[::HOP_LENGTH]
    power = np.abs(np.fft.rfft(frames * _WINDOW, axis=1)) ** MEL_POWER  # (T, 1 + N_FFT//2)
    return np.ascontiguousarray(power @ _MEL_BASIS.T, dtype=np.float32)


def _clip_frames(template: np.ndarray) -> np.ndarray:
    """프레임수 상한 가드(O(T^2) DTW 유계화). 초과 시 중앙 크롭."""
    t = template.shape[0]
    if t <= MAX_TEMPLATE_FRAMES:
        return template
    start = (t - MAX_TEMPLATE_FRAMES) // 2
    return template[start : start + MAX_TEMPLATE_FRAMES]


def _l2_normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.sqrt(np.sum(mat * mat, axis=1, keepdims=True))
    return mat / np.maximum(norms, COSINE_EPS)


def _dtw_exact(cost: np.ndarray) -> float:
    """비용행렬 위 정확 DTW 누적 → (Ta+Tb) 정규화 경로비용."""
    ta, tb = cost.shape
    acc = np.full((ta + 1, tb + 1), np.inf, dtype=np.float64)
    acc[0, 0] = 0.0
    for i in range(1, ta + 1):
        ci = cost[i - 1]
        row = acc[i]
        prev = acc[i - 1]
        for j in range(1, tb + 1):
            row[j] = ci[j - 1] + min(prev[j], row[j - 1], prev[j - 1])
    return float(acc[ta, tb] / (ta + tb))


def dtw_cosine_distance(template: np.ndarray, query: np.ndarray) -> float:
    """두 멜 템플릿 (T, N_MELS) 간 DTW-cosine 거리. 작을수록 유사, 0 이상."""
    for name, t in (("template", template), ("query", query)):
        if t.ndim != 2 or t.shape[0] == 0 or t.shape[1] != N_MELS:
            raise ValueError(f"{name}은 (T>0, {N_MELS}) 2D 여야 함, got shape={t.shape}")
    a = _l2_normalize(_clip_frames(np.asarray(template, dtype=np.float32)))
    b = _l2_normalize(_clip_frames(np.asarray(query, dtype=np.float32)))
    return _dtw_exact(1.0 - a @ b.T)
