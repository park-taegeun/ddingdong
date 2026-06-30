import { TriangleAlert } from "lucide-react"
import { useSettings } from "@/contexts/SettingsContext"
import { formatClock, formatConfidence } from "@/lib/format"
import {
  CLASS_META,
  FIRE_ALARM_GUIDELINES,
  SKIP_REASON_LABEL,
} from "@/lib/notification-meta"
import { cn } from "@/lib/utils"
import type { NotificationItem } from "@/types/notification"
import { NotificationImage } from "./NotificationImage"
import { NotificationStatusBadge } from "./NotificationStatusBadge"
import { NotificationSTT } from "./NotificationSTT"

export function NotificationCard({
  notification,
}: {
  notification: NotificationItem
}) {
  const { reduceMotion } = useSettings()
  const meta = CLASS_META[notification.predicted_class]
  const Icon = meta.icon
  const isFire = notification.predicted_class === "fire_alarm"
  const animate = isFire && !reduceMotion
  const status = notification.notification_status

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
              <h3 className={cn("text-h3 font-bold", isFire && "text-danger-deep")}>
                {meta.label}
              </h3>
              <p className="text-caption text-foreground-secondary tabular-nums">
                신뢰도 {formatConfidence(notification.confidence)}
              </p>
            </div>
            <div className="ml-auto flex flex-col items-end gap-1">
              <time
                className="text-caption text-foreground-secondary tabular-nums"
                dateTime={notification.detected_at}
              >
                {formatClock(notification.detected_at)}
              </time>
              <NotificationStatusBadge status={status} />
            </div>
          </div>

          {/* 발송 제외 사유 */}
          {!status.primary_sent && status.skip_reason && (
            <p className="mt-2 text-caption text-foreground-secondary">
              {SKIP_REASON_LABEL[status.skip_reason] ?? "발송 제외"} 때문에 알림을
              보내지 않았어요.
            </p>
          )}

          {/* STT 자막 */}
          {notification.stt && (
            <div className="mt-3">
              <NotificationSTT stt={notification.stt} />
            </div>
          )}

          {/* 캡처 이미지 */}
          {notification.media.image_url && (
            <div className="mt-3">
              <NotificationImage
                src={notification.media.image_url}
                alt={`${meta.label} 감지 사진`}
              />
            </div>
          )}

          {/* 화재경보 정부 지정 대응 수칙 3종 */}
          {isFire && (
            <div className="mt-3 rounded-xl bg-danger/10 p-3">
              <p className="mb-2 flex items-center gap-1.5 text-body font-bold text-danger-deep">
                <TriangleAlert className="h-4 w-4" aria-hidden />
                화재 시 대응 수칙
              </p>
              <ol className="space-y-1.5">
                {FIRE_ALARM_GUIDELINES.map((step, i) => (
                  <li key={step.text} className="flex gap-2 text-body">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-danger text-caption font-bold text-white">
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
        </div>
      </div>
    </article>
  )
}
