import { useEffect, useRef, useState } from "react"
import {
  FilterEmpty,
  NotificationFilterBar,
} from "@/components/notifications/NotificationFilterBar"
import { NotificationList } from "@/components/notifications/NotificationList"
import { Button } from "@/components/ui/button"
import { useNotificationsPage } from "@/hooks/useNotificationsPage"
import { useUnread } from "@/hooks/useUnread"
import { NOTIFICATIONS_PAGE_MAX } from "@/lib/constants"
import { formatRelativeTime } from "@/lib/format"
import type { LoadMoreState } from "@/lib/load-more"
import { filterNotifications, filterSummary } from "@/lib/notification-filter"
import type { ClassFilter } from "@/lib/notification-filter"

export function NotificationsPage() {
  const { notifications, isLoading, error, lastUpdated, loadState, loadMore } =
    useNotificationsPage()
  // 필터 = 화면 상태만(새로고침 · 다른 화면에 다녀오면 초기화). 저장하지 않는다 — 걸린 줄 모르고 다음에 열면
  // 화재 · 초인종 알림을 놓칠 수 있다. 거르는 범위 = 불러온 알림 안(서버 API 무변경).
  const [cls, setCls] = useState<ClassFilter>("all")
  const [sentOnly, setSentOnly] = useState(false)
  const allChipRef = useRef<HTMLButtonElement>(null)
  // 새 알림 표식 해제 = 들어올 때 · 나갈 때 마지막 확인 시각 갱신. 표식 기준은 들어올 때의 값으로 고정해
  // 이 방문 동안은 표식이 남는다(켜 둔 채 새로 온 알림에도 붙는다) — 화면을 나가면 사라진다.
  const { lastSeenMs, markSeen } = useUnread()
  const [newSince] = useState(lastSeenMs)
  useEffect(() => {
    markSeen()
    return markSeen
  }, [markSeen])
  const filtering = cls !== "all" || sentOnly
  const shown = filterNotifications(notifications, cls, sentOnly)
  const clearFilter = () => {
    setCls("all")
    setSentOnly(false)
    allChipRef.current?.focus()
  }

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

      {notifications.length > 0 && (
        <div className="space-y-2">
          <NotificationFilterBar
            cls={cls}
            sentOnly={sentOnly}
            onClsChange={setCls}
            onSentOnlyChange={setSentOnly}
            allChipRef={allChipRef}
          />
          {filtering && (
            <p className="text-caption text-foreground-secondary tabular-nums">
              {filterSummary(notifications.length, shown.length)}
            </p>
          )}
        </div>
      )}

      <NotificationList
        notifications={shown}
        isLoading={isLoading}
        error={error}
        lastUpdated={lastUpdated}
        groupByDay
        newSince={newSince}
        collapseOther
        // 불러온 알림은 있는데 거른 결과가 0건 — 「알림이 없다」가 아니라 「불러온 것 중에 없다」.
        emptySlot={notifications.length > 0 ? <FilterEmpty onClear={clearFilter} /> : undefined}
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
