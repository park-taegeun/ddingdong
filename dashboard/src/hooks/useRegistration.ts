// 초인종 등록 상태 폴링(3초) + 시작 · 해제 액션.
// 폴링은 이 훅을 쓰는 카드가 마운트된 동안만 돈다.

import { useCallback, useState } from "react"
import { clearRegistration, fetchRegistration, startRegistration } from "@/lib/api"
import {
  POLLING_INTERVAL_MS,
  REGISTRATION_EXPIRES_IN_SECONDS,
  REGISTRATION_TARGET_COUNT,
} from "@/lib/constants"
import type { RegistrationStatus } from "@/types/registration"
import { usePolling } from "./usePolling"

export function useRegistration() {
  const { data, isLoading, error, refetch } = usePolling<RegistrationStatus>(
    fetchRegistration,
    POLLING_INTERVAL_MS,
  )
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [actionError, setActionError] = useState<Error | null>(null)

  const run = useCallback(
    async (action: () => Promise<unknown>) => {
      setIsSubmitting(true)
      setActionError(null)
      try {
        await action()
        refetch()
      } catch (err) {
        setActionError(err instanceof Error ? err : new Error(String(err)))
      } finally {
        setIsSubmitting(false)
      }
    },
    [refetch],
  )

  const start = useCallback(
    () =>
      run(() =>
        startRegistration(REGISTRATION_TARGET_COUNT, REGISTRATION_EXPIRES_IN_SECONDS),
      ),
    [run],
  )
  const clear = useCallback(() => run(clearRegistration), [run])

  return {
    status: data,
    isLoading,
    loadError: error,
    isSubmitting,
    actionError,
    start,
    clear,
  }
}
