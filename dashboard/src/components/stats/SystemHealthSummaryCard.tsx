// 홈 빈 상태(알림 0건, 정상)용 "시스템 건강" 안심 카드.
// 에러(fetch 실패)가 아닌 "정상이나 데이터 0" 일 때 노출 → 불안 대신 안심 UX (페르소나 직결).
// 시안 = decisions.md 카테고리 8 / 2026-06-30 PoC-(20): 헤더 + 3지표(기기 상태 / 마지막 감지 / 신호).
// device_status 분기: online=정상 / offline=경고 / processing=중립. 색 단독 의존 금지(아이콘+텍스트 병행, WCAG 1.4.1).
import { Clock, Cpu, ShieldCheck, TriangleAlert, Wifi } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { formatRelativeTime } from "@/lib/format"
import { cn } from "@/lib/utils"
import type { DeviceStatus, SignalStrength, SystemHealth } from "@/types/stats"

interface HeaderState {
  icon: LucideIcon
  title: string
  description: string
  iconClass: string
  iconBgClass: string
}

// device_status → 헤더 톤(정상/경고/중립). 색 + 아이콘 + 문구 동시 전달.
const HEADER_STATE: Record<DeviceStatus, HeaderState> = {
  online: {
    icon: ShieldCheck,
    title: "시스템이 정상 작동 중이에요",
    description: "현관에서 소리가 감지되면 바로 알려드릴게요.",
    iconClass: "text-success",
    iconBgClass: "bg-success/10",
  },
  offline: {
    icon: TriangleAlert,
    title: "기기 연결을 확인해 주세요",
    description: "현관 기기가 응답하지 않아요. 전원과 네트워크를 확인해 주세요.",
    iconClass: "text-warning",
    iconBgClass: "bg-warning/10",
  },
  processing: {
    icon: Cpu,
    title: "상태를 확인하고 있어요",
    description: "잠시만 기다려 주세요.",
    iconClass: "text-foreground-secondary",
    iconBgClass: "bg-background-sub",
  },
}

const DEVICE_LABEL: Record<DeviceStatus, string> = {
  online: "켜짐",
  offline: "꺼짐",
  processing: "확인 중",
}

const DEVICE_DOT: Record<DeviceStatus, string> = {
  online: "bg-status-online",
  offline: "bg-status-offline",
  processing: "bg-status-processing",
}

const SIGNAL_LABEL: Record<SignalStrength, string> = {
  strong: "강함",
  weak: "약함",
  none: "없음",
}

const SIGNAL_DOT: Record<SignalStrength, string> = {
  strong: "bg-status-online",
  weak: "bg-status-processing",
  none: "bg-status-offline",
}

interface Indicator {
  icon: LucideIcon
  label: string
  value: string
  dotClass?: string
}

export function SystemHealthSummaryCard({ health }: { health: SystemHealth }) {
  const header = HEADER_STATE[health.device_status]
  const HeaderIcon = header.icon

  const indicators: Indicator[] = [
    {
      icon: Cpu,
      label: "기기 상태",
      value: DEVICE_LABEL[health.device_status],
      dotClass: DEVICE_DOT[health.device_status],
    },
    {
      icon: Clock,
      label: "마지막 감지",
      value: formatRelativeTime(health.device_last_seen_at),
    },
    {
      icon: Wifi,
      label: "신호",
      value: SIGNAL_LABEL[health.signal_strength],
      dotClass: SIGNAL_DOT[health.signal_strength],
    },
  ]

  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-5 px-6 py-8 text-center">
        <span
          className={cn(
            "flex h-14 w-14 items-center justify-center rounded-full",
            header.iconBgClass,
          )}
        >
          <HeaderIcon className={cn("h-7 w-7", header.iconClass)} aria-hidden />
        </span>
        <div className="space-y-1">
          <p className="text-h3 font-semibold">{header.title}</p>
          <p className="max-w-sm text-body text-foreground-secondary">
            {header.description}
          </p>
        </div>

        <dl className="grid w-full max-w-md grid-cols-3 gap-3">
          {indicators.map((item) => {
            const ItemIcon = item.icon
            return (
              <div
                key={item.label}
                className="flex flex-col items-center gap-1 rounded-xl bg-background-sub px-2 py-3"
              >
                <ItemIcon
                  className="h-5 w-5 text-foreground-secondary"
                  aria-hidden
                />
                <dt className="text-caption text-foreground-secondary">
                  {item.label}
                </dt>
                <dd className="flex items-center gap-1.5 text-body font-medium">
                  {item.dotClass && (
                    <span
                      className={cn("h-2.5 w-2.5 rounded-full", item.dotClass)}
                      aria-hidden
                    />
                  )}
                  {item.value}
                </dd>
              </div>
            )
          })}
        </dl>
      </CardContent>
    </Card>
  )
}
