import { http } from './http'

export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface UserPublic {
  id: number
  username: string
  email: string
  role: 'admin' | 'user'
  status: 'active' | 'disabled'
}

export function login(payload: LoginRequest): Promise<TokenResponse> {
  return http.post<TokenResponse>('/auth/login', payload)
}

export function fetchMe(): Promise<UserPublic> {
  return http.get<UserPublic>('/auth/me')
}
