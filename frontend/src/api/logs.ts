import { http } from './http'

export interface MailFetchLog {
  id: number
  trace_id: string
  user_id: number | null
  api_key_id: number | null
  mail_account_id: number | null
  email: string
  mailbox: string
  operation: string
  source_protocol: string | null
  status: string
  error_code: string | null
  error_message: string | null
  duration_ms: number | null
  created_at: string
  updated_at: string
}

export interface MailFetchLogFilters {
  email?: string
  status?: string
}

export function fetchMailFetchLogs(filters: MailFetchLogFilters = {}) {
  const params = new URLSearchParams()
  if (filters.email) params.set('email', filters.email)
  if (filters.status) params.set('status', filters.status)
  const qs = params.toString()
  return http.get<MailFetchLog[]>(`/api/logs/mail-fetch${qs ? `?${qs}` : ''}`)
}
