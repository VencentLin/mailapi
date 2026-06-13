<template>
  <section class="web-mail-page">
    <header class="page-header">
      <h2>网页取件</h2>
      <el-button :icon="Refresh" :loading="accountsLoading" @click="loadAccounts">
        刷新邮箱
      </el-button>
    </header>

    <p v-if="error" class="error-msg">{{ error }}</p>

    <el-form class="fetch-form" :model="form" label-width="110px">
      <el-form-item label="托管邮箱">
        <el-select
          v-model="selectedAccountId"
          clearable
          filterable
          placeholder="可直接选择已托管邮箱"
          @change="handleAccountSelect"
        >
          <el-option
            v-for="account in accounts"
            :key="account.id"
            :label="account.email"
            :value="account.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="邮箱">
        <el-input v-model="form.email" placeholder="outlook@example.com" />
      </el-form-item>
      <el-form-item label="邮箱夹">
        <el-segmented v-model="form.mailbox" :options="['INBOX', 'Junk']" />
      </el-form-item>
      <el-form-item label="取件模式">
        <el-radio-group v-model="mode">
          <el-radio-button label="latest">最新一封</el-radio-button>
          <el-radio-button label="all">全部邮件</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="mode === 'all'" label="数量限制">
        <el-input-number v-model="form.limit" :min="1" :max="100" />
      </el-form-item>
      <el-form-item label="Client ID">
        <el-input v-model="form.client_id" placeholder="已托管邮箱可留空" />
      </el-form-item>
      <el-form-item label="Refresh Token">
        <el-input
          v-model="form.refresh_token"
          type="textarea"
          :rows="4"
          placeholder="已托管邮箱可留空"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" :loading="loading" @click="handleFetch">
          取件
        </el-button>
      </el-form-item>
    </el-form>

    <section v-if="result" class="result-block">
      <el-descriptions :column="4" border>
        <el-descriptions-item label="协议">{{ result.protocol }}</el-descriptions-item>
        <el-descriptions-item label="邮箱状态">
          {{ accountStatusLabel(result.mail_account_status) }}
        </el-descriptions-item>
        <el-descriptions-item label="邮件数量">{{ result.data.length }}</el-descriptions-item>
        <el-descriptions-item label="Trace ID">{{ result.trace_id }}</el-descriptions-item>
      </el-descriptions>

      <el-table :data="result.data" class="mail-table" empty-text="暂无邮件" stripe>
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="mail-preview">
              <div class="mail-preview-title">{{ row.subject || '(无主题)' }}</div>
              <pre>{{ previewBody(row) }}</pre>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="sender" label="发件人" min-width="190" show-overflow-tooltip />
        <el-table-column prop="subject" label="主题" min-width="240" show-overflow-tooltip />
        <el-table-column prop="received_at" label="时间" min-width="180" />
        <el-table-column prop="verification_code" label="验证码" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.verification_code" type="success" size="small">
              {{ row.verification_code }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </section>
</template>

<script setup lang="ts">
import { Refresh, Search } from '@element-plus/icons-vue'
import { onMounted, reactive, ref } from 'vue'

import { ApiError } from '@/api/http'
import {
  type MailFetchRequest,
  type MailFetchResponse,
  type MailItem,
  fetchAllMail,
  fetchLatestMail,
} from '@/api/mailFetch'
import { type MailAccount, fetchMailAccounts } from '@/api/mailAccounts'

const accounts = ref<MailAccount[]>([])
const selectedAccountId = ref<number | null>(null)
const accountsLoading = ref(false)
const loading = ref(false)
const error = ref('')
const result = ref<MailFetchResponse | null>(null)
const mode = ref<'latest' | 'all'>('latest')

const form = reactive({
  email: '',
  client_id: '',
  refresh_token: '',
  mailbox: 'INBOX',
  limit: 10,
})

function handleAccountSelect(value: number | string | null) {
  const accountId = typeof value === 'number' ? value : Number(value)
  const account = accounts.value.find((item) => item.id === accountId)
  if (!account) return
  form.email = account.email
  form.client_id = ''
  form.refresh_token = ''
}

function payload(): MailFetchRequest {
  return {
    email: form.email,
    client_id: form.client_id || undefined,
    refresh_token: form.refresh_token || undefined,
    mailbox: form.mailbox,
    limit: mode.value === 'all' ? form.limit : 1,
  }
}

function previewBody(row: MailItem) {
  const body = row.text || row.html || ''
  return body.trim() || '(无正文预览)'
}

function accountStatusLabel(status: string) {
  const labels: Record<string, string> = {
    existing_user: '已托管用户邮箱',
    existing_public: '已托管公共邮箱',
    auto_created_user: '已自动托管到当前用户',
    auto_created_public: '已自动托管到公共池',
  }
  return labels[status] || status
}

async function loadAccounts() {
  accountsLoading.value = true
  try {
    accounts.value = await fetchMailAccounts()
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '加载托管邮箱失败'
  } finally {
    accountsLoading.value = false
  }
}

async function handleFetch() {
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value =
      mode.value === 'latest'
        ? await fetchLatestMail(payload())
        : await fetchAllMail(payload())
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '网页取件失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadAccounts)
</script>

<style scoped>
.web-mail-page {
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
  color: #1f2933;
  font-size: 20px;
  font-weight: 650;
}

.fetch-form {
  max-width: 760px;
}

.result-block {
  margin-top: 24px;
}

.mail-table {
  margin-top: 16px;
}

.mail-preview {
  padding: 12px 18px;
}

.mail-preview-title {
  margin-bottom: 10px;
  color: #1f2933;
  font-weight: 650;
}

.mail-preview pre {
  max-height: 360px;
  margin: 0;
  overflow: auto;
  color: #303133;
  font-family: Consolas, 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.error-msg {
  color: #f56c6c;
  margin-bottom: 16px;
}
</style>
