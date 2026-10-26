// 새 알림 표식 — 순수 함수(저장소 · 시각은 밖에서 주입). 「새 알림」 = 마지막 확인 시각보다 뒤에 감지된
// 「발송 시도」 행(lib/banner.ts isSendAttempt — 띠와 같은 정의). 기타 소리 · 의도된 차단 행은 세지 않는다.
// 한계 ① 마지막 확인 = 브라우저 시각, 감지 시각 = 서버 시각이다. 두 시계가 어긋난 폭 안에 들어온 행은
//   표식이 빠지거나(브라우저가 빠를 때) 첫 방문에 붙을 수 있다(늦을 때).
//   재판정 트리거: 어긋남이 관측되면 기준을 서버 시각(/stats server_time)으로 바꾼다.
// 한계 ② 세는 범위 = 넘겨받은 목록 안. 탭 제목은 셸 폴러가 불러온 최근 20건 안에서만 센다.
import { isSendAttempt } from "@/lib/banner"
import type { NotificationItem } from "@/types/notification"

const LAST_SEEN_KEY = "ddingdong-notifications-seen-at"

export type SeenStorage = Pick<Storage, "getItem" | "setItem">

export function isNewNotification(n: NotificationItem, lastSeenMs: number): boolean {
  return isSendAttempt(n) && new Date(n.detected_at).getTime() > lastSeenMs
}

export function countNew(notifications: NotificationItem[], lastSeenMs: number): number {
  return notifications.filter((n) => isNewNotification(n, lastSeenMs)).length
}

// 브라우저 저장소 — SSR 이거나 접근 자체가 막히면(차단된 사이트 데이터) 없음.
export function browserStorage(): SeenStorage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage
  } catch {
    return null
  }
}

export function writeLastSeen(storage: SeenStorage | null, ms: number): void {
  try {
    storage?.setItem(LAST_SEEN_KEY, String(ms))
  } catch {
    // 쓰기 실패 = 이번 화면 동안만 메모리 값으로 동작한다
  }
}

// 저장값이 없거나 못 읽으면 지금으로 초기화 — 첫 방문에 불러온 과거 알림이 전부 「새」가 되지 않게.
export function readLastSeen(storage: SeenStorage | null, nowMs: number): number {
  try {
    const raw = storage?.getItem(LAST_SEEN_KEY)
    const v = raw ? Number(raw) : NaN
    if (Number.isFinite(v)) return v
  } catch {
    // 읽기 실패 = 저장값 없음과 같다
  }
  writeLastSeen(storage, nowMs)
  return nowMs
}

// 브라우저 탭 제목 — 새 알림이 있으면 「(N) 띵동」, 없으면 원래 제목.
export function titleWithCount(count: number, baseTitle: string): string {
  return count > 0 ? `(${count}) 띵동` : baseTitle
}
