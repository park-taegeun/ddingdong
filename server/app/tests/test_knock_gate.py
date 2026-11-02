"""노크 단일 타격 차단(knock_gate) 회귀 (stdlib unittest).

실행(server/ 에서):  python3 -m unittest app.tests.test_knock_gate

- 순수 함수: strong_hits(뚜렷한 타격 — 비율 · 억제 · 경계 · 결정성) / judge(대상 · 사유 보존 · fail-open).
- 합성 포락선 3종: 2026-11-02 랩실 대조 측정(constants 「노크 단일 타격 차단」 근거)의 모양 —
  노크 3타 = 3 · 노크 1타 = 1 · 툭(큰 한 번 + 바로 뒤 되튐 + 작은 소리) = 1(raw 후보 · env_max 로는 못 가름).
- /detect 관통: 2타 발송 · 1타 차단(1 · 2차 없음) · 앞선 사유 보존 · doorbell 대상 아님 · 계산 예외 = 발송 + ERROR ·
  knock_rhythm_probes 행 불변 · /stats 새 키.

외부 연결 가드: test_knock_rhythm 선례대로 test_detect_regression 의 가드를 import 하고 자기 setUpModule 로
설치한다. /detect 헬퍼(_DetectCase)는 test_registration 것을 그대로 쓴다. 새 테이블 없음.
"""

from __future__ import annotations

import io
import unittest
from unittest import mock

import numpy as np
from sqlalchemy import text

from .. import knock_gate, knock_rhythm
from ..constants import KNOCK_STRONG_HIT_RATIO, SKIP_REASON_KNOCK_SINGLE_HIT
from .test_detect_regression import (
    _DEVICE_TOKEN,
    _NoNetworkTestCase,
    _install_network_guard,
    _uninstall_network_guard,
)
from .test_registration import _VOLATILE, _DetectCase

_SR = 16000
_N = 32768  # 2.048 초 = 보드 자동 창


def setUpModule() -> None:
    _install_network_guard()


def tearDownModule() -> None:
    _uninstall_network_guard()


# ── 합성 입력(test_knock_rhythm 과 같은 타격 모양) ──────────────────────────
def _pcm_of(strikes, seed=0):
    """strikes = [(초, 진폭, 길이, 감쇠)] → int16 LE PCM."""
    x = np.random.default_rng(seed).integers(-30, 31, _N)
    for t, amp, length, tau in strikes:
        i = int(t * _SR)
        x[i:i + length] += (amp * np.exp(-np.arange(length) / tau) * np.sin(np.arange(length))).astype(np.int64)
    return np.clip(x, -32768, 32767).astype("<i2").tobytes()


def _knock(*times):
    return _pcm_of([(t, 8000, 800, 320) for t in times])


KNOCK3 = _knock(0.5, 0.82, 1.14)  # 간격 320 ms(대조 측정 280 ~ 360)
KNOCK2 = _knock(0.5, 0.8)
KNOCK1 = _knock(1.0)
# 툭 = 더 큰 한 번 + 60 ms 뒤 되튐(억제 안) + 비율 0.5 미만 작은 소리 2개
TUK = _pcm_of([(1.0, 16000, 1600, 200), (1.06, 6000, 800, 320), (1.4, 3000, 800, 320), (1.7, 2500, 800, 320)], seed=3)


def _s50(pcm):
    return len(knock_gate.strong_hits(knock_rhythm.measure(pcm)["peaks"]))


class StrongHitsUnitTest(_NoNetworkTestCase):
    """순수 함수 — 앱 · DB 없음."""

    def test_three_hits(self):
        peaks = [[500, 1.0], [508, 0.6], [750, 0.9], [1000, 0.8]]
        self.assertEqual(knock_gate.strong_hits(peaks), [500, 750, 1000])

    def test_one_hit_with_ripples(self):
        self.assertEqual(knock_gate.strong_hits([[1000, 1.0], [1008, 0.7], [1100, 0.55]]), [1000])

    def test_two_hits_300ms(self):
        self.assertEqual(knock_gate.strong_hits([[500, 1.0], [800, 0.7]]), [500, 800])

    def test_two_peaks_within_100ms_are_one(self):  # NC-KG4 대상
        self.assertEqual(knock_gate.strong_hits([[500, 1.0], [600, 0.9]]), [500])

    def test_ratio_below_half_is_excluded(self):
        self.assertEqual(knock_gate.strong_hits([[500, 1.0], [800, 0.4]]), [500])

    def test_empty(self):
        self.assertEqual(knock_gate.strong_hits([]), [])

    def test_boundaries_are_inclusive(self):
        # 비율 == 0.5 는 남고, 간격 == 150 ms 는 따로 센다(≥).
        self.assertEqual(knock_gate.strong_hits([[500, 1.0], [650, 0.5]]), [500, 650])

    def test_equal_heights_keep_earlier(self):
        self.assertEqual(knock_gate.strong_hits([[600, 0.8], [500, 0.8], [1000, 1.0]]), [500, 1000])

    def test_rule_stays_inside_recorded_candidates(self):
        # 계측은 비율 ≥ R_MIN 만 남긴다 — 판정 비율이 그보다 낮으면 같은 기록으로 다시 셀 수 없다.
        self.assertGreaterEqual(KNOCK_STRONG_HIT_RATIO, knock_rhythm.R_MIN)
        self.assertEqual(knock_rhythm.GAP_MS, 0)


class JudgeUnitTest(_NoNetworkTestCase):
    def test_knock_sent_below_two_is_blocked(self):
        self.assertEqual(knock_gate.judge("knock", True, [1000]), SKIP_REASON_KNOCK_SINGLE_HIT)
        self.assertEqual(knock_gate.judge("knock", True, []), SKIP_REASON_KNOCK_SINGLE_HIT)

    def test_knock_two_or_more_passes(self):
        self.assertIsNone(knock_gate.judge("knock", True, [500, 800]))

    def test_not_judged(self):
        for args in (("knock", False, [1000]), ("doorbell", True, [1000]), ("fire_alarm", True, []),
                     ("knock", True, None)):
            with self.subTest(args):
                self.assertIsNone(knock_gate.judge(*args))


class ContrastShapesTest(_NoNetworkTestCase):
    """대조 측정 3종의 모양을 합성으로 재현 — 측정 함수(knock_rhythm.measure) 실물을 거친다."""

    def test_knock3_knock1_tuk(self):
        self.assertEqual((_s50(KNOCK3), _s50(KNOCK2), _s50(KNOCK1), _s50(TUK)), (3, 2, 1, 1))

    def test_raw_candidates_and_env_max_do_not_separate(self):
        k, t = knock_rhythm.measure(KNOCK3), knock_rhythm.measure(TUK)
        self.assertGreater(t["peak_count"], k["peak_count"])  # 툭이 후보는 더 많다
        self.assertGreater(t["env_max"], k["env_max"])  # 툭이 더 크다


class DetectGateTest(_DetectCase):
    """/detect 관통 — 등록 판정 뒤 · 카카오 앞."""

    def setUp(self) -> None:
        super().setUp()
        self.db.session.execute(text("DELETE FROM knock_rhythm_probes"))
        self.db.session.commit()

    def _send(self, *a, **kw):
        """(resp, send mock). 카카오 1차 대역은 진짜 _assert_commit_is_safe() 를 부른 뒤 성공."""
        from .. import kakao

        real_guard = kakao._assert_commit_is_safe

        def fake_send(predicted_class, client_request_id=None):
            real_guard()
            return None

        with mock.patch("app.kakao.send_primary_text", side_effect=fake_send) as send:
            resp = self._detect(*a, **kw)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))
        return resp, send

    @staticmethod
    def _st(resp):
        return resp.get_json()["notification_status"]

    def _probe(self, resp):
        from ..models import KnockRhythmProbe, Notification

        self.db.session.expire_all()
        notif = self.db.session.query(Notification).filter_by(
            client_request_id=resp.get_json()["client_request_id"]
        ).one()
        return self.db.session.query(KnockRhythmProbe).filter_by(notification_id=notif.id).one()

    def test_two_hits_are_sent(self):
        resp, send = self._send(KNOCK2, confidence=0.9, cls="knock")
        self.assertTrue(self._st(resp)["primary_sent"])
        self.assertNotIn("skip_reason", self._st(resp))
        send.assert_called_once_with("knock", mock.ANY)

    def test_single_hit_is_blocked_both_stages(self):  # NC-KG1 대상
        for name, pcm in (("knock1", KNOCK1), ("tuk", TUK)):
            with self.subTest(name):
                resp, send = self._send(pcm, confidence=0.9, cls="knock")
                st = self._st(resp)
                self.assertFalse(st["primary_sent"])
                self.assertIsNone(st["primary_sent_at"])
                self.assertEqual(st["skip_reason"], SKIP_REASON_KNOCK_SINGLE_HIT)
                self.assertEqual(st["enrich_status"], "skipped")  # 보드 2차 게이트
                send.assert_not_called()
                crid = resp.get_json()["client_request_id"]
                self.assertEqual(resp.get_json(), self._stored_notification(crid))  # 응답 = 저장 행
                # 2차가 와도 서버가 받지 않는다(종결 상태) — 사진 발송 호출 0
                with mock.patch("app.kakao.send_secondary") as sec:
                    r2 = self.client.post(
                        "/api/v1/enrich",
                        headers={"Authorization": f"Bearer {_DEVICE_TOKEN}"},
                        data={"client_request_id": crid,
                              "image": (io.BytesIO(b"\xff\xd8" + b"\x00" * 64), "a.jpg"),
                              "audio": (io.BytesIO(pcm), "a.pcm")},
                        content_type="multipart/form-data",
                    )
                self.assertEqual(r2.status_code, 409)
                sec.assert_not_called()

    def test_earlier_reasons_are_kept(self):  # NC-KG5 대상
        for name, kw, reason in (
            ("low_confidence", dict(confidence=0.5), "low_confidence"),
            ("tof_rejected", dict(confidence=0.9, tof_presence="false"), "tof_rejected"),
        ):
            with self.subTest(name):
                resp, send = self._send(KNOCK1, cls="knock", **kw)
                self.assertEqual(self._st(resp)["skip_reason"], reason)
                send.assert_not_called()

    def test_doorbell_single_hit_is_not_judged(self):  # NC-KG2 대상
        resp, send = self._send(KNOCK1, confidence=0.9, cls="doorbell")
        self.assertTrue(self._st(resp)["primary_sent"])
        send.assert_called_once_with("doorbell", mock.ANY)

    def test_measure_error_fails_open_with_one_error_line(self):  # NC-KG3 대상
        with mock.patch("app.knock_gate.measure", side_effect=RuntimeError("boom")), \
                self.assertLogs(self.app.logger, "ERROR") as logs:
            resp, send = self._send(KNOCK1, confidence=0.9, cls="knock")
        self.assertTrue(self._st(resp)["primary_sent"])
        send.assert_called_once_with("knock", mock.ANY)
        self.assertEqual(len(logs.output), 1)
        self.assertIn("knock gate failed", logs.output[0])
        self.assertIn(resp.get_json()["client_request_id"], logs.output[0])
        self.assertIsNone(self._probe(resp).error)  # 계측은 자기 measure 로 정상 기록

    def test_probe_rows_are_unchanged_by_gate(self):
        """차단 · 발송 양쪽에서 knock_rhythm_probes 행 = measure(pcm) 그대로(판정 전과 같은 값)."""
        for name, pcm in (("blocked", KNOCK1), ("sent", KNOCK3)):
            with self.subTest(name):
                resp, _ = self._send(pcm, confidence=0.9, cls="knock")
                p, m = self._probe(resp), knock_rhythm.measure(pcm)
                self.assertEqual(
                    (p.peaks, p.peak_count, p.env_max, p.mask_samples, p.error, p.params),
                    (m["peaks"], m["peak_count"], m["env_max"], m["mask_samples"], None, knock_rhythm.PARAMS),
                )

    def test_blocked_matches_gate_off_except_reason(self):
        """게이트를 끈 같은 요청과 비교 — 바뀌는 것은 발송 3필드 + 사유뿐."""

        def body(gate_on):
            if gate_on:
                resp, _ = self._send(KNOCK1, confidence=0.9, cls="knock")
            else:
                with mock.patch("app.routes.knock_gate.before_send", return_value=None) as g:
                    resp, _ = self._send(KNOCK1, confidence=0.9, cls="knock")
                g.assert_called_once()
            out = {k: v for k, v in resp.get_json().items() if k not in _VOLATILE}
            st = dict(out.pop("notification_status"))
            for k in ("primary_sent", "primary_sent_at", "enrich_status", "skip_reason"):
                st.pop(k, None)
            return out, st

        self.assertEqual(body(True), body(False))

    def test_stats_counts_new_key(self):
        def stats():
            r = self.client.get("/api/v1/stats?period=today", headers=self._auth())
            self.assertEqual(r.status_code, 200)
            return r.get_json()["skip_reasons"]

        before = stats()
        self.assertIn(SKIP_REASON_KNOCK_SINGLE_HIT, before)
        self._send(KNOCK1, confidence=0.9, cls="knock")
        self.assertEqual(stats()[SKIP_REASON_KNOCK_SINGLE_HIT], before[SKIP_REASON_KNOCK_SINGLE_HIT] + 1)


if __name__ == "__main__":
    unittest.main()
