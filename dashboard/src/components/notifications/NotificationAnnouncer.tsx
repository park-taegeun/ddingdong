// 신규 알림 스크린리더 announce (Phase B-1, 접근성).
// 1차 사용자 = 청각장애인/SR 의존 → 새 알림(특히 화재경보) 도착을 시각 외 채널로 전달.
// 설계(decisions.md 카테고리 7 화재경보 정책 정합):
//   - fire_alarm → role="alert"(aria-live=assertive): 긴급, 진행 중 발화 가로채 즉시 announce
//   - doorbell/knock → role="status"(aria-live=polite): 대기 후 announce
// 폴링 훅(usePolling/useNotifications) 무수정 — 소비 측 additive. 자체 폴링 구독 1개를
// AppShell에 상시 마운트해, 어느 페이지에 있든(설정/통계 화면 포함) 신규 알림을 announce.
// "신규만" 보장: seenRef로 announce 완료 ID 추적 + 첫 성공 로드 시 기존 ID 전량 seed(초기 무announce).

import { useEffect, useRef, useState } from "react"
import { useNotifications } from "@/hooks/useNotifications"
import { CLASS_META } from "@/lib/notification-meta"
import type { NotificationItem, PredictedClass } from "@/types/notification"

// 신규 알림들을 클래스별 건수로 집계해 한국어 announce 문구 생성 (라벨 DRY: CLASS_META 재사용).
// 예: 초인종 1 → "초인종 감지" / 초인종 2 + 노크 1 → "초인종 2건, 노크 감지"
function buildMessage(items: NotificationItem[]): string {
  const counts = new Map<PredictedClass, number>()
  for (const item of items) {
    counts.set(item.predicted_class, (counts.get(item.predicted_class) ?? 0) + 1)
  }
  const parts = Array.from(counts, ([cls, count]) =>
    count > 1 ? `${CLASS_META[cls].label} ${count}건` : CLASS_META[cls].label,
  )
  return `${parts.join(", ")} 감지`
}

// live region 메시지 — id는 React key로만 사용(텍스트 동일해도 노드 교체 → SR 재announce 보장).
interface Announcement {
  id: number
  text: string
}

const EMPTY: Announcement = { id: 0, text: "" }

export function NotificationAnnouncer() {
  const { notifications, lastUpdated } = useNotifications()

  const seenRef = useRef<Set<string>>(new Set())
  const initializedRef = useRef(false)
  const announceIdRef = useRef(0)

  const [assertive, setAssertive] = useState<Announcement>(EMPTY)
  const [polite, setPolite] = useState<Announcement>(EMPTY)

  useEffect(() => {
    // 첫 성공 fetch 전(lastUpdated=null)에는 아무것도 하지 않음.
    if (!lastUpdated) return

    const seen = seenRef.current

    // 첫 로드: 기존 알림 전량을 seen 처리 → 초기 마운트 시 전체 재announce 방지.
    if (!initializedRef.current) {
      for (const item of notifications) seen.add(item.request_id)
      initializedRef.current = true
      return
    }

    // 이후 폴링: seen에 없는 신규 도착분만 추출(폴링마다 동일 목록 재announce 방지).
    const fresh = notifications.filter((item) => !seen.has(item.request_id))
    if (fresh.length === 0) return
    for (const item of fresh) seen.add(item.request_id)

    const fires = fresh.filter((item) => item.predicted_class === "fire_alarm")
    const others = fresh.filter((item) => item.predicted_class !== "fire_alarm")

    if (fires.length > 0) {
      announceIdRef.current += 1
      setAssertive({ id: announceIdRef.current, text: buildMessage(fires) })
    }
    if (others.length > 0) {
      announceIdRef.current += 1
      setPolite({ id: announceIdRef.current, text: buildMessage(others) })
    }
  }, [notifications, lastUpdated])

  return (
    <>
      {/* 화재경보 — 긴급(assertive). 시각적으로 숨기되 DOM 상주(sr-only). */}
      <div className="sr-only" role="alert" aria-live="assertive" aria-atomic="true">
        {assertive.text && <span key={assertive.id}>{assertive.text}</span>}
      </div>
      {/* 초인종/노크 — 대기(polite). */}
      <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {polite.text && <span key={polite.id}>{polite.text}</span>}
      </div>
    </>
  )
}
