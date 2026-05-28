import { ShieldCheck } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { SystemHealth } from "@/types/stats"

function statusInfo(status: string): { color: string; label: string } {
  switch (status) {
    case "online":
      return { color: "bg-status-online", label: "온라인" }
    case "offline":
      return { color: "bg-status-offline", label: "오프라인" }
    case "processing":
      return { color: "bg-status-processing", label: "처리 중" }
    case "ok":
      return { color: "bg-status-online", label: "정상" }
    case "degraded":
      return { color: "bg-status-processing", label: "지연" }
    case "error":
      return { color: "bg-status-failed", label: "오류" }
    case "valid":
      return { color: "bg-status-online", label: "유효" }
    case "expiring":
      return { color: "bg-status-processing", label: "곧 만료" }
    case "expired":
      return { color: "bg-status-failed", label: "만료됨" }
    default:
      return { color: "bg-status-offline", label: status }
  }
}

export function SystemHealthCard({ health }: { health: SystemHealth }) {
  const rows = [
    { label: "디바이스", status: health.device_status, extra: undefined },
    {
      label: "카카오 토큰",
      status: health.kakao_token_status,
      extra: `${health.kakao_token_expires_in_minutes}분 후 만료`,
    },
    { label: "음성 인식(Clova)", status: health.clova_api_status, extra: undefined },
    { label: "데이터베이스", status: health.db_status, extra: undefined },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-h3">
          <ShieldCheck className="h-5 w-5 text-primary" aria-hidden />
          시스템 상태
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        {rows.map((row) => {
          const info = statusInfo(row.status)
          return (
            <div
              key={row.label}
              className="flex items-center gap-2 rounded-xl px-2 py-2.5"
            >
              <span className="text-body">{row.label}</span>
              {row.extra && (
                <span className="text-caption text-foreground-secondary">
                  {row.extra}
                </span>
              )}
              <span className="ml-auto flex items-center gap-2">
                <span
                  className={cn("h-2.5 w-2.5 rounded-full", info.color)}
                  aria-hidden
                />
                <span className="text-body font-medium tabular-nums">
                  {info.label}
                </span>
              </span>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
