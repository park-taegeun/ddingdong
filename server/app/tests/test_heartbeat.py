"""기기 heartbeat 수신 · /stats 기기 상태 파생 회귀 (stdlib unittest).

실행(server/ 에서):  python3 -m unittest app.tests.test_heartbeat

외부 연결 가드: test_registration 과 같은 방식 — test_detect_regression 의 가드 함수와
_NoNetworkTestCase 를 import 하고, 자기 setUpModule 로 가드를 설치해 자기 TestCase 를 검사한다.
_TestConfig 는 카카오 4항목 · NCP 2항목을 비워 로컬 server/.env 실값 유입을 막는다.

시각: routes 는 `from .utils import utc_now` 로 이름을 묶어 쓰므로 패치 지점은
app.routes.utc_now 다(app.utils.utc_now 를 패치하면 routes 에 닿지 않는다).
rate limit 표는 프로세스 전역이라 케이스마다 새 device_id 를 쓴다.
"""

from __future__ import annotations

import io
import os
import socket
import sqlite3
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta
from unittest import mock

from sqlalchemy import text

from .test_detect_regression import (
    _DASHBOARD_TOKEN,
    _DEVICE_TOKEN,
    _NET_ATTEMPTS,
    _NoNetworkTestCase,
    _install_network_guard,
    _pcm16_sine,
    _uninstall_network_guard,
)

_T0 = datetime(2026, 10, 6, 9, 0, 0)  # naive UTC
_TABLE = "device_heartbeats"


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


class NetworkGuardSelfTest(_NoNetworkTestCase):
    """이 모듈에서도 가드가 살아 있음을 매 실행 증명한다."""

    def test_connection_attempt_is_refused_and_recorded(self):
        with self.assertRaises(ConnectionRefusedError):
            socket.create_connection(("127.0.0.1", 9), timeout=0.1)
        self.assertEqual(_NET_ATTEMPTS, ["127.0.0.1:9"])
        _NET_ATTEMPTS.clear()


class HeartbeatTest(_NoNetworkTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fd, cls._db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        from .. import create_app
        from ..config import Config

        class _TestConfig(Config):
            DEVICE_TOKEN = _DEVICE_TOKEN
            DASHBOARD_TOKEN = _DASHBOARD_TOKEN
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{cls._db_path}"
            MODEL_PATH = ""
            KAKAO_REST_API_KEY = ""
            KAKAO_CLIENT_SECRET = ""
            KAKAO_ACCESS_TOKEN = ""
            KAKAO_REFRESH_TOKEN = ""
            NCP_CLIENT_ID = ""
            NCP_CLIENT_SECRET = ""

        cls.app = create_app(_TestConfig)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls) -> None:
        from ..extensions import db

        with cls.app.app_context():
            db.engine.dispose()
        os.unlink(cls._db_path)

    def setUp(self) -> None:
        super().setUp()
        from ..extensions import db

        self.db = db
        with self.app.app_context():
            db.session.execute(text(f"DELETE FROM {_TABLE}"))
            db.session.commit()

    # ── 헬퍼 ─────────────────────────────────────────────────────────────
    @staticmethod
    def _new_device() -> str:
        return f"hb-{uuid.uuid4().hex[:12]}"

    @staticmethod
    def _body(device_id: str, **over) -> dict:
        body = {"device_id": device_id, "rssi": -55, "uptime_s": 120, "fw": "v0_1", "enrich_sent": 3}
        body.update(over)
        return body

    def _beat(self, body, token=_DEVICE_TOKEN, at=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        if at is None:
            return self.client.post("/api/v1/heartbeat", headers=headers, json=body)
        with mock.patch("app.routes.utc_now", return_value=at):
            return self.client.post("/api/v1/heartbeat", headers=headers, json=body)

    def _health(self, at):
        with mock.patch("app.routes.utc_now", return_value=at):
            r = self.client.get(
                "/api/v1/stats?period=today",
                headers={"Authorization": f"Bearer {_DASHBOARD_TOKEN}"},
            )
        self.assertEqual(r.status_code, 200)
        h = r.get_json()["system_health"]
        return h["device_status"], h["signal_strength"], h["device_last_seen_at"]

    def _rows(self):
        with self.app.app_context():
            return self.db.session.execute(
                text(f"SELECT device_id, last_seen_at, rssi, uptime_s, fw, enrich_sent FROM {_TABLE}")
            ).all()

    def _detect(self, device_id):
        return self.client.post(
            "/api/v1/detect",
            headers={"Authorization": f"Bearer {_DEVICE_TOKEN}"},
            data={
                "client_request_id": f"hb-{uuid.uuid4().hex}",
                "device_id": device_id,
                "audio": (io.BytesIO(_pcm16_sine(32000)), "a.pcm"),
            },
            content_type="multipart/form-data",
        )

    # ── 인증 ─────────────────────────────────────────────────────────────
    def test_auth(self):
        dev = self._new_device()
        self.assertEqual(self._beat(self._body(dev), token=None).status_code, 401)
        self.assertEqual(self._beat(self._body(dev), token=_DASHBOARD_TOKEN).status_code, 401)
        self.assertEqual(self._rows(), [])
        r = self._beat(self._body(dev))
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r.get_data(), b"")

    # ── 검증 400 ────────────────────────────────────────────────────────
    def test_invalid_body_is_400_and_writes_nothing(self):
        dev = self._new_device()
        missing = self._body(dev)
        del missing["enrich_sent"]
        cases = {
            "누락": missing,
            "문자열 rssi": self._body(dev, rssi="-55"),
            "bool": self._body(dev, uptime_s=True),
            "rssi 범위 밖": self._body(dev, rssi=1),
            "음수 uptime": self._body(dev, uptime_s=-1),
            "fw 형식": self._body(dev, fw="v0.1"),
            "빈 device_id": self._body(""),
            "JSON 아님": None,
        }
        for name, body in cases.items():
            with self.subTest(name):
                if body is None:
                    r = self.client.post(
                        "/api/v1/heartbeat",
                        headers={"Authorization": f"Bearer {_DEVICE_TOKEN}"},
                        data="x",
                        content_type="text/plain",
                    )
                else:
                    r = self._beat(body)
                self.assertEqual(r.status_code, 400)
                self.assertEqual(r.get_json()["error"]["code"], "bad_request")
        self.assertEqual(self._rows(), [])

    # ── 저장 = 기기당 1행 덮어쓰기 ──────────────────────────────────────
    def test_second_beat_overwrites_single_row(self):
        dev = self._new_device()
        self.assertEqual(self._beat(self._body(dev), at=_T0).status_code, 204)
        later = _T0 + timedelta(seconds=30)
        self.assertEqual(
            self._beat(self._body(dev, rssi=-80, uptime_s=150, fw="v0_2", enrich_sent=4), at=later).status_code,
            204,
        )
        rows = self._rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], dev)
        self.assertEqual(tuple(rows[0][2:]), (-80, 150, "v0_2", 4))
        self.assertTrue(str(rows[0][1]).startswith("2026-10-06 09:00:30"))

    # ── /stats 파생 ─────────────────────────────────────────────────────
    def test_no_row_is_offline_none_null(self):
        self.assertEqual(self._health(_T0), ("offline", "none", None))

    def test_elapsed_boundary(self):
        dev = self._new_device()
        self._beat(self._body(dev), at=_T0)
        seen = "2026-10-06T18:00:00.000+09:00"
        cases = {
            "30초": (timedelta(seconds=30), "online"),
            "정확히 90초": (timedelta(seconds=90), "online"),
            "90초 + 1 ms": (timedelta(seconds=90, milliseconds=1), "offline"),
        }
        for name, (elapsed, status) in cases.items():
            with self.subTest(name):
                got_status, _, got_seen = self._health(_T0 + elapsed)
                self.assertEqual(got_status, status)
                self.assertEqual(got_seen, seen)  # 꺼져도 마지막 연결 시각은 남는다

    def test_signal_threshold(self):
        for rssi, signal in ((-70, "strong"), (-71, "weak")):
            with self.subTest(rssi=rssi):
                self._beat(self._body(self._new_device(), rssi=rssi), at=_T0)
                self.assertEqual(self._health(_T0 + timedelta(seconds=10))[:2], ("online", signal))
                with self.app.app_context():
                    self.db.session.execute(text(f"DELETE FROM {_TABLE}"))
                    self.db.session.commit()

    def test_offline_signal_is_none_even_with_good_rssi(self):
        self._beat(self._body(self._new_device(), rssi=-40), at=_T0)
        self.assertEqual(self._health(_T0 + timedelta(seconds=91))[:2], ("offline", "none"))

    def test_detection_without_heartbeat_is_offline(self):
        """감지 행이 방금 생겨도 heartbeat 가 없으면 꺼짐 — 감지는 기기 상태 판정 재료가 아니다."""
        self.assertEqual(self._detect(self._new_device()).status_code, 201)
        from ..utils import utc_now

        self.assertEqual(self._health(utc_now()), ("offline", "none", None))

    def test_detect_right_after_heartbeat_is_not_rate_limited(self):
        """heartbeat 는 /detect 의 device_id rate limit 을 쓰지 않는다."""
        dev = self._new_device()
        self.assertEqual(self._beat(self._body(dev)).status_code, 204)
        r = self._detect(dev)
        self.assertNotEqual(r.status_code, 429)
        self.assertEqual(r.status_code, 201)

    def test_stats_does_not_touch_heartbeat_row(self):
        self._beat(self._body(self._new_device()), at=_T0)
        before = self._rows()
        self._health(_T0 + timedelta(seconds=200))  # 꺼짐 판정 경로까지 지난다
        self.assertEqual(self._rows(), before)

    # ── 스키마: 새 표만 생기고 기존 표는 그대로 ──────────────────────────
    def test_create_all_adds_heartbeat_table_without_touching_others(self):
        self.assertEqual(self._detect(self._new_device()).status_code, 201)  # 기존 표에 행을 둔다
        with self.app.app_context():
            self.db.session.remove()
            with self.db.engine.begin() as conn:
                conn.execute(text(f"DROP TABLE {_TABLE}"))

            def snapshot():
                # 기존 표 목록을 하드코딩하지 않는다 — 목록에서 빠진 표는 검사를 피해 가기 때문.
                with sqlite3.connect(self._db_path) as con:
                    names = sorted(
                        r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    )
                    return {
                        t: (
                            con.execute(f"PRAGMA table_info({t})").fetchall(),
                            con.execute(f"SELECT * FROM {t} ORDER BY rowid").fetchall(),
                        )
                        for t in names
                    }

            before = snapshot()
            self.assertNotIn(_TABLE, before)
            self.assertIn("notifications", before)
            self.db.create_all()
            after = snapshot()
        self.assertIn(_TABLE, after)
        del after[_TABLE]
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
