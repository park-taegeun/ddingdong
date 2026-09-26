"""초인종 등록 저장 층 · API 회귀 (stdlib unittest).

실행(server/ 에서):  python3 -m unittest app.tests.test_registration

외부 연결 가드: test_detect_regression 의 가드 함수와 _NoNetworkTestCase 를 import 해
쓴다(가드 구현은 그 파일 한 벌만 유지). 그 파일의 setUpModule 상속 검사는 자기 모듈
globals 만 보므로, 이 모듈은 자기 setUpModule 로 가드를 설치하고 자기 TestCase 를 검사한다.

토큰: DEVICE_TOKEN / DASHBOARD_TOKEN 은 test_detect_regression 의 더미 문자열을 그대로
쓴다. _TestConfig 는 카카오 4항목 · NCP 2항목을 비워 로컬 server/.env 실값 유입을 막는다.
"""

from __future__ import annotations

import os
import socket
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest import mock

from sqlalchemy import text

from .test_detect_regression import (
    _DASHBOARD_TOKEN,
    _DEVICE_TOKEN,
    _NET_ATTEMPTS,
    _NoNetworkTestCase,
    _install_network_guard,
    _uninstall_network_guard,
)

_STATUS_KEYS = {"state", "collected", "target", "started_at", "expires_at", "registered_at"}
_BASE = "/api/v1/registration"
_T0 = datetime(2026, 9, 26, 3, 0, 0)  # naive UTC

# main 실물(PRAGMA table_info)에서 뽑은 기존 3테이블 컬럼. 등록 기능은 새 테이블로만 간다.
_EXISTING_COLUMNS = {
    "notifications": (
        "id", "client_request_id", "request_id", "device_id", "detected_at",
        "predicted_class", "confidence", "all_scores", "tof_applied", "tof_passed",
        "tof_reason", "primary_sent", "primary_sent_at", "enrich_status",
        "secondary_sent", "secondary_sent_at", "skip_reason", "image_url",
        "image_thumbnail_url", "audio_url", "stt",
    ),
    "idempotency_keys": ("client_request_id", "request_id", "response_json", "created_at"),
    "kakao_tokens": (
        "id", "access_token", "refresh_token", "access_expires_at",
        "refresh_expires_at", "updated_at",
    ),
}
_NEW_TABLES = ("registration_state", "registration_templates")


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


def _pcm(n_bytes: int, fill: int = 1) -> bytes:
    return bytes([fill]) * n_bytes


class NetworkGuardSelfTest(_NoNetworkTestCase):
    """이 모듈에서도 가드가 살아 있음을 매 실행 증명한다."""

    def test_connection_attempt_is_refused_and_recorded(self):
        with self.assertRaises(ConnectionRefusedError):
            socket.create_connection(("127.0.0.1", 9), timeout=0.1)
        self.assertEqual(_NET_ATTEMPTS, ["127.0.0.1:9"])
        _NET_ATTEMPTS.clear()


class _AppCase(_NoNetworkTestCase):
    """클래스마다 임시 파일 DB 1개. 테스트마다 등록 테이블 2개를 비운다."""

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
        from .. import registration
        from ..extensions import db

        ctx = self.app.app_context()
        ctx.push()
        self.addCleanup(ctx.pop)
        self.addCleanup(db.session.rollback)
        self.reg = registration
        self.db = db
        registration.clear()
        db.session.commit()

    # ── 헬퍼 ──
    def _auth(self, token=_DASHBOARD_TOKEN):
        return {"Authorization": f"Bearer {token}"}

    def _start(self, body, token=_DASHBOARD_TOKEN):
        return self.client.post(f"{_BASE}/start", json=body, headers=self._auth(token))

    def _get(self):
        return self.client.get(_BASE, headers=self._auth())

    def _template_rows(self):
        return self.db.session.execute(
            text("SELECT registration_id FROM registration_templates ORDER BY id")
        ).scalars().all()

    def _insert_orphan(self, registration_id="orphan"):
        from ..models import RegistrationTemplate

        self.db.session.add(
            RegistrationTemplate(
                registration_id=registration_id,
                client_request_id="orphan-req",
                pcm=_pcm(4, 9),
                created_at=_T0,
            )
        )
        self.db.session.commit()

    def _start_direct(self, target, seconds=60, now=_T0):
        self.reg.start(target, seconds, now)
        self.db.session.commit()


class StateOfTest(_NoNetworkTestCase):
    """상태 판정 전 분기 (now 주입, 순수 함수)."""

    def test_all_branches(self):
        from ..registration import state_of

        exp = _T0 + timedelta(seconds=60)
        row = lambda completed: SimpleNamespace(completed_at=completed, expires_at=exp)  # noqa: E731
        cases = [
            ("행 없음", None, _T0, "none"),
            ("completed", row(_T0), _T0, "registered"),
            ("now < exp", row(None), exp - timedelta(microseconds=1), "collecting"),
            ("now == exp", row(None), exp, "expired"),
            ("now > exp", row(None), exp + timedelta(seconds=1), "expired"),
            ("completed + now > exp", row(_T0), exp + timedelta(days=1), "registered"),
        ]
        for label, r, now, expected in cases:
            with self.subTest(label):
                self.assertEqual(state_of(r, now), expected)


class AuthTest(_AppCase):
    def test_non_dashboard_tokens_rejected(self):
        endpoints = [
            ("get", _BASE, None),
            ("post", f"{_BASE}/start", {"target_count": 1, "expires_in_seconds": 1}),
            ("delete", _BASE, None),
        ]
        headers = {
            "토큰 없음": {},
            "틀린 토큰": self._auth("wrong-token"),
            "DEVICE 토큰": self._auth(_DEVICE_TOKEN),
        }
        for method, path, body in endpoints:
            for label, hdr in headers.items():
                with self.subTest(method=method, token=label):
                    resp = getattr(self.client, method)(path, json=body, headers=hdr)
                    self.assertEqual(resp.status_code, 401)
                    self.assertEqual(resp.get_json()["error"]["code"], "unauthorized")
        # 거부된 start 가 상태를 바꾸지 않았다
        self.assertEqual(self._get().get_json()["state"], "none")


class ApiTest(_AppCase):
    def test_initial_state_none_with_exact_keys(self):
        resp = self._get()
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(set(body), _STATUS_KEYS)
        self.assertEqual(
            body,
            {"state": "none", "collected": 0, "target": None, "started_at": None,
             "expires_at": None, "registered_at": None},
        )

    def test_start_returns_201_collecting(self):
        resp = self._start({"target_count": 3, "expires_in_seconds": 120})
        self.assertEqual(resp.status_code, 201)
        body = resp.get_json()
        self.assertEqual(set(body), _STATUS_KEYS)
        self.assertEqual(
            (body["state"], body["collected"], body["target"], body["registered_at"]),
            ("collecting", 0, 3, None),
        )
        self.assertTrue(body["started_at"].endswith("+09:00"))
        # 내부 식별자 · PCM 미노출
        raw = resp.get_data(as_text=True)
        row_id = self.db.session.execute(
            text("SELECT registration_id FROM registration_state")
        ).scalar_one()
        self.assertNotIn(row_id, raw)
        self.assertNotIn("registration_id", raw)
        self.assertNotIn("pcm", raw)

    def test_start_input_validation(self):
        from ..constants import REGISTRATION_EXPIRES_MAX_SECONDS as EMAX
        from ..constants import REGISTRATION_TARGET_COUNT_MAX as NMAX

        ok = {"target_count": 1, "expires_in_seconds": 1}
        cases = [
            ("target 0", {**ok, "target_count": 0}, 400),
            ("target 1", {**ok, "target_count": 1}, 201),
            ("target 상한", {**ok, "target_count": NMAX}, 201),
            ("target 상한+1", {**ok, "target_count": NMAX + 1}, 400),
            ("target True", {**ok, "target_count": True}, 400),
            ("target 1.0", {**ok, "target_count": 1.0}, 400),
            ("target '3'", {**ok, "target_count": "3"}, 400),
            ("target 누락", {"expires_in_seconds": 1}, 400),
            ("expires 0", {**ok, "expires_in_seconds": 0}, 400),
            ("expires 1", {**ok, "expires_in_seconds": 1}, 201),
            ("expires 상한", {**ok, "expires_in_seconds": EMAX}, 201),
            ("expires 상한+1", {**ok, "expires_in_seconds": EMAX + 1}, 400),
            ("expires True", {**ok, "expires_in_seconds": True}, 400),
            ("expires 누락", {"target_count": 1}, 400),
            ("모르는 키", {**ok, "extra": 1}, 400),
            ("배열", [1, 1], 400),
        ]
        for label, body, expected in cases:
            with self.subTest(label):
                self.reg.clear()
                self.db.session.commit()
                resp = self._start(body)
                self.assertEqual(resp.status_code, expected, resp.get_data(as_text=True))
                if expected == 400:
                    self.assertEqual(resp.get_json()["error"]["code"], "bad_request")
                    self.assertEqual(self._get().get_json()["state"], "none")
        with self.subTest("JSON 아님"):
            self.reg.clear()
            self.db.session.commit()
            resp = self.client.post(
                f"{_BASE}/start", data="target_count=1", headers=self._auth(),
                content_type="application/x-www-form-urlencoded",
            )
            self.assertEqual(resp.status_code, 400)
            resp = self.client.post(
                f"{_BASE}/start", data="{broken", headers=self._auth(),
                content_type="application/json",
            )
            self.assertEqual(resp.status_code, 400)

    def test_start_conflict_while_collecting(self):
        self.assertEqual(self._start({"target_count": 2, "expires_in_seconds": 60}).status_code, 201)
        resp = self._start({"target_count": 2, "expires_in_seconds": 60})
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.get_json()["error"]["code"], "conflict")
        self.assertIn("해제", resp.get_json()["error"]["message"])

    def test_start_conflict_while_registered(self):
        self._start({"target_count": 1, "expires_in_seconds": 60})
        from ..utils import utc_now

        self.assertEqual(self.reg.add_template(_pcm(4), "r1", utc_now()), "completed")
        self.db.session.commit()
        resp = self._start({"target_count": 1, "expires_in_seconds": 60})
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(self._get().get_json()["state"], "registered")
        self.assertEqual(len(self.reg.load_registered_templates()), 1)

    def test_start_after_expired_clears_previous_templates(self):
        self._start({"target_count": 3, "expires_in_seconds": 1})
        from ..utils import utc_now

        self.assertEqual(self.reg.add_template(_pcm(4), "r1", utc_now()), "added")
        self.db.session.commit()
        later = utc_now() + timedelta(seconds=5)
        with mock.patch("app.registration_api.utc_now", return_value=later):
            self.assertEqual(self._get().get_json()["state"], "expired")
            resp = self._start({"target_count": 2, "expires_in_seconds": 60})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["collected"], 0)
        self.assertEqual(self._template_rows(), [])

    def test_api_expiry_uses_module_clock(self):
        resp = self._start({"target_count": 2, "expires_in_seconds": 30})
        self.assertEqual(resp.get_json()["state"], "collecting")
        from ..utils import utc_now

        base = utc_now()
        with mock.patch("app.registration_api.utc_now", return_value=base + timedelta(seconds=31)):
            self.assertEqual(self._get().get_json()["state"], "expired")
        self.assertEqual(self._get().get_json()["state"], "collecting")

    def test_delete_from_every_state(self):
        from ..utils import utc_now

        def to_collecting():
            self._start({"target_count": 2, "expires_in_seconds": 60})

        def to_registered():
            self._start({"target_count": 1, "expires_in_seconds": 60})
            self.reg.add_template(_pcm(4), "r1", utc_now())
            self.db.session.commit()

        def to_expired():
            self._start_direct(2, seconds=1, now=utc_now() - timedelta(seconds=10))

        for label, setup in (("none", lambda: None), ("collecting", to_collecting),
                             ("registered", to_registered), ("expired", to_expired)):
            with self.subTest(label):
                self.reg.clear()
                self.db.session.commit()
                setup()
                self.assertEqual(self._get().get_json()["state"], label)
                self._insert_orphan()
                for _ in range(2):  # 멱등
                    resp = self.client.delete(_BASE, headers=self._auth())
                    self.assertEqual(resp.status_code, 200)
                    self.assertEqual(resp.get_json()["state"], "none")
                    self.assertEqual(set(resp.get_json()), _STATUS_KEYS)
                self.db.session.expire_all()
                self.assertEqual(self._template_rows(), [])


class StoreTest(_AppCase):
    def test_collect_flow_and_overflow(self):
        self._start_direct(2)
        self.assertEqual(self.reg.add_template(_pcm(4, 1), "r1", _T0), "added")
        self.assertEqual(self.reg.status(_T0)["collected"], 1)
        self.assertEqual(self.reg.add_template(_pcm(4, 2), "r2", _T0), "completed")
        self.db.session.commit()
        status = self.reg.status(_T0)
        self.assertEqual((status["state"], status["collected"]), ("registered", 2))
        self.assertIsNotNone(status["registered_at"])
        self.assertEqual(self.reg.add_template(_pcm(4, 3), "r3", _T0), "not_collecting")
        self.assertEqual(len(self._template_rows()), 2)

    def test_not_collecting_in_none_and_expired(self):
        self.assertEqual(self.reg.add_template(_pcm(4), "r1", _T0), "not_collecting")
        self._start_direct(2, seconds=10)
        self.assertEqual(
            self.reg.add_template(_pcm(4), "r1", _T0 + timedelta(seconds=10)), "not_collecting"
        )
        self.assertEqual(self._template_rows(), [])

    def test_target_reached_but_uncompleted_rejects_more(self):
        # 경합 등으로 collecting 인 채 개수만 목표에 도달한 상태 — 개수 검사만이 막는다.
        from ..models import RegistrationState, RegistrationTemplate

        self._start_direct(1)
        row = self.db.session.get(RegistrationState, RegistrationState.SINGLETON_ID)
        self.db.session.add(RegistrationTemplate(
            registration_id=row.registration_id, client_request_id="x",
            pcm=_pcm(4), created_at=_T0,
        ))
        self.db.session.commit()
        self.assertEqual(self.reg.status(_T0)["state"], "collecting")
        self.assertEqual(self.reg.add_template(_pcm(4), "r1", _T0), "not_collecting")
        self.assertEqual(len(self._template_rows()), 1)

    def test_invalid_pcm_raises(self):
        from ..constants import AUDIO_MAX_BYTES

        self._start_direct(2)
        for label, pcm in (("str", "abcd"), ("bytearray", bytearray(4)), ("빈 값", b""),
                           ("홀수", _pcm(3)), ("상한 초과", _pcm(AUDIO_MAX_BYTES + 2))):
            with self.subTest(label), self.assertRaises(ValueError):
                self.reg.add_template(pcm, "r1", _T0)
        # 상한 정확히는 허용
        self.assertEqual(self.reg.add_template(_pcm(AUDIO_MAX_BYTES), "r1", _T0), "added")

    def test_orphans_are_not_counted_or_loaded(self):
        self._start_direct(1)
        self._insert_orphan()
        self.assertEqual(self.reg.status(_T0)["collected"], 0)
        self.assertEqual(self.reg.add_template(_pcm(4, 7), "r1", _T0), "completed")
        self.db.session.commit()
        self.assertEqual(self.reg.status(_T0)["collected"], 1)
        self.assertEqual(self.reg.load_registered_templates(), [_pcm(4, 7)])

    def test_store_layer_does_not_commit(self):
        self._start_direct(3)
        self.assertEqual(self.reg.add_template(_pcm(4), "r1", _T0), "added")
        self.assertEqual(self.reg.status(_T0)["collected"], 1)  # 세션 안에서는 보인다
        self.db.session.rollback()
        self.assertEqual(self._template_rows(), [])
        self.assertEqual(self.reg.status(_T0)["collected"], 0)

    def test_load_registered_templates_only_when_registered(self):
        self.assertEqual(self.reg.load_registered_templates(), [])  # none
        self._start_direct(3, seconds=1, now=datetime(2000, 1, 1))
        self.assertEqual(self.reg.load_registered_templates(), [])  # expired

        self.reg.clear()
        from ..utils import utc_now

        now = utc_now()
        self._start_direct(3, seconds=600, now=now)
        pcms = [_pcm(4, 3), _pcm(4, 1), _pcm(4, 2)]
        for i, p in enumerate(pcms[:2]):
            self.reg.add_template(p, f"r{i}", now)
        self.db.session.commit()
        self.assertEqual(self.reg.load_registered_templates(), [])  # collecting
        self.assertEqual(self.reg.add_template(pcms[2], "r2", now), "completed")
        self.db.session.commit()
        self.assertEqual(self.reg.load_registered_templates(), pcms)  # 생성 순


class SchemaTest(_AppCase):
    def _pragma(self, table):
        with sqlite3.connect(self._db_path) as con:
            return con.execute(f"PRAGMA table_info({table})").fetchall()

    def test_existing_table_columns_are_pinned(self):
        for table, expected in _EXISTING_COLUMNS.items():
            with self.subTest(table):
                self.assertEqual(
                    tuple(r[1] for r in self._pragma(table)),
                    expected,
                    f"{table} 컬럼이 바뀌었다. create_all 은 기존 테이블에 컬럼을 추가하지 "
                    "않는다 → 기존 ddingdong.db 에서 새 컬럼 조회가 오류난다. 등록 기능 "
                    "데이터는 새 테이블에만 둔다.",
                )

    def test_pcm_column_is_blob(self):
        types = {r[1]: r[2] for r in self._pragma("registration_templates")}
        self.assertEqual(types["pcm"], "BLOB")

    def test_create_all_restores_new_tables_without_touching_old(self):
        self._start_direct(1)
        self.db.session.commit()
        self.db.session.remove()
        with self.db.engine.begin() as conn:
            for t in _NEW_TABLES:
                conn.execute(text(f"DROP TABLE {t}"))

        def snapshot():
            with sqlite3.connect(self._db_path) as con:
                return {
                    t: (self._pragma(t), con.execute(f"SELECT * FROM {t} ORDER BY rowid").fetchall())
                    for t in _EXISTING_COLUMNS
                }

        before = snapshot()
        self.db.create_all()
        with sqlite3.connect(self._db_path) as con:
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue(set(_NEW_TABLES) <= tables)
        self.assertEqual(snapshot(), before)


if __name__ == "__main__":
    unittest.main()
