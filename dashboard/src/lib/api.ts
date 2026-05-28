// ⭐ Phase 1 → Phase 2 전환 단일 지점 ⭐
// Phase 1: mock 데이터를 Promise로 반환 (fetch 흉내).
// Phase 2: 아래 두 함수 본문만 실제 fetch로 교체하면 전체 대시보드가 실 서버로 전환.
//   예)
//   const base = import.meta.env.VITE_API_BASE_URL
//   const token = import.meta.env.VITE_DASHBOARD_TOKEN
//   const res = await fetch(`${base}${API_ENDPOINTS.notifications}`, {
//     headers: { Authorization: `Bearer ${token}` },
//   })
//   if (!res.ok) throw new Error(`알림 조회 실패 (${res.status})`)
//   const json: NotificationsApiResponse = await res.json()
//   return json.notifications

import type { NotificationItem } from "@/types/notification"
import type { StatsResponse } from "@/types/stats"
import { MOCK_LATENCY_MS } from "./constants"
import { MOCK_NOTIFICATIONS, MOCK_STATS } from "./mock-data"

function withLatency<T>(value: T): Promise<T> {
  return new Promise((resolve) => {
    setTimeout(() => resolve(value), MOCK_LATENCY_MS)
  })
}

export function fetchNotifications(): Promise<NotificationItem[]> {
  return withLatency(MOCK_NOTIFICATIONS)
}

export function fetchStats(): Promise<StatsResponse> {
  return withLatency(MOCK_STATS)
}
