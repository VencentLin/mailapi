# Outlook Reauthorize Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a mailbox-management "重新授权" action that sends the user through Microsoft OAuth authorization-code flow and replaces an expired stored refresh token.

**Architecture:** The backend generates a signed short-lived OAuth `state` tied to the current MailAPI user and mail account, exchanges Microsoft callback `code` for tokens, verifies the Microsoft profile email matches the mail account, encrypts the new refresh token, and redirects back to the SPA. The frontend adds a row action that opens the Microsoft authorization URL and displays success/failure messages after callback.

**Tech Stack:** FastAPI, SQLAlchemy async, httpx, python-jose JWT, Vue 3, Element Plus.

---

### Task 1: Backend OAuth Configuration And Service

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/microsoft_oauth.py`
- Test: `tests/backend/test_mail_accounts_api.py`

- [ ] **Step 1: Write failing tests**

Add tests that expect:
- `POST /api/mail-accounts/{id}/reauthorize-url` returns a Microsoft authorization URL for a manageable account.
- `GET /api/oauth/microsoft/callback` exchanges `code`, verifies the profile email, encrypts the new refresh token, marks the account active, clears `last_error_code`, and redirects to `/mail-accounts?reauthorize=success`.
- A mismatched Microsoft profile email redirects with failure and does not update stored credentials.

- [ ] **Step 2: Verify red**

Run:

```powershell
pytest tests/backend/test_mail_accounts_api.py -k reauthorize -v
```

Expected: tests fail because the endpoints and service do not exist.

- [ ] **Step 3: Implement service**

Add Microsoft OAuth settings, a signed state helper, authorization URL builder, token exchange, and Graph `/me` profile lookup.

- [ ] **Step 4: Verify green**

Run:

```powershell
pytest tests/backend/test_mail_accounts_api.py -k reauthorize -v
```

Expected: reauthorize tests pass.

### Task 2: Backend Routes

**Files:**
- Modify: `backend/app/api/routes/mail_accounts.py`
- Create: `backend/app/api/routes/oauth.py`
- Modify: `backend/app/api/router.py`
- Modify: `backend/app/schemas/mail_accounts.py`
- Modify: `.env.example`

- [ ] **Step 1: Add response schema**

Create `MailAccountReauthorizeUrlResponse` with `auth_url` and `expires_in`.

- [ ] **Step 2: Add mail-account URL endpoint**

Add `POST /api/mail-accounts/{account_id}/reauthorize-url`, restricted to users who can manage the account.

- [ ] **Step 3: Add callback endpoint**

Add `GET /api/oauth/microsoft/callback`, validate state, update credentials, audit the action, and redirect with success or failure query params.

- [ ] **Step 4: Document required environment**

Add Microsoft OAuth env names to `.env.example`.

### Task 3: Frontend Mailbox Action

**Files:**
- Modify: `frontend/src/api/mailAccounts.ts`
- Modify: `frontend/src/views/mail/MailAccountListView.vue`

- [ ] **Step 1: Add API wrapper**

Add `createMailAccountReauthorizeUrl(id)` returning `{ auth_url, expires_in }`.

- [ ] **Step 2: Add row action**

Add a "重新授权" button for manageable accounts. Clicking it requests the URL and navigates `window.location.href` to Microsoft.

- [ ] **Step 3: Add callback message handling**

On `/mail-accounts?reauthorize=success|failed`, show an Element Plus message, remove callback query params, and reload accounts.

### Task 4: Verification And Commit

**Files:**
- All modified files

- [ ] **Step 1: Run backend tests**

```powershell
pytest tests/backend/test_mail_accounts_api.py -k reauthorize -v
pytest tests/backend -v
```

- [ ] **Step 2: Run lint**

```powershell
ruff check backend tests/backend
```

- [ ] **Step 3: Run frontend build**

```powershell
cd frontend
npm run build
```

- [ ] **Step 4: Commit**

```powershell
git add .
git commit -m "feat: add outlook reauthorization flow"
```
