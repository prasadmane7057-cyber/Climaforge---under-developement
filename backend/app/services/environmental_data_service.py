"""Environmental Data Coordination Service.

Unifies weather forecasts, IMD district warnings, and Indrayani River
monitoring references into cohesive domain responses.
"""

from datetime import datetime, timezone
import logging
from typing import Optional

from app.schemas.environmental import (
    IndrayaniMonitoringResponse,
    RiverGaugeReading,
)
from app.services.imd_service import imd_service
from app.services.river_monitoring_service import (
    PRIMARY_MOSHI_STATION,
    river_monitoring_service,
)
from app.services.weather_service import weather_service

logger = logging.getLogger("climaforge.environmental_data_service")


class EnvironmentalDataService:
    """Coordinator service for environmental intelligence and Indrayani River monitoring."""

    def __init__(self) -> None:
        self.weather = weather_service
        self.imd = imd_service
        self.river = river_monitoring_service

    async def get_indrayani_monitoring_summary(
        self,
        station_id: Optional[str] = None,
        force_refresh: bool = False,
    ) -> IndrayaniMonitoringResponse:
        """Compile a complete Indrayani River environmental monitoring snapshot."""
        primary_station = PRIMARY_MOSHI_STATION
        if station_id:
            found = self.river.get_station_by_id(station_id)
            if found:
                primary_station = found

        corridor_stations = self.river.get_corridor_stations()

        # 1. Fetch real-time weather at the station coordinates
        weather_forecast = await self.weather.get_forecast(
            latitude=primary_station.latitude,
            longitude=primary_station.longitude,
            location_name=f"{primary_station.station_name}, {primary_station.taluka}, Pune",
            force_refresh=force_refresh,
        )

        # Compute 24h rainfall sum from next 24 hourly intervals if available
        rainfall_24h = 0.0
        prob_max = 0.0
        if weather_forecast.hourly:
            next_24 = weather_forecast.hourly[:24]
            rain_values = [h.precipitation_mm for h in next_24 if h.precipitation_mm is not None]
            rainfall_24h = sum(rain_values) if rain_values else 0.0
            prob_values = [h.precipitation_probability_pct for h in next_24 if h.precipitation_probability_pct is not None]
            prob_max = max(prob_values) if prob_values else 0.0

        # 2. Fetch IMD warnings for Pune District
        imd_warnings = await self.imd.get_district_warnings(
            district="Pune",
            state="Maharashtra",
            force_refresh=force_refresh,
        )

        # 3. Retrieve river gauge telemetry (strictly None when unverified)
        gauge_reading: Optional[RiverGaugeReading] = self.river.get_live_gauge_reading(
            primary_station.station_id
        )

        # 4. Retrieve historical records for primary station
        historical_records = self.river.get_historical_environmental_records(
            primary_station.station_id
        )

        # Freshness determination
        freshness = "LIVE" if (weather_forecast.current and weather_forecast.current.freshness_status == "LIVE") else "FORECAST"

        return IndrayaniMonitoringResponse(
            river_name="Indrayani River",
            district="Pune District, Maharashtra, India",
            primary_reference_station=primary_station,
            corridor_stations=corridor_stations,
            local_weather=weather_forecast.current,
            rainfall_forecast_24h_mm=round(rainfall_24h, 1),
            rainfall_probability_max_pct=round(prob_max, 1),
            imd_warnings=imd_warnings,
            river_telemetry_status=self.river.get_telemetry_status_text(),
            river_gauge_reading=gauge_reading,
            historical_records=historical_records,
            data_freshness=freshness,
            attribution="MPCB (Station 11 Reference), Open-Meteo (Weather CC BY 4.0), IMD (Warnings Advisory).",
            disclaimer=(
                "VERIFIED GEOGRAPHICAL REFERENCE ONLY: The Moshi monitoring location is an official MPCB water-quality "
                "sampling reference point. Real-time automated flood-level telemetry for the Indrayani River is currently "
                "unverified / unavailable. Do not derive river flood risk from rainfall alone. Never use for emergency navigation."
            ),
            fetched_timestamp=datetime.now(timezone.utc),
        )


# Global singleton instance
environmental_data_service = EnvironmentalDataService()

