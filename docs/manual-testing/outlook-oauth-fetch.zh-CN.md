# Outlook OAuth2 真实取件验证

本文档用于验证 MailAPI 的真实 Outlook OAuth2 取件路径。不要把真实 `refresh_token`、`client_id` 或邮箱凭据写入 git、任务文档、截图或聊天记录。

## 前置条件

你需要准备：

- Outlook 邮箱地址。
- 对应 Microsoft OAuth 应用的 `client_id`。
- 有效 `refresh_token`。
- Microsoft Graph `Mail.Read` 权限，或 IMAP `IMAP.AccessAsUser.All` 权限。

Graph 优先。如果 Graph token 没有 `Mail.Read`/`Mail.ReadWrite`，系统会尝试 IMAP XOAUTH2 fallback。

## 启动本机后端

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\uvicorn.exe backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

确认健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/health/db
```

## 匿名调用：托管到公共池

```powershell
$body = @{
  email = $env:OUTLOOK_TEST_EMAIL
  client_id = $env:OUTLOOK_TEST_CLIENT_ID
  refresh_token = $env:OUTLOOK_TEST_REFRESH_TOKEN
  mailbox = "INBOX"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/mail_new" `
  -ContentType "application/json" `
  -Body $body
```

成功时返回：

```json
{
  "code": "200",
  "data": [],
  "trace_id": "...",
  "protocol": "graph",
  "mail_account_status": "auto_created_public"
}
```

`data` 为空也可以是成功结果，表示邮箱文件夹里没有邮件；关键看 `code`、`protocol` 和日志。

## 带管理员 token 调用：托管到当前用户

先登录：

```powershell
$login = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/auth/login" `
  -ContentType "application/json" `
  -Body (@{ username = "vincentlin"; password = "你的密码" } | ConvertTo-Json)

$headers = @{ Authorization = "Bearer $($login.access_token)" }
```

再调用：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/mail_new" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body
```

成功时 `mail_account_status` 应为 `auto_created_user` 或 `existing_user`。

## 已托管邮箱二次调用

同一个邮箱托管后，可以不再传 `client_id` 和 `refresh_token`：

```powershell
$body2 = @{
  email = $env:OUTLOOK_TEST_EMAIL
  mailbox = "INBOX"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/mail_new" `
  -ContentType "application/json" `
  -Body $body2
```

成功时 `mail_account_status` 应为 `existing_public` 或 `existing_user`。

## 其他兼容接口

获取列表：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/mail_all" `
  -ContentType "application/json" `
  -Body $body
```

清空邮箱：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/process-mailbox" `
  -ContentType "application/json" `
  -Body $body
```

GET 方式也支持同名参数：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/mail_new?email=$env:OUTLOOK_TEST_EMAIL&mailbox=INBOX"
```

## 排错

每次 API 调用都会返回 `trace_id`，并写入 `mail_fetch_logs`。

常见错误：

- `oauth_refresh_failed` 或 `mail_fetch_failed`：refresh token 失效、client_id 不匹配或权限不足。
- `mail_permission_missing`：Graph 和 IMAP 都没有可用邮件权限。
- `imap_mailbox_open_failed`：IMAP 文件夹名称不正确或账号不允许 IMAP。

如果 Graph 不可用但 IMAP 成功，响应中的 `protocol` 会是 `imap`。
