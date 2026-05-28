import { MessageSquareText } from "lucide-react"
import { formatConfidence } from "@/lib/format"
import type { NotificationStt } from "@/types/notification"

export function NotificationSTT({ stt }: { stt: NotificationStt }) {
  return (
    <div className="rounded-xl bg-background-sub p-3">
      <div className="mb-1 flex items-center gap-1.5 text-foreground-secondary">
        <MessageSquareText className="h-4 w-4" aria-hidden />
        <span className="text-caption font-medium">현관 음성</span>
        <span className="ml-auto text-caption tabular-nums">
          {formatConfidence(stt.confidence)}
        </span>
      </div>
      <p className="text-body">“{stt.transcript}”</p>
    </div>
  )
}
