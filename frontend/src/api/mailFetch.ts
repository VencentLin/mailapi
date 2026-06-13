import { http } from './http'

export interface MailFetchRequest {
  email: string
  client_id?: string
  refresh_token?: string
  mailbox?: string
  limit?: number
}

export interface MailItem {
  id: string | null
  send: string
  sender: string
  subject: string
  text: string
  html: string | null
  date: string | null
  received_at: string | null
  verification_code: string | null
}

export interface MailFetchResponse {
  code: string
  data: MailItem[]
  trace_id: string
  protocol: string
  mail_account_status: string
}

export function fetchLatestMail(payload: MailFetchRequest) {
  return http.post<MailFetchResponse>('/api/mail_new', payload)
}

export function fetchAllMail(payload: MailFetchRequest) {
  return http.post<MailFetchResponse>('/api/mail_all', payload)
}
