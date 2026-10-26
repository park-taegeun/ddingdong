import { useEffect, useState } from "react"
import { ChevronDown, MessageSquareOff, TriangleAlert } from "lucide-react"
import { useSettings } from "@/contexts/SettingsContext"
import { FIRE_MOTION_WINDOW_MS } from "@/lib/constants"
import { formatConfidence, formatDetectedAt } from "@/lib/format"
import {
  CLASS_META,
  FIRE_ALARM_GUIDELINES,
  isPhotoExpired,
  isWithinWindow,
  KAKAO_FAILURE_REASONS,
  SKIP_REASON_LABEL,
} from "@/lib/notification-meta"
import { cn } from "@/lib/utils"
import type { NotificationItem } from "@/types/notification"
import { NotificationImage } from "./NotificationImage"
import { NotificationStatusBadge } from "./NotificationStatusBadge"
import { NotificationSTT } from "./NotificationSTT"
import { NotificationTof } from "./NotificationTof"

export function NotificationCard({
  notification,
  isNew = false,
}: {
  notification: NotificationItem
  // 새 알림 표식(lib/unread.ts) — 글자 + 점. 색 단독 의존 금지 · 모션 0 · 자동 사라짐 타이머 0.
  isNew?: boolean
}) {
  const { reduceMotion } = useSettings()
  const meta = CLASS_META[notification.predicted_class]
  const Icon = meta.icon
  const isFire = notification.predicted_class === "fire_alarm"
  // 화재 카드만 지금 시각을 들고 있다가 창이 지나면 다시 그려 모션을 멈춘다(30초 해상도 — 판정은 원값).
  const [nowMs, setNowMs] = useState(() => Date.now())
  useEffect(() => {
    if (!isFire) return
    const id = setInterval(() => setNowMs(Date.now()), 30_000)
    return () => clearInterval(id)
  }, [isFire])
  // 움직임 줄이기 설정이 먼저, 그다음 감지 후 최근 창(FIRE_MOTION_WINDOW_MS). 창 밖은 정적 빨강 테두리.
  const animate =
    isFire &&
    !reduceMotion &&
    isWithinWindow(notification.detected_at, nowMs, FIRE_MOTION_WINDOW_MS)
  // 기술 정보(모델 신뢰도) — 기본 접힘. 카드마다 따로, 화면을 나가면 다시 접힌다.
  const [detailsOpen, setDetailsOpen] = useState(false)
  const status = notification.notification_status
  const detectedLabel = formatDetectedAt(notification.detected_at)
  // 사진 확대 화면 아래 맥락 줄 — 소리 종류 · 감지 시각, 자막이 있으면 다음 줄에 자막
  const photoCaption = [
    `${meta.label} · ${detectedLabel}`,
    notification.stt ? `“${notification.stt.transcript}”` : null,
  ]
    .filter(Boolean)
    .join("\n")
  // 사진 보관 기간이 지났는가 — 위 nowMs(카드가 처음 그려진 시각 · 화재 카드만 30초마다 갱신)로 판정, 새 타이머 0.
  // 한계: 열어 둔 화면에서 경계를 넘은 카드는 다시 그려질 때(화면 이동 · 새로고침) 반영된다 — 그 사이엔 기존 동작.
  // 넘는 순간 key 가 바뀌어 사진 칸이 다시 마운트되므로 진행 중이던 재시도 타이머도 함께 정리된다.
  const photoExpired = isPhotoExpired(notification.detected_at, nowMs)

  return (
    <article
      className={cn(
        "rounded-2xl bg-background p-4 shadow-sm",
        isFire ? "border-2 border-danger" : "border border-border",
        animate && "animate-pulse-border",
      )}
    >
      <div className="flex gap-4">
        {/* 좌측 64px 원형 아이콘 (카카오톡 알림 패턴) */}
        <span
          className={cn(
            "flex h-16 w-16 shrink-0 items-center justify-center rounded-full",
            meta.bgColor,
            animate && "animate-shake",
          )}
        >
          <Icon className={cn("h-8 w-8", meta.iconColor)} aria-hidden />
        </span>

        {/* 중앙 본문 */}
        <div className="min-w-0 flex-1">
          <div className="flex items-start gap-2">
            <div className="min-w-0">
              {isNew && (
                <p className="flex items-center gap-1.5 text-caption font-bold text-primary">
                  <span className="h-2 w-2 shrink-0 rounded-full bg-primary" aria-hidden />
                  새 알림
                </p>
              )}
              <h3 className={cn("text-(length:--text-h3) font-bold", isFire && "text-danger-deep")}>
                {meta.label}
              </h3>
            </div>
            <div className="ml-auto flex flex-col items-end gap-1">
              <time
                className="text-caption text-foreground-secondary tabular-nums"
                dateTime={notification.detected_at}
              >
                {detectedLabel}
              </time>
              <NotificationStatusBadge status={status} />
            </div>
          </div>

          {/* 발송 제외 사유 — 카카오 발송 실패는 원인을 말하지 않고 경고 톤으로 따로 알린다 */}
          {!status.primary_sent &&
            status.skip_reason &&
            (KAKAO_FAILURE_REASONS.has(status.skip_reason) ? (
              <p className="mt-2 flex items-center gap-1.5 text-caption font-medium text-danger-deep">
                <TriangleAlert className="h-4 w-4 shrink-0" aria-hidden />
                카카오톡으로 보내지 못했어요.
              </p>
            ) : (
              <p className="mt-2 text-caption text-foreground-secondary">
                {SKIP_REASON_LABEL[status.skip_reason] ?? "발송 제외"} 때문에 알림을
                보내지 않았어요.
              </p>
            ))}

          {/* 캡처 이미지 — 본문 순서 = 사진 → 자막 → 거리 센서. 카톡 2차처럼 「누가 왔는지」가 먼저다. */}
          {notification.media.image_url && (
            <div className="mt-3">
              <NotificationImage
                key={photoExpired ? "expired" : notification.media.image_url}
                src={notification.media.image_url}
                alt={`${meta.label} 감지 사진`}
                caption={photoCaption}
                expired={photoExpired}
              />
            </div>
          )}

          {/* STT 자막 */}
          {notification.stt && (
            <div className="mt-3">
              <NotificationSTT stt={notification.stt} />
            </div>
          )}

          {/* 사진은 왔는데 자막이 없을 때 — 2차가 끝났다는 표시(카톡 사진 카드 「알아들은 말 없음」과 짝).
              서버가 STT 실패와 빈 결과를 둘 다 null로 접어(7.6(e)) 「말이 없었다」로 단정하지 않는다.
              문구 = 후보 수용(확정 카피 아님), 사용자 결정 2026-10-26. 사진 URL은 2차 처리 끝에 저장된다
              → 처리 중엔 뜨지 않는다. */}
          {notification.media.image_url && !notification.stt && (
            <div className="mt-3 rounded-xl bg-background-sub p-3">
              <p className="flex items-center gap-1.5 text-body">
                <MessageSquareOff className="h-4 w-4 shrink-0 text-foreground-secondary" aria-hidden />
                알아들은 말이 없어요
              </p>
              <p className="mt-1 text-caption text-foreground-secondary">
                방문자가 말하지 않았거나, 소리가 작아 알아듣지 못했을 수 있어요.
              </p>
            </div>
          )}

          {/* 거리 센서(ToF) 검증 결과 — 통과/거부/미적용 3상태를 항상 표시한다.
              숨기면 "ToF 부재"가 "통과"와 같아 보인다(6.4(c) 불변식). */}
          <div className="mt-3">
            <NotificationTof tof={notification.tof_check} />
          </div>

          {/* 화재경보 정부 지정 대응 수칙 4단계 — FIRE_ALARM_GUIDELINES(decisions.md 7.1 확정 카피 ①) */}
          {isFire && (
            <div className="mt-3 rounded-xl bg-danger/10 p-3">
              <p className="mb-2 flex items-center gap-1.5 text-body font-bold text-danger-deep">
                <TriangleAlert className="h-4 w-4" aria-hidden />
                화재 시 대응 수칙
              </p>
              <ol className="space-y-1.5">
                {FIRE_ALARM_GUIDELINES.map((step, i) => (
                  <li key={step.text} className="flex gap-2 text-body">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-danger-deep text-caption font-bold text-background">
                      {i + 1}
                    </span>
                    <div className="space-y-0.5">
                      <span>{step.text}</span>
                      {step.subLines?.map((sub) => (
                        <p
                          key={sub}
                          className="text-caption text-foreground-secondary"
                        >
                          → {sub}
                        </p>
                      ))}
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* 기술 정보 접기(감사 UX-D08) — 펼치면 신뢰도. 거리 센서 칸은 위에 늘 보인다: 3상태 라벨이
              상시 표시 불변식(6.4(c))이고 부스 리셋 뒤 초기화 확인(33.33(b))에 쓴다. */}
          <div className="mt-1">
            <button
              type="button"
              aria-expanded={detailsOpen}
              onClick={() => setDetailsOpen((v) => !v)}
              className="flex h-touch items-center gap-1 text-caption font-medium text-foreground-secondary hover:text-foreground"
            >
              {detailsOpen ? "접기" : "자세히"}
              <ChevronDown className={cn("h-4 w-4", detailsOpen && "rotate-180")} aria-hidden />
            </button>
            {detailsOpen && (
              <p className="text-caption text-foreground-secondary tabular-nums">
                신뢰도 {formatConfidence(notification.confidence)}
              </p>
            )}
          </div>
        </div>
      </div>
    </article>
  )
}
