import { BellOff, TriangleAlert } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { KAKAO_FAILURE_REASONS, SKIP_REASON_LABEL } from "@/lib/notification-meta"
import type { SkipReason } from "@/types/notification"
import type { SkipReasonCounts } from "@/types/stats"

interface Row {
  key: string
  label: string
  count: number
  failure: boolean
}

// 카톡 실패 2키는 한 줄로 합친다 — 화면은 원인(내부 어휘)을 말하지 않는다(KAKAO_FAILURE_REASONS 주석 규칙).
// 손쓸 일이라 맨 위. 나머지 = 서버 집계 키 순서 그대로 · 라벨 = SKIP_REASON_LABEL(값 무변경). 0건 줄은 숨긴다.
function reasonRows(counts: SkipReasonCounts): Row[] {
  const keys = Object.keys(counts) as SkipReason[]
  const failed = keys.filter((k) => KAKAO_FAILURE_REASONS.has(k)).reduce((sum, k) => sum + counts[k], 0)
  return [
    { key: "kakao_failed", label: "카카오톡으로 보내지 못했어요", count: failed, failure: true },
    ...keys
      .filter((k) => !KAKAO_FAILURE_REASONS.has(k))
      .map((k) => ({ key: k, label: SKIP_REASON_LABEL[k] ?? "발송 제외", count: counts[k], failure: false })),
  ].filter((r) => r.count > 0)
}

// 통계 화면 「오늘 보내지 않은 이유」(감사 UX-D25) — /stats skip_reasons(당일 0시부터 집계). 합계는 화면 계산.
// 라벨 + 아이콘 + 색 3중 — 카톡 실패 줄만 경고 톤(알림 카드 실패 문장과 같은 표기).
export function SkipReasonsCard({ counts }: { counts: SkipReasonCounts }) {
  const rows = reasonRows(counts)
  const total = rows.reduce((sum, r) => sum + r.count, 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-h3">
          <BellOff className="h-5 w-5 text-primary" aria-hidden />
          오늘 보내지 않은 이유
        </CardTitle>
      </CardHeader>
      <CardContent>
        {rows.length === 0 ? (
          <p className="text-body text-foreground-secondary">오늘은 보내지 않은 알림이 없어요.</p>
        ) : (
          <>
            <ul className="space-y-1">
              {rows.map((r) => (
                <li key={r.key} className="flex items-center gap-2 rounded-xl px-2 py-2.5">
                  {r.failure ? (
                    <span className="flex items-center gap-1.5 text-body font-medium text-danger-deep">
                      <TriangleAlert className="h-4 w-4 shrink-0" aria-hidden />
                      {r.label}
                    </span>
                  ) : (
                    <span className="text-body">{r.label}</span>
                  )}
                  <span className="ml-auto text-body font-medium tabular-nums">{r.count}건</span>
                </li>
              ))}
            </ul>
            <p className="mt-2 border-t border-border px-2 pt-3 text-right text-body font-bold tabular-nums">
              모두 {total}건
            </p>
          </>
        )}
      </CardContent>
    </Card>
  )
}
