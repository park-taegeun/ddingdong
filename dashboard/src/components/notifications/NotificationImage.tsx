import { useState } from "react"
import { ImageOff, Maximize2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { ImageLightbox } from "./ImageLightbox"

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
    <ImageLightbox src={src} alt={alt}>
      {/* relative 래퍼: 확대 힌트 뱃지를 사진 우측 상단에 오버레이.
          뱃지는 트리거 button 안에 있어 클릭 히트영역은 사진 전체 그대로 유지된다. */}
      <div className="relative">
        <img
          src={src}
          alt={alt}
          loading="lazy"
          onError={() => setErrored(true)}
          className="h-40 w-full rounded-xl object-cover"
        />
        {/* 어포던스 힌트: "클릭하면 커진다"를 5060 노안·터치 사용자에게 상시 노출.
            트리거 aria-label("사진 크게 보기")과 중복 낭독 방지 위해 aria-hidden.
            pointer-events-none 으로 클릭은 항상 트리거 button 이 받게 한다.
            bg-black/60 + 흰 텍스트(닫기 버튼과 동일 idiom) + WCAG 1.4.1 텍스트 병기. */}
        <Badge
          aria-hidden
          className="pointer-events-none absolute right-2 top-2 gap-1 border-transparent bg-black/60 px-2.5 py-1 text-caption text-white [&>svg]:size-4"
        >
          <Maximize2 aria-hidden />
          크게 보기
        </Badge>
      </div>
    </ImageLightbox>
  )
}
