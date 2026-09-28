"""app.sound_match 동등성 픽스처 생성기 — librosa 가 있는 ML 환경에서만 실행.

기대값은 프로즌 ml/experiments/dtw_doorbell 의 features · distance 를 import 해서 만든다
(재구현 코드로 기대값을 만들면 순환 검증). 입력은 결정적 합성 int16 PCM 을 wav 로
써서 experiment.py 와 같은 경로(wav_to_template → dtw_cosine(backend="exact"))로 계산.

실행(repo 루트에서, ML 환경 python):
    python -B server/app/tests/fixtures/make_sound_match_fixture.py
(-m 실행은 server.app 패키지 초기화가 flask 를 import 해서 ML 환경에서 막히므로 경로 실행.)

산출: 같은 폴더의 sound_match_fixture.npz (PCM · 기대 멜) + sound_match_fixture.json
(기대 거리 · 버전 · 프로즌 파일 sha256 · 생성 명령). 프로즌 파일이 바뀌면 재생성.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
FROZEN_DIR = REPO_ROOT / "ml" / "experiments" / "dtw_doorbell"
FROZEN_FILES = ("features.py", "distance.py", "constants.py")
SR = 16000
WINDOW_SAMPLES = 32768  # 2.048초 = 제품 /detect 창
LONG_SAMPLES = 67200  # 4.2초 → 421 프레임 > 400 (크롭 경로)


def _tone(freqs, n, decay):
    t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * t) for f in freqs) * np.exp(-decay * t) / len(freqs)


def _sweep(f0, f1, n):
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * (f0 * t + (f1 - f0) * t * t / (2 * t[-1])))


def _to_int16(x):
    return np.clip(np.round(x * 32767), -32768, 32767).astype("<i2")


def make_signals() -> dict[str, np.ndarray]:
    rs = np.random.RandomState(20260926)  # 버전 간 고정 스트림
    n = WINDOW_SAMPLES
    silence = np.zeros(4000)

    # bell_a: 무음 0.25초 → 딩(880+1320Hz 감쇠) → 동(660+990Hz) + 약한 잡음
    ding = _tone((880, 1320), 12000, 3.0)
    dong = _tone((660, 990), n - 16000, 2.0)
    bell_a = 0.6 * np.concatenate([silence, ding, dong]) + 0.003 * rs.randn(n)
    # bell_b: bell_a 와 비슷한 모양, 음높이 · 시작점 · 음량이 다름
    ding_b = _tone((900, 1350), 12800, 3.0)
    dong_b = _tone((675, 1012), n - 2000 - 12800, 2.0)
    bell_b = 0.3 * np.concatenate([np.zeros(2000), ding_b, dong_b]) + 0.003 * rs.randn(n)
    # sweep_noise: 선형 스윕 200→6000Hz 1초 + 완전 무음(0) 구간 + 백색잡음
    noise_n = n - SR - 6000
    sweep_noise = np.concatenate([0.5 * _sweep(200, 6000, SR), np.zeros(6000), 0.2 * rs.randn(noise_n)])
    # long_mix: 4.2초 — 스윕 · 무음 · 벨 · 잡음 (크롭 경로)
    m = LONG_SAMPLES
    long_mix = np.concatenate([
        0.4 * _sweep(3000, 300, 24000),
        np.zeros(8000),
        0.5 * _tone((1000, 1500), 24000, 1.5),
        0.1 * rs.randn(m - 56000),
    ])
    return {
        "bell_a": _to_int16(bell_a),
        "bell_b": _to_int16(bell_b),
        "sweep_noise": _to_int16(sweep_noise),
        "long_mix": _to_int16(long_mix),
    }


def main() -> None:
    sys.path.insert(0, str(REPO_ROOT))
    import librosa
    import soundfile as sf

    from ml.experiments.dtw_doorbell.distance import dtw_cosine, has_fastdtw
    from ml.experiments.dtw_doorbell.features import wav_to_template

    signals = make_signals()
    arrays: dict[str, np.ndarray] = {}
    templates: dict[str, np.ndarray] = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, pcm in signals.items():
            path = Path(tmp) / f"{name}.wav"
            sf.write(str(path), pcm, SR, subtype="PCM_16")
            templates[name] = wav_to_template(path)
            arrays[f"pcm_{name}"] = pcm
            arrays[f"mel_{name}"] = templates[name]

    distances = [
        {"a": a, "b": b, "distance": dtw_cosine(templates[a], templates[b], backend="exact")}
        for a, b in itertools.combinations_with_replacement(signals, 2)
    ]
    meta = {
        "generator": "server/app/tests/fixtures/make_sound_match_fixture.py",
        "command": "python -B server/app/tests/fixtures/make_sound_match_fixture.py (repo 루트, librosa 환경)",
        "path": "soundfile PCM_16 wav → features.wav_to_template → distance.dtw_cosine(backend='exact')",
        "versions": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "librosa": librosa.__version__,
            "soundfile": sf.__version__,
            "fastdtw_installed": has_fastdtw(),
        },
        "frozen_sha256": {
            f: hashlib.sha256((FROZEN_DIR / f).read_bytes()).hexdigest() for f in FROZEN_FILES
        },
        "frames": {name: int(t.shape[0]) for name, t in templates.items()},
        "distances": distances,
    }
    np.savez_compressed(HERE / "sound_match_fixture.npz", **arrays)
    (HERE / "sound_match_fixture.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
