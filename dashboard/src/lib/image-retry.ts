// 알림 사진 재시도 — 순수 함수(상수는 밖에서 주입). NotificationImage가 쓴다.

// failures = 지금까지 실패한 요청 수(첫 요청 포함). 다음 재시도까지의 지연 ms, 상한을 다 썼으면 null.
// 재시도는 실패 1 ~ max번째 뒤에만 한다 → 요청 최대 1 + max회.
// 실패 0 이하 · 정수 아님 = 호출 오류라 기본값으로 넘기지 않고 던진다.
export function nextRetryDelay(failures: number, max: number, intervalMs: number): number | null {
  if (!Number.isInteger(failures) || failures < 1) {
    throw new RangeError(`failures는 1 이상의 정수여야 한다: ${failures}`)
  }
  const exhausted = failures > max
  if (exhausted) return null
  return intervalMs
}

// 재시도 요청 URL — 시도 번호 쿼리 1개를 덧붙인다(실패 응답 캐시 재사용 배제 · Network 탭에서 구분).
// 기존 쿼리 · 해시는 보존. 상대 · 절대 경로 모두 문자열로만 다룬다.
// attempt = 재시도 번호(1부터). 첫 요청은 이 함수를 거치지 않고 원본 그대로 쓴다.
export function retryUrl(src: string, attempt: number): string {
  if (!Number.isInteger(attempt) || attempt < 1) {
    throw new RangeError(`attempt는 1 이상의 정수여야 한다: ${attempt}`)
  }
  const hashAt = src.indexOf("#")
  const base = hashAt === -1 ? src : src.slice(0, hashAt)
  const hash = hashAt === -1 ? "" : src.slice(hashAt)
  return `${base}${base.includes("?") ? "&" : "?"}_retry=${attempt}${hash}`
}
