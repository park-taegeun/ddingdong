"""/detect 노크 타격 리듬 계측 — 예측 knock 건마다 봉우리 후보 목록을 knock_rhythm_probes 에 1행.

계측용 — 판정 기준 아님. 이 모듈은 발송 · 응답 · skip_reason 을 바꾸지 않는다(판정 0줄).
「똑똑(똑)」 리듬 규칙은 동작별 표시가 붙은 보드 세션 · 리허설에서 이 행을 모은 뒤 정한다.

★ 위치 계약(registration_observe.record 와 같은 자리): 카카오 1차 발송 **뒤** · 단일 commit 앞.
  kakao._assert_commit_is_safe() 는 세션의 미커밋 객체를 보면 RuntimeError 를 낸다 — add 를
  발송 앞으로 옮기면 발송 경로가 5xx 가 된다. 이 모듈은 commit · 명시적 flush 를 하지 않는다.
★ 대상 = 예측 knock 전부(발송 여부 무관 — 저신뢰 · ToF 거부 · 등록 억제 포함).
★ 계산 실패는 막지 않는다: 실패 사유 행 + ERROR 1줄, /detect 는 그대로 진행.
★ 저장 = 숫자만(봉우리 시각 · 상대 높이 · 창 최대 · 마스크 샘플 수). 오디오 · 파형은 저장하지 않는다.

정의 = 오프라인 PoC-(75) knock_hits.py(repo 밖) Step 2 그대로: 글리치 마스크 → 16 ms 프레임 RMS
포락선(제외 샘플 뺌) → 이웃보다 큰 프레임 = 봉우리 후보. 기록은 상위 규칙(r 0.3 · 억제 100 ms)보다
넓게 — r ≥ R_MIN · 억제 없음(GAP_MS 0). 탐욕적 억제는 한 번 줄여 두면 다른 억제 간격으로 정확히
다시 계산할 수 없어서, 억제 전 후보를 남겨 나중에 어떤 (r ≥ R_MIN, 억제 g) 규칙이든 다시 계산한다.
재판정 트리거 = 판정 PR 착수 시(기록 파라미터가 그 규칙을 덮는지 다시 본다).
"""

import time
from itertools import groupby

import numpy as np
from flask import current_app

from .extensions import db
from .models import KnockRhythmProbe

# ml/curation/slice_direct.py 의 글리치 마스크 상수 · 함수 복제 — 서버는 ml 을 import 하지 않는다
# (sound_match · serving_level 선례). test_knock_rhythm 이 ml 원문을 ast 로 떼어 매 실행 대조한다.
CLAMP = 32767
CLAMP_MASK_HALF_WIDTH = 32
GLITCH_MAX_RUN = 2

# 계측용 — 판정 기준 아님.
PROBE_VERSION = "knock_rhythm_v1"
SAMPLE_RATE = 16000
FRAME = 256  # 16 ms 창
HOP = 128  # 8 ms 간격
HOP_MS = HOP * 1000 // SAMPLE_RATE
R_MIN = 0.1  # 기록 하한(창 최대 대비). 오프라인 격자 최저 r 0.2 · Step 2 분포 최저 열 r 0.1
GAP_MS = 0  # 억제 없음
RATIO_DIGITS = 4
PARAMS = {
    "probe_version": PROBE_VERSION,
    "sample_rate": SAMPLE_RATE,
    "frame": FRAME,
    "hop": HOP,
    "r_min": R_MIN,
    "gap_ms": GAP_MS,
    "clamp": CLAMP,
    "clamp_mask_half_width": CLAMP_MASK_HALF_WIDTH,
    "glitch_max_run": GLITCH_MAX_RUN,
}

_ERROR_TEXT_MAX = 120  # 예외 타입 + 메시지 앞부분만 남긴다


def mask_glitch_clamps(a: list[int]) -> list[int]:
    """a = |x| 목록 → 길이 ≤ GLITCH_MAX_RUN 클램프 런의 [시작 − K, 끝 + K] 를 CLAMP 로 채운 새 목록(a 무변경).

    K = CLAMP_MASK_HALF_WIDTH. ml/curation/slice_direct.py 원문 복제(본문 무변경).
    """
    n = len(a)
    out = a[:]
    i = 0
    for is_clamp, g in groupby(a, key=lambda v: v >= CLAMP):
        k = sum(1 for _ in g)
        if is_clamp and k <= GLITCH_MAX_RUN:
            lo, hi = max(i - CLAMP_MASK_HALF_WIDTH, 0), min(i + k + CLAMP_MASK_HALF_WIDTH, n)
            out[lo:hi] = [CLAMP] * (hi - lo)
        i += k
    return out


def _envelope(x, excl):
    """프레임 RMS(제외 샘플 빼고 평균). FRAME 보다 짧은 입력 = 빈 포락선."""
    y = np.where(excl, 0, x).astype(np.float64)
    ok = (~excl).astype(np.float64)
    n = max(0, 1 + (len(x) - FRAME) // HOP)
    idx = np.arange(FRAME)[None, :] + HOP * np.arange(n)[:, None]
    s2, c = (y[idx] ** 2).sum(1), ok[idx].sum(1)
    return np.sqrt(np.divide(s2, c, out=np.zeros(n), where=c > 0))


def _local_max(e):
    """봉우리 후보 = 이웃 프레임보다 큰 프레임(평탄 꼭대기는 첫 프레임)."""
    i = np.arange(1, len(e) - 1)
    return i[(e[i] > e[i - 1]) & (e[i] >= e[i + 1])]


def measure(pcm):
    """PCM int16 LE bytes → {peaks: [[ms, 비율], …] 시각순, peak_count, env_max, mask_samples}.

    제외 = 마스크 표식 위치 + 모든 클램프(마스크 출력 ≥ CLAMP — 오프라인 mask_of 와 같다).
    값은 전부 파이썬 int · float(JSON 컬럼에 그대로 들어간다).
    """
    x = np.frombuffer(pcm, dtype="<i2").astype(np.int64)
    excl = np.array(mask_glitch_clamps(np.abs(x).tolist()), dtype=np.int64) >= CLAMP
    e = _envelope(x, excl)
    top = float(e.max()) if e.size else 0.0
    peaks = []
    if top > 0:
        peaks = [
            [int(p) * HOP_MS, round(float(e[p]) / top, RATIO_DIGITS)]
            for p in _local_max(e)
            if e[p] >= R_MIN * top
        ]
    return {
        "peaks": peaks,
        "peak_count": len(peaks),
        "env_max": round(top, 1),
        "mask_samples": int(excl.sum()),
    }


def record(pcm, notif, now):
    """카카오 뒤 · commit 앞. 예측 knock 이면 1행 add, 아니면 아무것도 하지 않는다."""
    if notif.predicted_class != "knock":
        return
    started = time.monotonic()
    try:
        m, error = measure(pcm), None
    except Exception as exc:
        m = dict.fromkeys(("peaks", "peak_count", "env_max", "mask_samples"))
        error = f"{type(exc).__name__}: {exc}"[:_ERROR_TEXT_MAX]
        current_app.logger.exception(
            "knock rhythm probe failed (detect continues): client_request_id=%s",
            notif.client_request_id,
        )
    db.session.add(
        KnockRhythmProbe(
            notification_id=notif.id,
            probe_version=PROBE_VERSION,
            params=PARAMS,
            compute_ms=(time.monotonic() - started) * 1000,
            error=error,
            created_at=now,
            **m,
        )
    )
