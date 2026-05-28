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
        <button
          type="button"
          aria-label={label}
          className="inline-flex h-6 w-6 items-center justify-center rounded-full text-foreground-secondary transition-colors hover:bg-background-sub hover:text-foreground"
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
