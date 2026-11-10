"""CLIMAFORGE Environmental Intelligence & Indrayani River Monitoring Schemas.

Strict Pydantic contracts for real-time weather, precipitation forecasts,
India Meteorological Department (IMD) warnings, and Indrayani River environmental monitoring.
"""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


FreshnessStatus = Literal[
    "LIVE",
    "FORECAST",
    "HISTORICAL",
    "UNAVAILABLE",
    "STALE",
    "SIMULATED",
]

QualityStatus = Literal[
    "VERIFIED_OBSERVATION",
    "PROVIDER_ESTIMATE",
    "CALCULATED_FORECAST",
    "HISTORICAL_ARCHIVE",
    "TELEMETRY_UNVERIFIED",
    "OFFLINE_FALLBACK",
    "UNAVAILABLE",
]


class GeoCoordinate(BaseModel):
    """Geographic coordinate with optional elevation and accuracy."""

    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")
    accuracy_m: Optional[float] = Field(None, ge=0.0, description="GPS accuracy in meters if measured")
    elevation_m: Optional[float] = Field(None, description="Elevation above mean sea level in meters")


class WeatherCurrentObservation(BaseModel):
    """Current ambient meteorological observation from Open-Meteo."""

    temperature_c: Optional[float] = Field(None, description="Ambient air temperature in degrees Celsius")
    relative_humidity_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Relative humidity percentage")
    precipitation_mm: Optional[float] = Field(None, ge=0.0, description="Current precipitation rate in mm")
    rain_mm: Optional[float] = Field(None, ge=0.0, description="Liquid rain rate in mm")
    wind_speed_kmh: Optional[float] = Field(None, ge=0.0, description="Wind speed at 10m height in km/h")
    wind_direction_deg: Optional[float] = Field(None, ge=0.0, le=360.0, description="Wind direction in degrees")
    weather_code: Optional[int] = Field(None, description="WMO weather interpretation code")
    weather_description: Optional[str] = Field(None, description="Human-readable WMO weather description")
    observation_timestamp: Optional[datetime] = Field(None, description="Timestamp of the observation from provider")
    fetched_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when data was fetched")
    quality_status: QualityStatus = Field(default="VERIFIED_OBSERVATION")
    freshness_status: FreshnessStatus = Field(default="LIVE")


class HourlyPrecipitationItem(BaseModel):
    """Single hourly precipitation forecast step."""

    timestamp: datetime = Field(..., description="Forecast target timestamp (UTC or local)")
    precipitation_mm: Optional[float] = Field(None, ge=0.0, description="Predicted precipitation amount in mm")
    rain_mm: Optional[float] = Field(None, ge=0.0, description="Predicted rain in mm")
    precipitation_probability_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Precipitation probability %")
    temperature_c: Optional[float] = Field(None, description="Predicted temperature in degrees Celsius")
    wind_speed_kmh: Optional[float] = Field(None, ge=0.0, description="Predicted wind speed in km/h")


class DailyPrecipitationSummary(BaseModel):
    """Daily forecast summary item."""

    date: str = Field(..., description="Calendar date YYYY-MM-DD")
    precipitation_sum_mm: Optional[float] = Field(None, ge=0.0, description="Total daily precipitation in mm")
    precipitation_probability_max_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Max precipitation probability %")
    wind_speed_max_kmh: Optional[float] = Field(None, ge=0.0, description="Maximum wind gust speed in km/h")
    temp_min_c: Optional[float] = Field(None, description="Minimum temperature in degrees Celsius")
    temp_max_c: Optional[float] = Field(None, description="Maximum temperature in degrees Celsius")


class WeatherForecastResponse(BaseModel):
    """Comprehensive weather and precipitation forecast payload."""

    latitude: float = Field(..., description="Query latitude")
    longitude: float = Field(..., description="Query longitude")
    location_name: Optional[str] = Field(None, description="Descriptive location name")
    timezone: str = Field(default="Asia/Kolkata", description="Timezone of the returned data")
    current: Optional[WeatherCurrentObservation] = None
    hourly: List[HourlyPrecipitationItem] = Field(default_factory=list, description="Hourly forecast steps")
    daily: List[DailyPrecipitationSummary] = Field(default_factory=list, description="Daily forecast steps")
    provider: str = Field(default="Open-Meteo", description="Name of weather data provider")
    attribution: str = Field(
        default="Weather data by Open-Meteo.com under CC BY 4.0",
        description="Mandatory legal attribution for weather data",
    )
    fetched_timestamp: datetime = Field(default_factory=datetime.utcnow)
    freshness_status: FreshnessStatus = Field(default="FORECAST")


class IMDWarningItem(BaseModel):
    """Individual district or regional weather warning from IMD."""

    warning_id: str = Field(..., description="Unique warning record identifier")
    district: str = Field(..., description="Target district, e.g. Pune")
    state: str = Field(default="Maharashtra", description="Target state")
    warning_level: Literal["GREEN", "YELLOW", "ORANGE", "RED", "NO_WARNING"] = Field(
        ..., description="IMD color-coded warning severity"
    )
    warning_type: str = Field(..., description="Category, e.g. HEAVY_RAINFALL, THUNDERSTORM, SQUALL, NONE")
    valid_from: Optional[datetime] = Field(None, description="Start of warning validity period")
    valid_to: Optional[datetime] = Field(None, description="End of warning validity period")
    headline: str = Field(..., description="Summary headline of warning")
    description: str = Field(..., description="Actionable details and guidance")
    issued_by: str = Field(default="India Meteorological Department (IMD)", description="Issuing authority")
    source_url: Optional[str] = Field(None, description="Official IMD portal reference URL")
    freshness_status: FreshnessStatus = Field(default="LIVE")


class IMDWarningsResponse(BaseModel):
    """IMD warning response payload for Pune/Maharashtra region."""

    district: str = Field(default="Pune")
    state: str = Field(default="Maharashtra")
    provider_status: Literal["CONFIGURED_LIVE", "UNCONFIGURED_FALLBACK", "DISABLED", "PROVIDER_UNAVAILABLE"] = Field(
        ..., description="Current operational state of IMD provider"
    )
    warnings: List[IMDWarningItem] = Field(default_factory=list, description="Active weather warning records")
    fetched_timestamp: datetime = Field(default_factory=datetime.utcnow)
    attribution: str = Field(
        default="Warnings data sourced from India Meteorological Department (IMD) / Regional Meteorological Centre Mumbai",
        description="Official source attribution",
    )
    disclaimer: str = Field(
        default="Official IMD warnings are advisory. Follow local district disaster management authority instructions.",
        description="Mandatory warning disclaimer",
    )


class RiverStationReference(BaseModel):
    """Verified geographic environmental reference metadata for Indrayani River."""

    station_id: str = Field(..., description="Unique station reference code")
    station_name: str = Field(..., description="Official station designation")
    river_name: str = Field(default="Indrayani River", description="Associated river course")
    basin_name: str = Field(default="Bhima Basin (Krishna Basin)", description="River basin hierarchy")
    village: str = Field(..., description="Village / locality")
    taluka: str = Field(..., description="Taluka administrative division")
    district: str = Field(default="Pune", description="District")
    state: str = Field(default="Maharashtra", description="State")
    country: str = Field(default="India", description="Country")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    station_type: Literal[
        "WATER_QUALITY_MONITORING_REFERENCE",
        "HYDROLOGICAL_GAUGE",
        "PILGRIMAGE_GHAT_REFERENCE",
        "BASIN_CONFLUENCE_REFERENCE",
    ] = Field(..., description="Primary classification of station")
    monitoring_body: str = Field(
        ..., description="Official monitoring authority, e.g. MPCB, CWC, or Municipal Council"
    )
    source_citation: str = Field(..., description="Official verifiable source URL or document reference")
    telemetry_status: Literal[
        "TELEMETRY_UNVERIFIED",
        "TELEMETRY_UNAVAILABLE",
        "TELEMETRY_OPERATIONAL",
    ] = Field(
        default="TELEMETRY_UNVERIFIED",
        description="Whether live automated flood telemetry is certified at this point",
    )
    telemetry_available: bool = Field(
        default=False,
        description="Strict boolean: true only when automated river level telemetry is connected",
    )
    disclaimer: str = Field(
        ...,
        description="Mandatory notice stating whether flood telemetry is verified or unverified",
    )


class RiverGaugeReading(BaseModel):
    """River water level reading structure (only populated when genuine telemetry exists)."""

    station_id: str = Field(..., description="Reference station ID")
    observation_timestamp: Optional[datetime] = None
    water_level_m: Optional[float] = Field(None, description="Water surface elevation or gauge height in meters")
    warning_level_m: Optional[float] = Field(None, description="Official warning stage in meters")
    danger_level_m: Optional[float] = Field(None, description="Official danger stage in meters")
    discharge_cumecs: Optional[float] = Field(None, description="Discharge rate in cubic meters per second")
    trend: Optional[Literal["RISING", "FALLING", "STEADY", "UNKNOWN"]] = None
    data_source: str = Field(..., description="Authoritative data source")
    quality_status: QualityStatus = Field(default="TELEMETRY_UNVERIFIED")
    freshness_status: FreshnessStatus = Field(default="UNAVAILABLE")


class RiverHistoricalRecord(BaseModel):
    """Historical environmental reference record."""

    station_id: str
    record_date: str
    parameter_name: str
    measured_value: Optional[float]
    unit: str
    source_agency: str
    disclaimer: str


class IndrayaniMonitoringResponse(BaseModel):
    """Comprehensive Indrayani River Environmental Monitoring Payload."""

    river_name: str = Field(default="Indrayani River")
    district: str = Field(default="Pune, Maharashtra, India")
    primary_reference_station: RiverStationReference
    corridor_stations: List[RiverStationReference] = Field(default_factory=list)
    local_weather: Optional[WeatherCurrentObservation] = None
    rainfall_forecast_24h_mm: Optional[float] = Field(None, description="Cumulative 24h forecasted rainfall")
    rainfall_probability_max_pct: Optional[float] = Field(None, description="Max 24h precipitation probability")
    imd_warnings: Optional[IMDWarningsResponse] = None
    river_telemetry_status: str = Field(
        default="Indrayani River telemetry currently unavailable. Verified geographical environmental monitoring reference — flood telemetry not verified.",
        description="Clear, truthful statement on telemetry status",
    )
    river_gauge_reading: Optional[RiverGaugeReading] = None
    historical_records: List[RiverHistoricalRecord] = Field(default_factory=list)
    data_freshness: FreshnessStatus = Field(default="LIVE")
    attribution: str = Field(
        default="Environmental reference: MPCB (Maharashtra Pollution Control Board); Weather: Open-Meteo (CC BY 4.0); Warnings: IMD.",
        description="Comprehensive attribution",
    )
    disclaimer: str = Field(
        default=(
            "VERIFIED GEOGRAPHICAL REFERENCE ONLY: The Moshi monitoring location is an official MPCB water-quality "
            "sampling reference point. Real-time automated flood-level telemetry for the Indrayani River is currently "
            "unverified / unavailable. Do not derive river flood risk from rainfall alone. Never use for emergency navigation."
        ),
        description="Mandatory scientific and life-safety disclaimer",
    )
    fetched_timestamp: datetime = Field(default_factory=datetime.utcnow)

