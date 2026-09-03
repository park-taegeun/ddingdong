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

# ── 카카오 나에게 보내기(memo) 연동 (카테고리 7) ─────────────────────────
# refresh 토큰 수명 60일 (카테고리 7 토큰 정책 = access 6시간 / refresh 60일).
# env 부트스트랩 시점엔 이 토큰이 언제 발급됐는지 알 수 없어 만료 시각을 60일
# 상한으로 잡아둔다. 이후 실값은 갱신 응답의 refresh_token_expires_in 이 채운다.
# ※ access 쪽 6시간은 상수로 두지 않는다 — 부트스트랩이 access 를 "만료"로 간주해
#   첫 사용에서 반드시 갱신을 태우므로(kakao.py _bootstrap 주석) 참조처가 없다.
KAKAO_REFRESH_TOKEN_TTL = timedelta(days=60)

# access 토큰 "만료 임박" 판정 여유. 만료 직전 토큰을 통과시켜 발송 도중 401 을
# 맞는 일을 막는다. 10분 근거 = ① 서버(naive UTC)와 카카오 서버 시계 오차 흡수
# ② 갱신 판정 시점 ~ 실제 발송 시점 사이 간격 흡수. 6시간 TTL 대비 2.8% 조기
# 갱신이라 갱신 호출 증가는 무시할 수준.
KAKAO_REFRESH_MARGIN = timedelta(minutes=10)

# 카카오 OAuth 토큰 갱신 엔드포인트 (kauth = 인증 도메인, kapi(API) 와 별개).
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"

# 카카오 HTTP 호출 1건당 타임아웃. 근거유형 = 논증(역산). 입력값만 실측(카테고리 6.2/7.2).
#
# 역산: 5000ms − ESP32 업로드 p95 1900ms(TLS 포함) − 디코딩/추론 ~105ms ≈ 3000ms 잔여.
#       한 요청에서 최대 2회(토큰 갱신 + 발송) 호출될 수 있어 3000/2 = 1500ms.
#       memo 왕복 실측 p95 84.1ms(7.2) 대비 약 18배 여유 → 정상 구간을 자르지 않는다.
#
# ★ 전제 = "사전 링버퍼" 설계. 위 역산에는 카테고리 6.2 G29(2초 오디오 캡처 윈도우가
#   5초 예산에 미반영)가 반영돼 있지 않다. G29 는 사용자 판단 대기 중인 미결이라
#   여기서 어느 쪽으로도 확정하지 않는다.
#     - 사전 링버퍼(트리거 시점에 최근 2초가 이미 확보됨) → 잔여 3000ms, 현 값 1.5s 유효.
#     - 사후 녹음(트리거 후 2초를 녹음하고서야 업로드 시작) → 잔여 3000 − 2000 = 995ms,
#       호출당 상한 약 500ms 로 내려간다.
#   재조정 방법: G29 확정 시 위 역산식에 2000ms 를 차감해 재계산하고 이 값을 갱신한다.
#
# ※ urlopen(timeout=) 은 소켓 연산(connect/recv) 단위 무응답 한계지 요청 전체 경과시간의
#   하드 상한이 아니다. 서버가 조금씩 응답을 흘리면 총 경과가 이 값을 넘을 수 있다.
#   현 시점 무해 판단 근거 = memo 왕복 실측 p95 84.1ms(7.2) 로 여유가 18배라 다단계
#   지연이 겹쳐야 예산을 잠식하고, 예산 잠식은 5xx 가 아니라 1차 알림 미발송으로만
#   드러난다(발송 실패 = primary_sent=False 기록, 요청은 정상 응답).
KAKAO_HTTP_TIMEOUT_SECONDS = 1.5

# 카카오 memo(나에게 보내기) 발송 엔드포인트 (kapi = API 도메인, kauth(인증) 와 별개).
KAKAO_MEMO_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"

# text 템플릿의 필수 필드 link(web_url/mobile_web_url 중 최소 1개) 값. 본 알림의 목적은
# 본문 열람이라 이동 대상이 없고, 대시보드 public URL 도 아직 없다(11주차 소관).
# 값 근거 = 2026-09-03 프로브가 이 값으로 HTTP 200 + result_code 0 을 실측했다
# (카카오는 web_url 도메인을 앱 플랫폼에 등록된 것으로 제한할 수 있어, 이미 통과가
#  확인된 값을 그대로 쓰는 것이 최소 위험이다).
# ★ 11주차 교체 지점: 대시보드 public URL 확정 시 이 값을 교체하고 1회 재발송으로 재검증.
KAKAO_LINK_URL = "https://developers.kakao.com"

# ── 1차 알림 본문 (카테고리 7.1) ─────────────────────────────────────────
# decisions.md 7.1 **확정 카피 ② 카카오 알림용** verbatim. 손 전사가 아니라
# git show HEAD:docs/decisions.md 의 코드펜스 블록을 실추출해 옮긴 값이다
# (검증: server/app/tests/test_detect_regression.py 가 decisions.md 원문과 매 실행 대조).
#
# 근거 각인:
#   - 266자 / 603 bytes / 9줄
#   - 2026-09-03 실측: 이 원문 그대로 1회 발송 → HTTP 200 + result_code 0, 카카오톡
#     화면에서 마지막 2줄까지 절단 없이 렌더됨을 육안 확인.
#   - 문서상 "text 템플릿 본문 200자 상한 / 초과 시 말줄임표 절단"은 위 실측으로
#     반증됐다. ★ 이 200자를 근거로 다시 축약·분할하지 말 것. 분할 발송 로직 없음.
#   - "200자가 무엇을 의미하는지"는 확인되지 않았다. 추측을 여기에 적지 않는다.
#     확정 사실은 "266자 text 템플릿이 절단 없이 렌더된다(실측 2026-09-03)" 하나뿐이다.
#   - 재검증 방법: /tmp/ddingdong_copy2_probe.py 컨벤션(repo 밖 1회 발송 스크립트,
#     토큰은 env 경유)으로 1회 발송 후 카카오톡 화면 육안 확인.
FIRE_ALARM_PRIMARY_MESSAGE = "\n".join(
    (
        "🚨[띵동] 화재경보 감지 🚨",
        "지금 화재경보가 울리고 있습니다.",
        "① 즉시 대피 (끄기·신고보다 대피 먼저)",
        "② 엘리베이터 ✕, 비상계단 ◯ / 젖은 천으로 코·입 가리고 낮은 자세로",
        "③ 안전한 곳 도착 후 119 신고",
        "   ▸ 119 영상통화(수어)·문자로 신고 (음성통화 없이 OK) · 「긴급신고 바로앱」 가능",
        "④ 못 나가면 화장실·베란다 창문 쪽으로",
        "   ▸ 휴대폰으로 119에 위치 전송(영상·문자) + 창밖으로 손전등·밝은 천 흔들기",
        "— 소방청 청각장애인 화재 행동요령",
    )
)

# 초인종·노크 본문. ★ 확정 카피 아님 — decisions.md 에 이 두 클래스의 확정 카피는
# 없다(7.1 은 화재경보만 확정). 근거로 삼은 것은 26.3 진입점 1의 시연 문구
# "누군가 노크했어요"와 카테고리 3/5 한글 표기 컨벤션("초인종", "도어벨" 미사용)뿐이다.
# ★ 확정 전까지 잠정값으로 다룰 것. 확정 카피가 등재되면 이 두 줄만 교체한다.
PRIMARY_MESSAGES = {
    "doorbell": "🔔[띵동] 초인종이 울렸어요.",
    "knock": "🔔[띵동] 누군가 노크했어요.",
    "fire_alarm": FIRE_ALARM_PRIMARY_MESSAGE,
}
