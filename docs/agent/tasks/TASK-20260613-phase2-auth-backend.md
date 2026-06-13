# TASK-20260613-phase2-auth-backend

Status: DONE
Created at: 2026-06-13

## 背景

当前后端只有健康检查，没有登录接口。前端无法进行真实登录，也无法根据用户角色展示管理功能。

## 目标

实现后端登录、JWT、当前用户接口和默认管理员初始化命令。

不实现 API Key、邮箱托管或验证码取件。

## 修改范围

- `backend/app/core/security.py`
- `backend/app/core/config.py`
- `backend/app/api/routes/auth.py`
- `backend/app/api/router.py`
- `backend/app/schemas/auth.py`
- `backend/app/services/users.py`
- `backend/app/cli.py`
- `pyproject.toml`
- `tests/backend/test_auth.py`

## 建议方案

按 `docs/superpowers/plans/2026-06-13-mailapi-phase-2-auth-management-db.md` 的 Task 2 执行。

## 执行方式

这是一个偏大的认证任务，Claude 不要试图一次性吞完所有 Phase 2 任务；本任务也要按 checkpoint 逐段完成。

恢复会话时先做：

1. 运行 `git status --short --branch`。
2. 如果看到 `backend/app/core/config.py`、`pyproject.toml`、`backend/app/core/security.py`、`backend/app/schemas/auth.py` 等未提交改动，先阅读这些文件并继续，不要重建或回滚。
3. 只执行本任务，不要开始前端登录、管理导航或用户管理任务。

Checkpoint 顺序：

1. **配置和安全基础**
   - 确认 `pyproject.toml` 包含 `pwdlib[argon2]` 和 `aiosqlite`。
   - 确认 `backend/app/core/config.py` 支持 `secret_key`、`access_token_expire_minutes`、`init_admin_username`、`init_admin_password`、`init_admin_email`。
   - 确认 `backend/app/core/security.py` 已实现密码哈希、密码校验、JWT 创建和 JWT 解码。

2. **用户服务**
   - 创建或补全 `backend/app/services/users.py`。
   - 至少提供按用户名查用户、认证用户、创建用户、创建默认管理员的函数。
   - 不在这里实现 API Key、邮箱托管或验证码取件。

3. **认证路由**
   - 创建 `backend/app/api/routes/auth.py`。
   - 实现 `POST /auth/login` 和 `GET /auth/me`。
   - 在 `backend/app/api/router.py` 注册 auth router。

4. **管理员初始化 CLI**
   - 创建 `backend/app/cli.py`。
   - 实现 `python -m backend.app.cli create-admin`。
   - 如果管理员已存在，打印清楚提示，不重复创建。

5. **测试和提交**
   - 创建 `tests/backend/test_auth.py`，覆盖密码、登录、`/auth/me`、禁用用户不能登录、初始化管理员。
   - 运行本任务测试和全量后端基础测试。
   - 验证通过后填写完成记录，把状态改为 `DONE`，再提交。

如果中途必须退出：

- 保持 `Status: IN_PROGRESS`。
- 在“Claude 完成记录”里追加 `Checkpoint:`、`Next:`、`Blocking:` 三行。
- 不要把未验证的任务标成 `DONE`。

## 测试建议

- `pytest tests/backend/test_auth.py -v`
- `pytest tests/backend -v`
- `ruff check backend tests/backend`
- `python -m compileall backend`

## 验收标准

1. `POST /auth/login` 可返回 JWT。
2. `GET /auth/me` 可返回当前用户。
3. 禁用用户不能登录。
4. `python -m backend.app.cli create-admin` 可从环境变量初始化管理员。

## 风险与回退

涉及认证，必须有自动化测试。出问题时 revert 本任务 commit。

## Claude 完成记录

Status: DONE
Summary:
- `backend/app/core/security.py`：密码哈希（pwdlib/argon2）、密码校验、JWT 创建（python-jose HS256）和 JWT 解码。
- `backend/app/core/config.py`：新增 `secret_key`、`access_token_expire_minutes`、`init_admin_*` 三个环境变量配置。
- `backend/app/api/routes/auth.py`：实现 `POST /auth/login`（返回 JWT）、`GET /auth/me`（返回当前用户）、`get_current_user` 依赖（Bearer token 验证）。
- `backend/app/schemas/auth.py`：`LoginRequest`、`TokenResponse`、`UserPublic` Pydantic 模型。
- `backend/app/services/users.py`：`get_user_by_username`、`get_user_by_email`、`get_user_by_id`、`authenticate_user`、`touch_last_login`、`create_user`、`ensure_admin_user`。
- `backend/app/cli.py`：`python -m backend.app.cli create-admin` 从环境变量初始化管理员。
- `backend/app/main.py`：注册 auth router。
- `pyproject.toml`：新增 `pwdlib[argon2]`、`python-jose[cryptography]` 依赖；`aiosqlite`、`pytest-asyncio` dev 依赖；ruff 忽略 API 路由文件 B008。
- `tests/backend/test_auth.py`：12 个测试（密码哈希 2 + JWT 2 + 登录 4 + /me 3 + last_login 1）。
- `backend/app/models/user.py`：修复 `User.mail_accounts` 关系的 `foreign_keys` 歧义。

Verification:
- `python -m pytest tests/backend/test_auth.py -v` → 12 passed
- `python -m pytest tests/backend -v` → 14 passed（含之前 2 个 health 测试）
- `python -m ruff check backend tests/backend` → All checks passed
- `python -m compileall backend` → OK

Notes:
- 缺少的依赖已在当前 venv 手动安装（pytest-asyncio、pwdlib[argon2]、pydantic-settings、aiosqlite、asyncpg、email-validator）。后续需确保 `pip install -e ".[dev]"` 能工作（当前因 flat-layout 报错未修复，但不阻塞本任务）。
- `User.mail_accounts` 外键歧义修复：显式指定 `foreign_keys="MailAccount.owner_user_id"`。
