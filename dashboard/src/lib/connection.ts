// 서버 연결 상태 판정 — 순수 함수(시각은 밖에서 주입). 헤더 · 통계 · 알림 목록 공통.
import { RefreshCw, ServerOff, Wifi, WifiOff } from "lucide-react"
import type { LucideIcon } from "lucide-react"

// 등록 카드 staleError와 같은 문구의 단일 출처.
export const STALE_NOTICE = "최근 상태를 불러오지 못해 마지막으로 받은 상태를 보여 드려요."

// 「오류가 났는가」가 아니라 「마지막 성공이 얼마나 오래됐는가」로 본다 —
// fetch에 타임아웃이 없어 서버가 매달리면 오류가 생기지 않기 때문.
// 첫 성공 전에는 오류가 있을 때만 끊김(오류 없이 기다리는 중 = 연결 확인 중).
export function isStale(
  lastUpdated: Date | null,
  hasError: boolean,
  nowMs: number,
  staleAfterMs: number,
): boolean {
  if (lastUpdated === null) return hasError
  return nowMs - lastUpdated.getTime() >= staleAfterMs
}

// 헤더 연결 상태 4구분. 끊김이 먼저 — 서버가 안 보이면 기기 상태를 모른다.
// 색 + 아이콘 shape + 텍스트 3중 표현(WCAG 1.4.1 색 단독 의존 해소).
// Header.tsx에서 옮겨 왔다(컴포넌트 파일은 컴포넌트만 export — react-refresh 규칙).
export function deriveConnection(
  isOnline: boolean,
  hasHealth: boolean,
  disconnected: boolean,
): { label: string; Icon: LucideIcon; colorClass: string } {
  if (disconnected) {
    return { label: "서버 연결 끊김", Icon: ServerOff, colorClass: "text-status-failed" }
  }
  if (isOnline) {
    return { label: "디바이스 온라인", Icon: Wifi, colorClass: "text-status-online" }
  }
  if (hasHealth) {
    return { label: "디바이스 오프라인", Icon: WifiOff, colorClass: "text-status-failed" }
  }
  return { label: "연결 확인 중", Icon: RefreshCw, colorClass: "text-status-processing" }
}
