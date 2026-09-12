// 랜딩(`/`) — 부스 관람객이 대시보드보다 먼저 보는 화면.
// 대시보드 테마 토큰과 분리된 잉크 팔레트(index.css `--ink*` / `--signal*`)를 쓴다.
// 문구 원칙: 제품에 없는 기능(초인종 등록/해제)은 쓰지 않는다. 성능 수치 인용 없음.

import { useEffect } from "react"
import { BellRing, MessageSquareText, ScanEye } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { Link } from "react-router-dom"
import { useReducedMotion } from "@/hooks/useReducedMotion"
import { cn } from "@/lib/utils"

interface Step {
  icon: LucideIcon
  accent: string
  title: string
  body: string
}

// 파이프라인 실제 순서(decisions.md 카테고리 26.3 진입점 1·3 / 33.5 「USP 2층 재정립」).
const STEPS: Step[] = [
  {
    icon: ScanEye,
    accent: "text-signal",
    title: "문 앞에 사람이 있는지 먼저 확인합니다",
    body: "소리가 나면 거리 센서로 현관 앞을 살핍니다. 벽 너머로 새어 들어온 옆집 초인종 소리와 우리 집 방문을 갈라내기 위한 단계입니다.",
  },
  {
    icon: BellRing,
    accent: "text-signal-amber",
    title: "무슨 소리였는지 먼저 알립니다",
    body: "초인종·노크·화재경보를 구분해 짧은 알림을 보냅니다. 화재경보는 사람 확인을 건너뛰고 바로, 대피 수칙과 함께 보냅니다.",
  },
  {
    icon: MessageSquareText,
    accent: "text-signal-ember",
    title: "이어서 사진과 자막을 보냅니다",
    body: "현관 사진과, 방문자가 한 말을 받아쓴 자막을 두 번째 알림으로 보냅니다. 누가 왔고 뭐라고 했는지 읽어서 확인합니다.",
  },
]

// 링 3겹 — 초인종에서 소리가 퍼지는 모습. 굵기가 바깥으로 갈수록 얇아진다.
const RINGS = [
  { r: 40, width: 2, delay: "0s" },
  { r: 62, width: 1.5, delay: "0.12s" },
  { r: 86, width: 1, delay: "0.24s" },
]

export function LandingPage() {
  const reduced = useReducedMotion()
  // 모션이 꺼져 있으면 클래스를 아예 붙이지 않는다 → 최종 상태로 즉시 렌더.
  const rise = reduced ? undefined : "motion-rise"
  const at = (delay: string) => (reduced ? undefined : { animationDelay: delay })

  // 랜딩이 떠 있는 동안만 문서 캔버스를 잉크로(스크롤 바운스 흰 바닥 방지).
  useEffect(() => {
    document.documentElement.classList.add("landing-canvas")
    return () => document.documentElement.classList.remove("landing-canvas")
  }, [])

  return (
    <main className="min-h-screen bg-ink text-ink-paper">
      <div className="mx-auto w-full max-w-5xl px-6 py-16 lg:py-24">
        <section className="grid items-center gap-12 lg:grid-cols-[1.15fr_1fr]">
          <div>
            <p
              className={cn("text-caption font-medium tracking-wide text-signal", rise)}
              style={at("0.05s")}
            >
              띵동
            </p>
            <h1
              className={cn(
                "mt-3 text-[clamp(2rem,6vw,3.5rem)] font-extrabold leading-[1.15] tracking-[-0.02em]",
                rise,
              )}
              style={at("0.15s")}
            >
              현관에서 난 소리를
              <br />
              눈으로 확인합니다
            </h1>
            <p
              className={cn(
                "mt-5 max-w-[46ch] text-[clamp(1.0625rem,2vw,1.25rem)] leading-relaxed text-ink-mist",
                rise,
              )}
              style={at("0.28s")}
            >
              소리가 들리지 않아도 현관 상황은 알아야 합니다. 띵동은 현관에서 난
              소리를 구분해 스마트폰으로 알리고, 누가 왔는지 사진과 자막으로
              이어서 전합니다.
            </p>
            <div
              className={cn("mt-9 flex flex-wrap items-center gap-x-6 gap-y-4", rise)}
              style={at("0.4s")}
            >
              <Link
                to="/home"
                className="inline-flex h-btn items-center rounded-xl bg-signal px-7 text-body font-bold text-ink outline-none transition-colors hover:bg-signal/90 focus-visible:ring-[3px] focus-visible:ring-ink-paper focus-visible:ring-offset-2 focus-visible:ring-offset-ink"
              >
                대시보드 열기
              </Link>
              <Link
                to="/help"
                className="rounded-md text-body font-medium text-ink-mist underline-offset-4 outline-none hover:text-ink-paper hover:underline focus-visible:ring-[3px] focus-visible:ring-ink-paper focus-visible:ring-offset-2 focus-visible:ring-offset-ink"
              >
                사용법 보기
              </Link>
            </div>
          </div>

          {/* 현관문 + 초인종에서 퍼지는 소리. 장식이므로 SR 에서 숨긴다. */}
          <div className="order-first mx-auto w-full max-w-xs lg:order-none lg:max-w-none">
            <svg
              viewBox="0 0 240 240"
              className="h-auto w-full"
              aria-hidden
              focusable="false"
            >
              <g fill="none" stroke="var(--signal)">
                {RINGS.map((ring) => (
                  <circle
                    key={ring.r}
                    cx="152"
                    cy="132"
                    r={ring.r}
                    strokeWidth={ring.width}
                    className={cn(!reduced && "motion-ring")}
                    // 모션 없이도 링이 보이도록 정적 불투명도로 대체한다(빈 그림 방지).
                    style={reduced ? { opacity: 0.32 } : { animationDelay: ring.delay }}
                  />
                ))}
              </g>
              <rect
                x="26"
                y="22"
                width="106"
                height="196"
                rx="10"
                fill="var(--ink-surface)"
                stroke="var(--ink-line)"
                strokeWidth="2"
              />
              <circle cx="114" cy="128" r="4.5" fill="var(--ink-mist)" />
              <rect
                x="142"
                y="116"
                width="20"
                height="32"
                rx="7"
                fill="var(--ink-surface)"
                stroke="var(--signal)"
                strokeWidth="2"
              />
              <circle cx="152" cy="132" r="4.5" fill="var(--signal)" />
            </svg>
          </div>
        </section>

        <section className="mt-20 border-t border-ink-line pt-12">
          <h2 className={cn("text-h2 font-bold", rise)} style={at("0.5s")}>
            소리가 난 뒤 일어나는 일
          </h2>
          <ol className="mt-8 space-y-8 border-l border-ink-line pl-7">
            {STEPS.map((step, i) => (
              <li
                key={step.title}
                className={cn("relative", rise)}
                style={at(`${0.55 + i * 0.13}s`)}
              >
                <span
                  className="absolute -left-7 top-1 flex h-6 w-6 -translate-x-1/2 items-center justify-center rounded-full bg-ink-surface ring-1 ring-ink-line"
                  aria-hidden
                >
                  <step.icon className={cn("h-3.5 w-3.5", step.accent)} />
                </span>
                <h3 className="text-h3 font-bold">{step.title}</h3>
                <p className="mt-2 max-w-[62ch] text-body leading-relaxed text-ink-mist">
                  {step.body}
                </p>
              </li>
            ))}
          </ol>
        </section>

        <footer
          className={cn(
            "mt-20 border-t border-ink-line pt-6 text-caption text-ink-mist",
            rise,
          )}
          style={at("0.95s")}
        >
          청각장애인 1인 가구를 위한 현관 알림 시스템 · 서경대학교 공학종합설계
        </footer>
      </div>
    </main>
  )
}
