<template>
  <el-container class="app-layout">
    <el-aside width="220px" class="app-aside">
      <div class="aside-brand">MailAPI</div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#001529"
        text-color="#ffffffb3"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/">
          <el-icon><Monitor /></el-icon>
          <span>工作台</span>
        </el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/mail-accounts">
          <el-icon><Message /></el-icon>
          <span>邮箱管理</span>
        </el-menu-item>
        <el-menu-item index="/api-keys">
          <el-icon><Key /></el-icon>
          <span>API Key</span>
        </el-menu-item>
        <el-menu-item index="/verification-code">
          <el-icon><Lock /></el-icon>
          <span>验证码取件</span>
        </el-menu-item>
        <el-menu-item index="/logs/mail-fetch">
          <el-icon><Document /></el-icon>
          <span>取件日志</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="app-header">
        <div class="header-left">
          <span class="header-greeting">欢迎，{{ auth.username }}</span>
        </div>
        <el-button text @click="handleLogout">退出登录</el-button>
      </el-header>

      <el-main class="app-main">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { Document, Key, Lock, Message, Monitor, User } from '@element-plus/icons-vue'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const activeMenu = computed(() => route.path)

function handleLogout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
}

.app-aside {
  background: #001529;
  overflow-y: auto;
}

.aside-brand {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-size: 18px;
  font-weight: 650;
  letter-spacing: 1px;
  border-bottom: 1px solid #ffffff1a;
}

.el-menu {
  border-right: none;
}

.app-header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #ffffff;
  border-bottom: 1px solid #e4e7ed;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-greeting {
  color: #303133;
  font-size: 14px;
}

.app-main {
  background: #f6f8fb;
  min-height: calc(100vh - 64px);
}
</style>
