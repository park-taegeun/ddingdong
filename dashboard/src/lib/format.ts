// 표시용 포맷터 (한국어, 50-60대 가독성). 카드/알림 공통 DRY.

export function formatClock(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return "-"
  return new Intl.DateTimeFormat("ko-KR", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(d)
}

export function formatRelativeTime(iso: string, now: Date = new Date()): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return "-"
  const sec = Math.round((now.getTime() - d.getTime()) / 1000)
  if (sec < 10) return "방금 전"
  if (sec < 60) return `${sec}초 전`
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}분 전`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}시간 전`
  return `${Math.floor(hr / 24)}일 전`
}

// 0.87 → "87%"
export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`
}

// 57.1 → "57.1%"
export function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`
}

// 2847 → "2.8초", 521 → "521ms"
export function formatMs(ms: number): string {
  if (ms < 1000) return `${ms.toLocaleString("ko-KR")}ms`
  return `${(ms / 1000).toFixed(1)}초`
}

// 0.92 → "92%"
export function formatRate(rate: number): string {
  return `${Math.round(rate * 100)}%`
}
