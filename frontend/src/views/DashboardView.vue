<template>
  <section class="dashboard">
    <header class="page-header">
      <h1>MailAPI 控制台</h1>
      <el-button :icon="Refresh" :loading="loading" @click="loadMetrics">刷新</el-button>
    </header>

    <p v-if="error" class="error-msg">{{ error }}</p>

    <section class="metrics" v-loading="loading">
      <article v-for="metric in visibleMetrics" :key="metric.label">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
      </article>
    </section>

    <section class="section-block">
      <header class="section-header">
        <h2>最近错误</h2>
      </header>
      <el-table :data="metrics?.recent_errors || []" empty-text="暂无错误记录" stripe>
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="error_code" label="错误码" min-width="160" />
        <el-table-column prop="error_message" label="错误信息" min-width="220" show-overflow-tooltip />
        <el-table-column prop="trace_id" label="Trace ID" min-width="180" show-overflow-tooltip />
        <el-table-column prop="created_at" label="时间" min-width="180" />
      </el-table>
    </section>
  </section>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue'
import { computed, onMounted, ref } from 'vue'

import { type DashboardMetrics, fetchDashboardMetrics } from '@/api/dashboard'
import { ApiError } from '@/api/http'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const metrics = ref<DashboardMetrics | null>(null)
const loading = ref(false)
const error = ref('')

const visibleMetrics = computed(() => {
  const data = metrics.value
  const base = [
    { label: '我的邮箱', value: data?.my_mail_accounts ?? 0 },
    { label: '公共池', value: data?.public_mail_accounts ?? 0 },
    { label: '今日取件', value: data?.today_fetches ?? 0 },
    { label: '失败次数', value: data?.today_failed_fetches ?? 0 },
  ]
  if (!auth.isAdmin) return base
  return [
    ...base,
    { label: '全局用户', value: data?.global_users ?? 0 },
    { label: '全局邮箱', value: data?.global_mail_accounts ?? 0 },
    { label: 'API Key', value: data?.global_api_keys ?? 0 },
    { label: '全局失败', value: data?.global_today_failed_fetches ?? 0 },
  ]
})

async function loadMetrics() {
  loading.value = true
  error.value = ''
  try {
    metrics.value = await fetchDashboardMetrics()
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '加载工作台失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadMetrics)
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.page-header,
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-header h1,
.section-header h2 {
  margin: 0;
  color: #1f2933;
  font-size: 20px;
  font-weight: 650;
}

.section-header h2 {
  font-size: 16px;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 14px;
}

.metrics article {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 88px;
  padding: 16px;
  border: 1px solid #d9e2ec;
  border-radius: 8px;
  background: #ffffff;
}

.metrics span {
  color: #5c6b7a;
  font-size: 13px;
}

.metrics strong {
  color: #1f2933;
  font-size: 28px;
}

.section-block {
  margin-top: 24px;
}

.error-msg {
  color: #f56c6c;
  margin-bottom: 16px;
}
</style>
