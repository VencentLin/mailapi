from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.routes.auth import get_current_user
from backend.app.db.session import get_db_session
from backend.app.models.api_key import ApiKey
from backend.app.models.enums import UserRole
from backend.app.models.user import User
from backend.app.schemas.api_keys import (
    ApiKeyCreate,
    ApiKeyCreateResponse,
    ApiKeyPublic,
    ApiKeyUpdate,
)
from backend.app.services.api_keys import (
    create_api_key,
    disable_api_key,
    list_api_keys,
    update_api_key,
)
from backend.app.services.users import get_user_by_id

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def _can_manage_api_key(current_user: User, api_key: ApiKey) -> bool:
    return current_user.role == UserRole.ADMIN or api_key.user_id == current_user.id


async def _get_manageable_key(
    session: AsyncSession,
    api_key_id: int,
    current_user: User,
) -> ApiKey:
    api_key = await session.get(ApiKey, api_key_id)
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    if not _can_manage_api_key(current_user, api_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return api_key


@router.get("", response_model=list[ApiKeyPublic])
async def get_api_keys(
    user_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ApiKeyPublic]:
    include_all = current_user.role == UserRole.ADMIN
    keys = await list_api_keys(
        session,
        user=current_user,
        target_user_id=user_id,
        include_all=include_all,
    )
    return [ApiKeyPublic.model_validate(key) for key in keys]


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key_endpoint(
    payload: ApiKeyCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApiKeyCreateResponse:
    owner = current_user
    if payload.user_id is not None:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        target = await get_user_by_id(session, payload.user_id)
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        owner = target

    key, plain_text = await create_api_key(
        session,
        user=owner,
        name=payload.name,
        scopes=payload.scopes,
        expires_at=payload.expires_at,
    )
    return ApiKeyCreateResponse(key=ApiKeyPublic.model_validate(key), api_key=plain_text)


@router.patch("/{api_key_id}", response_model=ApiKeyPublic)
async def patch_api_key(
    api_key_id: int,
    payload: ApiKeyUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ApiKeyPublic:
    api_key = await _get_manageable_key(session, api_key_id, current_user)
    updated = await update_api_key(
        session,
        api_key,
        name=payload.name,
        scopes=payload.scopes,
        status=payload.status,
        expires_at=payload.expires_at,
    )
    return ApiKeyPublic.model_validate(updated)


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    api_key_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    api_key = await _get_manageable_key(session, api_key_id, current_user)
    await disable_api_key(session, api_key)
