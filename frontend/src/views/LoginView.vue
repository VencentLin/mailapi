<template>
  <main class="login-page">
    <section class="login-panel">
      <h1>MailAPI</h1>

      <el-segmented
        v-model="mode"
        class="mode-switch"
        :options="modeOptions"
        block
      />

      <el-form
        v-if="mode === 'login'"
        label-position="top"
        @submit.prevent="handleLogin"
      >
        <el-form-item label="用户名">
          <el-input v-model="loginForm.username" placeholder="admin" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="loginForm.password" type="password" show-password />
        </el-form-item>
        <p v-if="error" class="form-error">{{ error }}</p>
        <p v-if="successMessage" class="form-success">{{ successMessage }}</p>
        <el-button
          type="primary"
          class="submit-button"
          :loading="loading"
          @click="handleLogin"
        >
          登录
        </el-button>
      </el-form>

      <el-form v-else label-position="top" @submit.prevent="handleRegister">
        <el-form-item label="用户名">
          <el-input v-model="registerForm.username" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="registerForm.email" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="registerForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            show-password
          />
        </el-form-item>
        <p v-if="error" class="form-error">{{ error }}</p>
        <el-button
          type="primary"
          class="submit-button"
          :loading="loading"
          @click="handleRegister"
        >
          注册
        </el-button>
      </el-form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { register } from '@/api/auth'
import { ApiError } from '@/api/http'
import { useAuthStore } from '@/stores/auth'

type AuthMode = 'login' | 'register'

const router = useRouter()
const auth = useAuthStore()

const mode = ref<AuthMode>('login')
const modeOptions = [
  { label: '登录', value: 'login' },
  { label: '注册', value: 'register' },
]

const loginForm = reactive({
  username: '',
  password: '',
})

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
})

const loading = ref(false)
const error = ref('')
const successMessage = ref('')

function validateRequired(value: string, message: string) {
  if (!value.trim()) {
    error.value = message
    return false
  }
  return true
}

async function handleLogin() {
  error.value = ''
  successMessage.value = ''
  if (
    !validateRequired(loginForm.username, '请输入用户名') ||
    !validateRequired(loginForm.password, '请输入密码')
  ) {
    return
  }

  loading.value = true
  try {
    await auth.login(loginForm.username, loginForm.password)
    router.push({ name: 'dashboard' })
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = e.message
    } else {
      error.value = '登录失败，请检查网络连接'
    }
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  error.value = ''
  successMessage.value = ''
  if (
    !validateRequired(registerForm.username, '请输入用户名') ||
    !validateRequired(registerForm.email, '请输入邮箱') ||
    !validateRequired(registerForm.password, '请输入密码')
  ) {
    return
  }
  if (registerForm.password.length < 6) {
    error.value = '密码至少 6 位'
    return
  }
  if (registerForm.password !== registerForm.confirmPassword) {
    error.value = '两次输入的密码不一致'
    return
  }

  loading.value = true
  try {
    await register({
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password,
    })
    loginForm.username = registerForm.username
    loginForm.password = ''
    registerForm.username = ''
    registerForm.email = ''
    registerForm.password = ''
    registerForm.confirmPassword = ''
    mode.value = 'login'
    successMessage.value = '注册成功，请等待管理员审核激活后登录'
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = e.message
    } else {
      error.value = '注册失败，请检查网络连接'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: #f6f8fb;
}

.login-panel {
  width: min(420px, calc(100vw - 32px));
  padding: 28px;
  border: 1px solid #d9e2ec;
  border-radius: 8px;
  background: #ffffff;
}

.login-panel h1 {
  margin: 0 0 18px;
  color: #1f2933;
  font-size: 28px;
  line-height: 1.2;
}

.mode-switch {
  width: 100%;
  margin-bottom: 20px;
}

.submit-button {
  width: 100%;
}

.form-error,
.form-success {
  font-size: 13px;
  margin: 0 0 8px;
}

.form-error {
  color: #f56c6c;
}

.form-success {
  color: #15803d;
}
</style>
