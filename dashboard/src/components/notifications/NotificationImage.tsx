import { useState } from "react"
import { ImageOff } from "lucide-react"

interface NotificationImageProps {
  src: string
  alt: string
}

export function NotificationImage({ src, alt }: NotificationImageProps) {
  // Phase 1 mock 경로(/static/...)는 서버가 없어 404 → fallback 노출 (의도된 동작)
  const [errored, setErrored] = useState(false)

  if (errored) {
    return (
      <div className="flex h-40 w-full flex-col items-center justify-center gap-1 rounded-xl bg-background-sub text-foreground-secondary">
        <ImageOff className="h-6 w-6" aria-hidden />
        <span className="text-caption">사진을 불러올 수 없어요</span>
      </div>
    )
  }

  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      onError={() => setErrored(true)}
      className="h-40 w-full rounded-xl object-cover"
    />
  )
}
