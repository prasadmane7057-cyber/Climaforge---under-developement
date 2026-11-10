"""Tests for Real-Time Environmental Intelligence & Indrayani River Monitoring.

Verifies:
- Coordinate boundary validation
- Weather parsing and null-preservation (zero conversions avoided)
- Open-Meteo timeout and fallback handling
- IMD warnings service unconfigured and error fallbacks
- Indrayani River Moshi MPCB reference coordinates (18.68365, 73.87855)
- Honest telemetry unavailability (zero invented river levels)
- Unified coordinator payload synthesis
- API endpoints with RBAC access control
"""

from datetime import datetime, timezone
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.schemas.environmental import (
    DailyPrecipitationSummary,
    HourlyPrecipitationItem,
    IMDWarningsResponse,
    IndrayaniMonitoringResponse,
    RiverStationReference,
    WeatherCurrentObservation,
    WeatherForecastResponse,
)
from app.services.environmental_data_service import EnvironmentalDataService
from app.services.imd_service import IMDService
from app.services.river_monitoring_service import (
    PRIMARY_MOSHI_STATION,
    RiverMonitoringService,
)
from app.services.weather_service import WeatherService


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def fast_environmental_timeout(monkeypatch):
    """Ensure upstream network timeouts are fast during offline unit testing."""
    from app.services.weather_service import weather_service
    from app.services.imd_service import imd_service
    monkeypatch.setattr(weather_service, "timeout", 0.05)
    monkeypatch.setattr(imd_service, "timeout", 0.05)


# ==============================================================================
# 1. Coordinate Validation Tests
# ==============================================================================

def test_weather_service_valid_coordinates():
    """Valid coordinates must pass validation without raising."""
    WeatherService.validate_coordinates(18.68365, 73.87855)
    WeatherService.validate_coordinates(-90.0, -180.0)
    WeatherService.validate_coordinates(90.0, 180.0)
    WeatherService.validate_coordinates(0.0, 0.0)


def test_weather_service_invalid_latitude():
    """Latitudes exceeding [-90, 90] must raise ValueError."""
    with pytest.raises(ValueError, match="Latitude 95.0 out of valid range"):
        WeatherService.validate_coordinates(95.0, 73.87855)

    with pytest.raises(ValueError, match="Latitude -90.5 out of valid range"):
        WeatherService.validate_coordinates(-90.5, 73.87855)


def test_weather_service_invalid_longitude():
    """Longitudes exceeding [-180, 180] must raise ValueError."""
    with pytest.raises(ValueError, match="Longitude 185.0 out of valid range"):
        WeatherService.validate_coordinates(18.68365, 185.0)

    with pytest.raises(ValueError, match="Longitude -180.1 out of valid range"):
        WeatherService.validate_coordinates(18.68365, -180.1)


# ==============================================================================
# 2. Open-Meteo Parsing & Null Preservation
# ==============================================================================

def test_weather_parsing_preserves_nulls():
    """Missing measurements must remain None and NEVER convert to zero."""
    svc = WeatherService()
    raw_mock_data = {
        "latitude": 18.68,
        "longitude": 73.88,
        "timezone": "Asia/Kolkata",
        "current": {
            "time": "2026-11-10T14:00:00",
            "temperature_2m": None,  # Missing temperature
            "relative_humidity_2m": 65.0,
            "precipitation": None,  # Missing precipitation
            "rain": None,  # Missing rain
            "wind_speed_10m": 12.4,
            "wind_direction_10m": 240.0,
            "weather_code": 2,
        },
        "hourly": {
            "time": ["2026-11-10T14:00:00", "2026-11-10T15:00:00"],
            "precipitation": [None, 0.4],
            "rain": [None, 0.4],
            "precipitation_probability": [None, 30.0],
            "temperature_2m": [28.5, None],
            "wind_speed_10m": [10.0, 12.0],
        },
        "daily": {
            "time": ["2026-11-10"],
            "precipitation_sum": [None],
            "precipitation_probability_max": [45.0],
            "wind_speed_10m_max": [15.0],
            "temperature_2m_max": [31.0],
            "temperature_2m_min": [21.0],
        },
    }

    parsed = svc._parse_open_meteo_response(18.68365, 73.87855, "Moshi Reference", raw_mock_data)

    assert parsed.current is not None
    assert parsed.current.temperature_c is None, "Missing temperature must remain None"
    assert parsed.current.precipitation_mm is None, "Missing precipitation must remain None"
    assert parsed.current.rain_mm is None, "Missing rain must remain None"
    assert parsed.current.relative_humidity_pct == 65.0
    assert parsed.current.weather_description == "Partly cloudy"

    # Hourly check
    assert parsed.hourly[0].precipitation_mm is None
    assert parsed.hourly[0].precipitation_probability_pct is None
    assert parsed.hourly[1].precipitation_mm == 0.4
    assert parsed.hourly[1].temperature_c is None

    # Daily check
    assert parsed.daily[0].precipitation_sum_mm is None


def test_weather_fallback_on_failure():
    """Provider failure or timeout must produce structured fallback with UNAVAILABLE status."""
    svc = WeatherService()
    fallback = svc._create_fallback_response(18.68365, 73.87855, "Moshi Test", error_detail="Timeout after 10s")

    assert fallback.freshness_status == "UNAVAILABLE"
    assert fallback.current is not None
    assert fallback.current.quality_status == "OFFLINE_FALLBACK"
    assert "Timeout after 10s" in str(fallback.current.weather_description)
    assert fallback.current.temperature_c is None
    assert len(fallback.hourly) == 0


# ==============================================================================
# 3. IMD Service Tests
# ==============================================================================

def test_imd_service_unconfigured_fallback():
    """When IMD credentials are not enabled, return unconfigured status with clear advisory."""
    import anyio
    svc = IMDService()
    svc.enabled = False
    svc.api_key = ""

    resp = anyio.run(svc.get_district_warnings, "Pune", "Maharashtra")

    assert resp.district == "Pune"
    assert resp.provider_status == "UNCONFIGURED_FALLBACK"
    assert len(resp.warnings) >= 1
    assert "IMD_ENABLED=true" in resp.warnings[0].description
    assert resp.warnings[0].freshness_status == "UNAVAILABLE"


def test_imd_service_error_handling():
    """IMD error response must populate PROVIDER_UNAVAILABLE status."""
    svc = IMDService()
    resp = svc._build_error_response("Pune", "Maharashtra", error="HTTP 401 Unauthorized")

    assert resp.provider_status == "PROVIDER_UNAVAILABLE"
    assert len(resp.warnings) == 1
    assert resp.warnings[0].warning_type == "PROVIDER_ERROR"
    assert "HTTP 401 Unauthorized" in resp.warnings[0].headline


# ==============================================================================
# 4. Indrayani River Geographical & Telemetry Tests
# ==============================================================================

def test_indrayani_moshi_primary_station_reference():
    """Verify primary Moshi reference point coordinates, village, and MPCB citation."""
    svc = RiverMonitoringService()
    station = svc.get_primary_reference_station()

    assert station.station_id == "MPCB-INDRAYANI-MOSHI-11"
    assert station.river_name == "Indrayani River"
    assert station.village == "Moshi"
    assert station.taluka == "Haveli"
    assert station.district == "Pune"
    assert station.state == "Maharashtra"
    assert station.country == "India"
    assert pytest.approx(station.latitude, 0.0001) == 18.68365
    assert pytest.approx(station.longitude, 0.0001) == 73.87855
    assert station.monitoring_body == "Maharashtra Pollution Control Board (MPCB)"
    assert "gemsminar80.php" in station.source_citation
    assert station.telemetry_status == "TELEMETRY_UNVERIFIED"
    assert station.telemetry_available is False
    assert "flood telemetry not verified" in station.disclaimer.lower()


def test_indrayani_corridor_stations_geographic_order():
    """Corridor stations must include Moshi, Dehu, Alandi, and Tulapur confluence."""
    svc = RiverMonitoringService()
    stations = svc.get_corridor_stations()

    assert len(stations) >= 4
    station_ids = [s.station_id for s in stations]
    assert "MPCB-INDRAYANI-MOSHI-11" in station_ids
    assert "INDRAYANI-DEHU-GHAT" in station_ids
    assert "INDRAYANI-ALANDI-GHAT" in station_ids
    assert "INDRAYANI-TULAPUR-CONFLUENCE" in station_ids

    # All stations must honestly disclose unverified telemetry
    for s in stations:
        assert s.telemetry_available is False
        assert s.telemetry_status == "TELEMETRY_UNVERIFIED"


def test_indrayani_telemetry_honesty():
    """Must return None for live gauge readings — zero invented river levels."""
    svc = RiverMonitoringService()
    gauge = svc.get_live_gauge_reading("MPCB-INDRAYANI-MOSHI-11")
    assert gauge is None, "Gauge reading must be None when no verified telemetry exists"

    status_text = svc.get_telemetry_status_text()
    assert "telemetry currently unavailable" in status_text.lower()
    assert "flood telemetry not verified" in status_text.lower()


def test_indrayani_historical_records_clarity():
    """Historical records must be MPCB water-quality parameters, NOT flood levels."""
    svc = RiverMonitoringService()
    records = svc.get_historical_environmental_records("MPCB-INDRAYANI-MOSHI-11")

    assert len(records) >= 3
    param_names = [r.parameter_name for r in records]
    assert any("Dissolved Oxygen" in p for p in param_names)
    assert any("pH" in p for p in param_names)
    assert any("Biochemical Oxygen Demand" in p for p in param_names)

    for r in records:
        assert "Not a water level measurement" in r.disclaimer


# ==============================================================================
# 5. Unified Coordinator Service Tests
# ==============================================================================

def test_environmental_coordinator_indrayani_summary():
    """Environmental coordinator compiles complete Indrayani monitoring summary."""
    import anyio
    svc = EnvironmentalDataService()
    summary = anyio.run(svc.get_indrayani_monitoring_summary)

    assert isinstance(summary, IndrayaniMonitoringResponse)
    assert summary.river_name == "Indrayani River"
    assert summary.primary_reference_station.station_id == "MPCB-INDRAYANI-MOSHI-11"
    assert summary.river_gauge_reading is None
    assert "telemetry currently unavailable" in summary.river_telemetry_status.lower()
    assert summary.imd_warnings is not None
    assert len(summary.corridor_stations) >= 4
    assert len(summary.historical_records) >= 3
    assert "MPCB" in summary.attribution


# ==============================================================================
# 6. REST API Endpoints Tests
# ==============================================================================

def test_api_environmental_strict_mode_rejection(client, monkeypatch):
    """When strict auth is configured, unauthenticated requests must return 401."""
    from app.config import settings
    monkeypatch.setattr(settings, "jwt_signing_key", "k" * 32)
    res = client.get("/api/environmental/indrayani")
    assert res.status_code == 401


def test_api_environmental_indrayani_stations(client):
    """GET /api/environmental/indrayani/stations returns corridor station list."""
    res = client.get("/api/environmental/indrayani/stations")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 4
    assert data[0]["village"] == "Moshi"


def test_api_environmental_indrayani_history(client):
    """GET /api/environmental/indrayani/history returns historical MPCB records."""
    res = client.get("/api/environmental/indrayani/history?station_id=MPCB-INDRAYANI-MOSHI-11")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    assert any("pH" in r["parameter_name"] for r in data)


def test_api_environmental_warnings(client):
    """GET /api/environmental/warnings returns district warning response."""
    res = client.get("/api/environmental/warnings?district=Pune&state=Maharashtra")
    assert res.status_code == 200
    data = res.json()
    assert data["district"] == "Pune"
    assert data["provider_status"] in ("CONFIGURED_LIVE", "UNCONFIGURED_FALLBACK", "PROVIDER_UNAVAILABLE")


def test_api_environmental_forecast_invalid_coords(client):
    """GET /api/environmental/forecast with invalid coordinates must return 422."""
    res = client.get("/api/environmental/forecast?lat=95.0&lon=73.87855")
    assert res.status_code == 422


def test_api_environmental_indrayani_summary(client):
    """GET /api/environmental/indrayani returns unified response."""
    res = client.get("/api/environmental/indrayani")
    assert res.status_code == 200
    data = res.json()
    assert data["river_name"] == "Indrayani River"
    assert data["primary_reference_station"]["village"] == "Moshi"
    assert data["river_gauge_reading"] is None
    assert "telemetry currently unavailable" in data["river_telemetry_status"].lower()
