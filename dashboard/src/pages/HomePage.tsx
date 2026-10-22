import { ChevronRight } from "lucide-react"
import { Link } from "react-router-dom"
import { HelpTooltip } from "@/components/feedback/HelpTooltip"
import { NotificationList } from "@/components/notifications/NotificationList"
import { StatsCardsSection } from "@/components/stats/StatsCardsSection"
import { SystemHealthSummaryCard } from "@/components/stats/SystemHealthSummaryCard"
import { useDevice } from "@/hooks/useDevice"
import { useNotifications } from "@/hooks/useNotifications"
import { useUnread } from "@/hooks/useUnread"

export function HomePage() {
  const { notifications, isLoading, error, lastUpdated } = useNotifications()
  // 빈 상태(알림 0건, 정상)일 때 안심 카드로 대체. system_health = useDevice(stats 파생).
  // ※ 폴러 통합은 deferred(decisions.md 8.3) — 본 PR 비범위, 기존 useDevice 패턴 재사용.
  const { health } = useDevice()
  // 홈은 표식만 보여 주고 지우지 않는다 — 확인은 알림 화면에서.
  const { lastSeenMs } = useUnread()

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-h1 font-bold">오늘 현관 소식</h1>
        <p className="mt-1 text-body text-foreground-secondary">
          실시간으로 감지된 소리와 알림 현황이에요.
        </p>
      </header>

      {/* 최근 알림이 먼저 — 「누가 왔었나」가 첫 질문이다(통계는 그 다음). */}
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
          lastUpdated={lastUpdated}
          limit={3}
          newSince={lastSeenMs}
          emptySlot={
            health ? <SystemHealthSummaryCard health={health} /> : undefined
          }
        />
      </section>

      <section className="space-y-3">
        <div className="flex items-center gap-1.5">
          <h2 className="text-h2 font-bold">오늘 통계</h2>
          <HelpTooltip>
            3초마다 자동으로 새로고침돼요. 숫자는 오늘 0시부터 누적된 값이에요.
          </HelpTooltip>
        </div>
        <StatsCardsSection />
      </section>
    </div>
  )
}
