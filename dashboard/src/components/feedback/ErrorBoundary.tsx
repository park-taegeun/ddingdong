import { Component } from "react"
import type { ErrorInfo, ReactNode } from "react"
import { TriangleAlert } from "lucide-react"
import { Button } from "@/components/ui/button"

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("렌더링 오류:", error, info)
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background-sub p-6 text-center">
          <span className="flex h-16 w-16 items-center justify-center rounded-full bg-danger/10 text-danger">
            <TriangleAlert className="h-8 w-8" aria-hidden />
          </span>
          <div>
            <h1 className="text-h2 font-bold">문제가 발생했어요</h1>
            <p className="mt-1 text-body text-foreground-secondary">
              잠시 후 다시 시도해 주세요.
            </p>
          </div>
          <Button className="h-btn px-6" onClick={() => window.location.reload()}>
            새로고침
          </Button>
        </div>
      )
    }
    return this.props.children
  }
}
