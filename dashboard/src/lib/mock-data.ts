// Phase 1 mock 데이터 (SSoT: 위임 프롬프트 섹션 4 응답 구조).
// Phase 2 진입 시 이 파일은 제거하고 lib/api.ts의 fetch가 실제 서버를 호출.

import type { NotificationItem } from "@/types/notification"
import type { StatsResponse } from "@/types/stats"
import { DEVICE_ID } from "./constants"

// 알림 5종: 초인종(성공) / 노크(성공) / 화재경보(우회) / 초인종(신뢰도 부족) / 노크(2차 처리중)
//
// ★ tof_check.reason = 서버가 실제로 내는 어휘 형식(tof_meta.telemetry_summary):
//   "presence=<true|false> near=<n>/64 center=<n>mm ndet=<n>/16" — 9.3(b) 펌웨어 시리얼
//   로그 표기와 동형이다. 구 가짜 ToF 하드코딩 문자열은 서버 /detect 경로에서 이미
//   소멸했으므로(6.4(e) 실측) 여기 남아 있으면 화면이 실물과 어긋난다(6.4(f) 미결).
//   수치 자체는 개발용 픽스처지 실측값이 아니다 — 형식만 실물을 따른다.
// ★ 3상태(통과 / 거부 / 미적용)가 모두 들어 있어야 NotificationTof 의 분기를 개발 중에
//   눈으로 확인할 수 있다: 통과 3건 + 거부 1건(신뢰도 부족 건) + 미적용 1건(화재경보).
export const MOCK_NOTIFICATIONS: NotificationItem[] = [
  {
    client_request_id: "esp_1716878531_0005",
    request_id: "req_01HZQ9D2K3M4N5P6Q7R8S9T0U5",
    detected_at: "2026-05-28T16:02:11.900+09:00",
    predicted_class: "knock",
    confidence: 0.79,
    all_scores: { doorbell: 0.16, knock: 0.79, fire_alarm: 0.05 },
    tof_check: {
      applied: true,
      passed: true,
      reason: "presence=true near=11/64 center=1015mm ndet=4/16",
    },
    notification_status: {
      primary_sent: true,
      primary_sent_at: "2026-05-28T16:02:13.420+09:00",
      enrich_status: "processing",
      secondary_sent: false,
      secondary_sent_at: null,
    },
    media: {
      image_url: "/static/captures/req_01HZQ9D2K3.jpg",
      image_thumbnail_url: "/static/captures/thumb_req_01HZQ9D2K3.jpg",
      audio_url: "/static/audio/req_01HZQ9D2K3.wav",
    },
    stt: null,
    device_id: DEVICE_ID,
  },
  {
    client_request_id: "esp_1716874245_0001",
    request_id: "req_01HZQ8X7K3M4N5P6Q7R8S9T0U1",
    detected_at: "2026-05-28T15:30:45.456+09:00",
    predicted_class: "doorbell",
    confidence: 0.87,
    all_scores: { doorbell: 0.87, knock: 0.09, fire_alarm: 0.04 },
    tof_check: {
      applied: true,
      passed: true,
      reason: "presence=true near=13/64 center=980mm ndet=3/16",
    },
    notification_status: {
      primary_sent: true,
      primary_sent_at: "2026-05-28T15:30:47.890+09:00",
      enrich_status: "completed",
      secondary_sent: true,
      secondary_sent_at: "2026-05-28T15:30:56.123+09:00",
    },
    media: {
      image_url: "/static/captures/req_01HZQ8X7K3.jpg",
      image_thumbnail_url: "/static/captures/thumb_req_01HZQ8X7K3.jpg",
      audio_url: "/static/audio/req_01HZQ8X7K3.wav",
    },
    stt: {
      transcript: "택배 왔습니다. 문 앞에 두고 갈게요.",
      confidence: 0.94,
      language: "ko-KR",
      processed_at: "2026-05-28T15:30:55.700+09:00",
    },
    device_id: DEVICE_ID,
  },
  {
    client_request_id: "esp_1716869528_0004",
    request_id: "req_01HZQ7M1K3M4N5P6Q7R8S9T0U4",
    detected_at: "2026-05-28T14:12:08.220+09:00",
    predicted_class: "knock",
    confidence: 0.81,
    all_scores: { doorbell: 0.14, knock: 0.81, fire_alarm: 0.05 },
    tof_check: {
      applied: true,
      passed: true,
      reason: "presence=true near=10/64 center=1150mm ndet=2/16",
    },
    notification_status: {
      primary_sent: true,
      primary_sent_at: "2026-05-28T14:12:10.510+09:00",
      enrich_status: "completed",
      secondary_sent: true,
      secondary_sent_at: "2026-05-28T14:12:18.640+09:00",
    },
    media: {
      image_url: "/static/captures/req_01HZQ7M1K3.jpg",
      image_thumbnail_url: "/static/captures/thumb_req_01HZQ7M1K3.jpg",
      audio_url: "/static/audio/req_01HZQ7M1K3.wav",
    },
    stt: {
      transcript: "계세요? 옆집인데요.",
      // 실 CSR 경로 재현 — 신뢰도 미제공(30.9). "0%" 가 아니라 "정보 없음"으로 떠야 한다.
      confidence: null,
      language: "ko-KR",
      processed_at: "2026-05-28T14:12:17.900+09:00",
    },
    device_id: DEVICE_ID,
  },
  {
    client_request_id: "esp_1716865533_0003",
    request_id: "req_01HZQ6F0K3M4N5P6Q7R8S9T0U3",
    detected_at: "2026-05-28T13:05:33.100+09:00",
    predicted_class: "fire_alarm",
    confidence: 0.93,
    all_scores: { doorbell: 0.04, knock: 0.03, fire_alarm: 0.93 },
    tof_check: {
      applied: false,
      passed: null,
      reason: "fire_alarm_bypass",
    },
    notification_status: {
      primary_sent: true,
      primary_sent_at: "2026-05-28T13:05:34.210+09:00",
      enrich_status: "skipped",
      secondary_sent: false,
      secondary_sent_at: null,
    },
    media: {
      image_url: null,
      image_thumbnail_url: null,
      audio_url: null,
    },
    stt: null,
    device_id: DEVICE_ID,
  },
  {
    client_request_id: "esp_1716860900_0002",
    request_id: "req_01HZQ5B9K3M4N5P6Q7R8S9T0U2",
    detected_at: "2026-05-28T11:48:20.700+09:00",
    predicted_class: "doorbell",
    confidence: 0.52,
    all_scores: { doorbell: 0.52, knock: 0.39, fire_alarm: 0.09 },
    tof_check: {
      // 거부 상태(passed=false). 신뢰도 게이트가 ToF 보다 먼저 걸려(G12 확정, PR #46)
      // skip_reason 은 low_confidence 지만, 게이트를 적용해 사람이 없었다는 기록은 남는다.
      applied: true,
      passed: false,
      reason: "presence=false near=1/64 center=2953mm ndet=0/16",
    },
    notification_status: {
      primary_sent: false,
      primary_sent_at: null,
      enrich_status: "skipped",
      secondary_sent: false,
      secondary_sent_at: null,
      skip_reason: "low_confidence",
    },
    media: {
      image_url: null,
      image_thumbnail_url: null,
      audio_url: null,
    },
    stt: null,
    device_id: DEVICE_ID,
  },
]

export const MOCK_STATS: StatsResponse = {
  period: "today",
  period_start: "2026-05-28T00:00:00+09:00",
  period_end: "2026-05-28T23:59:59+09:00",
  server_time: "2026-05-28T16:05:00+09:00",
  summary: {
    total_detections: 14,
    total_notifications_sent: 11,
    skip_count: 3,
    average_confidence: 0.83,
  },
  class_distribution: {
    doorbell: {
      count: 8,
      percentage: 57.1,
      average_confidence: 0.85,
      notifications_sent: 7,
    },
    knock: {
      count: 4,
      percentage: 28.6,
      average_confidence: 0.78,
      notifications_sent: 3,
    },
    fire_alarm: {
      count: 2,
      percentage: 14.3,
      average_confidence: 0.91,
      notifications_sent: 1,
    },
  },
  timing_metrics: {
    primary_notification_avg_ms: 2847,
    primary_notification_max_ms: 4521,
    secondary_notification_avg_ms: 12350,
    secondary_notification_max_ms: 14890,
    primary_under_5s_rate: 1.0,
    secondary_under_15s_rate: 0.92,
  },
  skip_reasons: {
    low_confidence: 2,
    tof_rejected: 1,
    kakao_api_error: 0,
    token_expired: 0,
  },
  system_health: {
    device_last_seen_at: "2026-05-28T16:04:50+09:00",
    device_status: "online",
    signal_strength: "strong",
    kakao_token_status: "valid",
    kakao_token_expires_in_minutes: 240,
    clova_api_status: "ok",
    db_status: "ok",
  },
  hourly_distribution: [
    { hour: "00", count: 0 },
    { hour: "01", count: 0 },
    { hour: "02", count: 0 },
    { hour: "03", count: 0 },
    { hour: "04", count: 0 },
    { hour: "05", count: 0 },
    { hour: "06", count: 0 },
    { hour: "07", count: 0 },
    { hour: "08", count: 1 },
    { hour: "09", count: 1 },
    { hour: "10", count: 2 },
    { hour: "11", count: 1 },
    { hour: "12", count: 0 },
    { hour: "13", count: 1 },
    { hour: "14", count: 2 },
    { hour: "15", count: 5 },
    { hour: "16", count: 1 },
    { hour: "17", count: 0 },
    { hour: "18", count: 0 },
    { hour: "19", count: 0 },
    { hour: "20", count: 0 },
    { hour: "21", count: 0 },
    { hour: "22", count: 0 },
    { hour: "23", count: 0 },
  ],
}
