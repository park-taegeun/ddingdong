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

# 카테고리 6.2 A안 (2026-07-09 PoC-(26) transport 계약): /detect multipart 오디오 파트명
AUDIO_FILE_FIELD = "audio"

# 오디오 파트 최대 크기 — 10초 @ 16kHz mono int16 (2 bytes/sample) 상한 + 여유
# (§0 기준치 64KB/2초 대비 5배 여유; PoC 단계 단발 발화 상한이라 충분)
AUDIO_MAX_BYTES = 320_000

# 카테고리 6.2 A안 (transport 계약 동형): /enrich multipart 이미지 파트명
IMAGE_FILE_FIELD = "image"

# 이미지 파트 최대 크기 — abuse/메모리 가드 전용, 캡처 해상도와 무관(해상도 확정 = 11주차)
IMAGE_MAX_BYTES = 512_000

# 카테고리 7: 캡처 이미지 public 호스팅용 opaque 키 바이트수 (secrets.token_urlsafe 입력).
# 16 bytes → ~22자 URL-safe base64. 추측 불가 = 프라이버시 게이트(옆 번호를 찔러 남의
# 방문자 사진을 여는 열람 차단). notification_id·순차값 유래 절대 금지.
# ★ 11주차 교체 지점: public 호스팅 방식이 바뀌어도 키 강도 정책은 유지.
CAPTURE_OPAQUE_BYTES = 16

# 캡처 이미지 TTL — 카카오가 발송 시점에 image_url 을 즉시 fetch 하지 않고 lazy 로딩하므로
# (카테고리 7.3) 짧게 못 잡음 → 넉넉히 72시간. cleanup_expired() 수동 호출 대상
# (스케줄러 신설 X, 스케줄링은 11주차 defer). IDEMPOTENCY_TTL 과 동일 timedelta 관례.
# ★ 11주차 교체 지점: 실 호스팅 이관 시 만료 정책 재확정.
CAPTURE_TTL = timedelta(hours=72)

# 한국 표준시 (KST, UTC+9). DB 는 naive UTC 저장, 응답 직렬화 시 KST 변환.
KST = timezone(timedelta(hours=9))
