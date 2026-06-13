import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: '',
    username: '',
    role: 'user' as 'admin' | 'user',
  }),
  getters: {
    isAuthenticated: (state) => state.token.length > 0,
    isAdmin: (state) => state.role === 'admin',
  },
})
