import { defineStore } from 'pinia'

import { type UserPublic, fetchMe, login as loginApi } from '@/api/auth'
import { ApiError } from '@/api/http'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: (localStorage.getItem('accessToken') || '') as string,
    username: '' as string,
    role: 'user' as 'admin' | 'user',
  }),
  getters: {
    isAuthenticated: (state) => state.token.length > 0,
    isAdmin: (state) => state.role === 'admin',
  },
  actions: {
    setUser(user: UserPublic) {
      this.username = user.username
      this.role = user.role
    },

    async login(username: string, password: string) {
      const resp = await loginApi({ username, password })
      this.token = resp.access_token
      localStorage.setItem('accessToken', resp.access_token)
      const me = await fetchMe()
      this.setUser(me)
    },

    async loadMe() {
      if (!this.token) return
      try {
        const me = await fetchMe()
        this.setUser(me)
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          this.logout()
        }
      }
    },

    logout() {
      this.token = ''
      this.username = ''
      this.role = 'user'
      localStorage.removeItem('accessToken')
    },
  },
})
