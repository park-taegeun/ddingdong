import type { Ref } from "react"
import { Check, ListFilter } from "lucide-react"
import { EmptyState } from "@/components/feedback/EmptyState"
import { Button } from "@/components/ui/button"
import { CLASS_META, STATS_CLASS_ORDER } from "@/lib/notification-meta"
import type { ClassFilter } from "@/lib/notification-filter"
import { cn } from "@/lib/utils"

const CLASS_CHIPS: { value: ClassFilter; label: string }[] = [
  { value: "all", label: "전체" },
  ...STATS_CLASS_ORDER.map((c) => ({ value: c, label: CLASS_META[c].label })),
]

interface NotificationFilterBarProps {
  cls: ClassFilter
  sentOnly: boolean
  onClsChange: (cls: ClassFilter) => void
  onSentOnlyChange: (sentOnly: boolean) => void
  // 「필터 해제」 뒤 포커스를 둘 곳(「전체」 칩) — 해제 버튼이 사라져 포커스가 빠지지 않게.
  allChipRef?: Ref<HTMLButtonElement>
}

// 알림 화면 종류 필터 칩(하나 선택) + 「보낸 알림만」 토글. 칩 = 버튼 · aria-pressed.
// 눌림 = 체크 아이콘 + 테두리 색 + 라벨(색 단독 의존 금지).
export function NotificationFilterBar({
  cls,
  sentOnly,
  onClsChange,
  onSentOnlyChange,
  allChipRef,
}: NotificationFilterBarProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <div role="group" aria-label="알림 종류" className="flex flex-wrap gap-2">
        {CLASS_CHIPS.map((chip) => (
          <Chip
            key={chip.value}
            ref={chip.value === "all" ? allChipRef : undefined}
            label={chip.label}
            pressed={cls === chip.value}
            onClick={() => onClsChange(chip.value)}
          />
        ))}
      </div>
      <Chip label="보낸 알림만" pressed={sentOnly} onClick={() => onSentOnlyChange(!sentOnly)} />
    </div>
  )
}

function Chip({
  label,
  pressed,
  onClick,
  ref,
}: {
  label: string
  pressed: boolean
  onClick: () => void
  ref?: Ref<HTMLButtonElement>
}) {
  return (
    <button
      ref={ref}
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={cn(
        "flex h-touch items-center gap-1.5 rounded-full border px-4 text-body font-medium outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50",
        pressed
          ? "border-2 border-primary bg-primary/10 text-foreground"
          : "border-border bg-background text-foreground-secondary hover:bg-background-sub",
      )}
    >
      {pressed && <Check className="h-4 w-4 shrink-0" aria-hidden />}
      {label}
    </button>
  )
}

// 불러온 알림은 있는데 거른 결과가 0건일 때의 빈 상태 — 범위(불러온 알림)를 말하고 해제 버튼을 둔다.
export function FilterEmpty({ onClear }: { onClear: () => void }) {
  return (
    <EmptyState
      icon={ListFilter}
      title="불러온 알림 중에는 맞는 알림이 없어요"
      description="필터를 해제하면 불러온 알림을 모두 볼 수 있어요."
      action={
        <Button variant="outline" className="h-btn text-body" onClick={onClear}>
          필터 해제
        </Button>
      }
    />
  )
}
