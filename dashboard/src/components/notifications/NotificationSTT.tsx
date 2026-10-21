import { MessageSquareText } from "lucide-react"
import { formatConfidence } from "@/lib/format"
import type { NotificationStt } from "@/types/notification"

export function NotificationSTT({ stt }: { stt: NotificationStt }) {
  return (
    <div className="rounded-xl bg-background-sub p-3">
      <div className="mb-1 flex items-center gap-1.5 text-foreground-secondary">
        <MessageSquareText className="h-4 w-4" aria-hidden />
        <span className="text-caption font-medium">현관 음성</span>
        {/* 신뢰도가 없으면(null — 실 STT는 신뢰도를 주지 않는다) 칸을 숨긴다. 0.0은 값이라 「0%」로 보인다
            — 엄격 비교(!== null)여야 한다. 문구 판정은 formatConfidence 그대로. */}
        {stt.confidence !== null && (
          <span className="ml-auto text-caption tabular-nums">
            {formatConfidence(stt.confidence)}
          </span>
        )}
      </div>
      <p className="text-body">“{stt.transcript}”</p>
    </div>
  )
}
