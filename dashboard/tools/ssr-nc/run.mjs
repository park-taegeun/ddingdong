#!/usr/bin/env node
/**
 * 대시보드 프론트 negative control 하네스 (실행: `npm run ssr-nc`)
 *
 * 방식 = decisions.md 8.4(f). 실제 소스(src/)를 앵커 패턴으로 **일시 변형** →
 * `vite build --ssr` 로 재번들 → `react-dom/server` 렌더 → **텍스트 라벨 단언** → 복원.
 * 대시보드에 테스트 러너가 없어도 돌아간다 — **신규 의존성 0**(react-dom·vite 기설치).
 *
 * 판정: baseline(무변형)은 **전건 통과가 정상**이고, 각 NC 변형은 **1건 이상 실패해야**
 * 정상이다. NC가 통과해 버리면 "가드 부재"로 결론짓기 전에 카테고리 20 「미검출의 판정」
 * 순서를 밟는다 — ① 도구 생존(변형이 실제 적용됐는가) ② 그 변형이 도달 가능 입력에서
 * 결함이 되는가 ③ 단언 자체가 무디지 않은가.
 *
 * ── 🔴 한계 (자산화 = 전면 해소가 아니다) ──────────────────────────────────
 * ✅ 해소: 하네스가 scratchpad 밖 repo 자산이 됐다(8.4(f) 한계 ①).
 * ⚠️ 승계: **텍스트 라벨만** 검사한다. 8.3 3중 표기(라벨·아이콘·색) 중 실제로 단언하는
 *          축은 **라벨 하나뿐**이며 색·아이콘·레이아웃·대비비·터치 타깃은 미검증이다
 *          (8.4(f) 한계 ② / 8.5(h)).
 * ⚠️ 승계: SSR 문자열 렌더라 **실제 브라우저 CSS 적용·반응형·포커스 거동 미검증**.
 * ⚠️ 신규: **CI 미연결.** 사람이 `npm run ssr-nc` 를 쳐야 돈다 → 회귀 방지는 자동이 아니다.
 *          `.github/workflows/` 연결은 별건(사용자 판단 사안).
 */
import { execFileSync } from "node:child_process"
import { readFileSync, rmSync, writeFileSync } from "node:fs"
import path from "node:path"
import { fileURLToPath, pathToFileURL } from "node:url"

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..") // dashboard/
const OUT_REL = "dist-ssr/ssr-nc" // .gitignore 의 `dist-ssr` 이 이미 덮는다
const ENTRY_REL = "tools/ssr-nc/entry.tsx"

const SRC = {
  health: "src/components/stats/SystemHealthCard.tsx",
  tof: "src/components/notifications/NotificationTof.tsx",
  format: "src/lib/format.ts",
}

/**
 * 변형 케이스. `anchor` 는 **라인 번호 비의존 패턴**이며 파일 안에서 정확히 1건이어야
 * 한다(preflight 가 강제). 늘리는 것이 목적이 아니라 하네스가 작동함을 증명하는
 * 최소 집합이다 — 새 케이스는 이 배열에 한 줄 추가하면 된다.
 */
const CASES = [
  {
    id: "NC-1",
    file: SRC.health,
    desc: "expired 분기 제거 — 음수 잔여 분이 '…분 후 만료'로 샌다 (PR #49 재현)",
    anchor: 'if (status !== "expired") return',
    patch: "if (true) return",
  },
  {
    id: "NC-2",
    file: SRC.health,
    desc: "경과 분 부호 뒤집기 — '-10분 전 만료' (PR #49 재현, 무딘 단언 함정)",
    anchor: "const elapsed = -minutes",
    patch: "const elapsed = minutes",
  },
  {
    id: "NC-3",
    file: SRC.tof,
    desc: "ToF 미적용 분기 제거 — 부재가 '사람 없음'으로 위장 (PR #47 재현)",
    anchor: "if (!tof.applied) {",
    patch: "if (false) {",
  },
  {
    id: "NC-4",
    file: SRC.format,
    desc: "confidence null 비교 완화 — 실측 0 이 '정보 없음'이 된다 (PR #47 재현)",
    anchor: 'if (value === null) return "정보 없음"',
    patch: 'if (!value) return "정보 없음"',
  },
]

/**
 * 단언. `has` = 그 텍스트가 있어야 정상, `lacks` = 없어야 정상.
 *
 * ★ 비교 단위가 "부분 문자열"이 아니라 **텍스트 노드 완전 일치**인 이유:
 *   PR #49 NC-4b 에서 `"10분 전 만료" in out` 이 `-10분 전 만료` 를 **통과시켰다**.
 *   가드 부재가 아니라 단언이 무뎠던 것이다(8.5(g)). 접두/접미가 붙은 변형이
 *   통과하지 못하도록 segments() 로 노드를 쪼갠 뒤 === 로 비교한다.
 */
const ASSERTIONS = [
  { fixture: "token_valid", kind: "has", text: "360분 후 만료" },
  { fixture: "token_valid", kind: "has", text: "유효" },
  { fixture: "token_expiring", kind: "has", text: "5분 후 만료" },
  { fixture: "token_expiring", kind: "has", text: "곧 만료" },
  { fixture: "token_expired_10m", kind: "has", text: "10분 전 만료" },
  { fixture: "token_expired_10m", kind: "has", text: "만료됨" },
  { fixture: "token_expired_3d", kind: "has", text: "3일 전 만료" },
  { fixture: "tof_passed", kind: "has", text: "사람 확인" },
  { fixture: "tof_rejected", kind: "has", text: "사람 없음" },
  { fixture: "tof_absent", kind: "has", text: "검증 안 함" },
  { fixture: "tof_absent", kind: "lacks", text: "사람 없음" },
  { fixture: "tof_absent", kind: "has", text: "tof_absent" },
  { fixture: "stt_conf_zero", kind: "has", text: "0%" },
  { fixture: "stt_conf_zero", kind: "lacks", text: "정보 없음" },
  { fixture: "stt_conf_null", kind: "has", text: "정보 없음" },
]

const abs = (file) => path.join(ROOT, file)
const read = (file) => readFileSync(abs(file), "utf8")
const countOf = (hay, needle) => hay.split(needle).length - 1

// 태그·주석을 지우고 남은 텍스트 노드 배열. 위 ASSERTIONS 주석 참조.
function segments(html) {
  return html
    .replace(/<!--[\s\S]*?-->/g, "")
    .split(/<[^>]*>/)
    .map((s) => s.trim())
    .filter(Boolean)
}

/**
 * 착수 전 게이트. ① 앵커가 파일마다 정확히 1건인지 ② 같은 파일을 치는 케이스끼리
 * 앵커가 서로를 삼키지 않는지(= 상호 배타) 확인한다.
 * 근거 = 8.5(g): `expiring` 블록 제거 변형의 앵커가 다른 NC 앵커와 충돌해 count == 2 가
 * 됐고, 이 검사가 거짓 결론을 막았다(카테고리 20 4단계 보장 3번째 작동).
 * export 하는 이유 = 이 검사 자체가 작동하는지 밖에서 검증할 수 있어야 하기 때문.
 */
export function preflight(cases) {
  for (const c of cases) {
    const n = countOf(read(c.file), c.anchor)
    if (n !== 1) {
      throw new Error(
        `${c.id}: 앵커 매치 ${n}건 (1건이어야 함) — ${c.file}\n  앵커: ${c.anchor}`,
      )
    }
  }
  for (let i = 0; i < cases.length; i++) {
    for (let j = i + 1; j < cases.length; j++) {
      const [a, b] = [cases[i], cases[j]]
      if (a.file !== b.file) continue
      if (a.anchor.includes(b.anchor) || b.anchor.includes(a.anchor)) {
        throw new Error(
          `${a.id}/${b.id}: 같은 파일의 앵커가 상호 배타적이지 않다 — ${a.file}`,
        )
      }
    }
  }
}

let buildCount = 0

function renderAll() {
  execFileSync(
    "npx",
    ["vite", "build", "--ssr", ENTRY_REL, "--outDir", OUT_REL, "--logLevel", "error"],
    { cwd: ROOT, stdio: ["ignore", "ignore", "inherit"] },
  )
  // 재빌드한 같은 경로를 다시 import 하므로 ESM 모듈 캐시를 우회해야 한다.
  const url = pathToFileURL(path.join(ROOT, OUT_REL, "entry.js")).href
  return import(`${url}?build=${++buildCount}`).then((m) => m.output)
}

function check(output) {
  const fails = []
  for (const a of ASSERTIONS) {
    const found = segments(output[a.fixture] ?? "").includes(a.text)
    if (a.kind === "has" ? !found : found) {
      fails.push(`${a.fixture} ${a.kind} "${a.text}"`)
    }
  }
  return fails
}

/**
 * 카테고리 20 「4단계 보장」. ① 앵커 1건(preflight) → ② 변형 후 디스크 재독 →
 * ③ assert 변형본 != 원본 → ④ 복원 후 assert 복원본 == 원본.
 * ④ 는 finally 라 예외·중단 경로에서도 돈다 — 복원 실패는 제품 코드 오염이다.
 */
async function withMutation(c, fn) {
  const file = abs(c.file)
  const original = readFileSync(file, "utf8")
  try {
    writeFileSync(file, original.replace(c.anchor, () => c.patch))
    const mutated = readFileSync(file, "utf8") // ② 디스크 재독
    if (mutated === original) throw new Error(`${c.id}: 변형이 디스크에 반영되지 않았다`) // ③
    if (countOf(mutated, c.anchor) !== 0) throw new Error(`${c.id}: 앵커가 잔존한다`)
    return await fn()
  } finally {
    writeFileSync(file, original) // ④
    if (readFileSync(file, "utf8") !== original) {
      throw new Error(`🔴 ${c.file} 복원 실패 — 제품 코드가 오염됐다. 즉시 확인할 것.`)
    }
  }
}

function assertCleanSrc() {
  const dirty = execFileSync("git", ["status", "--porcelain", "--", "src"], {
    cwd: ROOT,
    encoding: "utf8",
  }).trim()
  if (dirty) throw new Error(`🔴 src/ 에 잔여 변경이 있다 — 복원 누락:\n${dirty}`)
}

async function main() {
  assertCleanSrc()
  preflight(CASES)

  const baseFails = check(await renderAll())
  console.log(
    baseFails.length === 0
      ? "baseline  ✅ 통과 (도구 생존 — 무변형은 통과가 정상)"
      : `baseline  ❌ 실패 ${baseFails.length}건\n  ${baseFails.join("\n  ")}`,
  )

  const results = []
  for (const c of CASES) {
    const fails = await withMutation(c, async () => check(await renderAll()))
    results.push({ c, fails })
    console.log(
      `${c.id}      ${fails.length > 0 ? "✅ 검출" : "❌ 미검출"} (실패 단언 ${fails.length}건) — ${c.desc}`,
    )
    for (const f of fails) console.log(`            · ${f}`)
  }

  assertCleanSrc()
  rmSync(path.join(ROOT, OUT_REL), { recursive: true, force: true })

  const bad = baseFails.length > 0 || results.some((r) => r.fails.length === 0)
  console.log(bad ? "\n❌ 하네스 판정 실패" : "\n✅ 전건 정상 (baseline 통과 + NC 전건 검출)")
  process.exitCode = bad ? 1 : 0
}

// 직접 실행일 때만 돈다 — preflight 를 밖에서 import 해 검증할 수 있어야 하기 때문.
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch((e) => {
    console.error(e.message)
    process.exitCode = 1
  })
}
