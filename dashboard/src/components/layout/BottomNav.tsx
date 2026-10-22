import { NavLink } from "react-router-dom"
import { NAV_ITEMS } from "@/lib/nav"
import { cn } from "@/lib/utils"

// 폰 폭(lg 미만) 하단 탭 — 메뉴 5개를 아이콘 + 글자로 상시 노출(감사 UX-D15). 햄버거 · drawer 는 그대로 둔다.
// 높이 = 메뉴 토큰(56px) + 기기 하단 안전 영역. index.html 에 viewport-fit=cover 가 없어 안전 영역은 대개 0이다
// (사용자 결정 2026-10-22 — cover 는 헤더 · 좌우까지 다시 처리해야 하는 전역 변경). 본문 아래 여백 = AppShell.
// 현재 위치 = 색 + 굵기 + aria-current(NavLink 가 붙인다). drawer 가 열리면 그 덮개가 이 탭 위에 깔린다(헤더와 같은 층).
export function BottomNav() {
  return (
    <nav
      aria-label="주요 메뉴"
      className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-background pb-[env(safe-area-inset-bottom,0px)] lg:hidden"
    >
      <ul className="grid grid-cols-5">
        {NAV_ITEMS.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex h-menu flex-col items-center justify-center gap-0.5 text-caption",
                  isActive ? "font-bold text-primary" : "font-medium text-foreground-secondary",
                )
              }
            >
              <item.icon className="h-5 w-5 shrink-0" aria-hidden />
              <span>{item.label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
