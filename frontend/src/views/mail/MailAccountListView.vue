<template>
  <section class="mail-account-page">
    <header class="page-header">
      <h2>邮箱管理</h2>
      <div class="header-actions">
        <el-button :icon="Refresh" :loading="loading" @click="loadAccounts">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">
          托管邮箱
        </el-button>
      </div>
    </header>

    <el-form class="filter-bar" :model="filters" inline>
      <el-form-item label="邮箱">
        <el-input v-model="filters.email" clearable placeholder="email@example.com" />
      </el-form-item>
      <el-form-item v-if="auth.isAdmin" label="归属">
        <el-select v-model="filters.owner_type" clearable placeholder="全部" style="width: 130px">
          <el-option label="用户" value="user" />
          <el-option label="公共池" value="public" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="filters.status" clearable placeholder="全部" style="width: 130px">
          <el-option label="正常" value="active" />
          <el-option label="已禁用" value="disabled" />
          <el-option label="无效" value="invalid" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="loadAccounts">筛选</el-button>
      </el-form-item>
    </el-form>

    <p v-if="error" class="error-msg">{{ error }}</p>

    <el-table :data="accounts" v-loading="loading" empty-text="暂无邮箱账号" stripe>
      <el-table-column prop="email" label="邮箱" min-width="210" />
      <el-table-column label="归属" width="120">
        <template #default="{ row }">
          <el-tag :type="row.owner_type === 'public' ? 'warning' : 'success'" size="small">
            {{ ownerLabel(row) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_protocol" label="协议" width="100" />
      <el-table-column prop="last_error_code" label="最近错误" min-width="150" />
      <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
      <el-table-column label="操作" width="340" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.can_claim"
            text
            type="primary"
            :icon="Check"
            @click="handleClaim(row)"
          >
            认领
          </el-button>
          <el-button
            v-if="canEditCredentials(row)"
            text
            :icon="Key"
            @click="openCredentials(row)"
          >
            凭据
          </el-button>
          <el-button text :icon="VideoPlay" @click="handleTest(row)">测试</el-button>
          <el-button
            v-if="canManage(row) && row.status === 'active'"
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

    <el-dialog v-model="showCreateDialog" title="托管邮箱" width="560px">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="110px">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="createForm.email" />
        </el-form-item>
        <el-form-item label="Client ID" prop="client_id">
          <el-input v-model="createForm.client_id" />
        </el-form-item>
        <el-form-item label="Refresh Token" prop="refresh_token">
          <el-input v-model="createForm.refresh_token" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item v-if="auth.isAdmin" label="归属">
          <el-radio-group v-model="createForm.owner_type">
            <el-radio-button label="user">用户</el-radio-button>
            <el-radio-button label="public">公共池</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="auth.isAdmin && createForm.owner_type === 'user'" label="用户 ID">
          <el-input-number v-model="createForm.owner_user_id" :min="1" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="createForm.remark" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showCredentialsDialog" title="邮箱凭据" width="580px">
      <el-form label-width="110px">
        <el-form-item label="邮箱">
          <el-input v-model="credentials.email" readonly />
        </el-form-item>
        <el-form-item label="Client ID">
          <el-input v-model="credentials.client_id" />
        </el-form-item>
        <el-form-item label="Refresh Token">
          <el-input
            v-model="credentials.refresh_token"
            type="textarea"
            :rows="5"
            placeholder="留空则不修改"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCredentialsDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingCredentials" @click="saveCredentials">
          保存
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { Check, Delete, Key, Plus, Refresh, Search, VideoPlay } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import { ApiError } from '@/api/http'
import {
  type MailAccount,
  type MailAccountCreate,
  type MailAccountFilters,
  claimMailAccount,
  createMailAccount,
  disableMailAccount,
  fetchMailAccountCredentials,
  fetchMailAccounts,
  testFetchMailAccount,
  updateMailAccountCredentials,
} from '@/api/mailAccounts'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const accounts = ref<MailAccount[]>([])
const loading = ref(false)
const creating = ref(false)
const savingCredentials = ref(false)
const error = ref('')
const showCreateDialog = ref(false)
const showCredentialsDialog = ref(false)
const createFormRef = ref<FormInstance>()

const filters = reactive<MailAccountFilters>({
  email: '',
  owner_type: '',
  status: '',
})

const createForm = reactive<MailAccountCreate>({
  email: '',
  client_id: '',
  refresh_token: '',
  owner_type: 'user',
  owner_user_id: null,
  remark: '',
})

const credentials = reactive({
  account_id: 0,
  email: '',
  client_id: '',
  refresh_token: '',
})

const createRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  client_id: [{ required: true, message: '请输入 Client ID', trigger: 'blur' }],
  refresh_token: [{ required: true, message: '请输入 Refresh Token', trigger: 'blur' }],
}

function ownerLabel(row: MailAccount) {
  if (row.owner_type === 'public') return '公共池'
  if (row.owner_user_id === auth.userId) return '我的'
  return `用户 ${row.owner_user_id}`
}

function statusLabel(status: MailAccount['status']) {
  const labels = { active: '正常', disabled: '已禁用', invalid: '无效' }
  return labels[status]
}

function statusTag(status: MailAccount['status']) {
  if (status === 'active') return 'success'
  if (status === 'invalid') return 'danger'
  return 'info'
}

function canManage(row: MailAccount) {
  return auth.isAdmin || (row.owner_type === 'user' && row.owner_user_id === auth.userId)
}

function canEditCredentials(row: MailAccount) {
  return row.can_view_credentials || canManage(row)
}

async function loadAccounts() {
  loading.value = true
  error.value = ''
  try {
    accounts.value = await fetchMailAccounts(filters)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '加载邮箱失败'
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return
  creating.value = true
  try {
    await createMailAccount({ ...createForm })
    ElMessage.success('已托管邮箱')
    showCreateDialog.value = false
    createForm.email = ''
    createForm.client_id = ''
    createForm.refresh_token = ''
    createForm.remark = ''
    await loadAccounts()
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '创建邮箱失败'
  } finally {
    creating.value = false
  }
}

async function handleClaim(row: MailAccount) {
  await claimMailAccount(row.id)
  ElMessage.success('已认领')
  await loadAccounts()
}

async function openCredentials(row: MailAccount) {
  credentials.account_id = row.id
  credentials.email = row.email
  credentials.client_id = row.client_id
  credentials.refresh_token = ''
  if (row.can_view_credentials) {
    const resp = await fetchMailAccountCredentials(row.id)
    credentials.client_id = resp.client_id
    credentials.refresh_token = resp.refresh_token
  }
  showCredentialsDialog.value = true
}

async function saveCredentials() {
  const payload: { client_id?: string; refresh_token?: string } = {}
  if (credentials.client_id) payload.client_id = credentials.client_id
  if (credentials.refresh_token) payload.refresh_token = credentials.refresh_token
  savingCredentials.value = true
  try {
    await updateMailAccountCredentials(credentials.account_id, payload)
    ElMessage.success('凭据已保存')
    showCredentialsDialog.value = false
    await loadAccounts()
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '保存凭据失败'
  } finally {
    savingCredentials.value = false
  }
}

async function handleTest(row: MailAccount) {
  const resp = await testFetchMailAccount(row.id)
  ElMessage.success(`取件成功，协议 ${resp.protocol}，邮件 ${resp.message_count} 封`)
  await loadAccounts()
}

async function handleDisable(row: MailAccount) {
  await ElMessageBox.confirm(`确认禁用 ${row.email}？`, '禁用邮箱', { type: 'warning' })
  await disableMailAccount(row.id)
  ElMessage.success('已禁用')
  await loadAccounts()
}

onMounted(loadAccounts)
</script>

<style scoped>
.mail-account-page {
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

.header-actions {
  display: flex;
  gap: 8px;
}

.filter-bar {
  margin-bottom: 12px;
}

.error-msg {
  color: #f56c6c;
  margin-bottom: 16px;
}
</style>
