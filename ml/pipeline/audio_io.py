"""오디오 입출력·검증 헬퍼 (soundfile + librosa)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from . import config

AUDIO_EXTS: tuple[str, ...] = (".wav", ".flac", ".mp3", ".m4a", ".ogg")


@dataclass(frozen=True)
class AudioInfo:
    samplerate: int
    channels: int
    frames: int

    @property
    def duration_sec(self) -> float:
        return self.frames / self.samplerate if self.samplerate else 0.0


def probe(path: Path) -> AudioInfo:
    """디코딩 없이 메타만 읽음(포맷/SR/채널/길이 검증용)."""
    info = sf.info(str(path))
    return AudioInfo(samplerate=info.samplerate, channels=info.channels, frames=info.frames)


def load_mono(path: Path, target_sr: int = config.SAMPLE_RATE) -> np.ndarray:
    """float32 mono [-1,1] 로 로드. SR 다르면 리샘플, 스테레오면 평균 다운믹스.

    (실측상 입력은 이미 16k mono라 리샘플/다운믹스는 무동작이지만, 방어적으로 유지.)
    """
    data, sr = sf.read(str(path), dtype="float32", always_2d=False)
    if data.ndim == 2:  # (frames, channels) → mono
        data = data.mean(axis=1)
    if sr != target_sr:
        import librosa  # 지연 import (전처리 assert 통과분은 리샘플 불필요)

        data = librosa.resample(data, orig_sr=sr, target_sr=target_sr)
    return np.ascontiguousarray(data, dtype=np.float32)


def save_wav(path: Path, y: np.ndarray, sr: int = config.SAMPLE_RATE) -> None:
    """PCM_16 wav 로 저장. 클리핑 방지 위해 [-1,1] 로 clip."""
    path.parent.mkdir(parents=True, exist_ok=True)
    y = np.clip(y, -1.0, 1.0).astype(np.float32)
    sf.write(str(path), y, sr, subtype=config.OUTPUT_SUBTYPE)


def peak_normalize(y: np.ndarray, target_peak: float = config.TARGET_PEAK) -> np.ndarray:
    """최대 진폭을 target_peak 로 스케일. 무음(피크 0)이면 원본 반환."""
    peak = float(np.max(np.abs(y))) if y.size else 0.0
    if peak <= 1e-9:
        return y
    return y * (target_peak / peak)


def fix_duration(y: np.ndarray, seconds: float, sr: int = config.SAMPLE_RATE) -> np.ndarray:
    """고정 길이 정책: 짧으면 뒤를 zero-pad, 길면 앞에서 trim."""
    target = int(round(seconds * sr))
    if y.shape[0] == target:
        return y
    if y.shape[0] < target:
        return np.pad(y, (0, target - y.shape[0]))
    return y[:target]


def iter_audio_files(directory: Path):
    """디렉토리 바로 아래 오디오 파일을 정렬된 순서로 순회(재현성)."""
    if not directory.is_dir():
        return
    for p in sorted(directory.iterdir()):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
            yield p
