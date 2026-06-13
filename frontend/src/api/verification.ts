import { http } from './http'

export interface VerificationCodeRequest {
  email: string
  client_id?: string
  refresh_token?: string
  mailbox?: string
  sender?: string
  subject_keyword?: string
  body_keyword?: string
  since_minutes?: number | null
  regex?: string
  delete_after_fetch?: boolean
  user_token?: string
}

export interface VerificationCodeResponse {
  code: string
  verification_code: string
  matched_email: {
    id: string
    sender: string
    subject: string
    text: string
    received_at: string | null
    verification_code: string | null
  }
  source_protocol: string
  mail_account_status: string
  trace_id: string
}

export function fetchVerificationCode(payload: VerificationCodeRequest) {
  return http.post<VerificationCodeResponse>('/api/verification-code', payload)
}
