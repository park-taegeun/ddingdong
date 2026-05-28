// 네비게이션 메뉴 5종 단일 출처 (Sidebar / 라우팅 정합)

import { BarChart3, Bell, CircleHelp, House, Settings } from "lucide-react"
import type { LucideIcon } from "lucide-react"

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "홈", icon: House },
  { to: "/notifications", label: "알림", icon: Bell },
  { to: "/stats", label: "통계", icon: BarChart3 },
  { to: "/settings", label: "설정", icon: Settings },
  { to: "/help", label: "도움말", icon: CircleHelp },
]
