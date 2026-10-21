// 매직 넘버 중앙 관리

// REST 폴링 주기 (decisions.md 카테고리 8: REST 폴링 3초)
export const POLLING_INTERVAL_MS = 3000

// 초인종 등록 시작 요청값 — 잠정.
// 목표 3개 = 옛 설계의 「3~5회 누름」 하한(시연이 가장 짧다).
// 만료 300초 = 3회 × (기기 요청 간격 5초 + 조작 여유) ≈ 1분의 약 5배,
// 서버 상한(600초, server/app/constants.py) 이내.
// 재판정 = 벨 녹음 뒤 목표 개수 결정 · 리허설 동선 실측.
export const REGISTRATION_TARGET_COUNT = 3
export const REGISTRATION_EXPIRES_IN_SECONDS = 300

// 서버 연결 끊김 판정 — 잠정.
// 마지막 성공 응답 뒤 이 시간 동안 새 성공이 없으면 끊김(오류든 무응답이든).
// 폴링 2회분 = 순간 실패 1회로 표시가 깜빡이지 않게 하는 최소 여유.
// 재판정 = ① 부스 리허설에서 깜빡임 · 늦은 표시 관측 ② 폴링 간격 변경 ③ api 타임아웃 도입.
export const STALE_AFTER_MS = POLLING_INTERVAL_MS * 2

// 알림 사진 자동 재시도 — 잠정(2026-10-16 10:03 KST 결정).
// 실패 직후부터 10초 간격 · 최대 6회 = 첫 요청 포함 카드 하나당 최대 7요청, 약 1분 창.
// 1분 = 터널 순간 끊김이 돌아오기를 기다리는 창. 상한이 필요한 이유 = 영영 안 뜨는 사진이 있다 —
// ① 보관 기한(서버 CAPTURE_TTL 72시간)이 지난 사진은 404 ② mock 경로(/static/captures/…)는 404
// ③ 터널 재기동 전 옛 주소로 저장된 사진(26.11(d) — 추정).
// 백그라운드 탭에선 브라우저가 타이머를 늦춰 창이 1분보다 길어질 수 있다(결함 아님).
// 재판정 = ① 부스 리허설에서 터널 복구 시간 · 깜빡임 관측 ② 사용자 불편 보고 ③ 사진 서빙 경로 변경.
export const IMAGE_RETRY_INTERVAL_MS = 10_000
export const IMAGE_RETRY_MAX = 6

// 알림 화면 「이전 알림 더 보기」 — 잠정(2026-10-16 13:05 KST 결정).
// 누를 때마다 알림 화면이 폴링으로 받는 개수를 단위만큼 늘린다(최대까지). 이어 붙이지 않고
// 매 폴링이 서버 목록 그대로다. 두 값은 서버 server/app/constants.py 의 DEFAULT_PAGE_LIMIT ·
// MAX_PAGE_LIMIT 를 그대로 따른다 — 서버가 최대로 자르므로 「최근 알림 N개까지」 문구가 사실이려면
// 같아야 한다. 대조 가드 = server/app/tests/test_detect_regression.py DashboardPageLimitMatchesServerTest.
// 재판정 = ① 서버 상한 변경 ② 최대 개수 폴링 응답 크기 부담 ③ 사용자 불편 보고.
export const NOTIFICATIONS_PAGE_STEP = 20
export const NOTIFICATIONS_PAGE_MAX = 100

// 화재 카드 흔들림 · 테두리 맥동을 보여 줄 「감지 후 최근」 창 — 잠정(2026-10-21 결정 · 머지 전 사용자 확인).
// 근거(논증) = 화재 1차 카톡을 받은 사용자가 대시보드를 열어 확인하는 시간 창. 그 뒤에도 지난 기록이 계속
// 흔들리면 읽기를 방해하고 「지금 화재」로 오인된다. 경보가 이어져 다시 감지되면 새 행이 생겨 다시 움직인다.
// 판정 = 감지 시각 원값과 지금의 차이(표시 반올림 무관 — 8.5(k)). 「움직임 줄이기」 설정이 항상 먼저다.
// 재판정 = ① 부스 리허설 화면 확인 ② 화재 반복 감지 관측(경보가 이어질 때 행 간격이 이 창보다 긴지).
export const FIRE_MOTION_WINDOW_MS = 10 * 60 * 1000
