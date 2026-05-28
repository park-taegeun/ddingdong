// GET /api/v1/stats 응답 타입 (SSoT: 위임 프롬프트 섹션 4, period = today 단일)

import type { PredictedClass } from "./notification"

export type StatsPeriod = "today"
export type DeviceStatus = "online" | "offline" | "processing"
export type TokenStatus = "valid" | "expiring" | "expired"
export type ServiceStatus = "ok" | "degraded" | "error"

export interface StatsSummary {
  total_detections: number
  total_notifications_sent: number
  skip_count: number
  average_confidence: number
}

export interface ClassDistributionItem {
  count: number
  percentage: number
  average_confidence: number
  notifications_sent: number
}

export type ClassDistribution = Record<PredictedClass, ClassDistributionItem>

export interface TimingMetrics {
  primary_notification_avg_ms: number
  primary_notification_max_ms: number
  secondary_notification_avg_ms: number
  secondary_notification_max_ms: number
  primary_under_5s_rate: number
  secondary_under_15s_rate: number
}

export interface SkipReasonCounts {
  low_confidence: number
  tof_rejected: number
  kakao_api_error: number
  token_expired: number
}

export interface SystemHealth {
  device_last_seen_at: string
  device_status: DeviceStatus
  kakao_token_status: TokenStatus
  kakao_token_expires_in_minutes: number
  clova_api_status: ServiceStatus
  db_status: ServiceStatus
}

export interface HourlyDistributionItem {
  hour: string
  count: number
}

export interface StatsResponse {
  period: StatsPeriod
  period_start: string
  period_end: string
  server_time: string
  summary: StatsSummary
  class_distribution: ClassDistribution
  timing_metrics: TimingMetrics
  skip_reasons: SkipReasonCounts
  system_health: SystemHealth
  hourly_distribution: HourlyDistributionItem[]
}
