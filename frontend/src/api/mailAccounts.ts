import { http } from './http'

export type MailAccountOwnerType = 'user' | 'public'
export type MailAccountStatus = 'active' | 'disabled' | 'invalid'

export interface MailAccount {
  id: number
  email: string
  client_id: string
  owner_type: MailAccountOwnerType
  owner_user_id: number | null
  status: MailAccountStatus
  default_proxy: string | null
  last_protocol: string | null
  last_success_at: string | null
  last_error_code: string | null
  remark: string | null
  created_by_user_id: number | null
  created_via: string
  created_at: string
  updated_at: string
  can_claim: boolean
  can_view_credentials: boolean
}

export interface MailAccountCreate {
  email: string
  client_id: string
  refresh_token: string
  owner_type?: MailAccountOwnerType
  owner_user_id?: number | null
  status?: MailAccountStatus
  default_proxy?: string | null
  remark?: string | null
}

export interface MailAccountUpdate {
  owner_type?: MailAccountOwnerType
  owner_user_id?: number | null
  status?: MailAccountStatus
  default_proxy?: string | null
  remark?: string | null
}

export interface MailAccountImportRequest {
  text: string
  owner_type?: MailAccountOwnerType
  owner_user_id?: number | null
  remark?: string | null
}

export interface MailAccountImportItem {
  line: number
  email: string | null
  status: 'created' | 'skipped' | 'failed'
  message: string
  account_id: number | null
}

export interface MailAccountImportResponse {
  created: number
  skipped: number
  failed: number
  items: MailAccountImportItem[]
}

export interface MailAccountCredentials {
  client_id: string
  refresh_token: string
}

export interface MailAccountTestResponse {
  code: string
  protocol: string
  message_count: number
  trace_id: string
}

export interface MailAccountReauthorizeUrlResponse {
  auth_url: string
  expires_in: number
}

export interface MailAccountFilters {
  email?: string
  owner_type?: MailAccountOwnerType | ''
  owner_user_id?: number | null
  status?: MailAccountStatus | ''
}

function query(filters: MailAccountFilters = {}) {
  const params = new URLSearchParams()
  if (filters.email) params.set('email', filters.email)
  if (filters.owner_type) params.set('owner_type', filters.owner_type)
  if (filters.owner_user_id) params.set('owner_user_id', String(filters.owner_user_id))
  if (filters.status) params.set('status', filters.status)
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

export function fetchMailAccounts(filters: MailAccountFilters = {}) {
  return http.get<MailAccount[]>(`/api/mail-accounts${query(filters)}`)
}

export function createMailAccount(payload: MailAccountCreate) {
  return http.post<MailAccount>('/api/mail-accounts', payload)
}

export function importMailAccounts(payload: MailAccountImportRequest) {
  return http.post<MailAccountImportResponse>('/api/mail-accounts/import', payload)
}

export function claimMailAccount(id: number) {
  return http.post<MailAccount>(`/api/mail-accounts/${id}/claim`)
}

export function updateMailAccount(id: number, payload: MailAccountUpdate) {
  return http.patch<MailAccount>(`/api/mail-accounts/${id}`, payload)
}

export function disableMailAccount(id: number) {
  return http.delete<void>(`/api/mail-accounts/${id}`)
}

export function permanentlyDeleteMailAccount(id: number) {
  return http.delete<void>(`/api/mail-accounts/${id}/permanent`)
}

export function fetchMailAccountCredentials(id: number) {
  return http.get<MailAccountCredentials>(`/api/mail-accounts/${id}/credentials`)
}

export function updateMailAccountCredentials(id: number, payload: Partial<MailAccountCredentials>) {
  return http.patch<MailAccount>(`/api/mail-accounts/${id}/credentials`, payload)
}

export function createMailAccountReauthorizeUrl(id: number) {
  return http.post<MailAccountReauthorizeUrlResponse>(
    `/api/mail-accounts/${id}/reauthorize-url`,
  )
}

export function testFetchMailAccount(id: number, mailbox = 'INBOX') {
  return http.post<MailAccountTestResponse>(
    `/api/mail-accounts/${id}/test-fetch?mailbox=${encodeURIComponent(mailbox)}`,
  )
}

export function clearMailAccount(id: number, mailbox = 'INBOX') {
  return http.post<MailAccountTestResponse>(
    `/api/mail-accounts/${id}/clear?mailbox=${encodeURIComponent(mailbox)}`,
  )
}
