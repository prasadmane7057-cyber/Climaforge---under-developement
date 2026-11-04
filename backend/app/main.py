"""CLIMAFORGE FastAPI Backend Application Entrypoint."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.health import router as health_router
from app.routers.scenarios import router as scenarios_router
from app.routers.audit import router as audit_router
from app.routers.ml_prediction import router as ml_prediction_router
from app.routers.chatbot import router as chatbot_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings.validate_auth_configuration()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "CLIMAFORGE — Climate-Flood Decision-Support System Backend. "
        "Deterministic explainable calculation core with advisory AI integration."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS Middleware for Frontend Development Server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers (Both direct and /api prefixes)
app.include_router(health_router)
app.include_router(health_router, prefix="/api")

app.include_router(scenarios_router)
app.include_router(scenarios_router, prefix="/api")

app.include_router(audit_router)
app.include_router(audit_router, prefix="/api")
app.include_router(ml_prediction_router)
app.include_router(ml_prediction_router, prefix="/api")
app.include_router(chatbot_router)
app.include_router(chatbot_router, prefix="/api")


@app.get("/", summary="Root Index")
async def root():
    """Root endpoint returning basic service metadata."""
    return {
        "service": settings.app_name,
        "version": settings.version,
        "status": "operational",
        "docs_url": "/docs",
        "health_url": "/health",
        "scenarios_url": "/api/scenarios",
        "audit_logs_url": "/api/audit-logs",
        "disclaimer": "SYNTHETIC / ILLUSTRATIVE DATA ONLY",
    }
