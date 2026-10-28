"""Tests for GET /health and root service metadata."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    """Verify GET /health returns HTTP 200 with structured JSON diagnostic schema."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "app_name" in data
        assert "version" in data
        assert "environment" in data
        assert "timestamp" in data
        assert "subsystems" in data
        assert isinstance(data["subsystems"], dict)
        assert data["subsystems"]["api_server"] == "operational"
        assert "disclaimer" in data


@pytest.mark.asyncio
async def test_health_api_prefix():
    """Verify GET /api/health is accessible with identical schema."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint():
    """Verify root endpoint returns operational metadata."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert "/health" in data["health_url"]
