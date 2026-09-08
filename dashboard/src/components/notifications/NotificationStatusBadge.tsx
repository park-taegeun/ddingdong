import { Bell, CircleCheck, CircleSlash, Clock, TriangleAlert } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { NotificationStatus } from "@/types/notification"

type Tone = "success" | "processing" | "primary" | "danger" | "muted"

const TONE_CLASS: Record<Tone, string> = {
  success: "bg-success/10 text-success",
  processing: "bg-warning/10 text-warning",
  primary: "bg-primary/10 text-primary",
  danger: "bg-danger/10 text-danger",
  muted: "bg-background-sub text-foreground-secondary",
}

function derive(status: NotificationStatus): {
  label: string
  tone: Tone
  Icon: LucideIcon
} {
  if (!status.primary_sent) {
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
    <Badge variant="outline" className={cn("gap-1 border-transparent", TONE_CLASS[tone])}>
      <Icon aria-hidden />
      {label}
    </Badge>
  )
}
