import type { Ref } from "react"
import { Menu, Moon, Sun } from "lucide-react"
import { useSettings } from "@/contexts/SettingsContext"
import { useDevice } from "@/hooks/useDevice"
import { useStale } from "@/hooks/useStale"
import { deriveConnection } from "@/lib/connection"
import { cn } from "@/lib/utils"

interface HeaderProps {
  onMenuClick: () => void
  // 모바일 drawer 닫힐 때 포커스를 되돌릴 트리거(B-1b 포커스 복원)
  menuButtonRef?: Ref<HTMLButtonElement>
}

export function Header({ onMenuClick, menuButtonRef }: HeaderProps) {
  const { isOnline, health, error, lastUpdated } = useDevice()
  const disconnected = useStale(lastUpdated, error)
  const { theme, toggleTheme } = useSettings()

  const { label: deviceLabel, Icon: ConnIcon, colorClass } = deriveConnection(
    isOnline,
    health !== null,
    disconnected,
  )

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-2 border-b border-border bg-background/95 px-4 backdrop-blur lg:px-6">
      <button
        ref={menuButtonRef}
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
          {/* 아이콘 shape가 상태별로 달라(Wifi/WifiOff/Refresh/ServerOff) 색 외에 형태로도 구분 — WCAG 1.4.1. */}
          <ConnIcon className={cn("h-4 w-4 shrink-0", colorClass)} aria-hidden />
          {/* sm 미만에서도 SR이 상태를 읽도록 sr-only로 a11y 트리 상주(시각 표현은 아이콘).
              색상 단독 의존 해소 — 텍스트 라벨 + 아이콘 shape 병행. */}
          <span className="sr-only text-caption font-medium text-foreground-secondary sm:not-sr-only">
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
