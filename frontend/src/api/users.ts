import { http } from './http'

export interface UserPublic {
  id: number
  username: string
  email: string
  role: 'admin' | 'user'
  status: 'active' | 'disabled'
}

export interface UserCreate {
  username: string
  email: string
  password: string
  role?: 'admin' | 'user'
  status?: 'active' | 'disabled'
}

export interface UserUpdate {
  username?: string
  email?: string
  password?: string
  role?: 'admin' | 'user'
  status?: 'active' | 'disabled'
}

export function fetchUsers(
  offset = 0,
  limit = 20,
): Promise<UserPublic[]> {
  return http.get<UserPublic[]>(`/api/users?offset=${offset}&limit=${limit}`)
}

export function createUser(payload: UserCreate): Promise<UserPublic> {
  return http.post<UserPublic>('/api/users', payload)
}

export function updateUser(userId: number, payload: UserUpdate): Promise<UserPublic> {
  return http.patch<UserPublic>(`/api/users/${userId}`, payload)
}
