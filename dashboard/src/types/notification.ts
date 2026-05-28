// GET /api/v1/notifications 응답 타입 (SSoT: 위임 프롬프트 섹션 4)
// Phase 1 = mock, Phase 2 = 실제 서버 응답. 구조는 동일.

export type PredictedClass = "doorbell" | "knock" | "fire_alarm"

export type EnrichStatus =
  | "completed"
  | "processing"
  | "pending"
  | "skipped"
  | "failed"

export type SkipReason =
  | "low_confidence"
  | "tof_rejected"
  | "kakao_api_error"
  | "token_expired"

export interface AllScores {
  doorbell: number
  knock: number
  fire_alarm: number
}

export interface TofCheck {
  applied: boolean
  passed: boolean | null
  reason: string
}

export interface NotificationStatus {
  primary_sent: boolean
  primary_sent_at: string | null
  enrich_status: EnrichStatus
  secondary_sent: boolean
  secondary_sent_at: string | null
  // 신뢰도 부족 등으로 1차 알림 미발송 시 사유 (섹션 4)
  skip_reason?: SkipReason
}

export interface NotificationMedia {
  image_url: string | null
  image_thumbnail_url: string | null
  audio_url: string | null
}

export interface NotificationStt {
  transcript: string
  confidence: number
  language: string
  processed_at: string
}

export interface NotificationItem {
  client_request_id: string
  request_id: string
  detected_at: string
  predicted_class: PredictedClass
  confidence: number
  all_scores: AllScores
  tof_check: TofCheck
  notification_status: NotificationStatus
  // 화재경보 = 모든 필드 null, 신뢰도 부족 = 일부 null
  media: NotificationMedia
  // 화재경보 = null
  stt: NotificationStt | null
  device_id: string
}
