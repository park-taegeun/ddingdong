"""/detect 추론 입력 레벨(serving_level) 회귀 (stdlib unittest).

실행(server/ 에서):  python3 -m unittest app.tests.test_serving_level

학습 식 대조: ml 패키지를 import 하지 않고(서버 규칙) ml/pipeline 원문을 ast 로 읽는다 —
audio_io.peak_normalize · peak_normalize_clampmask 함수 본문을 그대로 컴파일해 서버 함수와 같은 입력에
돌리고, config 상수(TARGET_PEAK · PEAK_NORMALIZE · 규칙 이름 · CLAMP_*)를 서버 상수와 비교한다. 원문이 바뀌면 FAIL.
규칙 계보: run 폴더 train_config.json peak_rule → 기동 시 규칙 해석(T6) → predict 입력(T4 · T7).

외부 연결 가드: test_registration 과 같은 방식(가드 함수 import + 자기 setUpModule).
"""

from __future__ import annotations

import ast
import io
import json
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
_ML_TRAIN = Path(__file__).resolve().parents[3] / "ml" / "training" / "train.py"
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
    """config.py 최상위 대입 중 builtins 없이 평가되는 값(리터럴 · 산술 · 앞선 상수 참조)만."""
    tree = ast.parse((_ML_PIPELINE / "config.py").read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name, value = node.target.id, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name, value = node.targets[0].id, node.value
        else:
            continue
        try:
            out[name] = eval(compile(ast.Expression(value), "config.py", "eval"), {"__builtins__": {}}, dict(out))
        except Exception:
            pass
    return out


def _ml_fn(name):
    """ml/pipeline/audio_io.py 의 함수 원문을 떼어 컴파일한 함수(학습 식 그 자체)."""
    src = (_ML_PIPELINE / "audio_io.py").read_text(encoding="utf-8")
    fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == name)
    lit = _ml_config_literals()
    cfg = SimpleNamespace(**{k: lit[k] for k in ("TARGET_PEAK", "CLAMP_LEVEL", "CLAMP_GUARD_SAMPLES")})
    ns = {"np": np, "config": cfg}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "audio_io.py", "exec"), ns)
    return ns[name]


def _ml_peak_normalize():
    return _ml_fn("peak_normalize")


def _level_cases() -> dict:
    """규칙 대조 입력 — 무음 · 전체 클램프 · 고립 클램프 · 2샘플 런 + 두 번째 튐 · 진짜 잘림 · 짧은 창."""
    rng = np.random.default_rng(0)
    hi = np.float32(32767 / 32768)
    base = (rng.standard_normal(16000) * 0.01).astype(np.float32)
    clamp = base.copy()
    clamp[[10, 500]] = [hi, -1.0]  # int16 양 끝값 클램프
    run2 = base.copy()
    run2[[5000, 5001]] = hi
    run2[5001 + 17] = 0.5  # 글리치 뒤 두 번째 튐(±32 안)
    t = np.arange(16000) / 16000
    loud = np.clip(1.5 * np.minimum(t / 0.5, 1.0) * np.sin(2 * np.pi * 1000 * t), -1.0, hi).astype(np.float32)
    short = base[:20].copy()
    short[3] = hi
    return {
        "random": (rng.standard_normal(16000) * 0.05).astype(np.float32),
        "silent": np.zeros(16000, dtype=np.float32),
        "tiny_peak": np.full(16000, 1e-10, dtype=np.float32),
        "all_clamp": np.full(16000, hi, dtype=np.float32),
        "clamp": clamp,
        "run2_bump": run2,
        "loud_clipped": loud,
        "short": short,
    }


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

    def test_t1b_clampmask_same_as_training_formula(self) -> None:
        ml_fn = _ml_fn("peak_normalize_clampmask")
        for name, x in _level_cases().items():
            with self.subTest(name):
                wf = x.reshape(1, -1)
                before = wf.copy()
                got = serving_level.peak_normalize_clampmask(wf)
                np.testing.assert_array_equal(wf, before)  # 입력 무변경
                np.testing.assert_array_equal(got, ml_fn(wf.copy()))
                self.assertEqual(got.dtype, np.float32)
                self.assertEqual(got.shape, wf.shape)
                self.assertTrue(np.all(np.isfinite(got)))
        # 대조가 공허하지 않다: 클램프 케이스에서 두 규칙이 실제로 갈린다
        wf = _level_cases()["run2_bump"].reshape(1, -1)
        self.assertFalse(np.allclose(serving_level.peak_normalize_clampmask(wf), serving_level.peak_normalize(wf)))

    def test_t2_contract_text_matches_ml(self) -> None:
        lit = _ml_config_literals()
        self.assertEqual(serving_level.TARGET_PEAK, lit["TARGET_PEAK"])
        # 학습이 정규화를 끄면 서버 peak 모드의 근거가 사라진다 → 재판정.
        self.assertIs(lit["PEAK_NORMALIZE"], True)
        self.assertEqual(serving_level.RULE_PLAIN, lit["PEAK_RULE_PLAIN"])
        self.assertEqual(serving_level.RULE_CLAMPMASK32, lit["PEAK_RULE_CLAMPMASK32"])
        self.assertEqual(serving_level.CLAMP_LEVEL, lit["CLAMP_LEVEL"])
        self.assertEqual(serving_level.CLAMP_GUARD_SAMPLES, lit["CLAMP_GUARD_SAMPLES"])
        self.assertIn(lit["PEAK_RULE"], serving_level.RULES)  # 학습 기본 규칙을 서버가 안다
        # train_config.json 파일명 · 키가 학습 코드와 같다
        train_src = _ML_TRAIN.read_text(encoding="utf-8")
        self.assertIn(f'TRAIN_CONFIG_NAME = "{serving_level.TRAIN_CONFIG_NAME}"', train_src)
        self.assertIn(f'"{serving_level.RULE_KEY}": peak_rule', train_src)


def _run_dir(root: Path, cfg) -> str:
    """run 폴더(train_config.json = cfg, None 이면 파일 없음) → MODEL_PATH(= run/inference_savedmodel)."""
    root.mkdir(parents=True, exist_ok=True)
    if cfg is not None:
        (root / "train_config.json").write_text(json.dumps(cfg), encoding="utf-8")
    return str(root / "inference_savedmodel")


class ResolveRuleTest(_NoNetworkTestCase):
    """T6 규칙 해석 표 — run 폴더 train_config.json peak_rule."""

    def test_t6_table(self) -> None:
        plain, cm = serving_level.RULE_PLAIN, serving_level.RULE_CLAMPMASK32
        base = {"epochs": 60, "classes": list(_CLASSES_4)}
        table = {
            "plain": ({**base, "peak_rule": plain}, (plain, False)),
            "clampmask": ({**base, "peak_rule": cm}, (cm, False)),
            "key_missing": (base, (plain, True)),  # 2차 run 실물 모양
            "file_missing": (None, (plain, True)),  # 1차 run 실물 모양
            "unknown": ({**base, "peak_rule": "peak_foo_v9"}, ValueError),
            "empty": ({**base, "peak_rule": ""}, ValueError),
            "null": ({**base, "peak_rule": None}, ValueError),
        }
        with tempfile.TemporaryDirectory() as tmp:
            for name, (cfg, want) in table.items():
                with self.subTest(name):
                    mp = _run_dir(Path(tmp) / name, cfg)
                    if want is ValueError:
                        with self.assertRaises(ValueError):
                            serving_level.resolve_rule(mp)
                    else:
                        self.assertEqual(serving_level.resolve_rule(mp), want)
                        self.assertEqual(serving_level.resolve_rule(mp + "/"), want)  # 끝 슬래시


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

    def _make_app(self, classes, level=None, model_path=""):
        from .. import create_app
        from ..config import Config

        db_uri = f"sqlite:///{self._db_file.name}"

        class _TestConfig(Config):
            DEVICE_TOKEN = _DEVICE_TOKEN
            DASHBOARD_TOKEN = _DASHBOARD_TOKEN
            SQLALCHEMY_DATABASE_URI = db_uri
            MODEL_PATH = model_path
            SERVING_LEVEL = level
            KAKAO_REST_API_KEY = ""
            KAKAO_CLIENT_SECRET = ""
            KAKAO_ACCESS_TOKEN = ""
            KAKAO_REFRESH_TOKEN = ""
            NCP_CLIENT_ID = ""
            NCP_CLIENT_SECRET = ""

        # 모드는 create_app 이 constants.PREDICTED_CLASSES 를 읽어 정한다 → 그 속성을 주입.
        # 실모델 로드(init_app)는 대역 — 규칙 해석은 MODEL_PATH 경로 문자열만 쓴다.
        with mock.patch("app.constants.PREDICTED_CLASSES", classes), mock.patch("app.model_serving.init_app"):
            return create_app(_TestConfig)

    def _detect_capture(self, app, pcm=None):
        """real 모드 대역으로 /detect 1회 → (predict 입력, 등록 record 의 waveform 인자).

        등록 판정(before_send)도 같은 원본 waveform 객체를 받는지 함께 단언한다.
        """
        from inference.audio_decode import decode_pcm16

        from .. import model_serving, registration_observe

        pcm = self.pcm if pcm is None else pcm
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
            "app.routes.registration_observe.record"
        ) as observe, mock.patch(
            "app.routes.registration_observe.before_send",
            wraps=registration_observe.before_send,
        ) as before_send:
            r = app.test_client().post(
                "/api/v1/detect",
                headers={"Authorization": f"Bearer {_DEVICE_TOKEN}"},
                data={
                    "client_request_id": f"lvl-{self._testMethodName}",
                    "device_id": f"dev-{self._testMethodName}",
                    "audio": (io.BytesIO(pcm), "a.pcm"),
                },
                content_type="multipart/form-data",
            )
        self.assertEqual(r.status_code, 201, r.get_data(as_text=True))
        observe.assert_called_once()
        pcm_arg, wf_arg = observe.call_args.args[:2]
        self.assertEqual(pcm_arg, pcm)
        before_send.assert_called_once()
        self.assertIs(before_send.call_args.args[0], wf_arg)
        return seen["predict"], wf_arg, decode_pcm16(pcm)

    def test_t4_four_class_peak_goes_to_predict_only(self) -> None:
        # 옛 모델(2차 run 실물 모양 — train_config.json 에 peak_rule 없음) = plain + WARNING
        with tempfile.TemporaryDirectory() as tmp:
            mp = _run_dir(Path(tmp) / "run", {"classes": list(_CLASSES_4)})
            with self.assertLogs("app", level="WARNING") as logs:
                app = self._make_app(_CLASSES_4, model_path=mp)
        self.assertEqual(app.config["SERVING_LEVEL_MODE"], "peak")
        self.assertEqual(app.config["SERVING_LEVEL_RULE"], serving_level.RULE_PLAIN)
        self.assertTrue(any("peak_rule 없음" in m for m in logs.output), logs.output)
        model_in, wf_arg, decoded = self._detect_capture(app)
        np.testing.assert_array_equal(model_in, serving_level.peak_normalize(decoded))
        self.assertFalse(np.array_equal(model_in, decoded))
        self.assertEqual(wf_arg.tobytes(), decoded.tobytes())  # observe = decode 원본(바이트 동일)

    def test_t7_declared_clampmask_goes_to_predict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mp = _run_dir(Path(tmp) / "run", {"peak_rule": serving_level.RULE_CLAMPMASK32})
            app = self._make_app(_CLASSES_4, model_path=mp)
        self.assertEqual(app.config["SERVING_LEVEL_RULE"], serving_level.RULE_CLAMPMASK32)
        pcm = np.frombuffer(self.pcm, "<i2").copy()
        pcm[5000] = 32767  # 글리치 클램프 1샘플 — plain 이면 이득이 여기에 묶인다
        model_in, wf_arg, decoded = self._detect_capture(app, pcm.tobytes())
        np.testing.assert_array_equal(model_in, serving_level.peak_normalize_clampmask(decoded))
        self.assertFalse(np.allclose(model_in, serving_level.peak_normalize(decoded)))
        self.assertEqual(wf_arg.tobytes(), decoded.tobytes())  # observe = decode 원본

    def test_t8_unknown_rule_fails_startup_only_in_peak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mp = _run_dir(Path(tmp) / "run", {"peak_rule": "peak_foo_v9"})
            with self.assertRaisesRegex(ValueError, "peak_foo_v9"):
                self._make_app(_CLASSES_4, model_path=mp)
            # raw 모드(3클래스 · env raw)는 규칙을 읽지 않는다 → 규칙 무관
            self.assertIsNone(self._make_app(_CLASSES_3, model_path=mp).config["SERVING_LEVEL_RULE"])
            self.assertIsNone(self._make_app(_CLASSES_4, level="raw", model_path=mp).config["SERVING_LEVEL_RULE"])

    def test_t4_three_class_raw(self) -> None:
        app = self._make_app(_CLASSES_3)
        self.assertEqual(app.config["SERVING_LEVEL_MODE"], "raw")
        self.assertIsNone(app.config["SERVING_LEVEL_RULE"])
        model_in, wf_arg, decoded = self._detect_capture(app)
        self.assertEqual(model_in.tobytes(), decoded.tobytes())
        self.assertEqual(wf_arg.tobytes(), decoded.tobytes())

    def test_t5_three_class_with_peak_fails_startup(self) -> None:
        with self.assertRaisesRegex(ValueError, "DDINGDONG_SERVING_LEVEL=peak"):
            self._make_app(_CLASSES_3, level="peak")


if __name__ == "__main__":
    unittest.main()
