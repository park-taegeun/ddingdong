import { useState } from "react"
import { Bell, Flame, ShieldCheck } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { useOnboarding } from "@/contexts/OnboardingContext"
import { CLASS_META, PREDICTED_CLASS_ORDER } from "@/lib/notification-meta"
import { cn } from "@/lib/utils"

interface Step {
  icon: LucideIcon
  iconClass: string
  title: string
  description: string
  showClasses?: boolean
}

const STEPS: Step[] = [
  {
    icon: Bell,
    iconClass: "bg-primary/10 text-primary",
    title: "띵동에 오신 것을 환영합니다",
    description:
      "현관에서 나는 소리를 자동으로 감지해, 휴대폰과 이 화면으로 알려드려요.",
  },
  {
    icon: ShieldCheck,
    iconClass: "bg-success/10 text-success",
    title: "세 가지 소리를 구분해요",
    description: "초인종, 노크, 화재경보를 구분해 표시합니다.",
    showClasses: true,
  },
  {
    icon: Flame,
    iconClass: "bg-danger/10 text-danger",
    title: "화재경보는 더 크게 알려요",
    description: "화재경보는 빨간색으로 강조하고, 대응 수칙을 함께 보여드려요.",
  },
]

export function OnboardingModal() {
  const { open, closeOnboarding } = useOnboarding()
  const [step, setStep] = useState(0)
  const current = STEPS[step]
  const isLast = step === STEPS.length - 1
  const Icon = current.icon

  const handleClose = () => {
    setStep(0)
    closeOnboarding()
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) handleClose()
      }}
    >
      <DialogContent>
        <DialogHeader>
          <span
            className={cn(
              "mx-auto mb-2 flex h-16 w-16 items-center justify-center rounded-full sm:mx-0",
              current.iconClass,
            )}
          >
            <Icon className="h-8 w-8" aria-hidden />
          </span>
          <DialogTitle className="text-h2">{current.title}</DialogTitle>
          <DialogDescription className="text-body text-foreground-secondary">
            {current.description}
          </DialogDescription>
        </DialogHeader>

        {current.showClasses && (
          <div className="grid grid-cols-3 gap-2">
            {PREDICTED_CLASS_ORDER.map((cls) => {
              const meta = CLASS_META[cls]
              const ClsIcon = meta.icon
              return (
                <div
                  key={cls}
                  className="flex flex-col items-center gap-1 rounded-xl bg-background-sub p-3"
                >
                  <span
                    className={cn(
                      "flex h-10 w-10 items-center justify-center rounded-full",
                      meta.bgColor,
                    )}
                  >
                    <ClsIcon className={cn("h-5 w-5", meta.iconColor)} aria-hidden />
                  </span>
                  <span className="text-caption font-medium">{meta.label}</span>
                </div>
              )
            })}
          </div>
        )}

        <div className="flex justify-center gap-1.5">
          {STEPS.map((s, i) => (
            <span
              key={s.title}
              className={cn(
                "h-2 rounded-full transition-all",
                i === step ? "w-6 bg-primary" : "w-2 bg-border",
              )}
              aria-hidden
            />
          ))}
        </div>

        <DialogFooter className="sm:justify-between">
          {step > 0 ? (
            <Button
              variant="outline"
              className="h-btn"
              onClick={() => setStep((s) => s - 1)}
            >
              이전
            </Button>
          ) : (
            <span className="hidden sm:block" />
          )}
          {isLast ? (
            <Button className="h-btn" onClick={handleClose}>
              시작하기
            </Button>
          ) : (
            <Button className="h-btn" onClick={() => setStep((s) => s + 1)}>
              다음
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
