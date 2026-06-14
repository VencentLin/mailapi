<template>
  <section class="fetch-log-page">
    <header class="page-header">
      <h2>取件日志</h2>
      <el-button :icon="Refresh" :loading="loading" @click="loadLogs">刷新</el-button>
    </header>

    <el-form class="filter-bar" :model="filters" inline>
      <el-form-item label="邮箱">
        <el-input v-model="filters.email" clearable placeholder="email@example.com" />
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="filters.status" clearable placeholder="全部" style="width: 130px">
          <el-option label="成功" value="success" />
          <el-option label="失败" value="failed" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="loadLogs">筛选</el-button>
      </el-form-item>
    </el-form>

    <p v-if="error" class="error-msg">{{ error }}</p>

    <el-table :data="logs" v-loading="loading" empty-text="暂无取件记录" stripe>
      <el-table-column prop="email" label="邮箱" min-width="190" />
      <el-table-column prop="operation" label="操作" width="140" />
      <el-table-column prop="mailbox" label="邮箱夹" width="100" />
      <el-table-column prop="source_protocol" label="协议" width="90" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
            {{ row.status === 'success' ? '成功' : '失败' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="error_code" label="错误码" min-width="160" />
      <el-table-column prop="error_message" label="错误信息" min-width="220" show-overflow-tooltip />
      <el-table-column prop="duration_ms" label="耗时(ms)" width="110" />
      <el-table-column prop="trace_id" label="Trace ID" min-width="180" show-overflow-tooltip />
      <el-table-column prop="created_at" label="时间" min-width="180" />
    </el-table>
  </section>
</template>

<script setup lang="ts">
import { Refresh, Search } from '@element-plus/icons-vue'
import { onMounted, reactive, ref } from 'vue'

import { ApiError } from '@/api/http'
import { type MailFetchLog, fetchMailFetchLogs } from '@/api/logs'

const logs = ref<MailFetchLog[]>([])
const loading = ref(false)
const error = ref('')
const filters = reactive({ email: '', status: '' })

async function loadLogs() {
  loading.value = true
  error.value = ''
  try {
    logs.value = await fetchMailFetchLogs(filters)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '加载取件日志失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadLogs)
</script>

<style scoped>
.fetch-log-page {
  padding: 0;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 650;
}

.filter-bar {
  margin-bottom: 12px;
}

.error-msg {
  color: #f56c6c;
  margin-bottom: 16px;
}
</style>
