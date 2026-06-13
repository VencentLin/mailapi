from fastapi import APIRouter

from backend.app.api.routes import api_keys, dashboard, health, logs, mail, mail_accounts, users

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(mail.router)
api_router.include_router(users.router)
api_router.include_router(api_keys.router)
api_router.include_router(mail_accounts.router)
api_router.include_router(logs.router)
api_router.include_router(dashboard.router)
