// 알림 화면 전용 폴링 훅 (3초) — 「이전 알림 더 보기」로 받는 개수를 늘린다.
// 스크린리더 안내 · 홈은 useNotifications 를 그대로 쓴다(이 훅과 별개 구독).

import { useEffect, useMemo, useState } from "react"
import { fetchNotificationsPage } from "@/lib/api"
import {
  NOTIFICATIONS_PAGE_MAX,
  NOTIFICATIONS_PAGE_STEP,
  POLLING_INTERVAL_MS,
} from "@/lib/constants"
import { loadMoreState, nextLimit } from "@/lib/load-more"
import { usePolling } from "./usePolling"

export function useNotificationsPage() {
  const [limit, setLimit] = useState(NOTIFICATIONS_PAGE_STEP)
  const { data, isLoading, error, lastUpdated, refetch } = usePolling(
    () => fetchNotificationsPage(limit),
    POLLING_INTERVAL_MS,
  )

  // 개수가 바뀐 렌더 뒤에 한 번 바로 부른다 — 클릭 핸들러 안에서 부르면 usePolling 의
  // fetcherRef 가 아직 옛 개수라 옛 개수로 한 번 더 부른다. 첫 개수는 usePolling 이 마운트 때 부른다.
  // 클릭 직전에 떠난 옛 개수 응답이 늦게 오면 다음 폴링(≤ 3초)까지 목록이 줄 수 있다 — 그동안
  // 상태는 「불러오는 중」으로 남고(요청 > 받은 limit) 다음 폴링이 고친다. 막지 않는다.
  useEffect(() => {
    if (limit > NOTIFICATIONS_PAGE_STEP) refetch()
  }, [limit, refetch])

  // useNotifications 와 같은 규칙 — detected_at 내림차순(최신 우선).
  const notifications = useMemo(() => {
    if (!data) return []
    return [...data.notifications].sort(
      (a, b) =>
        new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime(),
    )
  }, [data])

  const loadState = data
    ? loadMoreState(limit, data.limit, data.hasMore, NOTIFICATIONS_PAGE_MAX)
    : null
  const loadMore = () =>
    setLimit((l) => nextLimit(l, NOTIFICATIONS_PAGE_STEP, NOTIFICATIONS_PAGE_MAX))

  return { notifications, isLoading, error, lastUpdated, loadState, loadMore }
}
