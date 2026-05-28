import { NotificationList } from "@/components/notifications/NotificationList"
import { useNotifications } from "@/hooks/useNotifications"
import { formatRelativeTime } from "@/lib/format"

export function NotificationsPage() {
  const { notifications, isLoading, error, lastUpdated } = useNotifications()

  return (
    <div className="space-y-4">
      <header className="flex items-end justify-between gap-2">
        <div>
          <h1 className="text-h1 font-bold">알림</h1>
          <p className="mt-1 text-body text-foreground-secondary">
            감지된 모든 소리를 최신순으로 보여드려요.
          </p>
        </div>
        {lastUpdated && (
          <span className="shrink-0 text-caption text-foreground-secondary">
            업데이트 {formatRelativeTime(lastUpdated.toISOString())}
          </span>
        )}
      </header>

      <NotificationList
        notifications={notifications}
        isLoading={isLoading}
        error={error}
      />
    </div>
  )
}
