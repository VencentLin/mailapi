<template>
  <section class="mail-account-page">
    <header class="page-header">
      <h2>邮箱管理</h2>
    </header>
    <el-empty description="暂无邮箱账号" />
  </section>
</template>

<script setup lang="ts">
</script>

<style scoped>
.mail-account-page {
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
</style>
