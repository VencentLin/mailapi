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
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column prop="role" label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : ''" size="small">
            {{ row.role === 'admin' ? '管理员' : '普通用户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
            {{ row.status === 'active' ? '正常' : '已禁用' }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create User Dialog -->
    <el-dialog v-model="showCreateDialog" title="添加用户" width="480px">
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="80px"
        @submit.prevent="handleCreate"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
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
  </section>
</template>

<script setup lang="ts">
import type { FormInstance, FormRules } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

import { type UserCreate, type UserPublic, createUser, fetchUsers } from '@/api/users'
import { ApiError } from '@/api/http'

const users = ref<UserPublic[]>([])
const loading = ref(false)
const error = ref('')
const creating = ref(false)
const showCreateDialog = ref(false)
const formRef = ref<FormInstance>()

const form = reactive<UserCreate>({
  username: '',
  email: '',
  password: '',
  role: 'user',
})

const formRules = computed<FormRules>(() => ({
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
}))

async function loadUsers() {
  loading.value = true
  error.value = ''
  try {
    users.value = await fetchUsers()
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
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  creating.value = true
  try {
    await createUser({ ...form })
    showCreateDialog.value = false
    form.username = ''
    form.email = ''
    form.password = ''
    form.role = 'user'
    formRef.value?.resetFields()
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

onMounted(() => {
  loadUsers()
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

.error-msg {
  color: #f56c6c;
  margin-bottom: 16px;
}
</style>
