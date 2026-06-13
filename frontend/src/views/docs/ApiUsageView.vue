<template>
  <section class="api-usage-page">
    <header class="page-header">
      <h2>API 使用说明</h2>
    </header>

    <el-collapse v-model="activePanels">
      <el-collapse-item title="认证方式" name="auth">
        <p>推荐在 API Key 页面创建 Key，并通过请求头传入。</p>
        <CodeBlock :code="authExample" />
        <p>如果调用方不能设置请求头，也可以在 JSON body 中传入 user_token。</p>
        <CodeBlock :code="userTokenExample" />
      </el-collapse-item>

      <el-collapse-item title="获取最新一封邮件" name="mail-new">
        <p>邮箱已托管时只需要 email 和 mailbox；未托管时需要 client_id 和 refresh_token。</p>
        <CodeBlock :code="mailNewExample" />
      </el-collapse-item>

      <el-collapse-item title="获取邮件列表" name="mail-all">
        <p>limit 最大建议 100。返回 data 数组，包含发件人、主题、正文、时间和自动提取的验证码。</p>
        <CodeBlock :code="mailAllExample" />
      </el-collapse-item>

      <el-collapse-item title="验证码取件" name="verification">
        <p>默认提取 4-8 位数字，也可以传 regex 自定义验证码规则。</p>
        <CodeBlock :code="verificationExample" />
      </el-collapse-item>

      <el-collapse-item title="批量导入邮箱" name="import">
        <p>每行格式固定为：邮箱----密码----客户端ID----刷新令牌。密码字段只用于兼容格式，不会保存。</p>
        <CodeBlock :code="importExample" />
      </el-collapse-item>

      <el-collapse-item title="清空邮箱夹" name="clear">
        <el-alert
          title="这个接口会删除指定邮箱夹内的邮件，手动测试前请确认邮箱内容可以清空。"
          type="warning"
          show-icon
          :closable="false"
        />
        <CodeBlock :code="clearExample" />
      </el-collapse-item>
    </el-collapse>
  </section>
</template>

<script setup lang="ts">
import { DocumentCopy } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { defineComponent, h, ref } from 'vue'

const activePanels = ref(['auth', 'mail-new', 'mail-all', 'verification'])

async function copyCode(code: string) {
  await navigator.clipboard.writeText(code)
  ElMessage.success('已复制')
}

const CodeBlock = defineComponent({
  props: {
    code: {
      type: String,
      required: true,
    },
  },
  setup(props) {
    return () =>
      h('div', { class: 'code-block' }, [
        h(
          'button',
          {
            class: 'copy-button',
            type: 'button',
            onClick: () => copyCode(props.code),
            title: '复制',
          },
          [h(DocumentCopy), h('span', { class: 'copy-button-label' }, '复制')],
        ),
        h('pre', props.code),
      ])
  },
})

const authExample = `Invoke-RestMethod \`
  -Method Post \`
  -Uri "http://127.0.0.1:8000/api/mail_new" \`
  -Headers @{ Authorization = "Bearer mailapi_xxx" } \`
  -ContentType "application/json" \`
  -Body (@{
    email = "your-outlook@example.com"
    mailbox = "INBOX"
  } | ConvertTo-Json)`

const userTokenExample = `{
  "email": "your-outlook@example.com",
  "mailbox": "INBOX",
  "user_token": "mailapi_xxx"
}`

const mailNewExample = `POST /api/mail_new

{
  "email": "your-outlook@example.com",
  "mailbox": "INBOX",
  "client_id": "microsoft-client-id",
  "refresh_token": "microsoft-refresh-token"
}`

const mailAllExample = `POST /api/mail_all

{
  "email": "your-outlook@example.com",
  "mailbox": "INBOX",
  "limit": 10
}`

const verificationExample = `POST /api/verification-code

{
  "email": "your-outlook@example.com",
  "mailbox": "INBOX",
  "sender": "noreply",
  "subject_keyword": "code",
  "regex": "(?<!\\\\d)\\\\d{6}(?!\\\\d)"
}`

const importExample = `POST /api/mail-accounts/import

{
  "text": "user1@outlook.com----password----client-id----refresh-token\\nuser2@outlook.com----password----client-id----refresh-token",
  "owner_type": "user"
}`

const clearExample = `POST /api/process-mailbox

{
  "email": "your-outlook@example.com",
  "mailbox": "INBOX"
}`
</script>

<style scoped>
.api-usage-page {
  max-width: 980px;
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  color: #1f2933;
  font-size: 20px;
  font-weight: 650;
}

p {
  margin: 0 0 12px;
  color: #4b5563;
  line-height: 1.7;
}

.code-block {
  position: relative;
  margin-bottom: 14px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
}

.code-block :deep(pre) {
  min-height: 48px;
  margin: 0;
  overflow-x: auto;
  padding: 18px 96px 18px 18px;
  color: #0f172a;
  font-family: Consolas, 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.code-block :deep(.copy-button) {
  position: absolute;
  top: 10px;
  right: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 32px;
  padding: 0 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  color: #1f2933;
  background: #ffffff;
  cursor: pointer;
  font-size: 12px;
  line-height: 1;
  z-index: 2;
}

.code-block :deep(.copy-button:hover) {
  border-color: #409eff;
  color: #2563eb;
  background: #eff6ff;
}

.code-block :deep(.copy-button-label) {
  white-space: nowrap;
}
</style>
