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

카카오 발송: ★ 이 스위트는 카카오로 실제 요청을 보내지 않는다. 발송 경로 케이스는
unittest.mock 으로 kakao.send_primary_text / kakao.get_access_token /
urllib.request.urlopen 을 스텁해 검증한다. _FAKE_ACCESS_TOKEN 은 발송 경로를 통과
시키기 위한 자리표시 문자열이며 카카오가 발급한 값이 아니다(실값 금지 원칙 유지).
"""

from __future__ import annotations

import io
import math
import os
import json
import struct
import tempfile
import unittest
import urllib.error
import urllib.parse
from datetime import datetime
from pathlib import Path
from unittest import mock

# 더미 인증 토큰(실값 아님). create_app 이전에 넣어야 Config 가 읽는다.
_DEVICE_TOKEN = "test-device-token"
_DASHBOARD_TOKEN = "test-dashboard-token"

# 발송 경로 스텁용 자리표시 문자열. 카카오 발급값 아님 — 실값은 이 파일에 없다.
_FAKE_ACCESS_TOKEN = "test-access-token-not-real"
_FAKE_REFRESH_TOKEN = "test-refresh-token-not-real"
_FAKE_RENEWED_TOKEN = "test-renewed-token-not-real"

# 갱신 경로를 열기 위한 자리표시 자격증명. _TestConfig 는 이 둘을 비워 두므로(로컬
# .env 유출 차단) 갱신을 태우는 케이스에서만 patch.dict 로 잠시 채운다. 실값 아님.
_FAKE_KAKAO_CREDS = {
    "KAKAO_REST_API_KEY": "test-rest-api-key-not-real",
    "KAKAO_CLIENT_SECRET": "test-client-secret-not-real",
}

# decisions.md 원문 위치. tests → app → server → repo 루트.
# dashboard/src/types/notification.ts NotificationItem 필드 11종 (to_dict 계약 SSoT).
_NOTIFICATION_ITEM_KEYS = (
    "client_request_id",
    "request_id",
    "detected_at",
    "predicted_class",
    "confidence",
    "all_scores",
    "tof_check",
    "notification_status",
    "media",
    "stt",
    "device_id",
)

# HTTPError 생성용 자리표시 URL(실 호출 없음 — urlopen 은 전부 스텁된다).
KAKAO_MEMO_URL_FOR_TEST = "https://kapi.example.test/memo"

_DECISIONS_MD = Path(__file__).resolve().parents[3] / "docs" / "decisions.md"
_COPY2_MARKER = "**확정 카피 ② 카카오 알림용**"


def _copy2_from_decisions() -> str | None:
    """decisions.md 의 확정 카피 ② 코드펜스를 실추출. 파일이 없으면 None.

    상수를 손으로 옮겨 적지 않았다는 것을 매 실행 대조로 증명하기 위한 것이다
    (문서가 수정되면 이 대조가 먼저 깨져 드리프트를 알려준다).
    """
    if not _DECISIONS_MD.exists():
        return None
    lines = _DECISIONS_MD.read_text(encoding="utf-8").split("\n")
    marker = next((i for i, ln in enumerate(lines) if _COPY2_MARKER in ln), None)
    if marker is None:
        return None
    opened = next(
        (i for i in range(marker + 1, len(lines)) if lines[i].strip() == "```"), None
    )
    if opened is None:
        return None
    closed = next(
        (i for i in range(opened + 1, len(lines)) if lines[i].strip() == "```"), None
    )
    if closed is None:
        return None
    return "\n".join(lines[opened + 1 : closed])


class _FakeResponse:
    """urlopen 의 컨텍스트매니저 계약만 흉내 내는 최소 스텁."""

    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._body


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
    def _detect(self, client_request_id, device_id, audio=None, tof=None):
        """tof = ToF 메타 form field dict(부재가 기본). 값은 multipart 관례대로 문자열."""
        data = {
            "client_request_id": client_request_id,
            "device_id": device_id,
            "audio": (io.BytesIO(self.pcm if audio is None else audio), "a.pcm"),
        }
        if tof:
            data.update(tof)
        return self.client.post(
            "/api/v1/detect",
            headers={"Authorization": f"Bearer {_DEVICE_TOKEN}"},
            data=data,
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

    # ── 판정 정책 (G12 확정 사양 고정) ───────────────────────────────────
    def test_prediction_policy_branches(self) -> None:
        """_apply_prediction_policy 분기. 신뢰도 비교가 fire_alarm early return 보다
        **앞**이라는 순서를 고정한다.

        ★ 이 케이스는 원래 그 반대(fire_alarm 선행)를 "현행 동작 고정"으로 걸어둔
          것이었고, decisions.md 카테고리 3 G12 미결이 걸려 "확정 사양 아님"으로
          표기돼 있었다. **2026-09-08 사용자 결정으로 확정**됐다 — 신뢰도 비교를
          앞으로 옮기고 fire_alarm 의 ToF 우회만 유지한다(근거유형 = 논증,
          입력 실측 = 33.2 confusion `doorbell → fire_alarm` 오분류 10건 최다 /
          실경로 재현 2026-09-05·2026-09-08). 케이스를 지우지 않고 갱신하는 이유 =
          이 지점이 한때 미결이었다는 이력을 남기기 위해서다.

        ★ 이제 이 케이스가 깨지면 확정 사양이 뒤집힌 것이다. 테스트를 고쳐 통과시키지
          말 것.
        """
        from ..constants import CONFIDENCE_THRESHOLD
        from ..utils import _apply_prediction_policy

        scores = {"doorbell": 0.1, "knock": 0.1, "fire_alarm": 0.8}

        # 신 사양: 임계값 미만이면 fire_alarm 도 1차 미발송이다.
        # (구 사양에서는 여기서 primary_sent=True 였다 — G12 확정으로 뒤집힌 단언.)
        fire = _apply_prediction_policy("fire_alarm", CONFIDENCE_THRESHOLD - 0.1, scores)
        self.assertFalse(fire["primary_sent"])
        self.assertEqual(fire["skip_reason"], "low_confidence")
        self.assertEqual(fire["enrich_status"], "skipped")
        # 우회 자체는 유지 — 게이트를 적용하지 않았다는 기록은 그대로 남는다.
        self.assertFalse(fire["tof"]["applied"])

        # 엄격 비교(<): 임계값 미만만 skip
        low = _apply_prediction_policy("doorbell", CONFIDENCE_THRESHOLD - 0.01, scores)
        self.assertFalse(low["primary_sent"])
        self.assertEqual(low["skip_reason"], "low_confidence")

        # 임계값 '정확히 일치'는 통과여야 한다(<= 로 바뀌면 여기서 깨진다)
        at = _apply_prediction_policy("doorbell", CONFIDENCE_THRESHOLD, scores)
        self.assertTrue(at["primary_sent"])
        self.assertEqual(at["enrich_status"], "pending")

    # ── G12 확정 사양 신규 케이스 (2026-09-08) ───────────────────────────
    #
    # 이 절이 고정하는 불변식 3개:
    #   J1 신뢰도 게이트는 클래스 무관이다 — fire_alarm 도 0.70 미만이면 미발송.
    #   J2 경계는 strict `<` 그대로다 — 정확히 0.70 은 fire_alarm 도 발송.
    #   J3 ToF 우회는 살아 있다 — 임계값을 넘긴 fire_alarm 은 presence=false 여도 발송.
    #
    # ★ J1 과 J3 은 함께 걸어야 의미가 있다. J1 만 있으면 "threshold 와 함께 ToF
    #   우회까지 지운" 과잉 수정이 통과하고, J3 만 있으면 순서를 되돌린 변형이 통과한다.

    _TOF_META_ABSENT = None
    _TOF_META_REJECT = {
        "tof_presence": "false",
        "tof_near_count": "1",
        "tof_center_mm": "2953",
        "tof_motion_ndet": "0",
    }

    @staticmethod
    def _policy_with_tof(predicted_class, confidence, tof_form=None):
        """_apply_prediction_policy 직접 호출 + ToF form 을 실제 파서에 통과시킨다."""
        from ..tof_meta import parse_tof_meta
        from ..utils import _apply_prediction_policy

        scores = {"doorbell": 0.34, "knock": 0.33, "fire_alarm": 0.33}
        meta = None if tof_form is None else parse_tof_meta(tof_form)
        return _apply_prediction_policy(predicted_class, confidence, scores, meta)

    def test_fire_alarm_below_threshold_is_not_sent(self) -> None:
        """J1. fire_alarm 0.69 → 1차 미발송 + skip_reason=low_confidence.

        0.69 = 임계값 0.70 바로 아래. 구 사양에서는 발송됐다.
        """
        r = self._policy_with_tof("fire_alarm", 0.69)
        self.assertFalse(r["primary_sent"])
        self.assertEqual(r["skip_reason"], "low_confidence")
        self.assertEqual(r["enrich_status"], "skipped")

    def test_fire_alarm_at_threshold_is_sent(self) -> None:
        """J2. fire_alarm 0.70 → 발송. strict `<` 경계 보존(실증 3회: 9/03·9/05·9/08).

        ★ 비교를 `<=` 로 바꾸는 변형은 0.69/0.71 만 검사해서는 잡히지 않는다.
          경계값 자체를 여기서 고정한다.
        """
        from ..constants import CONFIDENCE_THRESHOLD

        self.assertEqual(CONFIDENCE_THRESHOLD, 0.7)
        r = self._policy_with_tof("fire_alarm", CONFIDENCE_THRESHOLD)
        self.assertTrue(r["primary_sent"])
        self.assertIsNone(r["skip_reason"])
        self.assertEqual(r["enrich_status"], "skipped")  # 2차 미발송(카테고리 7)

    def test_fire_alarm_above_threshold_still_bypasses_tof(self) -> None:
        """J3. fire_alarm 0.71 + presence=false → 그래도 발송(ToF 우회 유지).

        ★ 이 케이스가 깨지면 threshold 를 앞으로 옮기면서 ToF 우회까지 지운 것이다 —
          카테고리 3 "화재경보: ToF 우회" 위배. 7.1 대피 수칙 발송이 사람 검증에
          묶이면 안 된다.
        """
        r = self._policy_with_tof("fire_alarm", 0.71, self._TOF_META_REJECT)
        self.assertTrue(r["primary_sent"])
        self.assertIsNone(r["skip_reason"])
        self.assertFalse(r["tof"]["applied"])
        self.assertIsNone(r["tof"]["passed"])
        self.assertTrue(r["tof"]["reason"].startswith("fire_alarm_bypass"))

    def test_low_confidence_fire_alarm_with_tof_reject_is_not_sent(self) -> None:
        """J1. fire_alarm 0.45 + presence=false → 미발송.

        2026-09-08 실경로에서 `fire_alarm 0.45` 가 primary_sent=True 로 관찰된 바로
        그 조합이다. 신 사양에서는 발송되지 않는다.
        우회 기록(fire_alarm_bypass)은 남되 발송은 신뢰도에서 막힌다 —
        skip_reason 은 먼저 걸린 low_confidence 다(tof_rejected 아님).
        """
        r = self._policy_with_tof("fire_alarm", 0.45, self._TOF_META_REJECT)
        self.assertFalse(r["primary_sent"])
        self.assertEqual(r["skip_reason"], "low_confidence")
        self.assertFalse(r["tof"]["applied"])
        self.assertTrue(r["tof"]["reason"].startswith("fire_alarm_bypass"))

    def test_doorbell_and_knock_low_confidence_unchanged(self) -> None:
        """초인종·노크 저신뢰는 무회귀 — 신 사양이 이 두 클래스를 건드리지 않는다."""
        for cls in ("doorbell", "knock"):
            with self.subTest(cls=cls):
                r = self._policy_with_tof(cls, 0.69)
                self.assertFalse(r["primary_sent"])
                self.assertEqual(r["skip_reason"], "low_confidence")
                at = self._policy_with_tof(cls, 0.70)
                self.assertTrue(at["primary_sent"])
                self.assertEqual(at["enrich_status"], "pending")

    def test_policy_decision_table_is_total(self) -> None:
        """전 분기 열거 — 클래스 3 × 신뢰도 4 × ToF 4상태 = 48조합.

        고정하는 것 둘:
          ① 미정의 동작 0 — 48조합 전부가 닫힌 값 도메인 안에서 끝난다.
          ② 48조합이 고유 결정 4행으로 붕괴한다. 행이 늘면 분기가 새로 생긴 것이고,
             줄면 분기 하나가 죽은 것이다 — 어느 쪽이든 여기서 드러나야 한다.
        """
        classes = ("doorbell", "knock", "fire_alarm")
        # 경계 0.70 을 반드시 포함한다(<= 변형 검출용).
        confidences = (0.45, 0.69, 0.70, 0.95)
        tof_forms = {
            "absent": None,
            "pass": {
                "tof_presence": "true",
                "tof_near_count": "13",
                "tof_center_mm": "1015",
                "tof_motion_ndet": "1",
            },
            "reject": self._TOF_META_REJECT,
            # 이탈: presence 를 읽을 수 없는 값 → tof_meta state="invalid"
            "invalid": {
                "tof_presence": "maybe",
                "tof_near_count": "13",
                "tof_center_mm": "1015",
                "tof_motion_ndet": "1",
            },
        }

        rows = {}
        total = 0
        for cls in classes:
            for conf in confidences:
                for tof_name, form in tof_forms.items():
                    total += 1
                    r = self._policy_with_tof(cls, conf, form)
                    # ① 닫힌 도메인 — 미정의 값이 새어나오지 않는다
                    self.assertIn(r["skip_reason"], (None, "low_confidence", "tof_rejected"))
                    self.assertIn(r["enrich_status"], ("pending", "skipped"))
                    self.assertIsInstance(r["primary_sent"], bool)
                    self.assertIn(r["tof"]["passed"], (None, True, False))
                    # 미발송이면 enrich 는 반드시 skipped (상태전이 일관)
                    if not r["primary_sent"]:
                        self.assertEqual(r["enrich_status"], "skipped")
                    # 발송인데 skip_reason 이 붙는 조합은 없다
                    if r["primary_sent"]:
                        self.assertIsNone(r["skip_reason"])
                    key = (r["primary_sent"], r["enrich_status"], r["skip_reason"])
                    rows.setdefault(key, []).append((cls, conf, tof_name))

        self.assertEqual(total, 48)
        # ② 고유 결정 4행
        self.assertEqual(
            sorted(rows),
            sorted(
                [
                    (False, "skipped", "low_confidence"),   # 저신뢰 전 클래스 (24)
                    (False, "skipped", "tof_rejected"),     # 고신뢰 초인종·노크 + 거부 (4)
                    (True, "skipped", None),                # 고신뢰 fire_alarm (8)
                    (True, "pending", None),                # 고신뢰 초인종·노크 통과 (12)
                ]
            ),
        )
        self.assertEqual(len(rows[(False, "skipped", "low_confidence")]), 24)
        self.assertEqual(len(rows[(True, "skipped", None)]), 8)
        self.assertEqual(len(rows[(True, "pending", None)]), 12)
        self.assertEqual(len(rows[(False, "skipped", "tof_rejected")]), 4)
        # 저신뢰 24건에 fire_alarm 8건이 전부 포함된다 = 신뢰도 게이트가 클래스 무관
        low_rows = rows[(False, "skipped", "low_confidence")]
        self.assertEqual(sum(1 for c, _, _ in low_rows if c == "fire_alarm"), 8)

    # ── G14: primary_sent_at 분리 ────────────────────────────────────────
    def test_primary_sent_at_is_not_detected_at(self) -> None:
        """1차 알림 시각이 detected_at 과 같은 변수를 공유하지 않는다.

        공유하던 시절엔 두 값이 항상 동일해 timing_metrics 1차 지연이 구조적으로
        0ms 만 나왔다.

        발송을 성공으로 스텁한다: 테스트 config 는 카카오 항목이 비어 있어 실제로는
        전건이 미발송(token_expired)으로 떨어지고 primary_sent_at 이 전부 None 이 된다.
        여기서 고정하려는 것은 발송 성공 여부가 아니라 '두 시각이 같은 변수를 쓰지
        않는다'는 구조라서, 발송을 성공시킨 뒤 두 값을 비교한다.
        """
        from ..extensions import db
        from ..models import Notification

        made = 0
        with self.app.app_context(), mock.patch(
            "app.kakao.send_primary_text", return_value=None
        ):
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

    # ── 1차 알림 발송 배선 (카테고리 7, 실발송 없음 — 전부 스텁) ─────────
    #
    # 이 절의 모든 케이스는 카카오로 요청을 보내지 않는다. 스텁 지점은 두 층뿐이다:
    #   (a) app.kakao.send_primary_text  = routes 배선을 볼 때
    #   (b) app.kakao.get_access_token + urlopen = kakao 내부 실패 분기를 볼 때

    @staticmethod
    def _policy(predicted_class, confidence):
        """정책 dict 를 손으로 짓지 않고 실제 판정 함수로 만든다(드리프트 방지)."""
        from ..utils import _apply_prediction_policy

        scores = {"doorbell": 0.34, "knock": 0.33, "fire_alarm": 0.33}
        return _apply_prediction_policy(predicted_class, confidence, scores)

    def _row(self, client_request_id):
        from ..extensions import db
        from ..models import Notification
        from sqlalchemy import select

        return db.session.execute(
            select(Notification).where(
                Notification.client_request_id == client_request_id
            )
        ).scalar_one()

    def test_send_not_called_when_policy_skips(self) -> None:
        """정책이 미발송으로 판정한 건은 발송 호출 자체를 하지 않는다.

        저신뢰 건까지 카카오 왕복을 태우면 5초 예산과 skip_reason 집계가 함께 오염된다.
        """
        from ..constants import CONFIDENCE_THRESHOLD

        low = self._policy("doorbell", CONFIDENCE_THRESHOLD - 0.2)
        self.assertFalse(low["primary_sent"])  # 전제 확인

        with self.app.app_context(), mock.patch(
            "app.routes.mock_prediction", return_value=low
        ), mock.patch("app.kakao.send_primary_text") as send:
            r = self._detect("regr-send-skip", "dev-send-skip")
            self.assertEqual(r.status_code, 201)
            send.assert_not_called()

            row = self._row("regr-send-skip")
            self.assertFalse(row.primary_sent)
            self.assertIsNone(row.primary_sent_at)
            self.assertEqual(row.skip_reason, "low_confidence")

    def test_send_success_records_primary_sent(self) -> None:
        """발송 성공 = primary_sent True + primary_sent_at 기록 + skip_reason 없음."""
        sent = self._policy("doorbell", 0.95)
        self.assertTrue(sent["primary_sent"])

        with self.app.app_context(), mock.patch(
            "app.routes.mock_prediction", return_value=sent
        ), mock.patch("app.kakao.send_primary_text", return_value=None) as send:
            r = self._detect("regr-send-ok", "dev-send-ok")
            self.assertEqual(r.status_code, 201)
            send.assert_called_once_with("doorbell")

            row = self._row("regr-send-ok")
            self.assertTrue(row.primary_sent)
            self.assertIsNotNone(row.primary_sent_at)
            self.assertIsNone(row.skip_reason)

    def test_send_failure_is_recorded_and_not_5xx(self) -> None:
        """발송 실패는 요청 실패가 아니다 — 201 + primary_sent False + skip_reason."""
        sent = self._policy("doorbell", 0.95)

        with self.app.app_context(), mock.patch(
            "app.routes.mock_prediction", return_value=sent
        ), mock.patch("app.kakao.send_primary_text", return_value="kakao_api_error"):
            r = self._detect("regr-send-fail", "dev-send-fail")
            self.assertEqual(r.status_code, 201)  # 5xx 아님

            # 응답 본문(= 멱등 replay 로 재생될 스냅샷)에도 실제 발송 결과가 담긴다
            status = r.get_json()["notification_status"]
            self.assertFalse(status["primary_sent"])
            self.assertIsNone(status["primary_sent_at"])
            self.assertEqual(status["skip_reason"], "kakao_api_error")

            row = self._row("regr-send-fail")
            self.assertFalse(row.primary_sent)
            self.assertIsNone(row.primary_sent_at)
            self.assertEqual(row.skip_reason, "kakao_api_error")

    def test_token_unavailable_records_token_expired(self) -> None:
        """토큰 계층 실패는 kakao_api_error 가 아니라 token_expired 로 집계된다.

        스텁 없이 실제 kakao 계층을 탄다 — 테스트 config 의 카카오 항목이 비어 있어
        부트스트랩이 fail-fast 하고, 네트워크 호출은 일어나지 않는다.
        """
        sent = self._policy("doorbell", 0.95)

        with self.app.app_context(), mock.patch(
            "app.routes.mock_prediction", return_value=sent
        ):
            r = self._detect("regr-send-notoken", "dev-send-notoken")
            self.assertEqual(r.status_code, 201)

            row = self._row("regr-send-notoken")
            self.assertFalse(row.primary_sent)
            self.assertEqual(row.skip_reason, "token_expired")

    def test_send_timeout_leaves_primary_sent_determined(self) -> None:
        """타임아웃 경로에서도 primary_sent 상태가 확정된다.

        [4] 자체검증 ③이 "Step 3 소관"으로 남긴 미해결 항목의 증명이다. urlopen 이
        TimeoutError 를 던지는 상황에서 요청이 5xx 로 새거나 primary_sent 가 판정
        직후 값(True)으로 남지 않고, False + kakao_api_error 로 확정되어야 한다.
        """
        sent = self._policy("doorbell", 0.95)

        with self.app.app_context(), mock.patch(
            "app.routes.mock_prediction", return_value=sent
        ), mock.patch("app.kakao.get_access_token", return_value=_FAKE_ACCESS_TOKEN), mock.patch(
            "app.kakao.urllib.request.urlopen", side_effect=TimeoutError("timed out")
        ) as urlopen:
            r = self._detect("regr-send-timeout", "dev-send-timeout")
            self.assertEqual(r.status_code, 201)
            # 재시도 없음 — 왕복은 정확히 1회만 시도된다
            self.assertEqual(urlopen.call_count, 1)
            # 타임아웃이 실제로 걸려 있다(무기한 대기 금지). 값 근거는 constants 주석.
            from ..constants import KAKAO_HTTP_TIMEOUT_SECONDS

            self.assertEqual(
                urlopen.call_args.kwargs["timeout"], KAKAO_HTTP_TIMEOUT_SECONDS
            )

            row = self._row("regr-send-timeout")
            self.assertFalse(row.primary_sent)
            self.assertIsNone(row.primary_sent_at)
            self.assertEqual(row.skip_reason, "kakao_api_error")

    def test_send_precedes_notification_add(self) -> None:
        """발송이 Notification 생성보다 먼저 일어난다 — 두 방식으로 증명한다.

        (1) 순서 직접 관찰: Notification 생성자를 감싸 호출 순서를 기록한다.
        (2) 규약 실행 증명: 발송 시점에 _assert_commit_is_safe() 를 직접 돌려,
            토큰 갱신 커밋에 딸려갈 남의 미커밋 변경이 없음을 확인한다.

        negative control(2026-09-03): 발송 호출을 db.session.add(notif) +
        db.session.flush() 뒤로 옮기면 이 케이스가 500 으로 깨지는 것을 확인했다.
        """
        from .. import kakao
        from ..models import Notification

        sent = self._policy("doorbell", 0.95)
        seen = []

        def _guarded(predicted_class):
            kakao._assert_commit_is_safe()  # 위반이면 RuntimeError
            seen.append("send")
            return None

        def _recording(*args, **kwargs):
            seen.append("notification")
            return Notification(*args, **kwargs)

        with self.app.app_context(), mock.patch(
            "app.routes.mock_prediction", return_value=sent
        ), mock.patch("app.kakao.send_primary_text", side_effect=_guarded), mock.patch(
            "app.routes.Notification", side_effect=_recording
        ):
            r = self._detect("regr-send-order", "dev-send-order")
            self.assertEqual(r.status_code, 201)

        self.assertEqual(seen, ["send", "notification"])

    def test_commit_guard_sees_flushed_but_uncommitted_rows(self) -> None:
        """flush 를 거쳐 session.new 에서 빠진 미커밋 행도 가드가 잡는다.

        flush 이전(session.new/dirty)만 보던 초판 가드는 이 상황을 놓쳤다
        (2026-09-03 negative control 로 발견). SQLAlchemy 상향으로 내부 컬렉션이
        사라지면 가드가 조용히 약해지므로, 그 퇴화를 여기서 감지한다.

        ★ 객체 참조를 지역변수로 들고 있는 형태로 재현한다 — routes.detect() 가 notif
          를 끝까지 들고 있는 것과 같은 모양이다. 참조를 아무도 안 들고 있으면 identity
          map 약참조 때문에 가드가 못 잡는다(kakao._uncommitted_classes docstring 의
          "알려진 한계"). 그 한계를 숨기지 않으려고 형태를 실제 호출부에 맞췄다.
        """
        from .. import kakao
        from ..extensions import db
        from ..models import Notification
        from ..utils import utc_now

        with self.app.app_context():
            pending = Notification(
                    client_request_id="guard-flushed",
                    request_id="req_guardflushed",
                    device_id="dev-guard-flushed",
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
            db.session.add(pending)
            db.session.flush()  # ← 여기서 session.new 가 비워진다
            self.assertEqual(len(db.session.new), 0)  # 전제 확인

            with self.assertRaises(RuntimeError) as ctx:
                kakao.get_access_token()
            self.assertNotIsInstance(ctx.exception, kakao.KakaoTokenError)
            self.assertIn("Notification", str(ctx.exception))
            self.assertIsNotNone(pending)  # 참조 유지가 이 케이스의 전제다
            db.session.rollback()

    # ── 확정 카피 ② (카테고리 7.1) ───────────────────────────────────────
    def test_fire_alarm_copy_matches_decisions_md(self) -> None:
        """상수가 decisions.md 확정 카피 ② 원문과 바이트 동일한지 매 실행 대조.

        손 전사가 아님의 증명이자 드리프트 감지다. 문서가 수정되면 여기서 먼저 깨진다.
        """
        from ..constants import FIRE_ALARM_PRIMARY_MESSAGE

        doc = _copy2_from_decisions()
        if doc is None:
            self.skipTest(f"decisions.md 를 찾지 못했다: {_DECISIONS_MD}")
        self.assertEqual(FIRE_ALARM_PRIMARY_MESSAGE.encode("utf-8"), doc.encode("utf-8"))

    def test_fire_alarm_copy_size_facts(self) -> None:
        """266자 / 603 bytes / 9줄 — 2026-09-03 실측이 절단 없음을 확인한 그 크기다.

        ★ 문서상 "200자 상한"은 실측으로 반증됐다. 이 케이스가 깨진다면 카피가 바뀐
          것이므로 재발송 1회로 렌더를 재확인할 것 — 200자로 축약하는 것이 답이 아니다.
        """
        from ..constants import FIRE_ALARM_PRIMARY_MESSAGE as msg

        self.assertEqual(len(msg), 266)
        self.assertEqual(len(msg.encode("utf-8")), 603)
        self.assertEqual(len(msg.splitlines()), 9)

    def test_memo_request_carries_full_copy_in_one_call(self) -> None:
        """발송 요청 본문에 카피 ② 전문이 1회 요청으로 실린다(분할·축약 없음).

        urlopen 을 가로채 실제 전송 파라미터를 복원해 대조한다 — 카카오로 나가는
        요청은 없다.
        """
        from .. import kakao
        from ..constants import FIRE_ALARM_PRIMARY_MESSAGE

        captured = []

        def _capture(req, timeout=None):
            captured.append(req)
            return _FakeResponse({"result_code": 0})

        with self.app.app_context(), mock.patch(
            "app.kakao.get_access_token", return_value=_FAKE_ACCESS_TOKEN
        ), mock.patch("app.kakao.urllib.request.urlopen", side_effect=_capture):
            self.assertIsNone(kakao.send_primary_text("fire_alarm"))

        self.assertEqual(len(captured), 1)  # 분할 발송 없음
        form = urllib.parse.parse_qs(captured[0].data.decode("utf-8"))
        template = json.loads(form["template_object"][0])
        self.assertEqual(template["object_type"], "text")
        self.assertEqual(template["text"], FIRE_ALARM_PRIMARY_MESSAGE)
        self.assertIn("link", template)  # text 템플릿 필수 필드

    def test_memo_non_zero_result_code_is_failure(self) -> None:
        """HTTP 200 이어도 result_code 가 0 이 아니면 실패로 집계한다."""
        from .. import kakao

        with self.app.app_context(), mock.patch(
            "app.kakao.get_access_token", return_value=_FAKE_ACCESS_TOKEN
        ), mock.patch(
            "app.kakao.urllib.request.urlopen",
            return_value=_FakeResponse({"result_code": -1}),
        ):
            self.assertEqual(
                kakao.send_primary_text("doorbell"), kakao.SKIP_REASON_KAKAO_API_ERROR
            )

    def test_memo_401_is_token_expired_not_api_error(self) -> None:
        """발송 중 401 은 원인 계층이 토큰이므로 token_expired 로 집계된다."""
        import urllib.error

        from .. import kakao

        err = urllib.error.HTTPError(
            kakao.KAKAO_MEMO_URL, 401, "Unauthorized", {}, None
        )
        with self.app.app_context(), mock.patch(
            "app.kakao.get_access_token", return_value=_FAKE_ACCESS_TOKEN
        ), mock.patch("app.kakao.urllib.request.urlopen", side_effect=err) as urlopen:
            self.assertEqual(
                kakao.send_primary_text("doorbell"), kakao.SKIP_REASON_TOKEN_EXPIRED
            )
            # 갱신 후 재발송 없음(재시도 금지)
            self.assertEqual(urlopen.call_count, 1)

    # ── 401 자기 치유 (G-신규, 2026-09-03) ────────────────────────────────
    # 배경: needs_refresh() 는 access_expires_at 만 본다. 그 값이 미래인데 카카오가
    # 토큰을 거부하는 상태(콘솔 수동 재발급 / client_secret rotate / 시계 어긋남)가
    # 실재한다 — 2026-09-03 에 client_secret rotate 가 실제로 수행됐다.
    # 보완 전 프로브 실측: 3회 연속 401, access_expires_at 불변, 복구 경로 없음.
    def _drop_kakao_token(self) -> None:
        from ..extensions import db
        from ..models import KakaoToken

        with self.app.app_context():
            row = db.session.get(KakaoToken, KakaoToken.SINGLETON_ID)
            if row is not None:
                db.session.delete(row)
                db.session.commit()

    def _seed_kakao_token(self, expires_in_hours):
        """kakao_tokens 단일 행을 심는다(케이스 종료 시 삭제).

        토큰·시크릿 실값은 없다 — 전부 자리표시 문자열이다.
        expires_in_hours=6 이면 needs_refresh False, 0 이면 True 인 상태를 만든다.
        """
        from datetime import timedelta

        from ..extensions import db
        from ..models import KakaoToken
        from ..utils import utc_now

        self.addCleanup(self._drop_kakao_token)
        now = utc_now()
        db.session.merge(
            KakaoToken(
                id=KakaoToken.SINGLETON_ID,
                access_token=_FAKE_ACCESS_TOKEN,
                refresh_token=_FAKE_REFRESH_TOKEN,
                access_expires_at=now + timedelta(hours=expires_in_hours),
                refresh_expires_at=now + timedelta(days=59),
                updated_at=now,
            )
        )
        db.session.commit()

    def test_memo_401_marks_token_expired_for_next_event(self) -> None:
        """needs_refresh=False 인데 401 → DB 토큰을 만료 표시(다음 이벤트가 갱신을 태운다).

        이 케이스가 깨지면 "죽은 토큰으로 401 무한 반복" 상태로 되돌아간 것이다.
        """
        import urllib.error

        from .. import kakao
        from ..extensions import db
        from ..models import KakaoToken
        from ..utils import utc_now

        err = urllib.error.HTTPError(kakao.KAKAO_MEMO_URL, 401, "Unauthorized", {}, None)
        with self.app.app_context():
            self._seed_kakao_token(6)
            row = db.session.get(KakaoToken, KakaoToken.SINGLETON_ID)
            self.assertFalse(row.needs_refresh(utc_now()))  # 전제: 갱신이 안 걸리는 상태

            with mock.patch(
                "app.kakao.urllib.request.urlopen", side_effect=err
            ) as urlopen:
                self.assertEqual(
                    kakao.send_primary_text("doorbell"), kakao.SKIP_REASON_TOKEN_EXPIRED
                )
            # 같은 요청 안에서 갱신 후 재발송하지 않는다(위임 §5 Step 3 "재시도 없음")
            self.assertEqual(urlopen.call_count, 1)

            db.session.expire_all()
            row = db.session.get(KakaoToken, KakaoToken.SINGLETON_ID)
            self.assertTrue(row.needs_refresh(utc_now()))

    def test_401_self_heals_on_next_event(self) -> None:
        """다음 이벤트에서 갱신이 걸려 발송이 회복되고, 그 다음부터는 갱신이 재발하지 않는다."""
        import urllib.error

        from .. import kakao

        err = urllib.error.HTTPError(kakao.KAKAO_MEMO_URL, 401, "Unauthorized", {}, None)
        calls = []

        def _fake(req, timeout=None):
            calls.append(req.full_url)
            if req.full_url == kakao.KAKAO_TOKEN_URL:
                return _FakeResponse(
                    {"access_token": _FAKE_RENEWED_TOKEN, "expires_in": 21599}
                )
            return _FakeResponse({"result_code": 0})

        with self.app.app_context():
            self._seed_kakao_token(6)
            with mock.patch("app.kakao.urllib.request.urlopen", side_effect=err):
                kakao.send_primary_text("doorbell")  # 이벤트 1: 401 → 만료 표시

            with mock.patch.dict(self.app.config, _FAKE_KAKAO_CREDS), mock.patch(
                "app.kakao.urllib.request.urlopen", side_effect=_fake
            ):
                self.assertIsNone(kakao.send_primary_text("doorbell"))  # 이벤트 2
                self.assertEqual(calls, [kakao.KAKAO_TOKEN_URL, kakao.KAKAO_MEMO_URL])

                calls.clear()
                self.assertIsNone(kakao.send_primary_text("doorbell"))  # 이벤트 3
                self.assertEqual(calls, [kakao.KAKAO_MEMO_URL])  # 갱신 재발 없음

    def test_repeated_401_does_not_amplify_round_trips(self) -> None:
        """새 토큰도 거부당하는 최악의 경우에도 왕복은 이벤트당 2회(갱신+발송)로 고정된다.

        무한 갱신 루프가 불가능함의 값 도메인 증명이다: get_access_token() 의 갱신은
        while 이 아니라 if 1회이고, 401 처리는 상태만 바꿀 뿐 재귀·재발송을 하지 않는다.
        """
        import urllib.error

        from .. import kakao

        err = urllib.error.HTTPError(kakao.KAKAO_MEMO_URL, 401, "Unauthorized", {}, None)
        calls = []

        def _fake(req, timeout=None):
            calls.append(req.full_url)
            if req.full_url == kakao.KAKAO_TOKEN_URL:
                return _FakeResponse(
                    {"access_token": _FAKE_RENEWED_TOKEN, "expires_in": 21599}
                )
            raise err  # 갱신받은 토큰마저 거부당한다

        with self.app.app_context():
            self._seed_kakao_token(6)
            with mock.patch.dict(self.app.config, _FAKE_KAKAO_CREDS), mock.patch(
                "app.kakao.urllib.request.urlopen", side_effect=_fake
            ):
                for _ in range(3):
                    self.assertEqual(
                        kakao.send_primary_text("doorbell"),
                        kakao.SKIP_REASON_TOKEN_EXPIRED,
                    )

        self.assertEqual(
            calls,
            [
                kakao.KAKAO_MEMO_URL,  # 이벤트 1: 아직 만료 표시 전
                kakao.KAKAO_TOKEN_URL,
                kakao.KAKAO_MEMO_URL,  # 이벤트 2
                kakao.KAKAO_TOKEN_URL,
                kakao.KAKAO_MEMO_URL,  # 이벤트 3
            ],
        )

    def test_refresh_failure_skips_send_without_extra_write(self) -> None:
        """갱신 실패는 발송을 시도하지 않고, 만료 표시를 덧쓰지도 않는다.

        401 자기 치유가 "토큰을 못 구한 경우"까지 번지지 않는지 본다 — env 미설정 같은
        원인은 만료 표시로 풀리지 않으므로 쓸모없는 쓰기를 하지 않는 편이 맞다.
        (자동 복구 불가 구간이며, 사람이 env 를 고치는 것 외의 경로는 없다.)
        """
        from .. import kakao
        from ..extensions import db
        from ..models import KakaoToken

        with self.app.app_context():
            self._seed_kakao_token(0)  # needs_refresh True
            before = db.session.get(KakaoToken, KakaoToken.SINGLETON_ID).access_expires_at

            # _TestConfig 가 KAKAO_REST_API_KEY 를 비워 둔다 → 네트워크 이전에 실패
            with mock.patch("app.kakao.urllib.request.urlopen") as urlopen:
                self.assertEqual(
                    kakao.send_primary_text("doorbell"), kakao.SKIP_REASON_TOKEN_EXPIRED
                )
            self.assertEqual(urlopen.call_count, 0)  # 갱신도 발송도 왕복 0회

            db.session.expire_all()
            after = db.session.get(KakaoToken, KakaoToken.SINGLETON_ID).access_expires_at
            self.assertEqual(before, after)

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

    # ── 카카오 토큰 상태 실배선 (system_health) ───────────────────────────
    #
    # 이 절이 고정하는 불변식 5개:
    #   T1 만료된 토큰은 절대 valid 로 나오지 않는다(초록불 거짓 표시 = 본 배선의 사고 형태).
    #   T2 만료 임박은 valid 로 뭉개지지 않는다 — 임계 = KAKAO_REFRESH_MARGIN 재사용.
    #   T3 토큰 행 부재는 valid 가 아니라 expired 로 합류한다(부트스트랩 전 = 발송 불가).
    #   T4 상태 어휘는 TokenStatus 3값을 넘지 않는다(4번째 상태 = 프론트 default 분기 노출).
    #   T5 만료 후 잔여 분은 음수(경과 분)로 보존된다 — 0 클램프 금지.
    #      "10분 전 만료"(재발송)와 "3일 전 만료"(refresh 체인 단절)는 대응이 갈린다.
    #
    # 시각은 전부 고정 주입(now_utc 인자) — 실시간 utc_now() 에 의존하면 간헐 실패한다.

    @staticmethod
    def _token_row(access_expires_at):
        """세션에 넣지 않는 KakaoToken 인스턴스(파생 로직 입력용). 실값 없음."""
        from ..models import KakaoToken

        return KakaoToken(access_expires_at=access_expires_at)

    def test_token_status_grid_collapses_to_three(self) -> None:
        """(행 유무 × 잔여 구간 × 경계값) 전수 → 고유 상태 3개로 붕괴한다(T4).

        축을 넓혀도 새 상태 어휘가 생기지 않는다는 것이 설계의 증명이다.
        """
        from datetime import timedelta

        from ..constants import KAKAO_REFRESH_MARGIN
        from ..routes import _kakao_token_health

        now = datetime(2026, 9, 9, 12, 0, 0)
        second = timedelta(seconds=1)
        # 잔여 구간 8종: 음수 深 / 음수 淺 / 정확히 0 / 양수 淺 / 임계 직전 /
        #                임계 정확히 / 임계 직후 / 정상
        deltas = [
            -timedelta(days=3),
            -second,
            timedelta(0),
            second,
            KAKAO_REFRESH_MARGIN - second,
            KAKAO_REFRESH_MARGIN,
            KAKAO_REFRESH_MARGIN + second,
            timedelta(hours=6),
        ]
        rows = [None] + [self._token_row(now + d) for d in deltas]  # 축 = 9행

        with self.app.app_context():
            statuses = [_kakao_token_health(r, now)[0] for r in rows]

        self.assertEqual(len(rows), 9)
        self.assertEqual(
            set(statuses), {"valid", "expiring", "expired"}
        )  # 9행 → 고유 3행
        # stats.ts TokenStatus 유니온과 1:1 (신규 어휘 발명 X)
        self.assertEqual(
            statuses,
            [
                "expired",  # 행 부재
                "expired",  # -3d
                "expired",  # -1s
                "expired",  # 정확히 0  (비교가 <= 0 임을 고정)
                "expiring",  # +1s
                "expiring",  # 임계 -1s
                "expiring",  # 임계 정확히 (비교가 <= MARGIN 임을 고정)
                "valid",  # 임계 +1s
                "valid",  # +6h
            ],
        )

    def test_expired_token_is_not_reported_valid(self) -> None:
        """만료된 토큰이 valid 로 나오면 대시보드가 초록불로 거짓말한다(T1)."""
        from datetime import timedelta

        from ..routes import _kakao_token_health

        now = datetime(2026, 9, 9, 12, 0, 0)
        with self.app.app_context():
            status, minutes = _kakao_token_health(
                self._token_row(now - timedelta(days=3)), now
            )
        self.assertEqual(status, "expired")
        self.assertNotEqual(status, "valid")
        self.assertEqual(minutes, -3 * 24 * 60)  # T5: 경과 4320분이 음수로 보존

    def test_expiring_is_not_collapsed_into_valid(self) -> None:
        """임계 이내는 expiring — valid 로 뭉개면 "곧 만료" 경고가 사라진다(T2)."""
        from datetime import timedelta

        from ..constants import KAKAO_REFRESH_MARGIN
        from ..routes import _kakao_token_health

        now = datetime(2026, 9, 9, 12, 0, 0)
        with self.app.app_context():
            at_threshold = _kakao_token_health(
                self._token_row(now + KAKAO_REFRESH_MARGIN), now
            )
            past_threshold = _kakao_token_health(
                self._token_row(now + KAKAO_REFRESH_MARGIN + timedelta(seconds=1)), now
            )
        self.assertEqual(at_threshold, ("expiring", 10))
        self.assertEqual(past_threshold[0], "valid")

    def test_missing_token_row_is_expired_not_valid(self) -> None:
        """행 부재(부트스트랩 전) = 발송 불가 → expired 합류. 4번째 상태를 만들지 않는다(T3/T4)."""
        from ..routes import _kakao_token_health

        with self.app.app_context():
            status, minutes = _kakao_token_health(None, datetime(2026, 9, 9, 12, 0, 0))
        self.assertEqual(status, "expired")
        self.assertEqual(minutes, 0)  # 만료 시각 자체를 모른다 — 경과 분을 지어내지 않는다

    def test_expired_minutes_are_not_clamped_to_zero(self) -> None:
        """0 클램프 금지(T5). 클램프하면 "3일 전"과 "방금"이 화면에서 구분 불가가 된다."""
        from datetime import timedelta

        from ..routes import _kakao_token_health

        now = datetime(2026, 9, 9, 12, 0, 0)
        with self.app.app_context():
            just = _kakao_token_health(self._token_row(now), now)[1]
            ten = _kakao_token_health(self._token_row(now - timedelta(minutes=10)), now)[1]
            days = _kakao_token_health(self._token_row(now - timedelta(days=3)), now)[1]
        self.assertEqual(just, 0)
        self.assertEqual(ten, -10)
        self.assertEqual(days, -4320)
        self.assertEqual(len({just, ten, days}), 3)  # 세 상황이 서로 구분된다

    def test_stats_token_status_comes_from_db_row(self) -> None:
        """/stats 가 하드코딩이 아니라 DB 행을 읽는다 — 행을 심으면 잔여 분이 따라 움직인다."""
        with self.app.app_context():
            self._seed_kakao_token(6)  # access 만료 = 6시간 후

        r = self.client.get(
            "/api/v1/stats?period=today",
            headers={"Authorization": f"Bearer {_DASHBOARD_TOKEN}"},
        )
        health = r.get_json()["system_health"]
        self.assertEqual(health["kakao_token_status"], "valid")
        # 하드코딩 240 이 아니라 실제 잔여(6시간 = 359~360분)여야 한다
        self.assertIn(health["kakao_token_expires_in_minutes"], (359, 360))

    def test_stats_without_token_row_is_expired(self) -> None:
        """토큰 행이 없는 서버에서 /stats 가 초록불을 내보내지 않는다(T3 wire)."""
        self._drop_kakao_token()
        r = self.client.get(
            "/api/v1/stats?period=today",
            headers={"Authorization": f"Bearer {_DASHBOARD_TOKEN}"},
        )
        health = r.get_json()["system_health"]
        self.assertEqual(health["kakao_token_status"], "expired")

    def test_stats_key_count_unchanged(self) -> None:
        """값 소스만 교체한다 — /stats 응답 키 집합은 불변(위임 §7-c)."""
        r = self.client.get(
            "/api/v1/stats?period=today",
            headers={"Authorization": f"Bearer {_DASHBOARD_TOKEN}"},
        )
        body = r.get_json()
        self.assertEqual(
            sorted(body),
            sorted(
                [
                    "period",
                    "period_start",
                    "period_end",
                    "server_time",
                    "summary",
                    "class_distribution",
                    "timing_metrics",
                    "skip_reasons",
                    "system_health",
                    "hourly_distribution",
                ]
            ),
        )
        self.assertEqual(
            sorted(body["system_health"]),
            sorted(
                [
                    "device_last_seen_at",
                    "device_status",
                    "signal_strength",
                    "kakao_token_status",
                    "kakao_token_expires_in_minutes",
                    "clova_api_status",
                    "db_status",
                ]
            ),
        )

    def test_token_status_read_is_side_effect_free(self) -> None:
        """관측 전용 — /stats 호출이 토큰 행을 갱신·무효화하지 않는다(위임 §7-h)."""
        from ..extensions import db
        from ..models import KakaoToken

        with self.app.app_context():
            self._seed_kakao_token(6)
            before = db.session.get(KakaoToken, KakaoToken.SINGLETON_ID)
            snapshot = (before.access_token, before.access_expires_at, before.updated_at)

        self.client.get(
            "/api/v1/stats?period=today",
            headers={"Authorization": f"Bearer {_DASHBOARD_TOKEN}"},
        )

        with self.app.app_context():
            db.session.expire_all()
            after = db.session.get(KakaoToken, KakaoToken.SINGLETON_ID)
            self.assertEqual(
                (after.access_token, after.access_expires_at, after.updated_at), snapshot
            )

    def test_token_value_never_reaches_stats_response(self) -> None:
        """응답에 나가는 것은 상태와 잔여 시간뿐 — 토큰 문자열·일부가 새지 않는다(위임 §7-b)."""
        with self.app.app_context():
            self._seed_kakao_token(6)

        r = self.client.get(
            "/api/v1/stats?period=today",
            headers={"Authorization": f"Bearer {_DASHBOARD_TOKEN}"},
        )
        body = r.get_data(as_text=True)
        self.assertNotIn(_FAKE_ACCESS_TOKEN, body)
        self.assertNotIn(_FAKE_REFRESH_TOKEN, body)
        self.assertNotIn(_FAKE_ACCESS_TOKEN[:8], body)

    # ── Clova STT 상태 실배선 (system_health.clova_api_status) ────────────
    #
    # 8.5(i) 후보 1순위 — 판정 재료(stt.is_real_mode, PR #45)는 이미 있었고 표시
    # 어휘(ServiceStatus)도 이미 있었다. 이 절이 고정하는 불변식:
    #   C1 real 모드(자격증명 둘 다 설정)면 "ok".
    #   C2 mock 모드(둘 중 하나라도 미설정/빈 문자열)면 "degraded" — "error" 아님
    #      (7.7(k): "안 불렀다"와 "불렀는데 실패"를 어휘로 섞지 않는다).
    #   C3 어느 쪽이든 NCP 자격증명 문자열 자체는 응답에 나가지 않는다.
    # is_real_mode() 자체의 (ID×SECRET×빈문자열) 전수 분기는 이미
    # test_half_credentials_is_not_real_mode 가 고정한다 — 여기서는 그 판정이
    # /stats 응답까지 실제로 이어지는지만 본다(중복 재검증 금지).

    def test_stats_clova_status_is_ok_when_real_mode(self) -> None:
        """C1 — 자격증명이 둘 다 설정되면 화면이 'ok'를 낸다."""
        with mock.patch.dict(self.app.config, self._FAKE_NCP_CREDS):
            r = self.client.get(
                "/api/v1/stats?period=today",
                headers={"Authorization": f"Bearer {_DASHBOARD_TOKEN}"},
            )
        self.assertEqual(r.get_json()["system_health"]["clova_api_status"], "ok")

    def test_stats_clova_status_is_degraded_when_mock_mode(self) -> None:
        """C2 — 자격증명 미설정(mock 자막)이면 'degraded'다. 'ok' 로 위장하지 않는다."""
        with mock.patch.dict(
            self.app.config, {"NCP_CLIENT_ID": "", "NCP_CLIENT_SECRET": ""}
        ):
            r = self.client.get(
                "/api/v1/stats?period=today",
                headers={"Authorization": f"Bearer {_DASHBOARD_TOKEN}"},
            )
        health = r.get_json()["system_health"]
        self.assertEqual(health["clova_api_status"], "degraded")
        self.assertNotEqual(health["clova_api_status"], "ok")
        self.assertNotEqual(health["clova_api_status"], "error")  # 8.5(i)/7.7(k)

    def test_stats_clova_status_never_leaks_ncp_credentials(self) -> None:
        """C3 — 응답에 나가는 것은 ok/degraded 뿐, 자격증명 문자열은 새지 않는다."""
        with mock.patch.dict(self.app.config, self._FAKE_NCP_CREDS):
            r = self.client.get(
                "/api/v1/stats?period=today",
                headers={"Authorization": f"Bearer {_DASHBOARD_TOKEN}"},
            )
        body = r.get_data(as_text=True)
        self.assertNotIn(self._FAKE_NCP_CREDS["NCP_CLIENT_ID"], body)
        self.assertNotIn(self._FAKE_NCP_CREDS["NCP_CLIENT_SECRET"], body)

    # ── ToF 메타 wire (카테고리 6.2 G10) ──────────────────────────────────
    #
    # 이 절이 고정하는 불변식 5개:
    #   I1 ToF 부재 요청은 현행대로 통과한다(2026-09-03 A-1 경로 보존, fail-open).
    #   I2 노크·초인종은 tof_presence 가 참일 때만 발송 경로에 진입한다.
    #   I3 화재경보는 ToF 게이트를 우회한다(카테고리 3 SSoT).
    #   I4 "게이트를 통과한 요청"과 "ToF 부재로 게이트를 적용하지 않은 요청"이
    #      응답·DB 두 곳에서 구분 가능하다(부재를 통과로 위장하지 않는다).
    #   I5 서버는 tof_presence 를 재판정하지 않는다 — near_count/center/ndet 로
    #      통과 여부를 다시 계산하지 않는다(9.2(e)/9.4(b) 시간축 판정 재구성 불가).

    @staticmethod
    def _prediction_stub(predicted_class, confidence=0.95):
        """클래스·신뢰도만 고정하고 판정은 실제 함수에 맡기는 mock_prediction 대역.

        상수 dict 를 돌려주는 스텁을 쓰면 라우트가 파싱한 ToF 메타가 판정까지
        흘러가는지를 검증하지 못한다 — 여기서는 랜덤 요소만 제거한다.
        """

        def _stub(tof_meta=None):
            from ..utils import _apply_prediction_policy

            scores = {"doorbell": 0.34, "knock": 0.33, "fire_alarm": 0.33}
            return _apply_prediction_policy(
                predicted_class, confidence, scores, tof_meta
            )

        return _stub

    _TOF_PASS = {
        # 9.2(b) 실측 로그(near=13/64, center=1015mm) + 9.4(d) 재충전 로그(ndet=1) 어휘
        "tof_presence": "true",
        "tof_near_count": "13",
        "tof_center_mm": "1015",
        "tof_motion_ndet": "1",
    }
    _TOF_FAIL = {
        "tof_presence": "false",
        "tof_near_count": "1",
        "tof_center_mm": "2953",
        "tof_motion_ndet": "0",
    }

    def _detect_with(self, key, predicted_class, tof, confidence=0.95):
        """클래스 고정 + ToF 메타 동봉 detect 1회. (응답, 발송 스텁) 반환."""
        with self.app.app_context(), mock.patch(
            "app.routes.mock_prediction",
            side_effect=self._prediction_stub(predicted_class, confidence),
        ), mock.patch("app.kakao.send_primary_text", return_value=None) as send:
            resp = self._detect(f"regr-tof-{key}", f"dev-tof-{key}", tof=tof)
            row = self._row(f"regr-tof-{key}") if resp.status_code == 201 else None
            return resp, send, row

    def test_tof_absent_preserves_current_behavior(self) -> None:
        """I1. ToF 4필드 부재 = 현행 A-1 경로 그대로 발송된다(400 아님, 차단 아님)."""
        resp, send, row = self._detect_with("absent", "knock", None)
        self.assertEqual(resp.status_code, 201)
        send.assert_called_once_with("knock")

        status = resp.get_json()["notification_status"]
        self.assertTrue(status["primary_sent"])
        self.assertNotIn("skip_reason", status)
        self.assertTrue(row.primary_sent)

    def test_knock_with_presence_true_enters_send_path(self) -> None:
        """I2. 노크 + presence 참 → 발송 경로 진입 + 게이트 적용 기록."""
        resp, send, row = self._detect_with("knock-pass", "knock", self._TOF_PASS)
        self.assertEqual(resp.status_code, 201)
        send.assert_called_once_with("knock")

        check = resp.get_json()["tof_check"]
        self.assertTrue(check["applied"])
        self.assertTrue(check["passed"])
        # 하드코딩 문자열이 아니라 수신값에서 생성됐다는 증명 — 요청에 실은 값이 보인다
        self.assertIn("near=13/64", check["reason"])
        self.assertIn("center=1015mm", check["reason"])
        self.assertIn("ndet=1/16", check["reason"])
        self.assertTrue(row.tof_applied)
        self.assertTrue(row.tof_passed)

    def test_knock_with_presence_false_is_blocked(self) -> None:
        """I2. 노크 + presence 거짓 → 차단 + 사유 기록 + 카카오 왕복 자체를 태우지 않음."""
        resp, send, row = self._detect_with("knock-fail", "knock", self._TOF_FAIL)
        self.assertEqual(resp.status_code, 201)  # 차단은 요청 실패가 아니다
        send.assert_not_called()

        body = resp.get_json()
        self.assertFalse(body["notification_status"]["primary_sent"])
        self.assertEqual(body["notification_status"]["skip_reason"], "tof_rejected")
        self.assertEqual(body["notification_status"]["enrich_status"], "skipped")
        self.assertTrue(body["tof_check"]["applied"])
        self.assertFalse(body["tof_check"]["passed"])
        self.assertEqual(row.skip_reason, "tof_rejected")
        self.assertIsNone(row.primary_sent_at)

    def test_doorbell_with_presence_false_is_blocked(self) -> None:
        """I2. 초인종도 동일 게이트. (SP/DTW 2층은 본 PR 범위 밖 — 여기선 ToF 1층만)"""
        resp, send, row = self._detect_with("bell-fail", "doorbell", self._TOF_FAIL)
        self.assertEqual(resp.status_code, 201)
        send.assert_not_called()
        self.assertFalse(row.primary_sent)
        self.assertEqual(row.skip_reason, "tof_rejected")

    def test_fire_alarm_bypasses_tof_gate(self) -> None:
        """I3. 화재경보 + presence 거짓 → 그래도 발송(카테고리 3 "ToF 우회").

        ★ 이 케이스가 실패하면 화재경보가 ToF 게이트를 따르게 바뀐 것이다 —
          청각장애인 대응 수칙(7.1) 발송이 사람 검증에 묶이면 안 된다.
        """
        resp, send, row = self._detect_with("fire-fail", "fire_alarm", self._TOF_FAIL)
        self.assertEqual(resp.status_code, 201)
        send.assert_called_once_with("fire_alarm")
        self.assertTrue(row.primary_sent)
        self.assertIsNone(row.skip_reason)

        check = resp.get_json()["tof_check"]
        self.assertFalse(check["applied"])  # 게이트 미적용 = 우회
        self.assertIsNone(check["passed"])
        self.assertTrue(check["reason"].startswith("fire_alarm_bypass"))
        # 우회했더라도 받은 증거는 버리지 않는다
        self.assertIn("presence=false", check["reason"])

    def test_tof_absent_is_distinguishable_from_tof_pass(self) -> None:
        """I4. 부재와 통과가 응답·DB 에서 갈린다.

        ★ negative control 대상 불변식이다. "ToF 부재를 presence=true 로 취급"하는
          변형은 발송 결과(primary_sent True)만 보면 부재 케이스와 구별되지 않아
          아무 테스트도 깨지지 않는다 — applied/passed/reason 세 값을 함께 고정해야
          그 변형이 검출된다.
        """
        _, _, absent_row = self._detect_with("distinct-absent", "knock", None)
        resp_pass, _, pass_row = self._detect_with(
            "distinct-pass", "knock", self._TOF_PASS
        )

        # 발송 결과는 둘 다 동일 — 이 값만으로는 두 상태를 구분할 수 없다
        self.assertTrue(absent_row.primary_sent)
        self.assertTrue(pass_row.primary_sent)

        # 응답에서 구분 가능
        absent_check = self._body("regr-tof-distinct-absent")["tof_check"]
        pass_check = resp_pass.get_json()["tof_check"]
        self.assertFalse(absent_check["applied"])
        self.assertIsNone(absent_check["passed"])
        self.assertEqual(absent_check["reason"], "tof_absent")
        self.assertTrue(pass_check["applied"])
        self.assertTrue(pass_check["passed"])

        # DB 기록에서도 구분 가능
        self.assertFalse(absent_row.tof_applied)
        self.assertIsNone(absent_row.tof_passed)
        self.assertEqual(absent_row.tof_reason, "tof_absent")
        self.assertTrue(pass_row.tof_applied)

    def test_tof_invalid_is_distinguishable_from_absent_and_pass(self) -> None:
        """I4. 이탈(invalid)은 부재와도 통과와도 다른 제3의 상태로 기록된다.

        여기서는 presence 없이 telemetry 만 온 오배선을 쓴다 — 게이트 입력이 없으므로
        차단하지 않되(fail-open) 사유가 tof_absent 와 달라야 한다.
        """
        resp, send, row = self._detect_with(
            "invalid", "knock", {"tof_near_count": "13", "tof_center_mm": "1015"}
        )
        self.assertEqual(resp.status_code, 201)  # 400 아님 — 체인을 죽이지 않는다
        send.assert_called_once_with("knock")

        check = resp.get_json()["tof_check"]
        self.assertFalse(check["applied"])
        self.assertIsNone(check["passed"])
        self.assertNotEqual(check["reason"], "tof_absent")
        self.assertIn("tof_invalid", check["reason"])
        self.assertIn("tof_presence", check["reason"])
        self.assertIn("tof_invalid", row.tof_reason)

    def test_tof_out_of_range_telemetry_is_recorded_not_rejected(self) -> None:
        """§2-C. 구조 상한(zone 64 / aggregate 16) 이탈 = 400 아님, 값은 버리고 사유 기록.

        상한 근거 = decisions.md 9.2/9.3 실측 구조 상수(constants.py 주석 참조).
        """
        resp, _, row = self._detect_with(
            "range",
            "knock",
            {
                "tof_presence": "true",
                "tof_near_count": "65",  # 64 초과
                "tof_motion_ndet": "17",  # 16 초과
                "tof_center_mm": "-1",  # 음수
            },
        )
        self.assertEqual(resp.status_code, 201)

        check = resp.get_json()["tof_check"]
        # presence 는 멀쩡하므로 게이트는 그대로 적용된다(telemetry 이탈이 게이트를
        # 끄면, 거절될 요청이 telemetry 를 망가뜨리는 것만으로 통과하게 된다)
        self.assertTrue(check["applied"])
        self.assertTrue(check["passed"])
        for field in ("tof_near_count", "tof_motion_ndet", "tof_center_mm"):
            self.assertIn(field, check["reason"])
        self.assertIn("invalid", check["reason"])
        # 이탈값은 기록에 그대로 실리지 않는다(요약 표기는 invalid)
        self.assertNotIn("near=65", row.tof_reason)

    def test_tof_telemetry_invalid_does_not_disable_gate(self) -> None:
        """§2-C. presence 거짓 + telemetry 이탈 → 여전히 차단된다(게이트 우회 불가)."""
        resp, send, row = self._detect_with(
            "range-fail",
            "knock",
            {"tof_presence": "false", "tof_near_count": "999"},
        )
        self.assertEqual(resp.status_code, 201)
        send.assert_not_called()
        self.assertEqual(row.skip_reason, "tof_rejected")

    def test_tof_presence_boolean_tokens(self) -> None:
        """multipart 는 전부 문자열 — "false"/"0"/"" 가 참으로 평가되면 안 된다."""
        from ..tof_meta import parse_tof_meta

        for raw in ("true", "TRUE", " true ", "1"):
            meta = parse_tof_meta({"tof_presence": raw})
            self.assertEqual(meta["state"], "present", raw)
            self.assertIs(meta["presence"], True, raw)

        for raw in ("false", "False", "0"):
            meta = parse_tof_meta({"tof_presence": raw})
            self.assertEqual(meta["state"], "present", raw)
            self.assertIs(meta["presence"], False, raw)

        # 허용표 밖 = 이탈. 빈 문자열이 '부재'로 흡수되지 않는 것이 핵심이다
        # (부재는 게이트 미적용이지만, 빈 값은 송신측 오배선이라 사유가 남아야 한다).
        for raw in ("", "  ", "yes", "on", "presence", "2"):
            meta = parse_tof_meta({"tof_presence": raw})
            self.assertEqual(meta["state"], "invalid", raw)
            self.assertIsNone(meta["presence"], raw)

    def test_server_does_not_recompute_presence_from_telemetry(self) -> None:
        """I5. 게이트는 tof_presence 단독. near_count 로 임계값 8 을 다시 계산하지 않는다.

        근거 = Stage A 디바운스(9.2(e))·Stage B-2 latch(9.4(b))는 15Hz 프레임 이력이
        있어야 성립하는 시간축 판정이라 단발 POST 스냅샷으로 재구성 불가. 서버가
        재계산하면 디바이스 판정과 갈린다.
        """
        # near=64(임계값 8 을 한참 넘김)인데 디바이스가 사람 없음이라 했으면 → 차단
        _, send_hi, row_hi = self._detect_with(
            "norecompute-hi",
            "knock",
            {"tof_presence": "false", "tof_near_count": "64", "tof_motion_ndet": "16"},
        )
        send_hi.assert_not_called()
        self.assertEqual(row_hi.skip_reason, "tof_rejected")

        # near=0(임계값 미달)인데 디바이스가 사람 있음이라 했으면 → 통과
        # (latch 가 붙잡고 있는 구간 = 9.4(d) `#4291~#4351` 실측 사례)
        _, send_lo, row_lo = self._detect_with(
            "norecompute-lo",
            "knock",
            {"tof_presence": "true", "tof_near_count": "0", "tof_motion_ndet": "0"},
        )
        send_lo.assert_called_once_with("knock")
        self.assertTrue(row_lo.primary_sent)

    def test_tof_meta_does_not_change_gate_order(self) -> None:
        """게이트 순서(멱등 → rate limit → 디코드 → 추론) 무이동 회귀.

        ToF 파싱은 게이트가 아니다 — ToF 를 실어도 멱등 replay 가 먼저 잡고,
        같은 device 의 새 키는 rate limit 에 걸리며, 깨진 오디오는 400 이다.
        """
        dev = "dev-tof-order"
        with self.app.app_context(), mock.patch(
            "app.kakao.send_primary_text", return_value=None
        ):
            first = self._detect("regr-tof-order-1", dev, tof=self._TOF_PASS)
            self.assertEqual(first.status_code, 201)

            blocked = self._detect("regr-tof-order-2", dev, tof=self._TOF_PASS)
            self.assertEqual(blocked.status_code, 429)

            replayed = self._detect("regr-tof-order-1", dev, tof=self._TOF_FAIL)
            self.assertEqual(replayed.status_code, 200)
            self.assertEqual(replayed.headers.get("Idempotent-Replay"), "true")
            # 멱등 replay 는 최초 응답 스냅샷 — 나중 요청의 ToF 값이 끼어들지 않는다
            self.assertEqual(replayed.get_json(), first.get_json())

        # 깨진 오디오는 ToF 유무와 무관하게 여전히 400(디코드 게이트 무이동)
        bad = self._detect(
            "regr-tof-order-3", "dev-tof-order-3", audio=b"\x01", tof=self._TOF_PASS
        )
        self.assertEqual(bad.status_code, 400)

    def _body(self, client_request_id):
        """저장된 알림의 응답 스냅샷(멱등 키에 캐시된 최초 응답 본문)."""
        from ..extensions import db
        from ..models import IdempotencyKey

        with self.app.app_context():
            return db.session.get(IdempotencyKey, client_request_id).response_json

    # ── 2차 알림 발송 배선 (A-2, 카테고리 7 — 실발송 없음, 전부 스텁) ────
    #
    # 이 절이 고정하는 불변식:
    #   S1. 자막이 있으면 2건(사진 feed → 자막 text)이, **이 순서로** 나간다.
    #   S2. 자막이 없으면 사진 1건만 나가고 text 는 **호출되지 않는다**.
    #   S3. 부분 실패는 완전 성공과 다른 상태로 기록된다(4조합 전부 서로 구분).
    #   S4. 재시도는 **실패한 건에만** 걸린다 — 성공한 건은 다시 발송되지 않는다.
    #   S5. 1차 경로(/detect)는 본 배선의 영향을 받지 않는다.
    #
    # 스텁 지점은 두 층뿐이다(1차 절 컨벤션 동형):
    #   (a) app.kakao.send_secondary   = routes 배선/상태 매핑을 볼 때
    #   (b) app.kakao.get_access_token + urlopen = kakao 내부 순서·재시도를 볼 때

    _JPEG = b"\xff\xd8" + b"\x00" * 64  # SOI 매직바이트 + 더미 본문

    def _seed_pending(self, key, predicted_class="doorbell"):
        """/detect 를 태워 enrich_status=pending 인 알림 1건을 만든다."""
        sent = self._policy(predicted_class, 0.95)
        self.assertEqual(sent["enrich_status"], "pending")  # 전제 확인
        with self.app.app_context(), mock.patch(
            "app.routes.mock_prediction", return_value=sent
        ), mock.patch("app.kakao.send_primary_text", return_value=None):
            r = self._detect(key, "dev-" + key)
            self.assertEqual(r.status_code, 201)

    def _enrich(self, key):
        return self.client.post(
            "/api/v1/enrich",
            headers={"Authorization": f"Bearer {_DEVICE_TOKEN}"},
            data={
                "client_request_id": key,
                "image": (io.BytesIO(self._JPEG), "a.jpg"),
                "audio": (io.BytesIO(self.pcm), "a.pcm"),
            },
            content_type="multipart/form-data",
        )

    @staticmethod
    def _stt(transcript):
        """mock_enrichment 반환값을 자막만 바꿔 재구성(나머지 mock 형태 유지)."""

        def _fake(request_id):
            from ..utils import mock_enrichment

            enr = mock_enrichment(request_id)
            enr["stt"] = None if transcript is None else dict(enr["stt"], transcript=transcript)
            return enr

        return _fake

    def _run_enrich(self, key, transcript, send_result):
        """자막·발송결과를 고정한 /enrich 1회. (응답 json, send 호출 mock) 반환."""
        with self.app.app_context(), mock.patch(
            "app.routes.mock_enrichment", side_effect=self._stt(transcript)
        ), mock.patch(
            "app.kakao.send_secondary", return_value=send_result
        ) as send:
            r = self._enrich(key)
            self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
            return r.get_json(), send

    @staticmethod
    def _result(photo_sent, caption_sent):
        """send_secondary 반환 계약 그대로의 스텁 결과."""
        return {
            "photo_sent": photo_sent,
            "photo_reason": None if photo_sent else "kakao_api_error",
            "caption_sent": caption_sent,
            "caption_reason": None if caption_sent is not False else "kakao_api_error",
        }

    @staticmethod
    def _status(body):
        return body["notification_status"]

    def test_caption_present_sends_photo_then_caption(self) -> None:
        """S1 — 자막이 있으면 사진(feed) → 자막(text) 2건이 그 순서로 나간다.

        ★ 순서를 결과가 아니라 **wire 로** 검사한다. 두 발송이 서로 독립이라 "순서를
          뒤집는" 변형은 결과만 보는 케이스로는 검출되지 않는다(NC-4 함정) — 실제
          urlopen 요청 2건의 template object_type 을 순서대로 본다.
        """
        from .. import kakao

        captured = []

        def _capture(req, timeout=None):
            form = urllib.parse.parse_qs(req.data.decode("utf-8"))
            captured.append(json.loads(form["template_object"][0]))
            return _FakeResponse({"result_code": 0})

        with self.app.app_context(), mock.patch(
            "app.kakao.get_access_token", return_value=_FAKE_ACCESS_TOKEN
        ), mock.patch("app.kakao.urllib.request.urlopen", side_effect=_capture):
            from datetime import datetime

            out = kakao.send_secondary(
                "doorbell", "https://example.test/c/abc.jpg", "택배 왔습니다.",
                datetime(2026, 9, 4, 6, 30, 0),
            )

        self.assertEqual([t["object_type"] for t in captured], ["feed", "text"])
        self.assertEqual(captured[0]["content"]["image_url"], "https://example.test/c/abc.jpg")
        self.assertEqual(captured[1]["text"], "택배 왔습니다.")
        self.assertTrue(out["photo_sent"])
        self.assertTrue(out["caption_sent"])
        # 자막은 feed description 에 들어가지 않는다(2줄 절단, 2026-09-04 프로브)
        self.assertNotIn("택배", captured[0]["content"]["description"])
        # 감지 시각(KST = UTC+9 → 15:30)이 본문이 된다
        self.assertIn("15:30", captured[0]["content"]["description"])

    def test_caption_absent_sends_photo_only(self) -> None:
        """S2 — 자막이 없으면 text 를 호출하지 않는다(사진 1건만)."""
        from .. import kakao

        captured = []

        def _capture(req, timeout=None):
            form = urllib.parse.parse_qs(req.data.decode("utf-8"))
            captured.append(json.loads(form["template_object"][0]))
            return _FakeResponse({"result_code": 0})

        with self.app.app_context(), mock.patch(
            "app.kakao.get_access_token", return_value=_FAKE_ACCESS_TOKEN
        ), mock.patch("app.kakao.urllib.request.urlopen", side_effect=_capture):
            out = kakao.send_secondary("knock", "https://example.test/c/x.jpg", None, None)

        self.assertEqual([t["object_type"] for t in captured], ["feed"])
        self.assertTrue(out["photo_sent"])
        # None = "보낼 자막이 없었다". False("보내려다 실패") 와 섞이면 안 된다(§2-C).
        self.assertIsNone(out["caption_sent"])
        self.assertIsNone(out["caption_reason"])

    def test_blank_transcript_is_treated_as_no_caption(self) -> None:
        """공백만 있는 transcript 는 자막 없음으로 접힌다(빈 말풍선 방지)."""
        from ..routes import _caption_from_stt

        self.assertIsNone(_caption_from_stt(None))
        self.assertIsNone(_caption_from_stt({}))
        self.assertIsNone(_caption_from_stt({"transcript": ""}))
        self.assertIsNone(_caption_from_stt({"transcript": "   "}))
        self.assertEqual(_caption_from_stt({"transcript": " 안녕 "}), "안녕")

    def test_full_success_state(self) -> None:
        """S3 (1/4) — 사진O 자막O = 완전 성공."""
        self._seed_pending("regr-sec-ok")
        body, send = self._run_enrich("regr-sec-ok", "택배 왔습니다.", self._result(True, True))
        send.assert_called_once()
        st = self._status(body)
        self.assertTrue(st["secondary_sent"])
        self.assertIsNotNone(st["secondary_sent_at"])
        self.assertEqual(st["enrich_status"], "completed")

    def test_photo_ok_caption_failed_is_not_full_success(self) -> None:
        """S3 (2/4) — 사진O 자막X. 완전 성공과 반드시 달라야 한다.

        ★ secondary_sent 를 "사진 성공"으로 두면 대시보드 뱃지가 이 건을 "전송 완료"로
          렌더한다(derive 가 secondary_sent 를 enrich_status 보다 먼저 본다) — §2-E 가
          금지한 "부분 성공이 완전 성공처럼 보이는" 상태다. 그래서 False 다.
        """
        self._seed_pending("regr-sec-cap-fail")
        body, _ = self._run_enrich(
            "regr-sec-cap-fail", "택배 왔습니다.", self._result(True, False)
        )
        st = self._status(body)
        self.assertFalse(st["secondary_sent"])
        self.assertEqual(st["enrich_status"], "failed")
        # 사진은 실제로 갔다 → 전달 시각이 남는다(완전 실패와 구분되는 지점)
        self.assertIsNotNone(st["secondary_sent_at"])

    def test_photo_failed_caption_ok_is_distinct(self) -> None:
        """S3 (3/4) — 사진X 자막O. 위 (2/4) 와도, 완전 성공과도 다른 상태."""
        self._seed_pending("regr-sec-photo-fail")
        body, _ = self._run_enrich(
            "regr-sec-photo-fail", "택배 왔습니다.", self._result(False, True)
        )
        st = self._status(body)
        self.assertFalse(st["secondary_sent"])
        self.assertIsNone(st["secondary_sent_at"])   # 사진이 안 갔다
        self.assertEqual(st["enrich_status"], "completed")  # 자막은 실패가 아니다

    def test_both_failed_is_distinct(self) -> None:
        """S3 (4/4) — 2건 다 실패. 나머지 3조합 어느 것과도 겹치지 않는다."""
        self._seed_pending("regr-sec-both-fail")
        body, _ = self._run_enrich(
            "regr-sec-both-fail", "택배 왔습니다.", self._result(False, False)
        )
        st = self._status(body)
        self.assertFalse(st["secondary_sent"])
        self.assertIsNone(st["secondary_sent_at"])
        self.assertEqual(st["enrich_status"], "failed")

    def test_four_combinations_are_mutually_distinguishable(self) -> None:
        """S3 — 위 4조합의 상태 3키 조합이 실제로 서로 다름을 한자리에서 확인.

        개별 케이스가 각자 통과해도 두 조합이 같은 튜플로 수렴하면 진단이 불가능하다.
        """
        seen = {}
        for name, (photo, caption) in {
            "photo_ok_caption_ok": (True, True),
            "photo_ok_caption_fail": (True, False),
            "photo_fail_caption_ok": (False, True),
            "photo_fail_caption_fail": (False, False),
        }.items():
            key = f"regr-sec-combo-{name}"
            self._seed_pending(key)
            body, _ = self._run_enrich(key, "자막 있음", self._result(photo, caption))
            st = self._status(body)
            triple = (
                st["secondary_sent"],
                st["secondary_sent_at"] is not None,
                st["enrich_status"],
            )
            self.assertNotIn(triple, seen, f"{name} 이 {seen.get(triple)} 와 같은 상태로 수렴")
            seen[triple] = name
        self.assertEqual(len(seen), 4)

    def test_no_caption_success_is_not_marked_failed(self) -> None:
        """자막이 없어 안 보낸 것은 실패가 아니다 — enrich_status 가 failed 가 되면 안 된다."""
        self._seed_pending("regr-sec-nocap")
        body, _ = self._run_enrich("regr-sec-nocap", None, self._result(True, None))
        st = self._status(body)
        self.assertTrue(st["secondary_sent"])
        self.assertEqual(st["enrich_status"], "completed")
        # 자막 유무 자체는 stt 필드가 보존한다(상태 3키와 합쳐 전 상태 복원 가능)
        self.assertIsNone(body["stt"])

    def test_retry_applies_only_to_the_failed_part(self) -> None:
        """S4 — 사진 성공 + 자막 첫 실패 → 재시도는 자막에만. 사진 재발송 0건.

        ★ 이 케이스가 "2건 통째 재시도" 변형의 유일한 검출 지점이다: 결과(둘 다 성공)만
          보면 통째 재시도도 통과하므로, **wire 요청 시퀀스**를 본다.
        """
        from .. import kakao

        seq = []

        def _capture(req, timeout=None):
            form = urllib.parse.parse_qs(req.data.decode("utf-8"))
            kind = json.loads(form["template_object"][0])["object_type"]
            seq.append(kind)
            if kind == "text" and seq.count("text") == 1:
                return _FakeResponse({"result_code": -1})  # 자막 1회차만 실패
            return _FakeResponse({"result_code": 0})

        with self.app.app_context(), mock.patch(
            "app.kakao.get_access_token", return_value=_FAKE_ACCESS_TOKEN
        ), mock.patch("app.kakao.urllib.request.urlopen", side_effect=_capture):
            out = kakao.send_secondary("doorbell", "https://e.test/a.jpg", "자막", None)

        self.assertEqual(seq, ["feed", "text", "text"])
        self.assertEqual(seq.count("feed"), 1)  # 성공한 사진은 단 한 번만 나갔다
        self.assertTrue(out["photo_sent"])
        self.assertTrue(out["caption_sent"])

    def test_retry_budget_is_one_per_part(self) -> None:
        """재시도는 건당 1회까지 — 계속 실패해도 무한 반복하지 않는다."""
        from .. import kakao
        from ..constants import KAKAO_SECONDARY_MAX_ATTEMPTS

        seq = []

        def _capture(req, timeout=None):
            form = urllib.parse.parse_qs(req.data.decode("utf-8"))
            seq.append(json.loads(form["template_object"][0])["object_type"])
            return _FakeResponse({"result_code": -1})

        with self.app.app_context(), mock.patch(
            "app.kakao.get_access_token", return_value=_FAKE_ACCESS_TOKEN
        ), mock.patch("app.kakao.urllib.request.urlopen", side_effect=_capture):
            out = kakao.send_secondary("doorbell", "https://e.test/a.jpg", "자막", None)

        self.assertEqual(seq.count("feed"), KAKAO_SECONDARY_MAX_ATTEMPTS)
        self.assertEqual(seq.count("text"), KAKAO_SECONDARY_MAX_ATTEMPTS)
        self.assertFalse(out["photo_sent"])
        self.assertFalse(out["caption_sent"])
        self.assertEqual(out["photo_reason"], "kakao_api_error")

    def test_secondary_401_does_not_resend_in_same_request(self) -> None:
        """401 은 재시도하지 않는다 — 1차가 확립한 자기 치유 규약(다음 이벤트에서 갱신).

        같은 죽은 토큰으로 두 번째 왕복을 태우지도 않는다(자막까지 즉시 중단).
        """
        from .. import kakao

        seq = []

        def _capture(req, timeout=None):
            form = urllib.parse.parse_qs(req.data.decode("utf-8"))
            seq.append(json.loads(form["template_object"][0])["object_type"])
            raise urllib.error.HTTPError(KAKAO_MEMO_URL_FOR_TEST, 401, "u", {}, None)

        with self.app.app_context(), mock.patch(
            "app.kakao.get_access_token", return_value=_FAKE_ACCESS_TOKEN
        ), mock.patch("app.kakao._invalidate_access_token") as invalidate, mock.patch(
            "app.kakao.urllib.request.urlopen", side_effect=_capture
        ):
            out = kakao.send_secondary("doorbell", "https://e.test/a.jpg", "자막", None)

        self.assertEqual(seq, ["feed"])  # 재시도 0회 + 자막 왕복 0회
        invalidate.assert_called_once()
        self.assertEqual(out["photo_reason"], "token_expired")
        self.assertEqual(out["caption_reason"], "token_expired")
        self.assertFalse(out["caption_sent"])

    def test_token_unavailable_skips_both_sends(self) -> None:
        """토큰 확보 실패 → 네트워크 왕복 0회로 두 건 모두 token_expired."""
        from .. import kakao

        with self.app.app_context(), mock.patch(
            "app.kakao.get_access_token",
            side_effect=kakao.KakaoTokenError("no token"),
        ), mock.patch("app.kakao.urllib.request.urlopen") as urlopen:
            out = kakao.send_secondary("doorbell", "https://e.test/a.jpg", "자막", None)

        urlopen.assert_not_called()
        self.assertFalse(out["photo_sent"])
        self.assertEqual(out["photo_reason"], "token_expired")
        self.assertEqual(out["caption_reason"], "token_expired")

    def test_secondary_send_precedes_notification_update(self) -> None:
        """발송은 notif 수정보다 먼저 — kakao 계층 commit 에 미커밋 변경이 딸려가지 않는다.

        1차(test_send_precedes_notification_add)와 같은 규약을 2차에서 재고정한다.
        순서가 뒤집히면 kakao._assert_commit_is_safe() 가 RuntimeError 를 올린다.
        """
        from .. import kakao

        self._seed_pending("regr-sec-order")

        seen = {}

        def _recording(*args, **kwargs):
            # 발송 시점에 세션이 깨끗해야 한다(= 가드가 통과할 수 있는 상태).
            kakao._assert_commit_is_safe()
            seen["called"] = True
            return self._result(True, True)

        with self.app.app_context(), mock.patch(
            "app.routes.mock_enrichment", side_effect=self._stt("자막")
        ), mock.patch("app.kakao.send_secondary", side_effect=_recording):
            r = self._enrich("regr-sec-order")
            self.assertEqual(r.status_code, 200)
        self.assertTrue(seen.get("called"))

    def test_failed_enrich_is_terminal_no_duplicate_photo(self) -> None:
        """S4 — 자막 실패로 failed 가 된 건은 재처리되지 않는다(사진 중복 발송 차단)."""
        self._seed_pending("regr-sec-terminal")
        body, _ = self._run_enrich(
            "regr-sec-terminal", "자막", self._result(True, False)
        )
        self.assertEqual(self._status(body)["enrich_status"], "failed")

        with self.app.app_context(), mock.patch(
            "app.kakao.send_secondary"
        ) as send:
            again = self._enrich("regr-sec-terminal")
            self.assertEqual(again.status_code, 409)
            send.assert_not_called()  # 두 번째 요청은 발송을 태우지 않는다

    def test_fire_alarm_never_reaches_secondary(self) -> None:
        """카테고리 7 "화재경보 = 1차 알림만(2차 사진+자막 미발송)" 이 코드로 유지된다."""
        fire = self._policy("fire_alarm", 0.95)
        self.assertEqual(fire["enrich_status"], "skipped")  # 전제 확인

        with self.app.app_context(), mock.patch(
            "app.routes.mock_prediction", return_value=fire
        ), mock.patch("app.kakao.send_primary_text", return_value=None):
            self.assertEqual(self._detect("regr-sec-fire", "dev-sec-fire").status_code, 201)

        with self.app.app_context(), mock.patch("app.kakao.send_secondary") as send:
            r = self._enrich("regr-sec-fire")
            self.assertEqual(r.status_code, 409)
            send.assert_not_called()

    def test_secondary_wiring_does_not_change_primary_path(self) -> None:
        """S5 — /detect 응답 계약·게이트가 2차 배선과 무관하게 그대로다(§2-B).

        같은 요청을 두 번 보내 멱등 replay 가 그대로 재생되는지까지 본다.
        """
        sent = self._policy("doorbell", 0.95)
        with self.app.app_context(), mock.patch(
            "app.routes.mock_prediction", return_value=sent
        ), mock.patch("app.kakao.send_primary_text", return_value=None) as primary, \
                mock.patch("app.kakao.send_secondary") as secondary:
            first = self._detect("regr-sec-primary", "dev-sec-primary")
            self.assertEqual(first.status_code, 201)
            secondary.assert_not_called()  # /detect 는 2차를 태우지 않는다
            primary.assert_called_once()

            body = first.get_json()
            self.assertEqual(sorted(body.keys()), sorted(_NOTIFICATION_ITEM_KEYS))
            st = body["notification_status"]
            self.assertTrue(st["primary_sent"])
            self.assertFalse(st["secondary_sent"])
            self.assertIsNone(st["secondary_sent_at"])
            self.assertEqual(st["enrich_status"], "pending")

            replay = self._detect("regr-sec-primary", "dev-sec-primary")
            self.assertEqual(replay.status_code, 200)
            self.assertEqual(replay.get_json(), body)

    def test_to_dict_key_count_unchanged(self) -> None:
        """§2-E 제약 — 2차 배선 후에도 to_dict() 최상위 키는 11개 그대로."""
        self._seed_pending("regr-sec-keys")
        body, _ = self._run_enrich("regr-sec-keys", "자막", self._result(True, True))
        self.assertEqual(len(body), 11)
        self.assertEqual(sorted(body.keys()), sorted(_NOTIFICATION_ITEM_KEYS))
        # notification_status 하위도 프론트 NotificationStatus 선언 범위를 넘지 않는다
        self.assertLessEqual(
            set(body["notification_status"]),
            {
                "primary_sent",
                "primary_sent_at",
                "enrich_status",
                "secondary_sent",
                "secondary_sent_at",
                "skip_reason",
            },
        )

    # ── 실 STT 소스 배선 (CSR, 카테고리 7 / 30.9 — 실호출 없음, 전부 스텁) ──
    #
    # 이 절이 고정하는 불변식:
    #   T1. 🔴 STT 실패는 enrich_status="failed" 가 **아니다**. 모든 실패 모드(빈 텍스트
    #       / API 오류 / 타임아웃 / 인증 거부)가 7.6(e) "자막 없음 ≠ 실패" 경로로
    #       합류한다 — 사진 1건만 나가고 secondary_sent 는 True 로 남는다.
    #   T2. 세 상태가 갈린다: 미호출(자격증명 미설정) / 호출 성공 / 호출 실패.
    #   T3. CSR 호출은 **정확히 1회**다(재시도 없음 — 15초 단위 과금, 30.9).
    #   T4. CSR 로 나가는 바이트는 **WAV 컨테이너**다(raw PCM 직송 미검증 경로 금지).
    #   T5. 자격증명 미설정이면 기존 mock 자막 경로가 그대로 유지된다(무회귀).
    #
    # ★ 스텁 지점은 urlopen 한 층뿐이다. app.stt 와 app.kakao 는 같은
    #   urllib.request 모듈을 공유하므로 하나의 스텁이 CSR·카카오 요청을 **한 시퀀스로**
    #   받는다 — 덕분에 "CSR → feed → text" 순서와 호출 횟수를 wire 로 직접 볼 수 있다
    #   (7.6(g) NC-4 가 남긴 교훈: 결과만 보는 케이스는 순서·횟수 변형을 놓친다).

    # 자리표시 NCP 자격증명. 실값 아님 — _TestConfig 는 Config 를 상속하지만
    # 개발자 로컬 .env 값이 들어올 수 있으므로 real 모드 케이스에서만 patch.dict 로
    # 이 더미를 덮어 쓴다(카카오 _FAKE_KAKAO_CREDS 컨벤션 동형).
    _FAKE_NCP_CREDS = {
        "NCP_CLIENT_ID": "test-ncp-client-id-not-real",
        "NCP_CLIENT_SECRET": "test-ncp-client-secret-not-real",
    }

    def _csr_and_kakao(self, csr_result):
        """CSR + 카카오 요청을 한 시퀀스로 받는 urlopen 스텁.

        csr_result = _FakeResponse(...) 이면 그 응답을, 예외 인스턴스면 raise.
        반환 (side_effect 함수, captured 리스트). captured 원소 = ("csr", 요청바이트)
        또는 ("kakao", template_object dict) — 순서가 그대로 보존된다.
        """
        from ..constants import STT_CSR_URL

        captured = []

        def _side_effect(req, timeout=None):
            if req.full_url.startswith(STT_CSR_URL):
                captured.append(("csr", req.data))
                if isinstance(csr_result, Exception):
                    raise csr_result
                return csr_result()
            form = urllib.parse.parse_qs(req.data.decode("utf-8"))
            captured.append(("kakao", json.loads(form["template_object"][0])))
            return _FakeResponse({"result_code": 0})

        return _side_effect, captured

    def _run_enrich_real(self, key, csr_result):
        """자격증명이 설정된(real) 상태로 /enrich 1회. (응답 json, captured) 반환."""
        side_effect, captured = self._csr_and_kakao(csr_result)
        with self.app.app_context(), mock.patch.dict(
            self.app.config, self._FAKE_NCP_CREDS
        ), mock.patch(
            "app.kakao.get_access_token", return_value=_FAKE_ACCESS_TOKEN
        ), mock.patch("app.kakao.urllib.request.urlopen", side_effect=side_effect):
            r = self._enrich(key)
            self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
            return r.get_json(), captured

    @staticmethod
    def _kinds(captured):
        return [kind for kind, _ in captured]

    # ── T4 · NC-3: WAV 컨테이너 합성 ─────────────────────────────────────
    def test_wav_header_fields_are_derived_from_input(self) -> None:
        """생성 바이트를 직접 뜯어 헤더 필드를 검사한다.

        ★ NC-3 함정: 실 API 를 부르지 않는 테스트에서 샘플레이트를 16000→8000 으로
          바꿔도 **인식 결과는 동일**하다(응답이 스텁이므로). 그래서 결과가 아니라
          **생성된 바이트**를 본다. 아래 assert 중 하나라도 빼면 NC-3 이 통과해 버린다.
        """
        from ..stt import wav_from_pcm16

        pcm = _pcm16_sine(1600)  # 0.1초 @16kHz = 3,200 bytes
        wav = wav_from_pcm16(pcm)

        self.assertEqual(len(wav), 44 + len(pcm))          # 헤더 44바이트 + 원본
        self.assertEqual(wav[0:4], b"RIFF")
        self.assertEqual(wav[8:12], b"WAVE")
        self.assertEqual(wav[12:16], b"fmt ")
        self.assertEqual(wav[36:40], b"data")
        self.assertEqual(wav[44:], pcm)                    # 원본 바이트 무손실

        (chunk_size,) = struct.unpack("<I", wav[4:8])
        (fmt_size, audio_fmt, channels, rate, byte_rate, block_align, bits) = struct.unpack(
            "<IHHIIHH", wav[16:36]
        )
        (data_size,) = struct.unpack("<I", wav[40:44])
        self.assertEqual(chunk_size, len(wav) - 8)         # 입력 길이에서 산출
        self.assertEqual(fmt_size, 16)
        self.assertEqual(audio_fmt, 1)                     # PCM
        self.assertEqual(channels, 1)                      # mono
        self.assertEqual(rate, 16000)                      # ★ NC-3 가 겨냥하는 필드
        self.assertEqual(bits, 16)
        self.assertEqual(block_align, channels * bits // 8)
        self.assertEqual(byte_rate, rate * block_align)
        self.assertEqual(data_size, len(pcm))              # 하드코딩이면 여기서 깨진다

    def test_wav_size_fields_track_a_different_length(self) -> None:
        """길이가 다른 입력에서도 산출된다 — 한 길이에 맞춘 하드코딩 헤더 검출용."""
        from ..stt import wav_from_pcm16

        short, long = _pcm16_sine(160), _pcm16_sine(16000)
        for pcm in (short, long):
            wav = wav_from_pcm16(pcm)
            self.assertEqual(struct.unpack("<I", wav[40:44])[0], len(pcm))
            self.assertEqual(struct.unpack("<I", wav[4:8])[0], len(wav) - 8)

    def test_odd_length_pcm_is_rejected_not_silently_truncated(self) -> None:
        """프레임 경계에 맞지 않는 입력 = 조용한 손상 대신 예외."""
        from ..stt import wav_from_pcm16

        with self.assertRaises(ValueError):
            wav_from_pcm16(b"\x01\x02\x03")

    def test_csr_receives_wav_not_raw_pcm(self) -> None:
        """T4 — wire 로 나가는 본문이 WAV 다. raw PCM 직송은 미검증 경로(30.9)."""
        self._seed_pending("regr-stt-wav")
        _, captured = self._run_enrich_real(
            "regr-stt-wav", lambda: _FakeResponse({"text": "택배 왔습니다"})
        )
        kind, body = captured[0]
        self.assertEqual(kind, "csr")
        self.assertEqual(body[0:4], b"RIFF")
        self.assertEqual(len(body), 44 + len(self.pcm))

    def test_csr_request_carries_lang_and_credential_headers(self) -> None:
        """요청 조립 — lang 쿼리 + 헤더 2종. 값 SSoT = 30.9 왕복 실측."""
        from ..constants import STT_CLIENT_ID_HEADER, STT_CLIENT_SECRET_HEADER
        from ..stt import build_request

        req = build_request(b"RIFFwav", "id-not-real", "secret-not-real")
        self.assertTrue(req.full_url.endswith("/recog/v1/stt?lang=Kor"))
        self.assertEqual(req.get_method(), "POST")
        # urllib 은 헤더 이름을 capitalize 해 보관한다 — 이름 자체를 대조한다.
        headers = {k.lower(): v for k, v in req.header_items()}
        self.assertEqual(headers[STT_CLIENT_ID_HEADER.lower()], "id-not-real")
        self.assertEqual(headers[STT_CLIENT_SECRET_HEADER.lower()], "secret-not-real")
        self.assertEqual(headers["content-type"], "application/octet-stream")

    # ── T1: 성공 경로 ────────────────────────────────────────────────────
    def test_real_transcript_reaches_kakao_caption(self) -> None:
        """STT 성공 → CSR → feed → text 3요청, 자막은 **실 인식 문자열**.

        ★ NC-4 함정 대응: _caption_from_stt 를 우회해 원문을 그대로 넘기는 변형은
          가공이 항등인 입력에서는 무해하다. 그래서 앞뒤 공백이 있는 CSR 응답을 골라
          **가공이 실제로 값을 바꾸게** 만든다(" … " → strip).
        """
        self._seed_pending("regr-stt-ok")
        body, captured = self._run_enrich_real(
            "regr-stt-ok", lambda: _FakeResponse({"text": "  옆집 사람인데 잠깐 나와 보실래요?  "})
        )
        self.assertEqual(self._kinds(captured), ["csr", "kakao", "kakao"])
        self.assertEqual(
            [t["object_type"] for _, t in captured[1:]], ["feed", "text"]
        )
        # 우회 변형이면 여기서 공백이 남는다.
        self.assertEqual(captured[2][1]["text"], "옆집 사람인데 잠깐 나와 보실래요?")
        # mock 문구가 아니다 — 실 소스로 갈아탄 것이 이 대조로 증명된다.
        from ..utils import _MOCK_TRANSCRIPTS

        self.assertNotIn(captured[2][1]["text"], _MOCK_TRANSCRIPTS)
        self.assertEqual(body["stt"]["transcript"], "옆집 사람인데 잠깐 나와 보실래요?")
        st = self._status(body)
        self.assertTrue(st["secondary_sent"])
        self.assertEqual(st["enrich_status"], "completed")

    # ── T1 · NC-1: 실패는 전부 "자막 부재"로 합류한다 ────────────────────
    #
    # ★ NC-1 함정: enrich_status 만 검사하면 "failed 로 올리는" 변형이 부분적으로만
    #   잡힌다. secondary_sent 와 secondary_sent_at 까지 함께 고정해야 4조합 표현이
    #   무너지는 것을 검출한다(7.6(d): derive() 가 secondary_sent 를 먼저 본다).
    def _assert_caption_absent_path(self, body, captured, *, expect_csr=True):
        """자막 부재 경로 = CSR 1회(선택) + feed 1건, text 없음, 상태는 완전 성공."""
        expected = (["csr"] if expect_csr else []) + ["kakao"]
        self.assertEqual(self._kinds(captured), expected)
        self.assertEqual(captured[-1][1]["object_type"], "feed")
        st = self._status(body)
        self.assertTrue(st["secondary_sent"])            # ← NC-1 이 겨냥
        self.assertIsNotNone(st["secondary_sent_at"])    # ← NC-1 이 겨냥
        self.assertEqual(st["enrich_status"], "completed")
        self.assertNotEqual(st["enrich_status"], "failed")
        self.assertIsNone(body["stt"])

    def test_empty_transcript_is_caption_absent_not_failed(self) -> None:
        """T1 (1/4) — 빈 인식 결과(무음 클립)."""
        self._seed_pending("regr-stt-empty")
        body, captured = self._run_enrich_real(
            "regr-stt-empty", lambda: _FakeResponse({"text": "   "})
        )
        self._assert_caption_absent_path(body, captured)

    def test_api_error_is_caption_absent_not_failed(self) -> None:
        """T1 (2/4) — CSR 5xx."""
        self._seed_pending("regr-stt-5xx")
        err = urllib.error.HTTPError(
            KAKAO_MEMO_URL_FOR_TEST, 500, "server error", {}, None
        )
        body, captured = self._run_enrich_real("regr-stt-5xx", err)
        self._assert_caption_absent_path(body, captured)

    def test_timeout_is_caption_absent_not_failed(self) -> None:
        """T1 (3/4) — 소켓 타임아웃."""
        self._seed_pending("regr-stt-timeout")
        body, captured = self._run_enrich_real("regr-stt-timeout", TimeoutError())
        self._assert_caption_absent_path(body, captured)

    def test_auth_refusal_is_caption_absent_not_failed(self) -> None:
        """T1 (4/4) — CSR 401. 카카오 401 과 달리 2차 발송을 막지 않는다."""
        self._seed_pending("regr-stt-401")
        err = urllib.error.HTTPError(KAKAO_MEMO_URL_FOR_TEST, 401, "unauthorized", {}, None)
        body, captured = self._run_enrich_real("regr-stt-401", err)
        self._assert_caption_absent_path(body, captured)

    def test_malformed_response_is_caption_absent_not_failed(self) -> None:
        """T1 (보강) — 200 인데 text 키가 없는 계약 위반 응답."""
        self._seed_pending("regr-stt-nokey")
        body, captured = self._run_enrich_real(
            "regr-stt-nokey", lambda: _FakeResponse({"result": "?"})
        )
        self._assert_caption_absent_path(body, captured)

    # ── T3 · NC-2: 재시도 없음 ───────────────────────────────────────────
    def test_failed_csr_call_is_not_retried(self) -> None:
        """T3 — 실패해도 CSR 호출은 1회다.

        ★ NC-2 함정: 성공 케이스에서는 재시도 루프를 넣어도 호출이 1회라 무해하게
          통과한다. **실패 케이스에서 호출 횟수를 세야** 잡힌다. 15초 단위 과금이라
          재시도 1회 = 과금·한도 소진 2배다(30.9).
        """
        self._seed_pending("regr-stt-noretry")
        _, captured = self._run_enrich_real("regr-stt-noretry", TimeoutError())
        self.assertEqual(self._kinds(captured).count("csr"), 1)

    def test_no_backoff_constant_exists(self) -> None:
        """재시도가 없으므로 백오프 상수도 없다(죽은 상수 회피, §5 Step 1-d)."""
        from .. import constants

        self.assertEqual(
            [n for n in dir(constants) if "BACKOFF" in n or "STT_MAX_ATTEMPTS" in n], []
        )

    # ── T2 · T5: 미호출 상태는 성공·실패와 갈린다 ────────────────────────
    def test_credentials_absent_keeps_mock_caption_and_skips_csr(self) -> None:
        """T5 — 자격증명 미설정이면 CSR 을 부르지 않고 mock 자막이 그대로 나간다.

        ⚠️ 위임 §5 Step 4-b 는 "자격증명 미설정 → 자막 부재 경로"를 요구했으나, 기존
          mock/real 게이트 컨벤션(model_serving: MODEL_PATH 미설정 = mock 유지)을
          따르면 미설정은 **real 모드 진입 자체가 없는 상태**라 자막 부재가 아니라
          기존 mock 경로다. 학습 16(기존 컨벤션 우선)에 따라 컨벤션을 택했고,
          "자격증명 없이 transcribe 를 부르면 SttAuthError" 계약은 아래 케이스가
          따로 고정한다.
        """
        from .. import stt as stt_mod

        self._seed_pending("regr-stt-nocreds")
        side_effect, captured = self._csr_and_kakao(
            lambda: _FakeResponse({"text": "불려서는 안 되는 값"})
        )
        with self.app.app_context(), mock.patch.dict(
            self.app.config, {"NCP_CLIENT_ID": "", "NCP_CLIENT_SECRET": ""}
        ), mock.patch(
            "app.kakao.get_access_token", return_value=_FAKE_ACCESS_TOKEN
        ), mock.patch(
            "app.kakao.urllib.request.urlopen", side_effect=side_effect
        ), mock.patch.object(
            stt_mod, "transcribe", wraps=stt_mod.transcribe
        ) as transcribe:
            r = self._enrich("regr-stt-nocreds")
            self.assertEqual(r.status_code, 200)
            body = r.get_json()

        transcribe.assert_not_called()                       # T2: 미호출
        self.assertNotIn("csr", self._kinds(captured))
        from ..utils import _MOCK_TRANSCRIPTS

        self.assertIn(body["stt"]["transcript"], _MOCK_TRANSCRIPTS)  # T5: mock 유지
        self.assertEqual(self._status(body)["enrich_status"], "completed")

    def test_half_credentials_is_not_real_mode(self) -> None:
        """NC-5(자체) — 한쪽만 설정된 상태로 real 모드에 들어가면 401 왕복만 태운다."""
        from .. import stt as stt_mod

        with self.app.app_context():
            for creds in (
                {"NCP_CLIENT_ID": "id-not-real", "NCP_CLIENT_SECRET": ""},
                {"NCP_CLIENT_ID": "", "NCP_CLIENT_SECRET": "secret-not-real"},
                {"NCP_CLIENT_ID": "", "NCP_CLIENT_SECRET": ""},
            ):
                with mock.patch.dict(self.app.config, creds):
                    self.assertFalse(stt_mod.is_real_mode())
            with mock.patch.dict(self.app.config, self._FAKE_NCP_CREDS):
                self.assertTrue(stt_mod.is_real_mode())

    def test_transcribe_without_credentials_raises_auth_error(self) -> None:
        """Step 1-f 계약 — 자격증명 없이 부르면 예외(호출부가 자막 부재로 흡수)."""
        from .. import stt as stt_mod

        with self.app.app_context(), mock.patch.dict(
            self.app.config, {"NCP_CLIENT_ID": "", "NCP_CLIENT_SECRET": ""}
        ):
            with self.assertRaises(stt_mod.SttAuthError):
                stt_mod.transcribe(self.pcm)

    def test_audio_part_missing_skips_stt_entirely(self) -> None:
        """T2 — 오디오 부재는 /enrich 게이트에서 400 이라 STT 에 도달하지 않는다.

        ⚠️ 위임 §5 Step 4-b 의 "오디오 부재 → STT 미호출"은 이 형태로만 실재한다:
          /enrich 는 오디오 파트를 **required** 로 받으므로(routes.enrich), "오디오
          없이 본문 처리에 들어가는" 상태는 코드에 존재하지 않는다.
        """
        from .. import stt as stt_mod

        self._seed_pending("regr-stt-noaudio")
        with self.app.app_context(), mock.patch.dict(
            self.app.config, self._FAKE_NCP_CREDS
        ), mock.patch.object(stt_mod, "transcribe") as transcribe:
            r = self.client.post(
                "/api/v1/enrich",
                headers={"Authorization": f"Bearer {_DEVICE_TOKEN}"},
                data={
                    "client_request_id": "regr-stt-noaudio",
                    "image": (io.BytesIO(self._JPEG), "a.jpg"),
                },
                content_type="multipart/form-data",
            )
        self.assertEqual(r.status_code, 400)
        transcribe.assert_not_called()

    # ── 예외 계층 · 응답 파싱 (NC-6 · NC-7 자체 설계) ────────────────────
    def test_error_layers_are_distinguishable(self) -> None:
        """NC-6(자체) — 인증 거부와 그 외 실패가 같은 예외로 뭉개지지 않는다.

        뭉개지면 로그에서 "자격증명이 틀렸다"와 "네트워크가 흔들렸다"가 구분되지 않아
        운영 중 원인 규명이 불가능해진다(kakao 의 Token/Send 2계층과 같은 이유).
        """
        from .. import stt as stt_mod

        cases = {
            401: stt_mod.SttAuthError,
            403: stt_mod.SttAuthError,
            500: stt_mod.SttRequestError,
            429: stt_mod.SttRequestError,
        }
        for code, expected in cases.items():
            err = urllib.error.HTTPError(KAKAO_MEMO_URL_FOR_TEST, code, "x", {}, None)
            with self.app.app_context(), mock.patch.dict(
                self.app.config, self._FAKE_NCP_CREDS
            ), mock.patch("app.stt.urllib.request.urlopen", side_effect=err):
                with self.assertRaises(expected):
                    stt_mod.transcribe(self.pcm)
        # 두 계층이 서로를 삼키지 않는다(한쪽이 다른 쪽의 부모면 위 대조가 무의미해진다)
        self.assertFalse(issubclass(stt_mod.SttAuthError, stt_mod.SttRequestError))
        self.assertFalse(issubclass(stt_mod.SttRequestError, stt_mod.SttAuthError))

    def test_parse_transcript_does_not_swallow_contract_breaks(self) -> None:
        """NC-7(자체) — text 키 부재를 "자막 없음"으로 흡수하면 스펙 변경이 무음이 된다."""
        from .. import stt as stt_mod

        self.assertEqual(stt_mod.parse_transcript(b'{"text": " \xea\xb0\x80 "}'), "가")
        self.assertEqual(stt_mod.parse_transcript(b'{"text": ""}'), "")
        with self.assertRaises(stt_mod.SttRequestError):
            stt_mod.parse_transcript(b'{"result": 0}')
        with self.assertRaises(stt_mod.SttRequestError):
            stt_mod.parse_transcript(b"not json")

    def test_secrets_do_not_leak_into_logs(self) -> None:
        """NC-8(자체) — 자격증명 값과 인식 전문이 로그에 남지 않는다(§7 시크릿 제약).

        transcript 전문이 로그에 흐르면 방문자 발화가 서버 로그에 영구 기록된다.
        """
        from .. import stt as stt_mod

        secret_text = "여기는 로그에 남으면 안 되는 발화입니다"
        with self.app.app_context(), mock.patch.dict(
            self.app.config, self._FAKE_NCP_CREDS
        ), mock.patch(
            "app.stt.urllib.request.urlopen",
            side_effect=lambda req, timeout=None: _FakeResponse({"text": secret_text}),
        ), self.assertLogs(self.app.logger, level="INFO") as logs:
            self.assertEqual(stt_mod.transcribe(self.pcm), secret_text)

        blob = "\n".join(logs.output)
        self.assertNotIn(secret_text, blob)
        self.assertNotIn(self._FAKE_NCP_CREDS["NCP_CLIENT_ID"], blob)
        self.assertNotIn(self._FAKE_NCP_CREDS["NCP_CLIENT_SECRET"], blob)
        self.assertIn("transcript_len=", blob)  # 길이는 남는다(성공 여부 추적용)

    def test_stt_timeout_constant_fits_secondary_budget(self) -> None:
        """§5 Step 2-b 역산 검산 — 최악 총합이 2차 예산 15초 안이다.

        입력은 전부 실측·문서 인용값이다(7.6(f) 7.5초 / 7.6(h) 2.61초 / 7.3 490ms).
        ⚠️ ESP32 캡처·업로드 구간은 미측정이라 이 검산은 **서버측 구간 기준**이다.
        """
        from ..constants import KAKAO_HTTP_TIMEOUT_SECONDS, STT_HTTP_TIMEOUT_SECONDS

        kakao_worst = KAKAO_HTTP_TIMEOUT_SECONDS * 5      # 토큰 1 + 사진 2 + 자막 2
        server_side = 2.61 - 0.49 * 2                     # 7.6(h) − 카카오 정상 왕복분
        worst = kakao_worst + server_side + STT_HTTP_TIMEOUT_SECONDS
        self.assertLess(worst, 15.0)
        self.assertGreater(STT_HTTP_TIMEOUT_SECONDS, 0.892)  # CSR 왕복 실측을 자르지 않는다

    def test_caption_always_passes_through_caption_from_stt(self) -> None:
        """NC-4 — 자막은 소스가 무엇이든 _caption_from_stt 가공을 거쳐 나간다.

        ★ NC-4 함정 정면 대응: 실 CSR 경로에서는 stt.parse_transcript 가 경계에서 이미
          strip 해 넘기므로 _caption_from_stt 의 가공이 **항등**이 된다 — 그 경로만 보면
          "가공을 우회하는" 변형이 무해하게 통과한다(2026-09-08 실측: 우회 변형을 심고
          돌렸더니 82건 전건 OK). 가공이 실제로 값을 바꾸는 입력은 가공되지 않은 소스
          쪽에 있으므로, mock 소스에 앞뒤 공백을 실어 **wire 로** 검사한다.
        """
        self._seed_pending("regr-stt-nc4")
        captured = []

        def _capture(req, timeout=None):
            form = urllib.parse.parse_qs(req.data.decode("utf-8"))
            captured.append(json.loads(form["template_object"][0]))
            return _FakeResponse({"result_code": 0})

        with self.app.app_context(), mock.patch.dict(
            self.app.config, {"NCP_CLIENT_ID": "", "NCP_CLIENT_SECRET": ""}
        ), mock.patch(
            "app.routes.mock_enrichment", side_effect=self._stt("  가공 전 자막  ")
        ), mock.patch(
            "app.kakao.get_access_token", return_value=_FAKE_ACCESS_TOKEN
        ), mock.patch("app.kakao.urllib.request.urlopen", side_effect=_capture):
            r = self._enrich("regr-stt-nc4")
            self.assertEqual(r.status_code, 200)

        self.assertEqual([t["object_type"] for t in captured], ["feed", "text"])
        # 우회 변형이면 앞뒤 공백이 그대로 카카오로 나간다.
        self.assertEqual(captured[1]["text"], "가공 전 자막")

    def test_stt_wiring_does_not_change_to_dict_contract(self) -> None:
        """§2 제약 — 실 STT 경로에서도 to_dict() 최상위 키 11개 / 상태값 집합 불변."""
        self._seed_pending("regr-stt-keys")
        body, _ = self._run_enrich_real(
            "regr-stt-keys", lambda: _FakeResponse({"text": "택배 왔습니다"})
        )
        self.assertEqual(len(body), 11)
        self.assertEqual(sorted(body.keys()), sorted(_NOTIFICATION_ITEM_KEYS))
        self.assertIn(
            self._status(body)["enrich_status"], ("completed", "skipped", "failed", "pending")
        )
        self.assertEqual(
            sorted(body["stt"]), ["confidence", "language", "processed_at", "transcript"]
        )

if __name__ == "__main__":
    unittest.main()
