from __future__ import annotations

import pytest
from sqlalchemy import text

from backend.app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from backend.app.models.enums import UserRole, UserStatus
from backend.app.services.users import create_user

# ---------------------------------------------------------------------------
# password hashing unit tests (no DB needed)
# ---------------------------------------------------------------------------


def test_password_hash_verifies_correct_password():
    password = "a-strong-password"
    h = hash_password(password)
    assert password != h
    assert verify_password(password, h) is True


def test_password_hash_rejects_wrong_password():
    h = hash_password("correct")
    assert verify_password("wrong", h) is False


# ---------------------------------------------------------------------------
# JWT unit tests
# ---------------------------------------------------------------------------


def test_create_and_decode_access_token_roundtrip():
    token = create_access_token(subject="42")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"


def test_decode_tampered_token_raises():
    token = create_access_token(subject="1")
    with pytest.raises(ValueError, match="Invalid"):
        decode_access_token(token[:-3] + "xxx")


# ---------------------------------------------------------------------------
# auth endpoint tests (fixtures from conftest.py)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_returns_token_for_active_user(client, test_session):
    await create_user(
        test_session,
        username="alice",
        email="alice@example.com",
        password="secret123",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )

    resp = await client.post("/auth/login", json={"username": "alice", "password": "secret123"})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_rejects_disabled_user(client, test_session):
    await create_user(
        test_session,
        username="bob",
        email="bob@example.com",
        password="secret123",
        role=UserRole.USER,
        status=UserStatus.DISABLED,
    )

    resp = await client.post("/auth/login", json={"username": "bob", "password": "secret123"})
    assert resp.status_code == 401
    assert "Invalid" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(client, test_session):
    await create_user(
        test_session,
        username="carol",
        email="carol@example.com",
        password="correct",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )

    resp = await client.post("/auth/login", json={"username": "carol", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_rejects_unknown_user(client):
    resp = await client.post("/auth/login", json={"username": "ghost", "password": "x"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register_creates_disabled_user_pending_admin_review(client, test_session):
    resp = await client.post(
        "/auth/register",
        json={
            "username": "pending",
            "email": "pending@example.com",
            "password": "secret123",
        },
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "pending"
    assert body["email"] == "pending@example.com"
    assert body["role"] == "user"
    assert body["status"] == "disabled"

    login_resp = await client.post(
        "/auth/login",
        json={"username": "pending", "password": "secret123"},
    )
    assert login_resp.status_code == 401

    row = await test_session.execute(
        text("SELECT * FROM users WHERE username = 'pending'")
    )
    user = row.mappings().one()
    assert user["status"] == "disabled"


@pytest.mark.asyncio
async def test_register_rejects_duplicate_username_or_email(client, test_session):
    await create_user(
        test_session,
        username="registered",
        email="registered@example.com",
        password="pw",
        role=UserRole.USER,
        status=UserStatus.DISABLED,
    )

    dup_username = await client.post(
        "/auth/register",
        json={
            "username": "registered",
            "email": "new-registered@example.com",
            "password": "secret123",
        },
    )
    assert dup_username.status_code == 409

    dup_email = await client.post(
        "/auth/register",
        json={
            "username": "newregistered",
            "email": "registered@example.com",
            "password": "secret123",
        },
    )
    assert dup_email.status_code == 409


@pytest.mark.asyncio
async def test_me_returns_current_user_for_valid_token(client, test_session):
    await create_user(
        test_session,
        username="dan",
        email="dan@example.com",
        password="pw",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )

    login_resp = await client.post("/auth/login", json={"username": "dan", "password": "pw"})
    token = login_resp.json()["access_token"]

    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "dan"
    assert body["email"] == "dan@example.com"
    assert body["role"] == "user"
    assert body["status"] == "active"


@pytest.mark.asyncio
async def test_me_rejects_missing_token(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_rejects_invalid_token(client):
    resp = await client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_last_login_is_updated_on_login(client, test_session):
    await create_user(
        test_session,
        username="eve",
        email="eve@example.com",
        password="pw",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )

    resp = await client.post("/auth/login", json={"username": "eve", "password": "pw"})
    assert resp.status_code == 200

    row = (
        await test_session.execute(
            text("SELECT * FROM users WHERE username = 'eve'")
        )
    )
    user = row.mappings().one()
    assert user["last_login_at"] is not None
