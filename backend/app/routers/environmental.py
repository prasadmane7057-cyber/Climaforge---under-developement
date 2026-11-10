"""Real-Time Environmental Intelligence & Indrayani River Monitoring Router.

Endpoints for live meteorological observations, hourly precipitation forecasts,
official IMD weather warnings, and verified Indrayani River environmental monitoring.
"""

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.auth import require_permission
from app.schemas.environmental import (
    IMDWarningsResponse,
    IndrayaniMonitoringResponse,
    RiverHistoricalRecord,
    RiverStationReference,
    WeatherCurrentObservation,
    WeatherForecastResponse,
)
from app.security.rbac import PERM_SCENARIO_READ
from app.services.environmental_data_service import environmental_data_service
from app.services.imd_service import imd_service
from app.services.river_monitoring_service import (
    PRIMARY_MOSHI_STATION,
    river_monitoring_service,
)
from app.services.weather_service import weather_service

router = APIRouter(prefix="/environmental", tags=["Environmental Intelligence"])


@router.get(
    "/weather",
    response_model=WeatherCurrentObservation,
    summary="Get Current Weather",
    description="Retrieve live ambient weather conditions for specific coordinates (defaults to Indrayani River Moshi reference).",
)
async def get_current_weather(
    lat: float = Query(PRIMARY_MOSHI_STATION.latitude, ge=-90.0, le=90.0, description="Latitude"),
    lon: float = Query(PRIMARY_MOSHI_STATION.longitude, ge=-180.0, le=180.0, description="Longitude"),
    _: Any = Depends(require_permission(PERM_SCENARIO_READ)),
) -> WeatherCurrentObservation:
    """Fetch current ambient meteorological observation."""
    forecast = await weather_service.get_forecast(lat, lon)
    if not forecast.current:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Current weather observation unavailable from provider.",
        )
    return forecast.current


@router.get(
    "/forecast",
    response_model=WeatherForecastResponse,
    summary="Get Weather & Precipitation Forecast",
    description="Retrieve current weather, hourly precipitation forecast (48h), and daily summaries from Open-Meteo.",
)
async def get_weather_forecast(
    lat: float = Query(PRIMARY_MOSHI_STATION.latitude, ge=-90.0, le=90.0, description="Latitude"),
    lon: float = Query(PRIMARY_MOSHI_STATION.longitude, ge=-180.0, le=180.0, description="Longitude"),
    location_name: Optional[str] = Query(None, description="Optional descriptive location name"),
    force_refresh: bool = Query(False, description="Bypass cache and force upstream refresh"),
    _: Any = Depends(require_permission(PERM_SCENARIO_READ)),
) -> WeatherForecastResponse:
    """Fetch complete weather and precipitation forecast payload."""
    try:
        return await weather_service.get_forecast(
            latitude=lat,
            longitude=lon,
            location_name=location_name,
            force_refresh=force_refresh,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get(
    "/warnings",
    response_model=IMDWarningsResponse,
    summary="Get IMD Weather Warnings",
    description="Retrieve official India Meteorological Department weather warnings for Pune District / Maharashtra.",
)
async def get_imd_warnings(
    district: str = Query("Pune", description="District name"),
    state: str = Query("Maharashtra", description="State name"),
    force_refresh: bool = Query(False, description="Bypass cache"),
    _: Any = Depends(require_permission(PERM_SCENARIO_READ)),
) -> IMDWarningsResponse:
    """Fetch district-level IMD weather warnings."""
    return await imd_service.get_district_warnings(
        district=district,
        state=state,
        force_refresh=force_refresh,
    )


@router.get(
    "/indrayani",
    response_model=IndrayaniMonitoringResponse,
    summary="Get Indrayani River Environmental Monitoring Summary",
    description="Unified monitoring payload for Indrayani River: Moshi MPCB reference, corridor stations, local weather, 24h rainfall forecast, IMD warnings, and honest telemetry status.",
)
async def get_indrayani_monitoring(
    station_id: Optional[str] = Query(None, description="Optional station ID filter"),
    force_refresh: bool = Query(False, description="Force fresh upstream fetches"),
    _: Any = Depends(require_permission(PERM_SCENARIO_READ)),
) -> IndrayaniMonitoringResponse:
    """Fetch unified Indrayani River environmental monitoring snapshot."""
    return await environmental_data_service.get_indrayani_monitoring_summary(
        station_id=station_id,
        force_refresh=force_refresh,
    )


@router.get(
    "/indrayani/stations",
    response_model=List[RiverStationReference],
    summary="List Indrayani River Corridor Stations",
    description="Retrieve verified geographic environmental reference locations along the Indrayani River course (Moshi, Dehu, Alandi, Tulapur).",
)
async def list_indrayani_stations(
    _: Any = Depends(require_permission(PERM_SCENARIO_READ)),
) -> List[RiverStationReference]:
    """Retrieve list of verified Indrayani River reference stations."""
    return river_monitoring_service.get_corridor_stations()


@router.get(
    "/indrayani/history",
    response_model=List[RiverHistoricalRecord],
    summary="Get Indrayani Historical Environmental Parameters",
    description="Retrieve verified historical environmental parameters (MPCB water quality sampling records; not hydraulic gauge levels).",
)
async def get_indrayani_history(
    station_id: str = Query(PRIMARY_MOSHI_STATION.station_id, description="Station identifier"),
    _: Any = Depends(require_permission(PERM_SCENARIO_READ)),
) -> List[RiverHistoricalRecord]:
    """Retrieve verified historical environmental records for specified station."""
    return river_monitoring_service.get_historical_environmental_records(station_id)

