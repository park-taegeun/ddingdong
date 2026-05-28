import { Bar, BarChart, CartesianGrid, XAxis } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import type { ChartConfig } from "@/components/ui/chart"
import { StatsCardsSection } from "@/components/stats/StatsCardsSection"
import { useStats } from "@/hooks/useStats"

const chartConfig = {
  count: { label: "감지", color: "var(--color-primary)" },
} satisfies ChartConfig

export function StatsPage() {
  const { stats } = useStats()

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-h1 font-bold">통계</h1>
        <p className="mt-1 text-body text-foreground-secondary">
          오늘 하루 감지·알림 현황을 자세히 보여드려요.
        </p>
      </header>

      <StatsCardsSection />

      {stats && (
        <Card>
          <CardHeader>
            <CardTitle className="text-h3">시간대별 감지</CardTitle>
          </CardHeader>
          <CardContent>
            <ChartContainer config={chartConfig} className="h-56 w-full">
              <BarChart
                accessibilityLayer
                data={stats.hourly_distribution}
                margin={{ left: 0, right: 0, top: 8 }}
              >
                <CartesianGrid vertical={false} />
                <XAxis
                  dataKey="hour"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  interval={2}
                  tickFormatter={(h: string) => `${Number(h)}시`}
                />
                <ChartTooltip
                  content={<ChartTooltipContent labelFormatter={(h) => `${Number(h)}시`} />}
                />
                <Bar dataKey="count" fill="var(--color-count)" radius={4} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
