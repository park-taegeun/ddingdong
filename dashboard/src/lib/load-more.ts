// 알림 화면 「이전 알림 더 보기」 — 순수 함수(상수는 밖에서 주입). useNotificationsPage · NotificationsPage가 쓴다.

export type LoadMoreState = "loading" | "end" | "max" | "button"

// 정의역 밖(0 이하 · 정수 아님)은 호출 오류라 기본값으로 넘기지 않고 던진다.
function assertPositiveInt(name: string, value: number): void {
  if (!Number.isInteger(value) || value < 1) {
    throw new RangeError(`${name}는 1 이상의 정수여야 한다: ${value}`)
  }
}

// 다음 요청 개수 = 지금 + 단위, 최대에서 멈춘다.
export function nextLimit(current: number, step: number, max: number): number {
  assertPositiveInt("current", current)
  assertPositiveInt("step", step)
  assertPositiveInt("max", max)
  if (max < step) throw new RangeError(`max(${max})가 step(${step})보다 작다`)
  return Math.min(current + step, max)
}

// 버튼 영역 상태. requested = 지금 요청 개수, receivedLimit = 마지막으로 받은 응답을 요청할 때 쓴 limit
// (받은 건수가 아니다 — 끝에선 건수가 limit보다 적다), hasMore = 그 응답의 has_more.
// ★ 판정 순서가 규칙의 일부다: ① 불러오는 중 → ② 끝 → ③ 최대치 → ④ 버튼.
//   ②③을 바꾸면 「limit 100 · 더 없음」이 끝이 아니라 최대치 문구로 나온다.
//   ③은 ②를 지났으니 has_more 참일 때만 닿는다.
export function loadMoreState(
  requested: number,
  receivedLimit: number,
  hasMore: boolean,
  max: number,
): LoadMoreState {
  assertPositiveInt("requested", requested)
  assertPositiveInt("receivedLimit", receivedLimit)
  assertPositiveInt("max", max)
  if (requested > receivedLimit) return "loading"
  if (!hasMore) return "end"
  if (receivedLimit >= max) return "max"
  return "button"
}
