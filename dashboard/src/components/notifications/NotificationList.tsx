import { BellOff, ChevronDown, TriangleAlert } from "lucide-react"
import { useState } from "react"
import type { ReactNode } from "react"
import { EmptyState } from "@/components/feedback/EmptyState"
import { LoadingSkeleton } from "@/components/feedback/LoadingSkeleton"
import { StaleDataNotice } from "@/components/feedback/StaleDataNotice"
import { useStale } from "@/hooks/useStale"
import { formatDetectedAt } from "@/lib/format"
import { groupByDay } from "@/lib/notification-filter"
import { CLASS_META } from "@/lib/notification-meta"
import { isNewNotification } from "@/lib/unread"
import { cn } from "@/lib/utils"
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
  // 이 시각보다 뒤에 감지된 발송 시도 행에 「새 알림」 표식(lib/unread.ts). 없으면 표식 0.
  newSince?: number
  // 기타 소리 행을 한 줄로 줄인다(누르면 펼침) — 알림 화면만. 홈은 현행.
  collapseOther?: boolean
}

export function NotificationList({
  notifications,
  isLoading,
  error,
  lastUpdated,
  limit,
  emptySlot,
  groupByDay: grouped = false,
  newSince,
  collapseOther = false,
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
  const isNew = (n: NotificationItem) => newSince !== undefined && isNewNotification(n, newSince)
  // 줄이는 것은 기타 소리뿐 — 화재 · 초인종 · 노크는 늘 전체 카드다.
  const row = (n: NotificationItem) =>
    collapseOther && n.predicted_class === "other" ? (
      <OtherRow key={n.request_id} notification={n} />
    ) : (
      <NotificationCard key={n.request_id} notification={n} isNew={isNew(n)} />
    )

  return (
    <div className="space-y-3">
      {/* 끊김이면 옛 목록 위에 안내 — 새 알림이 안 와도 모르는 상태를 막는다. */}
      {stale && <StaleDataNotice lastUpdated={lastUpdated} />}
      {grouped
        ? groupByDay(items).map((group) => (
            // 머리 = h2 — 페이지 제목(h1)과 카드 제목(h3) 사이 계층.
            <section key={group.heading} className="space-y-3">
              <h2 className="pt-2 text-body font-bold text-foreground-secondary">{group.heading}</h2>
              {group.items.map(row)}
            </section>
          ))
        : items.map(row)}
    </div>
  )
}

// 기타 소리 한 줄(감사 UX-D29) — 숨기지 않고(33.17(f)①) 줄여 보인다. 누르면 원래 카드가 아래에 펼쳐진다.
// 펼침 상태 = 행마다(key = request_id라 폴링에도 유지) · 화면을 나가면 다시 접힌다.
function OtherRow({ notification }: { notification: NotificationItem }) {
  const [open, setOpen] = useState(false)
  const meta = CLASS_META.other
  return (
    <div className="space-y-2">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex min-h-touch w-full items-center gap-3 rounded-2xl border border-border bg-background px-4 py-2 text-left"
      >
        <meta.icon className={cn("h-5 w-5 shrink-0", meta.iconColor)} aria-hidden />
        <span className="text-body font-medium">{meta.label}</span>
        <time className="text-caption text-foreground-secondary tabular-nums" dateTime={notification.detected_at}>
          {formatDetectedAt(notification.detected_at)}
        </time>
        <span className="ml-auto text-caption text-foreground-secondary">알림 안 보냄</span>
        <ChevronDown
          className={cn("h-4 w-4 shrink-0 text-foreground-secondary", open && "rotate-180")}
          aria-hidden
        />
      </button>
      {open && <NotificationCard notification={notification} />}
    </div>
  )
}
