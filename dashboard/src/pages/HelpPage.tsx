import { TriangleAlert } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useOnboarding } from "@/contexts/OnboardingContext"
import {
  CLASS_META,
  FIRE_ALARM_GUIDELINES,
  FIRE_ALARM_SOURCE,
  PREDICTED_CLASS_ORDER,
} from "@/lib/notification-meta"
import { cn } from "@/lib/utils"

const CLASS_DESCRIPTION: Record<string, string> = {
  doorbell: "등록된 초인종 소리가 울리면 알려드려요.",
  knock: "현관문을 두드리는 노크 소리를 감지해요.",
  fire_alarm: "화재경보음을 감지하면 가장 먼저, 가장 크게 알려요.",
}

const FAQS = [
  {
    q: "알림은 얼마나 빨리 오나요?",
    a: "소리가 감지되면 보통 5초 이내에 1차 알림이, 15초 이내에 사진·자막이 담긴 2차 알림이 도착해요.",
  },
  {
    q: "사진과 음성은 어떻게 보이나요?",
    a: "현관 카메라가 찍은 사진과, 방문자가 한 말을 글자로 바꾼 자막이 알림 카드에 함께 표시돼요.",
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
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-danger text-caption font-bold text-white">
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
