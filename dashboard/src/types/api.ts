// API 엔드포인트 + 응답 래퍼 타입 (SSoT: 위임 프롬프트 섹션 4)

import type { NotificationItem } from "./notification"

// Phase 1 = mock, Phase 2 = 실제 서버. 경로는 동일하게 유지.
export const API_ENDPOINTS = {
  // ESP32 → 서버 (대시보드 무관, 참조용)
  detect: "/api/v1/detect",
  enrich: "/api/v1/enrich",
  // 대시보드 폴링 대상
  notifications: "/api/v1/notifications",
  stats: "/api/v1/stats",
} as const

export interface NotificationsApiResponse {
  notifications: NotificationItem[]
  // cursor pagination 메타 (백엔드 routes.py list_notifications additive 필드).
  // 현재 대시보드는 전체 폴링이라 미사용이나, 무한 스크롤 대비 타입으로 보존.
  next_cursor: string | null
  has_more: boolean
}
