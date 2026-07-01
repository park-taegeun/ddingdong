"""tf.signal 로그멜 프론트엔드 — YAMNet 파라미터와 일치(카테고리 4).

용도: SpecAugment(logmel 모드)가 마스킹할 **실제 로그멜**을 waveform 에서 계산.
      기본 학습 경로(embedding 모드)는 frozen hub YAMNet 이 내부에서 자체 로그멜을
      계산하므로 이 프론트엔드를 쓰지 않는다(그 경우 SpecAugment 는 backbone 블랙박스
      안에 도달 불가 — README '설계 노트' 참조).

decisions.md 카테고리 4 규격: 16kHz mono, 25ms/10ms STFT, 64 mel(125–7500Hz).
"""

from __future__ import annotations

import tensorflow as tf

from . import config


def waveform_to_log_mel(
    waveform: tf.Tensor,
    sample_rate: int = config.SAMPLE_RATE,
    mel_bands: int = config.MEL_BANDS,
) -> tf.Tensor:
    """[num_samples] float32 waveform → [frames, mel_bands] 로그멜 스펙트로그램.

    log(mel + 1e-6) 스케일. YAMNet 의 프레임 파라미터와 동일한 창/홉.
    """
    win = int(round(config.STFT_WINDOW_SEC * sample_rate))
    hop = int(round(config.STFT_HOP_SEC * sample_rate))
    fft_len = 1
    while fft_len < win:
        fft_len *= 2  # win 이상인 최소 2의 거듭제곱

    stft = tf.signal.stft(
        waveform, frame_length=win, frame_step=hop, fft_length=fft_len,
        window_fn=tf.signal.hann_window,
    )
    mag = tf.abs(stft)  # [frames, fft_len/2+1]
    num_bins = fft_len // 2 + 1
    mel_matrix = tf.signal.linear_to_mel_weight_matrix(
        num_mel_bins=mel_bands,
        num_spectrogram_bins=num_bins,
        sample_rate=sample_rate,
        lower_edge_hertz=config.MEL_MIN_HZ,
        upper_edge_hertz=config.MEL_MAX_HZ,
    )
    mel = tf.matmul(mag, mel_matrix)          # [frames, mel_bands]
    return tf.math.log(mel + 1e-6)
