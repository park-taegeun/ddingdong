"""SQLAlchemy 모델 (카테고리 6).

Notification.to_dict() 출력은 dashboard/src/types/notification.ts 의
NotificationItem 과 1:1 매칭된다 (SSoT = types).
"""

from datetime import datetime

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .constants import IDEMPOTENCY_TTL
from .extensions import db
from .utils import to_kst_iso


class Notification(db.Model):
    __tablename__ = "notifications"

    # 내부 PK = cursor pagination 기준(시간순 단조 증가)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # 카테고리 6.1: client_request_id(ESP32 멱등 키) / request_id(서버 ULID) 분리
    client_request_id: Mapped[str] = mapped_column(unique=True, index=True)
    request_id: Mapped[str] = mapped_column(unique=True, index=True)

    device_id: Mapped[str] = mapped_column(index=True)
    detected_at: Mapped[datetime] = mapped_column(index=True)  # naive UTC

    # ML 결과 (카테고리 4)
    predicted_class: Mapped[str]
    confidence: Mapped[float]
    all_scores: Mapped[dict] = mapped_column(JSON)

    # ToF 사람 검증 (카테고리 9)
    tof_applied: Mapped[bool]
    tof_passed: Mapped[bool | None]
    tof_reason: Mapped[str]

    # 알림 상태 (notification.ts NotificationStatus)
    primary_sent: Mapped[bool]
    primary_sent_at: Mapped[datetime | None]
    enrich_status: Mapped[str]
    secondary_sent: Mapped[bool]
    secondary_sent_at: Mapped[datetime | None]
    skip_reason: Mapped[str | None]

    # 미디어 + STT (enrich 단계에서 채움, 그 전까진 null)
    image_url: Mapped[str | None]
    image_thumbnail_url: Mapped[str | None]
    audio_url: Mapped[str | None]
    stt: Mapped[dict | None] = mapped_column(JSON)

    def to_dict(self):
        status = {
            "primary_sent": self.primary_sent,
            "primary_sent_at": to_kst_iso(self.primary_sent_at),
            "enrich_status": self.enrich_status,
            "secondary_sent": self.secondary_sent,
            "secondary_sent_at": to_kst_iso(self.secondary_sent_at),
        }
        # notification.ts 의 skip_reason 은 optional → 값이 있을 때만 포함
        if self.skip_reason:
            status["skip_reason"] = self.skip_reason

        return {
            "client_request_id": self.client_request_id,
            "request_id": self.request_id,
            "detected_at": to_kst_iso(self.detected_at),
            "predicted_class": self.predicted_class,
            "confidence": self.confidence,
            "all_scores": self.all_scores,
            "tof_check": {
                "applied": self.tof_applied,
                "passed": self.tof_passed,
                "reason": self.tof_reason,
            },
            "notification_status": status,
            "media": {
                "image_url": self.image_url,
                "image_thumbnail_url": self.image_thumbnail_url,
                "audio_url": self.audio_url,
            },
            "stt": self.stt,
            "device_id": self.device_id,
        }


class IdempotencyKey(db.Model):
    """client_request_id 기반 재시도 중복 차단 (카테고리 6.1, 24h TTL)."""

    __tablename__ = "idempotency_keys"

    client_request_id: Mapped[str] = mapped_column(primary_key=True)
    request_id: Mapped[str]
    response_json: Mapped[dict] = mapped_column(JSON)  # 최초 응답 본문 캐시
    created_at: Mapped[datetime]  # naive UTC

    def is_valid(self, now_utc):
        """생성 후 24시간 이내면 True (TTL 내 유효한 멱등 키)."""
        return (now_utc - self.created_at) < IDEMPOTENCY_TTL
