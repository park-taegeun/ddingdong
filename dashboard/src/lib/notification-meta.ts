// 알림 클래스 3종 메타데이터 — 도어벨/노크/화재경보 분기 DRY 단일 출처.
// NotificationCard / ClassDistributionCard / 차트 등에서 공통 참조.

import { Bell, Flame, Hand } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import type { PredictedClass } from "@/types/notification"

export interface ClassMeta {
  label: string
  icon: LucideIcon
  iconColor: string // text-* 토큰
  bgColor: string // 아이콘 배경 bg-* 토큰
  dotColor: string // 상태 dot bg-* 토큰
  chartVar: string // 차트 색상 CSS 변수
}

export const CLASS_META: Record<PredictedClass, ClassMeta> = {
  doorbell: {
    label: "초인종",
    icon: Bell,
    iconColor: "text-primary",
    bgColor: "bg-primary/10",
    dotColor: "bg-primary",
    chartVar: "var(--color-chart-1)",
  },
  knock: {
    label: "노크",
    icon: Hand,
    iconColor: "text-warning",
    bgColor: "bg-warning/10",
    dotColor: "bg-warning",
    chartVar: "var(--color-chart-2)",
  },
  fire_alarm: {
    label: "화재경보",
    icon: Flame,
    iconColor: "text-danger",
    bgColor: "bg-danger/10",
    dotColor: "bg-danger",
    chartVar: "var(--color-chart-3)",
  },
}

export const PREDICTED_CLASS_ORDER: PredictedClass[] = [
  "doorbell",
  "knock",
  "fire_alarm",
]

// 화재경보 정부 지정 대응 수칙 3종 (decisions.md 카테고리 7 / 26.3 화재경보 진입점)
export const FIRE_ALARM_GUIDELINES = [
  "119에 즉시 신고하세요.",
  "낮은 자세로 대피로를 확보해 이동하세요.",
  "젖은 수건으로 코와 입을 막으세요.",
] as const

// skip_reason 한국어 라벨
export const SKIP_REASON_LABEL: Record<string, string> = {
  low_confidence: "신뢰도 부족",
  tof_rejected: "사람 감지 실패",
  kakao_api_error: "카카오 전송 오류",
  token_expired: "토큰 만료",
}
