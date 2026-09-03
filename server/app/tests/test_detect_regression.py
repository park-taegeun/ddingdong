"""/detect 게이트 회귀 (stdlib unittest — 서버 추가 의존성 없이 실행).

실행(server/ 에서):  python3 -m unittest app.tests.test_detect_regression

★ 이 파일은 프로즌 대상이 아니다. 후속 PR 이 케이스를 추가·수정해도 된다
  (프로즌 = server/inference/*, model_serving.py, image_store.py, captures.py, run.py).

경위: decisions.md 6.2 의 "curl 10종/15종/25종 통과"는 과거 실행의 서술 기록이지
repo 에 실행 가능한 자산으로 남아 있지 않았다(2026-09-03 확인). 그 계보를 Flask
test_client 로 재구성해 repo 자산으로 고정한 것이 이 파일이다 — 다음 세션이 게이트
순서·임계값 무변경을 손으로 다시 증명하지 않아도 되게 한다.

토큰: DEVICE_TOKEN/DASHBOARD_TOKEN 은 setUpClass 의 _TestConfig 가 주입하는 더미
문자열이다(이 파일 상단 상수 2개가 전부). 카카오 토큰·시크릿 실값은 픽스처에 일절
등장하지 않으며, _TestConfig 가 카카오 4개 항목을 빈 문자열로 덮어 개발자 로컬
server/.env 의 실값이 테스트 경로로 새어드는 것까지 막는다.
"""

from __future__ import annotations

import io
import math
import os
import struct
import tempfile
import unittest

# 더미 인증 토큰(실값 아님). create_app 이전에 넣어야 Config 가 읽는다.
_DEVICE_TOKEN = "test-device-token"
_DASHBOARD_TOKEN = "test-dashboard-token"


def _pcm16_sine(num_samples: int, freq_hz: int = 440, rate: int = 16000) -> bytes:
    """합성 int16 PCM 사인톤 (little-endian). inference.tests 의 _pcm16_bytes 관례 동형."""
    return b"".join(
        struct.pack("<h", int(10000 * math.sin(2 * math.pi * freq_hz * i / rate)))
        for i in range(num_samples)
    )


class DetectRegressionTest(unittest.TestCase):
    """게이트 순서(멱등 → rate limit → 디코드 → 추론)와 응답 계약 회귀."""

    @classmethod
    def setUpClass(cls) -> None:
        # 실 ddingdong.db 를 건드리지 않도록 임시 파일 DB 로 격리
        cls._db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls._db_file.close()

        from .. import create_app
        from ..config import Config

        # env 를 건드리지 않고 config 클래스로 주입한다. Config 는 클래스 본문에서
        # os.environ 을 읽으므로(=import 시점) 테스트가 나중에 env 를 바꿔도 늦는다.
        # 카카오 항목은 여기서 명시적으로 비운다 — 개발자 로컬 server/.env 에 실 토큰이
        # 있어도 테스트 경로로 새어들지 않게 하기 위함이다.
        class _TestConfig(Config):
            DEVICE_TOKEN = _DEVICE_TOKEN
            DASHBOARD_TOKEN = _DASHBOARD_TOKEN
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{cls._db_file.name}"
            MODEL_PATH = ""  # 실추론 게이트 off = mock 경로 고정
            KAKAO_REST_API_KEY = ""
            KAKAO_CLIENT_SECRET = ""
            KAKAO_ACCESS_TOKEN = ""
            KAKAO_REFRESH_TOKEN = ""

        cls.app = create_app(_TestConfig)
        cls.client = cls.app.test_client()
        cls.pcm = _pcm16_sine(32000)  # 2초 @16kHz = 64,000 bytes (6.2 transport A안)

    @classmethod
    def tearDownClass(cls) -> None:
        os.unlink(cls._db_file.name)

    # ── 헬퍼 ─────────────────────────────────────────────────────────────
    def _detect(self, client_request_id, device_id, audio=None):
        return self.client.post(
            "/api/v1/detect",
            headers={"Authorization": f"Bearer {_DEVICE_TOKEN}"},
            data={
                "client_request_id": client_request_id,
                "device_id": device_id,
                "audio": (io.BytesIO(self.pcm if audio is None else audio), "a.pcm"),
            },
            content_type="multipart/form-data",
        )

    # ── 인증/입력 검증 ───────────────────────────────────────────────────
    def test_auth_missing_returns_401(self) -> None:
        r = self.client.post("/api/v1/detect", data={}, content_type="multipart/form-data")
        self.assertEqual(r.status_code, 401)

    def test_required_fields_missing_returns_400(self) -> None:
        r = self.client.post(
            "/api/v1/detect",
            headers={"Authorization": f"Bearer {_DEVICE_TOKEN}"},
            data={},
            content_type="multipart/form-data",
        )
        self.assertEqual(r.status_code, 400)

    def test_audio_part_missing_returns_400(self) -> None:
        r = self.client.post(
            "/api/v1/detect",
            headers={"Authorization": f"Bearer {_DEVICE_TOKEN}"},
            data={"client_request_id": "no-audio", "device_id": "dev-noaudio"},
            content_type="multipart/form-data",
        )
        self.assertEqual(r.status_code, 400)

    # ── 게이트 순서 ──────────────────────────────────────────────────────
    def test_detect_then_idempotent_replay(self) -> None:
        first = self._detect("regr-idem", "dev-idem")
        self.assertEqual(first.status_code, 201)

        replay = self._detect("regr-idem", "dev-idem")
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.headers.get("Idempotent-Replay"), "true")
        # 멱등 응답은 최초 응답 본문 그대로여야 한다
        self.assertEqual(replay.get_json(), first.get_json())

    def test_idempotency_precedes_rate_limit(self) -> None:
        """같은 device 로 연속 요청: 새 키는 429, 기존 키는 rate limit 을 통과해 replay.

        멱등이 rate limit 보다 앞에 있다는 순서 증명(뒤바뀌면 replay 도 429 가 된다).
        """
        dev = "dev-order"
        first = self._detect("regr-order-1", dev)
        self.assertEqual(first.status_code, 201)

        blocked = self._detect("regr-order-2", dev)  # 새 키 + 5초 이내 → rate limit
        self.assertEqual(blocked.status_code, 429)
        self.assertIn("Retry-After", blocked.headers)

        replayed = self._detect("regr-order-1", dev)  # 기존 키 → 멱등이 먼저 잡는다
        self.assertEqual(replayed.status_code, 200)
        self.assertEqual(replayed.headers.get("Idempotent-Replay"), "true")

    def test_odd_length_audio_returns_400(self) -> None:
        r = self._detect("regr-odd", "dev-odd", audio=b"\x01")
        self.assertEqual(r.status_code, 400)

    def test_oversized_audio_returns_400(self) -> None:
        from ..constants import AUDIO_MAX_BYTES

        r = self._detect("regr-big", "dev-big", audio=b"\x00" * (AUDIO_MAX_BYTES + 2))
        self.assertEqual(r.status_code, 400)

    # ── 판정 정책 (G12 무접촉 확인 포함) ─────────────────────────────────
    def test_prediction_policy_branches(self) -> None:
        """_apply_prediction_policy 3분기. fire_alarm 이 임계값 검사보다 앞이라는
        현행 순서(G12)를 '바꾸지 않았음'의 회귀 고정이다.

        ★ 이 순서는 decisions.md 카테고리 3 에 G12 로 등재된 미결이며, 사용자 판단
          대기 중이다. 본 케이스는 "현행 동작 고정"이지 "확정 사양"이 아니다 —
          여기서 통과한다는 사실이 이 순서를 옳다고 승인하지 않는다.

        ★ G12 가 "threshold 선행"으로 결정되면 이 케이스는 실패하는 것이 정상이며,
          그때 테스트를 새 결정에 맞춰 갱신할 것. 테스트를 먼저 지우고 로직을 고치지
          말 것 — 순서가 바뀌었다는 사실을 이 실패가 드러내 주는 것이 고정의 목적이다.
        """
        from ..constants import CONFIDENCE_THRESHOLD
        from ..utils import _apply_prediction_policy

        scores = {"doorbell": 0.1, "knock": 0.1, "fire_alarm": 0.8}

        # 임계값 미만이어도 fire_alarm 이면 먼저 잡혀 발송된다.
        # 현행 동작 고정 — G12 가 threshold 선행으로 결정되면 이 단언이 뒤집힌다
        # (그때 갱신할 것. 위 docstring 참조).
        fire = _apply_prediction_policy("fire_alarm", CONFIDENCE_THRESHOLD - 0.1, scores)
        self.assertTrue(fire["primary_sent"])
        self.assertIsNone(fire["skip_reason"])
        self.assertFalse(fire["tof"]["applied"])

        # 엄격 비교(<): 임계값 미만만 skip
        low = _apply_prediction_policy("doorbell", CONFIDENCE_THRESHOLD - 0.01, scores)
        self.assertFalse(low["primary_sent"])
        self.assertEqual(low["skip_reason"], "low_confidence")

        # 임계값 '정확히 일치'는 통과여야 한다(<= 로 바뀌면 여기서 깨진다)
        at = _apply_prediction_policy("doorbell", CONFIDENCE_THRESHOLD, scores)
        self.assertTrue(at["primary_sent"])
        self.assertEqual(at["enrich_status"], "pending")

    # ── G14: primary_sent_at 분리 ────────────────────────────────────────
    def test_primary_sent_at_is_not_detected_at(self) -> None:
        """1차 알림 시각이 detected_at 과 같은 변수를 공유하지 않는다.

        공유하던 시절엔 두 값이 항상 동일해 timing_metrics 1차 지연이 구조적으로
        0ms 만 나왔다. 발송 배선 전이라 차이는 서브밀리초지만 '동일하지 않음'은
        구조 회귀로 고정할 수 있다.
        """
        from ..extensions import db
        from ..models import Notification

        made = 0
        with self.app.app_context():
            for i in range(10):
                if self._detect(f"regr-g14-{i}", f"dev-g14-{i}").status_code == 201:
                    made += 1
            self.assertGreater(made, 0)

            rows = (
                db.session.query(Notification)
                .filter(Notification.primary_sent_at.isnot(None))
                .all()
            )
            self.assertGreater(len(rows), 0)
            for row in rows:
                self.assertGreaterEqual(row.primary_sent_at, row.detected_at)
                self.assertNotEqual(row.primary_sent_at, row.detected_at)

    # ── 카카오 토큰 계층 ─────────────────────────────────────────────────
    def test_kakao_tokens_table_created(self) -> None:
        from sqlalchemy import inspect

        from ..extensions import db

        with self.app.app_context():
            names = set(inspect(db.engine).get_table_names())
        self.assertIn("kakao_tokens", names)

    def test_get_access_token_rejects_unsafe_commit_point(self) -> None:
        """세션에 미커밋 Notification 이 있으면 토큰 갱신이 그것을 함께 커밋하므로,
        호출 자체가 거부돼야 한다(커밋 부작용 구조 가드)."""
        from .. import kakao
        from ..extensions import db
        from ..models import Notification
        from ..utils import utc_now

        with self.app.app_context():
            db.session.add(
                Notification(
                    client_request_id="guard-probe",
                    request_id="req_guardprobe",
                    device_id="dev-guard",
                    detected_at=utc_now(),
                    predicted_class="doorbell",
                    confidence=0.9,
                    all_scores={"doorbell": 0.9, "knock": 0.05, "fire_alarm": 0.05},
                    tof_applied=True,
                    tof_passed=True,
                    tof_reason="probe",
                    primary_sent=False,
                    primary_sent_at=None,
                    enrich_status="skipped",
                    secondary_sent=False,
                    secondary_sent_at=None,
                    skip_reason=None,
                    image_url=None,
                    image_thumbnail_url=None,
                    audio_url=None,
                    stt=None,
                )
            )
            with self.assertRaises(RuntimeError) as ctx:
                kakao.get_access_token()
            # 발송 실패로 둔갑하지 않아야 한다
            self.assertNotIsInstance(ctx.exception, kakao.KakaoTokenError)
            db.session.rollback()

    def test_bootstrap_without_refresh_token_fails_fast(self) -> None:
        """refresh 토큰 env 부재 = 조용한 폴백 없이 KakaoTokenError."""
        from .. import kakao

        with self.app.app_context():
            self.app.config["KAKAO_REFRESH_TOKEN"] = ""
            with self.assertRaises(kakao.KakaoTokenError):
                kakao.get_access_token()

    # ── stats ────────────────────────────────────────────────────────────
    def test_stats_contract(self) -> None:
        r = self.client.get(
            "/api/v1/stats?period=today",
            headers={"Authorization": f"Bearer {_DASHBOARD_TOKEN}"},
        )
        self.assertEqual(r.status_code, 200)
        timing = r.get_json()["timing_metrics"]
        for key in (
            "primary_notification_avg_ms",
            "primary_notification_max_ms",
            "primary_under_5s_rate",
            "secondary_notification_avg_ms",
            "secondary_notification_max_ms",
            "secondary_under_15s_rate",
        ):
            self.assertIn(key, timing)

    def test_stats_requires_dashboard_token(self) -> None:
        """Device 토큰으로는 대시보드 API 에 접근할 수 없다(토큰 분리 회귀)."""
        r = self.client.get(
            "/api/v1/stats?period=today",
            headers={"Authorization": f"Bearer {_DEVICE_TOKEN}"},
        )
        self.assertEqual(r.status_code, 401)


if __name__ == "__main__":
    unittest.main()
