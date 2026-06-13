import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import create_app


@pytest.mark.asyncio
async def test_health_endpoint_returns_service_status():
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "MailAPI",
        "version": "0.1.0",
    }


@pytest.mark.asyncio
async def test_db_health_endpoint_reports_configured_database(monkeypatch):
    from backend.app.api.routes import health

    async def fake_check_database() -> dict[str, str]:
        return {"status": "ok", "database": "postgresql"}

    monkeypatch.setattr(health, "check_database", fake_check_database)

    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "postgresql"}
