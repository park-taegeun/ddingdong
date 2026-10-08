"""/detect 신뢰도 반올림 갈림 계측(decisions.md 33.6(e)) 회귀 (stdlib unittest).

실행(server/ 에서):  python3 -m unittest app.tests.test_round_gap_log

★ 판정 무변경 계측이다 — 반올림 전 top 원점수가 임계 미만인데 2자리 반올림값이 게이트를
  통과한 /detect 만 WARNING 1줄로 남는다. 판정은 여전히 반올림값으로 한다. 33.6(e) 수정
  여부(방식 포함)는 미결이며 이 파일의 존재를 「현행 유지」 승인으로 읽지 말 것.

경계 = test_detect_regression 의 _f32_gate_boundaries() · _f32_top_scores() 재사용(리터럴 신설 X).
ToF 는 부재(fail-open) — 이 파일이 보는 축은 신뢰도 게이트 하나다. 카카오 발송은 대역.

외부 연결 가드: test_registration 과 같은 방식(가드 함수 import + 자기 setUpModule).
"""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from unittest import mock

from sqlalchemy import select

from .test_detect_regression import (
    _DASHBOARD_TOKEN,
    _DEVICE_TOKEN,
    _NoNetworkTestCase,
    _f32_gate_boundaries,
    _f32_top_scores,
    _install_network_guard,
    _pcm16_sine,
    _uninstall_network_guard,
)

_PREFIX = "detect round gap:"
_FLIPS = ("flip_min", "flip_max")
_NO_FLIPS = ("no_flip_below", "no_flip_above")


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


class RoundGapLogTest(_NoNetworkTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls._db_file.close()

        from .. import create_app
        from ..config import Config

        class _TestConfig(Config):
            DEVICE_TOKEN = _DEVICE_TOKEN
            DASHBOARD_TOKEN = _DASHBOARD_TOKEN
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{cls._db_file.name}"
            MODEL_PATH = ""  # 실모델 로드 없음 — real 분기는 is_real_mode · predict 대역으로 연다
            # 4클래스 + MODEL_PATH 미설정이면 mode=peak · rule=None 이라 real 분기가 RULES[None]
            # 에서 멈춘다. raw 로 고정 — 이 파일은 입력 레벨이 아니라 반올림 갈림만 본다.
            SERVING_LEVEL = "raw"
            KAKAO_REST_API_KEY = ""
            KAKAO_CLIENT_SECRET = ""
            KAKAO_ACCESS_TOKEN = ""
            KAKAO_REFRESH_TOKEN = ""
            NCP_CLIENT_ID = ""
            NCP_CLIENT_SECRET = ""

        cls.app = create_app(_TestConfig)
        cls.client = cls.app.test_client()
        cls.pcm = _pcm16_sine(32000)

    @classmethod
    def tearDownClass(cls) -> None:
        os.unlink(cls._db_file.name)

    def _detect(self, name, raw, real=True):
        """predict 대역이 _f32_top_scores(raw) 를 내는 /detect 1회 → (응답, 접두 로그 레코드, 발송 대역, 저장 행).

        rate limit · 멱등 게이트가 추론 앞이라 요청마다 device_id · client_request_id 를 다르게 한다.
        """
        from ..extensions import db
        from ..models import Notification

        crid = f"gap-{self._testMethodName}-{name}"
        # INFO 로 받는다 — 매 요청 INFO 가 최소 1줄(추론 · tof 로그) 나와 assertLogs 가 0줄로 실패하지 않는다.
        with mock.patch("app.routes.model_serving.is_real_mode", return_value=real), mock.patch(
            "app.routes.model_serving.predict", return_value=_f32_top_scores(raw)
        ) as predict, mock.patch(
            "app.kakao.send_primary_text", return_value=None
        ) as send, self.assertLogs("app", level="INFO") as logs:
            r = self.client.post(
                "/api/v1/detect",
                headers={"Authorization": f"Bearer {_DEVICE_TOKEN}"},
                data={
                    "client_request_id": crid,
                    "device_id": f"dev-{crid}",
                    "audio": (io.BytesIO(self.pcm), "a.pcm"),
                },
                content_type="multipart/form-data",
            )
        self.assertEqual(r.status_code, 201, r.get_data(as_text=True))
        self.assertEqual(predict.called, real)
        gap = [rec for rec in logs.records if rec.getMessage().startswith(_PREFIX)]
        with self.app.app_context():
            row = db.session.scalar(
                select(Notification).where(Notification.client_request_id == crid)
            )
            stored = (row.primary_sent, row.skip_reason, row.enrich_status, row.confidence)
        return crid, r.get_json(), gap, send, stored

    def test_flip_boundaries_log_one_warning_with_raw_score(self) -> None:
        messages = []
        for name in _FLIPS:
            raw = _f32_gate_boundaries()[name]
            with self.subTest(boundary=name):
                crid, _, gap, _, _ = self._detect(name, raw)
                self.assertEqual(len(gap), 1, [g.getMessage() for g in gap])
                self.assertEqual(gap[0].levelname, "WARNING")
                msg = gap[0].getMessage()
                messages.append(msg)
                self.assertIn(f"client_request_id={crid} ", msg)
                self.assertIn("rounded=0.70 ", msg)
                self.assertIn("predicted_class=doorbell ", msg)
                # repr 는 float 를 왕복 보존한다 → 문자열 일치 = 원점수 일치(소수 6자리면 이웃 f32 가 접힌다)
                self.assertIn(f"raw={float(raw)!r} ", msg)
        # demo_up 실시간 표시는 같은 WARNING 을 1회만 보여 준다 → 줄마다 달라야 한다
        self.assertEqual(len(set(messages)), len(messages))

    def test_no_flip_boundaries_log_nothing(self) -> None:
        for name in _NO_FLIPS:
            with self.subTest(boundary=name):
                _, _, gap, _, _ = self._detect(name, _f32_gate_boundaries()[name])
                self.assertEqual(gap, [])

    def test_decision_is_unchanged_on_all_boundaries(self) -> None:
        """기대 = 반올림값으로 정책을 부른 결과(현행). 발송 대역 · 저장 행 · 응답을 축별로 따로 본다.

        응답만 보면 안 된다 — 응답 스냅샷이 판정 침입보다 먼저 만들어져 못 잡은 선례(#88)가 있다.
        """
        from .. import model_serving
        from ..utils import _apply_prediction_policy

        for name, raw in _f32_gate_boundaries().items():
            cls, rounded, all_scores = model_serving.scores_to_prediction(_f32_top_scores(raw))
            want = _apply_prediction_policy(cls, rounded, all_scores)
            _, body, _, send, stored = self._detect(name, raw)
            status = body["notification_status"]
            with self.subTest(boundary=name, axis="send"):
                self.assertEqual(send.called, want["primary_sent"])
            with self.subTest(boundary=name, axis="row"):
                self.assertEqual(
                    stored,
                    (want["primary_sent"], want["skip_reason"], want["enrich_status"], rounded),
                )
            with self.subTest(boundary=name, axis="response"):
                self.assertEqual(
                    (status["primary_sent"], status.get("skip_reason"), status["enrich_status"]),
                    (want["primary_sent"], want["skip_reason"], want["enrich_status"]),
                )
                self.assertEqual(body["confidence"], rounded)

    def test_mock_branch_logs_nothing(self) -> None:
        for name in _FLIPS:
            with self.subTest(boundary=name):
                _, _, gap, _, _ = self._detect(name, _f32_gate_boundaries()[name], real=False)
                self.assertEqual(gap, [])


if __name__ == "__main__":
    unittest.main()
