# TASK-20260613-phase3a-real-outlook-verification

Status: TODO
Owner: Claude
Created by: Codex
Created at: 2026-06-13

## 背景

OAuth2 相关代码只有 mock 测试不够。Phase 3A 必须用真实 Outlook 邮箱验证至少一次，否则不能声称核心取件完成。

## 目标

补充真实 Outlook 验证文档，运行完整自动验证，并在用户提供真实测试凭据时完成真实 API 取件验收。

不把真实 `email/client_id/refresh_token` 写入 git、任务文档或 README。

## 修改范围

- `.env.example`
- `README.md`
- `docs/manual-testing/outlook-oauth-fetch.zh-CN.md`
- `docs/agent/tasks/TASK-20260613-phase3a-real-outlook-verification.md`

## 建议方案

按 `docs/superpowers/plans/2026-06-13-mailapi-phase-3a-oauth-mail-fetch.zh-CN.md` 的 Task 5 执行。

如果没有真实 Outlook 测试凭据，本任务必须标记 `BLOCKED`，并写明等待用户提供：
- Outlook 邮箱地址
- client_id
- refresh_token

## 测试建议

- `.venv\Scripts\python.exe -m pytest tests/backend -v`
- `.venv\Scripts\ruff.exe check backend tests/backend`
- `.venv\Scripts\python.exe -m compileall backend`
- `cd frontend && npm run build`
- 手工调用 `POST /api/mail_new`
- 手工验证第二次同邮箱调用可不传 `client_id`/`refresh_token`

## 验收标准

1. 自动测试全部通过。
2. 文档说明如何准备和验证 Outlook OAuth2。
3. 真实 Outlook `mail_new` 至少成功返回一次可解释结果：有邮件列表，或空列表但 protocol 成功。
4. 数据库有对应 `mail_accounts` 记录。
5. 数据库有对应 `mail_fetch_logs` 记录。
6. 未提供真实凭据时状态为 `BLOCKED`，不能写 `DONE`。

## 风险与回退

真实 refresh token 极敏感，绝不提交。真实验证失败时先记录错误码、Microsoft 返回描述、trace_id，再交给 Codex 分析。

## Claude 完成记录

Status:
Summary:
Verification:
Notes:
