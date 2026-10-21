import { Bell, CircleCheck, CircleSlash, Clock, TriangleAlert } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { KAKAO_FAILURE_REASONS } from "@/lib/notification-meta"
import { cn } from "@/lib/utils"
import type { NotificationStatus } from "@/types/notification"

type Tone = "success" | "processing" | "primary" | "danger" | "muted"

// 글자는 진한 본문색(대비 4.5:1 이상), 상태 색은 옅은 배경과 아이콘이 맡는다 — 라벨 · 아이콘 · 색 3중.
// 아이콘 색은 글자용 대비 보정 토큰이 있는 톤만 보정분을 쓴다(성공 톤은 보정 토큰이 없어 원래 색).
const TONE_CLASS: Record<Tone, string> = {
  success: "bg-success/10 text-foreground [&>svg]:text-success",
  processing: "bg-warning/10 text-foreground [&>svg]:text-lp-amber",
  primary: "bg-primary/10 text-foreground [&>svg]:text-lp-blue",
  danger: "bg-danger/10 text-foreground [&>svg]:text-danger-deep",
  muted: "bg-background-sub text-foreground-secondary",
}

function derive(status: NotificationStatus): {
  label: string
  tone: Tone
  Icon: LucideIcon
} {
  if (!status.primary_sent) {
    // 카카오 발송 실패는 의도된 차단과 갈라 경고 톤으로 보인다. 아래 읽는 순서(secondary_sent →
    // enrich_status)와 무관한 1차 미발송 블록 안의 분기다.
    if (status.skip_reason && KAKAO_FAILURE_REASONS.has(status.skip_reason)) {
      return { label: "보내기 실패", tone: "danger", Icon: TriangleAlert }
    }
    return { label: "발송 제외", tone: "muted", Icon: CircleSlash }
  }
  if (status.secondary_sent) {
    return { label: "전송 완료", tone: "success", Icon: CircleCheck }
  }
  if (status.enrich_status === "processing" || status.enrich_status === "pending") {
    return { label: "2차 처리 중", tone: "processing", Icon: Clock }
  }
  // ★ 읽는 순서(secondary_sent → enrich_status)는 그대로 두고 분기만 넓힌다.
  //   순서를 바꾸면 "부분 성공이 전송 완료로 렌더"되는 금지 상태가 되살아난다(7.6(d)).
  //   enrich 가 끝났는데(completed) 사진 전달 시각이 없으면 = 사진 발송 실패다
  //   (server/app/routes.py: `secondary_sent_at = utc_now() if photo_sent else None`).
  //   이 조합이 없으면 (사진 실패 + 자막 성공) / (사진 실패 + 자막 없음) 두 건이
  //   "1차 발송"으로 과소 표기된다(8.3 미결).
  //   ⚠️ enrich_status="skipped"(화재경보)는 여기 걸리면 안 된다 — 2차를 시도한 적이
  //     없으므로 실패가 아니다. 그래서 "completed" 를 명시 비교한다.
  if (
    status.enrich_status === "failed" ||
    (status.enrich_status === "completed" && status.secondary_sent_at === null)
  ) {
    return { label: "2차 실패", tone: "danger", Icon: TriangleAlert }
  }
  // enrich skipped(화재경보 등) 또는 1차만 발송
  return { label: "1차 발송", tone: "primary", Icon: Bell }
}

export function NotificationStatusBadge({
  status,
}: {
  status: NotificationStatus
}) {
  const { label, tone, Icon } = derive(status)
  return (
    <Badge
      variant="outline"
      className={cn("gap-1 border-transparent text-caption [&>svg]:size-4", TONE_CLASS[tone])}
    >
      <Icon aria-hidden />
      {label}
    </Badge>
  )
}
