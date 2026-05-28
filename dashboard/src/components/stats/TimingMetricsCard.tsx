import { Clock } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatMs, formatRate } from "@/lib/format"
import type { TimingMetrics } from "@/types/stats"

export function TimingMetricsCard({ metrics }: { metrics: TimingMetrics }) {
  const columns = [
    {
      title: "1차 알림",
      avg: metrics.primary_notification_avg_ms,
      max: metrics.primary_notification_max_ms,
      rate: metrics.primary_under_5s_rate,
      slaLabel: "5초 이내",
    },
    {
      title: "2차 알림",
      avg: metrics.secondary_notification_avg_ms,
      max: metrics.secondary_notification_max_ms,
      rate: metrics.secondary_under_15s_rate,
      slaLabel: "15초 이내",
    },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-h3">
          <Clock className="h-5 w-5 text-primary" aria-hidden />
          알림 속도
        </CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-3">
        {columns.map((col) => (
          <div key={col.title} className="rounded-xl bg-background-sub p-4">
            <p className="text-caption font-medium text-foreground-secondary">
              {col.title}
            </p>
            <p className="mt-1 text-h2 font-bold tabular-nums">
              {formatMs(col.avg)}
            </p>
            <p className="text-caption text-foreground-secondary">
              최대 {formatMs(col.max)}
            </p>
            <p className="mt-2 text-caption">
              <span className="font-bold text-success tabular-nums">
                {formatRate(col.rate)}
              </span>
              <span className="text-foreground-secondary"> {col.slaLabel}</span>
            </p>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
