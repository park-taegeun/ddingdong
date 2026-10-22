import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Outlet } from "react-router-dom"
import { Dialog as DialogPrimitive } from "radix-ui"
import { OnboardingModal } from "@/components/feedback/OnboardingModal"
import { StatusBanner } from "@/components/feedback/StatusBanner"
import { NotificationAnnouncer } from "@/components/notifications/NotificationAnnouncer"
import { useDevice } from "@/hooks/useDevice"
import { useNotifications } from "@/hooks/useNotifications"
import { useReducedMotion } from "@/hooks/useReducedMotion"
import { useStale } from "@/hooks/useStale"
import type { UnreadState } from "@/hooks/useUnread"
import { deriveBanner } from "@/lib/banner"
import { browserStorage, countNew, readLastSeen, titleWithCount, writeLastSeen } from "@/lib/unread"
import { cn } from "@/lib/utils"
import { BottomNav } from "./BottomNav"
import { Header } from "./Header"
import { Sidebar } from "./Sidebar"

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false)
  // drawer 닫힐 때 포커스를 되돌릴 트리거(메뉴 버튼). radix는 Dialog.Trigger를
  // 쓸 때만 자동 복원하므로, 외부 버튼으로 여는 이 구조에선 직접 복원이 필요하다.
  const menuButtonRef = useRef<HTMLButtonElement>(null)
  // 진입 연출 게이트 — 꺼져 있으면 클래스 자체를 붙이지 않는다(최종 상태 즉시 렌더).
  const reduced = useReducedMotion()
  // 셸 공용 구독 — 헤더 · 신규 알림 안내가 쓰던 훅을 여기서 한 번씩만 부른다(폴러 · 1초 타이머 개수 그대로).
  // 1초마다 셸이 다시 그려져도 페이지는 그대로다 — Outlet 은 같은 라우트 element 를 돌려준다(react-router useOutlet 의 useMemo).
  const { isOnline, health, error, lastUpdated } = useDevice()
  const disconnected = useStale(lastUpdated, error)
  const { notifications, lastUpdated: notificationsUpdated } = useNotifications()

  // 새 알림 표식 — 마지막 확인 시각(브라우저 저장, 실패하면 메모리). 탭 제목은 셸 폴러 목록으로 센다(새 폴링 · 타이머 0).
  const [lastSeenMs, setLastSeenMs] = useState(() => readLastSeen(browserStorage(), Date.now()))
  const markSeen = useCallback(() => {
    const t = Date.now()
    writeLastSeen(browserStorage(), t)
    setLastSeenMs(t)
  }, [])
  const unread = useMemo<UnreadState>(() => ({ lastSeenMs, markSeen }), [lastSeenMs, markSeen])
  const newCount = countNew(notifications, lastSeenMs)
  const [baseTitle] = useState(() => document.title)
  useEffect(() => {
    document.title = titleWithCount(newCount, baseTitle)
    // 셸을 벗어나면(랜딩) 원래 제목으로.
    return () => {
      document.title = baseTitle
    }
  }, [newCount, baseTitle])

  return (
    <div className="flex min-h-screen bg-background-sub">
      {/* 본문 바로가기: 키보드 사용자가 nav/헤더를 건너뛰고 본문으로 점프.
          평소 sr-only, 포커스 시 노출(WCAG 2.4.1 Bypass Blocks). */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[100] focus:flex focus:h-touch focus:items-center focus:rounded-xl focus:bg-primary focus:px-4 focus:text-body focus:font-medium focus:text-primary-foreground focus:shadow-xl focus:outline-none focus:ring-[3px] focus:ring-ring/50"
      >
        본문 바로가기
      </a>

      {/* 데스크톱 사이드바 */}
      <aside className="hidden lg:block">
        <div className="sticky top-0 h-screen">
          <Sidebar />
        </div>
      </aside>

      {/* 모바일 drawer — radix Dialog로 포커스 트랩/복원/Escape 위임(WAI-ARIA APG Dialog).
          모바일(lg 미만) 전용이라 데스크톱 레이아웃·포커스 흐름에는 영향 없음. */}
      <DialogPrimitive.Root open={mobileOpen} onOpenChange={setMobileOpen}>
        <DialogPrimitive.Portal>
          <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/40 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:animate-in data-[state=open]:fade-in-0 lg:hidden" />
          <DialogPrimitive.Content
            aria-describedby={undefined}
            onCloseAutoFocus={(e) => {
              // 닫힐 때 포커스를 연 트리거(메뉴 버튼)로 복원(WAI-ARIA APG).
              e.preventDefault()
              menuButtonRef.current?.focus()
            }}
            className="fixed inset-y-0 left-0 z-50 shadow-xl outline-none data-[state=closed]:animate-out data-[state=closed]:slide-out-to-left data-[state=open]:animate-in data-[state=open]:slide-in-from-left lg:hidden"
          >
            <DialogPrimitive.Title className="sr-only">메뉴</DialogPrimitive.Title>
            <Sidebar onNavigate={() => setMobileOpen(false)} />
          </DialogPrimitive.Content>
        </DialogPrimitive.Portal>
      </DialogPrimitive.Root>

      {/* 메인 영역 */}
      <div className="flex min-w-0 flex-1 flex-col">
        <Header
          onMenuClick={() => setMobileOpen(true)}
          menuButtonRef={menuButtonRef}
          isOnline={isOnline}
          hasHealth={health !== null}
          disconnected={disconnected}
        />
        <main
          id="main-content"
          tabIndex={-1}
          // 폰 폭 아래 여백 = 하단 탭 높이(메뉴 토큰 + 안전 영역) + 원래 여백 — 끝의 버튼 · 빈 상태가 탭에 가리지 않게.
          className="flex-1 px-4 pt-6 pb-[calc(var(--spacing-menu)_+_env(safe-area-inset-bottom,0px)_+_1.5rem)] outline-none lg:px-8 lg:pb-6"
        >
          <div className="mx-auto w-full max-w-5xl">
            <StatusBanner kind={deriveBanner(disconnected, isOnline, health !== null, notifications)} />
          </div>
          <div className={cn("mx-auto w-full max-w-5xl", !reduced && "page-enter")}>
            <Outlet context={unread} />
          </div>
        </main>
      </div>

      <BottomNav />

      <OnboardingModal />

      {/* 신규 알림 스크린리더 announce (어느 페이지든 동작하도록 상시 마운트) */}
      <NotificationAnnouncer notifications={notifications} lastUpdated={notificationsUpdated} />
    </div>
  )
}
