import { useEffect, useState } from "react"
import { ImageOff, Maximize2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { IMAGE_RETRY_INTERVAL_MS, IMAGE_RETRY_MAX } from "@/lib/constants"
import { nextRetryDelay, retryUrl } from "@/lib/image-retry"
import { ImageLightbox } from "./ImageLightbox"

interface NotificationImageProps {
  src: string
  alt: string
  /** 확대 화면 아래 한 줄(소리 종류 · 감지 시각 · 자막) — 라이트박스로 그대로 넘긴다 */
  caption?: string
}

export function NotificationImage({ src, alt, caption }: NotificationImageProps) {
  // url = 지금 보여 줄 사진 주소(첫 요청은 원본 그대로), null = 실패 표시 중.
  // 실패하면 상수 간격 · 상한만큼 화면 밖(배경 Image)에서 다시 받아 보고, 성공했을 때만 사진으로 바꾼다 —
  // 재시도마다 실패 표시 ↔ 빈 사진 상자가 깜빡이지 않게. 상한을 다 쓰면 실패 표시가 남는다
  // (mock 경로(/static/...)는 서버가 없어 404 → 상한 재시도 뒤 실패 표시 = 의도된 동작).
  // src가 바뀌면 카드 쪽 key로 다시 마운트돼 처음부터 센다.
  const [state, setState] = useState<{ failures: number; url: string | null }>({
    failures: 0,
    url: src,
  })
  const markFailed = () => setState((s) => ({ failures: s.failures + 1, url: null }))

  useEffect(() => {
    if (state.url !== null) return
    const delay = nextRetryDelay(state.failures, IMAGE_RETRY_MAX, IMAGE_RETRY_INTERVAL_MS)
    if (delay === null) return
    const url = retryUrl(src, state.failures)
    const probe = new Image()
    const timer = setTimeout(() => {
      probe.onload = () => setState((s) => ({ failures: s.failures, url }))
      probe.onerror = markFailed
      probe.src = url
    }, delay)
    // 언마운트 · 재실행 때: 대기 타이머 해제 + 진행 중 요청의 콜백 무력화(setState 0 · 새 요청 0).
    return () => {
      clearTimeout(timer)
      probe.onload = null
      probe.onerror = null
    }
  }, [src, state])

  if (state.url === null) {
    return (
      <div className="flex h-40 w-full flex-col items-center justify-center gap-1 rounded-xl bg-background-sub text-foreground-secondary">
        <ImageOff className="h-6 w-6" aria-hidden />
        <span className="text-caption">사진을 불러올 수 없어요</span>
      </div>
    )
  }

  return (
    <ImageLightbox src={state.url} alt={alt} caption={caption}>
      {/* relative 래퍼: 확대 힌트 뱃지를 사진 우측 상단에 오버레이.
          뱃지는 트리거 button 안에 있어 클릭 히트영역은 사진 전체 그대로 유지된다. */}
      <div className="relative">
        <img
          src={state.url}
          alt={alt}
          loading="lazy"
          onError={markFailed}
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
