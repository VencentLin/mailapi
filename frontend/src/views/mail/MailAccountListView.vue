<template>
  <section class="mail-account-page">
    <header class="page-header">
      <h2>邮箱管理</h2>
      <div class="header-actions">
        <el-button :icon="Refresh" :loading="loading" @click="loadAccounts">刷新</el-button>
        <el-button :icon="Upload" @click="showImportDialog = true">批量导入</el-button>
        <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">
          托管邮箱
        </el-button>
      </div>
    </header>

    <el-form class="filter-bar" :model="filters" inline>
      <el-form-item label="邮箱">
        <el-input v-model="filters.email" clearable placeholder="email@example.com" />
      </el-form-item>
      <el-form-item v-if="auth.isAdmin" label="归属类型">
        <el-select v-model="filters.owner_type" clearable placeholder="全部" style="width: 130px">
          <el-option label="用户" value="user" />
          <el-option label="公共池" value="public" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="auth.isAdmin" label="用户">
        <el-select
          v-model="filters.owner_user_id"
          :disabled="filters.owner_type === 'public'"
          :loading="usersLoading"
          filterable
          placeholder="全部用户"
          style="width: 180px"
        >
          <el-option label="全部用户" :value="0" />
          <el-option
            v-for="user in users"
            :key="user.id"
            :label="userLabel(user)"
            :value="user.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="filters.status" clearable placeholder="全部" style="width: 130px">
          <el-option label="正常" value="active" />
          <el-option label="已禁用" value="disabled" />
          <el-option label="无效" value="invalid" />
        </el-select>
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
      <el-table-column label="操作" width="520" fixed="right">
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
          <el-button
            v-if="canManage(row)"
            text
            type="warning"
            :icon="Refresh"
            @click="handleReauthorize(row)"
          >
            重新授权
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
          <el-button
            v-if="canManage(row) && row.status !== 'active'"
            text
            type="success"
            :icon="Check"
            @click="handleEnable(row)"
          >
            启用
          </el-button>
          <el-button
            v-if="canManage(row) && row.status !== 'active'"
            text
            type="danger"
            :icon="Delete"
            @click="handlePermanentDelete(row)"
          >
            彻底删除
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

    <el-dialog v-model="showImportDialog" title="批量导入邮箱" width="760px">
      <el-form label-width="100px">
        <el-form-item label="导入格式">
          <el-input
            v-model="importForm.text"
            type="textarea"
            :rows="8"
            placeholder="邮箱----密码----客户端ID----刷新令牌"
          />
        </el-form-item>
        <el-form-item v-if="auth.isAdmin" label="归属">
          <el-radio-group v-model="importForm.owner_type">
            <el-radio-button label="user">用户</el-radio-button>
            <el-radio-button label="public">公共池</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="auth.isAdmin && importForm.owner_type === 'user'" label="用户 ID">
          <el-input-number v-model="importForm.owner_user_id" :min="1" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="importForm.remark" />
        </el-form-item>
      </el-form>

      <section v-if="importResult" class="import-result">
        <el-alert
          :title="`创建 ${importResult.created}，跳过 ${importResult.skipped}，失败 ${importResult.failed}`"
          type="info"
          show-icon
          :closable="false"
        />
        <el-table :data="importResult.items" max-height="260" size="small">
          <el-table-column prop="line" label="行" width="70" />
          <el-table-column prop="email" label="邮箱" min-width="190" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="importStatusTag(row.status)" size="small">
                {{ importStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="message" label="说明" min-width="220" show-overflow-tooltip />
        </el-table>
      </section>

      <template #footer>
        <el-button @click="showImportDialog = false">关闭</el-button>
        <el-button type="primary" :loading="importing" @click="handleImport">导入</el-button>
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
import {
  Check,
  Delete,
  Key,
  Plus,
  Refresh,
  Upload,
  VideoPlay,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError } from '@/api/http'
import {
  type MailAccount,
  type MailAccountCreate,
  type MailAccountFilters,
  claimMailAccount,
  createMailAccount,
  createMailAccountReauthorizeUrl,
  disableMailAccount,
  fetchMailAccountCredentials,
  fetchMailAccounts,
  importMailAccounts,
  permanentlyDeleteMailAccount,
  testFetchMailAccount,
  updateMailAccount,
  updateMailAccountCredentials,
} from '@/api/mailAccounts'
import { type UserPublic, fetchUsers } from '@/api/users'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const accounts = ref<MailAccount[]>([])
const users = ref<UserPublic[]>([])
const loading = ref(false)
const usersLoading = ref(false)
const creating = ref(false)
const importing = ref(false)
const savingCredentials = ref(false)
const error = ref('')
const showCreateDialog = ref(false)
const showImportDialog = ref(false)
const showCredentialsDialog = ref(false)
const createFormRef = ref<FormInstance>()

const filters = reactive<MailAccountFilters>({
  email: '',
  owner_type: '',
  owner_user_id: null,
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

const importForm = reactive({
  text: '',
  owner_type: 'user' as 'user' | 'public',
  owner_user_id: null as number | null,
  remark: '',
})
const importResult = ref<Awaited<ReturnType<typeof importMailAccounts>> | null>(null)

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

let autoLoadTimer: ReturnType<typeof window.setTimeout> | null = null
let suppressAutoLoad = true

function ownerLabel(row: MailAccount) {
  if (row.owner_type === 'public') return '公共池'
  if (row.owner_user_id === auth.userId) return '我的'
  return `用户 ${row.owner_user_id}`
}

function userLabel(user: UserPublic) {
  return `${user.username} (${user.email})`
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

function importStatusLabel(status: string) {
  const labels: Record<string, string> = {
    created: '已创建',
    skipped: '已跳过',
    failed: '失败',
  }
  return labels[status] || status
}

function importStatusTag(status: string) {
  if (status === 'created') return 'success'
  if (status === 'failed') return 'danger'
  return 'warning'
}

function canManage(row: MailAccount) {
  return auth.isAdmin || (row.owner_type === 'user' && row.owner_user_id === auth.userId)
}

function canEditCredentials(row: MailAccount) {
  return row.can_view_credentials || canManage(row)
}

function reauthorizeReasonLabel(reason: unknown) {
  const key = typeof reason === 'string' ? reason : 'oauth_failed'
  const labels: Record<string, string> = {
    email_mismatch: '授权的 Microsoft 邮箱和当前托管邮箱不一致',
    invalid_state: '授权状态已失效，请重新点击授权',
    missing_code: 'Microsoft 没有返回授权码',
    microsoft_denied: 'Microsoft 授权被取消',
    not_found: '邮箱或用户不存在',
    oauth_failed: 'Microsoft OAuth 换取凭据失败',
    permission_denied: '没有权限更新这个邮箱',
  }
  return labels[key] || '重新授权失败'
}

function showReauthorizeResult() {
  const status = route.query.reauthorize
  if (status !== 'success' && status !== 'failed') return

  const email = typeof route.query.email === 'string' ? route.query.email : ''
  if (status === 'success') {
    ElMessage.success(email ? `${email} 重新授权成功` : '重新授权成功')
  } else {
    ElMessage.error(reauthorizeReasonLabel(route.query.reason))
  }

  const query = { ...route.query }
  delete query.reauthorize
  delete query.email
  delete query.reason
  void router.replace({ path: route.path, query })
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

async function loadUsers() {
  if (!auth.isAdmin) return
  usersLoading.value = true
  try {
    users.value = await fetchUsers(0, 100)
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '加载用户列表失败'
  } finally {
    usersLoading.value = false
  }
}

function loadAccountsDebounced() {
  if (suppressAutoLoad) return
  if (autoLoadTimer) window.clearTimeout(autoLoadTimer)
  autoLoadTimer = window.setTimeout(() => {
    void loadAccounts()
  }, 300)
}

function initializeDefaultFilters() {
  if (auth.isAdmin && auth.userId > 0) {
    filters.owner_user_id = auth.userId
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

async function handleImport() {
  importing.value = true
  error.value = ''
  importResult.value = null
  try {
    importResult.value = await importMailAccounts({
      text: importForm.text,
      owner_type: auth.isAdmin ? importForm.owner_type : undefined,
      owner_user_id:
        auth.isAdmin && importForm.owner_type === 'user'
          ? importForm.owner_user_id
          : undefined,
      remark: importForm.remark || undefined,
    })
    ElMessage.success(
      `导入完成：创建 ${importResult.value.created}，跳过 ${importResult.value.skipped}，失败 ${importResult.value.failed}`,
    )
    await loadAccounts()
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '批量导入失败'
  } finally {
    importing.value = false
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

async function handleReauthorize(row: MailAccount) {
  try {
    const resp = await createMailAccountReauthorizeUrl(row.id)
    window.location.href = resp.auth_url
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : '创建重新授权链接失败'
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

async function handleEnable(row: MailAccount) {
  await updateMailAccount(row.id, { status: 'active' })
  ElMessage.success('已启用')
  await loadAccounts()
}

async function handlePermanentDelete(row: MailAccount) {
  await ElMessageBox.confirm(
    `确认彻底删除 ${row.email}？删除后会释放邮箱地址，可以重新导入；历史取件日志会保留。`,
    '彻底删除邮箱',
    {
      type: 'error',
      confirmButtonText: '彻底删除',
      cancelButtonText: '取消',
    },
  )
  await permanentlyDeleteMailAccount(row.id)
  ElMessage.success('已彻底删除')
  await loadAccounts()
}

onMounted(() => {
  showReauthorizeResult()
  initializeDefaultFilters()
  void loadUsers()
  void loadAccounts()
  suppressAutoLoad = false
})

watch(
  () => [filters.email, filters.owner_type, filters.owner_user_id, filters.status],
  ([, ownerType]) => {
    if (ownerType === 'public' && filters.owner_user_id) {
      filters.owner_user_id = 0
      return
    }
    loadAccountsDebounced()
  },
)
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

.import-result {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}
</style>
