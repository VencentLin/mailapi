<template>
  <section class="verification-page">
    <header class="page-header">
      <h2>验证码取件测试</h2>
    </header>

    <p v-if="error" class="error-msg">{{ error }}</p>

    <el-form class="verification-form" :model="form" label-width="120px">
      <el-form-item label="邮箱">
        <el-input v-model="form.email" placeholder="outlook@example.com" />
      </el-form-item>
      <el-form-item label="邮箱夹">
        <el-segmented v-model="form.mailbox" :options="['INBOX', 'Junk']" />
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
      <el-form-item label="发件人">
        <el-input v-model="form.sender" clearable />
      </el-form-item>
      <el-form-item label="主题关键词">
        <el-input v-model="form.subject_keyword" clearable />
      </el-form-item>
      <el-form-item label="正文关键词">
        <el-input v-model="form.body_keyword" clearable />
      </el-form-item>
      <el-form-item label="时间窗口">
        <el-input-number v-model="form.since_minutes" :min="1" :max="1440" />
      </el-form-item>
      <el-form-item label="验证码正则">
        <el-input v-model="form.regex" placeholder="默认提取 4-8 位数字" />
      </el-form-item>
      <el-form-item>
        <el-checkbox v-model="form.delete_after_fetch">成功后清空邮箱夹</el-checkbox>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" :loading="loading" @click="handleFetch">
          开始取码
        </el-button>
      </el-form-item>
    </el-form>

    <section v-if="result" class="result-block">
      <div class="result-code">{{ result.verification_code }}</div>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="协议">{{ result.source_protocol }}</el-descriptions-item>
        <el-descriptions-item label="邮箱状态">
          {{ result.mail_account_status }}
        </el-descriptions-item>
        <el-descriptions-item label="发件人">
          {{ result.matched_email.sender }}
        </el-descriptions-item>
        <el-descriptions-item label="主题">
          {{ result.matched_email.subject }}
        </el-descriptions-item>
        <el-descriptions-item label="Trace ID" :span="2">
          {{ result.trace_id }}
        </el-descriptions-item>
      </el-descriptions>
    </section>
  </section>
</template>

<script setup lang="ts">
import { Search } from '@element-plus/icons-vue'
import { reactive, ref } from 'vue'

import { ApiError } from '@/api/http'
import {
  type VerificationCodeResponse,
  fetchVerificationCode,
} from '@/api/verification'

const loading = ref(false)
const error = ref('')
const result = ref<VerificationCodeResponse | null>(null)

const form = reactive({
  email: '',
  client_id: '',
  refresh_token: '',
  mailbox: 'INBOX',
  sender: '',
  subject_keyword: '',
  body_keyword: '',
  since_minutes: null as number | null,
  regex: '',
  delete_after_fetch: false,
})

async function handleFetch() {
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await fetchVerificationCode({
      ...form,
      client_id: form.client_id || undefined,
      refresh_token: form.refresh_token || undefined,
      sender: form.sender || undefined,
      subject_keyword: form.subject_keyword || undefined,
      body_keyword: form.body_keyword || undefined,
      regex: form.regex || undefined,
    })
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '取码失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.verification-page {
  max-width: 960px;
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 650;
}

.verification-form {
  max-width: 720px;
}

.result-block {
  margin-top: 24px;
}

.result-code {
  margin-bottom: 16px;
  color: #0f766e;
  font-size: 32px;
  font-weight: 700;
  letter-spacing: 0;
}

.error-msg {
  color: #f56c6c;
  margin-bottom: 16px;
}
</style>
