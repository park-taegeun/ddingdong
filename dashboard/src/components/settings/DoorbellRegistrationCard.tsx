import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useRegistration } from "@/hooks/useRegistration"
import { formatClock } from "@/lib/format"
import { cn } from "@/lib/utils"
import type { RegistrationState, RegistrationStatus } from "@/types/registration"

// 화면 문구 — 잠정, 카피 PR에서 확정.
// 아직 없는 동작(등록한 소리만 골라 알리기 · 등록 중 알림 멈춤 등)을 약속하는 문구를 넣지 않는다.
const COPY = {
  title: "우리집 초인종",
  loading: "등록 상태를 불러오는 중이에요.",
  loadError: "등록 상태를 불러오지 못했어요. 잠시 후 다시 시도합니다.",
  staleError: "최근 상태를 불러오지 못해 마지막으로 받은 상태를 보여 드려요.",
  actionError: "요청을 처리하지 못했어요.",
  none: "등록된 초인종 소리가 없어요.",
  collecting: (target: number | null) => `초인종을 ${target}번 눌러 주세요.`,
  expired: "시간이 지나 등록을 마치지 못했어요.",
  registered: "초인종 소리가 등록되어 있어요.",
  progress: (collected: number, target: number | null) => `${collected}/${target}`,
  until: (iso: string | null) => `${formatClock(iso ?? "")}까지`,
  registeredAt: (iso: string | null) => `${formatClock(iso ?? "")} 등록`,
  confirmClear: "등록을 해제할까요?",
  start: "등록 시작",
  restart: "다시 시작",
  cancel: "취소",
  clear: "해제",
}

// 상태 라벨은 색과 함께 글자로도 보인다. 색은 기존 상태 토큰만 쓴다.
const STATE_INFO: Record<RegistrationState, { label: string; color: string }> = {
  none: { label: "등록 안 됨", color: "bg-status-offline" },
  collecting: { label: "등록 중", color: "bg-status-processing" },
  expired: { label: "시간 초과", color: "bg-status-failed" },
  registered: { label: "등록됨", color: "bg-status-online" },
}

export interface DoorbellRegistrationViewProps {
  status: RegistrationStatus | null
  isLoading: boolean
  loadError: Error | null
  isSubmitting: boolean
  actionError: Error | null
  confirming: boolean
  onStart: () => void
  onClear: () => void
  onConfirmingChange: (value: boolean) => void
}

// 표시 전용 — 서버 · 시계를 부르지 않는다. 상태는 서버가 준 state 값만 따른다.
export function DoorbellRegistrationView({
  status,
  isLoading,
  loadError,
  isSubmitting,
  actionError,
  confirming,
  onStart,
  onClear,
  onConfirmingChange,
}: DoorbellRegistrationViewProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-h3">{COPY.title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {status ? (
          <StatusBody
            status={status}
            isSubmitting={isSubmitting}
            confirming={confirming}
            onStart={onStart}
            onClear={onClear}
            onConfirmingChange={onConfirmingChange}
          />
        ) : (
          <p aria-live="polite" className="text-body text-foreground-secondary">
            {isLoading && !loadError ? COPY.loading : COPY.loadError}
          </p>
        )}
        {status && loadError && (
          <p className="text-caption text-foreground-secondary">{COPY.staleError}</p>
        )}
        {actionError && (
          <div role="alert" className="text-body text-danger">
            <p>{COPY.actionError}</p>
            <p className="text-caption">{actionError.message}</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

interface StatusBodyProps {
  status: RegistrationStatus
  isSubmitting: boolean
  confirming: boolean
  onStart: () => void
  onClear: () => void
  onConfirmingChange: (value: boolean) => void
}

function StatusBody({
  status,
  isSubmitting,
  confirming,
  onStart,
  onClear,
  onConfirmingChange,
}: StatusBodyProps) {
  const info = STATE_INFO[status.state]
  let message: string
  let details: string[] = []
  let action: { label: string; onClick: () => void }

  switch (status.state) {
    case "none":
      message = COPY.none
      action = { label: COPY.start, onClick: onStart }
      break
    case "collecting":
      message = COPY.collecting(status.target)
      details = [COPY.progress(status.collected, status.target), COPY.until(status.expires_at)]
      action = { label: COPY.cancel, onClick: onClear }
      break
    case "expired":
      message = COPY.expired
      details = [COPY.progress(status.collected, status.target)]
      action = { label: COPY.restart, onClick: onStart }
      break
    case "registered":
      message = COPY.registered
      details = [COPY.registeredAt(status.registered_at)]
      action = { label: COPY.clear, onClick: () => onConfirmingChange(true) }
      break
  }

  const askingClear = status.state === "registered" && confirming

  return (
    <>
      <div className="flex items-center justify-between gap-4">
        <div aria-live="polite">
          <p className="flex items-center gap-2 text-body font-medium">
            <span className={cn("h-2.5 w-2.5 rounded-full", info.color)} aria-hidden />
            <span>{info.label}</span>
          </p>
          <p className="text-body text-foreground-secondary">{message}</p>
          {details.map((d) => (
            <p key={d} className="text-caption text-foreground-secondary tabular-nums">
              {d}
            </p>
          ))}
        </div>
        {!askingClear && (
          <Button
            variant="outline"
            className="h-btn shrink-0"
            disabled={isSubmitting}
            onClick={action.onClick}
          >
            {action.label}
          </Button>
        )}
      </div>
      {askingClear && (
        <div className="flex items-center justify-between gap-4">
          <p className="text-body font-medium">{COPY.confirmClear}</p>
          <div className="flex shrink-0 gap-2">
            <Button
              variant="destructive"
              className="h-btn"
              disabled={isSubmitting}
              onClick={onClear}
            >
              {COPY.clear}
            </Button>
            <Button
              variant="outline"
              className="h-btn"
              disabled={isSubmitting}
              onClick={() => onConfirmingChange(false)}
            >
              {COPY.cancel}
            </Button>
          </div>
        </div>
      )}
    </>
  )
}

// 컨테이너 — 훅을 연결하고 해제 확인 단계만 들고 있는다.
export function DoorbellRegistrationCard() {
  const { status, isLoading, loadError, isSubmitting, actionError, start, clear } =
    useRegistration()
  const [confirming, setConfirming] = useState(false)

  return (
    <DoorbellRegistrationView
      status={status}
      isLoading={isLoading}
      loadError={loadError}
      isSubmitting={isSubmitting}
      actionError={actionError}
      confirming={confirming}
      onStart={() => void start()}
      onClear={() => {
        setConfirming(false)
        void clear()
      }}
      onConfirmingChange={setConfirming}
    />
  )
}
