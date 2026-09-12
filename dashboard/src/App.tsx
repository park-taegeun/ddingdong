import { lazy, Suspense } from "react"
import { BrowserRouter, Route, Routes } from "react-router-dom"
import { LoadingSkeleton } from "@/components/feedback/LoadingSkeleton"
import { AppShell } from "@/components/layout/AppShell"
import { HelpPage } from "@/pages/HelpPage"
import { HomePage } from "@/pages/HomePage"
import { LandingPage } from "@/pages/LandingPage"
import { NotFoundPage } from "@/pages/NotFoundPage"
import { NotificationsPage } from "@/pages/NotificationsPage"
import { SettingsPage } from "@/pages/SettingsPage"

// 차트(recharts) 의존이 큰 통계 페이지는 분할 로딩 → 초기 번들 축소
const StatsPage = lazy(() =>
  import("@/pages/StatsPage").then((m) => ({ default: m.StatsPage })),
)

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* `/` = 랜딩(AppShell 밖 — 사이드바·헤더 없는 전체 화면).
            대시보드 홈은 `/home`. 나머지 4개 경로는 기존 그대로다. */}
        <Route path="/" element={<LandingPage />} />
        <Route element={<AppShell />}>
          <Route path="home" element={<HomePage />} />
          <Route path="notifications" element={<NotificationsPage />} />
          <Route
            path="stats"
            element={
              <Suspense fallback={<LoadingSkeleton variant="stats" count={4} />}>
                <StatsPage />
              </Suspense>
            }
          />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="help" element={<HelpPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
