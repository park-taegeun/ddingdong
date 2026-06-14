"""API v1 엔드포인트 4종 (카테고리 6.1).

  POST /api/v1/detect         ESP32 1차: mock 추론 + notification 저장 (Device Token)
  POST /api/v1/enrich         ESP32 2차: 사진/STT mock 채움 (Device Token)
  GET  /api/v1/notifications  대시보드 폴링: cursor pagination (Dashboard Token)
  GET  /api/v1/stats          대시보드 폴링: period=today 집계 (Dashboard Token)
"""

from datetime import timedelta, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy import select

from . import rate_limit
from .auth import dashboard_auth, device_auth
from .constants import (
    DEFAULT_PAGE_LIMIT,
    DEVICE_RATE_LIMIT_SECONDS,
    KST,
    MAX_PAGE_LIMIT,
    PREDICTED_CLASSES,
    STATS_PERIOD,
)
from .errors import ApiError
from .extensions import db
from .models import IdempotencyKey, Notification
from .utils import (
    kst_now_iso,
    mock_enrichment,
    mock_prediction,
    new_request_id,
    to_kst_iso,
    utc_now,
)

bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


# ── POST /api/v1/detect ──────────────────────────────────────────────────
@bp.post("/detect")
@device_auth
def detect():
    payload = request.get_json(silent=True) or {}
    client_request_id = payload.get("client_request_id")
    device_id = payload.get("device_id")
    if not client_request_id or not device_id:
        raise ApiError(400, "bad_request", "client_request_id 와 device_id 는 필수입니다.")

    now = utc_now()

    # 1) idempotency 우선 — 네트워크 재시도는 rate limit 소모 없이 캐시 응답 replay
    existing = db.session.get(IdempotencyKey, client_request_id)
    if existing is not None:
        if existing.is_valid(now):
            resp = jsonify(existing.response_json)
            resp.status_code = 200
            resp.headers["Idempotent-Replay"] = "true"
            return resp
        db.session.delete(existing)  # TTL 만료 → 폐기 후 신규 처리
        db.session.flush()

    # 2) rate limit (device_id 5초당 1회)
    retry_after = rate_limit.check_and_register(device_id)
    if retry_after is not None:
        raise ApiError(
            429,
            "rate_limited",
            f"{DEVICE_RATE_LIMIT_SECONDS}초당 1회만 허용됩니다.",
            headers={"Retry-After": str(retry_after)},
        )

    # 3) mock 추론 → notification 저장 (실제 YAMNet 통합은 11주차)
    pred = mock_prediction()
    request_id = new_request_id()
    notif = Notification(
        client_request_id=client_request_id,
        request_id=request_id,
        device_id=device_id,
        detected_at=now,
        predicted_class=pred["predicted_class"],
        confidence=pred["confidence"],
        all_scores=pred["all_scores"],
        tof_applied=pred["tof"]["applied"],
        tof_passed=pred["tof"]["passed"],
        tof_reason=pred["tof"]["reason"],
        primary_sent=pred["primary_sent"],
        primary_sent_at=now if pred["primary_sent"] else None,
        enrich_status=pred["enrich_status"],
        secondary_sent=False,
        secondary_sent_at=None,
        skip_reason=pred["skip_reason"],
        image_url=None,
        image_thumbnail_url=None,
        audio_url=None,
        stt=None,
    )
    db.session.add(notif)
    db.session.flush()  # PK 확정

    body = notif.to_dict()
    # 4) idempotency 키 기록 (동일 client_request_id 24h 내 재요청 → 위 replay)
    db.session.add(
        IdempotencyKey(
            client_request_id=client_request_id,
            request_id=request_id,
            response_json=body,
            created_at=now,
        )
    )
    db.session.commit()
    return jsonify(body), 201


# ── POST /api/v1/enrich ──────────────────────────────────────────────────
@bp.post("/enrich")
@device_auth
def enrich():
    payload = request.get_json(silent=True) or {}
    request_id = payload.get("request_id")
    if not request_id:
        raise ApiError(400, "bad_request", "request_id 는 필수입니다.")

    notif = db.session.scalar(
        select(Notification).where(Notification.request_id == request_id)
    )
    if notif is None:
        raise ApiError(404, "not_found", "해당 request_id 의 알림을 찾을 수 없습니다.")
    if notif.enrich_status in ("completed", "skipped"):
        raise ApiError(
            409,
            "conflict",
            f"이미 처리된 알림입니다 (enrich_status={notif.enrich_status}).",
        )

    enr = mock_enrichment(notif.request_id)
    notif.image_url = enr["media"]["image_url"]
    notif.image_thumbnail_url = enr["media"]["image_thumbnail_url"]
    notif.audio_url = enr["media"]["audio_url"]
    notif.stt = enr["stt"]
    notif.enrich_status = "completed"
    notif.secondary_sent = True
    notif.secondary_sent_at = utc_now()
    db.session.commit()
    return jsonify(notif.to_dict()), 200


# ── GET /api/v1/notifications ────────────────────────────────────────────
@bp.get("/notifications")
@dashboard_auth
def list_notifications():
    limit = _parse_limit(request.args.get("limit"))
    cursor = request.args.get("cursor")

    stmt = select(Notification).order_by(Notification.id.desc())
    if cursor:
        if not cursor.isdigit():
            raise ApiError(400, "bad_request", "cursor 형식이 올바르지 않습니다.")
        stmt = stmt.where(Notification.id < int(cursor))

    # limit+1 조회로 has_more 판정 (추가 count 쿼리 불필요)
    rows = db.session.scalars(stmt.limit(limit + 1)).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = str(rows[-1].id) if has_more and rows else None

    # NotificationsApiResponse(notifications) + cursor 메타(additive)
    return jsonify(
        {
            "notifications": [n.to_dict() for n in rows],
            "next_cursor": next_cursor,
            "has_more": has_more,
        }
    ), 200


def _parse_limit(raw):
    if raw is None:
        return DEFAULT_PAGE_LIMIT
    if not raw.isdigit():
        raise ApiError(400, "bad_request", "limit 은 양의 정수여야 합니다.")
    return min(max(1, int(raw)), MAX_PAGE_LIMIT)


# ── GET /api/v1/stats ────────────────────────────────────────────────────
@bp.get("/stats")
@dashboard_auth
def stats():
    period = request.args.get("period", STATS_PERIOD)
    if period != STATS_PERIOD:
        raise ApiError(400, "bad_request", f"period 는 '{STATS_PERIOD}' 만 지원합니다.")

    # 오늘(KST) 00:00 ~ 23:59:59.999 → DB 비교용 naive UTC 로 환산
    now_kst = utc_now().replace(tzinfo=timezone.utc).astimezone(KST)
    start_kst = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
    end_kst = start_kst + timedelta(days=1) - timedelta(milliseconds=1)
    start_utc = start_kst.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_kst.astimezone(timezone.utc).replace(tzinfo=None)

    rows = db.session.scalars(
        select(Notification).where(
            Notification.detected_at >= start_utc,
            Notification.detected_at <= end_utc,
        )
    ).all()

    return jsonify(_build_stats(rows, start_kst, end_kst)), 200


def _build_stats(rows, start_kst, end_kst):
    """오늘 알림 목록 → StatsResponse(stats.ts). 단일 쿼리 결과로 파이썬 집계(N+1 없음)."""
    total = len(rows)
    sent = [n for n in rows if n.primary_sent]
    skipped = [n for n in rows if not n.primary_sent]
    avg_conf = round(sum(n.confidence for n in rows) / total, 2) if total else 0.0

    # 클래스별 분포 (3종 모두 키 존재 — ClassDistribution = Record<PredictedClass, ...>)
    class_distribution = {}
    for cls in PREDICTED_CLASSES:
        group = [n for n in rows if n.predicted_class == cls]
        count = len(group)
        class_distribution[cls] = {
            "count": count,
            "percentage": round(count / total * 100, 1) if total else 0.0,
            "average_confidence": (
                round(sum(n.confidence for n in group) / count, 2) if count else 0.0
            ),
            "notifications_sent": sum(1 for n in group if n.primary_sent),
        }

    # skip 사유별 집계 (SkipReasonCounts 4종 키 고정)
    skip_reasons = {
        "low_confidence": 0,
        "tof_rejected": 0,
        "kakao_api_error": 0,
        "token_expired": 0,
    }
    for n in skipped:
        if n.skip_reason in skip_reasons:
            skip_reasons[n.skip_reason] += 1

    # 시간대별 분포 (00~23, KST 기준)
    buckets = {f"{h:02d}": 0 for h in range(24)}
    for n in rows:
        hour = n.detected_at.replace(tzinfo=timezone.utc).astimezone(KST).strftime("%H")
        buckets[hour] += 1
    hourly_distribution = [{"hour": h, "count": c} for h, c in buckets.items()]

    last_seen = max((n.detected_at for n in rows), default=None)

    return {
        "period": STATS_PERIOD,
        "period_start": start_kst.isoformat(),
        "period_end": end_kst.isoformat(timespec="seconds"),
        "server_time": kst_now_iso(),
        "summary": {
            "total_detections": total,
            "total_notifications_sent": len(sent),
            "skip_count": len(skipped),
            "average_confidence": avg_conf,
        },
        "class_distribution": class_distribution,
        # timing_metrics 는 실제 지연 계측 도입 전까지 placeholder (구조만 정확)
        "timing_metrics": {
            "primary_notification_avg_ms": 0,
            "primary_notification_max_ms": 0,
            "secondary_notification_avg_ms": 0,
            "secondary_notification_max_ms": 0,
            "primary_under_5s_rate": 0.0,
            "secondary_under_15s_rate": 0.0,
        },
        "skip_reasons": skip_reasons,
        # system_health: device_last_seen 만 실데이터, 외부 연동값은 11~14주차 전까지 mock
        "system_health": {
            "device_last_seen_at": kst_now_iso()
            if last_seen is None
            else to_kst_iso(last_seen),
            "device_status": "online" if last_seen is not None else "offline",
            "kakao_token_status": "valid",
            "kakao_token_expires_in_minutes": 240,
            "clova_api_status": "ok",
            "db_status": "ok",
        },
        "hourly_distribution": hourly_distribution,
    }
