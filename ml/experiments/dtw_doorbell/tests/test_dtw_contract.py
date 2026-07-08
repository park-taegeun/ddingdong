"""DTW 초인종 스파이크 계약 테스트 (stdlib unittest).

실행(repo 루트에서):  python3 -m unittest ml.experiments.dtw_doorbell.tests.test_dtw_contract

거리/통계 테스트는 numpy만 필요 → 항상 실행. 특징추출/스모크는 librosa 필요 →
부재 시 skip(§9 대체 규율, 정지 아님).
"""

from __future__ import annotations

import unittest

import numpy as np

from ..constants import MAX_TEMPLATE_FRAMES, N_MELS
from ..distance import _clip_frames, dtw_cosine
from ..experiment import separation_margin, source_id, threshold_sweep

try:
    import librosa  # noqa: F401

    _HAS_LIBROSA = True
except Exception:  # noqa: BLE001
    _HAS_LIBROSA = False


class TestDistance(unittest.TestCase):
    def test_identical_is_near_zero(self) -> None:
        rng = np.random.default_rng(0)
        t = rng.random((30, N_MELS)).astype(np.float32)
        self.assertAlmostEqual(dtw_cosine(t, t, backend="exact"), 0.0, places=5)

    def test_different_is_positive(self) -> None:
        a = np.tile(np.eye(1, N_MELS, 0, dtype=np.float32), (20, 1))  # 밴드0 활성
        b = np.tile(np.eye(1, N_MELS, N_MELS - 1, dtype=np.float32), (20, 1))  # 밴드끝
        # 직교 one-hot → cosine 1.0, (Ta+Tb) 정규화 대각경로 = 정확히 0.5 (최대 비유사)
        self.assertGreaterEqual(dtw_cosine(a, b, backend="exact"), 0.49)

    def test_variable_length_returns_finite(self) -> None:
        rng = np.random.default_rng(1)
        a = rng.random((17, N_MELS)).astype(np.float32)
        b = rng.random((43, N_MELS)).astype(np.float32)
        d = dtw_cosine(a, b, backend="exact")
        self.assertTrue(np.isfinite(d))
        self.assertGreaterEqual(d, 0.0)

    def test_mel_dim_mismatch_raises(self) -> None:
        a = np.ones((10, N_MELS), dtype=np.float32)
        b = np.ones((10, N_MELS + 1), dtype=np.float32)
        with self.assertRaises(ValueError):
            dtw_cosine(a, b, backend="exact")

    def test_frame_clip_bounds_runtime(self) -> None:
        big = np.ones((MAX_TEMPLATE_FRAMES + 500, N_MELS), dtype=np.float32)
        self.assertEqual(_clip_frames(big).shape[0], MAX_TEMPLATE_FRAMES)


class TestStats(unittest.TestCase):
    def test_source_id_grouping(self) -> None:
        # AudioSet-style + FSD50K-style 둘 다 원본ID 추출
        self.assertEqual(source_id("-9ek6eO0RtI_260.0_270.0_0003000.wav"), "-9ek6eO0RtI_260.0_270.0")
        self.assertEqual(source_id("125967_0009000.wav"), "125967")

    def test_margin_positive_when_separated(self) -> None:
        intra = [0.10, 0.12, 0.11, 0.09]  # 같은 초인종 = 가까움
        inter = [0.80, 0.85, 0.78, 0.82]  # 다른 초인종 = 멂
        m = separation_margin(intra, inter)
        self.assertGreater(m["margin"], 2.0)
        self.assertLess(m["mean_intra"], m["mean_inter"])

    def test_threshold_sweep_perfect_separation(self) -> None:
        intra = [0.1, 0.15, 0.2]
        inter = [0.7, 0.8, 0.9]
        s = threshold_sweep(intra, inter)
        self.assertAlmostEqual(s["best_accuracy"], 1.0, places=6)
        self.assertLessEqual(s["eer"], 0.01)

    def test_threshold_sweep_empty_safe(self) -> None:
        s = threshold_sweep([], [])
        self.assertEqual(s["best_accuracy"], 0.0)


@unittest.skipUnless(_HAS_LIBROSA, "librosa 미설치 — 특징추출 테스트 skip(§9 대체)")
class TestFeatures(unittest.TestCase):
    def test_template_shape_and_dtype(self) -> None:
        from ..features import waveform_to_template

        wave = np.sin(2 * np.pi * 440 * np.arange(16000) / 16000).astype(np.float32)
        tpl = waveform_to_template(wave, 16000)
        self.assertEqual(tpl.ndim, 2)
        self.assertEqual(tpl.shape[1], N_MELS)
        self.assertEqual(tpl.dtype, np.float32)
        self.assertTrue(bool((tpl >= 0).all()))  # power-mel 비음수

    def test_empty_waveform_raises(self) -> None:
        from ..features import waveform_to_template

        with self.assertRaises(ValueError):
            waveform_to_template(np.zeros(0, dtype=np.float32), 16000)


@unittest.skipUnless(_HAS_LIBROSA, "librosa 미설치 — 스모크 skip(§9 대체)")
class TestSmoke(unittest.TestCase):
    def test_synthetic_direction(self) -> None:
        from ..synth_smoke import run_smoke

        report = run_smoke(n_doorbells=4, fragments_per=2, duration_sec=0.5, seed=7)
        self.assertTrue(report["is_synthetic"])
        sep = report["separation"]
        # 합성이지만 코드가 맞으면 방향(intra<inter) 성립해야 함
        self.assertLess(sep["mean_intra"], sep["mean_inter"])


if __name__ == "__main__":
    unittest.main()
