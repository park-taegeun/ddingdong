import { ChevronRight } from "lucide-react"
import { Link } from "react-router-dom"
import { HelpTooltip } from "@/components/feedback/HelpTooltip"
import { NotificationList } from "@/components/notifications/NotificationList"
import { StatsCardsSection } from "@/components/stats/StatsCardsSection"
import { useNotifications } from "@/hooks/useNotifications"

export function HomePage() {
  const { notifications, isLoading, error } = useNotifications()

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-h1 font-bold">오늘 현관 소식</h1>
        <p className="mt-1 text-body text-foreground-secondary">
          실시간으로 감지된 소리와 알림 현황이에요.
        </p>
      </header>

      <section className="space-y-3">
        <div className="flex items-center gap-1.5">
          <h2 className="text-h2 font-bold">오늘 통계</h2>
          <HelpTooltip>
            3초마다 자동으로 새로고침돼요. 숫자는 오늘 0시부터 누적된 값이에요.
          </HelpTooltip>
        </div>
        <StatsCardsSection />
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-h2 font-bold">최근 알림</h2>
          <Link
            to="/notifications"
            className="flex items-center gap-0.5 text-body font-medium text-primary hover:underline"
          >
            전체 보기
            <ChevronRight className="h-4 w-4" aria-hidden />
          </Link>
        </div>
        <NotificationList
          notifications={notifications}
          isLoading={isLoading}
          error={error}
          limit={3}
        />
      </section>
    </div>
  )
}
