"""server/seed.py 확인 플래그 가드 회귀 (stdlib unittest).

실행(server/ 에서):  python3 -m unittest app.tests.test_seed_guard

--confirm-delete-all 이 없으면 쓰기 0 · 종료 코드 2, 있으면 기존 동작(삭제 → 데모 5건).
행 수는 출력이 아니라 sqlite3 로 임시 DB 파일을 다시 열어 센다(출력만 보면 삭제가 일어나도 통과).

외부 연결 가드: test_registration 선례대로 test_detect_regression 의 가드 함수와
_NoNetworkTestCase 를 import 하고 자기 setUpModule 로 가드를 설치한다.
"""

from __future__ import annotations

import contextlib
import io
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime
from unittest import mock

import seed

from .test_detect_regression import (
    _DASHBOARD_TOKEN,
    _DEVICE_TOKEN,
    _NoNetworkTestCase,
    _install_network_guard,
    _uninstall_network_guard,
)

_PRE_ROWS = 3  # 시드 전에 심어 두는 알림 수(데모 5건과 다른 값)


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


class SeedGuardTest(_NoNetworkTestCase):
    """임시 파일 DB 1개. 테스트마다 알림 _PRE_ROWS 건 + 멱등 키 1건으로 되돌린다."""

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

    @classmethod
    def tearDownClass(cls) -> None:
        from ..extensions import db

        with cls.app.app_context():
            db.engine.dispose()
        os.unlink(cls._db_path)

    def setUp(self) -> None:
        super().setUp()
        from ..extensions import db
        from ..models import IdempotencyKey, Notification

        with self.app.app_context():
            db.session.query(Notification).delete()
            db.session.query(IdempotencyKey).delete()
            t0 = datetime(2026, 10, 13, 3, 0, 0)
            db.session.add_all(
                Notification(
                    client_request_id=f"pre_{i}",
                    request_id=f"req_pre_{i}",
                    device_id="test",
                    detected_at=t0,
                    predicted_class="knock",
                    confidence=0.9,
                    all_scores={"knock": 0.9},
                    tof_applied=False,
                    tof_reason="test",
                    primary_sent=False,
                    enrich_status="skipped",
                    secondary_sent=False,
                )
                for i in range(_PRE_ROWS)
            )
            db.session.add(
                IdempotencyKey(
                    client_request_id="pre_0",
                    request_id="req_pre_0",
                    response_json={"ok": True},
                    created_at=t0,
                )
            )
            db.session.commit()

    def _rows(self, table: str) -> list:
        # 세션 캐시를 거치지 않도록 파일을 새로 연다.
        with contextlib.closing(sqlite3.connect(self._db_path)) as conn:
            return conn.execute(f"SELECT client_request_id FROM {table} ORDER BY 1").fetchall()

    def _seed(self, confirm: bool) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = seed.seed(self.app, confirm)
        return code, out.getvalue()

    def test_without_confirm_writes_nothing(self):
        before = self._rows("notifications")
        code, out = self._seed(False)
        self.assertEqual(code, 2)
        self.assertEqual(self._rows("notifications"), before)
        self.assertEqual(len(before), _PRE_ROWS)
        self.assertIn(f"{_PRE_ROWS}건", out)
        self.assertIn(os.path.basename(self._db_path), out)
        self.assertNotIn(os.path.dirname(self._db_path), out)  # 경로 전체가 아니라 파일 이름만
        self.assertIn("--confirm-delete-all", out)

    def test_with_confirm_replaces_with_demo_rows(self):
        keys_before = self._rows("idempotency_keys")
        code, out = self._seed(True)
        self.assertEqual(code, 0)
        self.assertEqual(
            [r[0] for r in self._rows("notifications")],
            [s["client_request_id"] for s in seed._SEED_SPECS],
        )
        self.assertEqual(self._rows("idempotency_keys"), keys_before)
        self.assertIn(f"기존 알림 {_PRE_ROWS}건 삭제 → 데모 알림 5건 삽입 완료.", out)

    def test_main_without_flag_exits_nonzero(self):
        before = self._rows("notifications")
        with mock.patch.object(seed, "create_app", return_value=self.app), \
                contextlib.redirect_stdout(io.StringIO()):
            code = seed.main([])
        self.assertNotEqual(code, 0)
        self.assertEqual(self._rows("notifications"), before)

    def test_main_with_flag_seeds(self):
        with mock.patch.object(seed, "create_app", return_value=self.app), \
                contextlib.redirect_stdout(io.StringIO()):
            code = seed.main(["--confirm-delete-all"])
        self.assertEqual(code, 0)
        self.assertEqual(len(self._rows("notifications")), len(seed._SEED_SPECS))


if __name__ == "__main__":
    unittest.main()
