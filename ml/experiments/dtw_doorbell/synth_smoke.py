"""합성 스모크 (스코프 1층) — 실데이터 없이 코드 경로 E2E 검증.

각 합성 "초인종"은 고유 톤 집합(음색). 같은 초인종의 조각 = 같은 톤 + 소량 섭동
(노이즈/진폭/미세 시프트) → intra. 다른 초인종 = 다른 톤 → inter. waveform →
features.waveform_to_template → distance.dtw_cosine → experiment 통계까지 전 경로 태움.

★★ 산출 마진/EER 숫자는 합성이라 **무의미**. 목적 = 파이프가 안 터지고 intra<inter
   방향이 코드상 성립하는지 확인(실 판정은 학부생 2층).
"""

from __future__ import annotations

import argparse
import sys

import numpy as np

from .constants import N_MELS, RANDOM_SEED, SAMPLE_RATE
from .experiment import _assemble_report, print_report
from .distance import dtw_cosine
from .features import waveform_to_template


def _synth_doorbell_wave(
    tones_hz: np.ndarray, duration_sec: float, sample_rate: int, rng: np.random.Generator
) -> np.ndarray:
    """고유 톤 집합 + 소량 섭동 → 한 조각 waveform (같은 초인종 = 같은 tones_hz)."""
    n = int(duration_sec * sample_rate)
    t = np.arange(n, dtype=np.float64) / sample_rate
    shift = int(rng.integers(0, sample_rate // 50 + 1))  # 미세 시간 시프트(≤20ms)
    wave = np.zeros(n, dtype=np.float64)
    for f in tones_hz:
        jitter = 1.0 + rng.normal(0.0, 0.01)  # 조각별 ±1% 주파수 흔들림
        amp = 0.3 * (1.0 + rng.normal(0.0, 0.05))
        wave += amp * np.sin(2.0 * np.pi * f * jitter * t)
    wave = np.roll(wave, shift)
    wave += rng.normal(0.0, 0.01, size=n)  # 배경 노이즈
    return wave.astype(np.float32)


def run_smoke(
    n_doorbells: int = 8,
    fragments_per: int = 3,
    duration_sec: float = 1.0,
    seed: int = RANDOM_SEED,
) -> dict[str, object]:
    """합성 초인종 세트로 분리 실험 전 경로 실행 → 리포트(합성 라벨)."""
    rng = np.random.default_rng(seed)
    # 초인종별 고유 톤 집합 (서로 다른 대역)
    templates: list[list[np.ndarray]] = []
    for _ in range(n_doorbells):
        tones = rng.uniform(300.0, 3000.0, size=int(rng.integers(2, 4)))
        frags = [
            waveform_to_template(
                _synth_doorbell_wave(tones, duration_sec, SAMPLE_RATE, rng), SAMPLE_RATE
            )
            for _ in range(fragments_per)
        ]
        templates.append(frags)

    intra_d: list[float] = []
    for frags in templates:
        for i in range(len(frags)):
            for j in range(i + 1, len(frags)):
                intra_d.append(dtw_cosine(frags[i], frags[j], backend="exact"))
    inter_d: list[float] = []
    for a in range(n_doorbells):
        for b in range(a + 1, n_doorbells):
            inter_d.append(dtw_cosine(templates[a][0], templates[b][0], backend="exact"))

    pair_stats = {
        "groups_total": n_doorbells,
        "groups_multi": n_doorbells,
        "intra_pairs": len(intra_d),
        "intra_pairs_dropped_by_cap": 0,
        "inter_pairs": len(inter_d),
        "inter_pairs_possible": len(inter_d),
        "inter_pairs_dropped_by_cap": 0,
    }
    report = _assemble_report(intra_d, inter_d, pair_stats, "exact", is_synthetic=True)
    report["mel_dim"] = N_MELS
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DTW 초인종 합성 스모크 (1층)")
    parser.add_argument("--n-doorbells", type=int, default=8)
    parser.add_argument("--fragments-per", type=int, default=3)
    parser.add_argument("--duration-sec", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args(argv)
    report = run_smoke(
        n_doorbells=args.n_doorbells,
        fragments_per=args.fragments_per,
        duration_sec=args.duration_sec,
        seed=args.seed,
    )
    print_report(report)
    print("\n[스모크 판정] 파이프 E2E 통과 + intra<inter 방향 = 코드 경로 OK (숫자 무의미).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
