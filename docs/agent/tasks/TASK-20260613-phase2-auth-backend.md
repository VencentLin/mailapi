# TASK-20260613-phase2-auth-backend

Status: TODO
Owner: Claude
Created by: Codex
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

Status:
Summary:
Verification:
Notes:
