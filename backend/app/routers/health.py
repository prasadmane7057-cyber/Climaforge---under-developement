"""Health diagnostic router for CLIMAFORGE backend."""

from datetime import datetime, timezone
from typing import Dict
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Structured health check response model."""

    status: str = Field("healthy", description="Operational status: healthy, degraded, or down")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application semantic version")
    environment: str = Field(..., description="Active runtime environment")
    timestamp: datetime = Field(..., description="UTC timestamp of the health verification")
    subsystems: Dict[str, str] = Field(
        ...,
        description="Status indicators for core subsystems (e.g. calculation core, advisory AI, data layer)",
    )
    disclaimer: str = Field(
        ..., description="Clarifying label that system uses synthetic demo data in prototype phase"
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Backend Health & System Diagnostics",
    description="Returns structured health diagnostics, system version, and operational readiness.",
)
async def get_health() -> HealthResponse:
    """Return health status and subsystem diagnostics."""
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.version,
        environment=settings.environment,
        timestamp=datetime.now(timezone.utc),
        subsystems={
            "api_server": "operational",
            "deterministic_calculation_core": "ready",
            "nugen_advisory_layer": "mock_provider (advisory only)",
            "persistence": "ready (in-memory / sqlite)",
        },
        disclaimer="SYNTHETIC / ILLUSTRATIVE DATA ONLY — Milestone 0 Prototype",
    )
