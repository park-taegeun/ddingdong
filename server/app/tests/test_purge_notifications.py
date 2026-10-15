"""server/purge_notifications.py 시간대 삭제 도구 회귀 (stdlib unittest).

실행(server/ 에서):  python3 -m unittest app.tests.test_purge_notifications

--confirm-delete 가 없으면 쓰기 0 · 종료 코드 2, 있으면 구간 [from, to)(KST) 안 notifications 행만 삭제.
행 수 · 내용은 출력이 아니라 sqlite3 로 임시 DB 파일을 다시 열어 비교한다(test_seed_guard 선례).

외부 연결 가드: test_seed_guard 선례대로 test_detect_regression 의 가드 함수와
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

import purge_notifications

from .test_detect_regression import (
    _DASHBOARD_TOKEN,
    _DEVICE_TOKEN,
    _NoNetworkTestCase,
    _install_network_guard,
    _uninstall_network_guard,
)

# 구간 = KST 2026-10-20 10:00 ~ 17:00 = UTC 01:00 ~ 08:00 (naive UTC 로 심는다).
_ARGS = ["--from", "2026-10-20 10:00", "--to", "2026-10-20 17:00"]
_ROWS = {  # client_request_id 접미사 → (detected_at naive UTC, 클래스, 구간 안?)
    "before": (datetime(2026, 10, 20, 0, 59), "knock", False),  # KST 09:59
    "at_from": (datetime(2026, 10, 20, 1, 0), "doorbell", True),  # KST 10:00 정각 → 삭제
    "inside": (datetime(2026, 10, 20, 4, 0), "knock", True),  # KST 13:00
    "at_to": (datetime(2026, 10, 20, 8, 0), "doorbell", False),  # KST 17:00 정각 → 유지
    "after": (datetime(2026, 10, 20, 8, 1), "knock", False),  # KST 17:01
    # 입력을 UTC 로 잘못 읽으면 구간 UTC 10:00 ~ 17:00 에 들어가 지워지는 행(KST 21:00).
    "utc_trap": (datetime(2026, 10, 20, 12, 0), "fire_alarm", False),
}
_SECRET_TRANSCRIPT = "방문자비밀자막"
_SECRET_IMAGE_ID = "opaquephotoid"
_CRID_PREFIX = "visitorcrid_"
_OTHER_TABLES = (
    "idempotency_keys",
    "kakao_tokens",
    "registration_state",
    "registration_templates",
    "registration_matches",
    "registration_failures",
    "device_heartbeats",
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


class PurgeNotificationsTest(_NoNetworkTestCase):
    """임시 파일 DB 1개. 테스트마다 알림 6건 + 다른 7테이블 1행씩으로 되돌린다."""

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
        from ..models import (
            DeviceHeartbeat,
            IdempotencyKey,
            KakaoToken,
            Notification,
            RegistrationFailure,
            RegistrationMatch,
            RegistrationState,
            RegistrationTemplate,
        )

        t0 = datetime(2026, 10, 20, 2, 0)
        with self.app.app_context():
            for model in (Notification, IdempotencyKey, KakaoToken, RegistrationState,
                          RegistrationTemplate, RegistrationMatch, RegistrationFailure,
                          DeviceHeartbeat):
                db.session.query(model).delete()
            db.session.add_all(
                Notification(
                    client_request_id=_CRID_PREFIX + key,
                    request_id=f"req_{key}",
                    device_id="test",
                    detected_at=at,
                    predicted_class=cls,
                    confidence=0.9,
                    all_scores={cls: 0.9},
                    tof_applied=False,
                    tof_reason="test",
                    primary_sent=True,
                    enrich_status="completed",
                    secondary_sent=True,
                    image_url=f"/captures/{_SECRET_IMAGE_ID}_{key}.jpg",
                    stt={"transcript": f"{_SECRET_TRANSCRIPT}_{key}", "confidence": 0.9},
                )
                for key, (at, cls, _) in _ROWS.items()
            )
            db.session.add_all([
                IdempotencyKey(client_request_id=_CRID_PREFIX + "at_from", request_id="req_at_from",
                               response_json={"stt": None}, created_at=t0),
                KakaoToken(id=KakaoToken.SINGLETON_ID, access_token="acc", refresh_token="ref",
                           access_expires_at=t0, refresh_expires_at=t0, updated_at=t0),
                RegistrationState(id=RegistrationState.SINGLETON_ID, registration_id="reg1",
                                  target_count=3, started_at=t0, expires_at=t0, completed_at=t0),
                RegistrationTemplate(registration_id="reg1", client_request_id=_CRID_PREFIX + "inside",
                                     pcm=b"\x01\x00\x02\x00", created_at=t0),
                RegistrationMatch(client_request_id=_CRID_PREFIX + "inside", registration_id="reg1",
                                  predicted_class="doorbell", template_count=1, distances=[0.5],
                                  min_distance=0.5, mean_distance=0.5, compare_ms=1.0, created_at=t0),
                RegistrationFailure(client_request_id=_CRID_PREFIX + "inside", registration_id="reg1",
                                    predicted_class="doorbell", judged=True, error="E", created_at=t0),
                DeviceHeartbeat(device_id="test", last_seen_at=t0, rssi=-50, uptime_s=1, fw="x",
                                enrich_sent=0),
            ])
            db.session.commit()

    def _snapshot(self, tables) -> dict:
        # 세션 캐시를 거치지 않도록 파일을 새로 연다. 행 내용 전체를 비교한다.
        with contextlib.closing(sqlite3.connect(self._db_path)) as conn:
            return {t: conn.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in tables}

    def _remaining_keys(self) -> set:
        with contextlib.closing(sqlite3.connect(self._db_path)) as conn:
            rows = conn.execute("SELECT client_request_id FROM notifications").fetchall()
        return {r[0].removeprefix(_CRID_PREFIX) for r in rows}

    def _main(self, argv) -> tuple[int, str, mock.MagicMock]:
        out = io.StringIO()
        with mock.patch.object(purge_notifications, "create_app", return_value=self.app) as ca, \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            try:
                code = purge_notifications.main(argv)
            except SystemExit as e:  # argparse 오류
                code = e.code
        return code, out.getvalue(), ca

    def test_without_confirm_writes_nothing(self):
        before = self._snapshot(("notifications",) + _OTHER_TABLES)
        code, out, _ = self._main(_ARGS)
        self.assertEqual(code, 2)
        self.assertEqual(self._snapshot(("notifications",) + _OTHER_TABLES), before)
        self.assertEqual(len(before["notifications"]), len(_ROWS))
        self.assertIn("지울 알림 2건", out)
        self.assertIn("구간 밖 4건", out)
        self.assertIn("doorbell 1건 · knock 1건", out)
        # 구간 표기에도 from 시각이 찍히므로 라벨까지 붙여 단언한다.
        self.assertIn("가장 이른 2026-10-20T10:00:00.000+09:00", out)  # from 정각 행(KST)
        self.assertIn("가장 늦은 2026-10-20T13:00:00.000+09:00", out)  # inside 행(KST)
        self.assertIn(os.path.basename(self._db_path), out)
        self.assertNotIn(os.path.dirname(self._db_path), out)  # 경로 전체가 아니라 파일 이름만
        self.assertIn("--confirm-delete", out)

    def test_with_confirm_deletes_only_half_open_kst_range(self):
        others = self._snapshot(_OTHER_TABLES)
        code, out, _ = self._main(_ARGS + ["--confirm-delete"])
        self.assertEqual(code, 0)
        # from 정각 = 삭제, to 정각 = 유지, UTC 로 잘못 읽으면 지워질 행 = 유지
        self.assertEqual(self._remaining_keys(), {k for k, (_, _, inside) in _ROWS.items() if not inside})
        self.assertEqual(self._snapshot(_OTHER_TABLES), others)
        self.assertIn("알림 2건 삭제 · 구간 밖 4건 → 4건.", out)

    def test_output_has_no_personal_data(self):
        _, dry, _ = self._main(_ARGS)
        _, real, _ = self._main(_ARGS + ["--confirm-delete"])
        for secret in (_SECRET_TRANSCRIPT, _SECRET_IMAGE_ID, _CRID_PREFIX):
            self.assertNotIn(secret, dry + real)

    def test_bad_args_write_nothing(self):
        before = self._snapshot(("notifications",) + _OTHER_TABLES)
        for argv in (
            ["--from", "2026-10-20 17:00", "--to", "2026-10-20 17:00", "--confirm-delete"],  # from = to
            ["--from", "2026-10-20 18:00", "--to", "2026-10-20 17:00", "--confirm-delete"],  # from > to
            ["--from", "2026-10-20T10:00", "--to", "2026-10-20 17:00", "--confirm-delete"],  # 형식 오류
            ["--to", "2026-10-20 17:00", "--confirm-delete"],  # 인자 누락
        ):
            with self.subTest(argv=argv):
                code, _, create_app = self._main(argv)
                self.assertEqual(code, 2)
                create_app.assert_not_called()  # DB 를 열기 전에 끝난다
                self.assertEqual(self._snapshot(("notifications",) + _OTHER_TABLES), before)


if __name__ == "__main__":
    unittest.main()
