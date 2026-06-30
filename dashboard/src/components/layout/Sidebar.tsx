import { Bell } from "lucide-react"
import { NavLink } from "react-router-dom"
import { NAV_ITEMS } from "@/lib/nav"
import { cn } from "@/lib/utils"

interface SidebarProps {
  // 모바일 drawer에서 링크 클릭 시 닫기
  onNavigate?: () => void
}

export function Sidebar({ onNavigate }: SidebarProps) {
  return (
    <div className="flex h-full w-64 flex-col border-r border-border bg-background">
      <div className="flex h-16 items-center gap-2 px-6">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground">
          <Bell className="h-5 w-5" />
        </span>
        <span className="text-h2 font-bold">띵동</span>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-2" aria-label="주요 메뉴">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex h-menu items-center gap-3 rounded-xl px-4 text-body font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-foreground-secondary hover:bg-background-sub hover:text-foreground",
              )
            }
          >
            {({ isActive }) => (
              <>
                <item.icon className="h-5 w-5 shrink-0" aria-hidden />
                <span>{item.label}</span>
                {isActive && (
                  <span
                    className="ml-auto h-2 w-2 rounded-full bg-primary"
                    aria-hidden
                  />
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-border p-4">
        <p className="text-caption text-foreground-secondary">
          청각장애인 알림 시스템
        </p>
      </div>
    </div>
  )
}
