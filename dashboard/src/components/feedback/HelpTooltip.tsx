import { CircleHelp } from "lucide-react"
import type { ReactNode } from "react"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

interface HelpTooltipProps {
  children: ReactNode
  label?: string
}

export function HelpTooltip({ children, label = "도움말" }: HelpTooltipProps) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        {/* 누르는 영역 = 터치 토큰(44px), 음수 여백으로 주변 배치는 예전 24px 자리 그대로 · 아이콘 크기 유지 */}
        <button
          type="button"
          aria-label={label}
          className="-m-2.5 inline-flex h-touch w-touch items-center justify-center rounded-full text-foreground-secondary transition-colors hover:bg-background-sub hover:text-foreground"
        >
          <CircleHelp className="h-4 w-4" aria-hidden />
        </button>
      </PopoverTrigger>
      <PopoverContent className="text-body leading-relaxed">
        {children}
      </PopoverContent>
    </Popover>
  )
}
