"""Step 1 — 02 전처리: 01_clips 검증·정규화 → 02_preprocessed.

- 16k mono 검증(위반 파일은 로그 + 스킵, 중단 X).
- peak 정규화(config), 길이 정책은 config.FIXED_DURATION_SEC (기본 원본 유지).
- 실측상 입력은 이미 16k mono Int16 → 리샘플/모노변환은 무동작, 검증은 유지.
"""

from __future__ import annotations

import logging
from pathlib import Path

from . import audio_io, config
from .config import Paths

log = logging.getLogger("ml.pipeline.preprocess")


def preprocess(paths: Paths) -> dict[str, dict]:
    """클래스별 전처리 실행. 반환: {class: {"ok": n, "skipped": [(stem, reason)]}}."""
    stats: dict[str, dict] = {}
    for cls in config.CLASSES:
        src_dir = paths.clips / cls
        dst_dir = paths.preprocessed / cls
        ok = 0
        skipped: list[tuple[str, str]] = []
        for src in audio_io.iter_audio_files(src_dir):
            info = audio_io.probe(src)
            if info.samplerate != config.SAMPLE_RATE:
                skipped.append((src.name, f"samplerate={info.samplerate}≠{config.SAMPLE_RATE}"))
                log.warning("SKIP %s (%s)", src.name, skipped[-1][1])
                continue
            if info.channels != config.CHANNELS:
                skipped.append((src.name, f"channels={info.channels}≠mono"))
                log.warning("SKIP %s (%s)", src.name, skipped[-1][1])
                continue

            y = audio_io.load_mono(src)
            if config.PEAK_NORMALIZE:
                y = audio_io.peak_normalize(y)
            if config.FIXED_DURATION_SEC is not None:
                y = audio_io.fix_duration(y, config.FIXED_DURATION_SEC)

            audio_io.save_wav(dst_dir / f"{src.stem}.wav", y)
            ok += 1

        stats[cls] = {"ok": ok, "skipped": skipped}
        log.info("preprocess %-11s ok=%d skipped=%d", cls, ok, len(skipped))
    return stats
