import type { ReactNode } from "react"
import { X } from "lucide-react"
import { Dialog as DialogPrimitive } from "radix-ui"

import {
  Dialog,
  DialogClose,
  DialogOverlay,
  DialogPortal,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { useSettings } from "@/contexts/SettingsContext"
import { cn } from "@/lib/utils"

interface ImageLightboxProps {
  /** 확대해서 보여줄 원본 이미지 경로 */
  src: string
  /** 이미지 대체 텍스트 (감지 사진 설명) */
  alt: string
  /** 트리거로 감쌀 썸네일 (NotificationImage 의 <img>) */
  children: ReactNode
}

/**
 * 알림 사진 전체화면 라이트박스.
 * 5060 노안 사용자가 "누가 왔는지" 크게 확인할 수 있도록,
 * 썸네일을 탭/클릭/Enter/Space 하면 어두운 배경 + 중앙 확대 이미지로 띄운다.
 *
 * 접근성·포커스 트랩·ESC·배경 클릭 닫기·스크롤 잠금·포커스 복원은
 * 기존 대시보드가 이미 쓰는 radix Dialog(= OnboardingModal 과 동일 패턴)에 위임한다.
 * (학습 16 — 신규 포커스 트랩 발명 없이 기존 컨벤션 재사용)
 */
export function ImageLightbox({ src, alt, children }: ImageLightboxProps) {
  const { reduceMotion } = useSettings()

  // 화재 애니메이션 정책과 동일하게, 인앱 '동작 줄이기' 설정이면 페이드 분기 제거.
  // (OS 레벨 prefers-reduced-motion 은 index.css 전역 규칙이 별도로 감속 처리)
  const fade = reduceMotion
    ? ""
    : "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:animate-in data-[state=open]:fade-in-0"

  return (
    <Dialog>
      <DialogTrigger
        aria-label="사진 크게 보기"
        className="block w-full cursor-pointer rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      >
        {children}
      </DialogTrigger>

      <DialogPortal>
        <DialogOverlay className={cn("bg-black/90", fade)} />
        <DialogPrimitive.Content
          aria-modal="true"
          // 라이트박스는 제목(Title) 외 별도 설명이 없으므로 describedby 미연결
          // (radix 의 dangling aria-describedby 경고 방지)
          aria-describedby={undefined}
          className={cn(
            "fixed inset-0 z-50 flex items-center justify-center p-4 outline-none",
            fade,
          )}
        >
          {/* radix 는 접근성 이름을 위해 Title 을 요구 → 화면엔 숨기고 aria 로만 노출 */}
          <DialogTitle className="sr-only">방문자 사진 확대</DialogTitle>

          {/* object-contain: 잘림 없이 사진 전체가 보이도록 */}
          <img
            src={src}
            alt={alt}
            className="max-h-full max-w-full rounded-xl object-contain"
          />

          <DialogClose
            aria-label="사진 닫기"
            className="absolute right-4 top-4 flex h-touch w-touch items-center justify-center rounded-full bg-black/60 text-white transition-colors hover:bg-black/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-black"
          >
            <X className="h-6 w-6" aria-hidden />
          </DialogClose>
        </DialogPrimitive.Content>
      </DialogPortal>
    </Dialog>
  )
}
