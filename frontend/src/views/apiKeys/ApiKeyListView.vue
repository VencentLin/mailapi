<template>
  <section class="api-key-page">
    <header class="page-header">
      <h2>API Key</h2>
    </header>
    <el-empty description="暂无 API Key" />
  </section>
</template>

<script setup lang="ts">
</script>

<style scoped>
.api-key-page {
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
