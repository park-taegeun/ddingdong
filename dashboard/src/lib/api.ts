// ⭐ Phase 2: 실제 서버 API 연동 단일 지점 ⭐
// 대시보드의 모든 서버 호출은 이 파일의 두 헬퍼(apiGet 조회 / apiSend 쓰기)를 통해서만 나간다.
// 호출 URL = `${VITE_API_BASE_URL}${path}` = 상대경로 `/api/v1/...` → dev 는 vite proxy 가
// Flask(5000)로 포워딩(CORS 우회). 반드시 상대경로여야 proxy 를 타므로 full URL 금지.
// (Phase 1 mock 은 mock-data.ts 에 참고용으로 보존 — 런타임 토글은 두지 않음(YAGNI).)

import type { NotificationItem } from "@/types/notification"
import type { NotificationsApiResponse } from "@/types/api"
import type { RegistrationStatus } from "@/types/registration"
import type { StatsResponse } from "@/types/stats"

// 끝 슬래시 방어 — base 가 "/api/v1/" 여도 "//notifications" 가 되지 않게.
const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "")
const DASHBOARD_TOKEN = import.meta.env.VITE_DASHBOARD_TOKEN

// GET 공용 헬퍼: Bearer 인증 + 상태 코드 검증 + JSON 파싱 (DRY).
async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${DASHBOARD_TOKEN}` },
  })
  if (!res.ok) {
    throw new Error(`API 요청 실패 (${res.status} ${res.statusText}): ${path}`)
  }
  return (await res.json()) as T
}

export async function fetchNotifications(): Promise<NotificationItem[]> {
  const json = await apiGet<NotificationsApiResponse>("/notifications")
  // cursor 메타(next_cursor/has_more)는 현재 전체 폴링이라 미사용 — 목록만 추출.
  return json.notifications
}

export function fetchStats(): Promise<StatsResponse> {
  return apiGet<StatsResponse>("/stats")
}

// 쓰기 공용 헬퍼: apiGet 과 같은 Bearer 인증. 실패 시 서버 본문 {"error": {"message"}} 를
// 읽을 수 있으면 그 문구를 에러에 싣고, 못 읽으면 상태 코드만 싣는다.
async function apiSend<T>(method: "POST" | "DELETE", path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Authorization: `Bearer ${DASHBOARD_TOKEN}` }
  if (body !== undefined) headers["Content-Type"] = "application/json"
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) {
    let serverMessage: unknown
    try {
      serverMessage = ((await res.json()) as { error?: { message?: unknown } }).error?.message
    } catch {
      // JSON 이 아닌 실패 응답 — 상태 코드만 남긴다.
    }
    const status = `API 요청 실패 (${res.status} ${res.statusText}): ${path}`
    throw new Error(typeof serverMessage === "string" ? `${status} — ${serverMessage}` : status)
  }
  return (await res.json()) as T
}

export function fetchRegistration(): Promise<RegistrationStatus> {
  return apiGet<RegistrationStatus>("/registration")
}

export function startRegistration(
  targetCount: number,
  expiresInSeconds: number,
): Promise<RegistrationStatus> {
  return apiSend<RegistrationStatus>("POST", "/registration/start", {
    target_count: targetCount,
    expires_in_seconds: expiresInSeconds,
  })
}

export function clearRegistration(): Promise<RegistrationStatus> {
  return apiSend<RegistrationStatus>("DELETE", "/registration")
}
