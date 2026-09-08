import { CircleSlash, ScanLine, UserCheck, UserX } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import type { TofCheck } from "@/types/notification"

// ToF(거리 센서) 검증 결과 표시 — USP 2층 1차인 "ToF 융합으로 옆집 초인종을 거른다"의
// 화면 근거. 6.4 로 서버가 실 ToF 값을 내기 시작했는데 화면 참조가 0건이었다(8.3 미결).
//
// 🔴 불변식(6.4(c)의 화면 판): "게이트 통과"와 "ToF 부재로 미적용"이 구분돼야 한다.
//    미적용을 통과와 같은 자리에 비워 두면 부재가 통과로 위장된다. 그래서 세 상태를
//    각각 다른 라벨로 찍고, 어느 상태에서도 이 블록 자체를 숨기지 않는다.
// ★ 색 단독 의존 금지(8.3 B-1a / WCAG 1.4.1, 5060 노안·색각) — 라벨 텍스트 + 아이콘
//   + 색 3중 표기. 폰트는 기존 토큰(caption 15)만 쓰고 신설하지 않는다.
function derive(tof: TofCheck): {
  label: string
  className: string
  Icon: LucideIcon
} {
  if (!tof.applied) {
    // tof_absent(필드 부재) / tof_invalid(이탈) / fire_alarm_bypass(화재경보 우회) 공통.
    // 세 경우의 차이는 아래 reason 원문이 그대로 드러낸다.
    return {
      label: "검증 안 함",
      className: "text-foreground-secondary",
      Icon: CircleSlash,
    }
  }
  return tof.passed
    ? { label: "사람 확인", className: "text-success", Icon: UserCheck }
    : { label: "사람 없음", className: "text-danger-deep", Icon: UserX }
}

export function NotificationTof({ tof }: { tof: TofCheck }) {
  const { label, className, Icon } = derive(tof)
  return (
    <div className="rounded-xl bg-background-sub p-3">
      <div className="flex items-center gap-1.5 text-foreground-secondary">
        <ScanLine className="h-4 w-4" aria-hidden />
        <span className="text-caption font-medium">거리 센서</span>
        <span
          className={cn(
            "ml-auto flex items-center gap-1 text-caption font-bold",
            className,
          )}
        >
          <Icon className="h-4 w-4" aria-hidden />
          {label}
        </span>
      </div>
      {/* ★ reason 은 원문 그대로 — 가공·재해석 금지. 이 어휘(near=n/64 · center=NNNNmm
          · ndet=n/16)는 9.3(b) 펌웨어 시리얼 로그 표기와 맞춘 값이라, 통합 후
          서버 기록 ↔ 시리얼 로그 대조에 쓴다(6.4(b)). */}
      <p className="mt-1 break-all text-caption text-foreground-secondary">
        {tof.reason}
      </p>
    </div>
  )
}
