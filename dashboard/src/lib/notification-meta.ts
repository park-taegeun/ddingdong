// 알림 클래스 4종(알림 대상 3종 + other) 메타데이터 — 초인종/노크/화재경보/기타 소리 분기 DRY 단일 출처.
// NotificationCard / ClassDistributionCard / 차트 등에서 공통 참조.

import { AudioLines, Bell, DoorClosed, Flame } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { CAPTURE_TTL_HOURS } from "@/lib/constants"
import type { PredictedClass, SkipReason } from "@/types/notification"

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
  // 노크 = 닫힌 문(카톡 🚪와 같은 뜻). 아이콘 색은 경고색의 글자용 대비 보정분(랜딩 토큰 재사용) —
  // 원래 경고색은 옅은 배경 위 1.80:1로 비텍스트 3:1에 못 미쳤다(보정분 5.53:1 · 다크 8.4:1).
  knock: {
    label: "노크",
    icon: DoorClosed,
    iconColor: "text-lp-amber",
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
  // 알림 대상이 아닌 소리(33.13(a)) — 경보 톤을 피해 기존 중립 토큰(foreground-secondary
  // = chart-5)만 쓴다. 아이콘은 기존 lucide 세트의 일반 "소리" 기호.
  other: {
    label: "기타 소리",
    icon: AudioLines,
    iconColor: "text-foreground-secondary",
    bgColor: "bg-foreground-secondary/10",
    dotColor: "bg-foreground-secondary",
    chartVar: "var(--color-chart-5)",
  },
}

export const PREDICTED_CLASS_ORDER: PredictedClass[] = [
  "doorbell",
  "knock",
  "fire_alarm",
]

// 통계(클래스 분포) 표시 순서 = 알림 대상 3종 + other. PREDICTED_CLASS_ORDER 는 도움말·
// 온보딩의 "감지하는 소리 3가지" 카피가 쓰므로 other 를 넣지 않는다.
export const STATS_CLASS_ORDER: PredictedClass[] = [...PREDICTED_CLASS_ORDER, "other"]

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
  not_target: "알림 대상이 아닌 소리",
  low_confidence: "신뢰도 부족",
  tof_rejected: "사람 감지 실패",
  kakao_api_error: "카카오 전송 오류",
  token_expired: "토큰 만료",
  // 카드 문장 = 「{라벨} 때문에 알림을 보내지 않았어요.」 — 저장 · 출처를 단정하지 않는다.
  registration_collecting: "초인종 등록 중에 들어온 소리",
  registration_mismatch: "등록한 초인종과 다른 소리",
}

// 스크린리더 announcer 가 읽지 않는 사유 — 등록 판정이 막은 행(other 미announce 와 같은 축).
// 목록 행 표시는 유지한다.
export const SILENT_SKIP_REASONS: ReadonlySet<SkipReason> = new Set<SkipReason>([
  "registration_collecting",
  "registration_mismatch",
])

// 카카오 발송 실패 사유 — 위 다른 사유(의도된 차단)와 달리 보내려다 못 보낸 것이다.
// 화면은 원인(내부 어휘)을 말하지 않고 「카카오톡으로 보내지 못했어요」로만 알린다.
export const KAKAO_FAILURE_REASONS: ReadonlySet<SkipReason> = new Set<SkipReason>([
  "token_expired",
  "kakao_api_error",
])

// 감지 후 windowMs 이내인가 — 경계 포함(경과 == windowMs 면 이내). 지금보다 뒤 시각(시계 어긋남)도 이내.
// 원값(ms) 비교만 한다 — 표시용 시각 문자열 · 반올림을 쓰지 않는다. 잘못된 시각은 이내가 아니다.
export function isWithinWindow(iso: string, nowMs: number, windowMs: number): boolean {
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return false
  return nowMs - t <= windowMs
}

// 사진 보관 기간(CAPTURE_TTL_HOURS)이 지났는가 — 서버 image_store 와 같은 「초과」 경계(정확히 72시간 = 아직 보관).
// 잘못된 시각은 지나지 않은 것으로 본다(지금처럼 요청해 본다).
// 한계 ① 서버 기준 = 파일 수정 시각(≈ 2차 처리 끝 = 감지 몇 초 뒤) · 여기 기준 = 감지 시각 → 경계 몇 초 동안은
//   지나기 전으로 보고 요청했다가 기존 실패 표시가 뜰 수 있다(무해).
// ② 브라우저 시계와 서버 시계가 어긋나면 그만큼 경계가 밀린다(lib/unread.ts 한계 ①과 같은 성격).
const CAPTURE_TTL_MS = CAPTURE_TTL_HOURS * 3_600_000
export function isPhotoExpired(iso: string, nowMs: number): boolean {
  const t = new Date(iso).getTime()
  return !Number.isNaN(t) && nowMs - t > CAPTURE_TTL_MS
}
