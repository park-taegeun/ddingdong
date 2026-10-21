"""노크 타격 리듬 계측(knock_rhythm) 회귀 (stdlib unittest). 계측용 — 판정 기준 아님.

실행(server/ 에서):  python3 -m unittest app.tests.test_knock_rhythm

- 순수 함수: 합성 3타 · 단타 · 무음 · 글리치만 · 짧은 입력. 기록한 후보(r ≥ R_MIN · 억제 없음)에서
  오프라인 상위 규칙(r 0.3 · 억제 100 ms)을 다시 계산할 수 있는지도 본다.
- 마스크 복제 대조: ml/curation/slice_direct.py 원문을 ast 로 떼어 상수 · 본문 · 출력을 비교한다
  (ml 패키지는 import 하지 않는다 — test_serving_level 선례). 한쪽만 바꾸면 FAIL.
- /detect 통합: 예측 knock → 1행(발송 여부 무관) · 다른 클래스 → 0행 · 계산 예외 → 실패 행 ·
  카카오 순서 가드 · 판정 불변(훅 유무로 응답 본문 · 저장 행 · 카카오 호출이 같다).

외부 연결 가드: test_registration 선례대로 test_detect_regression 의 가드를 import 하고
자기 setUpModule 로 설치한다. /detect 헬퍼(_DetectCase)는 test_registration 것을 그대로 쓴다.
"""

from __future__ import annotations

import ast
import inspect
import io
import json
import socket
import unittest
from itertools import groupby
from pathlib import Path
from unittest import mock

import numpy as np
from sqlalchemy import text

from .. import knock_rhythm
from .test_detect_regression import (
    _NET_ATTEMPTS,
    _NoNetworkTestCase,
    _install_network_guard,
    _uninstall_network_guard,
)
from .test_registration import _VOLATILE, _DetectCase

_ML_SLICE_DIRECT = Path(__file__).resolve().parents[3] / "ml" / "curation" / "slice_direct.py"
_SR = 16000
_N = 32768  # 2.048 초 = 보드 자동 창
_STRIKES_S = (0.5, 0.75, 1.0)


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


# ── 합성 입력(오프라인 knock_hits.py selftest 와 같은 모양) ─────────────────────
def _noise(seed=0):
    return np.random.default_rng(seed).integers(-30, 31, _N)


def _strike(x, t_s):
    i = int(t_s * _SR)
    x[i:i + 800] += (8000 * np.exp(-np.arange(800) / 320) * np.sin(np.arange(800))).astype(np.int64)


def _pcm(x):
    return np.clip(x, -32768, 32767).astype("<i2").tobytes()


def _three_hits(glitch_at_s=None):
    x = _noise()
    for t in _STRIKES_S:
        _strike(x, t)
    if glitch_at_s is not None:
        x[int(glitch_at_s * _SR)] = 32767  # 고립 1샘플 클램프 글리치
    return _pcm(x)


def _select(peaks, r, gmin_ms):
    """기록 후보 → 오프라인 hits(r, gmin) 와 같은 선택(높은 순 억제 → 시각순 ms)."""
    kept = []
    for t, h in sorted((p for p in peaks if p[1] >= r), key=lambda p: -p[1]):
        if all(abs(t - q) >= gmin_ms for q in kept):
            kept.append(t)
    return sorted(kept)


class NetworkGuardSelfTest(_NoNetworkTestCase):
    """이 모듈에서도 가드가 살아 있음을 매 실행 증명한다."""

    def test_connection_attempt_is_refused_and_recorded(self):
        with self.assertRaises(ConnectionRefusedError):
            socket.create_connection(("127.0.0.1", 9), timeout=0.1)
        self.assertEqual(_NET_ATTEMPTS, ["127.0.0.1:9"])
        _NET_ATTEMPTS.clear()


class MeasureUnitTest(_NoNetworkTestCase):
    """순수 함수 — DB · 앱 없음."""

    def test_three_hits_recomputable_at_offline_reference_rule(self):
        m = knock_rhythm.measure(_three_hits())
        hits = _select(m["peaks"], 0.3, 100)
        self.assertEqual(len(hits), 3, m["peaks"])
        for got, want in zip(hits, _STRIKES_S):
            self.assertLessEqual(abs(got - want * 1000), 16)
        self.assertEqual(m["peak_count"], len(m["peaks"]))
        self.assertTrue(all(knock_rhythm.R_MIN <= h <= 1.0 for _, h in m["peaks"]))
        self.assertEqual([t for t, _ in m["peaks"]], sorted(t for t, _ in m["peaks"]))
        self.assertEqual(max(h for _, h in m["peaks"]), 1.0)

    def test_candidates_are_not_suppressed(self):
        # 48 ms 간격 두 타격 — 기록에는 둘 다 남고, 억제 100 ms 로 다시 계산하면 하나로 묶인다.
        x = _noise(2)
        _strike(x, 0.5)
        _strike(x, 0.548)
        peaks = knock_rhythm.measure(_pcm(x))["peaks"]
        self.assertEqual(len(_select(peaks, 0.3, 0)), 2, peaks)
        self.assertEqual(len(_select(peaks, 0.3, 100)), 1)

    def test_single_hit(self):
        x = _noise(1)
        x[_SR:_SR + 800] += 8000
        self.assertEqual(len(_select(knock_rhythm.measure(_pcm(x))["peaks"], 0.3, 100)), 1)

    def test_silence(self):
        m = knock_rhythm.measure(bytes(2 * _N))
        self.assertEqual(m, {"peaks": [], "peak_count": 0, "env_max": 0.0, "mask_samples": 0})

    def test_glitch_only_is_masked_out(self):
        x = np.zeros(_N, dtype=np.int64)
        x[10_000] = 32767
        m = knock_rhythm.measure(_pcm(x))
        self.assertEqual(m["peaks"], [])
        self.assertEqual(m["mask_samples"], 1 + 2 * knock_rhythm.CLAMP_MASK_HALF_WIDTH)

    def test_glitch_does_not_add_a_hit(self):
        # 마스크가 없으면 1.6 초 글리치가 4번째 타격으로 잡힌다(오프라인 selftest NC 와 같은 입력).
        m = knock_rhythm.measure(_three_hits(glitch_at_s=1.6))
        self.assertEqual(len(_select(m["peaks"], 0.3, 100)), 3)
        self.assertGreater(m["mask_samples"], 0)

    def test_short_input_has_no_peaks(self):
        m = knock_rhythm.measure(_pcm(np.full(100, 500, dtype=np.int64)))
        self.assertEqual((m["peaks"], m["peak_count"]), ([], 0))

    def test_values_are_plain_json(self):
        m = knock_rhythm.measure(_three_hits(glitch_at_s=1.6))
        self.assertEqual(json.loads(json.dumps(m)), m)
        self.assertTrue(all(type(t) is int and type(h) is float for t, h in m["peaks"]))
        self.assertIs(type(m["env_max"]), float)
        self.assertIs(type(m["mask_samples"]), int)

    def test_params_record_definition(self):
        self.assertEqual(
            knock_rhythm.PARAMS,
            {
                "probe_version": knock_rhythm.PROBE_VERSION,
                "sample_rate": 16000,
                "frame": 256,
                "hop": 128,
                "r_min": 0.1,
                "gap_ms": 0,
                "clamp": 32767,
                "clamp_mask_half_width": 32,
                "glitch_max_run": 2,
            },
        )


class MaskReplicaTest(_NoNetworkTestCase):
    """서버 복제 ↔ ml/curation/slice_direct.py 원문(ast)."""

    _NAMES = ("CLAMP", "CLAMP_MASK_HALF_WIDTH", "GLITCH_MAX_RUN")

    @classmethod
    def setUpClass(cls) -> None:
        tree = ast.parse(_ML_SLICE_DIRECT.read_text(encoding="utf-8"))
        cls.lit = {
            n.targets[0].id: ast.literal_eval(n.value)
            for n in tree.body
            if isinstance(n, ast.Assign) and len(n.targets) == 1
            and isinstance(n.targets[0], ast.Name) and n.targets[0].id in cls._NAMES
        }
        cls.ml_def = next(
            n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "mask_glitch_clamps"
        )
        ns = {"groupby": groupby, **cls.lit}
        exec(compile(ast.Module(body=[cls.ml_def], type_ignores=[]), "slice_direct.py", "exec"), ns)
        cls.ml_fn = staticmethod(ns["mask_glitch_clamps"])

    @staticmethod
    def _body(fn_def):
        body = fn_def.body
        if isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            body = body[1:]  # docstring 제외
        return [ast.dump(n) for n in body]

    def test_constants_match(self):
        self.assertEqual(set(self.lit), set(self._NAMES))
        for name in self._NAMES:
            self.assertEqual(getattr(knock_rhythm, name), self.lit[name], name)

    def test_function_body_matches(self):
        server_def = ast.parse(inspect.getsource(knock_rhythm.mask_glitch_clamps)).body[0]
        self.assertEqual(self._body(server_def), self._body(self.ml_def))

    def test_outputs_match(self):
        rng = np.random.default_rng(3)
        cases = {"empty": [], "edges": [32767, 5, 5, 32768, 32768]}
        for run in (1, 2, 3, 40):  # 글리치 런 1 · 2 / 진짜 잘림 3 · 40
            a = rng.integers(0, 2000, 400).tolist()
            a[150:150 + run] = [32767] * run
            a[0] = 32768  # 처음 샘플 클램프(-32768 의 |x|)
            cases[f"run{run}"] = a
        for name, a in cases.items():
            with self.subTest(name):
                self.assertEqual(knock_rhythm.mask_glitch_clamps(a), self.ml_fn(a))


class DetectProbeTest(_DetectCase):
    """/detect 훅 — 예측 knock 만 1행, 발송 · 응답 · 저장 알림은 훅과 무관."""

    def setUp(self) -> None:
        super().setUp()
        self.db.session.execute(text("DELETE FROM knock_rhythm_probes"))
        self.db.session.commit()

    def _probes(self):
        self.db.session.expire_all()
        from ..models import KnockRhythmProbe

        return self.db.session.query(KnockRhythmProbe).order_by(KnockRhythmProbe.id).all()

    def _send(self, *a, **kw):
        """(resp, send mock). 카카오 1차 대역은 진짜 _assert_commit_is_safe() 를 부른 뒤 성공."""
        from .. import kakao

        real_guard = kakao._assert_commit_is_safe

        def fake_send(predicted_class):
            real_guard()
            return None

        with mock.patch("app.kakao.send_primary_text", side_effect=fake_send) as send:
            resp = self._detect(*a, **kw)
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))
        return resp, send

    def _stored(self, resp):
        return self._stored_notification(resp.get_json()["client_request_id"])

    def test_knock_writes_one_row_matching_measure(self):
        pcm = _three_hits()
        resp, send = self._send(pcm, confidence=0.9, cls="knock")
        send.assert_called_once_with("knock")  # 카카오 순서 가드를 실제로 지났다
        (p,) = self._probes()
        from ..models import Notification

        notif = self.db.session.query(Notification).filter_by(
            client_request_id=resp.get_json()["client_request_id"]
        ).one()
        self.assertEqual(p.notification_id, notif.id)
        self.assertEqual(p.created_at, notif.detected_at)  # 같은 now(naive UTC)
        m = knock_rhythm.measure(pcm)
        self.assertEqual(
            (p.peaks, p.peak_count, p.env_max, p.mask_samples),
            (m["peaks"], m["peak_count"], m["env_max"], m["mask_samples"]),
        )
        self.assertEqual((p.probe_version, p.params, p.error), (knock_rhythm.PROBE_VERSION, knock_rhythm.PARAMS, None))
        self.assertGreaterEqual(p.compute_ms, 0)

    def test_knock_recorded_whether_sent_or_not(self):
        cases = {  # 이름 → (요청 인자, 기대 skip_reason)
            "sent": (dict(confidence=0.9), None),
            "low_confidence": (dict(confidence=0.5), "low_confidence"),
            "tof_rejected": (dict(confidence=0.9, tof_presence="false"), "tof_rejected"),
        }
        for name, (kw, skip) in cases.items():
            with self.subTest(name):
                resp, _ = self._send(_three_hits(), cls="knock", **kw)
                self.assertEqual(resp.get_json()["notification_status"].get("skip_reason"), skip)
        self.assertEqual(len(self._probes()), len(cases))

    def test_other_classes_write_nothing(self):
        for cls in ("doorbell", "fire_alarm", "other"):
            with self.subTest(cls):
                self._send(_three_hits(), confidence=0.9, cls=cls)
        self.assertEqual(self._probes(), [])

    def test_idempotent_replay_writes_nothing_more(self):
        self._send(_three_hits(), crid="replay-k", confidence=0.9, cls="knock")
        with mock.patch("app.kakao.send_primary_text") as send:
            resp = self._detect(_three_hits(), crid="replay-k", confidence=0.9, cls="knock")
        self.assertEqual((resp.status_code, resp.headers.get("Idempotent-Replay")), (200, "true"))
        send.assert_not_called()
        self.assertEqual(len(self._probes()), 1)

    def test_measure_failure_writes_failure_row_and_detect_proceeds(self):
        with mock.patch("app.knock_rhythm.measure", side_effect=RuntimeError("boom")), \
                self.assertLogs(self.app.logger, "ERROR") as logs:
            resp, send = self._send(_three_hits(), confidence=0.9, cls="knock")
        send.assert_called_once_with("knock")
        crid = resp.get_json()["client_request_id"]
        self.assertEqual(len(logs.output), 1)  # ERROR 1줄
        self.assertIn(crid, logs.output[0])
        self.assertIn("boom", logs.output[0])  # traceback 포함(logger.exception)
        (p,) = self._probes()
        self.assertEqual(p.error, "RuntimeError: boom")
        self.assertEqual((p.peaks, p.peak_count, p.env_max, p.mask_samples), (None, None, None, None))
        self.assertEqual(self._stored(resp)["client_request_id"], crid)

    def test_judgment_unchanged_by_hook(self):
        """같은 입력 · 같은 예측에서 훅 유무로 응답 본문 · 저장 알림 · 카카오 호출이 같다."""

        def strip(d):
            out = {k: v for k, v in d.items() if k not in _VOLATILE}
            status = dict(out["notification_status"])
            status["primary_sent_at"] = status["primary_sent_at"] is not None  # 발송 완료 시각 = 요청마다 다름
            return {**out, "notification_status": status}

        def run(kw, hook):
            if hook:
                resp, send = self._send(_three_hits(), cls="knock", **kw)
            else:
                with mock.patch("app.routes.knock_rhythm.record") as rec:
                    resp, send = self._send(_three_hits(), cls="knock", **kw)
                rec.assert_called_once()  # 끈 자리가 실제 훅 호출 지점이다
            body = strip(resp.get_json())
            return body, strip(self._stored(resp)), send.call_args_list

        cases = {
            "sent": dict(confidence=0.9),
            "low_confidence": dict(confidence=0.5),
            "tof_rejected": dict(confidence=0.9, tof_presence="false"),
        }
        for name, kw in cases.items():
            with self.subTest(name):
                without = run(kw, hook=False)
                with_hook = run(kw, hook=True)
                self.assertEqual(with_hook, without)
                self.assertEqual(with_hook[0], with_hook[1])  # 응답 본문 = 저장 행
        self.assertEqual(len(self._probes()), len(cases))  # 훅이 실제로 돌았다
        with self.subTest("measure failure"):
            without = run(cases["sent"], hook=False)
            with mock.patch("app.knock_rhythm.measure", side_effect=RuntimeError("boom")), \
                    self.assertLogs(self.app.logger, "ERROR"):
                failed = run(cases["sent"], hook=True)
            self.assertEqual(failed, without)


if __name__ == "__main__":
    unittest.main()
