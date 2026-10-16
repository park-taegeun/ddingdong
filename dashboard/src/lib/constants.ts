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
