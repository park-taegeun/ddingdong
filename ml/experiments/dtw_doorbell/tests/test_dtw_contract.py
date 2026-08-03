"""DTW 초인종 스파이크 계약 테스트 (stdlib unittest).

실행(repo 루트에서):  python3 -m unittest ml.experiments.dtw_doorbell.tests.test_dtw_contract

거리/통계 테스트는 numpy만 필요 → 항상 실행. 특징추출/스모크는 librosa 필요 →
부재 시 skip(§9 대체 규율, 정지 아님).
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

from ..constants import MAX_TEMPLATE_FRAMES, N_MELS
from ..distance import _clip_frames, dtw_cosine
from ..experiment import (
    group_by_source,
    group_key,
    resolve_doorbell_dir,
    separation_margin,
    source_id,
    threshold_sweep,
    unit_id,
)

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


class TestUnitGrouping(unittest.TestCase):
    """직접녹음 `direct_{클래스}_{유닛}_{테이크}.wav` 유닛 그룹핑 (decisions.md 5.1)."""

    def test_unit_id_strips_only_take(self) -> None:
        # 끝 테이크만 제거 → 유닛 키
        self.assertEqual(unit_id("direct_doorbell_A_01.wav"), "direct_doorbell_A")
        self.assertEqual(unit_id("direct_doorbell_A_02.wav"), "direct_doorbell_A")
        self.assertEqual(unit_id("direct_doorbell_B_01.wav"), "direct_doorbell_B")
        # 클래스명 underscore(fire_alarm) 포함해도 견고 — 끝 테이크만 strip
        self.assertEqual(unit_id("direct_fire_alarm_C_10.wav"), "direct_fire_alarm_C")

    def test_unit_id_take_absent_strips_ext(self) -> None:
        # 테이크 없는 파일 → 확장자만 제거(자체 그룹)
        self.assertEqual(unit_id("direct_doorbell_A.wav"), "direct_doorbell_A")

    def test_group_key_dispatch(self) -> None:
        # direct_ prefix → 유닛 경로, 그 외 → 원본ID 경로(기존과 동일)
        self.assertEqual(group_key("direct_doorbell_A_01.wav"), "direct_doorbell_A")
        self.assertEqual(group_key("125967_0009000.wav"), source_id("125967_0009000.wav"))
        self.assertEqual(
            group_key("-9ek6eO0RtI_260.0_270.0_0003000.wav"),
            source_id("-9ek6eO0RtI_260.0_270.0_0003000.wav"),
        )

    def test_unit_case_sensitive(self) -> None:
        # 대소문자 유닛은 별개 그룹(A ≠ a)
        self.assertNotEqual(unit_id("direct_doorbell_A_01.wav"), unit_id("direct_doorbell_a_01.wav"))

    def test_synthetic_dir_groups_by_unit(self) -> None:
        # 합성 파일명 A_01/A_02/B_01/C_01 → A=2·B=1·C=1 = 3그룹, A쌍(intra 후보) 존재
        names = [
            "direct_doorbell_A_01.wav",
            "direct_doorbell_A_02.wav",
            "direct_doorbell_B_01.wav",
            "direct_doorbell_C_01.wav",
        ]
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            for n in names:
                (d / n).touch()
            groups = group_by_source(d)
        self.assertEqual(len(groups), 3)
        self.assertEqual({k: len(v) for k, v in groups.items()}, {
            "direct_doorbell_A": 2,
            "direct_doorbell_B": 1,
            "direct_doorbell_C": 1,
        })
        # 유닛 1개(A)만 다-테이크 → intra 후보 존재(재-누름 측정 가능)
        multi = [k for k, v in groups.items() if len(v) >= 2]
        self.assertEqual(multi, ["direct_doorbell_A"])

    def test_empty_dir_no_groups(self) -> None:
        # 빈 04 디렉토리 → 그룹 0(예외 없이)
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(group_by_source(Path(td)), {})


@unittest.skipUnless(
    os.environ.get("DDINGDONG_DATA_ROOT")
    and (Path(os.environ["DDINGDONG_DATA_ROOT"]) / "01_clips" / "doorbell").is_dir(),
    "DDINGDONG_DATA_ROOT 실데이터 부재 — 01_clips 그룹핑 회귀 skip(학부생 로컬 전용)",
)
class TestClipsGroupingRegression(unittest.TestCase):
    """공개데이터(01_clips) 그룹핑 불변 회귀 — prefix 분기 추가가 기존 경로를 바꾸지 않음(decisions.md 33.5)."""

    def test_source_grouping_unchanged(self) -> None:
        root = Path(os.environ["DDINGDONG_DATA_ROOT"])
        doorbell = resolve_doorbell_dir(root / "01_clips")
        groups = group_by_source(doorbell)
        n_files = sum(len(v) for v in groups.values())
        # 436→182(33.5) 불변 + 모든 키가 원본ID 경로와 동일(direct_ 미포함)
        self.assertEqual(n_files, 436)
        self.assertEqual(len(groups), 182)
        for k, members in groups.items():
            for p in members:
                self.assertEqual(group_key(p.name), source_id(p.name))
                self.assertEqual(k, source_id(p.name))


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
