// 알림 화면 날짜 묶음 · 종류 필터 — 순수 함수. 화면에 불러온 알림 안에서만 다룬다(서버 API 무변경).
import { formatDayHeading } from "@/lib/format"
import type { NotificationItem } from "@/types/notification"

export interface DayGroup {
  heading: string
  items: NotificationItem[]
}

// 최신순 목록을 이웃한 같은 날끼리 묶는다(머리 = formatDayHeading). 날마다 머리가 달라 머리가 곧 키다.
export function groupByDay(items: NotificationItem[], now: Date = new Date()): DayGroup[] {
  const groups: DayGroup[] = []
  for (const item of items) {
    const heading = formatDayHeading(item.detected_at, now)
    const last = groups[groups.length - 1]
    if (last && last.heading === heading) last.items.push(item)
    else groups.push({ heading, items: [item] })
  }
  return groups
}
