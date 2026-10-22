// 전역 경고 띠 판정 — 순수 함수. 동시에 하나만, 높은 것 하나: ① 서버 끊김 ② 현관 기기 꺼짐 ③ 카톡 발송 실패.
// 새 임계 없음 — 끊김 · 기기 상태는 헤더와 같은 입력, 카톡은 알림 목록의 사실만 본다.
import { KAKAO_FAILURE_REASONS } from "@/lib/notification-meta"
import type { NotificationItem } from "@/types/notification"

export type BannerKind = "server" | "device" | "kakao"

// 「발송 시도」 행 = 1차 카톡을 보냈거나 보내려다 실패한 행. 의도된 차단(기타 소리 · 신뢰도 · ToF · 등록)은
// 시도가 아니다. 띠의 카톡 실패 판정과 새 알림 표식(lib/unread.ts)이 같은 정의를 쓴다.
export function isSendAttempt(n: NotificationItem): boolean {
  const s = n.notification_status
  if (s.primary_sent) return true
  if (s.skip_reason && KAKAO_FAILURE_REASONS.has(s.skip_reason)) return true
  return false
}

// 최신순 목록에서 첫 「발송 시도」 행이 카톡 실패인가. 의도된 차단 행은 건너뛴다.
// 시도 행이 없으면 모르는 것이라 거짓 — 띄우지 않는다.
// 카카오 토큰 상태 필드는 보지 않는다: access 기준이라 발송이 없으면 평소에도 만료로 나오고
// 다음 발송 때 자동 갱신된다(decisions.md 7.5 · 8.5(d)) — 쓰면 거짓 경보가 난다.
export function lastSendFailed(notifications: NotificationItem[]): boolean {
  for (const n of notifications) {
    if (isSendAttempt(n)) return !n.notification_status.primary_sent
  }
  return false
}

// 기기 꺼짐 조건 = deriveConnection 의 「디바이스 오프라인」과 같다(상태를 받았는데 online 이 아님).
// 끊김이 먼저 — 서버가 안 보이면 기기 상태도 카톡 결과도 옛 값이다.
export function deriveBanner(
  disconnected: boolean,
  isOnline: boolean,
  hasHealth: boolean,
  notifications: NotificationItem[],
): BannerKind | null {
  if (disconnected) return "server"
  if (hasHealth && !isOnline) return "device"
  if (lastSendFailed(notifications)) return "kakao"
  return null
}
