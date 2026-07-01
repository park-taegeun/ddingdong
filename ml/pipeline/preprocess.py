"""Step 1 — 02 전처리: 01_clips 검증·정규화 → 02_preprocessed.

- 16k mono 검증(위반 파일은 로그 + 스킵, 중단 X).
- peak 정규화(config), 길이 정책은 config.FIXED_DURATION_SEC (기본 원본 유지).
- 실측상 입력은 이미 16k mono Int16 → 리샘플/모노변환은 무동작, 검증은 유지.
- ★ write 전 02 를 auto-clean(stale 방지): 가드 도입 전 02 로 흘러든 빈 클립이
  재실행에도 남아 05 로 부활하던 회귀를 원천 차단(05 clean_final 과 동일 idiom).
"""

from __future__ import annotations

import logging
from pathlib import Path

from . import audio_io, config
from .config import Paths

log = logging.getLogger("ml.pipeline.preprocess")


def preprocess(paths: Paths, clean: bool = True) -> dict[str, dict]:
    """클래스별 전처리 실행. 반환: {class: {"ok": n, "skipped": [(stem, reason)]}}.

    clean=True(기본): write 전 02_preprocessed/{class} 를 비워 이전 실행의 stale 산출물
    (특히 가드 도입 전 흘러든 빈 클립)을 제거. --no-clean 로 opt-out(run_all).
    """
    if clean:
        removed = config.clean_stage_class_dirs(paths.preprocessed, config.DIR_PREPROCESSED)
        if removed:
            log.info("02 auto-clean: %s 제거(stale 방지)", [p.name for p in removed])
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
            # 빈·초단파 클립 가드: 하류 augment FFT(길이 0) 크래시 1차 차단.
            # probe.frames 로 디코딩 없이 판정(빈 6개 = frames 0). 데이터 원본은 건드리지 않음.
            if info.frames < config.MIN_SAMPLES:
                skipped.append(
                    (src.name, f"too_short frames={info.frames} "
                               f"({info.duration_sec:.3f}s<{config.MIN_DURATION_SEC}s)")
                )
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
