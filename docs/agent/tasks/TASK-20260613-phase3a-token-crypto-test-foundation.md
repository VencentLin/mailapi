# TASK-20260613-phase3a-token-crypto-test-foundation

Status: DONE
Owner: Claude
Created by: Codex
Created at: 2026-06-13

## 背景

Phase 3A 要保存 Outlook refresh token。refresh token 不能明文落库，且后续会新增多个后端测试文件。当前 `test_auth.py` 和 `test_users_api.py` 里重复了 async SQLite fixture，继续复制会让取件测试变乱。

## 目标

实现 refresh token 加密基础能力，并把后端测试公共 fixture 抽到 `tests/backend/conftest.py`。

不实现邮箱托管、OAuth 请求或取件 API。

## 修改范围

- `pyproject.toml`
- `backend/app/core/config.py`
- `backend/app/core/crypto.py`
- `tests/backend/conftest.py`
- `tests/backend/test_crypto.py`
- `tests/backend/test_auth.py`
- `tests/backend/test_users_api.py`

## 建议方案

按 `docs/superpowers/plans/2026-06-13-mailapi-phase-3a-oauth-mail-fetch.zh-CN.md` 的 Task 1 执行。

关键点：
- 使用 TDD，先写 `tests/backend/test_crypto.py` 并确认失败。
- `TokenCipher` 使用 Fernet，key 由 `TOKEN_ENCRYPTION_KEY` 字符串派生。
- `.env` 不要写真实 token。
- 抽 fixture 时不能改变现有测试语义。

## 测试建议

- `.venv\Scripts\python.exe -m pytest tests/backend/test_crypto.py -v`
- `.venv\Scripts\python.exe -m pytest tests/backend -v`
- `.venv\Scripts\ruff.exe check backend tests/backend`

## 验收标准

1. refresh token 加密后不等于原文。
2. 加密内容可以正确解密。
3. 无效密文会抛 `ValueError`。
4. 后端现有 auth/users 测试仍通过。
5. 测试 fixture 已集中到 `tests/backend/conftest.py`。

## 风险与回退

加密 key 处理会影响未来已保存 token。当前阶段还没有生产 token，可直接 revert 本任务 commit。

## Claude 完成记录

Status: DONE
Summary:
- 新增 `backend/app/core/crypto.py` — TokenCipher 类（Fernet 对称加密，key 通过 SHA-256 派生）
- 新增 `tests/backend/test_crypto.py` — 5 个 TDD 单元测试（加密不等原文、解密还原、错 key 报错、垃圾密文报错、不同 key 不同密文）
- 新增 `tests/backend/conftest.py` — 抽取 test_engine/test_session/client 三个共享 fixture
- 清理 `test_auth.py` 和 `test_users_api.py`，移除重复 fixture 定义，改为引用 conftest.py
- `pyproject.toml` 添加 `cryptography>=44.0.0` 依赖
- `config.py` 新增 `token_encryption_key` 配置项

Verification:
- `ruff check backend tests/backend` — All checks passed
- `pytest tests/backend -v` — 30 passed（含 5 个新 crypto 测试 + 25 个已有测试全部通过）
- 重复 fixture 已消除，test_auth.py 和 test_users_api.py 正确使用 conftest.py 共享 fixture

Notes:
- TokenCipher 使用 Fernet (AES-128-CBC + HMAC)，key 经过 SHA-256 哈希派生为标准 Fernet 格式
- .env 中 TOKEN_ENCRYPTION_KEY 默认值为 "change-me-encryption-key"，生产环境需替换
