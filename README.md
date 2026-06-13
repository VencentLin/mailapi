# MailAPI

MailAPI 是一个面向 Outlook OAuth2 邮箱的验证码取件平台。

## 开发和部署约定

- **本机开发不使用 Docker**：直接启动 FastAPI 后端和 Vite 前端，方便调试。
- **最终部署再打包 Docker**：开发完成后，在服务器或有 Docker 的环境构建镜像；镜像内包含后端、前端静态文件和 Redis。
- **PostgreSQL 使用云端数据库**：本机开发和服务器部署都通过 `DATABASE_URL` 连接外部 PGSQL。

## 本机开发

安装后端依赖：

```bash
pip install -e ".[dev]"
```

准备环境变量：

```bash
copy .env.example .env
```

按实际情况修改 `.env` 里的 `DATABASE_URL`。第一阶段健康检查和基础测试不会连接真实数据库。

## 配置云端 PostgreSQL

不要把真实数据库密码提交到 git。复制 `.env.example` 为 `.env`，然后填写：

```env
DATABASE_URL=postgresql+asyncpg://用户名:密码@主机:5432/数据库名
```

应用运行时使用 `asyncpg`，`DATABASE_URL` 保持 `postgresql+asyncpg://...` 格式。Alembic 迁移会在内部使用项目依赖里的同步 PostgreSQL 驱动执行建表。

验证数据库连接：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000/api/health/db`，正常时返回：

```json
{"status": "ok", "database": "postgresql"}
```

执行迁移：

```bash
alembic upgrade head
```

启动后端：

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

安装并启动前端：

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

打开：

- 后端健康检查：`http://127.0.0.1:8000/api/health`
- 数据库健康检查：`http://127.0.0.1:8000/api/health/db`
- 前端开发服务：`http://127.0.0.1:5173/`

## 本机验证

后端测试：

```bash
pytest tests/backend -v
ruff check backend tests/backend
```

前端构建：

```bash
cd frontend
npm run build
```

Python 编译检查：

```bash
python -m compileall backend
```

## Outlook OAuth2 取件 API

兼容接口：

- `POST /api/mail_new`：获取最新邮件。
- `POST /api/mail_all`：获取邮件列表。
- `POST /api/process-mailbox`：清空指定邮箱文件夹。

这些接口也支持 GET 参数。参数名保留旧项目习惯：

```json
{
  "email": "your-outlook@example.com",
  "client_id": "microsoft-client-id",
  "refresh_token": "microsoft-refresh-token",
  "mailbox": "INBOX"
}
```

首次调用时，如果带用户 Bearer token，会自动托管到该用户；如果不带 token，会自动托管到公共池。邮箱已托管后，再次调用可只传 `email` 和 `mailbox`，系统会使用数据库里的加密凭据。

也可以使用后台创建的 API Key：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/mail_new" `
  -Headers @{ Authorization = "Bearer mailapi_xxx" } `
  -ContentType "application/json" `
  -Body (@{ email="your-outlook@example.com"; mailbox="INBOX" } | ConvertTo-Json)
```

无法设置请求头时，也支持在 body 里传 `user_token`。API Key 和 `user_token` 都会把新托管邮箱归属到 Key 所属用户。

## 管理后台功能

当前前端已接入真实接口：

- 工作台：显示我的邮箱、公共池、今日取件、失败次数；管理员额外看到全局用户、邮箱和 API Key 统计。
- 邮箱管理：普通用户可托管自己的邮箱、查看公共池、认领公共邮箱、更新自己的凭据、测试取件和禁用自己的邮箱；管理员可筛选全部邮箱，并查看或修改明文 refresh token。
- API Key：用户可创建多个 Key，明文只在创建时显示一次；禁用后不能继续用于取件。
- 验证码取件测试：支持托管邮箱直接取码，也支持临时传 `client_id` 和 `refresh_token`；可按发件人、主题、正文关键词和正则筛选。
- 取件日志：管理员看全部，普通用户只看自己的取件记录。

管理员查看或修改 refresh token 会写入 `audit_logs`。

## 验证码 API

```http
POST /api/verification-code
```

示例：

```json
{
  "email": "your-outlook@example.com",
  "mailbox": "INBOX",
  "sender": "noreply",
  "subject_keyword": "code",
  "regex": "(?<!\\d)\\d{6}(?!\\d)"
}
```

如果邮箱未托管，需要同时传 `client_id` 和 `refresh_token`。如果找到验证码，会返回 `verification_code`、匹配邮件、使用协议和 `trace_id`；找不到时返回 `VERIFICATION_CODE_NOT_FOUND`。

真实 Outlook 验证见：

```text
docs/manual-testing/outlook-oauth-fetch.zh-CN.md
```

## 服务器 Docker 部署

本机没有 Docker 时可以跳过这一节。等开发完成后，在服务器或有 Docker 的机器上执行：

```bash
docker build -t mailapi:latest .
docker run -d -p 8000:8000 --env-file .env --name mailapi mailapi:latest
```

打开：

- `http://服务器IP:8000/api/health`
- `http://服务器IP:8000/`
