from fastapi import APIRouter
from sqlalchemy import text

from backend.app.core.config import get_settings
from backend.app.db.session import AsyncSessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }


async def check_database() -> dict[str, str]:
    async with AsyncSessionLocal() as session:
        await session.execute(text("select 1"))
    return {"status": "ok", "database": "postgresql"}


@router.get("/health/db")
async def database_health() -> dict[str, str]:
    return await check_database()
