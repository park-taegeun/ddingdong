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


class RegistrationState(db.Model):
    """초인종 등록 상태 (전역 단일 행 — KakaoToken 과 같은 SINGLETON_ID 패턴).

    상태 판정은 registration.state_of() 한 곳에서만 한다. 시각은 전부 naive UTC.
    ★ 새 테이블로만 추가한다 — db.create_all() 은 기존 테이블에 컬럼을 추가하지 않으므로
      기존 3테이블을 고치면 이미 만들어진 ddingdong.db 에서 조회가 깨진다.
    """

    __tablename__ = "registration_state"

    SINGLETON_ID = 1

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)

    # 시작할 때마다 새로 발급. 템플릿을 이 값으로 묶어 이전 등록분과 섞이지 않게 한다.
    registration_id: Mapped[str]
    target_count: Mapped[int]
    started_at: Mapped[datetime]  # naive UTC
    expires_at: Mapped[datetime]  # naive UTC
    completed_at: Mapped[datetime | None]  # naive UTC, 목표 개수를 채운 시각


class RegistrationTemplate(db.Model):
    """등록 템플릿 원본 = /detect 로 받은 int16 PCM 바이트 그대로 (BLOB)."""

    __tablename__ = "registration_templates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    registration_id: Mapped[str] = mapped_column(index=True)
    client_request_id: Mapped[str]  # 어느 /detect 요청이 템플릿이 됐는지 추적
    pcm: Mapped[bytes]
    created_at: Mapped[datetime]  # naive UTC


class RegistrationMatch(db.Model):
    """등록 뒤 /detect 마다 저장 템플릿과 잰 DTW-cosine 거리 기록 (관측 전용, 판정 0).

    로그가 아니라 테이블인 이유: 이 서버는 로그 레벨을 설정하지 않아 INFO 줄이 기본
    출력되지 않는다(/detect 의 "detect audio decoded" 줄이 기본 로그 레벨에서 안 보였다).
    테이블이면 세션이 끝난 뒤에도 거리 분포를 꺼내 볼 수 있다.
    PCM 은 저장하지 않는다 — 숫자만. 삭제 경로 없음(등록을 해제해도 분석용 이력으로 남는다).
    """

    __tablename__ = "registration_matches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_request_id: Mapped[str] = mapped_column(index=True)
    registration_id: Mapped[str]
    predicted_class: Mapped[str]  # 클래스와 무관하게 전부 기록 — 클래스 간 거리도 판정 입력
    template_count: Mapped[int]
    distances: Mapped[list] = mapped_column(JSON)  # 템플릿 생성 순
    min_distance: Mapped[float]
    mean_distance: Mapped[float]
    compare_ms: Mapped[float]  # 저장 템플릿 디코드 · 특징 + 질의 특징 + DTW 전체
    created_at: Mapped[datetime]  # naive UTC
