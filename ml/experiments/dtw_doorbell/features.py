"""오디오 → power-mel 2D 템플릿 (T, n_mels).

카테고리 4 "멜스펙트로그램 2D 템플릿"을 프레임 시퀀스로 표현: 각 시간프레임이
n_mels 차원 벡터 → DTW가 프레임열을 정렬. librosa 사용(카테고리 4: librosa=16k mono
변환/특징 전용). 멜 세부값은 constants.py (★가정, YAMNet 관례).

성능(분류 정확도)이 아니라 **분리 마진**을 보는 스파이크이므로, cosine 국소거리가
프레임 진폭 스케일에 불변이도록 power-mel(비음수)을 그대로 쓴다(dB 미변환).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .constants import (
    FMAX_HZ,
    FMIN_HZ,
    HOP_LENGTH,
    MEL_POWER,
    N_FFT,
    N_MELS,
    SAMPLE_RATE,
)


def load_mono(path: Path, target_sr: int = SAMPLE_RATE) -> np.ndarray:
    """wav → float32 mono [-1,1]. SR 다르면 리샘플, 스테레오면 다운믹스(방어적).

    (ml.pipeline.audio_io.load_mono 컨벤션 미러 — 격리 위해 import는 안 함.)
    """
    import soundfile as sf

    data, sr = sf.read(str(path), dtype="float32", always_2d=False)
    if data.ndim == 2:  # (frames, channels) → mono
        data = data.mean(axis=1)
    if sr != target_sr:
        import librosa

        data = librosa.resample(data, orig_sr=sr, target_sr=target_sr)
    return np.ascontiguousarray(data, dtype=np.float32)


def waveform_to_template(
    waveform: np.ndarray, sample_rate: int = SAMPLE_RATE
) -> np.ndarray:
    """float32 mono waveform → power-mel 템플릿 (T, N_MELS) float32.

    librosa (n_mels, T) → 전치. 프레임(행)이 DTW 정렬 단위.
    """
    import librosa

    if waveform.ndim != 1:
        raise ValueError(f"waveform은 1D여야 함 (mono), got shape={waveform.shape}")
    if waveform.size == 0:
        raise ValueError("빈 waveform")

    mel = librosa.feature.melspectrogram(
        y=waveform.astype(np.float32),
        sr=sample_rate,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH,
        n_mels=N_MELS,
        fmin=FMIN_HZ,
        fmax=FMAX_HZ,
        power=MEL_POWER,
    )  # (N_MELS, T), 비음수
    template = np.ascontiguousarray(mel.T, dtype=np.float32)  # (T, N_MELS)
    if template.shape[0] == 0:
        raise ValueError("멜 프레임 0개 — waveform이 hop보다 짧음")
    return template


def wav_to_template(path: Path, target_sr: int = SAMPLE_RATE) -> np.ndarray:
    """wav 경로 → power-mel 템플릿 (T, N_MELS). load + 특징추출 편의 래퍼."""
    return waveform_to_template(load_mono(path, target_sr), target_sr)
