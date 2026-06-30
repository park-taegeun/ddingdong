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

// 화재경보 청각장애인 대응 수칙 — decisions.md 카테고리 7.1 확정 4단계 (2026-06-30 PoC-(20)).
// 도움말 카드 + 카카오 알림(11~14주차) 공용 SSoT. 임의 윤문 금지(확정 카피 ① 그대로).
export interface FireGuidelineStep {
  text: string
  subLines?: string[] // 보조 안내(신고 수단 등) — 들여쓰기 노출
}

export const FIRE_ALARM_GUIDELINES: FireGuidelineStep[] = [
  { text: "바로 대피하세요. 끄기·신고보다 대피가 먼저입니다." },
  {
    text: "엘리베이터 대신 비상계단으로, 젖은 천으로 입·코를 가리고 낮은 자세로 이동하세요.",
  },
  {
    text: "안전한 곳에 도착한 뒤 119에 신고하세요.",
    subLines: [
      "119 영상통화(수어)나 문자로 신고하세요. 음성통화 없이 가능합니다.",
      "「긴급신고 바로앱」도 사용할 수 있습니다.",
    ],
  },
  {
    text: "대피가 어려우면 화장실·베란다 창문 쪽으로 이동해, 휴대폰으로 119에 위치를 알리고(영상·문자), 창밖으로 손전등·밝은 천을 흔들며 구조를 기다리세요.",
  },
]

// 출처 라벨 (카테고리 7.1 확정 카피 ① 하단 ⓘ 출처 줄)
export const FIRE_ALARM_SOURCE =
  "출처: 소방청 「119 안전교육」(청각장애인용) · 119 영상통화 신고(손말이음센터 107)"

// skip_reason 한국어 라벨
export const SKIP_REASON_LABEL: Record<string, string> = {
  low_confidence: "신뢰도 부족",
  tof_rejected: "사람 감지 실패",
  kakao_api_error: "카카오 전송 오류",
  token_expired: "토큰 만료",
}
