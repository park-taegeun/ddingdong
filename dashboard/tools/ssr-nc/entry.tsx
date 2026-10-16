// SSR negative-control 진입점 — 실제 제품 컴포넌트(src/)를 픽스처와 함께 렌더해
// HTML 문자열만 내보낸다. 단언은 하지 않는다(= run.mjs 소관).
//
// ★ renderToStaticMarkup 을 쓰는 이유: renderToString 은 인접 표현식 사이에 `<!-- -->`
//   주석 마커를 넣어 텍스트 노드를 쪼갠다. run.mjs 의 단언은 텍스트 노드 **완전 일치**
//   비교이므로 마커가 끼면 비교 단위가 흔들린다.
// ★ 픽스처 시각·수치는 전부 고정 주입이다 — 실 서버·실 시계 미호출(8.5(g) 동형).
import { renderToStaticMarkup } from "react-dom/server"
import { StaleDataNotice } from "@/components/feedback/StaleDataNotice"
import { NotificationImage } from "@/components/notifications/NotificationImage"
import { NotificationSTT } from "@/components/notifications/NotificationSTT"
import { NotificationTof } from "@/components/notifications/NotificationTof"
import { SystemHealthCard } from "@/components/stats/SystemHealthCard"
import { SettingsProvider } from "@/contexts/SettingsContext"
import { deriveConnection, isStale } from "@/lib/connection"
import { IMAGE_RETRY_INTERVAL_MS, IMAGE_RETRY_MAX, STALE_AFTER_MS } from "@/lib/constants"
import { nextRetryDelay, retryUrl } from "@/lib/image-retry"
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

// AU-07 끊김 판정 — 고정 시각 기준 경과 ms 로 판정 결과를 텍스트로 낸다.
const LAST_OK = new Date("2026-10-13T12:00:00+09:00")
const staleAt = (elapsedMs: number) =>
  isStale(LAST_OK, false, LAST_OK.getTime() + elapsedMs, STALE_AFTER_MS) ? "끊김" : "정상"
const connLabel = (isOnline: boolean, hasHealth: boolean, disconnected: boolean) =>
  deriveConnection(isOnline, hasHealth, disconnected).label

// AU-18 사진 재시도 — 실패 횟수 → 다음 지연(ms) | 중단, 정의역 밖은 던진다(텍스트 「오류」).
const retryAt = (failures: number) => {
  try {
    const d = nextRetryDelay(failures, IMAGE_RETRY_MAX, IMAGE_RETRY_INTERVAL_MS)
    return d === null ? "중단" : `${d}ms`
  } catch {
    return "오류"
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

  // AU-07 끊김 안내 — 마지막 성공 12초 뒤(「방금 전」은 10초 미만이라 피함)
  stale_notice: renderToStaticMarkup(
    <StaleDataNotice lastUpdated={LAST_OK} now={new Date(LAST_OK.getTime() + 12_000)} />,
  ),
  // AU-07 I1 경계 · I2 첫 성공 전
  stale_boundary: renderToStaticMarkup(
    <ul>
      <li>{`5999ms=${staleAt(5_999)}`}</li>
      <li>{`6000ms=${staleAt(6_000)}`}</li>
      <li>{`첫성공전오류=${isStale(null, true, LAST_OK.getTime(), STALE_AFTER_MS) ? "끊김" : "정상"}`}</li>
      <li>{`첫성공전대기=${isStale(null, false, LAST_OK.getTime(), STALE_AFTER_MS) ? "끊김" : "정상"}`}</li>
    </ul>,
  ),
  // AU-07 I5 헤더 4상태 (끊김 우선)
  conn_labels: renderToStaticMarkup(
    <ul>
      <li>{`온라인+끊김=${connLabel(true, true, true)}`}</li>
      <li>{`온라인=${connLabel(true, true, false)}`}</li>
      <li>{`오프라인=${connLabel(false, true, false)}`}</li>
      <li>{`확인중=${connLabel(false, false, false)}`}</li>
    </ul>,
  ),
  // AU-18 I2 재시도 상한 — 경계 점(실패 6 = 마지막 재시도 · 실패 7 = 중단) · 정의역 밖(실패 0)
  image_retry_delay: renderToStaticMarkup(
    <ul>
      <li>{`실패1=${retryAt(1)}`}</li>
      <li>{`실패6=${retryAt(6)}`}</li>
      <li>{`실패7=${retryAt(7)}`}</li>
      <li>{`실패0=${retryAt(0)}`}</li>
    </ul>,
  ),
  // AU-18 I7 재시도 URL — 상대 · 절대 · 기존 쿼리 · 해시
  image_retry_url: renderToStaticMarkup(
    <ul>
      <li>{retryUrl("/captures/abc", 1)}</li>
      <li>{retryUrl("https://x.example/captures/abc", 2)}</li>
      <li>{retryUrl("/captures/abc?v=1", 3)}</li>
      <li>{retryUrl("/captures/abc#top", 4)}</li>
    </ul>,
  ),
  // AU-18 I1 첫 렌더 — 사진 + 「크게 보기」, 실패 문구 없음(ImageLightbox가 설정 컨텍스트를 쓴다)
  image_first_render: renderToStaticMarkup(
    <SettingsProvider>
      <NotificationImage src="/captures/abc" alt="노크 감지 사진" />
    </SettingsProvider>,
  ),
}
