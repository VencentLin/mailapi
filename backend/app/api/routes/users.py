from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.routes.auth import get_current_user
from backend.app.db.session import get_db_session
from backend.app.models.enums import UserRole
from backend.app.models.user import User
from backend.app.schemas.auth import UserPublic
from backend.app.schemas.users import UserCreate
from backend.app.services.users import (
    create_user,
    get_user_by_email,
    get_user_by_username,
    list_users,
)

router = APIRouter(prefix="/users", tags=["users"])


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


@router.get("", response_model=list[UserPublic])
async def get_users(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_admin),
) -> list[UserPublic]:
    users = await list_users(session, offset=offset, limit=limit)
    return [UserPublic.model_validate(u) for u in users]


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    payload: UserCreate,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_admin),
) -> UserPublic:
    """Create a new user (admin only).

    Returns 409 if username or email is already taken.
    """
    if await get_user_by_username(session, payload.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )
    if await get_user_by_email(session, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )
    user = await create_user(
        session,
        username=payload.username,
        email=payload.email,
        password=payload.password,
        role=payload.role,
        status=payload.status,
    )
    return UserPublic.model_validate(user)
