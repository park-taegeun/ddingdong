"""합성 더미 생성기 — 실제 데이터(EPERM) 없이 파이프라인 로직 검증용.

클래스별 16k mono wav(sine + noise)를 <root>/01_clips/{class} 에 생성.
실제 클립 규격(16kHz mono Int16)과 동일. 길이는 클립마다 살짝 다르게(가변 길이 경로 검증).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from . import audio_io, config

# 클래스별 대표 주파수(구분용, 의미 없음)
_CLASS_FREQ = {"doorbell": 880.0, "knock": 220.0, "fire_alarm": 3000.0}


def make_dummy_dataset(root: Path, per_class: int = 6, seed: int = 0) -> Path:
    """더미 데이터셋 생성 후 root 반환. 빈 스테이지 폴더도 함께 생성(실측 구조 모사)."""
    rng = np.random.default_rng(seed)
    for cls in config.CLASSES:
        freq = _CLASS_FREQ[cls]
        for i in range(per_class):
            dur = 0.6 + 0.4 * float(rng.random())  # 0.6~1.0s 가변
            n = int(dur * config.SAMPLE_RATE)
            t = np.arange(n) / config.SAMPLE_RATE
            tone = 0.6 * np.sin(2 * np.pi * freq * t)
            noise = 0.05 * rng.standard_normal(n)
            y = (tone + noise).astype(np.float32)
            audio_io.save_wav(root / config.DIR_CLIPS / cls / f"{cls}_{i:03d}.wav", y)

    # 실측 구조 모사: 나머지 스테이지 폴더는 빈 상태로 존재만
    for sub in (config.DIR_PREPROCESSED, config.DIR_AUGMENTED, config.DIR_FINAL):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root
