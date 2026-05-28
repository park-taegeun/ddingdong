// 다크 모드 + 접근성 토글 (localStorage 영속). Phase 1 유일한 영속 상태 영역.

import { createContext, useContext, useEffect, useState } from "react"
import type { ReactNode } from "react"

export type Theme = "light" | "dark"

interface Settings {
  theme: Theme
  largeText: boolean
  reduceMotion: boolean
}

interface SettingsContextValue extends Settings {
  toggleTheme: () => void
  setTheme: (theme: Theme) => void
  setLargeText: (value: boolean) => void
  setReduceMotion: (value: boolean) => void
}

const SettingsContext = createContext<SettingsContextValue | null>(null)
const STORAGE_KEY = "ddingdong-settings"

function getInitialSettings(): Settings {
  const fallback: Settings = {
    theme: window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light",
    largeText: false,
    reduceMotion: false,
  }
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return fallback
    const parsed = JSON.parse(raw) as Partial<Settings>
    return {
      theme: parsed.theme === "dark" || parsed.theme === "light"
        ? parsed.theme
        : fallback.theme,
      largeText: parsed.largeText === true,
      reduceMotion: parsed.reduceMotion === true,
    }
  } catch {
    return fallback
  }
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(getInitialSettings)

  useEffect(() => {
    const root = document.documentElement
    root.classList.toggle("dark", settings.theme === "dark")
    root.classList.toggle("large-text", settings.largeText)
    root.classList.toggle("reduce-motion", settings.reduceMotion)
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
    } catch {
      // 저장 실패(프라이빗 모드 등)는 무시 — 토글은 세션 내 동작 유지
    }
  }, [settings])

  const value: SettingsContextValue = {
    ...settings,
    toggleTheme: () =>
      setSettings((s) => ({
        ...s,
        theme: s.theme === "dark" ? "light" : "dark",
      })),
    setTheme: (theme) => setSettings((s) => ({ ...s, theme })),
    setLargeText: (largeText) => setSettings((s) => ({ ...s, largeText })),
    setReduceMotion: (reduceMotion) =>
      setSettings((s) => ({ ...s, reduceMotion })),
  }

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSettings(): SettingsContextValue {
  const ctx = useContext(SettingsContext)
  if (!ctx) {
    throw new Error("useSettings는 SettingsProvider 내부에서만 사용할 수 있습니다.")
  }
  return ctx
}
