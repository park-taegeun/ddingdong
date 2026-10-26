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
  connection: "src/lib/connection.ts",
  imageRetry: "src/lib/image-retry.ts",
  image: "src/components/notifications/NotificationImage.tsx",
  loadMore: "src/lib/load-more.ts",
  badge: "src/components/notifications/NotificationStatusBadge.tsx",
  card: "src/components/notifications/NotificationCard.tsx",
  stt: "src/components/notifications/NotificationSTT.tsx",
  meta: "src/lib/notification-meta.ts",
  banner: "src/lib/banner.ts",
  statusBanner: "src/components/feedback/StatusBanner.tsx",
  filter: "src/lib/notification-filter.ts",
  unread: "src/lib/unread.ts",
  skipCard: "src/components/stats/SkipReasonsCard.tsx",
  list: "src/components/notifications/NotificationList.tsx",
  regCard: "src/components/settings/DoorbellRegistrationCard.tsx",
  help: "src/pages/HelpPage.tsx",
  onboarding: "src/components/feedback/OnboardingModal.tsx",
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
  // AU-07 I1 — 정확히 STALE_AFTER_MS 경과면 끊김(≥). 결함 = > 로 바뀌면 경계 점에서 1틱 늦게
  // 끊김이 된다. 함정: 경계 점(6000ms)을 단언하지 않으면 5999 · 6001 만으로는 못 잡는다 —
  // 그래서 stale_boundary 는 바로 그 점을 렌더한다. 앵커는 >= 가 붙은 줄 전체(파일 안 1건).
  {
    id: "NC-a",
    file: SRC.connection,
    desc: "끊김 경계 ≥ → > — 정확히 6,000ms 가 '정상'으로 남는다 (AU-07 I1)",
    anchor: "return nowMs - lastUpdated.getTime() >= staleAfterMs",
    patch: "return nowMs - lastUpdated.getTime() > staleAfterMs",
  },
  // AU-07 I5 — 끊김은 온라인 · 오프라인보다 먼저 본다. 결함 = 끊김 분기를 지우면 서버가 죽어도
  // 마지막 health 가 online 이라 「현관 기기 연결됨」이 남는다(AU-07 원래 증상). 함정: 끊김 단독
  // 입력(online=false · health 없음)만 보면 「연결 확인 중」으로 떨어져도 라벨 차이를 못 볼 수
  // 있다 — 온라인+끊김 입력을 단언한다. 앵커 = 분기 조건 한 줄(NC-a 앵커와 문자열 비포함).
  {
    id: "NC-b",
    file: SRC.connection,
    desc: "헤더 끊김 우선 제거 — 온라인+끊김에서 '현관 기기 연결됨' (AU-07 I5)",
    anchor: "if (disconnected) {",
    patch: "if (false) {",
  },
  // AU-18 I2 — 재시도는 실패 1 ~ 6번째 뒤(요청 최대 7). 결함 = > 가 >= 로 바뀌면 마지막 재시도 1회가
  // 사라진다. 함정: 실패 7(중단)만 단언하면 못 잡는다 — 경계 점 실패 6을 단언한다.
  {
    id: "NC-c",
    file: SRC.imageRetry,
    desc: "재시도 상한 off-by-one > → >= — 실패 6 뒤 재시도가 '중단' (AU-18 I2)",
    anchor: "const exhausted = failures > max",
    patch: "const exhausted = failures >= max",
  },
  // AU-18 I2 — 상한이 없으면 만료 · mock · 옛 주소 사진에 무한 재시도. 함정: 실패 1 · 6만 보면
  // 정상과 같다 — 실패 7을 단언한다. 앵커 = 중단 분기 한 줄(NC-c 앵커와 문자열 비포함).
  {
    id: "NC-d",
    file: SRC.imageRetry,
    desc: "재시도 상한 제거 — 실패 7 뒤에도 재시도 (AU-18 I2)",
    anchor: "if (exhausted) return null",
    patch: "if (false) return null",
  },
  // AU-18 I7 — 시도 번호 쿼리는 덧붙이기만 한다. 결함 = 기존 쿼리를 버리면 서명 · 버전 쿼리가 붙은
  // 주소에서 재시도가 다른 리소스를 받는다. 함정: 쿼리 없는 픽스처만 보면 결과가 같다.
  {
    id: "NC-e",
    file: SRC.imageRetry,
    desc: "재시도 URL이 기존 쿼리를 덮어씀 (AU-18 I7)",
    anchor: "const base = hashAt === -1 ? src : src.slice(0, hashAt)",
    patch: 'const base = (hashAt === -1 ? src : src.slice(0, hashAt)).split("?")[0]',
  },
  // AU-18 I1 — 첫 렌더는 지금과 같은 사진. 결함 = 초기 상태가 실패면 서버가 멀쩡해도 실패 문구가
  // 먼저 보인다. 함정: 실패 문구 부재만 보면 빈 렌더도 통과 — 「크게 보기」 존재도 함께 단언한다.
  {
    id: "NC-f",
    file: SRC.image,
    desc: "초기 상태를 실패로 — 첫 렌더에 '사진을 불러올 수 없어요' (AU-18 I1)",
    anchor: "    url: src,",
    patch: "    url: null,",
  },
  // 이전 알림 더 보기 ① — 요청 개수가 받은 limit보다 크면 불러오는 중. 결함 = 분기가 없으면 누른 직후
  // 옛 응답(has_more 참)으로 버튼이 다시 살아나 연타된다. 함정: 요청 == 받은 픽스처만 보면 같다.
  {
    id: "NC-N1",
    file: SRC.loadMore,
    desc: "불러오는 중 분기 제거 — 요청 40 · 받은 20에서 '버튼' (더 보기 ①)",
    anchor: 'if (requested > receivedLimit) return "loading"',
    patch: 'if (false) return "loading"',
  },
  // 이전 알림 더 보기 ②③ — 끝을 최대치보다 먼저 본다. 결함 = 순서를 바꾸면 「100건 · 더 없음」이
  // 최대치 문구가 된다. 함정: 「100 · 더 있음」 · 「20 · 더 없음」만 보면 순서와 무관하게 같다.
  {
    id: "NC-N2",
    file: SRC.loadMore,
    desc: "끝 · 최대치 판정 순서 뒤집기 — limit 100 · has_more 거짓이 '최대치' (더 보기 ②③)",
    anchor: '  if (!hasMore) return "end"\n  if (receivedLimit >= max) return "max"',
    patch: '  if (receivedLimit >= max) return "max"\n  if (!hasMore) return "end"',
  },
  // 이전 알림 더 보기 ⓐ — 다음 개수는 최대에서 멈춘다. 결함 = 상한이 없으면 120을 요청해 서버가 100으로
  // 자르고 받은 limit(120) ≥ 최대라 최대치로 보이지만 개수 상태가 서버와 어긋난다. 함정: 20 · 80만 보면 같다.
  {
    id: "NC-N3",
    file: SRC.loadMore,
    desc: "다음 개수 상한(min) 제거 — 다음 90 · 100이 110 · 120 (더 보기 ⓐ)",
    anchor: "return Math.min(current + step, max)",
    patch: "return current + step",
  },
  // 이전 알림 더 보기 — 정의역 밖은 던진다. 결함 = 검사가 없으면 0 · 소수가 그대로 요청된다.
  {
    id: "NC-N4",
    file: SRC.loadMore,
    desc: "정의역 검사 제거 — 요청 0 · 다음 0 · 1.5가 던지지 않는다 (더 보기)",
    anchor: "if (!Number.isInteger(value) || value < 1) {",
    patch: "if (false) {",
  },
  // 8.4 · 7.6(d) — 뱃지는 secondary_sent 를 enrich_status 보다 먼저 본다. 결함 = 두 분기 순서를 바꾸면
  // 엇갈린 입력(전송 완료인데 처리 중 표기)이 「2차 처리 중」이 된다. 함정: 정상 조합만 보면 순서와 무관하게 같다.
  {
    id: "NC-B1",
    file: SRC.badge,
    desc: "뱃지 읽는 순서 뒤집기 — secondary_sent 보다 처리 중을 먼저 (7.6(d))",
    anchor:
      '  if (status.secondary_sent) {\n    return { label: "전송 완료", tone: "success", Icon: CircleCheck }\n  }\n  if (status.enrich_status === "processing" || status.enrich_status === "pending") {\n    return { label: "2차 처리 중", tone: "processing", Icon: Clock }\n  }',
    patch:
      '  if (status.enrich_status === "processing" || status.enrich_status === "pending") {\n    return { label: "2차 처리 중", tone: "processing", Icon: Clock }\n  }\n  if (status.secondary_sent) {\n    return { label: "전송 완료", tone: "success", Icon: CircleCheck }\n  }',
  },
  // B4 — 카톡 실패는 「보내기 실패」. 결함 = 분기가 없으면 실패가 회색 「발송 제외」로 숨는다(감사 D02 원래 증상).
  {
    id: "NC-B2",
    file: SRC.badge,
    desc: "뱃지 카톡 실패 분기 제거 — token_expired 가 '발송 제외' (B4)",
    anchor: "if (status.skip_reason && KAKAO_FAILURE_REASONS.has(status.skip_reason)) {",
    patch: "if (false) {",
  },
  // B4 — 카드 문장도 실패를 원인 없이 알린다. 결함 = 분기가 없으면 「토큰 만료 때문에 …」 내부 어휘가 보인다.
  {
    id: "NC-B3",
    file: SRC.card,
    desc: "카드 카톡 실패 문장 분기 제거 — '토큰 만료 때문에 …' 노출 (B4)",
    anchor: "(KAKAO_FAILURE_REASONS.has(status.skip_reason) ? (",
    patch: "(false ? (",
  },
  // B3 — 날짜는 달력(자정) 기준. 결함 = 경과 시간으로 세면 어제 23:59(9시간 전)가 「오늘」이 된다.
  // 함정: 어제 0시(33시간 전)만 보면 경과 시간으로도 「어제」라 같다 — 자정 바로 전 시각을 단언한다.
  {
    id: "NC-D1",
    file: SRC.format,
    desc: "날짜 판정을 달력 대신 경과 시간으로 — 어제 23:59 가 시각만 (B3)",
    anchor: "const dayStart = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime()",
    patch: "const dayStart = (x: Date) => x.getTime()",
  },
  // B3 — 다른 해면 연도를 붙인다. 결함 = 빠지면 작년 12월 31일이 올해 날짜처럼 보인다.
  {
    id: "NC-D2",
    file: SRC.format,
    desc: "연도 분기 제거 — 작년 날짜에 연도가 빠진다 (B3)",
    anchor: "d.getFullYear() === now.getFullYear() ? monthDay :",
    patch: "true ? monthDay :",
  },
  // B9 — 신뢰도 칸은 null 일 때만 숨긴다. 결함 = 참거짓 검사로 바꾸면 실측 0 도 숨는다(8.4(d) 0 ≠ 없음).
  {
    id: "NC-S1",
    file: SRC.stt,
    desc: "자막 신뢰도 숨김 조건 완화 — 실측 0 의 '0%'가 사라진다 (B9)",
    anchor: "{stt.confidence !== null && (",
    patch: "{Boolean(stt.confidence) && (",
  },
  // B10 — 창은 경계 포함. 결함 = < 로 바뀌면 정확히 10분 된 행이 창 밖이 된다. 함정: 경계 점을 단언해야 잡힌다.
  {
    id: "NC-W1",
    file: SRC.meta,
    desc: "화재 모션 창 경계 <= → < — 정확히 10분이 창 밖 (B10)",
    anchor: "return nowMs - t <= windowMs",
    patch: "return nowMs - t < windowMs",
  },
  // B10 — 카드가 창 판정을 쓴다. 결함 = 조건이 빠지면 지난 화재 카드가 영구히 흔들린다(감사 D12 원래 증상).
  {
    id: "NC-W2",
    file: SRC.card,
    desc: "카드 화재 모션 창 조건 제거 — 2020년 화재 카드가 흔들림 (B10)",
    anchor: "isWithinWindow(notification.detected_at, nowMs, FIRE_MOTION_WINDOW_MS)",
    patch: "true",
  },
  // 전역 경고 띠 — 끊김이 기기 꺼짐보다 먼저. 결함 = 순서를 바꾸면 서버가 죽었는데 옛 기기 상태로 「기기 꺼짐」이 뜬다.
  // 함정: 한 가지 상태만 켠 입력은 순서와 무관하게 같다 — 끊김 · 꺼짐이 동시에 참인 입력을 단언한다.
  {
    id: "NC-G1",
    file: SRC.banner,
    desc: "띠 우선순위 뒤집기 — 끊김 · 꺼짐 동시에 '기기' (전역 경고 띠)",
    anchor: '  if (disconnected) return "server"\n  if (hasHealth && !isOnline) return "device"',
    patch: '  if (hasHealth && !isOnline) return "device"\n  if (disconnected) return "server"',
  },
  // 전역 경고 띠 — 카톡 실패 판정. 결함 = 분기가 없으면 카톡이 끊겨도 띠가 안 뜬다(감사 D04 원래 증상).
  {
    id: "NC-G2",
    file: SRC.banner,
    desc: "카톡 실패 판정 제거 — 최신 시도 행이 실패여도 '없음' (전역 경고 띠)",
    anchor: "if (s.skip_reason && KAKAO_FAILURE_REASONS.has(s.skip_reason)) return true",
    patch: "if (false) return true",
  },
  // 전역 경고 띠 — 의도된 차단 행은 건너뛰고 첫 발송 시도 행을 본다. 결함 = 맨 위 행만 보면 실패 뒤 기타 소리
  // 한 건이 띠를 지운다. 함정: 실패 행이 맨 위인 입력만 보면 같다 — 차단 뒤 실패 입력을 단언한다.
  {
    id: "NC-G3",
    file: SRC.banner,
    desc: "맨 위 행만 판정 — 차단 뒤 실패가 '없음' (전역 경고 띠)",
    anchor: "for (const n of notifications) {",
    patch: "for (const n of notifications.slice(0, 1)) {",
  },
  // 띠 ① 본문 — 결함 = 끊김 안내 문장을 되살리면 옛 데이터 없는 화면(「알림을 불러오지 못했어요」) 위에서
  // 사실과 다른 말이 되고, 목록 위 끊김 안내와 겹친다. 패치는 문자열 그대로(띠 파일은 그 상수를 import 하지 않는다).
  {
    id: "NC-G4",
    file: SRC.statusBanner,
    desc: "띠 ① 본문 되살리기 — 끊김 띠에 '최근 상태를 불러오지 못해 …' (전역 경고 띠)",
    anchor: 'server: { Icon: ServerOff, title: "서버와 연결이 끊겼어요" },',
    patch: 'server: { Icon: ServerOff, title: "서버와 연결이 끊겼어요", body: "최근 상태를 불러오지 못해 마지막으로 받은 상태를 보여 드려요." },',
  },
  // 날짜 묶음 머리 — 달력(자정) 기준. 결함 = 경과 시간으로 세면 어제 23:59(9시간 전)가 「오늘」 묶음에 들어간다.
  // 함정: 어제 0시(33시간 전)만 보면 같다 — 자정 바로 전 시각을 단언한다. 앵커는 NC-D1(카드 시각)과 문자열 비포함.
  {
    id: "NC-D3",
    file: SRC.format,
    desc: "묶음 머리 날짜 판정을 경과 시간으로 — 어제 23:59 가 '오늘' (날짜 묶음 자정 경계)",
    anchor: "const startOfDay = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime()",
    patch: "const startOfDay = (x: Date) => x.getTime()",
  },
  // 날짜 묶음 — 이웃한 같은 날만 합친다. 결함 = 비교가 빠지면 하루 한 묶음이 아니라 행마다 머리가 붙는다.
  {
    id: "NC-D4",
    file: SRC.filter,
    desc: "같은 날 합치기 제거 — 오늘 2건이 머리 2개 (날짜 묶음)",
    anchor: "if (last && last.heading === heading) last.items.push(item)",
    patch: "if (false) last.items.push(item)",
  },
  // 필터 범위 — 안내는 「불러온 알림 N건 중」을 함께 말한다. 결함 = 범위가 빠지면 화면에 불러온 20건 안의 결과가
  // 전체 기록의 건수처럼 읽힌다(더 보기로 늘 수 있다).
  {
    id: "NC-F1",
    file: SRC.filter,
    desc: "필터 안내에서 범위 제거 — '1건'만 (불러온 범위를 넘어 단정)",
    anchor: "return `불러온 알림 ${loaded}건 중 ${shown}건`",
    patch: "return `${shown}건`",
  },
  // 「보낸 알림만」 — primary_sent 만 남긴다. 결함 = 조건이 빠지면 토글이 아무것도 거르지 않는다.
  {
    id: "NC-F2",
    file: SRC.filter,
    desc: "보낸 알림만 조건 제거 — 보낸만 4건 (필터)",
    anchor: "(!sentOnly || n.notification_status.primary_sent)",
    patch: "true",
  },
  // 종류 칩 — 결함 = 조건이 빠지면 칩이 아무것도 거르지 않는다. 함정: 「전체」만 보면 같다.
  {
    id: "NC-F3",
    file: SRC.filter,
    desc: "종류 조건 제거 — 초인종 칩이 4건 (필터)",
    anchor: '(cls === "all" || n.predicted_class === cls)',
    patch: "true",
  },
  // 새 알림 — 발송 시도 행만 센다. 결함 = 조건이 빠지면 기타 소리 · 차단 행도 「새」가 되어 탭 제목이 부푼다.
  // 함정: 확인 시각 뒤에 차단 행이 없으면 결과가 같다 — 픽스처의 기타 차단 행(10시)이 9시 확인보다 뒤다.
  {
    id: "NC-E1a",
    file: SRC.unread,
    desc: "새 알림에 차단 행 섞기 — 9시 확인 뒤 기타 소리가 '새' (새 알림 표식)",
    anchor: "isSendAttempt(n) && ",
    patch: "",
  },
  // 새 알림 — 저장값이 없으면 지금으로 초기화. 결함 = 초기화가 빠지면 첫 방문에 불러온 과거 알림이 전부 「새」.
  {
    id: "NC-E1b",
    file: SRC.unread,
    desc: "저장값 없을 때 초기화 제거 — 첫 방문 새 알림 2 (새 알림 표식)",
    anchor: "  writeLastSeen(storage, nowMs)\n  return nowMs",
    patch: "  return 0",
  },
  // 새 알림 — 저장소 읽기 예외를 삼킨다. 결함 = 던지면 셸 첫 렌더(useState 초기화)가 깨진다(차단된 사이트 데이터).
  {
    id: "NC-E1c-read",
    file: SRC.unread,
    desc: "저장소 읽기 예외를 다시 던짐 — 저장실패 '오류' (새 알림 표식)",
    anchor: "    // 읽기 실패 = 저장값 없음과 같다",
    patch: '    throw new Error("NC-E1c-read")',
  },
  // 새 알림 — 저장소 쓰기 예외도 삼킨다(읽기는 삼키고 쓰기에서 터지는 변형). 같은 픽스처가 잡는다.
  {
    id: "NC-E1c-write",
    file: SRC.unread,
    desc: "저장소 쓰기 예외를 다시 던짐 — 저장실패 '오류' (새 알림 표식)",
    anchor: "    // 쓰기 실패 = 이번 화면 동안만 메모리 값으로 동작한다",
    patch: '    throw new Error("NC-E1c-write")',
  },
  // 기술 정보 접기 — 거리 센서 칸은 접힘 밖. 결함 = 칸이 접힘 안으로 들어가면 3상태 라벨이 기본 화면에서 사라져
  // 부스 리셋 뒤 「검증 안 함」(ToF 초기화 실패)을 첫 카드에서 못 본다(6.4(c) · 33.33(b)).
  {
    id: "NC-E2",
    file: SRC.card,
    desc: "거리 센서 칸을 접힘 안으로 — 기본 카드에 '검증 안 함' 없음 (기술 정보 접기)",
    anchor: "<NotificationTof tof={notification.tof_check} />",
    // 패치에 앵커 문자열이 남지 않게 필드를 대괄호로 읽는다(하네스 ③ 「앵커 잔존」 가드).
    patch: '{detailsOpen && <NotificationTof tof={notification["tof_check"]} />}',
  },
  // 기술 정보 접기 — 기본은 접힘. 결함 = 펼친 채 시작하면 신뢰도 숫자가 다시 전면에 나온다.
  {
    id: "NC-E2b",
    file: SRC.card,
    desc: "기본 펼침 — 기본 카드에 '신뢰도 90%' (기술 정보 접기)",
    anchor: "const [detailsOpen, setDetailsOpen] = useState(false)",
    patch: "const [detailsOpen, setDetailsOpen] = useState(true)",
  },
  // 오늘 보내지 않은 이유 — 0건 줄은 숨긴다. 결함 = 걸러내지 않으면 7줄이 늘 보여 실제 사유가 묻힌다.
  // 함정: 픽스처 키가 전부 1 이상이면 같다 — 사람 감지 실패 · 등록 중 = 0.
  {
    id: "NC-E4a",
    file: SRC.skipCard,
    desc: "0건 줄 숨김 제거 — '사람 감지 실패' 0건 줄 노출 (보내지 않은 이유)",
    anchor: "].filter((r) => r.count > 0)",
    patch: "].filter(() => true)",
  },
  // 오늘 보내지 않은 이유 — 카톡 실패 줄만 경고 톤 + 아이콘. 결함 = 분기가 빠지면 라벨만 남아 3중 표기 중 2개(색 · 아이콘)를 잃는다.
  {
    id: "NC-E4b",
    file: SRC.skipCard,
    desc: "카톡 실패 줄 경고 톤 · 아이콘 제거 — 위험색 · 경고 아이콘 클래스 없음 (보내지 않은 이유)",
    anchor: "{r.failure ? (",
    patch: "{false ? (",
  },
  // 기타 소리 한 줄 — 줄이는 것은 기타 소리뿐. 결함 = 화재까지 줄이면 대응 수칙이 접힌 채 지나간다.
  {
    id: "NC-E5",
    file: SRC.list,
    desc: "화재 행도 한 줄로 — '화재 시 대응 수칙' 없음 (기타 소리 축약)",
    anchor: 'collapseOther && n.predicted_class === "other" ? (',
    patch: 'collapseOther && (n.predicted_class === "other" || n.predicted_class === "fire_alarm") ? (',
  },
  // 기타 소리 한 줄 — 숨기지 않는다(33.17(f)①). 결함 = 줄이는 대신 빼면 목록에서 기타 소리가 사라진다.
  {
    id: "NC-E5b",
    file: SRC.list,
    desc: "기타 소리 행 숨김 — '기타 소리' · '알림 안 보냄' 없음 (33.17(f)①)",
    anchor: "<OtherRow key={n.request_id} notification={n} />",
    patch: "null",
  },
  // 자막 없음 표시 — 사진이 없으면(1차만 · 2차 처리 중) 뜨면 안 된다. 결함 = 처리 중에 「없어요」로 단정.
  {
    id: "NC-K1",
    file: SRC.card,
    desc: "사진 조건 제거(자막만 봄) — 사진 없는 카드에도 '알아들은 말이 없어요' (자막 없음 표시)",
    anchor: "{notification.media.image_url && !notification.stt && (",
    patch: "{!notification.stt && (",
  },
  {
    id: "NC-K2",
    file: SRC.card,
    desc: "문구 줄 삭제 — 사진 있음 + 자막 없음에 '알아들은 말이 없어요' 없음 (자막 없음 표시)",
    anchor: "                알아들은 말이 없어요\n",
    patch: "",
  },
  // 사진 보관 기간 — 지난 사진은 요청하지 않고 안내. 결함 = 분기가 없으면 3일 지난 카드도 재시도 6회 뒤 실패 표시.
  // 함정: 안내 문구 존재만 보면 사진과 함께 그려지는 변형을 못 잡는다 — 「크게 보기」 부재도 단언한다.
  {
    id: "NC-X1",
    file: SRC.image,
    desc: "보관 기간 분기 제거 — 2020년 사진 카드에 '크게 보기' (사진 보관 기간)",
    anchor: "if (expired) {",
    patch: "if (false) {",
  },
  // 서버 image_store 와 같은 「초과」 경계. 함정: 경계 점(정확히 72시간)을 단언하지 않으면 못 잡는다.
  {
    id: "NC-X2",
    file: SRC.meta,
    desc: "보관 기간 경계 > → >= — 정확히 72시간이 '지남' (사진 보관 기간)",
    anchor: "nowMs - t > CAPTURE_TTL_MS",
    patch: "nowMs - t >= CAPTURE_TTL_MS",
  },
  // 잘못된 시각은 지금처럼 요청해 본다. 결함 = NaN 을 지남으로 보면 시각이 깨진 행의 사진이 영영 안 보인다.
  {
    id: "NC-X3",
    file: SRC.meta,
    desc: "잘못된 시각을 지남으로 — '잘못=지남' (사진 보관 기간)",
    anchor: "!Number.isNaN(t) &&",
    patch: "Number.isNaN(t) ||",
  },
  // 초인종 등록 카드 — 진행은 글자로 전달한다(동그라미는 장식). 결함 = 글자 줄이 빠지면 개수가 색으로만 남는다.
  {
    id: "NC-R1",
    file: SRC.regCard,
    desc: "진행 글자 줄 제거 — '2번 확인 · 1번 남음' 없음 (등록 카드)",
    anchor: "{COPY.progress(status.collected, status.target)}",
    patch: "",
  },
  {
    id: "NC-R2",
    file: SRC.regCard,
    desc: "등록 중 안내 줄 제거 — '등록하는 동안에는 초인종 알림을 보내지 않아요.' 없음 (등록 카드)",
    anchor: "note = COPY.collectingNote",
    patch: "",
  },
  // 함정: 문구 존재를 부분 문자열로 보면 앞 문장만 남은 변형이 통과한다 — 텍스트 노드 완전 일치라 잡힌다.
  {
    id: "NC-R3",
    file: SRC.regCard,
    desc: "등록됨 안내에서 '노크 · 화재경보는 그대로 알려요.' 삭제 (등록 카드)",
    anchor: " 노크 · 화재경보는 그대로 알려요.",
    patch: "",
  },
  {
    id: "NC-R4",
    file: SRC.regCard,
    desc: "요청 실패 영문 기술 줄 되살림 — 'API 요청 실패 (502 …' 노출 (등록 카드)",
    anchor: "<p>{COPY.actionError}</p>\n          </div>",
    patch: '<p>{COPY.actionError}</p>\n<p className="text-caption">{actionError.message}</p>\n          </div>',
  },
  // 서버가 target 보다 많이 센 비정상 값. 결함 = 자르기가 없으면 '-2번 남음'.
  {
    id: "NC-R5",
    file: SRC.regCard,
    desc: "남은 횟수 0 자르기 제거 — 5/3 에서 '-2번 남음' (등록 카드)",
    anchor: "Math.max(target - collected, 0)",
    patch: "target - collected",
  },
  // 도움말 FAQ — 알림이 안 온 이유 문답이 빠지면 미발송 경로를 설명할 곳이 없다.
  {
    id: "NC-H1",
    file: SRC.help,
    desc: "FAQ '알림이 안 왔어요' 문답 삭제 (도움말 FAQ)",
    anchor: "  {\n    q: \"소리가 났는데 알림이 안 왔어요.\",\n    a: \"확실하지 않은 소리, 현관 앞에 사람이 없어 보인 초인종·노크 소리, 등록한 초인종과 많이 다른 소리, 알림 대상이 아닌 기타 소리는 보내지 않아요. 알림 화면에서 보내지 않은 기록과 이유를 볼 수 있고, 통계 화면의 ‘오늘 보내지 않은 이유’에서 하루 합계를 볼 수 있어요.\",\n  },\n",
    patch: "",
  },
  // 사진 보관 일 수는 상수에서 만든다. 결함 = 손 숫자. 함정: 손 숫자가 지금 상수와 같은 3이면 렌더가 같아 못 잡는다
  // (동치 변형) — 상수가 바뀐 뒤 남은 손 숫자를 7로 대리한다.
  {
    id: "NC-H2",
    file: SRC.help,
    desc: "사진 보관 일 수를 손 숫자(7)로 — FAQ 가 상수와 어긋난다 (도움말 FAQ)",
    anchor: "const TTL_DAYS = CAPTURE_TTL_HOURS / 24",
    patch: "const TTL_DAYS = 7",
  },
  // 온보딩 — 설치 직후 할 일 단계가 빠지면 알림 확인 · 등록 안내가 없다.
  {
    id: "NC-O1",
    file: SRC.onboarding,
    desc: "온보딩 '설치하고 꼭 해 주세요' 단계 삭제 (온보딩)",
    anchor: "  {\n    icon: ListChecks,\n    iconClass: \"bg-primary/10 text-primary\",\n    title: \"설치하고 꼭 해 주세요\",\n    description: [\n      \"① 초인종을 한 번 눌러 카카오톡 ‘나와의 채팅’에 알림이 오는지 확인해 주세요.\",\n      \"② 설정에서 ‘우리집 초인종’을 등록해 주세요.\",\n    ],\n  },\n",
    patch: "",
  },
  {
    id: "NC-T1",
    file: SRC.health,
    desc: "기기 행 「꺼짐」 → 「오프라인」 되돌림 — 헤더 · 요약 카드와 용어가 갈린다 (PoC-(76))",
    anchor: 'label: "꺼짐"',
    patch: 'label: "오프라인"',
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
  { fixture: "device_online", kind: "has", text: "연결됨" },
  { fixture: "device_online", kind: "lacks", text: "온라인" },
  { fixture: "device_offline", kind: "has", text: "꺼짐" },
  { fixture: "device_offline", kind: "lacks", text: "오프라인" },
  { fixture: "tof_passed", kind: "has", text: "사람 확인" },
  { fixture: "tof_rejected", kind: "has", text: "사람 없음" },
  { fixture: "tof_absent", kind: "has", text: "검증 안 함" },
  { fixture: "tof_absent", kind: "lacks", text: "사람 없음" },
  { fixture: "tof_absent", kind: "has", text: "tof_absent" },
  { fixture: "stt_conf_zero", kind: "has", text: "0%" },
  { fixture: "stt_conf_zero", kind: "lacks", text: "정보 없음" },
  // B9(사용자 결정 2026-10-21) — null 이면 신뢰도 칸을 숨긴다: 「정보 없음」 has → lacks. 자막 본문은 남는다.
  { fixture: "stt_conf_null", kind: "lacks", text: "정보 없음" },
  { fixture: "stt_conf_null", kind: "has", text: "“택배입니다”" },
  { fixture: "stt_conf_zero", kind: "has", text: "“택배입니다”" },
  { fixture: "stale_notice", kind: "has", text: "최근 상태를 불러오지 못해 마지막으로 받은 상태를 보여 드려요." },
  { fixture: "stale_notice", kind: "has", text: "마지막 확인 12초 전" },
  { fixture: "stale_boundary", kind: "has", text: "5999ms=정상" },
  { fixture: "stale_boundary", kind: "has", text: "6000ms=끊김" },
  { fixture: "stale_boundary", kind: "has", text: "첫성공전오류=끊김" },
  { fixture: "stale_boundary", kind: "has", text: "첫성공전대기=정상" },
  { fixture: "conn_labels", kind: "has", text: "온라인+끊김=서버 연결 끊김" },
  { fixture: "conn_labels", kind: "has", text: "온라인=현관 기기 연결됨" },
  { fixture: "conn_labels", kind: "has", text: "오프라인=현관 기기 꺼짐" },
  { fixture: "conn_labels", kind: "has", text: "확인중=연결 확인 중" },
  { fixture: "image_retry_delay", kind: "has", text: "실패1=10000ms" },
  { fixture: "image_retry_delay", kind: "has", text: "실패6=10000ms" },
  { fixture: "image_retry_delay", kind: "has", text: "실패7=중단" },
  { fixture: "image_retry_delay", kind: "has", text: "실패0=오류" },
  { fixture: "image_retry_url", kind: "has", text: "/captures/abc?_retry=1" },
  { fixture: "image_retry_url", kind: "has", text: "https://x.example/captures/abc?_retry=2" },
  // segments() 는 HTML 엔티티를 풀지 않는다 — 렌더 출력의 & 는 &amp; 로 나온다.
  { fixture: "image_retry_url", kind: "has", text: "/captures/abc?v=1&amp;_retry=3" },
  { fixture: "image_retry_url", kind: "has", text: "/captures/abc?_retry=4#top" },
  { fixture: "load_more_state", kind: "has", text: "요청40·받은20·더있음=불러오는 중" },
  { fixture: "load_more_state", kind: "has", text: "요청20·받은20·더없음=끝" },
  { fixture: "load_more_state", kind: "has", text: "요청100·받은100·더없음=끝" },
  { fixture: "load_more_state", kind: "has", text: "요청100·받은100·더있음=최대치" },
  { fixture: "load_more_state", kind: "has", text: "요청40·받은40·더있음=버튼" },
  { fixture: "load_more_state", kind: "has", text: "요청0=오류" },
  { fixture: "load_more_next", kind: "has", text: "다음20=40" },
  { fixture: "load_more_next", kind: "has", text: "다음80=100" },
  { fixture: "load_more_next", kind: "has", text: "다음90=100" },
  { fixture: "load_more_next", kind: "has", text: "다음100=100" },
  { fixture: "load_more_next", kind: "has", text: "다음0=오류" },
  { fixture: "load_more_next", kind: "has", text: "다음1.5=오류" },
  { fixture: "load_more_next", kind: "has", text: "최대작음=오류" },
  { fixture: "image_first_render", kind: "has", text: "크게 보기" },
  { fixture: "image_first_render", kind: "lacks", text: "사진을 불러올 수 없어요" },
  { fixture: "image_first_render_caption", kind: "has", text: "크게 보기" },
  { fixture: "image_first_render_caption", kind: "lacks", text: "사진을 불러올 수 없어요" },
  // B3 날짜
  { fixture: "detected_at", kind: "has", text: "오늘0시=오전 12:00" },
  { fixture: "detected_at", kind: "has", text: "어제2359=어제 오후 11:59" },
  { fixture: "detected_at", kind: "has", text: "어제0시=어제 오전 12:00" },
  { fixture: "detected_at", kind: "has", text: "그제2359=10월 19일 오후 11:59" },
  { fixture: "detected_at", kind: "has", text: "작년=2025년 12월 31일 오후 11:00" },
  { fixture: "detected_at", kind: "has", text: "잘못=-" },
  // B4 · 8.4 뱃지 6상태 + 읽는 순서
  { fixture: "badge_blocked", kind: "has", text: "발송 제외" },
  { fixture: "badge_blocked", kind: "lacks", text: "보내기 실패" },
  { fixture: "badge_token_fail", kind: "has", text: "보내기 실패" },
  { fixture: "badge_token_fail", kind: "lacks", text: "발송 제외" },
  { fixture: "badge_api_fail", kind: "has", text: "보내기 실패" },
  { fixture: "badge_complete", kind: "has", text: "전송 완료" },
  { fixture: "badge_processing", kind: "has", text: "2차 처리 중" },
  { fixture: "badge_partial", kind: "has", text: "2차 실패" },
  { fixture: "badge_partial", kind: "lacks", text: "전송 완료" },
  { fixture: "badge_primary_only", kind: "has", text: "1차 발송" },
  { fixture: "badge_order", kind: "has", text: "전송 완료" },
  { fixture: "badge_order", kind: "lacks", text: "2차 처리 중" },
  // B5 뱃지 클래스 실물
  { fixture: "badge_class", kind: "has", text: "text-caption" },
  { fixture: "badge_class", kind: "lacks", text: "text-xs" },
  { fixture: "badge_class", kind: "has", text: "text-foreground" },
  { fixture: "badge_class", kind: "lacks", text: "text-success" },
  // B4 카드 문장
  { fixture: "card_token_fail", kind: "has", text: "카카오톡으로 보내지 못했어요." },
  { fixture: "card_token_fail", kind: "lacks", text: "토큰 만료 때문에 알림을 보내지 않았어요." },
  { fixture: "card_token_fail", kind: "has", text: "보내기 실패" },
  { fixture: "card_blocked", kind: "has", text: "알림 대상이 아닌 소리 때문에 알림을 보내지 않았어요." },
  { fixture: "card_blocked", kind: "lacks", text: "카카오톡으로 보내지 못했어요." },
  // B10 화재 모션 창
  { fixture: "fire_window", kind: "has", text: "10분=창 안" },
  { fixture: "fire_window", kind: "has", text: "10분1ms=창 밖" },
  { fixture: "fire_window", kind: "has", text: "미래=창 안" },
  { fixture: "fire_window", kind: "has", text: "잘못=창 밖" },
  { fixture: "fire_card_old", kind: "lacks", text: "animate-shake" },
  { fixture: "fire_card_old", kind: "lacks", text: "animate-pulse-border" },
  { fixture: "fire_card_old", kind: "has", text: "border-danger" },
  { fixture: "fire_card_new", kind: "has", text: "animate-shake" },
  { fixture: "fire_card_new", kind: "has", text: "animate-pulse-border" },
  // 전역 경고 띠
  { fixture: "banner_kind", kind: "has", text: "끊김·꺼짐·실패=서버" },
  { fixture: "banner_kind", kind: "has", text: "꺼짐·실패=기기" },
  { fixture: "banner_kind", kind: "has", text: "켜짐·실패=카톡" },
  { fixture: "banner_kind", kind: "has", text: "켜짐·차단뒤실패=카톡" },
  { fixture: "banner_kind", kind: "has", text: "켜짐·보냄뒤실패=없음" },
  { fixture: "banner_kind", kind: "has", text: "켜짐·실패뒤보냄=카톡" },
  { fixture: "banner_kind", kind: "has", text: "켜짐·차단만=없음" },
  { fixture: "banner_kind", kind: "has", text: "상태모름·목록없음=없음" },
  { fixture: "banner_server", kind: "has", text: "서버와 연결이 끊겼어요" },
  // 띠 ①은 제목만(사용자 결정 2026-10-22) — 옛 데이터가 없을 때 「마지막으로 받은 상태」는 사실과 다르다.
  { fixture: "banner_server", kind: "lacks", text: "최근 상태를 불러오지 못해 마지막으로 받은 상태를 보여 드려요." },
  { fixture: "banner_kakao", kind: "has", text: "최근 알림을 카카오톡으로 보내지 못했어요" },
  { fixture: "banner_kakao", kind: "lacks", text: "토큰 만료" },
  { fixture: "banner_none", kind: "lacks", text: "서버와 연결이 끊겼어요" },
  { fixture: "banner_none", kind: "lacks", text: "최근 알림을 카카오톡으로 보내지 못했어요" },
  // 날짜 묶음 머리 · 묶음
  { fixture: "day_heading", kind: "has", text: "오늘0시=오늘" },
  { fixture: "day_heading", kind: "has", text: "어제2359=어제" },
  { fixture: "day_heading", kind: "has", text: "어제0시=어제" },
  { fixture: "day_heading", kind: "has", text: "그제2359=10월 19일" },
  { fixture: "day_heading", kind: "has", text: "작년=2025년 12월 31일" },
  { fixture: "day_heading", kind: "has", text: "잘못=-" },
  { fixture: "day_groups", kind: "has", text: "오늘=2" },
  { fixture: "day_groups", kind: "has", text: "어제=1" },
  { fixture: "day_groups", kind: "has", text: "10월 19일=1" },
  // 알림 화면 필터
  { fixture: "filter_result", kind: "has", text: "전체=4" },
  { fixture: "filter_result", kind: "has", text: "초인종=2" },
  { fixture: "filter_result", kind: "has", text: "기타=1" },
  { fixture: "filter_result", kind: "has", text: "보낸만=1" },
  { fixture: "filter_result", kind: "has", text: "초인종·보낸만=1" },
  { fixture: "filter_result", kind: "has", text: "노크·보낸만=0" },
  { fixture: "filter_result", kind: "has", text: "불러온 알림 4건 중 1건" },
  { fixture: "filter_bar", kind: "has", text: "전체" },
  { fixture: "filter_bar", kind: "has", text: "초인종" },
  { fixture: "filter_bar", kind: "has", text: "노크" },
  { fixture: "filter_bar", kind: "has", text: "화재경보" },
  { fixture: "filter_bar", kind: "has", text: "기타 소리" },
  { fixture: "filter_bar", kind: "has", text: "보낸 알림만" },
  { fixture: "filter_empty", kind: "has", text: "불러온 알림 중에는 맞는 알림이 없어요" },
  { fixture: "filter_empty", kind: "has", text: "필터 해제" },
  { fixture: "filter_empty", kind: "lacks", text: "아직 알림이 없어요" },
  // 새 알림 표식
  { fixture: "unread_count", kind: "has", text: "6시확인=2" },
  { fixture: "unread_count", kind: "has", text: "9시확인=0" },
  { fixture: "unread_count", kind: "has", text: "첫방문=0" },
  { fixture: "unread_count", kind: "has", text: "저장소없음=0" },
  { fixture: "unread_count", kind: "has", text: "저장실패=0" },
  { fixture: "unread_count", kind: "has", text: "제목2=(2) 띵동" },
  { fixture: "unread_count", kind: "has", text: "제목0=띵동 — 알림 대시보드" },
  { fixture: "card_new", kind: "has", text: "새 알림" },
  { fixture: "card_blocked", kind: "lacks", text: "새 알림" },
  // 기술 정보 접기 — 기본 접힘 · 거리 센서 칸 상시
  { fixture: "card_blocked", kind: "has", text: "자세히" },
  { fixture: "card_blocked", kind: "lacks", text: "신뢰도 90%" },
  { fixture: "card_blocked", kind: "has", text: "거리 센서" },
  { fixture: "card_blocked", kind: "has", text: "검증 안 함" },
  { fixture: "card_token_fail", kind: "has", text: "검증 안 함" },
  // 폰 폭 하단 탭
  { fixture: "bottom_nav", kind: "has", text: "홈" },
  { fixture: "bottom_nav", kind: "has", text: "알림" },
  { fixture: "bottom_nav", kind: "has", text: "통계" },
  { fixture: "bottom_nav", kind: "has", text: "설정" },
  { fixture: "bottom_nav", kind: "has", text: "도움말" },
  // 오늘 보내지 않은 이유
  { fixture: "skip_some", kind: "has", text: "오늘 보내지 않은 이유" },
  { fixture: "skip_some", kind: "has", text: "카카오톡으로 보내지 못했어요" },
  { fixture: "skip_some", kind: "lacks", text: "토큰 만료" },
  { fixture: "skip_some", kind: "lacks", text: "카카오 전송 오류" },
  { fixture: "skip_some", kind: "has", text: "알림 대상이 아닌 소리" },
  { fixture: "skip_some", kind: "has", text: "등록한 초인종과 다른 소리" },
  { fixture: "skip_some", kind: "lacks", text: "사람 감지 실패" },
  { fixture: "skip_some", kind: "lacks", text: "초인종 등록 중에 들어온 소리" },
  { fixture: "skip_some", kind: "has", text: "모두 8건" },
  { fixture: "skip_some_class", kind: "has", text: "text-danger-deep" },
  { fixture: "skip_some_class", kind: "has", text: "lucide-triangle-alert" },
  { fixture: "skip_no_fail_class", kind: "lacks", text: "text-danger-deep" },
  { fixture: "skip_no_fail_class", kind: "lacks", text: "lucide-triangle-alert" },
  { fixture: "skip_zero", kind: "has", text: "오늘은 보내지 않은 알림이 없어요." },
  { fixture: "skip_zero", kind: "lacks", text: "모두 0건" },
  // 기타 소리 한 줄
  { fixture: "list_collapse", kind: "has", text: "화재 시 대응 수칙" },
  { fixture: "list_collapse", kind: "has", text: "초인종" },
  { fixture: "list_collapse", kind: "has", text: "기타 소리" },
  { fixture: "list_collapse", kind: "has", text: "알림 안 보냄" },
  { fixture: "list_collapse", kind: "lacks", text: "알림 대상이 아닌 소리 때문에 알림을 보내지 않았어요." },
  // 자막 없음 표시 — ① 사진 있음 + 자막 없음 = 두 문장 ② 자막 있음 = 0 ③ 사진 없음 = 0
  { fixture: "card_photo_no_stt", kind: "has", text: "알아들은 말이 없어요" },
  { fixture: "card_photo_no_stt", kind: "has", text: "방문자가 말하지 않았거나, 소리가 작아 알아듣지 못했을 수 있어요." },
  { fixture: "card_photo_stt", kind: "lacks", text: "알아들은 말이 없어요" },
  { fixture: "card_photo_stt", kind: "lacks", text: "방문자가 말하지 않았거나, 소리가 작아 알아듣지 못했을 수 있어요." },
  { fixture: "card_blocked", kind: "lacks", text: "알아들은 말이 없어요" },
  { fixture: "card_blocked", kind: "lacks", text: "방문자가 말하지 않았거나, 소리가 작아 알아듣지 못했을 수 있어요." },
  // 사진 보관 기간 — ① 2020년 = 안내 문구만(사진 · 실패 문구 0) ② 2100년 = 사진 ③ 경계 · 잘못된 시각
  { fixture: "card_photo_no_stt", kind: "has", text: "보관 기간(3일)이 지나 볼 수 없어요" },
  { fixture: "card_photo_no_stt", kind: "lacks", text: "사진을 불러올 수 없어요" },
  { fixture: "card_photo_no_stt", kind: "lacks", text: "크게 보기" },
  { fixture: "card_photo_future", kind: "lacks", text: "보관 기간(3일)이 지나 볼 수 없어요" },
  { fixture: "card_photo_future", kind: "has", text: "크게 보기" },
  { fixture: "photo_expired", kind: "has", text: "72시간=보관" },
  { fixture: "photo_expired", kind: "has", text: "72시간1ms=지남" },
  { fixture: "photo_expired", kind: "has", text: "잘못=보관" },
  // 초인종 등록 카드 — ① 진행 글자 ② 등록 중 안내 ③ 등록됨 안내 ④ 실패 한 줄(영문 0) ⑤ 시간 초과 줄 · 비정상 값
  { fixture: "reg_collecting", kind: "has", text: "2번 확인 · 1번 남음" },
  { fixture: "reg_collecting", kind: "has", text: "등록하는 동안에는 초인종 알림을 보내지 않아요." },
  { fixture: "reg_collecting", kind: "lacks", text: "2/3" },
  { fixture: "reg_collecting_no_target", kind: "has", text: "0번 확인" },
  { fixture: "reg_collecting_no_target", kind: "lacks", text: "0번 확인 · 0번 남음" },
  { fixture: "reg_registered", kind: "has", text: "등록한 소리와 많이 다른 초인종 소리는 알리지 않아요. 노크 · 화재경보는 그대로 알려요." },
  { fixture: "reg_registered", kind: "lacks", text: "등록하는 동안에는 초인종 알림을 보내지 않아요." },
  { fixture: "reg_expired", kind: "has", text: "3번 중 2번 확인했어요" },
  { fixture: "reg_action_error", kind: "has", text: "요청을 처리하지 못했어요. 잠시 후 다시 눌러 주세요." },
  { fixture: "reg_action_error", kind: "lacks", text: "API 요청 실패 (502 Bad Gateway): /api/v1/registration/start" },
  { fixture: "reg_over", kind: "has", text: "5번 확인 · 0번 남음" },
  { fixture: "reg_over", kind: "lacks", text: "5번 확인 · -2번 남음" },
  // 도움말 FAQ — 문답 전부 완전 일치(기존 1 · 3번 무변경 포함) + 다른 화면 문구와 같은 글자 · 상수와 같은 일 수
  // 온보딩 단계 — 1 ~ 3단계 무변경 + 4단계 제목 · 두 줄
  { fixture: "help", kind: "has", text: "알림은 얼마나 빨리 오나요?" },
  { fixture: "help", kind: "has", text: "알림이 갈 때는 보통 5초 이내에 1차 알림이, 15초 이내에 사진·자막이 담긴 2차 알림이 도착해요." },
  { fixture: "help", kind: "has", text: "사진과 음성은 어떻게 보이나요?" },
  { fixture: "help", kind: "has", text: "2차 알림이 갈 때는 현관 카메라가 찍은 사진과, 방문자가 한 말을 글자로 바꾼 자막이 알림 카드에 함께 표시돼요. 알아들은 말이 없으면 ‘알아들은 말이 없어요’라고 표시돼요." },
  { fixture: "help", kind: "has", text: "사진은 언제까지 볼 수 있나요?" },
  { fixture: "help", kind: "has", text: "사진은 3일 동안 볼 수 있어요. 3일이 지나면 ‘보관 기간(3일)이 지나 볼 수 없어요’로 바뀌어요. 카카오톡 사진도 3일이 지나면 보이지 않을 수 있어요." },
  { fixture: "help", kind: "has", text: "카카오톡 알림은 어디로 오나요?" },
  { fixture: "help", kind: "has", text: "카카오톡 ‘나와의 채팅’ 방으로 와요. 휴대폰 잠금 화면에는 알림이 뜨지 않을 수 있어서, 그 방을 열어 두거나 이 화면을 함께 확인해 주세요." },
  { fixture: "help", kind: "has", text: "소리가 났는데 알림이 안 왔어요." },
  { fixture: "help", kind: "has", text: "확실하지 않은 소리, 현관 앞에 사람이 없어 보인 초인종·노크 소리, 등록한 초인종과 많이 다른 소리, 알림 대상이 아닌 기타 소리는 보내지 않아요. 알림 화면에서 보내지 않은 기록과 이유를 볼 수 있고, 통계 화면의 ‘오늘 보내지 않은 이유’에서 하루 합계를 볼 수 있어요." },
  { fixture: "help", kind: "has", text: "화면이 잘 안 보여요." },
  { fixture: "help", kind: "has", text: "설정 화면에서 ‘글씨 크게’와 ‘어두운 화면’을 켜면 더 편하게 볼 수 있어요." },
  { fixture: "help_copy_match", kind: "has", text: "F3일수=일치" },
  { fixture: "help_copy_match", kind: "has", text: "F3만료문구=일치" },
  { fixture: "help_copy_match", kind: "has", text: "F4카드문구=일치" },
  { fixture: "onboarding_steps", kind: "has", text: "띵동에 오신 것을 환영합니다" },
  { fixture: "onboarding_steps", kind: "has", text: "현관에서 나는 소리를 자동으로 감지해, 휴대폰과 이 화면으로 알려드려요." },
  { fixture: "onboarding_steps", kind: "has", text: "세 가지 소리를 구분해요" },
  { fixture: "onboarding_steps", kind: "has", text: "초인종, 노크, 화재경보를 구분해 표시합니다." },
  { fixture: "onboarding_steps", kind: "has", text: "화재경보는 더 크게 알려요" },
  { fixture: "onboarding_steps", kind: "has", text: "화재경보는 빨간색으로 강조하고, 대응 수칙을 함께 보여드려요." },
  { fixture: "onboarding_steps", kind: "has", text: "설치하고 꼭 해 주세요" },
  { fixture: "onboarding_steps", kind: "has", text: "① 초인종을 한 번 눌러 카카오톡 ‘나와의 채팅’에 알림이 오는지 확인해 주세요." },
  { fixture: "onboarding_steps", kind: "has", text: "② 설정에서 ‘우리집 초인종’을 등록해 주세요." },
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
