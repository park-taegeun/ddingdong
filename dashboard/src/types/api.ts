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
}
