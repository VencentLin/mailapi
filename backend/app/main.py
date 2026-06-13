from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.router import api_router
from backend.app.api.routes import auth as auth_routes
from backend.app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.include_router(api_router)
    app.include_router(auth_routes.router)
    mount_frontend(app, settings.frontend_dist_dir)
    return app


def mount_frontend(app: FastAPI, dist_dir: Path) -> None:
    assets_dir = dist_dir / "assets"
    index_file = dist_dir / "index.html"

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    if not index_file.exists():
        return

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith("api/") or full_path.startswith("auth/"):
            raise HTTPException(status_code=404, detail="API route not found")
        return FileResponse(index_file)


app = create_app()
