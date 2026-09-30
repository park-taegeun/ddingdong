"""/detect 추론 입력 레벨(serving_level) 회귀 (stdlib unittest).

실행(server/ 에서):  python3 -m unittest app.tests.test_serving_level

학습 식 대조: ml 패키지를 import 하지 않고(서버 규칙) ml/pipeline 원문을 ast 로 읽는다 —
audio_io.peak_normalize 함수 본문을 그대로 컴파일해 서버 함수와 같은 입력에 돌리고,
config.TARGET_PEAK · PEAK_NORMALIZE 리터럴을 서버 상수와 비교한다. 원문이 바뀌면 FAIL.

외부 연결 가드: test_registration 과 같은 방식(가드 함수 import + 자기 setUpModule).
"""

from __future__ import annotations

import ast
import io
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from .. import serving_level
# routes(→ utils · model_serving · kakao)를 패치 전에 먼저 import 한다. 이 모듈들은
# PREDICTED_CLASSES 를 이름으로 가져오므로, 첫 import 가 아래 constants 패치 안에서 일어나면
# 4클래스 튜플이 영구히 바인딩된다(33.6(f) 이름공간 교훈 — 실제로 IndexError 로 재현됨).
from .. import routes as _routes  # noqa: F401
from .test_detect_regression import (
    _DASHBOARD_TOKEN,
    _DEVICE_TOKEN,
    _NoNetworkTestCase,
    _install_network_guard,
    _uninstall_network_guard,
)

_ML_PIPELINE = Path(__file__).resolve().parents[3] / "ml" / "pipeline"
_CLASSES_3 = ("doorbell", "knock", "fire_alarm")
_CLASSES_4 = ("doorbell", "knock", "fire_alarm", "other")


def setUpModule() -> None:
    _install_network_guard()
    stray = [
        name
        for name, obj in globals().items()
        if isinstance(obj, type)
        and issubclass(obj, unittest.TestCase)
        and not issubclass(obj, _NoNetworkTestCase)
    ]
    if stray:
        _uninstall_network_guard()
        raise AssertionError(f"_NoNetworkTestCase 를 상속하지 않은 TestCase: {stray}")


def tearDownModule() -> None:
    _uninstall_network_guard()


def _ml_config_literals() -> dict:
    tree = ast.parse((_ML_PIPELINE / "config.py").read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            try:
                out[node.target.id] = ast.literal_eval(node.value)
            except ValueError:
                pass
    return out


def _ml_peak_normalize():
    """ml/pipeline/audio_io.py 의 peak_normalize 원문을 떼어 컴파일한 함수(학습 식 그 자체)."""
    src = (_ML_PIPELINE / "audio_io.py").read_text(encoding="utf-8")
    fn = next(
        n for n in ast.parse(src).body
        if isinstance(n, ast.FunctionDef) and n.name == "peak_normalize"
    )
    ns = {"np": np, "config": SimpleNamespace(TARGET_PEAK=_ml_config_literals()["TARGET_PEAK"])}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "audio_io.py", "exec"), ns)
    return ns["peak_normalize"]


class FormulaTest(_NoNetworkTestCase):
    """T1 식 동등성 · T2 계약 대조."""

    def test_t1_same_as_training_formula(self) -> None:
        ml_fn = _ml_peak_normalize()
        rng = np.random.default_rng(0)
        clamp = (rng.standard_normal(16000) * 0.01).astype(np.float32)
        clamp[[10, 500]] = [32767 / 32768, -1.0]  # int16 양 끝값 클램프
        cases = {
            "random": (rng.standard_normal(16000) * 0.05).astype(np.float32),
            "silent": np.zeros(16000, dtype=np.float32),
            "tiny_peak": np.full(16000, 1e-10, dtype=np.float32),
            "clamp": clamp,
        }
        for name, x in cases.items():
            with self.subTest(name):
                wf = x.reshape(1, -1)
                before = wf.copy()
                got = serving_level.peak_normalize(wf)
                np.testing.assert_array_equal(wf, before)  # 입력 무변경
                np.testing.assert_array_equal(got, ml_fn(wf.copy()))
                self.assertEqual(got.dtype, np.float32)
                self.assertEqual(got.shape, wf.shape)
                self.assertTrue(np.all(np.isfinite(got)))

    def test_t2_contract_text_matches_ml(self) -> None:
        lit = _ml_config_literals()
        self.assertEqual(serving_level.TARGET_PEAK, lit["TARGET_PEAK"])
        # 학습이 정규화를 끄면 서버 peak 모드의 근거가 사라진다 → 재판정.
        self.assertIs(lit["PEAK_NORMALIZE"], True)


class ResolveModeTest(_NoNetworkTestCase):
    """T3 모드 결정 표 — {3, 4클래스} × {미설정, raw, peak, 모르는 값, 빈 문자열, 공백}."""

    def test_t3_table(self) -> None:
        err = ValueError
        table = {
            (_CLASSES_3, None): "raw",
            (_CLASSES_3, "raw"): "raw",
            (_CLASSES_3, "peak"): err,  # 안전장치 ① — 화재 우회(33.18(b))
            (_CLASSES_3, "loud"): err,
            (_CLASSES_3, ""): err,
            (_CLASSES_3, "  "): err,
            (_CLASSES_4, None): "peak",
            (_CLASSES_4, "raw"): "raw",
            (_CLASSES_4, "peak"): "peak",
            (_CLASSES_4, "loud"): err,
            (_CLASSES_4, ""): err,
            (_CLASSES_4, "  "): err,
        }
        for (classes, env), want in table.items():
            with self.subTest(classes=len(classes), env=env):
                if want is err:
                    with self.assertRaises(ValueError):
                        serving_level.resolve_mode(classes, env)
                else:
                    self.assertEqual(serving_level.resolve_mode(classes, env), want)


class DetectWiringTest(_NoNetworkTestCase):
    """T4 호출부(predict 에만 정규화본) · T5 기동 실패."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls._db_file.close()
        # 작은 진폭(피크 1000) — 정규화하면 값이 확실히 달라진다.
        t = np.arange(32000)
        cls.pcm = (1000 * np.sin(2 * np.pi * 440 * t / 16000)).astype("<i2").tobytes()

    @classmethod
    def tearDownClass(cls) -> None:
        os.unlink(cls._db_file.name)

    def _make_app(self, classes, level=None):
        from .. import create_app
        from ..config import Config

        db_uri = f"sqlite:///{self._db_file.name}"

        class _TestConfig(Config):
            DEVICE_TOKEN = _DEVICE_TOKEN
            DASHBOARD_TOKEN = _DASHBOARD_TOKEN
            SQLALCHEMY_DATABASE_URI = db_uri
            MODEL_PATH = ""
            SERVING_LEVEL = level
            KAKAO_REST_API_KEY = ""
            KAKAO_CLIENT_SECRET = ""
            KAKAO_ACCESS_TOKEN = ""
            KAKAO_REFRESH_TOKEN = ""
            NCP_CLIENT_ID = ""
            NCP_CLIENT_SECRET = ""

        # 모드는 create_app 이 constants.PREDICTED_CLASSES 를 읽어 정한다 → 그 속성을 주입.
        with mock.patch("app.constants.PREDICTED_CLASSES", classes):
            return create_app(_TestConfig)

    def _detect_capture(self, app):
        """real 모드 대역으로 /detect 1회 → (predict 입력, observe 의 waveform 인자)."""
        from inference.audio_decode import decode_pcm16

        from .. import model_serving

        seen = {}

        def _predict(x):
            seen["predict"] = x.copy()
            # 점수 개수 = scores_to_prediction 이 읽는 model_serving.PREDICTED_CLASSES(import 시점
            # 바인딩) — _make_app 이 패치하는 constants 값이 아니다. 하드코딩 3개면 4클래스(#83)에서 IndexError.
            n = len(model_serving.PREDICTED_CLASSES)
            return np.full((1, n), 0.1, dtype=np.float32)  # 저신뢰 → 발송 없음

        with app.app_context(), mock.patch(
            "app.routes.model_serving.is_real_mode", return_value=True
        ), mock.patch("app.routes.model_serving.predict", side_effect=_predict), mock.patch(
            "app.routes.registration_observe.observe"
        ) as observe:
            r = app.test_client().post(
                "/api/v1/detect",
                headers={"Authorization": f"Bearer {_DEVICE_TOKEN}"},
                data={
                    "client_request_id": f"lvl-{self._testMethodName}",
                    "device_id": f"dev-{self._testMethodName}",
                    "audio": (io.BytesIO(self.pcm), "a.pcm"),
                },
                content_type="multipart/form-data",
            )
        self.assertEqual(r.status_code, 201, r.get_data(as_text=True))
        observe.assert_called_once()
        pcm_arg, wf_arg = observe.call_args.args[:2]
        self.assertEqual(pcm_arg, self.pcm)
        return seen["predict"], wf_arg, decode_pcm16(self.pcm)

    def test_t4_four_class_peak_goes_to_predict_only(self) -> None:
        app = self._make_app(_CLASSES_4)
        self.assertEqual(app.config["SERVING_LEVEL_MODE"], "peak")
        model_in, wf_arg, decoded = self._detect_capture(app)
        np.testing.assert_array_equal(model_in, serving_level.peak_normalize(decoded))
        self.assertFalse(np.array_equal(model_in, decoded))
        self.assertEqual(wf_arg.tobytes(), decoded.tobytes())  # observe = decode 원본(바이트 동일)

    def test_t4_three_class_raw(self) -> None:
        app = self._make_app(_CLASSES_3)
        self.assertEqual(app.config["SERVING_LEVEL_MODE"], "raw")
        model_in, wf_arg, decoded = self._detect_capture(app)
        self.assertEqual(model_in.tobytes(), decoded.tobytes())
        self.assertEqual(wf_arg.tobytes(), decoded.tobytes())

    def test_t5_three_class_with_peak_fails_startup(self) -> None:
        with self.assertRaisesRegex(ValueError, "DDINGDONG_SERVING_LEVEL=peak"):
            self._make_app(_CLASSES_3, level="peak")


if __name__ == "__main__":
    unittest.main()
