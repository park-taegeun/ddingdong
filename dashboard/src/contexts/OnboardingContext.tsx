// 단계별 온보딩 표시 상태 (첫 방문 자동 표시 + 설정/도움말에서 재실행).

import { createContext, useContext, useState } from "react"
import type { ReactNode } from "react"

interface OnboardingContextValue {
  open: boolean
  openOnboarding: () => void
  closeOnboarding: () => void
}

const OnboardingContext = createContext<OnboardingContextValue | null>(null)
const STORAGE_KEY = "ddingdong-onboarded"

function hasOnboarded(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "1"
  } catch {
    return false
  }
}

export function OnboardingProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(() => !hasOnboarded())

  const value: OnboardingContextValue = {
    open,
    openOnboarding: () => setOpen(true),
    closeOnboarding: () => {
      setOpen(false)
      try {
        localStorage.setItem(STORAGE_KEY, "1")
      } catch {
        // 저장 실패는 무시 (다음 방문 시 다시 표시될 수 있음)
      }
    },
  }

  return (
    <OnboardingContext.Provider value={value}>
      {children}
    </OnboardingContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useOnboarding(): OnboardingContextValue {
  const ctx = useContext(OnboardingContext)
  if (!ctx) {
    throw new Error("useOnboarding은 OnboardingProvider 내부에서만 사용할 수 있습니다.")
  }
  return ctx
}
