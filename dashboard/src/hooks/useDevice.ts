// 디바이스 상태 훅 — stats.system_health에서 파생 (Header 온라인 인디케이터 등).
// Phase 1은 useStats를 재사용해 별도 엔드포인트 없이 system_health만 추출.

import { useStats } from "./useStats"
import type { SystemHealth } from "@/types/stats"

export function useDevice() {
  const { stats, isLoading, error, lastUpdated } = useStats()
  const health: SystemHealth | null = stats?.system_health ?? null

  return {
    health,
    isOnline: health?.device_status === "online",
    isLoading,
    error,
    lastUpdated,
  }
}
