import { Activity } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatConfidence } from "@/lib/format"
import type { StatsSummary } from "@/types/stats"

export function TotalDetectionsCard({ summary }: { summary: StatsSummary }) {
  const subStats = [
    { label: "알림 발송", value: `${summary.total_notifications_sent}건` },
    { label: "발송 제외", value: `${summary.skip_count}건` },
    { label: "평균 신뢰도", value: formatConfidence(summary.average_confidence) },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-h3">
          <Activity className="h-5 w-5 text-primary" aria-hidden />
          오늘 감지
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-display font-bold tabular-nums">
          {summary.total_detections}
          <span className="ml-1 text-body font-medium text-foreground-secondary">
            건
          </span>
        </p>
        <div className="mt-4 grid grid-cols-3 gap-2">
          {subStats.map((stat) => (
            <div
              key={stat.label}
              className="rounded-xl bg-background-sub p-3 text-center"
            >
              <p className="text-h3 font-bold tabular-nums">{stat.value}</p>
              <p className="mt-0.5 text-caption text-foreground-secondary">
                {stat.label}
              </p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
