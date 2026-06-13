from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from hmac import compare_digest
from hmac import new as hmac_new
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.models.api_key import ApiKey
from backend.app.models.enums import ApiKeyStatus, UserStatus
from backend.app.models.user import User

API_KEY_PREFIX_LENGTH = 16
API_KEY_PUBLIC_PREFIX = "mailapi_"


class ApiKeyAuthError(Exception):
    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        status_code: int = 401,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class VerifiedApiKey:
    api_key: ApiKey
    user: User


def generate_api_key_value() -> str:
    return f"{API_KEY_PUBLIC_PREFIX}{token_urlsafe(32)}"


def api_key_prefix(api_key_value: str) -> str:
    return api_key_value[:API_KEY_PREFIX_LENGTH]


def hash_api_key(api_key_value: str) -> str:
    secret = get_settings().secret_key.encode("utf-8")
    digest = hmac_new(secret, api_key_value.encode("utf-8"), sha256).hexdigest()
    return digest


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


async def create_api_key(
    session: AsyncSession,
    *,
    user: User,
    name: str,
    scopes: list[str] | None = None,
    expires_at: datetime | None = None,
) -> tuple[ApiKey, str]:
    api_key_value = generate_api_key_value()
    api_key = ApiKey(
        user_id=user.id,
        name=name,
        key_prefix=api_key_prefix(api_key_value),
        key_hash=hash_api_key(api_key_value),
        scopes=scopes or [],
        status=ApiKeyStatus.ACTIVE,
        expires_at=expires_at,
    )
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)
    return api_key, api_key_value


async def list_api_keys(
    session: AsyncSession,
    *,
    user: User,
    target_user_id: int | None = None,
    include_all: bool = False,
) -> list[ApiKey]:
    stmt = select(ApiKey).order_by(ApiKey.id.desc())
    if include_all:
        if target_user_id is not None:
            stmt = stmt.where(ApiKey.user_id == target_user_id)
    else:
        stmt = stmt.where(ApiKey.user_id == user.id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_api_key(
    session: AsyncSession,
    api_key: ApiKey,
    *,
    name: str | None = None,
    scopes: list[str] | None = None,
    status: ApiKeyStatus | None = None,
    expires_at: datetime | None = None,
) -> ApiKey:
    if name is not None:
        api_key.name = name
    if scopes is not None:
        api_key.scopes = scopes
    if status is not None:
        api_key.status = status
    if expires_at is not None:
        api_key.expires_at = expires_at
    await session.commit()
    await session.refresh(api_key)
    return api_key


async def disable_api_key(session: AsyncSession, api_key: ApiKey) -> None:
    api_key.status = ApiKeyStatus.DISABLED
    await session.commit()


async def verify_api_key(
    session: AsyncSession,
    api_key_value: str,
    *,
    required_scope: str | None = None,
) -> VerifiedApiKey:
    key_value = api_key_value.strip()
    if not key_value:
        raise ApiKeyAuthError("API_KEY_INVALID", "API key is empty.")

    result = await session.execute(
        select(ApiKey).where(ApiKey.key_prefix == api_key_prefix(key_value))
    )
    candidates = list(result.scalars().all())
    hashed_value = hash_api_key(key_value)
    api_key = next(
        (candidate for candidate in candidates if compare_digest(candidate.key_hash, hashed_value)),
        None,
    )
    if api_key is None:
        raise ApiKeyAuthError("API_KEY_INVALID", "Invalid API key.")
    if api_key.status == ApiKeyStatus.DISABLED:
        raise ApiKeyAuthError("API_KEY_DISABLED", "API key is disabled.")
    if api_key.expires_at is not None and _utc_datetime(api_key.expires_at) <= datetime.now(UTC):
        api_key.status = ApiKeyStatus.EXPIRED
        await session.commit()
        raise ApiKeyAuthError("API_KEY_EXPIRED", "API key is expired.")
    has_scope = (
        not required_scope
        or not api_key.scopes
        or required_scope in api_key.scopes
        or "*" in api_key.scopes
    )
    if not has_scope:
        raise ApiKeyAuthError(
            "API_KEY_SCOPE_DENIED",
            "API key does not have the required scope.",
            status_code=403,
        )

    user = await session.get(User, api_key.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise ApiKeyAuthError("API_KEY_USER_INACTIVE", "API key owner is inactive.")

    api_key.last_used_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(api_key)
    return VerifiedApiKey(api_key=api_key, user=user)
