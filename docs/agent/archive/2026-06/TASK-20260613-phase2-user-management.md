# TASK-20260613-phase2-user-management

Status: DONE
Owner: Claude
Created by: Codex
Created at: 2026-06-13

## 背景

用户需要看到管理功能。第一步先做管理员用户管理，后续再做邮箱托管、API Key 和日志的真实业务。

## 目标

实现管理员可用的用户列表和创建用户功能。

不实现邮箱托管、API Key 管理或日志查询。

## 修改范围

- `backend/app/api/routes/users.py`
- `backend/app/api/router.py`
- `backend/app/schemas/users.py`
- `backend/app/services/users.py`
- `tests/backend/test_users_api.py`
- `frontend/src/views/users/UserListView.vue`
- `frontend/src/api/users.ts`

## 建议方案

按 `docs/superpowers/plans/2026-06-13-mailapi-phase-2-auth-management-db.md` 的 Task 5 执行。

## 测试建议

- `pytest tests/backend/test_users_api.py -v`
- `pytest tests/backend -v`
- `ruff check backend tests/backend`
- `cd frontend && npm run build`

## 验收标准

1. 管理员可调用 `GET /users`。
2. 普通用户不可调用 `GET /users`。
3. 管理员可创建用户。
4. 前端用户管理页显示数据库用户列表。

## 风险与回退

涉及权限判断，必须有管理员/普通用户两类测试。出问题时 revert 本任务 commit。

## Claude 完成记录

Status: DONE
Summary:
- 后端：创建 `schemas/users.py`（UserCreate），`services/users.py` 新增 `list_users` + `get_user_count`
- 后端：创建 `api/routes/users.py` — `GET /api/users`（管理员列表用户，支持 offset/limit 分页）+ `POST /api/users`（管理员创建用户，409 重复检测）
- 后端：`api/router.py` 注册 users 路由；`require_admin` 依赖检查 UserRole.ADMIN
- 前端：`api/users.ts` — `fetchUsers` + `createUser` 两个 API 函数
- 前端：`UserListView.vue` 完整实现 — el-table 展示用户列表（ID/用户名/邮箱/角色/状态），el-dialog 创建用户表单（含表单验证），loading/error 状态处理

Verification:
- `ruff check backend tests/backend` — All checks passed
- `pytest tests/backend -v` — 24 passed（12 已有 + 8 新用户测试 + 4 数据库/健康检查）
- `cd frontend && npm run build` — vue-tsc 无错误，vite build 成功

Notes:
- 用户管理仅管理员可访问；非管理员返回 403
- 用户列表默认 limit=20，最大 100
- 创建用户默认 role=user, status=active
