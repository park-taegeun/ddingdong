import { BellOff, TriangleAlert } from "lucide-react"
import type { ReactNode } from "react"
import { EmptyState } from "@/components/feedback/EmptyState"
import { LoadingSkeleton } from "@/components/feedback/LoadingSkeleton"
import { StaleDataNotice } from "@/components/feedback/StaleDataNotice"
import { useStale } from "@/hooks/useStale"
import { groupByDay } from "@/lib/notification-filter"
import type { NotificationItem } from "@/types/notification"
import { NotificationCard } from "./NotificationCard"

interface NotificationListProps {
  notifications: NotificationItem[]
  isLoading: boolean
  error: Error | null
  // 마지막 성공 응답 시각 — 끊김 판정용(useNotifications 그대로 전달).
  lastUpdated: Date | null
  // 지정 시 최신 N건만 노출 (홈 화면 요약용)
  limit?: number
  // 정상 빈 상태(0건, 에러 아님) 전용 대체 노출. 로딩/에러 분기는 무영향.
  // 홈 = 시스템 건강 안심 카드, 그 외 = 기본 "아직 알림이 없어요" 유지.
  emptySlot?: ReactNode
  // 날짜 묶음 머리(오늘 · 어제 · 10월 19일) — 알림 화면만. 홈은 현행(묶지 않음).
  groupByDay?: boolean
}

export function NotificationList({
  notifications,
  isLoading,
  error,
  lastUpdated,
  limit,
  emptySlot,
  groupByDay: grouped = false,
}: NotificationListProps) {
  const stale = useStale(lastUpdated, error)

  if (isLoading && notifications.length === 0) {
    return <LoadingSkeleton variant="list" count={limit ?? 4} />
  }

  if (error && notifications.length === 0) {
    return (
      <EmptyState
        tone="error"
        icon={TriangleAlert}
        title="알림을 불러오지 못했어요"
        description="잠시 후 다시 시도합니다."
      />
    )
  }

  if (notifications.length === 0) {
    if (emptySlot) return <>{emptySlot}</>
    return (
      <EmptyState
        icon={BellOff}
        title="아직 알림이 없어요"
        description="현관에서 소리가 감지되면 여기에 표시됩니다."
      />
    )
  }

  const items = limit ? notifications.slice(0, limit) : notifications

  return (
    <div className="space-y-3">
      {/* 끊김이면 옛 목록 위에 안내 — 새 알림이 안 와도 모르는 상태를 막는다. */}
      {stale && <StaleDataNotice lastUpdated={lastUpdated} />}
      {grouped
        ? groupByDay(items).map((group) => (
            // 머리 = h2 — 페이지 제목(h1)과 카드 제목(h3) 사이 계층.
            <section key={group.heading} className="space-y-3">
              <h2 className="pt-2 text-body font-bold text-foreground-secondary">{group.heading}</h2>
              {group.items.map((notification) => (
                <NotificationCard key={notification.request_id} notification={notification} />
              ))}
            </section>
          ))
        : items.map((notification) => (
            <NotificationCard
              key={notification.request_id}
              notification={notification}
            />
          ))}
    </div>
  )
}
