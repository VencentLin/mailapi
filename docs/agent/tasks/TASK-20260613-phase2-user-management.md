# TASK-20260613-phase2-user-management

Status: TODO
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

Status:
Summary:
Verification:
Notes:
