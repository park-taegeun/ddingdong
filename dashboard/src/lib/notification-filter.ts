// 알림 화면 날짜 묶음 · 종류 필터 — 순수 함수. 화면에 불러온 알림 안에서만 다룬다(서버 API 무변경).
import { formatDayHeading } from "@/lib/format"
import type { NotificationItem, PredictedClass } from "@/types/notification"

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

export type ClassFilter = PredictedClass | "all"

// 종류 · 「보낸 알림만」(1차 카톡 발송 = primary_sent) 두 조건을 모두 만족하는 행만.
export function filterNotifications(
  items: NotificationItem[],
  cls: ClassFilter,
  sentOnly: boolean,
): NotificationItem[] {
  return items.filter(
    (n) =>
      (cls === "all" || n.predicted_class === cls) &&
      (!sentOnly || n.notification_status.primary_sent),
  )
}

// 거른 결과 안내 — 범위(불러온 알림)를 함께 말한다. 더 불러오면 늘 수 있어 「전부 M건」으로 단정하지 않는다.
export function filterSummary(loaded: number, shown: number): string {
  return `불러온 알림 ${loaded}건 중 ${shown}건`
}
