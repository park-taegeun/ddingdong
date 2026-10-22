import { MessageCircleOff, ServerOff, WifiOff } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import type { BannerKind } from "@/lib/banner"
import { STALE_NOTICE } from "@/lib/connection"

// 문구는 원인을 단정하지 않는다(내부 어휘 금지). 아이콘은 헤더 연결 표시와 같은 모양(끊김 · 기기 꺼짐).
const CONTENT: Record<BannerKind, { Icon: LucideIcon; title: string; body: string }> = {
  server: { Icon: ServerOff, title: "서버와 연결이 끊겼어요", body: STALE_NOTICE },
  device: {
    Icon: WifiOff,
    title: "현관 기기가 응답하지 않아요",
    body: "전원과 네트워크를 확인해 주세요.",
  },
  kakao: {
    Icon: MessageCircleOff,
    title: "최근 알림을 카카오톡으로 보내지 못했어요",
    body: "다음 알림도 카카오톡으로 가지 않을 수 있어요. 이 화면에서 확인해 주세요.",
  },
}

// 모든 화면 상단 경고 띠 — 닫기 버튼 · 자동 사라짐 없음(상태가 풀리면 사라진다).
// live 영역 틀은 늘 두고 내용만 바꾼다 — 나타날 때 낭독이 확실하다. 문구가 신규 알림 안내와 겹치지 않는다.
// 라벨 + 아이콘 + 색 3중 표기. 색 = 화재 수칙 상자와 같은 위험 틴트 바탕 + 진한 위험색 제목.
export function StatusBanner({ kind }: { kind: BannerKind | null }) {
  const content = kind ? CONTENT[kind] : null
  return (
    <div role="status" aria-live="polite" aria-atomic="true">
      {content && (
        <div className="mb-4 flex items-start gap-3 rounded-xl bg-danger/10 p-4">
          <content.Icon className="mt-0.5 h-5 w-5 shrink-0 text-danger-deep" aria-hidden />
          <div className="min-w-0">
            <p className="text-body font-bold text-danger-deep">{content.title}</p>
            <p className="text-body text-foreground">{content.body}</p>
          </div>
        </div>
      )}
    </div>
  )
}
