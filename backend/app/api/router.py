from fastapi import APIRouter

from backend.app.api.routes import health, mail, users

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(mail.router)
api_router.include_router(users.router)
