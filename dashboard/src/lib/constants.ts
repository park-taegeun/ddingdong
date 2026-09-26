// 매직 넘버 중앙 관리

// REST 폴링 주기 (decisions.md 카테고리 8: REST 폴링 3초)
export const POLLING_INTERVAL_MS = 3000

// 디바이스 ID (Phase 1 mock 단일 디바이스)
export const DEVICE_ID = "ddingdong-a3f2c1"

// 초인종 등록 시작 요청값 — 잠정.
// 목표 3개 = 옛 설계의 「3~5회 누름」 하한(시연이 가장 짧다).
// 만료 300초 = 3회 × (기기 요청 간격 5초 + 조작 여유) ≈ 1분의 약 5배,
// 서버 상한(600초, server/app/constants.py) 이내.
// 재판정 = 벨 녹음 뒤 목표 개수 결정 · 리허설 동선 실측.
export const REGISTRATION_TARGET_COUNT = 3
export const REGISTRATION_EXPIRES_IN_SECONDS = 300
