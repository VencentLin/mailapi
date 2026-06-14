<template>
  <section class="api-usage-page">
    <header class="page-header">
      <h2>API 使用说明</h2>
    </header>

    <section class="ai-tool-guide">
      <div class="guide-header">
        <h3>AI 工具说明</h3>
        <p>复制下面整段发给自动化 AI，让它知道如何调用 MailAPI。</p>
      </div>
      <CodeBlock :code="aiToolGuide" />
    </section>

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

      <el-collapse-item title="重新授权邮箱" name="reauthorize">
        <p>凭据失效时，在邮箱管理页面点击“重新授权”。系统会生成 Microsoft 授权链接，回调成功后自动更新 refresh token。</p>
        <CodeBlock :code="reauthorizeExample" />
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

const aiToolGuide = String.raw`# MailAPI 给 AI 自动化脚本的工具说明

你的任务：
当自动化流程需要读取 Outlook 邮件、查看全部邮件、提取邮箱验证码、托管邮箱或清空邮箱时，调用 MailAPI。不要猜接口，不要直接登录邮箱网页，不要在日志里打印 API Key、Authorization、refresh_token 或密码。

基础配置：
- MAILAPI_BASE_URL：MailAPI 服务地址，例如 http://127.0.0.1:8000 或云端地址。
- MAILAPI_API_KEY：在 MailAPI 前端的 API Key 页面创建，格式通常是 mailapi_xxx。
- 所有接口路径都以 /api 开头。
- 优先使用 POST JSON；兼容取件接口也支持 GET query。

认证规则：
- 自动化取件优先用请求头：Authorization: Bearer {MAILAPI_API_KEY}
- 如果调用环境不能设置请求头，可在 JSON body 里传 user_token: "{MAILAPI_API_KEY}"。
- 管理类接口使用网页登录 JWT：先 POST /api/auth/login 获取 access_token，再用 Authorization: Bearer {access_token}。
- 邮箱已托管时，取件请求只需要 email 和 mailbox。邮箱未托管时，需要额外传 client_id 和 refresh_token；如果传入 API Key/user_token，会自动托管到该用户，否则托管到公共账户。

核心取件 API：

1. 获取验证码
POST /api/verification-code
用途：从邮箱最新邮件中筛选并提取验证码。
请求体：
{
  "email": "your-outlook@example.com",
  "mailbox": "INBOX",
  "sender": "可选，发件人关键词",
  "subject_keyword": "可选，标题关键词",
  "body_keyword": "可选，正文关键词",
  "since_minutes": 10,
  "limit": 20,
  "regex": "(?<!\\d)\\d{4,8}(?!\\d)",
  "delete_after_fetch": false
}
成功返回 code = "200"，验证码字段是 verification_code。
如果返回 404 且 error_code = "VERIFICATION_CODE_NOT_FOUND"，等待 5 秒后重试，最多重试 90 秒。
如果返回 401/403，检查 API Key 或 JWT。返回 502 时记录 trace_id 方便排查。

2. 获取最新一封邮件
POST /api/mail_new
请求体：
{
  "email": "your-outlook@example.com",
  "mailbox": "INBOX"
}
成功返回 code = "200"，data 是邮件数组，最多 1 封。邮件字段包含 id、sender/send、subject、text、html、received_at/date、verification_code。

3. 获取邮件列表
POST /api/mail_all
请求体：
{
  "email": "your-outlook@example.com",
  "mailbox": "INBOX",
  "limit": 10
}
成功返回 code = "200"，data 是邮件数组。

4. 清空邮箱
POST /api/process-mailbox
请求体：
{
  "email": "your-outlook@example.com",
  "mailbox": "INBOX"
}
注意：这是危险操作，会删除指定邮箱文件夹内邮件。除非用户明确要求清空，否则不要调用。

邮箱托管和管理 API：
- POST /api/mail-accounts/import：批量导入邮箱，JWT 登录后使用。每行格式：邮箱----密码----客户端ID----刷新令牌。密码字段仅兼容格式，不保存。
- GET /api/mail-accounts：查看邮箱列表，可筛选 owner_user_id、owner_type、email、status、limit。
- POST /api/mail-accounts：新增托管邮箱。
- GET /api/mail-accounts/{account_id}：查看单个邮箱。
- PATCH /api/mail-accounts/{account_id}：修改归属、状态、备注等；传 {"status":"active"} 可重新启用邮箱。
- DELETE /api/mail-accounts/{account_id}：禁用托管邮箱，不释放邮箱地址。
- DELETE /api/mail-accounts/{account_id}/permanent：彻底删除托管邮箱，释放邮箱地址，可重新导入；历史取件日志会保留。
- POST /api/mail-accounts/{account_id}/claim：认领公共邮箱。
- GET /api/mail-accounts/{account_id}/credentials：查看 client_id 和 refresh_token，通常仅管理员或有权限用户可用。
- PATCH /api/mail-accounts/{account_id}/credentials：修改 client_id 或 refresh_token。
- POST /api/mail-accounts/{account_id}/reauthorize-url：生成 Microsoft 重新授权链接，凭据失效时使用。
- GET /api/oauth/microsoft/callback：Microsoft 授权码回调，成功后自动更新该邮箱的 refresh_token。
- POST /api/mail-accounts/{account_id}/test-fetch?mailbox=INBOX：测试取件。
- POST /api/mail-accounts/{account_id}/clear?mailbox=INBOX：清空该邮箱文件夹，危险操作。

用户、API Key、日志和系统 API：
- POST /api/auth/login：网页登录，body 为 username 和 password，返回 access_token。
- GET /api/auth/me：查看当前 JWT 用户。
- GET /api/users、POST /api/users：管理员查看/创建用户。
- GET /api/api-keys、POST /api/api-keys、PATCH /api/api-keys/{id}、DELETE /api/api-keys/{id}：管理 API Key。
- GET /api/logs/mail-fetch：查看取件日志，可筛选 email、status、user_id、limit。
- GET /api/logs/audit：查看审计日志，管理员接口。
- GET /api/dashboard：仪表盘统计。
- GET /api/health、GET /api/health/db：健康检查。

自动化脚本建议：
- 封装一个 get_email_code(email, sender=None, subject_keyword=None, body_keyword=None) 函数，内部调用 /api/verification-code 并按 404 轮询。
- 只把 verification_code 填入网页验证码输入框，不要把完整邮件正文、refresh_token 或 API Key 输出给用户界面。
- 优先使用已经托管的邮箱；只有用户明确提供 client_id 和 refresh_token 时才在请求中传临时凭据。`

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

const reauthorizeExample = `POST /api/mail-accounts/{account_id}/reauthorize-url

返回：
{
  "auth_url": "https://login.microsoftonline.com/...",
  "expires_in": 600
}

浏览器打开 auth_url 完成 Microsoft 授权。
Microsoft 会回调：
GET /api/oauth/microsoft/callback?code=...&state=...

成功后跳回：
/mail-accounts?reauthorize=success&email=your-outlook@example.com`

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

.ai-tool-guide {
  margin-bottom: 18px;
}

.guide-header {
  margin-bottom: 10px;
}

.guide-header h3 {
  margin: 0 0 4px;
  color: #1f2933;
  font-size: 16px;
  font-weight: 650;
}

.guide-header p {
  margin-bottom: 0;
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
