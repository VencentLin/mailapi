# MailAPI Phase 3A Outlook OAuth Mail Fetch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Outlook OAuth2 真实取件核心路径，让 `/api/mail_new`、`/api/mail_all` 和 `/api/process-mailbox` 可以使用托管或临时凭据访问 Outlook 邮箱。

**Architecture:** 后端保持 FastAPI + SQLAlchemy 分层。邮箱凭据先进入加密存储和归属解析服务，再由 Microsoft OAuth token provider 获取 access token，优先走 Microsoft Graph；Graph 权限不足时走 IMAP XOAUTH2 fallback。兼容 API 负责入参兼容、自动托管、日志记录和结构化响应。

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, httpx, cryptography/Fernet, imaplib, email.parser, pytest/pytest-asyncio, Ruff, PostgreSQL, optional Redis cache later.

---

## 外部依据

- Microsoft identity platform refresh token：refresh token 可换取新的 access token，且使用后可能返回新的 refresh token，旧 token 要安全替换。
  - <https://learn.microsoft.com/en-us/entra/identity-platform/refresh-tokens>
- Microsoft Graph mailFolder messages：读取指定文件夹消息使用 `GET /me/mailFolders/{id}/messages`，请求必须带 Bearer token。
  - <https://learn.microsoft.com/en-us/graph/api/mailfolder-list-messages?view=graph-rest-1.0>
- Microsoft IMAP OAuth：IMAP XOAUTH2 scope 为 `https://outlook.office.com/IMAP.AccessAsUser.All`，SASL 格式为 `user=<email>\x01auth=Bearer <token>\x01\x01` 再 base64。
  - <https://learn.microsoft.com/en-us/exchange/client-developer/legacy-protocols/how-to-authenticate-an-imap-pop-smtp-application-by-using-oauth>
- 原项目兼容入口：
  - `upstream-MS_OAuth2API_Next/controllers/api.js`
  - `upstream-MS_OAuth2API_Next/services/api.js`
  - `upstream-MS_OAuth2API_Next/services/MailService.js`

## 范围选择

推荐方案：Graph 优先 + IMAP fallback 同阶段打底。

原因：
- 你现在主要使用 Outlook，真实 OAuth2 取件是项目成败核心。
- Graph 是优先路径，错误更清晰，适合后续筛选、删除和日志。
- IMAP fallback 不能继续拖太久，否则 Graph 权限不足的邮箱会看似“系统坏了”。
- 前端邮箱管理页先不做大改，避免核心没通之前消耗在 UI 上。

本阶段做：
- refresh token 加密/解密。
- 邮箱凭据自动托管到用户或公共池。
- 已托管邮箱优先使用数据库凭据，默认忽略请求里重复传入的新凭据。
- Microsoft OAuth refresh token 换 access token。
- Graph 邮件列表、最新邮件、清空邮箱。
- IMAP XOAUTH2 邮件列表、最新邮件、清空邮箱 fallback。
- 兼容 API：`GET/POST /api/mail_new`、`GET/POST /api/mail_all`、`GET/POST /api/process-mailbox`。
- 取件日志写入 `mail_fetch_logs`。
- 真实 Outlook 手工验证文档。

本阶段不做：
- 完整前端邮箱管理 CRUD。
- API Key 创建和鉴权。
- Redis access token 缓存和限流。
- 批量导入/导出。
- 高级验证码规则引擎。
- 多租户共享邮箱。
- 代理支持的完整实现；保留 `socks5`、`http` 入参并记录，但如果 Python HTTP/IMAP 代理未实现，要明确返回/记录 `proxy_not_supported_yet`。

## 文件结构

新增：
- `tests/backend/conftest.py`：统一 async SQLite、client、登录 helper，替代重复 fixture。
- `tests/backend/test_crypto.py`：refresh token 加密测试。
- `tests/backend/test_mail_accounts_service.py`：邮箱托管和归属解析测试。
- `tests/backend/test_microsoft_oauth.py`：Microsoft token provider 单元测试，使用 `httpx.MockTransport`。
- `tests/backend/test_mail_fetcher.py`：Graph/IMAP fetcher 映射、XOAUTH2 和错误 fallback 测试。
- `tests/backend/test_mail_fetch_api.py`：兼容 API、自动托管和日志测试。
- `backend/app/core/crypto.py`：Fernet 加密封装。
- `backend/app/schemas/mail_accounts.py`：邮箱托管 schema。
- `backend/app/schemas/mail_fetch.py`：兼容 API 请求/响应 schema。
- `backend/app/services/mail_accounts.py`：邮箱凭据存储和归属解析。
- `backend/app/services/microsoft_oauth.py`：refresh token -> access token。
- `backend/app/services/mail_types.py`：邮件 DTO、错误类型、协议枚举。
- `backend/app/services/graph_mail.py`：Graph 邮件读取和删除。
- `backend/app/services/imap_mail.py`：IMAP XOAUTH2 读取和删除。
- `backend/app/services/mail_fetch.py`：Graph 优先、IMAP fallback 的取件编排。
- `backend/app/services/mail_fetch_logs.py`：取件日志写入。
- `backend/app/api/routes/mail_fetch.py`：兼容 API 路由。
- `docs/manual-testing/outlook-oauth-fetch.zh-CN.md`：真实 Outlook 验证步骤。

修改：
- `pyproject.toml`：显式加入 `cryptography`，如果测试需要也加入 `respx` 或继续用 `httpx.MockTransport`。
- `.env.example`：增加 `TOKEN_ENCRYPTION_KEY` 示例和 Outlook 手工测试变量说明。
- `backend/app/core/config.py`：增加 `token_encryption_key`。
- `backend/app/api/routes/auth.py`：增加 optional current user dependency，兼容匿名 API 自动托管到公共池。
- `backend/app/api/router.py`：注册 mail fetch 路由。
- `backend/app/models/mail_account.py`：如需要补充关系或状态字段，不做破坏性迁移。
- `tests/backend/test_auth.py`、`tests/backend/test_users_api.py`：移除重复 fixture，改用 `tests/backend/conftest.py`。
- `README.md`：增加 Phase 3A 本地运行和真实取件说明。

## Task 1: 测试夹具和 refresh token 加密

**Files:**
- Create: `tests/backend/conftest.py`
- Create: `tests/backend/test_crypto.py`
- Create: `backend/app/core/crypto.py`
- Modify: `backend/app/core/config.py`
- Modify: `pyproject.toml`
- Modify: `tests/backend/test_auth.py`
- Modify: `tests/backend/test_users_api.py`

- [ ] **Step 1: 写失败测试**

`tests/backend/test_crypto.py`：

```python
from backend.app.core.crypto import TokenCipher


def test_token_cipher_roundtrip():
    cipher = TokenCipher("test-secret")

    encrypted = cipher.encrypt("refresh-token-value")

    assert encrypted != "refresh-token-value"
    assert cipher.decrypt(encrypted) == "refresh-token-value"


def test_token_cipher_rejects_invalid_payload():
    cipher = TokenCipher("test-secret")

    try:
        cipher.decrypt("not-a-valid-fernet-token")
    except ValueError as exc:
        assert "Invalid encrypted token" in str(exc)
    else:
        raise AssertionError("decrypt should reject invalid payload")
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
.venv\Scripts\python.exe -m pytest tests/backend/test_crypto.py -v
```

Expected: `ModuleNotFoundError` 或 `ImportError`，因为 `backend.app.core.crypto` 尚不存在。

- [ ] **Step 3: 实现最小加密封装**

`backend/app/core/crypto.py`：

```python
from __future__ import annotations

from base64 import urlsafe_b64encode
from hashlib import sha256

from cryptography.fernet import Fernet, InvalidToken


class TokenCipher:
    def __init__(self, secret: str) -> None:
        if not secret:
            raise ValueError("TOKEN_ENCRYPTION_KEY must not be empty")
        key = urlsafe_b64encode(sha256(secret.encode("utf-8")).digest())
        self._fernet = Fernet(key)

    def encrypt(self, plain_text: str) -> str:
        return self._fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")

    def decrypt(self, encrypted_text: str) -> str:
        try:
            return self._fernet.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Invalid encrypted token") from exc
```

`backend/app/core/config.py` 增加：

```python
token_encryption_key: str = "change-me-token-encryption-key"
```

`pyproject.toml` dependencies 增加：

```toml
"cryptography>=43.0.0",
```

- [ ] **Step 4: 抽公共测试 fixture**

把 `test_auth.py` 和 `test_users_api.py` 里重复的 `test_engine`、`test_session`、`client`、`login_as` 移到 `tests/backend/conftest.py`。保留 `login_as` 签名：

```python
async def login_as(client: AsyncClient, test_session: AsyncSession, username: str, role: UserRole) -> str:
    ...
```

- [ ] **Step 5: 验证**

Run:

```bash
.venv\Scripts\python.exe -m pytest tests/backend/test_crypto.py -v
.venv\Scripts\python.exe -m pytest tests/backend -v
.venv\Scripts\ruff.exe check backend tests/backend
```

Expected:
- `test_crypto.py` 通过。
- 现有 auth/users 测试仍通过。
- Ruff 无错误。

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml backend/app/core/config.py backend/app/core/crypto.py tests/backend
git commit -m "feat: add encrypted token foundation"
```

## Task 2: 邮箱托管和归属解析服务

**Files:**
- Create: `backend/app/schemas/mail_accounts.py`
- Create: `backend/app/services/mail_accounts.py`
- Create: `tests/backend/test_mail_accounts_service.py`
- Modify: `backend/app/models/mail_account.py` only if relationships are needed.

- [ ] **Step 1: 写失败测试**

覆盖这些行为：

```python
@pytest.mark.asyncio
async def test_authenticated_fetch_auto_creates_user_owned_mailbox(test_session, regular_user):
    resolved = await resolve_mail_account_for_fetch(
        test_session,
        email="User@Outlook.com",
        client_id="client-id",
        refresh_token="refresh-token",
        requested_by=regular_user,
        created_via="api",
    )

    assert resolved.account.email == "user@outlook.com"
    assert resolved.account.owner_type == MailAccountOwnerType.USER
    assert resolved.account.owner_user_id == regular_user.id
    assert resolved.mail_account_status == "auto_created_user"
    assert resolved.credentials.refresh_token == "refresh-token"


@pytest.mark.asyncio
async def test_anonymous_fetch_auto_creates_public_mailbox(test_session):
    resolved = await resolve_mail_account_for_fetch(
        test_session,
        email="public@example.com",
        client_id="client-id",
        refresh_token="refresh-token",
        requested_by=None,
        created_via="api",
    )

    assert resolved.account.owner_type == MailAccountOwnerType.PUBLIC
    assert resolved.account.owner_user_id is None
    assert resolved.mail_account_status == "auto_created_public"


@pytest.mark.asyncio
async def test_existing_mailbox_uses_stored_credentials(test_session, regular_user):
    first = await resolve_mail_account_for_fetch(
        test_session,
        email="same@example.com",
        client_id="stored-client",
        refresh_token="stored-refresh",
        requested_by=regular_user,
        created_via="api",
    )

    second = await resolve_mail_account_for_fetch(
        test_session,
        email="same@example.com",
        client_id="new-client",
        refresh_token="new-refresh",
        requested_by=regular_user,
        created_via="api",
    )

    assert second.account.id == first.account.id
    assert second.credentials.client_id == "stored-client"
    assert second.credentials.refresh_token == "stored-refresh"
    assert second.mail_account_status == "existing_user"
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
.venv\Scripts\python.exe -m pytest tests/backend/test_mail_accounts_service.py -v
```

Expected: `ImportError`，因为服务尚不存在。

- [ ] **Step 3: 实现 schema 和服务**

核心接口：

```python
@dataclass(frozen=True)
class MailCredentials:
    email: str
    client_id: str
    refresh_token: str


@dataclass(frozen=True)
class ResolvedMailAccount:
    account: MailAccount
    credentials: MailCredentials
    mail_account_status: Literal[
        "existing_user",
        "existing_public",
        "auto_created_user",
        "auto_created_public",
    ]
```

函数：

```python
async def resolve_mail_account_for_fetch(
    session: AsyncSession,
    *,
    email: str,
    client_id: str | None,
    refresh_token: str | None,
    requested_by: User | None,
    created_via: str,
) -> ResolvedMailAccount:
    ...
```

规则：
- email 统一 `strip().lower()`。
- 已存在邮箱：解密数据库凭据并返回，忽略请求里新凭据。
- 不存在邮箱且缺少 `client_id` 或 `refresh_token`：抛 `MailAccountCredentialsRequired`。
- 有 `requested_by`：创建 `owner_type=user`、`owner_user_id=requested_by.id`。
- 无 `requested_by`：创建 `owner_type=public`、`owner_user_id=None`。
- `status=active`、`created_via="api"`。

- [ ] **Step 4: 验证**

Run:

```bash
.venv\Scripts\python.exe -m pytest tests/backend/test_mail_accounts_service.py -v
.venv\Scripts\python.exe -m pytest tests/backend -v
.venv\Scripts\ruff.exe check backend tests/backend
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/mail_accounts.py backend/app/services/mail_accounts.py backend/app/models/mail_account.py tests/backend
git commit -m "feat: add mailbox ownership resolution"
```

## Task 3: Microsoft OAuth、Graph 取件和 IMAP fallback

**Files:**
- Create: `backend/app/services/mail_types.py`
- Create: `backend/app/services/microsoft_oauth.py`
- Create: `backend/app/services/graph_mail.py`
- Create: `backend/app/services/imap_mail.py`
- Create: `backend/app/services/mail_fetch.py`
- Create: `tests/backend/test_microsoft_oauth.py`
- Create: `tests/backend/test_mail_fetcher.py`

- [ ] **Step 1: 写 Microsoft OAuth 失败测试**

使用 `httpx.MockTransport`，不要打真实 Microsoft 网络：

```python
@pytest.mark.asyncio
async def test_refresh_graph_token_posts_expected_payload():
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "access_token": "graph-access",
                "refresh_token": "new-refresh",
                "expires_in": 3600,
                "scope": "https://graph.microsoft.com/Mail.Read",
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = MicrosoftOAuthProvider(http_client=client)

    token = await provider.refresh_graph_token("client-id", "old-refresh")

    assert token.access_token == "graph-access"
    assert token.refresh_token == "new-refresh"
    assert token.has_mail_read is True
    assert "grant_type=refresh_token" in requests[0].content.decode()
```

- [ ] **Step 2: 写 Graph fetcher 失败测试**

```python
@pytest.mark.asyncio
async def test_graph_fetch_maps_messages_to_mail_items():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1.0/me/mailFolders/inbox/messages"
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "id": "m1",
                        "from": {"emailAddress": {"address": "sender@example.com"}},
                        "subject": "Code 123456",
                        "bodyPreview": "Your code is 123456",
                        "body": {"content": "<p>Your code is 123456</p>"},
                        "receivedDateTime": "2026-06-13T01:00:00Z",
                    }
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    fetcher = GraphMailFetcher(http_client=client)

    items = await fetcher.list_messages("graph-access", mailbox="INBOX", limit=1)

    assert items[0].id == "m1"
    assert items[0].sender == "sender@example.com"
    assert items[0].subject == "Code 123456"
```

- [ ] **Step 3: 写 IMAP XOAUTH2 失败测试**

```python
def test_generate_xoauth2_string():
    encoded = generate_xoauth2_string("user@example.com", "access-token")

    decoded = base64.b64decode(encoded).decode()

    assert decoded == "user=user@example.com\x01auth=Bearer access-token\x01\x01"
```

- [ ] **Step 4: 实现 token provider**

接口：

```python
@dataclass(frozen=True)
class OAuthToken:
    access_token: str
    refresh_token: str | None
    expires_in: int
    scope: str

    @property
    def has_mail_read(self) -> bool:
        return "Mail.Read" in self.scope or "Mail.ReadWrite" in self.scope
```

Graph token 请求：
- URL: `https://login.microsoftonline.com/consumers/oauth2/v2.0/token`
- Form: `client_id`, `grant_type=refresh_token`, `refresh_token`, `scope=https://graph.microsoft.com/.default`

IMAP token 请求：
- URL: `https://login.microsoftonline.com/consumers/oauth2/v2.0/token`
- Form: `client_id`, `grant_type=refresh_token`, `refresh_token`, `scope=https://outlook.office.com/IMAP.AccessAsUser.All offline_access`

错误要抛 `MicrosoftOAuthError(status_code, error_code, message)`，message 可以包含 Microsoft 返回的 `error_description`，但不要记录完整 refresh token。

- [ ] **Step 5: 实现 Graph fetcher**

规则：
- `INBOX` -> `inbox`
- `Junk` -> `junkemail`
- 其他输入默认 `inbox`
- `list_messages(token, mailbox, limit)` 请求 `GET /v1.0/me/mailFolders/{folder}/messages`
- Query:
  - `$top`: `limit`
  - `$orderby`: `receivedDateTime desc`
  - `$select`: `id,from,subject,bodyPreview,body,receivedDateTime,createdDateTime`
- 返回统一 `MailItem`：

```python
@dataclass(frozen=True)
class MailItem:
    id: str
    sender: str
    subject: str
    text: str
    html: str | None
    received_at: str | None
```

- [ ] **Step 6: 实现 IMAP fallback**

规则：
- 用 `asyncio.to_thread` 包裹 blocking `imaplib.IMAP4_SSL`。
- `generate_xoauth2_string(email, access_token)` 必须符合 Microsoft 文档。
- `list_messages` 默认取最近 `limit` 封。
- MIME 解析用标准库 `email.parser.BytesParser(policy=policy.default)`。
- 返回 `MailItem` 列表，字段尽量和 Graph 对齐。
- `clear_mailbox` 用 IMAP `STORE +FLAGS \Deleted` 和 `EXPUNGE`。

- [ ] **Step 7: 实现编排服务**

`fetch_messages(credentials, mailbox, limit, operation)`：
- 先刷新 Graph token。
- 如果 Graph token `has_mail_read`，走 Graph。
- 如果 Graph OAuth 成功但 scope 不含 Mail.Read，走 IMAP token + IMAP。
- 如果 Graph 请求返回 401/403，走 IMAP fallback。
- 如果两条路径都失败，抛 `MailFetchError`，保留 `error_code` 和 `protocol_attempts`。

- [ ] **Step 8: 验证**

Run:

```bash
.venv\Scripts\python.exe -m pytest tests/backend/test_microsoft_oauth.py tests/backend/test_mail_fetcher.py -v
.venv\Scripts\python.exe -m pytest tests/backend -v
.venv\Scripts\ruff.exe check backend tests/backend
```

- [ ] **Step 9: Commit**

```bash
git add backend/app/services tests/backend/test_microsoft_oauth.py tests/backend/test_mail_fetcher.py
git commit -m "feat: add outlook oauth mail fetchers"
```

## Task 4: 兼容取件 API 和取件日志

**Files:**
- Create: `backend/app/schemas/mail_fetch.py`
- Create: `backend/app/services/mail_fetch_logs.py`
- Create: `backend/app/api/routes/mail_fetch.py`
- Create: `tests/backend/test_mail_fetch_api.py`
- Modify: `backend/app/api/routes/auth.py`
- Modify: `backend/app/api/router.py`

- [ ] **Step 1: 写 API 失败测试**

测试用 monkeypatch 替换真实取件服务，不打 Microsoft 网络：

```python
@pytest.mark.asyncio
async def test_mail_new_auto_creates_public_mailbox_without_token(client, test_session, monkeypatch):
    async def fake_fetch(*args, **kwargs):
        return [
            MailItem(
                id="m1",
                sender="sender@example.com",
                subject="Code",
                text="Your code is 123456",
                html="<p>Your code is 123456</p>",
                received_at="2026-06-13T01:00:00Z",
            )
        ], "graph"

    monkeypatch.setattr("backend.app.services.mail_fetch.fetch_messages", fake_fetch)

    resp = await client.post(
        "/api/mail_new",
        json={
            "email": "public@example.com",
            "client_id": "client-id",
            "refresh_token": "refresh-token",
            "mailbox": "INBOX",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "200"
    assert body["mail_account_status"] == "auto_created_public"
    assert body["data"][0]["subject"] == "Code"
    assert body["data"][0]["verification_code"] == "123456"
```

再覆盖：
- 带 Bearer token 时自动创建用户私有邮箱。
- 已托管邮箱时可以不传 `client_id`/`refresh_token`。
- 缺凭据且未托管返回 400。
- 取件失败也写入 `mail_fetch_logs`。
- GET 请求也可用同样参数。

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
.venv\Scripts\python.exe -m pytest tests/backend/test_mail_fetch_api.py -v
```

Expected: route/import 不存在。

- [ ] **Step 3: 实现 optional auth**

`backend/app/api/routes/auth.py` 增加：

```python
async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User | None:
    if credentials is None:
        return None
    return await get_current_user(credentials, session)
```

- [ ] **Step 4: 实现 schema**

`MailFetchRequest` 字段：
- `email: EmailStr`
- `client_id: str | None = None`
- `refresh_token: str | None = None`
- `mailbox: str = "INBOX"`
- `socks5: str | None = None`
- `http: str | None = None`
- `limit: int = Field(default=1, ge=1, le=100)`

响应 envelope：

```python
class CompatibleMailFetchResponse(BaseModel):
    code: str = "200"
    data: list[MailItemPublic]
    trace_id: str
    protocol: str
    mail_account_status: str
```

`MailItemPublic` 增加 `verification_code: str | None`，验证码提取第一版用正则 `(?<!\d)\d{4,8}(?!\d)`，先从 `text` 再从 `subject`。

- [ ] **Step 5: 实现路由**

`backend/app/api/routes/mail_fetch.py`：
- `@router.api_route("/mail_new", methods=["GET", "POST"])`
- `@router.api_route("/mail_all", methods=["GET", "POST"])`
- `@router.api_route("/process-mailbox", methods=["GET", "POST"])`

GET 从 query 解析，POST 从 JSON body 解析。`mail_new` 强制 `limit=1`，`mail_all` 默认 `limit=50`，`process-mailbox` 调用 clear orchestration。

- [ ] **Step 6: 实现日志**

每次请求生成 `trace_id = uuid.uuid4().hex`。

成功写：
- `operation`: `mail_new` / `mail_all` / `process_mailbox`
- `status`: `success`
- `source_protocol`: `graph` / `imap`
- `duration_ms`
- `mail_account_id`
- `user_id`

失败写：
- `status`: `failed`
- `error_code`
- `error_message`

- [ ] **Step 7: 验证**

Run:

```bash
.venv\Scripts\python.exe -m pytest tests/backend/test_mail_fetch_api.py -v
.venv\Scripts\python.exe -m pytest tests/backend -v
.venv\Scripts\ruff.exe check backend tests/backend
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/routes/auth.py backend/app/api/router.py backend/app/api/routes/mail_fetch.py backend/app/schemas/mail_fetch.py backend/app/services/mail_fetch_logs.py tests/backend/test_mail_fetch_api.py
git commit -m "feat: add compatible mail fetch api"
```

## Task 5: 真实 Outlook 验证和文档

**Files:**
- Create: `docs/manual-testing/outlook-oauth-fetch.zh-CN.md`
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `docs/agent/tasks/TASK-20260613-phase3a-real-outlook-verification.md`

- [ ] **Step 1: 写手工验证文档**

文档必须包含：
- 如何准备 `email`、`client_id`、`refresh_token`。
- 如何确认 Microsoft App 有 Graph `Mail.Read` 或 IMAP `IMAP.AccessAsUser.All` 权限。
- 如何启动本机后端。
- 如何调用：

```powershell
$body = @{
  email = "your-outlook@example.com"
  client_id = "your-client-id"
  refresh_token = "your-refresh-token"
  mailbox = "INBOX"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/mail_new" -ContentType "application/json" -Body $body
```

- 如何带管理员 token 调用，让邮箱托管到当前用户。
- 如何不带 token 调用，让邮箱进入公共池。
- 如何查询 `mail_fetch_logs` 排错。
- 安全提醒：不要把 refresh token 写进 git、聊天记录或任务文档。

- [ ] **Step 2: 更新 `.env.example`**

添加：

```env
TOKEN_ENCRYPTION_KEY=replace-with-a-long-random-secret

# Manual Outlook test only. Do not commit real values.
OUTLOOK_TEST_EMAIL=
OUTLOOK_TEST_CLIENT_ID=
OUTLOOK_TEST_REFRESH_TOKEN=
```

- [ ] **Step 3: 运行自动验证**

Run:

```bash
.venv\Scripts\python.exe -m pytest tests/backend -v
.venv\Scripts\ruff.exe check backend tests/backend
.venv\Scripts\python.exe -m compileall backend
cd frontend
npm run build
```

- [ ] **Step 4: 真实 Outlook 验证**

如果用户已经提供真实 Outlook 测试凭据：
- 用临时环境变量或手工 PowerShell 变量调用，不写入文档。
- 验证 `POST /api/mail_new` 返回 `code=200` 和至少一个邮件对象，或返回空列表但 protocol 成功。
- 验证数据库出现 `mail_accounts` 记录。
- 验证数据库出现 `mail_fetch_logs` 成功记录。
- 验证第二次调用不再要求传 `client_id`/`refresh_token`。

如果没有真实凭据：
- 把本任务状态改为 `BLOCKED`。
- 在完成记录里写明自动测试已通过，真实 Outlook 验证等待用户提供 `email/client_id/refresh_token`。

- [ ] **Step 5: Commit**

```bash
git add .env.example README.md docs/manual-testing/outlook-oauth-fetch.zh-CN.md docs/agent/tasks/TASK-20260613-phase3a-real-outlook-verification.md
git commit -m "docs: add outlook oauth verification guide"
```

## 阶段验收标准

Phase 3A 完成时必须满足：
1. `pytest tests/backend -v` 通过。
2. `ruff check backend tests/backend` 通过。
3. `compileall backend` 通过。
4. `frontend npm run build` 通过。
5. 云端 PGSQL migration 仍在 head。
6. `POST /api/mail_new` 支持临时凭据，并自动托管邮箱。
7. 第二次同邮箱请求可以不传凭据，直接使用数据库托管凭据。
8. 带用户 token 时创建用户私有邮箱；不带 token 时创建公共邮箱。
9. Graph 成功时返回 `protocol=graph`。
10. Graph 权限不足或 Graph 401/403 时尝试 IMAP fallback，并在错误响应或日志里说明 fallback 结果。
11. 成功和失败都写入 `mail_fetch_logs`。
12. 如果没有真实 Outlook 凭据，最后一个任务只能 `BLOCKED`，不能声称真实取件完成。

## 风险和回退

- **OAuth token 失效**：返回结构化错误 `oauth_refresh_failed`，日志记录 Microsoft 错误描述，但不记录 refresh token。
- **Graph 权限不足**：尝试 IMAP fallback；如果 IMAP 权限也不足，返回 `mail_permission_missing`。
- **加密 key 变化**：旧 refresh token 无法解密；部署文档必须提示服务器 `TOKEN_ENCRYPTION_KEY` 不能随便更换。
- **代理参数**：本阶段保留入参，不保证完整代理链路；如果未实现要返回明确错误，避免假装支持。
- **真实 Outlook 测试凭据缺失**：自动测试可以通过，但阶段不能标记真实取件完成。
- **回退方式**：每个 Claude 任务独立 commit；出问题优先 revert 对应 commit。
