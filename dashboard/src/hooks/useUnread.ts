// 새 알림 표식 상태 — AppShell 이 들고 Outlet context 로 페이지에 넘긴다(탭 제목과 같은 값).
import { useOutletContext } from "react-router-dom"

export interface UnreadState {
  // 마지막으로 알림 화면을 확인한 시각(ms). 이보다 뒤에 감지된 발송 시도 행이 「새 알림」이다.
  lastSeenMs: number
  // 지금을 마지막 확인 시각으로 저장한다(알림 화면에 들어올 때 · 나갈 때).
  markSeen: () => void
}

export function useUnread(): UnreadState {
  return useOutletContext<UnreadState>()
}
