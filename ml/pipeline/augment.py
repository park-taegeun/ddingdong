"""Step 3 — 03 증강 (train split만): waveform 증강 → 03_augmented.

카테고리 5 스펙 그대로:
  time-stretch ×0.85/1.15 · BG noise SNR(클래스별) · volume -6dB · pitch ±2semitone(한국 환경음만)
★ SpecAugment 는 여기서 굽지 않음(학습 시점). val/test 는 절대 증강 X.
증강본 파일명 = "{원본stem}__{augtag}.wav" (추적성 — base stem 은 '__' 앞부분).
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import librosa
import numpy as np

from . import audio_io, config
from .config import Paths
from .split import load_split_manifest

log = logging.getLogger("ml.pipeline.augment")

AUG_SEP = "__"  # base stem 구분자. 원본 stem 에는 이 문자열이 없다고 가정.


def base_stem(name: str) -> str:
    """증강본/원본 파일명에서 원본 stem 추출 ('__augtag' 제거)."""
    stem = Path(name).stem
    return stem.split(AUG_SEP, 1)[0]


def _rng_for(stem: str, salt: str) -> np.random.Generator:
    """stem+salt 안정 해시로 시드 → 재현 가능한 잡음(파일마다 다르되 결정적).

    ★ 내장 hash() 는 PYTHONHASHSEED 로 프로세스마다 달라져 재현성이 깨짐 → blake2b 사용.
    """
    key = f"{config.SEED}|{stem}|{salt}".encode("utf-8")
    seed = int.from_bytes(hashlib.blake2b(key, digest_size=4).digest(), "big")
    return np.random.default_rng(seed)


def _pink_noise(n: int, rng: np.random.Generator) -> np.ndarray:
    """1/f 핑크 노이즈(주파수 영역 1/sqrt(f) 필터)."""
    if n <= 0:  # 길이 0 → rfft "Invalid number of FFT data points (0)" 방어(최종 안전판)
        return np.zeros(0, dtype=np.float32)
    white = rng.standard_normal(n)
    spec = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n)
    scale = np.ones_like(freqs)
    scale[1:] = 1.0 / np.sqrt(freqs[1:])
    pink = np.fft.irfft(spec * scale, n=n)
    return pink.astype(np.float32)


def _noise_like(y: np.ndarray, stem: str, snr_db: float) -> np.ndarray:
    """길이 맞춘 잡음을 목표 SNR 로 스케일. BG_NOISE_DIR 있으면 실제 파일 사용."""
    rng = _rng_for(stem, f"noise{snr_db}")
    if config.BG_NOISE_DIR is not None:
        pool = list(audio_io.iter_audio_files(config.BG_NOISE_DIR))
        if pool:
            noise = audio_io.load_mono(pool[rng.integers(len(pool))])
            noise = np.resize(noise, y.shape[0])
        else:
            noise = _pink_noise(y.shape[0], rng)
    elif config.BG_NOISE_KIND == "white":
        noise = rng.standard_normal(y.shape[0]).astype(np.float32)
    else:
        noise = _pink_noise(y.shape[0], rng)

    sig_rms = float(np.sqrt(np.mean(y**2))) or 1e-9
    noise_rms = float(np.sqrt(np.mean(noise**2))) or 1e-9
    target_noise_rms = sig_rms / (10.0 ** (snr_db / 20.0))
    return noise * (target_noise_rms / noise_rms)


def _pitch_targets(stem: str) -> list[float]:
    """이 stem 에 적용할 pitch shift semitone 목록(카테고리 5: 한국 환경음만)."""
    mode = config.PITCH_SHIFT_MODE
    if mode == "none":
        return []
    if mode == "all":
        return list(config.PITCH_SHIFT_SEMITONES)
    # korean_only
    if config.KOREAN_SOURCE_MARKERS and any(m in stem for m in config.KOREAN_SOURCE_MARKERS):
        return list(config.PITCH_SHIFT_SEMITONES)
    return []


def _augment_one(y: np.ndarray, cls: str, stem: str) -> dict[str, np.ndarray]:
    """원본 waveform 하나 → {augtag: waveform}. peak 정규화는 저장 시 save_wav 가 clip."""
    if y.shape[0] < config.MIN_SAMPLES:  # 2차 방어: 빈/초단파는 증강 불가 → 산출물 0
        return {}
    out: dict[str, np.ndarray] = {}
    for rate in config.TIME_STRETCH_RATES:
        tag = f"ts{str(rate).replace('.', '')}"  # 0.85→ts085
        out[tag] = librosa.effects.time_stretch(y, rate=rate)
    for snr in config.BG_NOISE_SNR_DB[cls]:
        tag = f"snr{int(snr)}"
        out[tag] = y + _noise_like(y, stem, snr)
    gain = 10.0 ** (config.VOLUME_GAIN_DB / 20.0)
    out[f"vol{int(config.VOLUME_GAIN_DB)}"] = y * gain
    for n_steps in _pitch_targets(stem):
        tag = f"ps{'+' if n_steps > 0 else ''}{int(n_steps)}"
        out[tag] = librosa.effects.pitch_shift(y, sr=config.SAMPLE_RATE, n_steps=n_steps)
    return out


def augment(paths: Paths, clean: bool = True) -> dict[str, int]:
    """train split 클립에만 증강 적용 → 03_augmented. 반환: {class: 증강본 개수}.

    clean=True(기본): write 전 03_augmented/{class} 를 비워 이전 실행의 stale 증강본
    (파라미터/split 변경 시 잔재)을 제거. 02 preprocess 와 동일 정합. --no-clean 로 opt-out.
    """
    if clean:
        removed = config.clean_stage_class_dirs(paths.augmented, config.DIR_AUGMENTED)
        if removed:
            log.info("03 auto-clean: %s 제거(stale 방지)", [p.name for p in removed])
    manifest = load_split_manifest(paths)
    train_rows = [r for r in manifest if r["split"] == "train"]
    counts: dict[str, int] = {c: 0 for c in config.CLASSES}

    pitch_applicable = any(_pitch_targets(r["stem"]) for r in train_rows)
    if config.PITCH_SHIFT_MODE == "korean_only" and not pitch_applicable:
        log.warning(
            "pitch shift 적용 대상 0 (mode=korean_only, KOREAN_SOURCE_MARKERS=%r). "
            "→ 한국 환경음 소스 명명 규칙 확인 후 config.KOREAN_SOURCE_MARKERS 설정 필요 "
            "(막힘 트리거: 학부생 결정).",
            config.KOREAN_SOURCE_MARKERS,
        )

    for row in train_rows:
        cls, stem = row["class"], row["stem"]
        y = audio_io.load_mono(Path(row["filepath"]))
        if y.shape[0] < config.MIN_SAMPLES:  # 2차 방어(preprocess 가드 누락분 대비)
            log.warning(
                "SKIP augment %s (too_short samples=%d<%d) — preprocess 1차 가드 이후 잔여분",
                stem, y.shape[0], config.MIN_SAMPLES,
            )
            continue
        for tag, aug in _augment_one(y, cls, stem).items():
            audio_io.save_wav(paths.augmented / cls / f"{stem}{AUG_SEP}{tag}.wav", aug)
            counts[cls] += 1

    for cls in config.CLASSES:
        log.info("augment %-11s +%d", cls, counts[cls])
    return counts
