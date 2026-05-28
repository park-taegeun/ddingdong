import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"

export function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
      <p className="text-display font-bold text-primary">404</p>
      <div>
        <h1 className="text-h2 font-bold">페이지를 찾을 수 없어요</h1>
        <p className="mt-1 text-body text-foreground-secondary">
          주소가 바뀌었거나 삭제된 페이지예요.
        </p>
      </div>
      <Button asChild className="h-btn px-6">
        <Link to="/">홈으로 가기</Link>
      </Button>
    </div>
  )
}
