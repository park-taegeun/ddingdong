import { useEffect, useState } from "react"
import { Outlet } from "react-router-dom"
import { OnboardingModal } from "@/components/feedback/OnboardingModal"
import { NotificationAnnouncer } from "@/components/notifications/NotificationAnnouncer"
import { Header } from "./Header"
import { Sidebar } from "./Sidebar"

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false)

  // Escape로 모바일 drawer 닫기
  useEffect(() => {
    if (!mobileOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileOpen(false)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [mobileOpen])

  return (
    <div className="flex min-h-screen bg-background-sub">
      {/* 데스크톱 사이드바 */}
      <aside className="hidden lg:block">
        <div className="sticky top-0 h-screen">
          <Sidebar />
        </div>
      </aside>

      {/* 모바일 drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setMobileOpen(false)}
            aria-hidden
          />
          <div className="absolute inset-y-0 left-0 shadow-xl">
            <Sidebar onNavigate={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      {/* 메인 영역 */}
      <div className="flex min-w-0 flex-1 flex-col">
        <Header onMenuClick={() => setMobileOpen(true)} />
        <main className="flex-1 px-4 py-6 lg:px-8">
          <div className="mx-auto w-full max-w-5xl">
            <Outlet />
          </div>
        </main>
      </div>

      <OnboardingModal />

      {/* 신규 알림 스크린리더 announce (어느 페이지든 동작하도록 상시 마운트) */}
      <NotificationAnnouncer />
    </div>
  )
}
