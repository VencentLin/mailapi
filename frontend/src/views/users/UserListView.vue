<template>
  <section class="user-list-page">
    <header class="page-header">
      <h2>用户管理</h2>
      <el-button type="primary" @click="showCreateDialog = true">添加用户</el-button>
    </header>

    <p v-if="error" class="error-msg">{{ error }}</p>

    <el-table
      v-if="!error"
      :data="users"
      v-loading="loading"
      empty-text="暂无用户数据"
      stripe
    >
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="username" label="用户名" min-width="130" />
      <el-table-column prop="email" label="邮箱" min-width="220" />
      <el-table-column prop="role" label="角色" width="110">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : ''" size="small">
            {{ roleText(row.role) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
            {{ statusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="190" fixed="right">
        <template #default="{ row }">
          <div class="table-actions">
            <el-button size="small" @click="openEditDialog(row)">编辑用户</el-button>
            <el-button
              size="small"
              :type="row.status === 'active' ? 'warning' : 'success'"
              :disabled="row.id === auth.userId && row.status === 'active'"
              :loading="togglingUserId === row.id"
              @click="handleToggleStatus(row)"
            >
              {{ row.status === 'active' ? '停用' : '启用' }}
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreateDialog" title="添加用户" width="480px">
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-width="80px"
        @submit.prevent="handleCreate"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="createForm.username" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="createForm.email" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="createForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="createForm.role">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="createForm.status">
            <el-option label="正常" value="active" />
            <el-option label="已禁用" value="disabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">
          创建
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEditDialog" title="编辑用户" width="480px">
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editRules"
        label-width="80px"
        @submit.prevent="handleUpdate"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="editForm.username" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="editForm.email" />
        </el-form-item>
        <el-form-item label="新密码" prop="password">
          <el-input
            v-model="editForm.password"
            type="password"
            show-password
            placeholder="留空表示不修改"
          />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="editForm.role" :disabled="isEditingSelf">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="editForm.status" :disabled="isEditingSelf">
            <el-option label="正常" value="active" />
            <el-option label="已禁用" value="disabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="updating" @click="handleUpdate">
          保存
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

import { ApiError } from '@/api/http'
import {
  type UserCreate,
  type UserPublic,
  type UserUpdate,
  createUser,
  fetchUsers,
  updateUser,
} from '@/api/users'
import { useAuthStore } from '@/stores/auth'

type UserRole = UserPublic['role']
type UserStatus = UserPublic['status']

const auth = useAuthStore()
const users = ref<UserPublic[]>([])
const loading = ref(false)
const error = ref('')
const creating = ref(false)
const updating = ref(false)
const togglingUserId = ref<number | null>(null)
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const createFormRef = ref<FormInstance>()
const editFormRef = ref<FormInstance>()

const createForm = reactive<Required<UserCreate>>({
  username: '',
  email: '',
  password: '',
  role: 'user',
  status: 'active',
})

const editForm = reactive({
  id: 0,
  username: '',
  email: '',
  password: '',
  role: 'user' as UserRole,
  status: 'active' as UserStatus,
})

const createRules = computed<FormRules>(() => ({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 64, message: '用户名长度 2-64', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}))

const editRules = computed<FormRules>(() => ({
  username: createRules.value.username,
  email: createRules.value.email,
  password: [
    {
      validator: (_rule, value: string, callback) => {
        if (value && value.length < 6) {
          callback(new Error('密码至少 6 位'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  role: createRules.value.role,
  status: createRules.value.status,
}))

const isEditingSelf = computed(() => editForm.id === auth.userId)

function roleText(role: UserRole) {
  return role === 'admin' ? '管理员' : '普通用户'
}

function statusText(status: UserStatus) {
  return status === 'active' ? '正常' : '已禁用'
}

function resetCreateForm() {
  createForm.username = ''
  createForm.email = ''
  createForm.password = ''
  createForm.role = 'user'
  createForm.status = 'active'
  createFormRef.value?.resetFields()
}

function openEditDialog(user: UserPublic) {
  editForm.id = user.id
  editForm.username = user.username
  editForm.email = user.email
  editForm.password = ''
  editForm.role = user.role
  editForm.status = user.status
  showEditDialog.value = true
}

async function loadUsers() {
  loading.value = true
  error.value = ''
  try {
    users.value = await fetchUsers(0, 100)
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = e.message
    } else {
      error.value = '加载用户列表失败'
    }
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return

  creating.value = true
  try {
    await createUser({ ...createForm })
    showCreateDialog.value = false
    resetCreateForm()
    ElMessage.success('用户已创建')
    await loadUsers()
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = e.message
    } else {
      error.value = '创建用户失败'
    }
  } finally {
    creating.value = false
  }
}

async function handleUpdate() {
  const valid = await editFormRef.value?.validate().catch(() => false)
  if (!valid) return

  const payload: UserUpdate = {
    username: editForm.username,
    email: editForm.email,
    role: editForm.role,
    status: editForm.status,
  }
  if (editForm.password) {
    payload.password = editForm.password
  }

  updating.value = true
  try {
    await updateUser(editForm.id, payload)
    showEditDialog.value = false
    ElMessage.success('用户已更新')
    await loadUsers()
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = e.message
    } else {
      error.value = '更新用户失败'
    }
  } finally {
    updating.value = false
  }
}

async function handleToggleStatus(user: UserPublic) {
  if (user.id === auth.userId && user.status === 'active') {
    return
  }

  const nextStatus: UserStatus = user.status === 'active' ? 'disabled' : 'active'
  if (nextStatus === 'disabled') {
    const confirmed = await ElMessageBox.confirm(
      `确认停用用户 ${user.username}？`,
      '停用用户',
      { type: 'warning', confirmButtonText: '停用', cancelButtonText: '取消' },
    )
      .then(() => true)
      .catch(() => false)
    if (!confirmed) return
  }

  togglingUserId.value = user.id
  try {
    await updateUser(user.id, { status: nextStatus })
    ElMessage.success(nextStatus === 'active' ? '用户已启用' : '用户已停用')
    await loadUsers()
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = e.message
    } else {
      error.value = '更新用户状态失败'
    }
  } finally {
    togglingUserId.value = null
  }
}

onMounted(() => {
  void loadUsers()
})
</script>

<style scoped>
.user-list-page {
  padding: 0;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 650;
}

.table-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.error-msg {
  color: #f56c6c;
  margin-bottom: 16px;
}
</style>
