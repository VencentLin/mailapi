# MailAPI 设计文档

日期：2026-06-13

## 目标

基于 `HChaoHui/MS_OAuth2API_Next` 的业务能力，开发一个云端部署的验证码取件平台，但后端改用 Python 重写，方便以后长期维护。

系统需要保留原项目的 API 取件方式，同时新增：

- 多用户网页管理。
- 基于角色的权限控制。
- Outlook 邮箱凭据托管。
- 公共邮箱池和用户认领流程。
- 用户自己的 API Key。
- 直接提取验证码。
- PostgreSQL 持久化存储。
- 一个 Docker 镜像内包含后端、前端和 Redis。

Outlook OAuth2 是核心功能。系统优先使用 Microsoft Graph；如果 Graph 权限不足，再回退到 IMAP XOAUTH2。

## 参考项目调研结论

上游项目是 Koa/Node 后端，加 Vue/Vite 前端。

现有可参考能力：

- `POST/GET /api/mail_new`：获取最新一封邮件。
- `POST/GET /api/mail_all`：获取邮件列表。
- `POST/GET /api/process-mailbox`：清空指定邮箱文件夹。
- `POST/GET /api/test-proxy`：测试代理。
- 优先 Graph API，Graph 邮件权限不可用时回退 IMAP。
- Redis 缓存 access token。
- 每次请求可传 HTTP/SOCKS 代理。

需要避免继承的问题：

- 前端把邮箱凭据存在 `localStorage`。
- 没有真正的用户、角色、API Key、数据库邮箱归属。
- 全局密码中间件太粗糙。
- 项目里虽然有 MySQL 依赖，但当前业务流程没有真正使用数据库。
- OAuth2 和 IMAP 错误信息不够清楚，不利于排查。

新项目只参考它的业务思路，不沿用 Node 代码结构。

## 最终选择方案

后端完整改用 Python 重写，前端也重新整理为正式管理后台。

后端技术栈：

- FastAPI。
- SQLAlchemy 2.x 异步 ORM。
- Alembic 数据库迁移。
- PostgreSQL，驱动使用 `asyncpg`。
- Redis 用于 OAuth access token 缓存、限流和短期状态。
- Pydantic 做请求和响应校验。

前端技术栈：

- Vue 3。
- Vite。
- Element Plus。
- Pinia。
- Vue Router，并按角色控制菜单。

部署方式：

- 最终交付一个 Docker 镜像。
- 镜像内包含 FastAPI、构建好的 Vue 静态文件、Redis、Alembic 迁移脚本和启动脚本。
- PostgreSQL 使用外部云数据库。
- 对外只暴露 FastAPI 的 HTTP 端口。

## 角色和权限

角色：

- `admin`：管理所有用户、所有邮箱、所有 API Key 和所有日志。
- `user`：管理自己的邮箱、认领公共邮箱、创建自己的 API Key、查看自己的日志。

邮箱可见性：

- 管理员可以看到所有邮箱。
- 管理员可以按归属用户、公共池、邮箱地址、状态、协议可用性筛选。
- 普通用户可以看到自己的邮箱和公共池邮箱。
- 普通用户不能看到其他普通用户的私有邮箱。

凭据可见性：

- 管理员可以查看、复制、修改 `client_id` 和 `refresh_token`。
- 普通用户可以新增或更新自己的邮箱凭据。
- 普通用户看到的敏感字段默认脱敏。
- `refresh_token` 必须加密存储。
- 管理员查看明文 `refresh_token` 必须记录审计日志。
- 修改邮箱凭据后，必须清理对应 OAuth access token 缓存。

未来共享权限：

- 第一版不做团队/多人共享邮箱。
- 数据库设计要预留以后增加邮箱共享表的空间。

## 邮箱归属规则

邮箱归属类型：

- `user`：某个用户私有邮箱。
- `public`：公共池邮箱，普通用户可以认领。

规则：

- API 请求带有效 API Key 或用户 token，且邮箱未托管时，自动托管到该用户。
- API 请求没有用户 token，且邮箱未托管时，自动托管到公共池。
- 邮箱已经托管时，直接使用数据库里的凭据取件。
- 邮箱已经托管时，即使请求又传了新凭据，默认也忽略，避免误覆盖已有资产。
- 公共池邮箱按先到先得认领。
- 认领后，`owner_type` 从 `public` 改为 `user`，并写入 `owner_user_id`。
- 认领后，普通用户不再能从公共池看到这个邮箱。
- 管理员仍然可以查看和修改已认领邮箱。

## 后端模块

### Auth

职责：

- 后台登录。
- 签发和校验 JWT 会话。
- 密码哈希。
- 角色检查。
- API Key 哈希、创建、轮换、禁用和过期控制。

API Key 规则：

- 一个用户可以创建多个 API Key。
- 每个 Key 有名称、哈希后的密钥、状态、可选过期时间、权限范围、最后使用时间和所属用户。
- 明文 API Key 只在创建时展示一次。
- API 请求推荐使用 `Authorization: Bearer <api_key>`。
- 对不能设置请求头的调用方，也支持在 body 里传 `user_token`。

### Mail Accounts

职责：

- 单个邮箱创建。
- 批量导入。
- 公共池列表。
- 邮箱认领。
- 管理员筛选。
- 凭据加密和解密。
- 凭据更新后清理 token 缓存。

### Mail Fetcher

职责：

- 从数据库或请求参数解析邮箱凭据。
- 用 refresh token 换 Microsoft access token。
- 有 `Mail.Read` 权限时优先使用 Microsoft Graph。
- Graph 邮件权限不可用时，回退 Outlook IMAP XOAUTH2。
- 获取最新邮件或全部邮件。
- 清空 `INBOX` 或 `Junk`。
- 支持每次请求传代理，也支持邮箱默认代理。
- 返回结构化、可诊断的错误。

协议流程：

1. 标准化邮箱文件夹：`INBOX` 映射到 Graph 的 `inbox`，`Junk` 映射到 Graph 的 `junkemail`。
2. 用 `https://graph.microsoft.com/.default` scope 尝试换 Graph access token。
3. 如果 Graph token 包含 `Mail.Read` 权限，使用 Graph API 取件。
4. 如果 Graph 不可用或权限不足，换取 IMAP 使用的 access token。
5. 使用 XOAUTH2 登录 `outlook.office365.com:993`。
6. 拉取并解析邮件。

### Verification Codes

职责：

- 通过 mail fetcher 获取候选邮件。
- 按发件人、主题关键词、正文关键词、邮箱文件夹和时间窗口过滤。
- 使用调用方传入的正则，或默认数字验证码规则提取验证码。
- 返回最新匹配验证码和匹配邮件摘要。
- 如果调用方要求，可以在成功取码后删除或清空邮件。

### Logs

取件日志记录：

- Trace ID。
- 调用用户。
- API Key。
- 邮箱。
- 使用协议：`graph` 或 `imap`。
- 调用结果。
- 错误码。
- 耗时。
- 请求过滤条件。
- 创建时间。

审计日志记录：

- 用户创建、修改、禁用、重置密码。
- API Key 创建、禁用、删除、重置。
- 邮箱创建、导入、修改、删除、认领。
- 管理员查看 refresh token。
- 管理员修改 refresh token。

## 数据模型

### `users`

- `id`
- `username`
- `email`
- `password_hash`
- `role`：`admin` 或 `user`
- `status`：`active` 或 `disabled`
- `created_at`
- `updated_at`
- `last_login_at`

### `api_keys`

- `id`
- `user_id`
- `name`
- `key_prefix`
- `key_hash`
- `scopes`
- `status`：`active`、`disabled` 或 `expired`
- `expires_at`
- `last_used_at`
- `created_at`
- `updated_at`

### `mail_accounts`

- `id`
- `email`
- `client_id`
- `refresh_token_encrypted`
- `owner_type`：`user` 或 `public`
- `owner_user_id`
- `status`：`active`、`disabled` 或 `invalid`
- `default_proxy`
- `last_protocol`：`graph` 或 `imap`
- `last_success_at`
- `last_error_code`
- `remark`
- `created_by_user_id`
- `created_via`：`admin`、`user_web`、`api_user_token` 或 `api_public`
- `created_at`
- `updated_at`

约束：

- 第一版中，`email` 全局唯一。
- `owner_type = user` 时，`owner_user_id` 必须有值。
- `owner_type = public` 时，`owner_user_id` 为空。

### `mail_account_claims`

- `id`
- `mail_account_id`
- `claimed_by_user_id`
- `claimed_at`
- `previous_owner_type`

### `mail_fetch_logs`

- `id`
- `trace_id`
- `user_id`
- `api_key_id`
- `mail_account_id`
- `email`
- `mailbox`
- `operation`
- `source_protocol`
- `status`
- `error_code`
- `error_message`
- `duration_ms`
- `created_at`

### `audit_logs`

- `id`
- `actor_user_id`
- `action`
- `target_type`
- `target_id`
- `metadata`
- `ip_address`
- `created_at`

### `verification_rules`

- `id`
- `owner_user_id`
- `mail_account_id`
- `name`
- `sender`
- `subject_keyword`
- `body_keyword`
- `regex`
- `is_default`
- `created_at`
- `updated_at`

这张表第一版可以先不实现，但设计上要允许以后增加它，而不破坏验证码 API。

## HTTP API

### 后台登录

- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/logout`

### 用户管理

仅管理员：

- `GET /users`
- `POST /users`
- `PATCH /users/{id}`
- `POST /users/{id}/reset-password`

### 邮箱管理

- `GET /mail-accounts`
- `POST /mail-accounts`
- `POST /mail-accounts/import`
- `GET /mail-accounts/{id}`
- `PATCH /mail-accounts/{id}`
- `DELETE /mail-accounts/{id}`
- `POST /mail-accounts/{id}/claim`
- `POST /mail-accounts/{id}/test-fetch`
- `POST /mail-accounts/{id}/clear`

管理员凭据操作：

- `GET /mail-accounts/{id}/credentials`
- `PATCH /mail-accounts/{id}/credentials`

### API Key

- `GET /api-keys`
- `POST /api-keys`
- `PATCH /api-keys/{id}`
- `DELETE /api-keys/{id}`

### 日志

- `GET /logs/mail-fetch`
- `GET /logs/audit`

管理员可以看全部日志。普通用户只能看自己的日志。

### 兼容取件 API

- `POST /api/mail_new`
- `POST /api/mail_all`
- `POST /api/process-mailbox`
- `POST /api/test-proxy`

兼容要求：

- 尽量保留原参数名：`email`、`client_id`、`refresh_token`、`mailbox`、`socks5`、`http`。
- 支持 `INBOX` 和 `Junk`。
- 支持请求头里的 API Key。
- 支持 body 里的 `user_token`。
- 如果邮箱已经托管，`client_id` 和 `refresh_token` 可不传。
- 如果邮箱未托管，必须传 `client_id` 和 `refresh_token`。

### 验证码 API

`POST /api/verification-code`

请求字段：

- `email`
- `mailbox`：`INBOX` 或 `Junk`
- `sender`
- `subject_keyword`
- `body_keyword`
- `since_minutes`
- `regex`
- `delete_after_fetch`
- `client_id`
- `refresh_token`
- `socks5`
- `http`
- `user_token`

响应字段：

- `code`
- `matched_email`
- `source_protocol`
- `mail_account_status`：`existing_user`、`existing_public`、`auto_created_user` 或 `auto_created_public`
- `trace_id`

如果没找到验证码，返回 `VERIFICATION_CODE_NOT_FOUND`，并带上 trace ID。

## 前端设计

前端是正式管理后台，不做落地页。

页面：

- 登录页。
- 工作台。
- 邮箱管理。
- 邮箱详情。
- 验证码取件测试。
- API Key 管理。
- 用户管理。
- 取件日志。
- 审计日志。

工作台：

- 普通用户看到自己的邮箱数量、公共池数量、今日取件次数、失败次数和最近错误。
- 管理员额外看到全局用户数量、全局邮箱数量、API 调用量和全局失败概况。

邮箱管理：

- 普通用户可以看自己的邮箱和公共池邮箱。
- 管理员可以查看和筛选所有邮箱。
- 支持单个创建、批量导入、编辑、禁用、删除、认领、测试取件、清空邮箱和查看日志。
- 公共池邮箱显示“认领”操作。
- 普通用户看到的敏感凭据脱敏。
- 管理员可以打开凭据面板查看或修改 `client_id` 和 `refresh_token`。

验证码取件测试：

- 选择托管邮箱，或临时输入凭据。
- 配置发件人、主题关键词、正文关键词、时间窗口和正则。
- 显示验证码、匹配邮件、协议、耗时和 trace ID。
- 失败时显示可诊断错误信息。

API Key 管理：

- 创建多个 Key。
- 设置名称、权限范围和可选过期时间。
- 明文 Key 只展示一次。
- 支持禁用或删除。

用户管理：

- 仅管理员可见。
- 创建普通用户和管理员。
- 启用或禁用用户。
- 重置密码。
- 查看用户邮箱和 API Key 概况。

日志：

- 取件日志可按用户、API Key、邮箱、结果、错误码、时间范围筛选。
- 审计日志可按操作者、操作、对象和时间范围筛选。

## 错误处理

每个 API 请求都应该有 `trace_id`。

常见错误码：

- `MAIL_ACCOUNT_NOT_FOUND`
- `MAIL_ACCOUNT_CREDENTIAL_REQUIRED`
- `MAIL_ACCOUNT_DISABLED`
- `OAUTH_REFRESH_FAILED`
- `GRAPH_PERMISSION_MISSING`
- `GRAPH_FETCH_FAILED`
- `IMAP_AUTH_FAILED`
- `IMAP_FETCH_FAILED`
- `PROXY_CONNECT_FAILED`
- `VERIFICATION_CODE_NOT_FOUND`
- `API_KEY_EXPIRED`
- `API_KEY_DISABLED`
- `API_KEY_SCOPE_DENIED`
- `PERMISSION_DENIED`

错误响应结构：

```json
{
  "error_code": "OAUTH_REFRESH_FAILED",
  "message": "Failed to refresh Microsoft OAuth token.",
  "trace_id": "..."
}
```

OAuth2、Graph、IMAP 失败时，必须写入 `mail_fetch_logs`。

## 安全

- 密码使用 Argon2 或 bcrypt 等现代哈希算法保存。
- API Key 只保存哈希。
- refresh token 加密落库。
- 通过环境变量 `TOKEN_ENCRYPTION_KEY` 提供加密密钥。
- 日志里不能记录明文 refresh token。
- 除管理员凭据接口外，不能返回明文 refresh token。
- 管理员查看或更新 refresh token 必须记录审计日志。
- 权限判断必须在后端执行，不能只依赖前端隐藏菜单。
- 生产环境 CORS 要严格限制。

## 部署

最终部署产物是一个 Docker 镜像。

镜像包含：

- Python 运行时和 FastAPI 应用。
- 构建好的 Vue 前端静态文件。
- Redis 服务。
- Alembic 迁移文件。
- 启动脚本。

外部服务：

- 云端 PostgreSQL 数据库。

容器启动流程：

1. 启动容器内 Redis。
2. 等待 Redis 可以连接。
3. 读取环境变量。
4. 连接 PostgreSQL。
5. 如果 `RUN_MIGRATIONS=true`，执行 `alembic upgrade head`。
6. 如果还没有管理员，可选初始化默认管理员。
7. 启动 FastAPI。
8. 同一个端口同时服务 API 和前端静态文件。

暴露端口：

- 只暴露 FastAPI HTTP 端口，例如 `8000`。
- Redis 不对外暴露。

环境变量：

- `DATABASE_URL`
- `SECRET_KEY`
- `TOKEN_ENCRYPTION_KEY`
- `RUN_MIGRATIONS`
- `INIT_ADMIN_USERNAME`
- `INIT_ADMIN_PASSWORD`
- `INIT_ADMIN_EMAIL`
- `REDIS_URL`，默认指向容器内 Redis。
- `ACCESS_TOKEN_CACHE_TTL_SECONDS`
- `LOG_LEVEL`

Redis 不是长期数据源。它只用于 OAuth access token 缓存、限流和短期状态。Redis 数据丢失不能影响邮箱归属、用户、API Key 或日志。

## 测试策略

后端测试：

- 用户登录和 JWT 校验。
- API Key 创建、哈希校验、禁用、过期和权限范围。
- 邮箱创建、导入、列表、更新、删除和认领。
- 公共池先到先得认领。
- 管理员全局邮箱筛选。
- 普通用户可见性限制。
- 管理员查看和修改 refresh token 的审计日志。
- 托管邮箱凭据解析。
- 带认证 API 请求自动创建用户私有邮箱。
- 不带认证 API 请求自动创建公共池邮箱。
- Graph token 换取。
- Graph 权限不足时回退 IMAP。
- IMAP XOAUTH2 登录流程。
- 默认规则提取验证码。
- 调用方传入正则提取验证码。
- 关键词和时间窗口过滤。
- 结构化错误响应和取件日志。

前端测试：

- 登录和按角色控制路由。
- 管理员和普通用户的邮箱列表过滤。
- 公共邮箱认领流程。
- API Key 创建流程，以及明文 Key 只展示一次。
- 验证码测试表单和结果展示。
- 管理员凭据面板。

部署检查：

- Docker 镜像可以构建。
- 容器可以启动 Redis 和 FastAPI。
- 前端路由可以回退到 `index.html`。
- `/docs` 或健康检查接口可以访问。
- 开启迁移时 PostgreSQL 迁移可以执行。

## 给 Claude 的实施边界

Claude 后续需要按这个 spec 拆成多个独立任务执行。

推荐顺序：

1. 搭建 FastAPI 后端、配置、数据库、Alembic 和健康检查。
2. 添加单 Docker 镜像构建和 Redis 启动流程。
3. 实现登录、用户、API Key 和权限。
4. 实现加密邮箱存储和归属规则。
5. 实现 Outlook OAuth2 Graph 取件。
6. 实现 IMAP XOAUTH2 回退。
7. 实现兼容取件 API。
8. 实现验证码 API。
9. 实现日志和审计。
10. 构建 Vue 管理后台。
11. 添加测试和部署验证。

第一个实现里程碑应该先证明 Outlook OAuth2 核心取件路径可用，再打磨完整前端。
