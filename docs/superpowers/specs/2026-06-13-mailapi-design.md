# MailAPI Design

Date: 2026-06-13

## Goal

Build a cloud-deployed verification-code mail retrieval platform based on the business capability of `HChaoHui/MS_OAuth2API_Next`, but rewrite the application in Python for long-term maintainability.

The system must keep the original API-style mail retrieval workflow while adding:

- Multi-user web management.
- Role-based permissions.
- Managed Outlook mailbox credentials.
- Public mailbox pool and user claim flow.
- User-owned API keys.
- Direct verification-code extraction.
- PostgreSQL persistence.
- One Docker image containing backend, frontend, and Redis.

Outlook OAuth2 support is the core requirement. Microsoft Graph should be preferred, with IMAP XOAUTH2 as the compatibility fallback.

## Reference Project Findings

The upstream project is a Koa/Node service with a Vue/Vite frontend.

Relevant existing capabilities:

- `POST/GET /api/mail_new`: fetch latest email.
- `POST/GET /api/mail_all`: fetch all emails.
- `POST/GET /api/process-mailbox`: clear a mailbox folder.
- `POST/GET /api/test-proxy`: test proxy routing.
- Graph API first, IMAP fallback when Graph mail permission is unavailable.
- Redis access-token cache.
- Optional HTTP/SOCKS proxy per request.

Limitations to avoid carrying forward:

- Frontend stores mailbox credentials in `localStorage`.
- No real users, roles, API keys, or database-backed mailbox ownership.
- Password middleware is global and coarse-grained.
- MySQL dependency exists, but the current business flow does not use it.
- Error handling hides too much diagnostic information for OAuth2 and IMAP failures.

The new project should reuse the business ideas, not the Node code structure.

## Chosen Approach

Use a full Python backend rewrite and a reorganized Vue frontend.

Backend:

- FastAPI.
- SQLAlchemy 2.x async ORM.
- Alembic migrations.
- PostgreSQL via `asyncpg`.
- Redis for OAuth access-token cache, rate limiting, and short-lived state.
- Pydantic schemas for request and response validation.

Frontend:

- Vue 3.
- Vite.
- Element Plus.
- Pinia.
- Vue Router with role-aware menus.

Deployment:

- One Docker image.
- The image contains FastAPI, built Vue static assets, Redis, Alembic migrations, and startup scripts.
- PostgreSQL stays external and is provided by the existing cloud database.
- Only the FastAPI HTTP port is exposed.

## Roles And Permissions

Roles:

- `admin`: can manage all users, all mailboxes, all API keys, and all logs.
- `user`: can manage their own mailboxes, claim public mailboxes, create their own API keys, and view their own logs.

Mailbox visibility:

- Admins can see every mailbox.
- Admins can filter by owner user, public pool, email address, status, and protocol availability.
- Ordinary users can see their own mailboxes and public-pool mailboxes.
- Ordinary users cannot see other users' private mailboxes.

Credential visibility:

- Admins can view, copy, and modify `client_id` and `refresh_token`.
- Ordinary users can add or update credentials for their own mailboxes.
- Ordinary users see sensitive fields masked by default.
- Refresh tokens must be encrypted at rest.
- Admin plaintext refresh-token views must be recorded in audit logs.
- Updating mailbox credentials must clear related OAuth access-token cache entries.

Future sharing:

- First version does not implement team/shared mailbox permissions.
- The schema should leave room for a future mailbox sharing table.

## Mailbox Ownership Rules

Mailbox ownership types:

- `user`: private mailbox owned by one user.
- `public`: public-pool mailbox that can be claimed by any ordinary user.

Rules:

- If an API request includes a valid API key or user token and the mailbox is not yet managed, automatically create the mailbox under that user.
- If an API request does not include a user token and the mailbox is not yet managed, automatically create the mailbox in the public pool.
- If the mailbox already exists, use the stored credentials for retrieval.
- If the mailbox already exists and the request also includes credentials, ignore those credentials by default to avoid accidental overwrites.
- Public-pool mailboxes are claimed on a first-come, first-served basis.
- Claiming changes `owner_type` from `public` to `user` and sets `owner_user_id`.
- After claim, the mailbox disappears from the public pool for ordinary users.
- Admins can still view and modify the mailbox after claim.

## Backend Modules

### Auth

Responsibilities:

- Web login.
- JWT session issuance and validation.
- Password hashing.
- Role checks.
- API key hashing, creation, rotation, disabling, and expiry.

API keys:

- A user can create multiple API keys.
- Each key has a name, hashed secret, status, optional expiry, scopes, last-used timestamp, and owner user.
- Plaintext API key is shown only once at creation time.
- API requests should prefer `Authorization: Bearer <api_key>`.
- Body parameter `user_token` is allowed for clients that cannot set headers.

### Mail Accounts

Responsibilities:

- Single mailbox creation.
- Batch import.
- Public-pool listing.
- Claiming.
- Admin filtering.
- Credential encryption and decryption.
- Credential update and token-cache invalidation.

### Mail Fetcher

Responsibilities:

- Resolve mailbox credentials from storage or request payload.
- Exchange refresh token for Microsoft access token.
- Prefer Microsoft Graph when `Mail.Read` permission is available.
- Fall back to Outlook IMAP XOAUTH2 when Graph mail permission is unavailable.
- Fetch latest mail or all mail.
- Clear `INBOX` or `Junk`.
- Support per-request proxy and stored default proxy.
- Return structured diagnostic errors.

Protocol flow:

1. Normalize mailbox folder: `INBOX` maps to Graph `inbox`, `Junk` maps to Graph `junkemail`.
2. Try Graph access-token exchange with scope `https://graph.microsoft.com/.default`.
3. If Graph token has `Mail.Read`, fetch via Graph API.
4. If Graph is unavailable or permission is missing, exchange a token for IMAP usage.
5. Authenticate to `outlook.office365.com:993` using XOAUTH2.
6. Fetch and parse messages.

### Verification Codes

Responsibilities:

- Fetch candidate messages using the mail fetcher.
- Filter by sender, subject keyword, body keyword, mailbox, and time window.
- Extract codes using either a caller-provided regex or default numeric-code rules.
- Return the newest matching code and the matched email summary.
- Optionally delete or clear after successful fetch when requested.

### Logs

Mail fetch logs record:

- Trace ID.
- Calling user.
- API key.
- Mailbox.
- Source protocol: `graph` or `imap`.
- Result status.
- Error code.
- Duration.
- Request filters.
- Created time.

Audit logs record:

- User creation, update, disable, and password reset.
- API key creation, disable, delete, and reset.
- Mailbox creation, import, update, delete, and claim.
- Admin refresh-token view.
- Admin refresh-token update.

## Data Model

### `users`

- `id`
- `username`
- `email`
- `password_hash`
- `role`: `admin` or `user`
- `status`: `active` or `disabled`
- `created_at`
- `updated_at`
- `last_login_at`

### `api_keys`

- `id`
- `user_id`
- `name`
- `key_prefix`
- `key_hash`
- `scopes`
- `status`: `active`, `disabled`, or `expired`
- `expires_at`
- `last_used_at`
- `created_at`
- `updated_at`

### `mail_accounts`

- `id`
- `email`
- `client_id`
- `refresh_token_encrypted`
- `owner_type`: `user` or `public`
- `owner_user_id`
- `status`: `active`, `disabled`, or `invalid`
- `default_proxy`
- `last_protocol`: `graph` or `imap`
- `last_success_at`
- `last_error_code`
- `remark`
- `created_by_user_id`
- `created_via`: `admin`, `user_web`, `api_user_token`, or `api_public`
- `created_at`
- `updated_at`

Constraints:

- `email` should be globally unique in the first version.
- `owner_user_id` is required when `owner_type = user`.
- `owner_user_id` is null when `owner_type = public`.

### `mail_account_claims`

- `id`
- `mail_account_id`
- `claimed_by_user_id`
- `claimed_at`
- `previous_owner_type`

### `mail_fetch_logs`

- `id`
- `trace_id`
- `user_id`
- `api_key_id`
- `mail_account_id`
- `email`
- `mailbox`
- `operation`
- `source_protocol`
- `status`
- `error_code`
- `error_message`
- `duration_ms`
- `created_at`

### `audit_logs`

- `id`
- `actor_user_id`
- `action`
- `target_type`
- `target_id`
- `metadata`
- `ip_address`
- `created_at`

### `verification_rules`

- `id`
- `owner_user_id`
- `mail_account_id`
- `name`
- `sender`
- `subject_keyword`
- `body_keyword`
- `regex`
- `is_default`
- `created_at`
- `updated_at`

This table is optional in the first implementation, but the design should allow adding it without changing the verification-code API contract.

## HTTP API

### Web Auth

- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/logout`

### Users

Admin only:

- `GET /users`
- `POST /users`
- `PATCH /users/{id}`
- `POST /users/{id}/reset-password`

### Mail Accounts

- `GET /mail-accounts`
- `POST /mail-accounts`
- `POST /mail-accounts/import`
- `GET /mail-accounts/{id}`
- `PATCH /mail-accounts/{id}`
- `DELETE /mail-accounts/{id}`
- `POST /mail-accounts/{id}/claim`
- `POST /mail-accounts/{id}/test-fetch`
- `POST /mail-accounts/{id}/clear`

Admin credential operations:

- `GET /mail-accounts/{id}/credentials`
- `PATCH /mail-accounts/{id}/credentials`

### API Keys

- `GET /api-keys`
- `POST /api-keys`
- `PATCH /api-keys/{id}`
- `DELETE /api-keys/{id}`

### Logs

- `GET /logs/mail-fetch`
- `GET /logs/audit`

Admins see all logs. Ordinary users see only their own logs.

### Compatible Retrieval API

- `POST /api/mail_new`
- `POST /api/mail_all`
- `POST /api/process-mailbox`
- `POST /api/test-proxy`

Compatibility requirements:

- Keep original parameter names where practical: `email`, `client_id`, `refresh_token`, `mailbox`, `socks5`, `http`.
- Support `INBOX` and `Junk`.
- Support API key in `Authorization` header.
- Support `user_token` in body for clients that cannot send custom headers.
- If managed credentials exist, `client_id` and `refresh_token` are optional.
- If managed credentials do not exist, `client_id` and `refresh_token` are required.

### Verification-Code API

`POST /api/verification-code`

Request fields:

- `email`
- `mailbox`: `INBOX` or `Junk`
- `sender`
- `subject_keyword`
- `body_keyword`
- `since_minutes`
- `regex`
- `delete_after_fetch`
- `client_id`
- `refresh_token`
- `socks5`
- `http`
- `user_token`

Response fields:

- `code`
- `matched_email`
- `source_protocol`
- `mail_account_status`: `existing_user`, `existing_public`, `auto_created_user`, or `auto_created_public`
- `trace_id`

If no code is found, return `VERIFICATION_CODE_NOT_FOUND` with the trace ID.

## Frontend Design

The frontend should be an actual management console, not a landing page.

Pages:

- Login.
- Dashboard.
- Mailbox management.
- Mailbox detail.
- Verification-code test.
- API key management.
- User management.
- Mail fetch logs.
- Audit logs.

Dashboard:

- Ordinary users see their mailbox count, public-pool count, today's fetch count, failure count, and recent errors.
- Admins also see global user count, global mailbox count, API call count, and global failure summary.

Mailbox management:

- Ordinary users can view their own mailboxes and public-pool mailboxes.
- Admins can view and filter all mailboxes.
- Supports single create, batch import, edit, disable, delete, claim, test fetch, clear mailbox, and log viewing.
- Public mailboxes show a claim action.
- Sensitive credentials are masked for ordinary users.
- Admins can open a credential panel to view or modify `client_id` and `refresh_token`.

Verification-code test:

- Select a managed mailbox or enter temporary credentials.
- Configure sender, subject keyword, body keyword, time window, and regex.
- Show code, matched email, protocol, duration, and trace ID.
- Show diagnostic error details when retrieval fails.

API key management:

- Create multiple keys.
- Configure name, scopes, and optional expiry.
- Show plaintext key only once.
- Disable or delete keys.

User management:

- Admin only.
- Create users and admins.
- Enable or disable users.
- Reset password.
- View user mailbox and API key summary.

Logs:

- Fetch logs can be filtered by user, API key, mailbox, result, error code, and time range.
- Audit logs can be filtered by actor, action, target, and time range.

## Error Handling

Every API request should have a `trace_id`.

Common error codes:

- `MAIL_ACCOUNT_NOT_FOUND`
- `MAIL_ACCOUNT_CREDENTIAL_REQUIRED`
- `MAIL_ACCOUNT_DISABLED`
- `OAUTH_REFRESH_FAILED`
- `GRAPH_PERMISSION_MISSING`
- `GRAPH_FETCH_FAILED`
- `IMAP_AUTH_FAILED`
- `IMAP_FETCH_FAILED`
- `PROXY_CONNECT_FAILED`
- `VERIFICATION_CODE_NOT_FOUND`
- `API_KEY_EXPIRED`
- `API_KEY_DISABLED`
- `API_KEY_SCOPE_DENIED`
- `PERMISSION_DENIED`

Error responses must be structured:

```json
{
  "error_code": "OAUTH_REFRESH_FAILED",
  "message": "Failed to refresh Microsoft OAuth token.",
  "trace_id": "..."
}
```

OAuth2, Graph, and IMAP failures must write a `mail_fetch_logs` row.

## Security

- Store password hashes with a modern password hasher such as Argon2 or bcrypt.
- Store API keys as hashes only.
- Store refresh tokens encrypted at rest.
- Use `TOKEN_ENCRYPTION_KEY` from environment variables.
- Do not log plaintext refresh tokens.
- Do not return plaintext refresh tokens except through the admin credential endpoint.
- Record audit logs for admin refresh-token views and updates.
- Enforce backend permissions even if frontend hides menu items.
- CORS should be restrictive in production.

## Deployment

Local development and server deployment are separate:

- Local development does not require Docker.
- Developers run FastAPI and Vite directly on the host.
- When local development needs a database, it connects to the cloud PostgreSQL through `DATABASE_URL`.
- Redis-backed features can use a local or remote Redis during development; when Redis is unavailable, the task completion notes must state which checks were skipped.
- Docker is built only for final server deployment or verification on a machine that has Docker.

The final deployment artifact is one Docker image.

The image contains:

- Python runtime and FastAPI app.
- Built Vue frontend static files.
- Redis server.
- Alembic migration files.
- Startup script.

External services:

- PostgreSQL cloud database.

Container startup:

1. Start Redis inside the container.
2. Wait for Redis to accept connections.
3. Read environment variables.
4. Connect to PostgreSQL.
5. If `RUN_MIGRATIONS=true`, run `alembic upgrade head`.
6. Optionally create the default admin if no admin exists.
7. Start FastAPI.
8. Serve API routes and frontend static files from the same exposed port.

Exposed ports:

- Expose only the FastAPI HTTP port, for example `8000`.
- Do not expose Redis outside the container.

Environment variables:

- `DATABASE_URL`
- `SECRET_KEY`
- `TOKEN_ENCRYPTION_KEY`
- `RUN_MIGRATIONS`
- `INIT_ADMIN_USERNAME`
- `INIT_ADMIN_PASSWORD`
- `INIT_ADMIN_EMAIL`
- `REDIS_URL`, defaulting to local container Redis.
- `ACCESS_TOKEN_CACHE_TTL_SECONDS`
- `LOG_LEVEL`

Redis is not the source of truth. It is used for OAuth access-token cache, rate limiting, and short-lived state. Losing Redis data must not break mailbox ownership, users, API keys, or logs.

## Testing Strategy

Backend tests:

- User login and JWT validation.
- API key create, hash validation, disable, expiry, and scope checks.
- Mailbox create, import, list, update, delete, and claim.
- Public-pool claim first-come behavior.
- Admin global mailbox filtering.
- Ordinary-user visibility restrictions.
- Admin refresh-token view and update audit logs.
- Managed mailbox resolution.
- Auto-create user-owned mailbox from authenticated API request.
- Auto-create public mailbox from unauthenticated API request.
- Graph token exchange.
- Graph permission-missing fallback to IMAP.
- IMAP XOAUTH2 authentication flow.
- Verification-code extraction with default rule.
- Verification-code extraction with caller regex.
- Keyword and time-window filtering.
- Structured error responses and fetch logs.

Frontend tests:

- Login and role-aware routing.
- Mailbox list filtering for admin and ordinary users.
- Public mailbox claim flow.
- API key create flow with one-time key display.
- Verification-code test form and result rendering.
- Admin credential panel behavior.

Deployment checks:

- Docker image builds.
- Container starts Redis and FastAPI.
- Frontend routes fall back to `index.html`.
- `/docs` or health endpoint is reachable.
- PostgreSQL migrations run when enabled.

## Implementation Boundaries For Claude

Claude should execute from this spec using separate implementation tasks.

Recommended order:

1. Scaffold FastAPI backend, settings, database, Alembic, and health check.
2. Add Docker single-image build with Redis startup.
3. Implement auth, users, API keys, and permissions.
4. Implement encrypted mailbox storage and ownership rules.
5. Implement Outlook OAuth2 Graph mail fetch.
6. Implement IMAP XOAUTH2 fallback.
7. Implement compatible mail APIs.
8. Implement verification-code API.
9. Implement logs and audit trails.
10. Build Vue management console.
11. Add tests and deployment verification.

The first implementation milestone should prove the Outlook OAuth2 core path works before polishing the full frontend.
