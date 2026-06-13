# TASK-20260613-phase3a-outlook-oauth-fetchers

Status: TODO
Owner: Claude
Created by: Codex
Created at: 2026-06-13

## 背景

项目核心是 Outlook OAuth2 取件。设计要求优先 Microsoft Graph；当 Graph 权限不足或 Graph 返回 401/403 时，回退到 IMAP XOAUTH2。

## 目标

实现 Microsoft refresh token 换 access token、Graph 邮件读取/删除、IMAP XOAUTH2 邮件读取/删除，以及统一编排服务。

不实现 FastAPI 兼容入口，不写真实 Outlook token 到仓库。

## 修改范围

- `backend/app/services/mail_types.py`
- `backend/app/services/microsoft_oauth.py`
- `backend/app/services/graph_mail.py`
- `backend/app/services/imap_mail.py`
- `backend/app/services/mail_fetch.py`
- `tests/backend/test_microsoft_oauth.py`
- `tests/backend/test_mail_fetcher.py`

## 建议方案

按 `docs/superpowers/plans/2026-06-13-mailapi-phase-3a-oauth-mail-fetch.zh-CN.md` 的 Task 3 执行。

关键点：
- 单元测试必须用 `httpx.MockTransport` mock Microsoft/Graph，不打真实网络。
- Graph token 使用 `https://graph.microsoft.com/.default` scope。
- IMAP token 使用 `https://outlook.office.com/IMAP.AccessAsUser.All offline_access` scope。
- XOAUTH2 字符串必须严格符合 Microsoft 文档。
- 所有错误都转成项目内结构化异常，不能泄漏 refresh token。

## 测试建议

- `.venv\Scripts\python.exe -m pytest tests/backend/test_microsoft_oauth.py tests/backend/test_mail_fetcher.py -v`
- `.venv\Scripts\python.exe -m pytest tests/backend -v`
- `.venv\Scripts\ruff.exe check backend tests/backend`

## 验收标准

1. Graph OAuth 请求 payload 正确。
2. Graph 消息能映射为统一 `MailItem`。
3. IMAP XOAUTH2 base64 字符串正确。
4. Graph 权限不足时会尝试 IMAP fallback。
5. Graph 和 IMAP 均失败时返回可排查的错误码和消息。

## 风险与回退

真实 Microsoft 行为和 mock 可能有差异。最后必须由真实 Outlook 验证任务兜底。出问题时 revert 本任务 commit。

## Claude 完成记录

Status:
Summary:
Verification:
Notes:
