# TASK-20260613-phase3a-mail-account-ownership

Status: DONE
Owner: Claude
Created by: Codex
Created at: 2026-06-13

## 背景

用户要求：后台已托管邮箱时 API 直接取件；未托管且传入用户 token 时自动托管到该用户；未传用户 token 时托管到公共账户，用户可在前端看到并认领。

## 目标

实现后端邮箱凭据存储和归属解析服务，供后续取件 API 调用。

不实现 Graph/IMAP 真实取件，不实现前端邮箱管理。

## 修改范围

- `backend/app/schemas/mail_accounts.py`
- `backend/app/services/mail_accounts.py`
- `backend/app/models/mail_account.py`（仅在关系需要时修改）
- `tests/backend/test_mail_accounts_service.py`

## 建议方案

按 `docs/superpowers/plans/2026-06-13-mailapi-phase-3a-oauth-mail-fetch.zh-CN.md` 的 Task 2 执行。

关键规则：
- email 必须 `strip().lower()`。
- 已存在邮箱默认使用数据库凭据，忽略请求里的新凭据。
- 不存在邮箱且无用户：创建公共邮箱。
- 不存在邮箱且有用户：创建用户私有邮箱。
- refresh token 必须用 Task 1 的 `TokenCipher` 加密落库。

## 测试建议

- `.venv\Scripts\python.exe -m pytest tests/backend/test_mail_accounts_service.py -v`
- `.venv\Scripts\python.exe -m pytest tests/backend -v`
- `.venv\Scripts\ruff.exe check backend tests/backend`

## 验收标准

1. 认证用户首次 API 请求会自动创建 user-owned mailbox。
2. 匿名请求会自动创建 public mailbox。
3. 已存在邮箱使用存储凭据。
4. 未托管邮箱缺少 `client_id` 或 `refresh_token` 时返回明确业务异常。
5. 数据库中不保存明文 refresh token。

## 风险与回退

涉及邮箱资产归属，必须有用户/公共/已存在三类测试。出问题时 revert 本任务 commit。

## Claude 完成记录

Status: DONE
Summary:
- 新增 `backend/app/schemas/mail_accounts.py` — MailAccountResolve (输入), MailAccountResolved (输出)
- 新增 `backend/app/services/mail_accounts.py` — resolve_or_create_mail_account 服务函数
  - email 统一 strip().lower() 归一化
  - 已存在邮箱 → 返回已有记录（忽略新凭据）
  - 不存在 + 有用户 → 创建 user-owned
  - 不存在 + 无用户 → 创建 public
  - 缺少 client_id 或 refresh_token → MailAccountNotReadyError
  - refresh_token 通过 TokenCipher 加密落库
- 新增 `tests/backend/test_mail_accounts_service.py` — 8 个测试覆盖所有场景

Verification:
- `ruff check backend tests/backend` — All checks passed
- `pytest tests/backend -q` — 38 passed

Notes:
- 任务范围仅为 service 层，不包含 API 路由或前端页面
- 加密后的 refresh_token 在数据库中不可读为明文
