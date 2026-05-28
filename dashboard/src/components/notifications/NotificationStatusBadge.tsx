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
  if (status.enrich_status === "failed") {
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
