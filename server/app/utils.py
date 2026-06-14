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


def mock_prediction():
    """detect 용 mock 추론 결과. 카테고리 4 enum + notification.ts 분기 의미 준수.

    분기:
      - fire_alarm → ToF 우회, 1차 알림만(enrich skipped) (카테고리 7 화재경보)
      - 신뢰도 < 임계값 → 1차 알림 skip (skip_reason="low_confidence")
      - 그 외 → 1차 알림 발송, enrich 대기(pending)
    """
    predicted = random.choice(PREDICTED_CLASSES)
    top = round(random.uniform(0.45, 0.97), 2)
    others = [c for c in PREDICTED_CLASSES if c != predicted]
    rest = round(1.0 - top, 2)
    a = round(random.uniform(0.0, rest), 2)
    b = round(rest - a, 2)
    raw = {predicted: top, others[0]: a, others[1]: b}
    # 출력 키 순서를 enum 순서(doorbell/knock/fire_alarm)로 고정 (AllScores 타입 일치)
    all_scores = {c: raw[c] for c in PREDICTED_CLASSES}

    if predicted == "fire_alarm":
        return {
            "predicted_class": predicted,
            "confidence": top,
            "all_scores": all_scores,
            "tof": {"applied": False, "passed": None, "reason": "fire_alarm_bypass"},
            "primary_sent": True,
            "enrich_status": "skipped",
            "skip_reason": None,
        }
    if top < CONFIDENCE_THRESHOLD:
        return {
            "predicted_class": predicted,
            "confidence": top,
            "all_scores": all_scores,
            "tof": {"applied": True, "passed": True, "reason": "zone_count=9 >= 8 + motion=true"},
            "primary_sent": False,
            "enrich_status": "skipped",
            "skip_reason": "low_confidence",
        }
    return {
        "predicted_class": predicted,
        "confidence": top,
        "all_scores": all_scores,
        "tof": {"applied": True, "passed": True, "reason": "zone_count=11 >= 8 + motion=true"},
        "primary_sent": True,
        "enrich_status": "pending",
        "skip_reason": None,
    }


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
