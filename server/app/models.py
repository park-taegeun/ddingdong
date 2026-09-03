"""SQLAlchemy 모델 (카테고리 6).

Notification.to_dict() 출력은 dashboard/src/types/notification.ts 의
NotificationItem 과 1:1 매칭된다 (SSoT = types).
"""

from datetime import datetime

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .constants import IDEMPOTENCY_TTL, KAKAO_REFRESH_MARGIN
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


class KakaoToken(db.Model):
    """카카오 OAuth 토큰 저장 (카테고리 7, 단일 행).

    나에게 보내기(memo)는 수신자가 서비스 운영자 1명이라 다중 사용자 모델이 필요
    없다. 항상 id=SINGLETON_ID 한 행만 두고 갱신은 그 행을 덮어쓴다.

    to_dict() 를 두지 않는다 — 이 테이블이 담는 값은 토큰 실값이라 직렬화 대상이
    아니다. 대시보드 토큰 상태(카테고리 6.1)는 절대 만료시각 대신 상대값만 노출해야
    하므로, 그 배선 시 전용 표현 함수를 따로 만든다(to_dict 재사용 금지).
    """

    __tablename__ = "kakao_tokens"

    # 단일 행 고정 PK. autoincrement 를 끄고 이 값만 써서 "두 번째 행"이 생길
    # 여지를 없앤다.
    SINGLETON_ID = 1

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)

    access_token: Mapped[str]
    refresh_token: Mapped[str]
    access_expires_at: Mapped[datetime]  # naive UTC
    refresh_expires_at: Mapped[datetime]  # naive UTC
    updated_at: Mapped[datetime]  # naive UTC

    def needs_refresh(self, now_utc):
        """access 토큰이 만료됐거나 만료 임박(KAKAO_REFRESH_MARGIN 이내)이면 True."""
        return (self.access_expires_at - now_utc) <= KAKAO_REFRESH_MARGIN
