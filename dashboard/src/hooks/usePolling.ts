// REST 폴링 공통 훅 (useNotifications/useStats DRY 단일 출처).
// 단일 setInterval + cleanup으로 메모리 누수 방지, unmount 후 setState 차단.

import { useCallback, useEffect, useRef, useState } from "react"

export interface PollingState<T> {
  data: T | null
  isLoading: boolean
  error: Error | null
  lastUpdated: Date | null
}

export interface PollingResult<T> extends PollingState<T> {
  refetch: () => void
}

export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
): PollingResult<T> {
  const [state, setState] = useState<PollingState<T>>({
    data: null,
    isLoading: true,
    error: null,
    lastUpdated: null,
  })

  // 최신 fetcher 참조 유지 (인라인 fetcher로 인한 effect 재실행 방지)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher
  const mountedRef = useRef(true)

  const run = useCallback(async () => {
    try {
      const data = await fetcherRef.current()
      if (!mountedRef.current) return
      setState({ data, isLoading: false, error: null, lastUpdated: new Date() })
    } catch (err) {
      if (!mountedRef.current) return
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: err instanceof Error ? err : new Error(String(err)),
      }))
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    void run()
    const id = setInterval(() => void run(), intervalMs)
    return () => {
      mountedRef.current = false
      clearInterval(id)
    }
  }, [run, intervalMs])

  return { ...state, refetch: run }
}
