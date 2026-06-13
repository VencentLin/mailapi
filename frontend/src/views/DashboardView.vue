<template>
  <section class="dashboard">
    <header class="page-header">
      <h1>MailAPI 控制台</h1>
    </header>

    <section class="metrics">
      <article>
        <span>我的邮箱</span>
        <strong>0</strong>
      </article>
      <article>
        <span>公共池</span>
        <strong>0</strong>
      </article>
      <article>
        <span>今日取件</span>
        <strong>0</strong>
      </article>
      <article>
        <span>失败次数</span>
        <strong>0</strong>
      </article>
    </section>
  </section>
</template>

<script setup lang="ts">
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 650;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.metrics article {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 18px;
  border: 1px solid #d9e2ec;
  border-radius: 8px;
  background: #ffffff;
}

.metrics span {
  color: #5c6b7a;
  font-size: 14px;
}

.metrics strong {
  color: #1f2933;
  font-size: 28px;
}
</style>
