"""매직 넘버/문자열 중앙 관리 (카테고리 21 자체검증 ② 리팩토링)."""

from datetime import timedelta, timezone

# 카테고리 4: ML predicted_class 3종 enum (코드 식별자만 영어, "도어벨" 미사용 — 카테고리 29.5)
PREDICTED_CLASSES = ("doorbell", "knock", "fire_alarm")

# 카테고리 6.1: device_id 5초당 1회 (초과 시 429 + Retry-After)
DEVICE_RATE_LIMIT_SECONDS = 5

# 카테고리 6.1: idempotency_keys 24시간 TTL
IDEMPOTENCY_TTL = timedelta(hours=24)

# mock ML: 신뢰도 임계값 미만 시 1차 알림 skip (notification.ts skip_reason="low_confidence")
CONFIDENCE_THRESHOLD = 0.7

# cursor pagination 기본/최대 페이지 크기
DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100

# stats period 단일값 (카테고리 6.1, stats.ts StatsPeriod)
STATS_PERIOD = "today"

# 한국 표준시 (KST, UTC+9). DB 는 naive UTC 저장, 응답 직렬화 시 KST 변환.
KST = timezone(timedelta(hours=9))
