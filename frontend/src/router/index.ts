import { createRouter, createWebHistory } from 'vue-router'

import AppLayout from '@/layouts/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'
import DashboardView from '@/views/DashboardView.vue'
import LoginView from '@/views/LoginView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { public: true },
    },
    {
      path: '/',
      component: AppLayout,
      children: [
        { path: '', name: 'dashboard', component: DashboardView },
        {
          path: 'users',
          name: 'users',
          component: () => import('@/views/users/UserListView.vue'),
        },
        {
          path: 'mail-accounts',
          name: 'mail-accounts',
          component: () => import('@/views/mail/MailAccountListView.vue'),
        },
        {
          path: 'api-keys',
          name: 'api-keys',
          component: () => import('@/views/apiKeys/ApiKeyListView.vue'),
        },
        {
          path: 'verification-code',
          name: 'verification-code',
          component: () => import('@/views/verification/VerificationCodeView.vue'),
        },
        {
          path: 'logs/mail-fetch',
          name: 'logs-mail-fetch',
          component: () => import('@/views/logs/MailFetchLogView.vue'),
        },
      ],
    },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()
  let hasRestoredUser = true

  if (auth.isAuthenticated && !auth.username) {
    hasRestoredUser = await auth.loadMe()
  }

  if (to.meta.public) {
    if (auth.isAuthenticated && hasRestoredUser) {
      return next({ name: 'dashboard' })
    }
    return next()
  }

  if (!auth.isAuthenticated || !hasRestoredUser) {
    return next({ name: 'login', query: { redirect: to.fullPath } })
  }

  next()
})

export default router
