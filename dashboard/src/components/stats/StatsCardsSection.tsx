import { TriangleAlert } from "lucide-react"
import { EmptyState } from "@/components/feedback/EmptyState"
import { LoadingSkeleton } from "@/components/feedback/LoadingSkeleton"
import { useStats } from "@/hooks/useStats"
import { ClassDistributionCard } from "./ClassDistributionCard"
import { SystemHealthCard } from "./SystemHealthCard"
import { TimingMetricsCard } from "./TimingMetricsCard"
import { TotalDetectionsCard } from "./TotalDetectionsCard"

// HomePage + StatsPage 공통 통계 블록 (DRY 단일 출처).
export function StatsCardsSection() {
  const { stats, isLoading, error } = useStats()

  if (isLoading && !stats) {
    return <LoadingSkeleton variant="stats" count={4} />
  }

  if (error && !stats) {
    return (
      <EmptyState
        tone="error"
        icon={TriangleAlert}
        title="통계를 불러오지 못했어요"
        description="잠시 후 다시 시도합니다."
      />
    )
  }

  if (!stats) return null

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <TotalDetectionsCard summary={stats.summary} />
      <ClassDistributionCard distribution={stats.class_distribution} />
      <TimingMetricsCard metrics={stats.timing_metrics} />
      <SystemHealthCard health={stats.system_health} />
    </div>
  )
}
