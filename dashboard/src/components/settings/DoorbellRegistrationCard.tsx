import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useRegistration } from "@/hooks/useRegistration"
import { STALE_NOTICE } from "@/lib/connection"
import { formatClock } from "@/lib/format"
import { cn } from "@/lib/utils"
import type { RegistrationState, RegistrationStatus } from "@/types/registration"

// 화면 문구 — 잠정, 카피 PR에서 확정.
// 아직 없는 동작(등록한 소리만 골라 알리기 · 등록 중 알림 멈춤 등)을 약속하는 문구를 넣지 않는다.
// [현재값 2026-10-26 — PR #100으로 두 동작이 생겨 안내를 넣는다 · 후보 수용 · 근거 = decisions.md 33.30(c) · 33.19(c)]
// 판정 대상은 초인종으로 들은 소리뿐이다 — 「우리 집 벨만」류 표현 금지(같은 제품 옆집 벨은 소리로 못 가른다).
const COPY = {
  title: "우리집 초인종",
  loading: "등록 상태를 불러오는 중이에요.",
  loadError: "등록 상태를 불러오지 못했어요. 잠시 후 다시 시도합니다.",
  staleError: STALE_NOTICE,
  actionError: "요청을 처리하지 못했어요. 잠시 후 다시 눌러 주세요.",
  none: "등록된 초인종 소리가 없어요.",
  collecting: (target: number | null) => `초인종을 ${target}번 눌러 주세요.`,
  collectingNote: "등록하는 동안에는 초인종 알림을 보내지 않아요.",
  expired: "시간이 지나 등록을 마치지 못했어요.",
  registered: "초인종 소리가 등록되어 있어요.",
  registeredNote:
    "등록한 소리와 많이 다른 초인종 소리는 알리지 않아요. 노크 · 화재경보는 그대로 알려요.",
  // 남은 횟수는 0 아래로 내려가지 않는다(서버가 target 보다 많이 세는 경우 방어).
  progress: (collected: number, target: number | null) =>
    target === null
      ? `${collected}번 확인`
      : `${collected}번 확인 · ${Math.max(target - collected, 0)}번 남음`,
  // 시간 초과 — 더 남은 게 아니라 멈춘 것이라 「남음」을 쓰지 않는다.
  expiredProgress: (collected: number, target: number | null) =>
    target === null ? `${collected}번 확인했어요` : `${target}번 중 ${collected}번 확인했어요`,
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
  let note: string | null = null
  let showProgress = false
  let details: string[] = []
  let action: { label: string; onClick: () => void }

  switch (status.state) {
    case "none":
      message = COPY.none
      action = { label: COPY.start, onClick: onStart }
      break
    case "collecting":
      message = COPY.collecting(status.target)
      note = COPY.collectingNote
      showProgress = true
      details = [COPY.until(status.expires_at)]
      action = { label: COPY.cancel, onClick: onClear }
      break
    case "expired":
      message = COPY.expired
      details = [COPY.expiredProgress(status.collected, status.target)]
      action = { label: COPY.restart, onClick: onStart }
      break
    case "registered":
      message = COPY.registered
      note = COPY.registeredNote
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
          {note && <p className="text-body text-foreground-secondary">{note}</p>}
          {showProgress && (
            <div className="mt-1 flex items-center gap-2">
              <ProgressDots collected={status.collected} target={status.target} color={info.color} />
              <p className="text-body font-medium tabular-nums">
                {COPY.progress(status.collected, status.target)}
              </p>
            </div>
          )}
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

// 진행 동그라미 — 장식이다. 개수는 옆 글자가 전달한다(색 단독 금지).
// target 이 서버 가드 범위(1 ~ 10) 정수일 때만 그리고, 채움은 target 개를 넘지 않는다.
function ProgressDots({
  collected,
  target,
  color,
}: {
  collected: number
  target: number | null
  color: string
}) {
  if (target === null || !Number.isInteger(target) || target < 1 || target > 10) return null
  return (
    <span className="flex gap-1" aria-hidden>
      {Array.from({ length: target }, (_, i) => (
        <span
          key={i}
          className={cn(
            "h-3 w-3 rounded-full border-2 border-foreground-secondary",
            i < collected && color,
          )}
        />
      ))}
    </span>
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
