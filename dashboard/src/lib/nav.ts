// 네비게이션 메뉴 5종 단일 출처 (Sidebar / 라우팅 정합)

import { BarChart3, CircleHelp, House, Inbox, Settings } from "lucide-react"
import type { LucideIcon } from "lucide-react"

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

export const NAV_ITEMS: NavItem[] = [
  { to: "/home", label: "홈", icon: House },
  // 알림 메뉴 = 받은 기록함(Inbox). 종(Bell)은 초인종 클래스 · 브랜드 로고가 쓰므로 겹치지 않게 한다.
  { to: "/notifications", label: "알림", icon: Inbox },
  { to: "/stats", label: "통계", icon: BarChart3 },
  { to: "/settings", label: "설정", icon: Settings },
  { to: "/help", label: "도움말", icon: CircleHelp },
]
