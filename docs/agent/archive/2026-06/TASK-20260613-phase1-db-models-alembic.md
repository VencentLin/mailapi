# TASK-20260613-phase1-db-models-alembic

Status: DONE
Owner: Claude
Created by: Codex
Created at: 2026-06-13

## 背景

项目需要 PostgreSQL 作为长期数据源，并用 Alembic 管理表结构。第一阶段只建立基础模型和迁移能力，不实现业务服务。

## 目标

完成 `docs/superpowers/plans/2026-06-13-mailapi-phase-1-foundation.md` 中的 Task 2。

不连接真实云端数据库，不写用户登录或邮箱业务逻辑。

## 修改范围

- `backend/app/db/**`
- `backend/app/models/**`
- `backend/migrations/**`
- `alembic.ini`
- `tests/backend/test_database_metadata.py`

## 建议方案

按 Phase 1 plan 的 Task 2 执行：

- 先写 metadata 测试。
- 添加 SQLAlchemy Base、session、枚举和基础模型。
- 添加 Alembic 配置和第一版 schema migration。
- 运行测试和编译检查。

## 测试建议

- `pytest tests/backend/test_database_metadata.py -v`
- `python -m compileall backend`

## 验收标准

1. `users`、`api_keys`、`mail_accounts`、`mail_account_claims`、`mail_fetch_logs`、`audit_logs` 已注册到 metadata。
2. Alembic 配置存在，并能加载项目 metadata。
3. 编译检查通过。
4. 提交信息为 `feat: add database foundation schema` 或同等清晰信息。

## 风险与回退

涉及数据库结构，后续真实部署前需要再次审核 migration。出问题时 revert 本任务 commit，并重新生成 migration。

## Claude 完成记录

Status: DONE
Summary: Created SQLAlchemy models (User, ApiKey, MailAccount, MailAccountClaim, MailFetchLog, AuditLog), enums, async session factory, Alembic config, and first foundation schema migration. Added ruff exclusion for migration versions directory.
Verification: pytest tests/backend/test_database_metadata.py -v → 2 passed. python -m compileall backend → no errors. pytest tests/backend -v → 3 passed (all). ruff check backend tests/backend → All checks passed. Commit: 63fa94b.
Notes: Migration file line lengths are auto-generated boilerplate, excluded via ruff per-file-ignores.
