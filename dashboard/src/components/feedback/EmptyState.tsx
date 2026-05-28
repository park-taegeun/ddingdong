import { Inbox } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
  tone?: "default" | "error"
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  tone = "default",
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-background px-6 py-12 text-center">
      <span
        className={cn(
          "mb-4 flex h-14 w-14 items-center justify-center rounded-full",
          tone === "error"
            ? "bg-danger/10 text-danger"
            : "bg-background-sub text-foreground-secondary",
        )}
      >
        <Icon className="h-7 w-7" aria-hidden />
      </span>
      <p className="text-h3 font-semibold">{title}</p>
      {description && (
        <p className="mt-1 max-w-sm text-body text-foreground-secondary">
          {description}
        </p>
      )}
    </div>
  )
}
