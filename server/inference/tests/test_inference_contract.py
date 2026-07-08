"""추론 계약 테스트 (stdlib unittest — 서버 추가 의존성 없이 실행).

실행(server/ 에서):  python3 -m unittest inference.tests.test_inference_contract

디코딩 테스트는 numpy 만 필요 → 항상 실행. predict/모델 테스트는 TF 필요 →
TF 부재 시 skip(정지 아님, §9 대체 규율).
"""

from __future__ import annotations

import struct
import tempfile
import unittest

import numpy as np

from ..audio_decode import decode_pcm16
from ..constants import NUM_CLASSES, SAMPLE_RATE

try:
    import tensorflow as _tf  # noqa: F401

    _HAS_TF = True
except Exception:  # noqa: BLE001
    _HAS_TF = False


def _pcm16_bytes(samples: list[int]) -> bytes:
    """int16 리스트 → little-endian PCM 바이트."""
    return struct.pack("<" + "h" * len(samples), *samples)


class TestAudioDecode(unittest.TestCase):
    def test_shape_and_dtype(self) -> None:
        data = _pcm16_bytes([0, 16384, -16384, 32767, -32768])
        wf = decode_pcm16(data, SAMPLE_RATE)
        self.assertEqual(wf.shape, (1, 5))
        self.assertEqual(wf.dtype, np.float32)

    def test_normalization_range(self) -> None:
        # 풀스케일 int16 → [-1, 1) 근처. 32767/32768≈0.99997, -32768/32768=-1.0
        wf = decode_pcm16(_pcm16_bytes([32767, -32768, 0]), SAMPLE_RATE)
        self.assertLessEqual(float(wf.max()), 1.0)
        self.assertGreaterEqual(float(wf.min()), -1.0)
        self.assertAlmostEqual(float(wf[0, 1]), -1.0, places=6)
        self.assertAlmostEqual(float(wf[0, 2]), 0.0, places=6)

    def test_empty_raises(self) -> None:
        with self.assertRaises(ValueError):
            decode_pcm16(b"", SAMPLE_RATE)

    def test_misaligned_bytes_raises(self) -> None:
        # 홀수 바이트 = int16 미정렬
        with self.assertRaises(ValueError):
            decode_pcm16(b"\x01\x02\x03", SAMPLE_RATE)

    def test_sample_rate_mismatch_raises(self) -> None:
        with self.assertRaises(ValueError):
            decode_pcm16(_pcm16_bytes([0, 1]), 44100)


@unittest.skipUnless(_HAS_TF, "TensorFlow 미설치 — predict 계약 테스트 skip(§9 대체)")
class TestModelRunnerContract(unittest.TestCase):
    _model_dir: str

    @classmethod
    def setUpClass(cls) -> None:
        from ..make_dummy_savedmodel import build_dummy_savedmodel

        cls._tmp = tempfile.TemporaryDirectory(prefix="dummy_sm_test_")
        cls._model_dir = build_dummy_savedmodel(cls._tmp.name, seed=42)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_predict_shape_and_softmax(self) -> None:
        from ..model_runner import ModelRunner

        runner = ModelRunner(self._model_dir)
        wf = decode_pcm16(_pcm16_bytes([1000, -1000, 500, -500] * 100), SAMPLE_RATE)
        scores = runner.predict(wf)
        self.assertEqual(scores.shape, (1, NUM_CLASSES))
        self.assertAlmostEqual(float(scores.sum()), 1.0, places=4)  # softmax sum≈1
        self.assertTrue(bool((scores >= 0).all()))

    def test_variable_length_input(self) -> None:
        from ..model_runner import ModelRunner

        runner = ModelRunner(self._model_dir)
        for n in (1, 16000, 32000):  # 1샘플 ~ 2초, 어떤 길이도 (1,3)
            wf = decode_pcm16(_pcm16_bytes([123] * n), SAMPLE_RATE)
            self.assertEqual(runner.predict(wf).shape, (1, NUM_CLASSES))

    def test_bad_model_path_raises(self) -> None:
        from ..model_runner import ModelRunner

        with self.assertRaises(RuntimeError):  # 로드 실패 graceful(크래시 아님)
            ModelRunner("/nonexistent/savedmodel/path")


if __name__ == "__main__":
    unittest.main()
