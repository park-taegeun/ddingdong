// 모션 게이트 단일 출처 — OS 설정(prefers-reduced-motion)과 앱 「움직임 줄이기」 토글의 OR.
// 둘 중 하나라도 켜져 있으면 진입 연출 클래스를 **아예 붙이지 않는다**(빈 화면 없이 최종 상태 즉시 렌더).
// index.css 의 전역 감속 규칙(html.reduce-motion / @media prefers-reduced-motion)은 2중 방어로 남는다.

import { useSyncExternalStore } from "react"
import { useSettings } from "@/contexts/SettingsContext"

const QUERY = "(prefers-reduced-motion: reduce)"

// matchMedia = React 밖의 외부 스토어 → useSyncExternalStore 가 정석(수동 useEffect+setState 아님).
function subscribe(onChange: () => void) {
  const mq = window.matchMedia(QUERY)
  mq.addEventListener("change", onChange)
  return () => mq.removeEventListener("change", onChange)
}

const getSnapshot = () => window.matchMedia(QUERY).matches
const getServerSnapshot = () => false // SSR(ssr-nc 하네스)엔 matchMedia 가 없다

export function useReducedMotion(): boolean {
  const { reduceMotion } = useSettings()
  const systemReduce = useSyncExternalStore(
    subscribe,
    getSnapshot,
    getServerSnapshot,
  )
  return reduceMotion || systemReduce
}
