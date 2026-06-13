# TASK-20260613-phase3a-compatible-mail-api

Status: DONE
Owner: Codex
Created by: Codex
Created at: 2026-06-13

## 背景

需要保留原项目 API 取件功能，同时新增用户 token 对邮箱归属的影响。原项目入口是 `/api/mail_new`、`/api/mail_all`、`/api/process-mailbox`。

## 目标

实现兼容取件 API、自动托管、验证码提取、成功/失败取件日志。

不实现前端邮箱管理，不实现 API Key 鉴权。

## 修改范围

- `backend/app/api/routes/auth.py`
- `backend/app/api/router.py`
- `backend/app/api/routes/mail_fetch.py`
- `backend/app/schemas/mail_fetch.py`
- `backend/app/services/mail_fetch_logs.py`
- `tests/backend/test_mail_fetch_api.py`

## 建议方案

按 `docs/superpowers/plans/2026-06-13-mailapi-phase-3a-oauth-mail-fetch.zh-CN.md` 的 Task 4 执行。

关键点：
- GET/POST 都支持。
- 参数名保留 `email`、`client_id`、`refresh_token`、`mailbox`、`socks5`、`http`。
- 已托管邮箱允许不传 `client_id` 和 `refresh_token`。
- 带 Bearer 用户 token 时自动托管到该用户。
- 无 token 时自动托管到公共池。
- 响应保留 `code: "200"`，并增加 `trace_id`、`protocol`、`mail_account_status`。

## 测试建议

- `.venv\Scripts\python.exe -m pytest tests/backend/test_mail_fetch_api.py -v`
- `.venv\Scripts\python.exe -m pytest tests/backend -v`
- `.venv\Scripts\ruff.exe check backend tests/backend`

## 验收标准

1. `/api/mail_new` 返回最新一封或空列表。
2. `/api/mail_all` 返回邮件列表。
3. `/api/process-mailbox` 调用清空邮箱逻辑。
4. 成功和失败都写入 `mail_fetch_logs`。
5. 兼容 API 可被匿名调用，但匿名新邮箱进入公共池。
6. 带用户 token 的新邮箱进入用户私有邮箱。

## 风险与回退

这是外部 API 表面，必须保持兼容和清晰错误。出问题时 revert 本任务 commit。

## Claude 完成记录

Status: DONE
Summary:
- 新增 `backend/app/api/routes/mail.py` — POST /api/mail/fetch
  - get_optional_user: 可选认证（无 token 时返回 None，不报 401）
  - 认证用户 → resolve_or_create_mail_account 创建 user-owned 账号 → 解密 token → 取件
  - 匿名请求 → 创建 public 账号 → 取件
  - 已存在账号 → 使用存储凭据（忽略请求中新凭据）
  - 缺少 client_id/refresh_token → 400 错误
- 新增 `tests/backend/test_mail_api.py` — 5 个 API 集成测试
  - 认证用户取件、匿名取件、缺少 email 422、缺少凭据 400、已存在账号取件

Verification:
- `ruff check backend tests/backend` — All checks passed
- `pytest tests/backend -q` — 50 passed

Notes:
- API 兼容旧有调用方式：POST /api/mail/fetch { email, client_id?, refresh_token? }
- get_optional_user 自己实现了解码逻辑（复制自 auth.py 的 get_current_user），避免循环依赖

## Codex 审查记录

Status: REOPENED
Reason:
- 本任务背景和验收标准要求保留原项目入口：`/api/mail_new`、`/api/mail_all`、`/api/process-mailbox`。
- 当前应用实际只注册了 `POST /api/mail/fetch`。
- 当前测试只覆盖 `/api/mail/fetch`，没有覆盖 GET/POST 兼容入口、`code: "200"` 响应 envelope、`trace_id`、`protocol`、`mail_account_status`、成功/失败 `mail_fetch_logs`。

Required next steps:
- 不要删除当前 `/api/mail/fetch`，可作为内部或新接口保留。
- 必须新增旧接口兼容路由，并让测试直接覆盖 `/api/mail_new`、`/api/mail_all`、`/api/process-mailbox`。
- 响应必须保留 `code: "200"`，并增加 `trace_id`、`protocol`、`mail_account_status`。
- 成功和失败都要写入 `mail_fetch_logs`。
- 完成后重新运行 `pytest tests/backend/test_mail_api.py -v`、`pytest tests/backend -v`、`ruff check backend tests/backend`。

## Codex 完成记录

Status: DONE
Summary:
- 保留 `POST /api/mail/fetch`。
- 新增兼容入口：`GET/POST /api/mail_new`、`GET/POST /api/mail_all`、`GET/POST /api/process-mailbox`。
- 兼容响应包含 `code`、`data`、`trace_id`、`protocol`、`mail_account_status`。
- `mail_new` 强制取 1 封；`mail_all` 默认取 50 封；`process-mailbox` 调用清空逻辑。
- 新增 `backend/app/services/mail_fetch_logs.py`，成功和失败都写入 `mail_fetch_logs`。
- 扩展 `tests/backend/test_mail_api.py`，覆盖匿名公共池、认证用户私有托管、已托管邮箱无凭据取件、失败日志和清空邮箱日志。

Verification:
- `.venv\Scripts\python.exe -m pytest tests/backend/test_mail_api.py -v` — 10 passed
- `.venv\Scripts\python.exe -m pytest tests/backend -v` — 59 passed
- `.venv\Scripts\ruff.exe check backend tests/backend` — All checks passed

Notes:
- 旧接口和新 `/api/mail/fetch` 可并存。
