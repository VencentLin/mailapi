import { http } from './http'

export type ApiKeyStatus = 'active' | 'disabled' | 'expired'

export interface ApiKey {
  id: number
  user_id: number
  name: string
  key_prefix: string
  scopes: string[]
  status: ApiKeyStatus
  expires_at: string | null
  last_used_at: string | null
  created_at: string
  updated_at: string
}

export interface ApiKeyCreate {
  name: string
  scopes?: string[]
  expires_at?: string | null
  user_id?: number | null
}

export interface ApiKeyCreateResponse {
  key: ApiKey
  api_key: string
}

export function fetchApiKeys() {
  return http.get<ApiKey[]>('/api/api-keys')
}

export function createApiKey(payload: ApiKeyCreate) {
  return http.post<ApiKeyCreateResponse>('/api/api-keys', payload)
}

export function disableApiKey(id: number) {
  return http.delete<void>(`/api/api-keys/${id}`)
}
