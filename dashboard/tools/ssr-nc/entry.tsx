// SSR negative-control 진입점 — 실제 제품 컴포넌트(src/)를 픽스처와 함께 렌더해
// HTML 문자열만 내보낸다. 단언은 하지 않는다(= run.mjs 소관).
//
// ★ renderToStaticMarkup 을 쓰는 이유: renderToString 은 인접 표현식 사이에 `<!-- -->`
//   주석 마커를 넣어 텍스트 노드를 쪼갠다. run.mjs 의 단언은 텍스트 노드 **완전 일치**
//   비교이므로 마커가 끼면 비교 단위가 흔들린다.
// ★ 픽스처 시각·수치는 전부 고정 주입이다 — 실 서버·실 시계 미호출(8.5(g) 동형).
import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { StaleDataNotice } from "@/components/feedback/StaleDataNotice"
import { StatusBanner } from "@/components/feedback/StatusBanner"
import { BottomNav } from "@/components/layout/BottomNav"
import { NotificationCard } from "@/components/notifications/NotificationCard"
import { FilterEmpty, NotificationFilterBar } from "@/components/notifications/NotificationFilterBar"
import { NotificationImage } from "@/components/notifications/NotificationImage"
import { NotificationStatusBadge } from "@/components/notifications/NotificationStatusBadge"
import { NotificationSTT } from "@/components/notifications/NotificationSTT"
import { NotificationTof } from "@/components/notifications/NotificationTof"
import { SkipReasonsCard } from "@/components/stats/SkipReasonsCard"
import { SystemHealthCard } from "@/components/stats/SystemHealthCard"
import { SettingsProvider } from "@/contexts/SettingsContext"
import { deriveBanner } from "@/lib/banner"
import { deriveConnection, isStale } from "@/lib/connection"
import {
  FIRE_MOTION_WINDOW_MS,
  IMAGE_RETRY_INTERVAL_MS,
  IMAGE_RETRY_MAX,
  NOTIFICATIONS_PAGE_MAX,
  NOTIFICATIONS_PAGE_STEP,
  STALE_AFTER_MS,
} from "@/lib/constants"
import { formatDayHeading, formatDetectedAt } from "@/lib/format"
import { nextRetryDelay, retryUrl } from "@/lib/image-retry"
import { loadMoreState, nextLimit } from "@/lib/load-more"
import { filterNotifications, filterSummary, groupByDay } from "@/lib/notification-filter"
import { isWithinWindow } from "@/lib/notification-meta"
import { countNew, readLastSeen, titleWithCount } from "@/lib/unread"
import type { SeenStorage } from "@/lib/unread"
import type {
  NotificationItem,
  NotificationStatus,
  NotificationStt,
  PredictedClass,
  SkipReason,
  TofCheck,
} from "@/types/notification"
import type { SkipReasonCounts, SystemHealth, TokenStatus } from "@/types/stats"

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

// 이전 알림 더 보기 — 버튼 영역 상태 · 다음 개수. 정의역 밖은 던진다(텍스트 「오류」).
const LOAD_LABEL = { loading: "불러오는 중", end: "끝", max: "최대치", button: "버튼" } as const
const loadAt = (requested: number, receivedLimit: number, hasMore: boolean) => {
  try {
    return LOAD_LABEL[loadMoreState(requested, receivedLimit, hasMore, NOTIFICATIONS_PAGE_MAX)]
  } catch {
    return "오류"
  }
}
const nextAt = (current: number, step = NOTIFICATIONS_PAGE_STEP, max = NOTIFICATIONS_PAGE_MAX) => {
  try {
    return String(nextLimit(current, step, max))
  } catch {
    return "오류"
  }
}

// 알림 카드 날짜 — 지역 시간대 달력 날짜 경계. 픽스처 시각을 지역 시각 생성자로 만들어 실행 기계의
// 시간대와 무관하게 「자정 앞뒤」가 같은 뜻이 되게 한다(ISO 문자열 고정이면 시간대마다 날짜가 갈린다).
const DAY_NOW = new Date(2026, 9, 21, 9, 0)
const localIso = (y: number, mo: number, d: number, h: number, mi: number) =>
  new Date(y, mo, d, h, mi).toISOString()

// 뱃지 상태 — primary_sent · secondary_sent · enrich_status · 사진 전달 시각 · 사유 조합
function status(
  primary: boolean,
  secondary: boolean,
  enrich: NotificationStatus["enrich_status"],
  photoAt: string | null,
  skip?: SkipReason,
): NotificationStatus {
  return {
    primary_sent: primary,
    primary_sent_at: primary ? "2026-10-21T09:00:00.000+09:00" : null,
    enrich_status: enrich,
    secondary_sent: secondary,
    secondary_sent_at: photoAt,
    ...(skip ? { skip_reason: skip } : {}),
  }
}
const badge = (s: NotificationStatus) => renderToStaticMarkup(<NotificationStatusBadge status={s} />)
const PHOTO_AT = "2026-10-21T09:00:12.000+09:00"

// 렌더 결과의 class 속성 토큰을 텍스트 노드로 — 「클래스가 코드에 있다 ≠ 화면에 적용됐다」(twMerge 병합 뒤 실물)
const classTokens = (html: string) =>
  renderToStaticMarkup(
    <ul>
      {[...new Set([...html.matchAll(/class="([^"]*)"/g)].flatMap((m) => m[1].split(/\s+/)))].map(
        (t) => (
          <li key={t}>{t}</li>
        ),
      )}
    </ul>,
  )

// 알림 카드 — 화재 모션 창 · 카톡 실패 문장. 감지 시각은 실행 시계와 무관하게 결정적인 값만 쓴다
// (2020년 = 창 밖이 확실 · 2100년 = 지금보다 뒤라 창 안).
function item(cls: PredictedClass, detectedAt: string, s: NotificationStatus): NotificationItem {
  return {
    client_request_id: "nc",
    request_id: `nc-${cls}-${detectedAt}`,
    detected_at: detectedAt,
    predicted_class: cls,
    confidence: 0.9,
    all_scores: { doorbell: 0.03, knock: 0.03, fire_alarm: 0.9, other: 0.04 },
    tof_check: tof(false, null, "fire_alarm_bypass"),
    notification_status: s,
    media: { image_url: null, image_thumbnail_url: null, audio_url: null },
    stt: null,
    device_id: "nc",
  }
}
const card = (n: NotificationItem, isNew = false) =>
  renderToStaticMarkup(
    <SettingsProvider>
      <NotificationCard notification={n} isNew={isNew} />
    </SettingsProvider>,
  )
const WINDOW_NOW = Date.parse("2026-10-21T09:00:00.000+09:00")
const windowAt = (iso: string) =>
  isWithinWindow(iso, WINDOW_NOW, FIRE_MOTION_WINDOW_MS) ? "창 안" : "창 밖"

// 전역 경고 띠 — 우선순위 · 카톡 판정. 목록은 최신순(앞이 최신). 시각은 판정에 안 쓰인다.
const SENT = item("doorbell", "2026-10-21T09:00:00.000+09:00", status(true, false, "skipped", null))
const FAILED = item("knock", "2026-10-21T08:00:00.000+09:00", status(false, false, "skipped", null, "token_expired"))
const BLOCKED = item("other", "2026-10-21T10:00:00.000+09:00", status(false, false, "skipped", null, "not_target"))
const BANNER_LABEL = { server: "서버", device: "기기", kakao: "카톡" } as const
const bannerAt = (disconnected: boolean, isOnline: boolean, hasHealth: boolean, rows: NotificationItem[]) => {
  const k = deriveBanner(disconnected, isOnline, hasHealth, rows)
  return k ? BANNER_LABEL[k] : "없음"
}

// 알림 화면 필터 — 불러온 4건(초인종 보냄 · 노크 실패 · 기타 차단 · 초인종 차단) 안에서만 거른다.
const LOADED = [
  SENT,
  FAILED,
  BLOCKED,
  { ...item("doorbell", "2026-10-21T07:00:00.000+09:00", status(false, false, "skipped", null, "low_confidence")), request_id: "nc-doorbell-low" },
]
const filterAt = (cls: Parameters<typeof filterNotifications>[1], sentOnly: boolean) =>
  filterNotifications(LOADED, cls, sentOnly).length
const noop = () => {}

const SKIP_ZERO: SkipReasonCounts = {
  not_target: 0,
  low_confidence: 0,
  tof_rejected: 0,
  kakao_api_error: 0,
  token_expired: 0,
  registration_collecting: 0,
  registration_mismatch: 0,
}
// 카톡 실패 = 1 + 1(합쳐 2) · 0건 = 사람 감지 실패 · 등록 중 · 합계 8
const SKIP_SOME: SkipReasonCounts = {
  ...SKIP_ZERO,
  not_target: 3,
  low_confidence: 1,
  kakao_api_error: 1,
  token_expired: 1,
  registration_mismatch: 2,
}

// 새 알림 — 불러온 4건(초인종 보냄 9시 · 노크 실패 8시 · 기타 차단 10시 · 초인종 신뢰도 차단 7시) 기준.
// 차단 행이 확인 시각보다 뒤에 있어야 「발송 시도만 센다」가 결과를 가른다(기타 차단 10시).
const SEEN_6 = Date.parse("2026-10-21T06:00:00.000+09:00")
const SEEN_9 = Date.parse("2026-10-21T09:00:00.000+09:00")
const VISIT_NOW = Date.parse("2026-10-21T10:30:00.000+09:00")
const memStorage = (): SeenStorage => {
  const m = new Map<string, string>()
  return { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => void m.set(k, v) }
}
const brokenStorage: SeenStorage = {
  getItem: () => {
    throw new Error("blocked")
  },
  setItem: () => {
    throw new Error("blocked")
  },
}
// 저장소 상태 → 첫 방문 새 알림 수. 저장 함수가 던지면 「오류」(= 셸 렌더 실패).
const firstVisitAt = (storage: SeenStorage | null) => {
  try {
    return String(countNew(LOADED, readLastSeen(storage, VISIT_NOW)))
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

  // 8.4(d) STT 신뢰도 — 실측 0 과 값 부재(null)는 다르다. null 이면 신뢰도 칸 자체를 숨긴다(B9)
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
  // 이전 알림 더 보기 — 상태 4종(판정 순서 ①~④) · 정의역 밖
  load_more_state: renderToStaticMarkup(
    <ul>
      <li>{`요청40·받은20·더있음=${loadAt(40, 20, true)}`}</li>
      <li>{`요청20·받은20·더없음=${loadAt(20, 20, false)}`}</li>
      <li>{`요청100·받은100·더없음=${loadAt(100, 100, false)}`}</li>
      <li>{`요청100·받은100·더있음=${loadAt(100, 100, true)}`}</li>
      <li>{`요청40·받은40·더있음=${loadAt(40, 40, true)}`}</li>
      <li>{`요청0=${loadAt(0, 20, true)}`}</li>
    </ul>,
  ),
  // 이전 알림 더 보기 — 다음 개수 경계(최대에서 멈춤) · 정의역 밖
  load_more_next: renderToStaticMarkup(
    <ul>
      <li>{`다음20=${nextAt(20)}`}</li>
      <li>{`다음80=${nextAt(80)}`}</li>
      <li>{`다음90=${nextAt(90)}`}</li>
      <li>{`다음100=${nextAt(100)}`}</li>
      <li>{`다음0=${nextAt(0)}`}</li>
      <li>{`다음1.5=${nextAt(1.5)}`}</li>
      <li>{`최대작음=${nextAt(20, 20, 10)}`}</li>
    </ul>,
  ),
  // AU-18 I1 첫 렌더 — 사진 + 「크게 보기」, 실패 문구 없음(ImageLightbox가 설정 컨텍스트를 쓴다)
  image_first_render: renderToStaticMarkup(
    <SettingsProvider>
      <NotificationImage src="/captures/abc" alt="노크 감지 사진" />
    </SettingsProvider>,
  ),
  // B15 — 라이트박스 맥락 줄 prop 이 붙어도 첫 렌더는 같은 사진 + 「크게 보기」(재시도 상태 무변경)
  image_first_render_caption: renderToStaticMarkup(
    <SettingsProvider>
      <NotificationImage src="/captures/abc" alt="노크 감지 사진" caption={"노크 · 오후 2:05\n“택배입니다”"} />
    </SettingsProvider>,
  ),

  // B3 알림 카드 날짜 — 오늘 · 어제 · 그 전 · 다른 해 · 잘못된 값(기준 = 10월 21일 오전 9시 지역 시각)
  detected_at: renderToStaticMarkup(
    <ul>
      <li>{`오늘0시=${formatDetectedAt(localIso(2026, 9, 21, 0, 0), DAY_NOW)}`}</li>
      <li>{`어제2359=${formatDetectedAt(localIso(2026, 9, 20, 23, 59), DAY_NOW)}`}</li>
      <li>{`어제0시=${formatDetectedAt(localIso(2026, 9, 20, 0, 0), DAY_NOW)}`}</li>
      <li>{`그제2359=${formatDetectedAt(localIso(2026, 9, 19, 23, 59), DAY_NOW)}`}</li>
      <li>{`작년=${formatDetectedAt(localIso(2025, 11, 31, 23, 0), DAY_NOW)}`}</li>
      <li>{`잘못=${formatDetectedAt("x", DAY_NOW)}`}</li>
    </ul>,
  ),

  // B4 · 8.4 뱃지 — 6상태(발송 제외 · 보내기 실패 · 전송 완료 · 2차 처리 중 · 2차 실패 · 1차 발송)
  badge_blocked: badge(status(false, false, "skipped", null, "not_target")),
  badge_token_fail: badge(status(false, false, "skipped", null, "token_expired")),
  badge_api_fail: badge(status(false, false, "skipped", null, "kakao_api_error")),
  badge_complete: badge(status(true, true, "completed", PHOTO_AT)),
  badge_processing: badge(status(true, false, "processing", null)),
  badge_partial: badge(status(true, false, "failed", PHOTO_AT)),
  badge_primary_only: badge(status(true, false, "skipped", null)),
  // 7.6(d) 읽는 순서 — secondary_sent 를 enrich_status 보다 먼저 본다. 둘이 엇갈리는 입력에서만
  // 순서가 결과를 가른다(전송 완료 + 아직 처리 중 표기).
  badge_order: badge(status(true, true, "processing", PHOTO_AT)),
  // B5 뱃지 클래스 실물(twMerge 병합 뒤) — 15px 토큰이 남고 12px 기본은 지워졌는가
  badge_class: classTokens(badge(status(true, true, "completed", PHOTO_AT))),

  // B4 카드 문장 — 카톡 실패는 원인 없이 「카카오톡으로 보내지 못했어요.」, 차단은 기존 문장
  card_token_fail: card(item("knock", "2020-01-01T09:00:00.000+09:00", status(false, false, "skipped", null, "token_expired"))),
  card_blocked: card(item("other", "2020-01-01T09:00:00.000+09:00", status(false, false, "skipped", null, "not_target"))),

  // B10 화재 모션 창 — 경계 포함 · 미래 · 잘못된 시각
  fire_window: renderToStaticMarkup(
    <ul>
      <li>{`10분=${windowAt("2026-10-21T08:50:00.000+09:00")}`}</li>
      <li>{`10분1ms=${windowAt("2026-10-21T08:49:59.999+09:00")}`}</li>
      <li>{`미래=${windowAt("2026-10-21T09:05:00.000+09:00")}`}</li>
      <li>{`잘못=${windowAt("x")}`}</li>
    </ul>,
  ),
  fire_card_old: classTokens(card(item("fire_alarm", "2020-01-01T09:00:00.000+09:00", status(true, false, "skipped", null)))),
  fire_card_new: classTokens(card(item("fire_alarm", "2100-01-01T09:00:00.000+09:00", status(true, false, "skipped", null)))),

  // 전역 경고 띠 — 우선순위(끊김 > 기기 꺼짐 > 카톡) · 최신 발송 시도 행 기준 · 차단 행 건너뛰기
  banner_kind: renderToStaticMarkup(
    <ul>
      <li>{`끊김·꺼짐·실패=${bannerAt(true, false, true, [FAILED])}`}</li>
      <li>{`꺼짐·실패=${bannerAt(false, false, true, [FAILED])}`}</li>
      <li>{`켜짐·실패=${bannerAt(false, true, true, [FAILED])}`}</li>
      <li>{`켜짐·차단뒤실패=${bannerAt(false, true, true, [BLOCKED, FAILED])}`}</li>
      <li>{`켜짐·보냄뒤실패=${bannerAt(false, true, true, [SENT, FAILED])}`}</li>
      <li>{`켜짐·실패뒤보냄=${bannerAt(false, true, true, [FAILED, SENT])}`}</li>
      <li>{`켜짐·차단만=${bannerAt(false, true, true, [BLOCKED])}`}</li>
      <li>{`상태모름·목록없음=${bannerAt(false, false, false, [])}`}</li>
    </ul>,
  ),
  banner_server: renderToStaticMarkup(<StatusBanner kind="server" />),
  banner_kakao: renderToStaticMarkup(<StatusBanner kind="kakao" />),
  banner_none: renderToStaticMarkup(<StatusBanner kind={null} />),

  // 알림 화면 날짜 묶음 머리 — 달력(자정) 경계 · 다른 해 · 잘못된 값(기준 = 10월 21일 오전 9시 지역 시각)
  day_heading: renderToStaticMarkup(
    <ul>
      <li>{`오늘0시=${formatDayHeading(localIso(2026, 9, 21, 0, 0), DAY_NOW)}`}</li>
      <li>{`어제2359=${formatDayHeading(localIso(2026, 9, 20, 23, 59), DAY_NOW)}`}</li>
      <li>{`어제0시=${formatDayHeading(localIso(2026, 9, 20, 0, 0), DAY_NOW)}`}</li>
      <li>{`그제2359=${formatDayHeading(localIso(2026, 9, 19, 23, 59), DAY_NOW)}`}</li>
      <li>{`작년=${formatDayHeading(localIso(2025, 11, 31, 23, 0), DAY_NOW)}`}</li>
      <li>{`잘못=${formatDayHeading("x", DAY_NOW)}`}</li>
    </ul>,
  ),
  // 날짜 묶음 — 최신순 4건이 자정을 사이에 두고 「오늘 2 · 어제 1 · 10월 19일 1」로 나뉜다
  day_groups: renderToStaticMarkup(
    <ul>
      {groupByDay(
        [
          localIso(2026, 9, 21, 8, 0),
          localIso(2026, 9, 21, 0, 0),
          localIso(2026, 9, 20, 23, 59),
          localIso(2026, 9, 19, 12, 0),
        ].map((iso) => item("doorbell", iso, status(true, false, "skipped", null))),
        DAY_NOW,
      ).map((g) => (
        <li key={g.heading}>{`${g.heading}=${g.items.length}`}</li>
      ))}
    </ul>,
  ),

  // 알림 화면 필터 — 종류 · 보낸 알림만 · 둘 다 · 범위 안내
  filter_result: renderToStaticMarkup(
    <ul>
      <li>{`전체=${filterAt("all", false)}`}</li>
      <li>{`초인종=${filterAt("doorbell", false)}`}</li>
      <li>{`기타=${filterAt("other", false)}`}</li>
      <li>{`보낸만=${filterAt("all", true)}`}</li>
      <li>{`초인종·보낸만=${filterAt("doorbell", true)}`}</li>
      <li>{`노크·보낸만=${filterAt("knock", true)}`}</li>
      <li>{filterSummary(LOADED.length, filterAt("doorbell", true))}</li>
    </ul>,
  ),
  filter_bar: renderToStaticMarkup(
    <NotificationFilterBar cls="fire_alarm" sentOnly={false} onClsChange={noop} onSentOnlyChange={noop} />,
  ),
  filter_empty: renderToStaticMarkup(<FilterEmpty onClear={noop} />),

  // 새 알림 — 발송 시도 행만 · 확인 시각 경계(같은 시각은 새 알림 아님) · 첫 방문 0 · 저장 실패여도 동작
  unread_count: renderToStaticMarkup(
    <ul>
      <li>{`6시확인=${countNew(LOADED, SEEN_6)}`}</li>
      <li>{`9시확인=${countNew(LOADED, SEEN_9)}`}</li>
      <li>{`첫방문=${firstVisitAt(memStorage())}`}</li>
      <li>{`저장소없음=${firstVisitAt(null)}`}</li>
      <li>{`저장실패=${firstVisitAt(brokenStorage)}`}</li>
      <li>{`제목2=${titleWithCount(2, "띵동 — 알림 대시보드")}`}</li>
      <li>{`제목0=${titleWithCount(0, "띵동 — 알림 대시보드")}`}</li>
    </ul>,
  ),
  // 폰 폭 하단 탭 — NAV_ITEMS 5개 글자(현재 위치 = 통계). 배치 · 겹침 · 안전 영역은 사정권 밖(화면 확인).
  bottom_nav: renderToStaticMarkup(
    <MemoryRouter initialEntries={["/stats"]}>
      <BottomNav />
    </MemoryRouter>,
  ),
  // 오늘 보내지 않은 이유 — 0건 줄 숨김 · 카톡 실패 2키 합산(원인 어휘 없음) · 합계 · 전부 0이면 빈 상태
  skip_some: renderToStaticMarkup(<SkipReasonsCard counts={SKIP_SOME} />),
  skip_some_class: classTokens(renderToStaticMarkup(<SkipReasonsCard counts={SKIP_SOME} />)),
  skip_no_fail_class: classTokens(renderToStaticMarkup(<SkipReasonsCard counts={{ ...SKIP_ZERO, not_target: 2 }} />)),
  skip_zero: renderToStaticMarkup(<SkipReasonsCard counts={SKIP_ZERO} />),
  card_new: card(item("doorbell", "2020-01-01T09:00:00.000+09:00", status(true, false, "skipped", null)), true),
}
