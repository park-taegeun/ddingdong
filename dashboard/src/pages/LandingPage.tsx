// 랜딩(`/`) — 부스 관람객이 대시보드보다 먼저 보는 화면.
//
// 화면의 주인공 = **실제로 도착하는 카카오톡 알림의 재현**이다. 좌 텍스트 / 우 일러스트
// 2분할을 버리고 세로 한 축(마스트헤드 → 대화 → 해설)으로 세웠다. 말풍선 문구는
// 지어낸 것이 아니라 서버 상수 실물이다:
//   `server/app/constants.py` PRIMARY_MESSAGES["doorbell"] / SECONDARY_FEED_TITLES["doorbell"]
//   / KAKAO_FEED_BUTTON_TITLE, `kakao.py` _feed_description 의 "{월}월 {일}일 {HH:MM} 감지"
//   형식(24시간제 — 말풍선 바깥 시각은 서버가 아니라 카카오톡이 그리는 12시간제라 다르다).
//   자막 말풍선은 `### 7.7` (g) ④런타임 실측에서 실제 CSR 이 뱉고 카카오톡에 도착한
//   문장 그대로다(구두점 없음 = STT 출력 원형). mock 문구가 아니다.
// 문구 원칙: 제품에 없는 기능(초인종 등록/해제)은 쓰지 않는다. 성능 수치 인용 없음.
// 카카오 로고·브랜드 자산은 쓰지 않는다 — 말풍선 레이아웃만 재현한다(상표).

// ⚠️ `cn()` = twMerge 라 `text-caption` 류 토큰 유틸이 뒤따르는 `text-<색>` 과 같은 그룹으로
// 묶여 **지워진다**(실측: twMerge("text-caption font-bold text-lp-blue") → "font-bold text-lp-blue").
// 그래서 cn() 안에서 글자 크기를 줄 때는 `text-(length:--text-*)` 로 쓴다. 평범한 문자열
// className 은 twMerge 를 안 거치므로 `text-body` 그대로 써도 된다.

import { Bell } from "lucide-react"
import { Link } from "react-router-dom"
import { useReducedMotion } from "@/hooks/useReducedMotion"
import { cn } from "@/lib/utils"

// 제품이 갈라내는 3종. 색은 대시보드 클래스 색과 같은 의미를 유지한다
// (초인종 --primary / 노크 --warning / 화재경보 --danger 의 대비 보정분).
const CLASSES = [
  { label: "초인종", tint: "bg-lp-blue/10 text-lp-blue" },
  { label: "노크", tint: "bg-lp-amber/10 text-lp-amber" },
  { label: "화재경보", tint: "bg-lp-red/10 text-lp-red" },
]

// 링 = 알림이 퍼지는 소리. 발신 아바타(종)를 원점으로, 바깥으로 갈수록 얇고 옅어진다.
// 대화 카드가 불투명해서 카드 안쪽은 가려지고 **카드 밖으로 나간 호(弧)만** 보인다.
const RINGS = [
  { r: 300, width: 2, opacity: 0.34, delay: "0.54s" },
  { r: 430, width: 1.5, opacity: 0.2, delay: "0.66s" },
  { r: 580, width: 1.25, opacity: 0.11, delay: "0.78s" },
]

const SENT_AT = "오후 1:39"

export function LandingPage() {
  const reduced = useReducedMotion()
  // 모션이 꺼져 있으면 클래스를 아예 붙이지 않는다 → 최종 상태로 즉시 렌더.
  const rise = reduced ? undefined : "motion-rise"
  const bubble = reduced ? undefined : "motion-bubble"
  const at = (delay: string) => (reduced ? undefined : { animationDelay: delay })

  return (
    <main className="min-h-screen break-keep bg-background text-foreground">
      {/* ── 마스트헤드. 폭을 좁게(max-w-3xl) 잡아 읽는 화면으로 만든다 ── */}
      <div className="mx-auto w-full max-w-3xl px-6 pt-14 lg:pt-20">
        <p
          className={cn("text-(length:--text-caption) font-bold tracking-wide text-lp-blue", rise)}
          style={at("0.04s")}
        >
          띵동
        </p>
        <h1
          className={cn(
            "mt-2.5 text-[clamp(1.875rem,5.5vw,3rem)] font-extrabold leading-[1.18] tracking-[-0.02em]",
            rise,
          )}
          style={at("0.12s")}
        >
          초인종 소리를 못 들어도
          <br />
          현관 앞은 알 수 있습니다
        </h1>
        <p
          className={cn(
            "mt-4 max-w-[40ch] text-pretty text-[clamp(1.125rem,2vw,1.25rem)] leading-relaxed text-foreground-secondary",
            rise,
          )}
          style={at("0.22s")}
        >
          현관에서 소리가 나면 어떤 소리였는지 판단해 스마트폰으로 보냅니다. 누가
          왔는지는 사진이 보여 주고, 무슨 말을 했는지는 자막으로 읽습니다.
        </p>
        <ul className={cn("mt-5 flex flex-wrap gap-2", rise)} style={at("0.3s")}>
          {CLASSES.map((c) => (
            <li
              key={c.label}
              className={cn("rounded-full px-3 py-1.5 text-(length:--text-caption) font-bold", c.tint)}
            >
              {c.label}
            </li>
          ))}
        </ul>
        <div
          className={cn("mt-8 flex flex-wrap items-center gap-x-6 gap-y-3", rise)}
          style={at("0.38s")}
        >
          <Link
            to="/home"
            className="inline-flex h-btn items-center rounded-xl bg-lp-blue px-7 text-body font-bold text-lp-on-blue outline-none transition-opacity hover:opacity-90 focus-visible:ring-[3px] focus-visible:ring-lp-blue focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            대시보드 열기
          </Link>
          <Link
            to="/help"
            className="rounded-md text-body font-medium text-foreground-secondary underline-offset-4 outline-none hover:text-foreground hover:underline focus-visible:ring-[3px] focus-visible:ring-lp-blue focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            사용법 보기
          </Link>
        </div>
      </div>

      {/* ── 대화 재현. 발신 아바타에서 링이 퍼져 나간다 ── */}
      <section className="relative overflow-hidden pb-16 pt-9">
        <div className="mx-auto w-full max-w-3xl px-6">
          <p
            className={cn("mb-3 text-pretty text-(length:--text-body) text-foreground-secondary", rise)}
            style={at("0.46s")}
          >
            초인종이 울리면 스마트폰에 이렇게 도착합니다.
          </p>

          <div className="lg:grid lg:grid-cols-[24rem_1fr] lg:items-start lg:gap-9">
            <div className="relative">
              {/* 원점 = 아바타 중심(카드 padding 16px + 아바타 반지름 18px). */}
              <svg
                viewBox="-640 -640 1280 1280"
                className="pointer-events-none absolute left-[2.125rem] top-[2.25rem] h-[80rem] w-[80rem] -translate-x-1/2 -translate-y-1/2"
                aria-hidden
                focusable="false"
              >
                <g fill="none" stroke="var(--lp-blue)">
                  {RINGS.map((ring) => (
                    <circle
                      key={ring.r}
                      cx="0"
                      cy="0"
                      r={ring.r}
                      strokeWidth={ring.width}
                      className={cn(!reduced && "motion-ring")}
                      // 모션이 없어도 링은 그대로 보인다(빈 그림 방지) — 최종 불투명도가 곧 정적 값.
                      style={
                        reduced
                          ? { opacity: ring.opacity }
                          : {
                              opacity: 0,
                              animationDelay: ring.delay,
                              ["--ring-o" as string]: ring.opacity,
                            }
                      }
                    />
                  ))}
                </g>
              </svg>

              <div className="relative rounded-2xl bg-lp-canvas p-4">
                <div className="flex gap-2.5">
                  <span
                    className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-[0.9rem] bg-lp-blue"
                    aria-hidden
                  >
                    <Bell className="h-4.5 w-4.5 text-lp-on-blue" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-[0.875rem] font-medium text-lp-meta">띵동</p>

                    {/* ① 1차 알림 — PRIMARY_MESSAGES["doorbell"] 실물 */}
                    <div
                      className={cn("mt-1 flex items-end gap-1.5", bubble)}
                      style={at("0.54s")}
                    >
                      <p className="rounded-2xl rounded-tl-md bg-lp-bubble px-3 py-2 text-[1rem] leading-snug text-foreground">
                        🔔[띵동] 초인종이 울렸어요.
                      </p>
                      <span className="shrink-0 text-[0.75rem] text-lp-meta">{SENT_AT}</span>
                    </div>

                    {/* ② 2차 사진 — feed 템플릿(제목 + 감지 시각 + 버튼) */}
                    <div
                      className={cn("mt-2 flex items-end gap-1.5", bubble)}
                      style={at("0.66s")}
                    >
                      <div className="w-[13.75rem] overflow-hidden rounded-2xl rounded-tl-md bg-lp-bubble">
                        <PhotoSlot />
                        <div className="px-3 pb-2 pt-2.5">
                          <p className="text-[0.875rem] font-bold leading-snug text-foreground">
                            🔔[띵동] 초인종 — 방문자 사진
                          </p>
                          <p className="mt-0.5 text-[0.8125rem] text-lp-meta">9월 12일 13:39 감지</p>
                        </div>
                        <p className="border-t border-border py-2 text-center text-[0.875rem] font-medium text-lp-blue">
                          사진 보기
                        </p>
                      </div>
                      <span className="shrink-0 text-[0.75rem] text-lp-meta">{SENT_AT}</span>
                    </div>

                    {/* ③ 2차 자막 — 받아쓴 문장을 그대로 보낸다(서버가 앞뒤에 아무것도 붙이지 않는다) */}
                    <div
                      className={cn("mt-2 flex items-end gap-1.5", bubble)}
                      style={at("0.78s")}
                    >
                      <p className="rounded-2xl rounded-tl-md bg-lp-bubble px-3 py-2 text-[1rem] leading-snug text-foreground">
                        계세요 택배 왔습니다 문 앞에 두고 갈게요
                      </p>
                      <span className="shrink-0 text-[0.75rem] text-lp-meta">{SENT_AT}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <p
              className={cn(
                "mt-4 text-pretty text-(length:--text-caption) leading-relaxed text-foreground-secondary lg:mt-1",
                rise,
              )}
              style={at("0.86s")}
            >
              말풍선 문구는 서버가 실제로 보낸 것입니다. 사진 자리만 그림으로
              대신했고, 실제 카카오톡에서는 「나와의 채팅」 오른쪽에 붙어 옵니다.
            </p>
          </div>
        </div>
      </section>

      {/* ── 해설. 세 항목을 같은 카드로 반복하지 않는다 — 하나가 크고 둘은 딸린다 ── */}
      <section className="mx-auto w-full max-w-3xl px-6 pb-14">
        <div className="grid gap-x-10 gap-y-9 border-t border-border pt-10 lg:grid-cols-[1.4fr_1fr]">
          <article className={cn(rise)} style={at("0.94s")}>
            <span className="block h-1 w-11 rounded-full bg-lp-blue" aria-hidden />
            <h2 className="mt-4 text-[clamp(1.375rem,3vw,1.625rem)] font-extrabold leading-snug tracking-[-0.01em]">
              옆집 초인종에는 반응하지 않습니다
            </h2>
            <p className="mt-3 text-pretty text-body leading-relaxed text-foreground-secondary">
              벽 너머로 새어 들어온 소리까지 알림으로 오면, 결국 알림을 꺼 두게
              됩니다. 그래서 소리가 나면 문 앞에 사람이 있는지부터 확인합니다.
              움직임까지 함께 봐야 방문으로 치기 때문에, 문 앞에 오래 멈춰 서
              있으면 놓칠 때도 있습니다.
            </p>
          </article>

          <div
            className={cn("space-y-7 lg:border-l lg:border-border lg:pl-9", rise)}
            style={at("1.02s")}
          >
            <article>
              <h3 className="text-h3 font-bold leading-snug text-lp-red">화재경보는 기다리지 않고</h3>
              <p className="mt-2 text-pretty text-body leading-relaxed text-foreground-secondary">
                사람 확인을 건너뛰고 곧바로 보냅니다. 소방청 청각장애인 화재
                행동요령 네 단계가 알림에 함께 옵니다.
              </p>
            </article>
            <article>
              <h3 className="text-h3 font-bold leading-snug text-lp-amber">자막은 받아쓴 그대로</h3>
              <p className="mt-2 text-pretty text-body leading-relaxed text-foreground-secondary">
                택배인지 잘못 찾아온 사람인지, 읽고 판단하면 됩니다. 소리가
                뭉개져 못 알아들은 날은 사진만 가고 자막은 붙지 않습니다.
              </p>
            </article>
          </div>
        </div>
      </section>

      <footer
        className={cn("mx-auto w-full max-w-3xl px-6 pb-12", rise)}
        style={at("1.1s")}
      >
        <p className="border-t border-border pt-5 text-pretty text-body text-foreground-secondary">
          청각장애인 1인 가구를 위한 현관 알림 시스템
        </p>
        <p className="mt-1 text-caption text-foreground-secondary">
          서경대학교 공학종합설계
        </p>
      </footer>
    </main>
  )
}

// 사진 자리. 실 현관 사진·스톡·AI 생성 이미지를 쓰지 않기로 한 자리라 "빈 프레임"이
// 아니라 **도식**을 넣는다 — 자막 말풍선("택배 왔습니다")과 같은 장면을 그린다.
// 와이어프레임으로 읽히지 않도록 바닥/벽/문을 다른 명도로 깔아 도형에 앞뒤를 준다.
function PhotoSlot() {
  return (
    <svg viewBox="0 0 220 132" className="block h-auto w-full" aria-hidden focusable="false">
      <rect width="220" height="132" fill="var(--background-sub)" />
      {/* 바닥 */}
      <rect y="104" width="220" height="28" fill="var(--border)" />
      {/* 현관문 + 손잡이 */}
      <rect x="124" y="10" width="80" height="94" fill="var(--lp-canvas)" />
      <rect x="124" y="10" width="80" height="4" fill="var(--foreground-secondary)" opacity="0.18" />
      <circle cx="134" cy="62" r="3" fill="var(--foreground-secondary)" opacity="0.55" />
      {/* 문 앞에 선 사람 */}
      <g fill="var(--foreground-secondary)" opacity="0.62">
        <circle cx="74" cy="45" r="14" />
        <path d="M74 62a21 21 0 0 1 21 21v21H53V83a21 21 0 0 1 21-21Z" />
      </g>
      {/* 발밑의 택배 상자 */}
      <g>
        <rect x="22" y="82" width="34" height="22" fill="var(--lp-amber)" opacity="0.8" />
        <rect x="36" y="82" width="6" height="22" fill="var(--background-sub)" opacity="0.55" />
      </g>
    </svg>
  )
}
