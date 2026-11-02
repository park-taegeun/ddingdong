"""/detect 노크 단일 타격 차단 — 판정 모듈(카테고리 20 「계측 → 실측 → 판정」의 판정 단계).

계측은 knock_rhythm(판정 0줄 계약 — 이 모듈은 그 본문을 고치지 않고 measure 만 import 해 쓴다).
값 · 근거 · 재판정 트리거 = constants.py 「노크 단일 타격 차단」.

★ 위치 = routes.detect 등록 판정 바로 뒤 · 카카오 앞(차단은 발송 전에 정해져야 한다).
★ DB 쓰기 0 — kakao._assert_commit_is_safe() 계약상 카카오 앞에서는 add 하지 않는다.
  계측 행은 지금처럼 knock_rhythm.record(카카오 뒤)가 남긴다 — 차단 · 발송 양쪽 다.
★ 예외를 밖으로 내지 않는다 — 계산 실패 = 막지 않음(fail-open) + ERROR 1줄.
"""

from flask import current_app

from .constants import (
    KNOCK_MIN_STRONG_HITS,
    KNOCK_STRONG_HIT_GAP_MS,
    KNOCK_STRONG_HIT_RATIO,
    SKIP_REASON_KNOCK_SINGLE_HIT,
)
# 함수를 직접 묶는다 — 계측 쪽 실패를 흉내 내는 패치(app.knock_rhythm.measure)가 판정까지 번지지 않게.
from .knock_rhythm import measure


def strong_hits(peaks, ratio=KNOCK_STRONG_HIT_RATIO, gap_ms=KNOCK_STRONG_HIT_GAP_MS):
    """봉우리 후보 [[ms, 비율], …] → 뚜렷한 타격 시각(ms) 오름차순 목록.

    비율 ≥ ratio 만 남겨 높이 내림차순(같은 높이는 이른 시각 먼저 — 결정적)으로 훑고,
    이미 남긴 것과 gap_ms 미만으로 붙은 봉우리는 버린다.
    """
    kept = []
    for ms, h in sorted((p for p in peaks if p[1] >= ratio), key=lambda p: (-p[1], p[0])):
        if all(abs(ms - k) >= gap_ms for k in kept):
            kept.append(ms)
    return sorted(kept)


def judge(predicted_class, primary_sent, hits):
    """순수 함수 → SKIP_REASON_KNOCK_SINGLE_HIT 또는 None(그대로 진행).

    이미 미발송이거나 knock 이 아니면 None(앞선 사유 보존). hits None = 계산 실패 → None(fail-open).
    """
    if not primary_sent or predicted_class != "knock" or hits is None:
        return None
    return SKIP_REASON_KNOCK_SINGLE_HIT if len(hits) < KNOCK_MIN_STRONG_HITS else None


def before_send(pcm, client_request_id, predicted_class, primary_sent):
    """카카오 앞 진입점. pcm = 원본 int16 LE bytes. → skip_reason 또는 None."""
    if not primary_sent or predicted_class != "knock":
        return None
    try:
        hits = strong_hits(measure(pcm)["peaks"])
    except Exception:
        current_app.logger.exception(
            "knock gate failed — fail-open, sending as policy decided: client_request_id=%s",
            client_request_id,
        )
        return None
    reason = judge(predicted_class, primary_sent, hits)
    current_app.logger.info(
        "knock gate: strong_hits=%d gaps_ms=%s skip_reason=%s client_request_id=%s",
        len(hits),
        [b - a for a, b in zip(hits, hits[1:])],
        reason,
        client_request_id,
    )
    return reason
