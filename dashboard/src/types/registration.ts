// 초인종 등록 상태 본문 (server/app/registration.py status() 와 1:1).
// 시각은 서버가 KST ISO 문자열로 내고, 값이 없으면 null 이다.

export type RegistrationState = "none" | "collecting" | "registered" | "expired"

export interface RegistrationStatus {
  state: RegistrationState
  collected: number
  target: number | null
  started_at: string | null
  expires_at: string | null
  registered_at: string | null
}
