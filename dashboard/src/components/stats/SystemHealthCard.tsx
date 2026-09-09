import { ShieldCheck } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { SystemHealth, TokenStatus } from "@/types/stats"

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

// 카카오 토큰 보조 문구. 서버가 만료 후 잔여 분을 음수(= 경과 분)로 내므로 상태별로
// 분기한다 — expired 에 "-4320분 후 만료"를 그대로 렌더하면 화면이 거짓말을 한다.
// 경과 분은 분/시간/일로 환산: 부스에서 "10분 전"과 "3일 전"은 대응이 갈린다
// (전자는 재발송, 후자는 refresh 체인 단절). 어느 상태에서도 문구를 비우지 않는다 —
// 비우면 행이 정상 상태와 구분되지 않는다.
function tokenExtra(status: TokenStatus, minutes: number): string {
  if (status !== "expired") return `${minutes}분 후 만료`
  if (minutes >= 0) return "만료 — 재발급 필요" // 방금 만료 / 토큰 행 부재(경과 시간 미상)
  const elapsed = -minutes
  if (elapsed < 60) return `${elapsed}분 전 만료`
  if (elapsed < 60 * 24) return `${Math.floor(elapsed / 60)}시간 전 만료`
  return `${Math.floor(elapsed / (60 * 24))}일 전 만료`
}

export function SystemHealthCard({ health }: { health: SystemHealth }) {
  const rows = [
    { label: "디바이스", status: health.device_status, extra: undefined },
    {
      label: "카카오 토큰",
      status: health.kakao_token_status,
      extra: tokenExtra(
        health.kakao_token_status,
        health.kakao_token_expires_in_minutes,
      ),
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
