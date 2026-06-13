from fastapi import APIRouter

from backend.app.api.routes import health, users

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(users.router)
