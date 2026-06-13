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
