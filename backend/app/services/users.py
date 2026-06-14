from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import hash_password, verify_password
from backend.app.models.enums import UserRole, UserStatus
from backend.app.models.user import User


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def authenticate_user(
    session: AsyncSession, username: str, password: str
) -> User | None:
    """Return an active user matching the credentials, or None on any failure.

    Returns None for unknown user, wrong password, or disabled account so the
    caller cannot distinguish reasons (avoids username enumeration).
    """
    user = await get_user_by_username(session, username)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if user.status != UserStatus.ACTIVE:
        return None
    return user


async def list_users(
    session: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 20,
) -> list[User]:
    result = await session.execute(
        select(User).order_by(User.id.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all())


async def get_user_count(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(User.id)))
    return result.scalar_one()


async def touch_last_login(session: AsyncSession, user: User) -> None:
    user.last_login_at = datetime.now(UTC)
    await session.commit()


async def create_user(
    session: AsyncSession,
    *,
    username: str,
    email: str,
    password: str,
    role: UserRole,
    status: UserStatus = UserStatus.ACTIVE,
) -> User:
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role=role,
        status=status,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user(
    session: AsyncSession,
    user: User,
    *,
    username: str | None = None,
    email: str | None = None,
    password: str | None = None,
    role: UserRole | None = None,
    status: UserStatus | None = None,
) -> User:
    if username is not None:
        user.username = username
    if email is not None:
        user.email = email
    if password is not None:
        user.password_hash = hash_password(password)
    if role is not None:
        user.role = role
    if status is not None:
        user.status = status
    await session.commit()
    await session.refresh(user)
    return user


async def ensure_admin_user(
    session: AsyncSession,
    *,
    username: str,
    email: str,
    password: str,
) -> tuple[User, bool]:
    """Create the bootstrap admin if it does not exist yet.

    Returns (user, created). When an admin is found by username we return it
    untouched — never overwrite an existing password from environment values.
    """
    existing = await get_user_by_username(session, username)
    if existing is not None:
        return existing, False
    user = await create_user(
        session,
        username=username,
        email=email,
        password=password,
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    return user, True
