import { TriangleAlert } from "lucide-react"
import { Button } from "@/components/ui/button"
import { EXPIRED_LABEL } from "@/components/notifications/NotificationImage"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useOnboarding } from "@/contexts/OnboardingContext"
import { CAPTURE_TTL_HOURS } from "@/lib/constants"
import {
  CLASS_META,
  FIRE_ALARM_GUIDELINES,
  FIRE_ALARM_SOURCE,
  PREDICTED_CLASS_ORDER,
} from "@/lib/notification-meta"
import { cn } from "@/lib/utils"

const CLASS_DESCRIPTION: Record<string, string> = {
  doorbell: "문 앞에 사람이 있을 때 초인종이 울리면 알려드려요.",
  knock: "문 앞에 사람이 있을 때 현관문을 두드리는 노크 소리가 나면 알려드려요.",
  fire_alarm: "화재경보음을 감지하면 가장 먼저, 가장 크게 알려요.",
}

// 사진 보관 일 수 — 만료 문구(NotificationImage.tsx EXPIRED_LABEL)와 같은 식
const TTL_DAYS = CAPTURE_TTL_HOURS / 24

// FAQ 문구 = 후보(확정 카피 아님)
const FAQS = [
  {
    q: "알림은 얼마나 빨리 오나요?",
    a: "알림이 갈 때는 보통 5초 이내에 1차 알림이, 15초 이내에 사진·자막이 담긴 2차 알림이 도착해요.",
  },
  {
    q: "사진과 음성은 어떻게 보이나요?",
    // ‘알아들은 말이 없어요’ = NotificationCard.tsx 자막 없음 문구와 같은 글자(ssr-nc 가 대조한다).
    // 상수로 공유하지 않는 이유 = 카드 쪽 그 줄이 ssr-nc NC-K2 앵커다.
    a: "2차 알림이 갈 때는 현관 카메라가 찍은 사진과, 방문자가 한 말을 글자로 바꾼 자막이 알림 카드에 함께 표시돼요. 알아들은 말이 없으면 ‘알아들은 말이 없어요’라고 표시돼요.",
  },
  {
    q: "사진은 언제까지 볼 수 있나요?",
    a: `사진은 ${TTL_DAYS}일 동안 볼 수 있어요. ${TTL_DAYS}일이 지나면 ‘${EXPIRED_LABEL}’로 바뀌어요. 카카오톡 사진도 ${TTL_DAYS}일이 지나면 보이지 않을 수 있어요.`,
  },
  {
    q: "카카오톡 알림은 어디로 오나요?",
    a: "카카오톡 ‘나와의 채팅’ 방으로 와요. 휴대폰 잠금 화면에는 알림이 뜨지 않을 수 있어서, 그 방을 열어 두거나 이 화면을 함께 확인해 주세요.",
  },
  {
    q: "소리가 났는데 알림이 안 왔어요.",
    a: "확실하지 않은 소리, 현관 앞에 사람이 없어 보인 초인종·노크 소리, 등록한 초인종과 많이 다른 소리, 알림 대상이 아닌 기타 소리는 보내지 않아요. 알림 화면에서 보내지 않은 기록과 이유를 볼 수 있고, 통계 화면의 ‘오늘 보내지 않은 이유’에서 하루 합계를 볼 수 있어요.",
  },
  {
    q: "화면이 잘 안 보여요.",
    a: "설정 화면에서 ‘글씨 크게’와 ‘어두운 화면’을 켜면 더 편하게 볼 수 있어요.",
  },
]

export function HelpPage() {
  const { openOnboarding } = useOnboarding()

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-h1 font-bold">도움말</h1>
        <p className="mt-1 text-body text-foreground-secondary">
          띵동 대시보드 사용법을 안내해 드려요.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="text-h3">감지하는 소리 3가지</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {PREDICTED_CLASS_ORDER.map((cls) => {
            const meta = CLASS_META[cls]
            const Icon = meta.icon
            return (
              <div key={cls} className="flex items-start gap-3">
                <span
                  className={cn(
                    "flex h-10 w-10 shrink-0 items-center justify-center rounded-full",
                    meta.bgColor,
                  )}
                >
                  <Icon className={cn("h-5 w-5", meta.iconColor)} aria-hidden />
                </span>
                <div>
                  <p className="text-body font-semibold">{meta.label}</p>
                  <p className="text-body text-foreground-secondary">
                    {CLASS_DESCRIPTION[cls]}
                  </p>
                </div>
              </div>
            )
          })}
        </CardContent>
      </Card>

      <Card className="border-danger/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-h3 text-danger-deep">
            <TriangleAlert className="h-5 w-5" aria-hidden />
            화재경보가 울리면
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <ol className="space-y-3">
            {FIRE_ALARM_GUIDELINES.map((step, i) => (
              <li key={step.text} className="flex gap-2 text-body">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-danger-deep text-caption font-bold text-background">
                  {i + 1}
                </span>
                <div className="space-y-1">
                  <p>{step.text}</p>
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
          <p className="text-caption text-foreground-secondary">
            ⓘ {FIRE_ALARM_SOURCE}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-h3">자주 묻는 질문</CardTitle>
        </CardHeader>
        <CardContent className="divide-y divide-border">
          {FAQS.map((faq) => (
            <div key={faq.q} className="py-3 first:pt-0 last:pb-0">
              <p className="text-body font-semibold">{faq.q}</p>
              <p className="mt-1 text-body text-foreground-secondary">{faq.a}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <div className="flex justify-center">
        <Button
          variant="outline"
          className="h-btn px-6"
          onClick={openOnboarding}
        >
          사용법 처음부터 보기
        </Button>
      </div>
    </div>
  )
}
