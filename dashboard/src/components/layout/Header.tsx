import { Menu, Moon, Sun } from "lucide-react"
import { useSettings } from "@/contexts/SettingsContext"
import { useDevice } from "@/hooks/useDevice"
import { cn } from "@/lib/utils"

interface HeaderProps {
  onMenuClick: () => void
}

export function Header({ onMenuClick }: HeaderProps) {
  const { isOnline, health } = useDevice()
  const { theme, toggleTheme } = useSettings()

  const deviceLabel = isOnline
    ? "디바이스 온라인"
    : health
      ? "디바이스 오프라인"
      : "연결 확인 중"

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-2 border-b border-border bg-background/95 px-4 backdrop-blur lg:px-6">
      <button
        type="button"
        onClick={onMenuClick}
        className="flex h-touch w-touch items-center justify-center rounded-xl text-foreground-secondary hover:bg-background-sub lg:hidden"
        aria-label="메뉴 열기"
      >
        <Menu className="h-6 w-6" />
      </button>

      <span className="text-h3 font-bold lg:hidden">띵동</span>

      <div className="ml-auto flex items-center gap-2">
        <div className="flex h-touch items-center gap-2 rounded-xl bg-background-sub px-3">
          <span
            className={cn(
              "h-2.5 w-2.5 rounded-full",
              isOnline ? "bg-status-online" : "bg-status-offline",
            )}
            aria-hidden
          />
          <span className="hidden text-caption font-medium text-foreground-secondary sm:inline">
            {deviceLabel}
          </span>
        </div>

        <button
          type="button"
          onClick={toggleTheme}
          className="flex h-touch w-touch items-center justify-center rounded-xl text-foreground-secondary hover:bg-background-sub"
          aria-label={theme === "dark" ? "밝은 테마로 전환" : "어두운 테마로 전환"}
        >
          {theme === "dark" ? (
            <Sun className="h-5 w-5" />
          ) : (
            <Moon className="h-5 w-5" />
          )}
        </button>
      </div>
    </header>
  )
}
