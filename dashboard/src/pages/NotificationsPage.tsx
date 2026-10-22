import { useEffect, useRef } from "react"
import { NotificationList } from "@/components/notifications/NotificationList"
import { Button } from "@/components/ui/button"
import { useNotificationsPage } from "@/hooks/useNotificationsPage"
import { NOTIFICATIONS_PAGE_MAX } from "@/lib/constants"
import { formatRelativeTime } from "@/lib/format"
import type { LoadMoreState } from "@/lib/load-more"

export function NotificationsPage() {
  const { notifications, isLoading, error, lastUpdated, loadState, loadMore } =
    useNotificationsPage()

  return (
    <div className="space-y-4">
      <header className="flex items-end justify-between gap-2">
        <div>
          <h1 className="text-h1 font-bold">알림</h1>
          <p className="mt-1 text-body text-foreground-secondary">
            최근 감지된 소리를 최신순으로 보여드려요.
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
        lastUpdated={lastUpdated}
        groupByDay
      />

      {notifications.length > 0 && loadState && (
        <LoadMore state={loadState} onLoadMore={loadMore} />
      )}
    </div>
  )
}

// 목록 아래 버튼 영역. 새 aria-live 는 두지 않는다(안내 채널은 NotificationAnnouncer 하나).
function LoadMore({ state, onLoadMore }: { state: LoadMoreState; onLoadMore: () => void }) {
  const buttonRef = useRef<HTMLButtonElement>(null)
  const messageRef = useRef<HTMLParagraphElement>(null)
  // 누른 뒤 첫 확정 상태에서 포커스를 이어 준다 — 불러오는 동안 버튼이 disabled 라 포커스가
  // 빠지므로, 버튼으로 돌아오면 버튼에 · 끝 · 최대치 문구로 바뀌면 그 문구에 둔다.
  const pressedRef = useRef(false)

  useEffect(() => {
    if (!pressedRef.current || state === "loading") return
    pressedRef.current = false
    ;(state === "button" ? buttonRef : messageRef).current?.focus()
  }, [state])

  if (state === "end" || state === "max") {
    return (
      <p
        ref={messageRef}
        tabIndex={-1}
        className="py-2 text-center text-body text-foreground-secondary"
      >
        {state === "end"
          ? "모든 알림을 다 봤어요."
          : `최근 알림 ${NOTIFICATIONS_PAGE_MAX}개까지 볼 수 있어요.`}
      </p>
    )
  }

  const loading = state === "loading"
  return (
    <Button
      ref={buttonRef}
      variant="outline"
      className="h-btn w-full text-body"
      disabled={loading}
      aria-busy={loading}
      onClick={() => {
        pressedRef.current = true
        onLoadMore()
      }}
    >
      이전 알림 더 보기
    </Button>
  )
}
