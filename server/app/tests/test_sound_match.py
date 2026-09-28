"""app.sound_match ↔ 프로즌 dtw_doorbell 동등성 (stdlib unittest).

실행(server/ 에서):  python3 -m unittest app.tests.test_sound_match

기대값 = fixtures/sound_match_fixture.{npz,json} — librosa 환경에서 프로즌 features ·
distance 를 import 해 만든 값(생성기 fixtures/make_sound_match_fixture.py). 여기서는
서버 입력 경로 그대로 PCM 바이트 → decode_pcm16 → waveform_to_template →
dtw_cosine_distance 를 돌려 비교한다.

허용 오차 근거(2026-09-26 관측, venv · venv_real 동일):
  멜  상대 오차(템플릿 최대값 대비) 최대 2.2e-7 = float32 반올림 수준 → 1e-5 로 고정.
  거리 end-to-end 최대 7.8e-9 (픽스처 거리 0.067~0.457) → 1e-6. 기준값 판단에 쓰일
       자릿수(소수 2~3째 자리)보다 네 자릿수 이상 작다.
  거리 (프로즌 멜을 그대로 넣은 DTW 단독) 관측 0.0 → 1e-12.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

import numpy as np

from app import sound_match as sm
from inference.audio_decode import decode_pcm16

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
FROZEN_DIR = Path(__file__).resolve().parents[3] / "ml" / "experiments" / "dtw_doorbell"
MEL_RTOL = 1e-5
DIST_ATOL = 1e-6
DTW_ONLY_ATOL = 1e-12


def setUpModule():
    global META, ARRAYS, TEMPLATES
    META = json.loads((FIXTURE_DIR / "sound_match_fixture.json").read_text(encoding="utf-8"))
    with np.load(FIXTURE_DIR / "sound_match_fixture.npz") as z:
        ARRAYS = {k: z[k] for k in z.files}
    TEMPLATES = {
        name: sm.waveform_to_template(decode_pcm16(ARRAYS[f"pcm_{name}"].tobytes())[0])
        for name in META["frames"]
    }


class FixtureProvenanceTest(unittest.TestCase):
    def test_frozen_sources_match_fixture(self):
        for fname, expected in META["frozen_sha256"].items():
            actual = hashlib.sha256((FROZEN_DIR / fname).read_bytes()).hexdigest()
            self.assertEqual(
                actual, expected,
                f"프로즌 {fname} 이 픽스처 생성 시점과 다름 — 픽스처 재생성 필요 "
                f"({META['command']})",
            )


class EquivalenceTest(unittest.TestCase):
    def test_mel_matches_frozen(self):
        for name, frames in META["frames"].items():
            ref = ARRAYS[f"mel_{name}"]
            got = TEMPLATES[name]
            with self.subTest(name=name):
                self.assertEqual(got.dtype, np.float32)
                self.assertEqual(got.shape, (frames, sm.N_MELS))
                rel = np.abs(got - ref).max() / np.abs(ref).max()
                self.assertLessEqual(rel, MEL_RTOL)

    def test_distance_matches_frozen_end_to_end(self):
        for d in META["distances"]:
            with self.subTest(a=d["a"], b=d["b"]):
                got = sm.dtw_cosine_distance(TEMPLATES[d["a"]], TEMPLATES[d["b"]])
                self.assertAlmostEqual(got, d["distance"], delta=DIST_ATOL)

    def test_distance_on_frozen_mel(self):
        for d in META["distances"]:
            with self.subTest(a=d["a"], b=d["b"]):
                got = sm.dtw_cosine_distance(ARRAYS[f"mel_{d['a']}"], ARRAYS[f"mel_{d['b']}"])
                self.assertAlmostEqual(got, d["distance"], delta=DTW_ONLY_ATOL)


class InvariantTest(unittest.TestCase):
    def test_long_template_is_center_cropped(self):
        long_t = TEMPLATES["long_mix"]
        self.assertGreater(long_t.shape[0], sm.MAX_TEMPLATE_FRAMES)
        start = (long_t.shape[0] - sm.MAX_TEMPLATE_FRAMES) // 2
        cropped = long_t[start : start + sm.MAX_TEMPLATE_FRAMES]
        other = TEMPLATES["bell_a"]
        self.assertEqual(
            sm.dtw_cosine_distance(long_t, other), sm.dtw_cosine_distance(cropped, other)
        )

    def test_symmetric_and_self_zero(self):
        # 자기 거리 0 은 디지털 무음(전부 0) 프레임이 없을 때만 성립한다: 그런 행은 L2 정규화
        # 후 영벡터라 자기 자신과도 cost 1 (프로즌도 같음 — 자기쌍 기대값이 픽스처에 있다).
        names = list(TEMPLATES)
        for a in names:
            if np.all(TEMPLATES[a].sum(axis=1) > 0):
                self.assertAlmostEqual(sm.dtw_cosine_distance(TEMPLATES[a], TEMPLATES[a]), 0.0, delta=1e-6)
            for b in names:
                self.assertAlmostEqual(
                    sm.dtw_cosine_distance(TEMPLATES[a], TEMPLATES[b]),
                    sm.dtw_cosine_distance(TEMPLATES[b], TEMPLATES[a]),
                    delta=1e-12,
                )

    def test_invalid_inputs_raise(self):
        wave = np.zeros(1600, dtype=np.float32)
        with self.assertRaises(ValueError):
            sm.waveform_to_template(wave.reshape(1, -1))
        with self.assertRaises(ValueError):
            sm.waveform_to_template(np.zeros(0, dtype=np.float32))
        with self.assertRaises(ValueError):
            sm.waveform_to_template(wave, sample_rate=8000)
        good = TEMPLATES["bell_a"]
        for bad in (good[:, :32], good[0], np.zeros((0, sm.N_MELS), dtype=np.float32)):
            with self.assertRaises(ValueError):
                sm.dtw_cosine_distance(good, bad)


if __name__ == "__main__":
    unittest.main()
