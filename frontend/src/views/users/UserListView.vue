<template>
  <section class="user-list-page">
    <header class="page-header">
      <h2>用户管理</h2>
      <el-button type="primary" disabled>添加用户</el-button>
    </header>
    <el-empty description="暂无用户数据" />
  </section>
</template>

<script setup lang="ts">
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
</style>
