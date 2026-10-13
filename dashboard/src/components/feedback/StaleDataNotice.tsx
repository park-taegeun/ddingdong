import { STALE_NOTICE } from "@/lib/connection"
import { formatRelativeTime } from "@/lib/format"

interface StaleDataNoticeProps {
  lastUpdated: Date | null
  // 결정적 렌더(ssr-nc)용 — 화면에서는 생략(= 지금).
  now?: Date
}

// 서버 연결 끊김 때 통계 · 알림 목록 위에 붙는 안내. 데이터는 지우지 않는다.
export function StaleDataNotice({ lastUpdated, now }: StaleDataNoticeProps) {
  return (
    <div>
      <p className="text-caption text-foreground-secondary">{STALE_NOTICE}</p>
      {lastUpdated && (
        <p className="text-caption text-foreground-secondary tabular-nums">
          마지막 확인 {formatRelativeTime(lastUpdated.toISOString(), now)}
        </p>
      )}
    </div>
  )
}
