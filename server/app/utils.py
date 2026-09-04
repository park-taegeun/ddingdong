"""시간/ID/mock ML 유틸.

시간 정책 (SQLite 는 native timezone 미지원):
  - DB 저장 = naive UTC datetime (utc_now)
  - 응답 직렬화 = KST ISO8601 (+09:00), 밀리초 정밀도 (to_kst_iso)
이렇게 분리해 비교/정렬은 UTC 로 일관되게, 화면 표기는 KST 로 정확하게 한다.
"""

import os
import random
import time
from datetime import datetime, timezone

from . import tof_meta as tof_meta_wire
from .constants import CONFIDENCE_THRESHOLD, KST, PREDICTED_CLASSES

# ── 시간 ────────────────────────────────────────────────────────────────


def utc_now():
    """DB 저장용 naive UTC datetime (tzinfo 제거)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_kst_iso(dt):
    """naive-UTC datetime → KST ISO8601 문자열(밀리초). None 은 그대로 None."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc).astimezone(KST).isoformat(timespec="milliseconds")


def kst_now_iso():
    """현재 시각을 KST ISO8601 문자열(밀리초)로."""
    return datetime.now(KST).isoformat(timespec="milliseconds")


# ── ULID (request_id 발급, 카테고리 6.1) ─────────────────────────────────
# Crockford Base32. 앞 48bit = ms 타임스탬프(정렬 가능) + 80bit 랜덤.
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _encode(value, length):
    out = []
    for _ in range(length):
        out.append(_CROCKFORD[value & 0x1F])
        value >>= 5
    return "".join(reversed(out))


def new_request_id():
    """서버 발급 ULID 기반 request_id. 예: req_01HZQ9D2K3M4N5P6Q7R8S9T0U5"""
    ts_ms = int(time.time() * 1000)               # 48bit
    rand = int.from_bytes(os.urandom(10), "big")  # 80bit
    return "req_" + _encode(ts_ms, 10) + _encode(rand, 16)


# ── mock ML 추론 (실제 YAMNet 통합은 11주차) ─────────────────────────────

_MOCK_TRANSCRIPTS = (
    "택배 왔습니다. 문 앞에 두고 갈게요.",
    "계세요? 옆집인데요.",
    "안녕하세요, 관리사무소입니다.",
    "잠시 문 좀 열어주시겠어요?",
)


def _tof_decision(predicted_class, tof_meta):
    """클래스별 ToF 정책(카테고리 3) 적용 → notification.ts TofCheck 3키 dict.

    - 화재경보: ToF 우회. 게이트를 적용하지 않되(applied False) 수신 telemetry 는
      증거로 함께 남긴다 — "우회했다"와 "받은 게 없다"가 기록에서 갈려야 한다.
    - 노크·초인종: tof_meta 상태가 그대로 게이트 결과가 된다(tof_meta.evaluate_gate).
    """
    if predicted_class == "fire_alarm":
        detail = tof_meta_wire.telemetry_summary(tof_meta)
        return {
            "applied": False,
            "passed": None,
            # 기존 값 "fire_alarm_bypass" 를 접두로 보존(seed.py·대시보드 표기 동형).
            "reason": f"fire_alarm_bypass ({detail})" if detail else "fire_alarm_bypass",
        }
    applied, passed, reason = tof_meta_wire.evaluate_gate(tof_meta)
    return {"applied": applied, "passed": passed, "reason": reason}


def _apply_prediction_policy(predicted_class, confidence, all_scores, tof_meta=None):
    """예측(mock/real 공통) → 알림 판정 dict. 카테고리 4 enum + notification.ts 분기 의미 준수.

    mock_prediction() 에서 순수 추출(로직 변경 없음, 2026-07-31 카테고리 6.2 실추론 배선
    pivot) — 랜덤 생성이든 ModelRunner 실추론이든 이 함수를 거치면 동일 판정을 받는다.

    분기(위에서부터 순서대로 — 먼저 걸린 사유가 skip_reason 이 된다):
      - fire_alarm → ToF 우회, 1차 알림만(enrich skipped) (카테고리 7 화재경보)
      - 신뢰도 < 임계값 → 1차 알림 skip (skip_reason="low_confidence")
      - ToF 게이트 적용 + 미통과 → 1차 알림 skip (skip_reason="tof_rejected")
      - 그 외 → 1차 알림 발송, enrich 대기(pending)

    ★ G12 무접촉: 위 1·2번 분기(fire_alarm early return ↔ 신뢰도 비교)의 상대 순서는
      decisions.md 카테고리 3 에 미결로 등재돼 사용자 판단 대기 중이라 **건드리지
      않았다.** ToF 게이트를 두 분기 사이가 아니라 신뢰도 비교 **뒤**에 넣은 것도
      같은 이유다 — 사이에 끼우면 "현행 순서"가 무엇이었는지가 흐려진다.
      부수 결과로 저신뢰 + ToF 미통과가 겹치면 skip_reason 은 low_confidence 로
      기록된다(둘 다 미발송이라 발송 여부는 어느 순서든 동일).

    tof_meta = tof_meta.parse_tof_meta() 결과, 또는 None(= ToF 를 모르는 호출부).
    None 은 "부재"로 취급해 게이트를 적용하지 않는다(현행 동작 보존, fail-open).
    ★ 서버는 tof_presence 를 재판정하지 않는다 — 근거는 tof_meta.py 상단 주석.
    """
    if tof_meta is None:
        tof_meta = tof_meta_wire.absent_meta()
    tof = _tof_decision(predicted_class, tof_meta)

    if predicted_class == "fire_alarm":
        return {
            "predicted_class": predicted_class,
            "confidence": confidence,
            "all_scores": all_scores,
            "tof": tof,
            "primary_sent": True,
            "enrich_status": "skipped",
            "skip_reason": None,
        }
    if confidence < CONFIDENCE_THRESHOLD:
        return {
            "predicted_class": predicted_class,
            "confidence": confidence,
            "all_scores": all_scores,
            "tof": tof,
            "primary_sent": False,
            "enrich_status": "skipped",
            "skip_reason": "low_confidence",
        }
    if tof["applied"] and not tof["passed"]:
        # 사람 없음 → 1차 알림 미발송. skip_reason 은 기존 enum 값 재사용
        # (notification.ts SkipReason "tof_rejected" / stats.ts skip_reasons 키 —
        #  신규 키 발명 없음, 프론트 타입 무변경).
        return {
            "predicted_class": predicted_class,
            "confidence": confidence,
            "all_scores": all_scores,
            "tof": tof,
            "primary_sent": False,
            "enrich_status": "skipped",
            "skip_reason": "tof_rejected",
        }
    return {
        "predicted_class": predicted_class,
        "confidence": confidence,
        "all_scores": all_scores,
        "tof": tof,
        "primary_sent": True,
        "enrich_status": "pending",
        "skip_reason": None,
    }


def mock_prediction(tof_meta=None):
    """detect 용 mock 추론 결과. 랜덤 예측 생성 후 _apply_prediction_policy 로 판정."""
    predicted = random.choice(PREDICTED_CLASSES)
    top = round(random.uniform(0.45, 0.97), 2)
    others = [c for c in PREDICTED_CLASSES if c != predicted]
    rest = round(1.0 - top, 2)
    a = round(random.uniform(0.0, rest), 2)
    b = round(rest - a, 2)
    raw = {predicted: top, others[0]: a, others[1]: b}
    # 출력 키 순서를 enum 순서(doorbell/knock/fire_alarm)로 고정 (AllScores 타입 일치)
    all_scores = {c: raw[c] for c in PREDICTED_CLASSES}
    return _apply_prediction_policy(predicted, top, all_scores, tof_meta)


def mock_enrichment(request_id):
    """enrich 용 mock 사진/STT (실제 카메라·Clova 연동은 11·13~14주차)."""
    short = request_id.removeprefix("req_")[:10]
    return {
        "media": {
            "image_url": f"/static/captures/{short}.jpg",
            "image_thumbnail_url": f"/static/captures/thumb_{short}.jpg",
            "audio_url": f"/static/audio/{short}.wav",
        },
        "stt": {
            "transcript": random.choice(_MOCK_TRANSCRIPTS),
            "confidence": round(random.uniform(0.85, 0.97), 2),
            "language": "ko-KR",
            "processed_at": kst_now_iso(),
        },
    }
