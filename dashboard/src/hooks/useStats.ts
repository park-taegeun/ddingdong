// 통계 폴링 훅 (3초).

import { fetchStats } from "@/lib/api"
import { POLLING_INTERVAL_MS } from "@/lib/constants"
import { usePolling } from "./usePolling"
import type { StatsResponse } from "@/types/stats"

export function useStats() {
  const { data, isLoading, error, lastUpdated, refetch } =
    usePolling<StatsResponse>(fetchStats, POLLING_INTERVAL_MS)

  return { stats: data, isLoading, error, lastUpdated, refetch }
}
