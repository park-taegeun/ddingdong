import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatPercent } from "@/lib/format"
import { CLASS_META, PREDICTED_CLASS_ORDER } from "@/lib/notification-meta"
import { cn } from "@/lib/utils"
import type { ClassDistribution } from "@/types/stats"

export function ClassDistributionCard({
  distribution,
}: {
  distribution: ClassDistribution
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-h3">소리 종류별 분포</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {PREDICTED_CLASS_ORDER.map((cls) => {
          const meta = CLASS_META[cls]
          const item = distribution[cls]
          const Icon = meta.icon
          return (
            <div key={cls}>
              <div className="mb-2 flex items-center gap-2">
                <span
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-lg",
                    meta.bgColor,
                  )}
                >
                  <Icon className={cn("h-4 w-4", meta.iconColor)} aria-hidden />
                </span>
                <span className="text-body font-medium">{meta.label}</span>
                <span className="ml-auto text-body font-bold tabular-nums">
                  {item.count}건
                </span>
                <span className="w-14 text-right text-caption text-foreground-secondary tabular-nums">
                  {formatPercent(item.percentage)}
                </span>
              </div>
              <div
                className="h-2.5 overflow-hidden rounded-full bg-background-sub"
                role="progressbar"
                aria-valuenow={Math.round(item.percentage)}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${meta.label} 비율`}
              >
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${item.percentage}%`,
                    backgroundColor: meta.chartVar,
                  }}
                />
              </div>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
