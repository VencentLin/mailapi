# TASK-20260613-phase1-backend-scaffold

Status: DONE
Owner: Claude
Created by: Codex
Created at: 2026-06-13

## 背景

MailAPI 当前只有设计文档，还没有可运行代码。第一步需要建立 FastAPI 后端基线，保证项目能被测试工具导入，并提供健康检查接口。

## 目标

完成 `docs/superpowers/plans/2026-06-13-mailapi-phase-1-foundation.md` 中的 Task 1。

不实现登录、邮箱托管、OAuth2 或数据库业务逻辑。

## 修改范围

- `pyproject.toml`
- `backend/app/**`
- `tests/backend/test_health.py`

## 建议方案

按 Phase 1 plan 的 Task 1 执行：

- 先写 `tests/backend/test_health.py`。
- 运行测试确认失败。
- 创建 FastAPI app factory、配置模块、API router 和 `/api/health`。
- 再运行测试和 ruff。

## 测试建议

- `pytest tests/backend/test_health.py -v`
- `ruff check backend tests/backend`

## 验收标准

1. `/api/health` 返回 `status/service/version`。
2. 后端测试通过。
3. Ruff 不报错。
4. 提交信息为 `feat: scaffold fastapi backend` 或同等清晰信息。

## 风险与回退

风险较低。出问题时 revert 本任务 commit 即可。

## Claude 完成记录

Status: DONE
Summary: Created FastAPI backend scaffold with health endpoint, config module, API router, and SPA fallback. Installed all dependencies and verified with pytest and ruff.
Verification: pytest tests/backend/test_health.py -v → 1 passed. ruff check backend tests/backend → All checks passed. Commit: ec568fd.
Notes: LF/CRLF warnings are Windows-only and harmless.
