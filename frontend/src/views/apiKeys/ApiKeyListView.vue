<template>
  <section class="api-key-page">
    <header class="page-header">
      <h2>API Key</h2>
      <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">
        新建 Key
      </el-button>
    </header>

    <el-alert
      v-if="plainTextKey"
      class="key-alert"
      title="明文 API Key 只会显示一次"
      type="success"
      show-icon
      :closable="false"
    >
      <el-input v-model="plainTextKey" readonly>
        <template #append>
          <el-button :icon="DocumentCopy" @click="copyKey" />
        </template>
      </el-input>
    </el-alert>

    <p v-if="error" class="error-msg">{{ error }}</p>

    <el-table :data="keys" v-loading="loading" empty-text="暂无 API Key" stripe>
      <el-table-column prop="name" label="名称" min-width="160" />
      <el-table-column prop="key_prefix" label="前缀" width="170" />
      <el-table-column prop="scopes" label="权限" min-width="160">
        <template #default="{ row }">
          <span>{{ row.scopes.length ? row.scopes.join(', ') : '全部取件权限' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_used_at" label="最后使用" min-width="170" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'active'"
            text
            type="danger"
            :icon="Delete"
            @click="handleDisable(row)"
          >
            禁用
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreateDialog" title="新建 API Key" width="460px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="权限">
          <el-checkbox v-model="mailFetchScope">mail:fetch</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">
          创建
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { Delete, DocumentCopy, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import { type ApiKey, createApiKey, disableApiKey, fetchApiKeys } from '@/api/apiKeys'
import { ApiError } from '@/api/http'

const keys = ref<ApiKey[]>([])
const loading = ref(false)
const creating = ref(false)
const error = ref('')
const showCreateDialog = ref(false)
const plainTextKey = ref('')
const mailFetchScope = ref(true)
const formRef = ref<FormInstance>()
const form = reactive({ name: '' })

const rules: FormRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
}

function statusLabel(status: ApiKey['status']) {
  const labels = { active: '可用', disabled: '已禁用', expired: '已过期' }
  return labels[status]
}

function statusTag(status: ApiKey['status']) {
  if (status === 'active') return 'success'
  if (status === 'expired') return 'warning'
  return 'info'
}

async function loadKeys() {
  loading.value = true
  error.value = ''
  try {
    keys.value = await fetchApiKeys()
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '加载 API Key 失败'
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  creating.value = true
  try {
    const resp = await createApiKey({
      name: form.name,
      scopes: mailFetchScope.value ? ['mail:fetch'] : [],
    })
    plainTextKey.value = resp.api_key
    showCreateDialog.value = false
    form.name = ''
    mailFetchScope.value = true
    await loadKeys()
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '创建 API Key 失败'
  } finally {
    creating.value = false
  }
}

async function handleDisable(row: ApiKey) {
  await ElMessageBox.confirm(`确认禁用 ${row.name}？`, '禁用 API Key', { type: 'warning' })
  await disableApiKey(row.id)
  ElMessage.success('已禁用')
  await loadKeys()
}

async function copyKey() {
  await navigator.clipboard.writeText(plainTextKey.value)
  ElMessage.success('已复制')
}

onMounted(loadKeys)
</script>

<style scoped>
.api-key-page {
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

.key-alert {
  margin-bottom: 16px;
}

.error-msg {
  color: #f56c6c;
  margin-bottom: 16px;
}
</style>
