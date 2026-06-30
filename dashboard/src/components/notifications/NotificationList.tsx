import { BellOff, TriangleAlert } from "lucide-react"
import type { ReactNode } from "react"
import { EmptyState } from "@/components/feedback/EmptyState"
import { LoadingSkeleton } from "@/components/feedback/LoadingSkeleton"
import type { NotificationItem } from "@/types/notification"
import { NotificationCard } from "./NotificationCard"

interface NotificationListProps {
  notifications: NotificationItem[]
  isLoading: boolean
  error: Error | null
  // 지정 시 최신 N건만 노출 (홈 화면 요약용)
  limit?: number
  // 정상 빈 상태(0건, 에러 아님) 전용 대체 노출. 로딩/에러 분기는 무영향.
  // 홈 = 시스템 건강 안심 카드, 그 외 = 기본 "아직 알림이 없어요" 유지.
  emptySlot?: ReactNode
}

export function NotificationList({
  notifications,
  isLoading,
  error,
  limit,
  emptySlot,
}: NotificationListProps) {
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
      {items.map((notification) => (
        <NotificationCard
          key={notification.request_id}
          notification={notification}
        />
      ))}
    </div>
  )
}
