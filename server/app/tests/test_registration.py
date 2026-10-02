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
_NEW_TABLES = (
    "registration_state",
    "registration_templates",
    "registration_matches",
    "registration_failures",
)


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


def _tone(freq_hz: float, n_samples: int = 8000) -> bytes:
    """int16 LE 사인파 PCM (16 kHz). 주파수가 다르면 DTW 거리가 0 이 아니게 된다."""
    import numpy as np

    t = np.arange(n_samples) / 16000
    return (np.sin(2 * np.pi * freq_hz * t) * 8000).astype("<i2").tobytes()


def _fixed_pred(confidence: float, cls: str = "doorbell", tof_presence: str | None = None):
    """utils 실물 판정 함수로 만든 고정 예측 dict. 0.7 미만이면 primary_sent=False.

    tof_presence = "true" | "false" 면 ToF 메타를 실물 파서로 만들어 게이트에 넣는다.
    """
    from ..constants import PREDICTED_CLASSES
    from ..tof_meta import parse_tof_meta
    from ..utils import _apply_prediction_policy

    rest = round((1.0 - confidence) / (len(PREDICTED_CLASSES) - 1), 2)
    scores = {c: (confidence if c == cls else rest) for c in PREDICTED_CLASSES}
    tof = parse_tof_meta({} if tof_presence is None else {"tof_presence": tof_presence})
    return _apply_prediction_policy(cls, confidence, scores, tof)


# 요청마다 달라지는 값 — 응답 · 저장 비교에서 뺀다
_VOLATILE = ("client_request_id", "request_id", "detected_at", "device_id")


class _DetectCase(_AppCase):
    """/detect 등록 경로 공통 헬퍼. 테스트마다 측정 · 실패 행도 비운다."""

    def setUp(self) -> None:
        super().setUp()
        self.db.session.execute(text("DELETE FROM registration_matches"))
        self.db.session.execute(text("DELETE FROM registration_failures"))
        self.db.session.commit()
        self._seq = 0

    # ── 헬퍼 ──
    def _detect(self, pcm, crid=None, confidence=0.5, cls="doorbell", tof_presence=None):
        import io

        self._seq += 1
        crid = crid or f"obs-{self._testMethodName}-{self._seq}"
        # rate limit 이 기기별 5초라 요청마다 device_id 를 바꾼다
        data = {
            "client_request_id": crid,
            "device_id": f"dev-{self._testMethodName}-{self._seq}",
            "audio": (io.BytesIO(pcm), "a.pcm"),
        }
        pred = _fixed_pred(confidence, cls, tof_presence)
        with mock.patch("app.routes.mock_prediction", return_value=pred):
            return self.client.post(
                "/api/v1/detect",
                headers=self._auth(_DEVICE_TOKEN),
                data=data,
                content_type="multipart/form-data",
            )

    def _count(self, table):
        return self.db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()

    def _matches(self):
        import json

        rows = self.db.session.execute(text(
            "SELECT client_request_id, registration_id, predicted_class, template_count, "
            "distances, min_distance, mean_distance, compare_ms FROM registration_matches "
            "ORDER BY id"
        )).all()
        return [SimpleNamespace(**{**r._asdict(), "distances": json.loads(r.distances)}) for r in rows]

    def _register(self, pcms):
        from ..utils import utc_now

        now = utc_now()
        self._start_direct(len(pcms), seconds=600, now=now)
        for i, p in enumerate(pcms):
            self.reg.add_template(p, f"seed-{i}", now)
        self.db.session.commit()
        self.assertEqual(self.reg.status(now)["state"], "registered")

    def _stored_notification(self, crid):
        from ..models import Notification

        self.db.session.expire_all()  # 요청이 쓴 값을 DB 에서 다시 읽는다
        return self.db.session.query(Notification).filter_by(client_request_id=crid).one().to_dict()


class DetectObserveTest(_DetectCase):
    """/detect 등록 계측 — 템플릿 저장 · 거리 기록 · 저신뢰(미발송) 건 응답 영향 0."""

    # ── 상태별 ──
    def test_none_writes_nothing(self):
        resp = self._detect(_tone(440))
        self.assertEqual(resp.status_code, 201)
        self.assertEqual((self._count("registration_templates"), self._count("registration_matches")), (0, 0))

    def test_expired_writes_nothing(self):
        from ..utils import utc_now

        self._start_direct(2, seconds=1, now=utc_now() - timedelta(seconds=10))
        resp = self._detect(_tone(440))
        self.assertEqual(resp.status_code, 201)
        self.assertEqual((self._count("registration_templates"), self._count("registration_matches")), (0, 0))

    def test_collecting_saves_templates_until_registered(self):
        from ..utils import utc_now

        self._start_direct(2, seconds=600, now=utc_now())
        pcms = [_tone(440), _tone(660)]
        crids = []
        for p in pcms:
            resp = self._detect(p, confidence=0.9)  # 수락 조건 = doorbell + 신뢰도 통과
            self.assertEqual(resp.status_code, 201)
            crids.append(resp.get_json()["client_request_id"])
        self.db.session.expire_all()
        self.assertEqual(self.reg.status(utc_now())["state"], "registered")
        rows = self.db.session.execute(text(
            "SELECT client_request_id, pcm FROM registration_templates ORDER BY id"
        )).all()
        self.assertEqual([(r[0], r[1]) for r in rows], list(zip(crids, pcms)))
        self.assertEqual(self._count("registration_matches"), 0)

    def test_registered_records_distances_matching_sound_match(self):
        from inference.audio_decode import decode_pcm16

        from ..sound_match import dtw_cosine_distance, waveform_to_template

        stored = [_tone(440), _tone(880)]
        self._register(stored)
        query_pcm = _tone(660)
        resp = self._detect(query_pcm)
        self.assertEqual(resp.status_code, 201)

        (m,) = self._matches()
        q = waveform_to_template(decode_pcm16(query_pcm)[0])
        expected = [dtw_cosine_distance(waveform_to_template(decode_pcm16(p)[0]), q) for p in stored]
        self.assertEqual(m.client_request_id, resp.get_json()["client_request_id"])
        self.assertEqual(m.predicted_class, "doorbell")
        self.assertEqual(m.template_count, 2)
        self.assertEqual(m.distances, expected)
        self.assertTrue(all(d > 0 for d in expected))  # 거리가 전부 0 이면 비교가 무딘 것
        self.assertEqual(m.min_distance, min(expected))
        self.assertAlmostEqual(m.mean_distance, sum(expected) / 2)
        self.assertGreaterEqual(m.compare_ms, 0)
        reg_id = self.db.session.execute(
            text("SELECT registration_id FROM registration_state")
        ).scalar_one()
        self.assertEqual(m.registration_id, reg_id)
        self.assertEqual(self._count("registration_templates"), 2)  # 등록 뒤엔 템플릿 불변

    def test_idempotent_replay_writes_nothing(self):
        from ..utils import utc_now

        with self.subTest("collecting"):
            self._start_direct(3, seconds=600, now=utc_now())
            self.assertEqual(self._detect(_tone(440), crid="replay-c", confidence=0.9).status_code, 201)
            resp = self._detect(_tone(440), crid="replay-c", confidence=0.9)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.headers.get("Idempotent-Replay"), "true")
            self.assertEqual(self._count("registration_templates"), 1)
        with self.subTest("registered"):
            self.reg.clear()
            self.db.session.commit()
            self._register([_tone(440)])
            self.assertEqual(self._detect(_tone(660), crid="replay-r").status_code, 201)
            self.assertEqual(self._detect(_tone(660), crid="replay-r").status_code, 200)
            self.assertEqual(self._count("registration_matches"), 1)
            self.assertEqual(self._count("registration_templates"), 1)

    def test_response_and_stored_notification_unchanged_by_registration(self):
        from ..utils import utc_now

        def strip(d):
            return {k: v for k, v in d.items() if k not in _VOLATILE}

        def run(label):
            resp = self._detect(_tone(660))
            self.assertEqual(resp.status_code, 201, label)
            body = resp.get_json()
            return strip(body), strip(self._stored_notification(body["client_request_id"]))

        baseline = run("none")
        self._start_direct(3, seconds=600, now=utc_now())
        collecting = run("collecting")
        self.reg.clear()
        self.db.session.commit()
        self._register([_tone(440)])
        registered = run("registered")

        self.assertEqual(self._count("registration_matches"), 1)  # 훅이 실제로 돌았다
        self.assertEqual(collecting, baseline)
        self.assertEqual(registered, baseline)
        # 응답 본문과 저장 행이 같은 내용이다(저장 뒤 훅이 행을 바꾸지 않았다)
        self.assertEqual(registered[0], registered[1])

    def test_hook_failure_is_logged_and_detect_proceeds(self):
        self._register([_tone(440)])
        with mock.patch(
            "app.registration_observe.dtw_cosine_distance", side_effect=RuntimeError("boom")
        ), self.assertLogs(self.app.logger, "ERROR") as logs:
            resp = self._detect(_tone(660))
        self.assertEqual(resp.status_code, 201)
        crid = resp.get_json()["client_request_id"]
        self.assertIn(crid, "\n".join(logs.output))
        self.assertIn("boom", "\n".join(logs.output))  # traceback 포함(logger.exception)
        self.assertEqual(self._stored_notification(crid)["client_request_id"], crid)
        self.assertEqual(self._count("registration_matches"), 0)


class JudgeUnitTest(_NoNetworkTestCase):
    """등록 판정 · 수락 조건 순수 함수 (DB 없음)."""

    def test_judge_table(self):
        from ..registration_observe import judge

        c, r, mm = "registration_collecting", None, "registration_mismatch"
        cases = [
            # (state, class, policy_sends, min_distance) → 기대
            (("collecting", "doorbell", True, None), c),
            (("collecting", "fire_alarm", True, None), r),
            (("collecting", "knock", True, None), r),
            (("collecting", "doorbell", False, None), r),  # 정책 미발송 = 정책 사유 그대로
            (("registered", "doorbell", True, 0.10), r),
            (("registered", "doorbell", True, 0.20), r),  # 경계 = 일치(strict >)
            (("registered", "doorbell", True, 0.2000001), mm),
            (("registered", "doorbell", True, None), r),  # 계산 실패 = 막지 않음(fail-open)
            (("registered", "knock", True, 0.9), r),
            (("registered", "doorbell", False, 0.9), r),
            (("none", "doorbell", True, None), r),
            (("expired", "doorbell", True, None), r),
            ((None, "doorbell", True, None), r),  # 상태 조회 실패
        ]
        for args, want in cases:
            with self.subTest(args=args):
                self.assertEqual(judge(*args), want)

    def test_accepts_template(self):
        from ..registration_observe import accepts_template

        self.assertTrue(accepts_template("doorbell", 0.70))
        self.assertTrue(accepts_template("doorbell", 0.99))
        self.assertFalse(accepts_template("doorbell", 0.69))
        for cls in ("knock", "fire_alarm", "other"):
            self.assertFalse(accepts_template(cls, 0.99), cls)


class DetectJudgmentTest(_DetectCase):
    """/detect 등록 판정 — 수집 중 억제 · 소리 불일치 차단 · 실패 = 발송 + 기록.

    카카오 1차 발송은 대역이 **진짜** kakao._assert_commit_is_safe() 를 부른 뒤 성공을
    돌려준다 — 카카오 앞에 add 가 생기면 어느 테스트에서든 500 으로 드러난다.
    """

    def _send(self, *a, **kw):
        """(resp, send mock). 카카오 대역 아래에서 /detect 1회."""
        from .. import kakao

        real_guard = kakao._assert_commit_is_safe

        def fake_send(predicted_class):
            real_guard()
            return None

        with mock.patch("app.kakao.send_primary_text", side_effect=fake_send) as send:
            resp = self._detect(*a, **kw)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))
        return resp, send

    def _status(self, resp):
        return resp.get_json()["notification_status"]

    def _collecting(self, target=3):
        from ..utils import utc_now

        self._start_direct(target, seconds=600, now=utc_now())

    def _register3(self):
        self._register([_tone(440), _tone(660), _tone(880)])

    def _distances(self, values):
        """판정 · 측정에 쓰이는 거리 함수를 고정값 순서열로 바꾼다(템플릿 생성 순)."""
        it = iter(values)
        return mock.patch(
            "app.registration_observe.dtw_cosine_distance", side_effect=lambda a, b: next(it)
        )

    def _failures(self):
        return self.db.session.execute(text(
            "SELECT client_request_id, registration_id, predicted_class, judged, error "
            "FROM registration_failures ORDER BY id"
        )).all()

    def _assert_blocked(self, resp, send, reason):
        st = self._status(resp)
        self.assertFalse(st["primary_sent"])
        self.assertIsNone(st["primary_sent_at"])
        self.assertEqual(st["skip_reason"], reason)
        self.assertEqual(st["enrich_status"], "skipped")
        send.assert_not_called()

    def _assert_sent(self, resp, send, cls="doorbell"):
        st = self._status(resp)
        self.assertTrue(st["primary_sent"])
        self.assertNotIn("skip_reason", st)
        send.assert_called_once_with(cls)

    # ── 수집 중 ──
    def test_collecting_doorbell_is_suppressed_and_saved(self):
        self._collecting()
        resp, send = self._send(_tone(440), confidence=0.9)
        self._assert_blocked(resp, send, "registration_collecting")
        self.assertEqual(self._count("registration_templates"), 1)
        # 응답 본문 == 저장 행(억제가 저장 뒤에 행을 바꾸지 않았다)
        self.assertEqual(resp.get_json(), self._stored_notification(resp.get_json()["client_request_id"]))

    def test_collecting_fire_alarm_and_knock_are_sent_not_saved(self):
        for cls in ("fire_alarm", "knock"):
            with self.subTest(cls=cls):
                self.reg.clear()
                self.db.session.commit()
                self._collecting()
                resp, send = self._send(_tone(440), confidence=0.9, cls=cls)
                self._assert_sent(resp, send, cls)
                self.assertEqual(self._count("registration_templates"), 0)

    def test_collecting_rejects_low_confidence_doorbell_and_other(self):
        self._collecting()
        resp, send = self._send(_tone(440), confidence=0.5)
        self._assert_blocked(resp, send, "low_confidence")  # 게이트 순서: 신뢰도가 먼저
        resp, send = self._send(_tone(440), confidence=0.9, cls="other")
        self._assert_blocked(resp, send, "not_target")
        self.assertEqual(self._count("registration_templates"), 0)

    def test_collecting_accepts_doorbell_regardless_of_tof(self):
        self._collecting()
        resp, send = self._send(_tone(440), confidence=0.9, tof_presence="false")
        self._assert_blocked(resp, send, "tof_rejected")  # ToF 가 먼저 걸린다
        self.assertEqual(self._count("registration_templates"), 1)  # 수락은 ToF 무관

    # ── 등록됨 ──
    def test_registered_matching_doorbell_is_sent(self):
        self._register3()
        resp, send = self._send(_tone(440), confidence=0.9)  # 템플릿 1번과 같은 소리
        self._assert_sent(resp, send)
        (m,) = self._matches()
        self.assertLessEqual(m.min_distance, 0.20)

    def test_registered_mismatch_is_blocked(self):
        self._register3()
        with self._distances([0.5, 0.6, 0.7]):
            resp, send = self._send(_tone(440), confidence=0.9)
        self._assert_blocked(resp, send, "registration_mismatch")
        (m,) = self._matches()
        self.assertEqual(m.distances, [0.5, 0.6, 0.7])
        self.assertEqual(resp.get_json(), self._stored_notification(resp.get_json()["client_request_id"]))

    def test_boundary_exactly_threshold_is_sent(self):
        self._register3()
        with self._distances([0.9, 0.20, 0.9]):
            resp, send = self._send(_tone(440), confidence=0.9)
        self._assert_sent(resp, send)

    def test_min_aggregation_one_close_template_is_enough(self):
        # 평균이면 0.35 > 0.20 으로 차단될 입력 — 하나만 가깝고 둘은 멀다.
        self._register3()
        with self._distances([0.5, 0.05, 0.5]):
            resp, send = self._send(_tone(440), confidence=0.9)
        self._assert_sent(resp, send)

    def test_registered_knock_far_is_sent_and_measured(self):
        self._register3()
        with self._distances([0.9, 0.9, 0.9]):
            resp, send = self._send(_tone(440), confidence=0.9, cls="knock")
        self._assert_sent(resp, send, "knock")
        self.assertEqual([m.predicted_class for m in self._matches()], ["knock"])

    def test_gate_order_tof_rejected_before_registration(self):
        self._register3()
        with self._distances([0.9, 0.9, 0.9]):
            resp, send = self._send(_tone(440), confidence=0.9, tof_presence="false")
        self._assert_blocked(resp, send, "tof_rejected")
        self.assertEqual(len(self._matches()), 1)  # 측정은 계속

    def test_measurement_rows_for_every_class(self):
        self._register3()
        for cls, conf in (("knock", 0.9), ("fire_alarm", 0.9), ("other", 0.9), ("doorbell", 0.5)):
            with self._distances([0.9, 0.9, 0.9]):
                self._send(_tone(440), confidence=conf, cls=cls)
        self.assertEqual(
            [m.predicted_class for m in self._matches()], ["knock", "fire_alarm", "other", "doorbell"]
        )

    def test_distances_computed_once_and_shared(self):
        from .. import registration_observe

        self._register3()
        returned = []

        def spy(a, b):
            d = real(a, b)
            returned.append(d)
            return d

        real = registration_observe.dtw_cosine_distance
        with mock.patch("app.registration_observe.dtw_cosine_distance", side_effect=spy):
            self._send(_tone(500), confidence=0.9)  # 판정 경로
            self._send(_tone(500), confidence=0.9, cls="knock")  # 측정 전용 경로
        self.assertEqual(len(returned), 6)  # 요청당 템플릿 수(3)만큼 — 재계산 0
        m1, m2 = self._matches()
        self.assertEqual(m1.distances, returned[:3])
        self.assertEqual(m2.distances, returned[3:])

    # ── 실패 = 막지 않음 ──
    def test_compute_error_sends_and_records_failure(self):
        self._register3()
        with mock.patch(
            "app.registration_observe.dtw_cosine_distance", side_effect=RuntimeError("boom")
        ), self.assertLogs(self.app.logger, "ERROR") as logs:
            resp, send = self._send(_tone(440), confidence=0.9)
        self._assert_sent(resp, send)
        crid = resp.get_json()["client_request_id"]
        self.assertIn("fail-open", "\n".join(logs.output))
        (f,) = self._failures()
        self.assertEqual((f.client_request_id, f.predicted_class, bool(f.judged)), (crid, "doorbell", True))
        self.assertEqual(f.error, "RuntimeError: boom")
        self.assertIsNotNone(f.registration_id)
        self.assertEqual(self._matches(), [])

    def test_no_templates_sends_and_records_failure(self):
        self._register3()
        self.db.session.execute(text("DELETE FROM registration_templates"))
        self.db.session.commit()
        resp, send = self._send(_tone(440), confidence=0.9)
        self._assert_sent(resp, send)
        (f,) = self._failures()
        self.assertEqual(f.error, "LookupError: no_templates")
        self.assertTrue(f.judged)

    def test_measurement_only_failure_is_not_judged(self):
        self._register3()
        with mock.patch(
            "app.registration_observe.dtw_cosine_distance", side_effect=RuntimeError("boom")
        ), self.assertLogs(self.app.logger, "ERROR"):
            self._send(_tone(440), confidence=0.9, cls="knock")
        (f,) = self._failures()
        self.assertFalse(f.judged)

    def test_none_and_expired_keep_current_behavior(self):
        from ..utils import utc_now

        resp, send = self._send(_tone(440), confidence=0.9)
        self._assert_sent(resp, send)
        self._start_direct(3, seconds=1, now=utc_now() - timedelta(seconds=10))
        resp, send = self._send(_tone(440), confidence=0.9)
        self._assert_sent(resp, send)
        counts = [self._count(t) for t in ("registration_templates", "registration_matches", "registration_failures")]
        self.assertEqual(counts, [0, 0, 0])

    # ── 커밋 가드(진짜 가드를 발송 대역 안에서 호출하는 원 패턴) ──
    def test_registration_writes_after_kakao_send_in_same_commit(self):
        with self.subTest("registered doorbell match → 발송 + 측정 행"):
            self._register3()
            resp, send = self._send(_tone(440), confidence=0.9)
            self._assert_sent(resp, send)
            self.assertEqual(len(self._matches()), 1)
        with self.subTest("collecting fire_alarm → 발송 + 템플릿 0"):
            self.reg.clear()
            self.db.session.commit()
            self._collecting()
            resp, send = self._send(_tone(440), confidence=0.9, cls="fire_alarm")
            self._assert_sent(resp, send, "fire_alarm")
            self.assertEqual(self._count("registration_templates"), 0)
        with self.subTest("registered doorbell 계산 실패 → 발송 + 실패 행"):
            self.reg.clear()
            self.db.session.commit()
            self._register3()
            with mock.patch(
                "app.registration_observe.dtw_cosine_distance", side_effect=RuntimeError("boom")
            ), self.assertLogs(self.app.logger, "ERROR"):
                resp, send = self._send(_tone(440), confidence=0.9)
            self._assert_sent(resp, send)
            self.assertEqual(len(self._failures()), 1)

    # ── /stats ──
    def test_stats_counts_new_skip_reasons(self):
        def stats():
            r = self.client.get("/api/v1/stats?period=today", headers=self._auth())
            self.assertEqual(r.status_code, 200)
            return r.get_json()["skip_reasons"]

        before = stats()
        self.assertEqual(
            sorted(before),
            sorted([
                "not_target", "low_confidence", "tof_rejected", "kakao_api_error",
                "token_expired", "registration_collecting", "registration_mismatch",
            ]),
        )
        self._collecting(target=1)
        self._send(_tone(440), confidence=0.9)  # 억제 + 템플릿 1 → 등록됨
        with self._distances([0.9]):
            self._send(_tone(440), confidence=0.9)  # 불일치 차단
        after = stats()
        self.assertEqual(after["registration_collecting"], before["registration_collecting"] + 1)
        self.assertEqual(after["registration_mismatch"], before["registration_mismatch"] + 1)


if __name__ == "__main__":
    unittest.main()
