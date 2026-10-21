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

// 0.87 → "87%". null = 값이 없음 → "정보 없음".
// ★ null 을 0 으로 접지 말 것: 실 STT(Naver CSR)는 응답이 `{"text": ...}` 뿐이라
//   신뢰도를 주지 않고(30.9 실측), 서버가 없는 값을 지어내지 않으려고 confidence=None
//   으로 남긴다(server/app/routes.py _stt_from_audio). 여기서 0 으로 접으면 인식에
//   성공한 자막이 화면에서 "신뢰도 0%"로 보인다 — 실측 없는 값을 표시하는 것과 같다.
//   ML confidence 경로(NotificationCard / TotalDetectionsCard)는 항상 number 라 무영향.
export function formatConfidence(value: number | null): string {
  if (value === null) return "정보 없음"
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

// 알림 감지 시각 표시 — 오늘이면 시각만, 어제면 「어제 오후 1:39」, 그 밖은 「10월 19일 오후 1:39」
// (해가 다르면 「2025년 12월 31일 …」). 목록은 여러 날에 걸치는데 시각만 보이면 지난 방문을 오늘로 읽는다.
// 날짜 판정 = formatClock 과 같은 브라우저 지역 시간대의 달력 날짜(자정 기준) 차이 — 경과 시간이 아니다
// (어제 23:59 는 9시간 전이어도 어제다). 판정은 Date 원값으로 하고 표시 문자열은 쓰지 않는다.
// now = 기준 시각 — 결정적 렌더(ssr-nc)용, 화면에서는 생략(= 지금).
export function formatDetectedAt(iso: string, now: Date = new Date()): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return "-"
  const dayStart = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime()
  const days = Math.round((dayStart(now) - dayStart(d)) / 86_400_000)
  const clock = formatClock(iso)
  if (days === 0) return clock
  if (days === 1) return `어제 ${clock}`
  const monthDay = `${d.getMonth() + 1}월 ${d.getDate()}일`
  const date =
    d.getFullYear() === now.getFullYear() ? monthDay : `${d.getFullYear()}년 ${monthDay}`
  return `${date} ${clock}`
}
