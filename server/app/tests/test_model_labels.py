"""기동 시 모델 라벨 순서 가드(model_labels) 회귀 (stdlib unittest).

실행(server/ 에서):  python3 -m unittest app.tests.test_model_labels

L1 ~ L9 = resolve_labels 값 도메인 표, L10 = create_app 통합(init_app 대역 — 모델 로드 전 실패 증명).
외부 연결 가드: test_registration 과 같은 방식(가드 함수 import + 자기 setUpModule).
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from .. import model_labels
from .test_detect_regression import (
    _DASHBOARD_TOKEN,
    _DEVICE_TOKEN,
    _NoNetworkTestCase,
    _install_network_guard,
    _uninstall_network_guard,
)

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


def _labels(classes):
    """ml/training/config.write_labels 와 같은 모양."""
    return {"classes": list(classes), "index": {c: i for i, c in enumerate(classes)}}


def _run_dir(root: Path, labels) -> str:
    """run 폴더(labels.json = labels — dict 면 JSON, str 이면 그대로, None 이면 파일 없음) → MODEL_PATH."""
    root.mkdir(parents=True, exist_ok=True)
    if labels is not None:
        text = labels if isinstance(labels, str) else json.dumps(labels)
        (root / model_labels.LABELS_NAME).write_text(text, encoding="utf-8")
    return str(root / "inference_savedmodel")


class ResolveLabelsTest(_NoNetworkTestCase):
    """L1 ~ L9 값 도메인 표."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "run"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _resolve(self, labels):
        return model_labels.resolve_labels(_run_dir(self.root, labels), _CLASSES_4)

    def _rejects(self, labels, pattern):
        with self.assertRaisesRegex(ValueError, pattern) as cm:
            self._resolve(labels)
        msg = str(cm.exception)
        self.assertIn(str(self.root / model_labels.LABELS_NAME), msg)  # 파일 경로
        self.assertIn(repr(_CLASSES_4), msg)  # 기대 목록
        return msg

    def test_l1_match(self) -> None:
        self.assertEqual(self._resolve(_labels(_CLASSES_4)), (_CLASSES_4, False))

    def test_l2_missing_file_is_legacy(self) -> None:
        self.assertEqual(self._resolve(None), (None, True))

    def test_l3_order_only_differs(self) -> None:
        swapped = ("fire_alarm", "knock", "doorbell", "other")
        msg = self._rejects(_labels(swapped), "서빙 라벨 순서")
        self.assertIn(repr(swapped), msg)  # 실제 목록

    def test_l4_count_differs(self) -> None:
        self._rejects(_labels(_CLASSES_4[:3]), "서빙 라벨 순서")

    def test_l5_name_differs(self) -> None:
        self._rejects(_labels(("doorbell", "knock", "fire", "other")), "서빙 라벨 순서")

    def test_l6_broken_json(self) -> None:
        self._rejects('{"classes": [', "JSON")

    def test_l7_classes_shape(self) -> None:
        for bad in ({"index": {}}, {"classes": "doorbell"}, {"classes": [0, 1, 2, 3]}, [list(_CLASSES_4)]):
            with self.subTest(bad=bad):
                self._rejects(bad, '"classes"')

    def test_l8_index(self) -> None:
        no_index = {"classes": list(_CLASSES_4)}
        wrong = _labels(_CLASSES_4)
        wrong["index"] = {"doorbell": 2, "knock": 1, "fire_alarm": 0, "other": 3}
        for bad in (no_index, wrong):
            with self.subTest(bad=bad):
                self._rejects(bad, '"index"')

    def test_l9_trailing_slash(self) -> None:
        # 서브테스트마다 다른 run 폴더 — 같은 폴더면 앞 케이스의 labels.json 이 남아 「없음」 경로를 못 탄다.
        for i, labels in enumerate((_labels(_CLASSES_4), None)):
            with self.subTest(labels=labels):
                mp = _run_dir(self.root / str(i), labels)
                self.assertEqual(
                    model_labels.resolve_labels(mp + "/", _CLASSES_4),
                    model_labels.resolve_labels(mp, _CLASSES_4),
                )


class CreateAppWiringTest(_NoNetworkTestCase):
    """L10 create_app 통합 — init_app 은 대역(호출 여부로 모델 로드 전 실패를 증명)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls._db_file.close()

    @classmethod
    def tearDownClass(cls) -> None:
        os.unlink(cls._db_file.name)

    def _make_app(self, model_path):
        """→ (app, model_labels 로그 줄, init_app 대역). 실패하면 예외가 그대로 올라간다(대역 = self.init_app)."""
        from .. import create_app
        from ..config import Config

        db_uri = f"sqlite:///{self._db_file.name}"

        class _TestConfig(Config):
            DEVICE_TOKEN = _DEVICE_TOKEN
            DASHBOARD_TOKEN = _DASHBOARD_TOKEN
            SQLALCHEMY_DATABASE_URI = db_uri
            MODEL_PATH = model_path
            SERVING_LEVEL = None
            KAKAO_REST_API_KEY = ""
            KAKAO_CLIENT_SECRET = ""
            KAKAO_ACCESS_TOKEN = ""
            KAKAO_REFRESH_TOKEN = ""
            NCP_CLIENT_ID = ""
            NCP_CLIENT_SECRET = ""

        # 실패 케이스도 호출 여부를 볼 수 있게 대역을 self 에 남긴다.
        with mock.patch("app.model_serving.init_app") as self.init_app, self.assertLogs("app", level="WARNING") as logs:
            app = create_app(_TestConfig)
        return app, [m for m in logs.output if "model_labels" in m], self.init_app

    def test_l10_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, lines, init_app = self._make_app(_run_dir(Path(tmp) / "run", _labels(_CLASSES_4)))
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("일치 (doorbell, knock, fire_alarm, other)", lines[0])
        init_app.assert_called_once()

    def test_l10_legacy_warns_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            app, lines, init_app = self._make_app(_run_dir(Path(tmp) / "run", None))
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("labels.json 없음", lines[0])
        init_app.assert_called_once()
        self.assertEqual(app.test_client().get("/health").status_code, 200)

    def test_l10_mismatch_fails_before_model_load(self) -> None:
        swapped = ("fire_alarm", "knock", "doorbell", "other")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "서빙 라벨 순서"):
                self._make_app(_run_dir(Path(tmp) / "run", _labels(swapped)))
        self.init_app.assert_not_called()

    def test_l10_mock_no_check_no_log(self) -> None:
        _, lines, _ = self._make_app("")
        self.assertEqual(lines, [])


if __name__ == "__main__":
    unittest.main()
