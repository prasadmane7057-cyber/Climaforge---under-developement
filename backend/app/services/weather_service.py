"""Open-Meteo Weather Service for Real-Time Environmental Intelligence.

Fetches current weather observations, hourly precipitation forecasts, and daily
summaries with bounded caching, strict timeouts, coordinate validation, and null-preservation.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional, Tuple
import httpx

from app.config import settings
from app.schemas.environmental import (
    DailyPrecipitationSummary,
    HourlyPrecipitationItem,
    WeatherCurrentObservation,
    WeatherForecastResponse,
)

logger = logging.getLogger("climaforge.weather_service")

# WMO Weather interpretation codes (WW)
WMO_CODE_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    62: "Moderate rain",
    63: "Heavy rain",
    65: "Very heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm: Slight or moderate",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherService:
    """Service client for Open-Meteo weather forecasts and observations."""

    def __init__(self) -> None:
        self.base_url = settings.open_meteo_base_url.rstrip("/")
        self.timeout = settings.open_meteo_timeout_seconds
        self.cache_ttl = settings.weather_cache_ttl_seconds
        # In-memory TTL cache: key -> (timestamp, WeatherForecastResponse)
        self._cache: Dict[Tuple[float, float], Tuple[float, WeatherForecastResponse]] = {}

    @staticmethod
    def validate_coordinates(latitude: float, longitude: float) -> None:
        """Validate latitude and longitude ranges."""
        if not (-90.0 <= latitude <= 90.0):
            raise ValueError(f"Latitude {latitude} out of valid range [-90.0, 90.0]")
        if not (-180.0 <= longitude <= 180.0):
            raise ValueError(f"Longitude {longitude} out of valid range [-180.0, 180.0]")

    def _get_cached(self, lat: float, lon: float) -> Optional[WeatherForecastResponse]:
        """Retrieve from cache if within TTL."""
        key = (round(lat, 3), round(lon, 3))
        if key in self._cache:
            ts, resp = self._cache[key]
            if (datetime.now(timezone.utc).timestamp() - ts) < self.cache_ttl:
                return resp
            del self._cache[key]
        return None

    def _set_cached(self, lat: float, lon: float, response: WeatherForecastResponse) -> None:
        """Store in cache with current timestamp."""
        key = (round(lat, 3), round(lon, 3))
        self._cache[key] = (datetime.now(timezone.utc).timestamp(), response)

    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        location_name: Optional[str] = None,
        force_refresh: bool = False,
    ) -> WeatherForecastResponse:
        """Fetch current weather and 72-hour precipitation forecast."""
        self.validate_coordinates(latitude, longitude)

        if not force_refresh:
            cached = self._get_cached(latitude, longitude)
            if cached:
                return cached

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,precipitation,rain,wind_speed_10m,wind_direction_10m,weather_code",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,rain,wind_speed_10m",
            "daily": "precipitation_sum,precipitation_probability_max,wind_speed_10m_max,temperature_2m_max,temperature_2m_min",
            "forecast_days": 3,
            "timezone": "Asia/Kolkata",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(f"{self.base_url}/forecast", params=params)

            if res.status_code != 200:
                logger.warning("Open-Meteo returned status %s: %s", res.status_code, res.text)
                return self._create_fallback_response(
                    latitude, longitude, location_name, error_detail=f"HTTP {res.status_code}"
                )

            data = res.json()
            parsed = self._parse_open_meteo_response(latitude, longitude, location_name, data)
            self._set_cached(latitude, longitude, parsed)
            return parsed

        except httpx.TimeoutException:
            logger.warning("Open-Meteo request timed out after %s seconds", self.timeout)
            return self._create_fallback_response(
                latitude, longitude, location_name, error_detail=f"Timeout after {self.timeout}s"
            )
        except Exception as exc:
            logger.error("Failed to fetch weather from Open-Meteo: %s", exc)
            return self._create_fallback_response(
                latitude, longitude, location_name, error_detail=str(exc)
            )

    def _parse_open_meteo_response(
        self,
        latitude: float,
        longitude: float,
        location_name: Optional[str],
        data: Dict[str, Any],
    ) -> WeatherForecastResponse:
        """Parse raw Open-Meteo JSON into structured Pydantic model with null-preservation."""
        current_raw = data.get("current") or {}
        hourly_raw = data.get("hourly") or {}
        daily_raw = data.get("daily") or {}

        # 1. Current Observation
        weather_code = current_raw.get("weather_code")
        weather_desc = WMO_CODE_MAP.get(weather_code) if weather_code is not None else None

        obs_time_str = current_raw.get("time")
        obs_time = datetime.fromisoformat(obs_time_str) if obs_time_str else None

        current = WeatherCurrentObservation(
            temperature_c=current_raw.get("temperature_2m"),
            relative_humidity_pct=current_raw.get("relative_humidity_2m"),
            precipitation_mm=current_raw.get("precipitation"),
            rain_mm=current_raw.get("rain"),
            wind_speed_kmh=current_raw.get("wind_speed_10m"),
            wind_direction_deg=current_raw.get("wind_direction_10m"),
            weather_code=weather_code,
            weather_description=weather_desc,
            observation_timestamp=obs_time,
            fetched_timestamp=datetime.now(timezone.utc),
            quality_status="VERIFIED_OBSERVATION",
            freshness_status="LIVE",
        )

        # 2. Hourly Forecast Items (limit to next 48 hours for clean display)
        hourly_times = hourly_raw.get("time") or []
        hourly_precip = hourly_raw.get("precipitation") or []
        hourly_rain = hourly_raw.get("rain") or []
        hourly_prob = hourly_raw.get("precipitation_probability") or []
        hourly_temp = hourly_raw.get("temperature_2m") or []
        hourly_wind = hourly_raw.get("wind_speed_10m") or []

        hourly_items: list[HourlyPrecipitationItem] = []
        for i in range(min(len(hourly_times), 48)):
            try:
                t_str = hourly_times[i]
                t_dt = datetime.fromisoformat(t_str)
                hourly_items.append(
                    HourlyPrecipitationItem(
                        timestamp=t_dt,
                        precipitation_mm=hourly_precip[i] if i < len(hourly_precip) else None,
                        rain_mm=hourly_rain[i] if i < len(hourly_rain) else None,
                        precipitation_probability_pct=hourly_prob[i] if i < len(hourly_prob) else None,
                        temperature_c=hourly_temp[i] if i < len(hourly_temp) else None,
                        wind_speed_kmh=hourly_wind[i] if i < len(hourly_wind) else None,
                    )
                )
            except Exception as e:
                logger.debug("Failed parsing hourly item %d: %s", i, e)

        # 3. Daily Forecast Items
        daily_times = daily_raw.get("time") or []
        daily_precip_sum = daily_raw.get("precipitation_sum") or []
        daily_prob_max = daily_raw.get("precipitation_probability_max") or []
        daily_wind_max = daily_raw.get("wind_speed_10m_max") or []
        daily_temp_max = daily_raw.get("temperature_2m_max") or []
        daily_temp_min = daily_raw.get("temperature_2m_min") or []

        daily_items: list[DailyPrecipitationSummary] = []
        for i in range(len(daily_times)):
            try:
                daily_items.append(
                    DailyPrecipitationSummary(
                        date=daily_times[i],
                        precipitation_sum_mm=daily_precip_sum[i] if i < len(daily_precip_sum) else None,
                        precipitation_probability_max_pct=daily_prob_max[i] if i < len(daily_prob_max) else None,
                        wind_speed_max_kmh=daily_wind_max[i] if i < len(daily_wind_max) else None,
                        temp_max_c=daily_temp_max[i] if i < len(daily_temp_max) else None,
                        temp_min_c=daily_temp_min[i] if i < len(daily_temp_min) else None,
                    )
                )
            except Exception as e:
                logger.debug("Failed parsing daily item %d: %s", i, e)

        return WeatherForecastResponse(
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
            timezone=data.get("timezone", "Asia/Kolkata"),
            current=current,
            hourly=hourly_items,
            daily=daily_items,
            provider="Open-Meteo",
            attribution="Weather data by Open-Meteo.com under CC BY 4.0",
            fetched_timestamp=datetime.now(timezone.utc),
            freshness_status="LIVE" if current.temperature_c is not None else "FORECAST",
        )

    def _create_fallback_response(
        self,
        latitude: float,
        longitude: float,
        location_name: Optional[str],
        error_detail: str,
    ) -> WeatherForecastResponse:
        """Create a safe structured fallback when the upstream weather provider fails."""
        current = WeatherCurrentObservation(
            temperature_c=None,
            relative_humidity_pct=None,
            precipitation_mm=None,
            rain_mm=None,
            wind_speed_kmh=None,
            wind_direction_deg=None,
            weather_code=None,
            weather_description=f"Weather unavailable ({error_detail})",
            observation_timestamp=None,
            fetched_timestamp=datetime.now(timezone.utc),
            quality_status="OFFLINE_FALLBACK",
            freshness_status="UNAVAILABLE",
        )

        return WeatherForecastResponse(
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
            timezone="Asia/Kolkata",
            current=current,
            hourly=[],
            daily=[],
            provider="Open-Meteo (Offline Fallback)",
            attribution="Weather data by Open-Meteo.com under CC BY 4.0",
            fetched_timestamp=datetime.now(timezone.utc),
            freshness_status="UNAVAILABLE",
        )


# Global singleton instance
weather_service = WeatherService()

