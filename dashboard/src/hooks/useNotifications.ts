// 알림 목록 폴링 훅 (3초). detected_at 내림차순(최신 우선) 정렬해 반환.

import { useMemo } from "react"
import { fetchNotifications } from "@/lib/api"
import { POLLING_INTERVAL_MS } from "@/lib/constants"
import { usePolling } from "./usePolling"
import type { NotificationItem } from "@/types/notification"

export function useNotifications() {
  const { data, isLoading, error, lastUpdated, refetch } = usePolling<
    NotificationItem[]
  >(fetchNotifications, POLLING_INTERVAL_MS)

  const notifications = useMemo(() => {
    if (!data) return []
    return [...data].sort(
      (a, b) =>
        new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime(),
    )
  }, [data])

  return { notifications, isLoading, error, lastUpdated, refetch }
}
