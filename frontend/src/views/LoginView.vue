<template>
  <main class="login-page">
    <section class="login-panel">
      <h1>MailAPI</h1>
      <el-form label-position="top">
        <el-form-item label="用户名">
          <el-input placeholder="admin" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input type="password" show-password />
        </el-form-item>
        <el-button type="primary" class="login-button">登录</el-button>
      </el-form>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: #f6f8fb;
}

.login-panel {
  width: min(380px, calc(100vw - 32px));
  padding: 28px;
  border: 1px solid #d9e2ec;
  border-radius: 8px;
  background: #ffffff;
}

.login-button {
  width: 100%;
}
</style>
