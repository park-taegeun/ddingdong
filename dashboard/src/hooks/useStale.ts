// 끊김 판정 훅 — 1초마다 다시 그려 「시간이 지나서」 끊김이 되는 경우(무응답)도 잡는다.
// usePolling은 성공 · 실패 때만 다시 그리므로 소비 측에서 따로 센다(폴링 훅 무수정 — additive).

import { useEffect, useState } from "react"
import { isStale } from "@/lib/connection"
import { STALE_AFTER_MS } from "@/lib/constants"

export function useStale(lastUpdated: Date | null, error: Error | null): boolean {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])

  return isStale(lastUpdated, error !== null, now, STALE_AFTER_MS)
}
