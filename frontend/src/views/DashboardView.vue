<template>
  <main class="dashboard">
    <header class="topbar">
      <h1>MailAPI 控制台</h1>
      <el-button @click="handleLogout">退出</el-button>
    </header>

    <section class="metrics">
      <article>
        <span>我的邮箱</span>
        <strong>0</strong>
      </article>
      <article>
        <span>公共池</span>
        <strong>0</strong>
      </article>
      <article>
        <span>今日取件</span>
        <strong>0</strong>
      </article>
      <article>
        <span>失败次数</span>
        <strong>0</strong>
      </article>
    </section>
  </main>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

function handleLogout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: #f6f8fb;
}

.topbar {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid #d9e2ec;
  background: #ffffff;
}

.topbar h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 650;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  padding: 24px;
}

.metrics article {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 18px;
  border: 1px solid #d9e2ec;
  border-radius: 8px;
  background: #ffffff;
}

.metrics span {
  color: #5c6b7a;
  font-size: 14px;
}

.metrics strong {
  color: #1f2933;
  font-size: 28px;
}
</style>
