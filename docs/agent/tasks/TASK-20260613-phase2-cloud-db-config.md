# TASK-20260613-phase2-cloud-db-config

Status: TODO
Owner: Claude
Created by: Codex
Created at: 2026-06-13

## 背景

用户反馈云端 PostgreSQL 还没有配置。当前代码已经从 `.env` 读取 `DATABASE_URL`，但缺少数据库连接检查接口和清晰的本机配置说明。

## 目标

完成 Phase 2 计划中的 Task 1：云 PostgreSQL 配置和连接检查。

不把真实数据库账号密码提交到 git。

## 修改范围

- `.env.example`
- `README.md`
- `backend/app/api/routes/health.py`
- `tests/backend/test_health.py`

## 建议方案

按 `docs/superpowers/plans/2026-06-13-mailapi-phase-2-auth-management-db.md` 的 Task 1 执行。

关键点：

- 新增 `/api/health/db`。
- 文档说明 `.env` 中如何填写云端 `DATABASE_URL`。
- 如果用户尚未提供真实连接串，代码和测试照常完成，真实 DB 验证标记为 BLOCKED。

## 测试建议

- `pytest tests/backend/test_health.py -v`
- `ruff check backend tests/backend`
- 有真实 `.env` 后运行 `alembic upgrade head` 并访问 `/api/health/db`

## 验收标准

1. `.env.example` 的 DATABASE_URL 格式清晰。
2. README 写明本机如何配置云端 PGSQL。
3. `/api/health/db` 能检查数据库连接。
4. 无真实凭据时不阻塞代码测试，但完成记录必须说明真实 DB 验证未执行。

## 风险与回退

真实云数据库凭据不能提交。若迁移失败，不要修改迁移文件猜测修复，先记录错误输出。

## Claude 完成记录

Status:
Summary:
Verification:
Notes:
