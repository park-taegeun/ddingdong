// SSR negative-control 진입점 — 실제 제품 컴포넌트(src/)를 픽스처와 함께 렌더해
// HTML 문자열만 내보낸다. 단언은 하지 않는다(= run.mjs 소관).
//
// ★ renderToStaticMarkup 을 쓰는 이유: renderToString 은 인접 표현식 사이에 `<!-- -->`
//   주석 마커를 넣어 텍스트 노드를 쪼갠다. run.mjs 의 단언은 텍스트 노드 **완전 일치**
//   비교이므로 마커가 끼면 비교 단위가 흔들린다.
// ★ 픽스처 시각·수치는 전부 고정 주입이다 — 실 서버·실 시계 미호출(8.5(g) 동형).
import { renderToStaticMarkup } from "react-dom/server"
import { NotificationSTT } from "@/components/notifications/NotificationSTT"
import { NotificationTof } from "@/components/notifications/NotificationTof"
import { SystemHealthCard } from "@/components/stats/SystemHealthCard"
import type { NotificationStt, TofCheck } from "@/types/notification"
import type { SystemHealth, TokenStatus } from "@/types/stats"

function health(status: TokenStatus, minutes: number): SystemHealth {
  return {
    device_last_seen_at: "2026-09-09T12:00:00+09:00",
    device_status: "online",
    signal_strength: "strong",
    kakao_token_status: status,
    kakao_token_expires_in_minutes: minutes,
    clova_api_status: "ok",
    db_status: "ok",
  }
}

function tof(applied: boolean, passed: boolean | null, reason: string): TofCheck {
  return { applied, passed, reason }
}

function stt(confidence: number | null): NotificationStt {
  return {
    transcript: "택배입니다",
    confidence,
    language: "ko-KR",
    processed_at: "2026-09-09T12:00:00+09:00",
  }
}

export const output: Record<string, string> = {
  // 8.5(f) 실렌더 대조 픽스처 (카카오 토큰 3상태 + 만료 경과 환산)
  token_valid: renderToStaticMarkup(<SystemHealthCard health={health("valid", 360)} />),
  token_expiring: renderToStaticMarkup(<SystemHealthCard health={health("expiring", 5)} />),
  token_expired_10m: renderToStaticMarkup(<SystemHealthCard health={health("expired", -10)} />),
  token_expired_3d: renderToStaticMarkup(<SystemHealthCard health={health("expired", -4320)} />),

  // 8.4(b) ToF 3상태 (6.4(c) "구분 가능" 불변식의 화면 판)
  tof_passed: renderToStaticMarkup(
    <NotificationTof tof={tof(true, true, "presence=true near=12/64 center=830mm ndet=3/16")} />,
  ),
  tof_rejected: renderToStaticMarkup(
    <NotificationTof tof={tof(true, false, "presence=false near=1/64 center=2450mm ndet=0/16")} />,
  ),
  tof_absent: renderToStaticMarkup(<NotificationTof tof={tof(false, null, "tof_absent")} />),

  // 8.4(d) STT 신뢰도 — 실측 0 과 값 부재(null)는 다르다
  stt_conf_zero: renderToStaticMarkup(<NotificationSTT stt={stt(0)} />),
  stt_conf_null: renderToStaticMarkup(<NotificationSTT stt={stt(null)} />),
}
