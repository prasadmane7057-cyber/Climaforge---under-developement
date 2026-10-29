"""Algorithm 0 — System Input & Data Preparation.

Canonical Report Page 10:
Turns raw inputs into one clean, zone-based dataset that every later algorithm
can trust. Validates ranges, checks required vs optional fields, applies fixed
reference range normalization without per-run min-max scaling, and sets
data-quality flags. Missing required fields produce DATA_INSUFFICIENT.
"""

import math
from typing import Any, Dict, List, Optional
from app.engine.constants import OPTIONAL_FIELDS, REF_RANGES, REQUIRED_FIELDS


def clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamps val within [lo, hi]. Validates finite numbers."""
    if not math.isfinite(val):
        raise ValueError(f"Value must be finite, received: {val}")
    return max(lo, min(hi, val))


def normalize(val: float, lo: float, hi: float) -> float:
    """Fixed reference range normalization: clamp((x - lo) / (hi - lo), 0, 1).
    
    Avoids per-run min-max normalization so results are deterministic and absolute.
    """
    if not math.isfinite(val):
        raise ValueError(f"Value must be finite, received: {val}")
    if hi == lo:
        return 0.0
    return clamp((val - lo) / (hi - lo), 0.0, 1.0)


def _extract_finite_non_negative_float(
    raw_zone: Dict[str, Any],
    keys: List[str],
    field_name: str,
    flags: List[str],
) -> Optional[float]:
    """Helper to extract and validate a non-negative finite float from candidate keys."""
    raw_val = None
    for k in keys:
        if k in raw_zone and raw_zone[k] is not None:
            raw_val = raw_zone[k]
            break

    if raw_val is None:
        return None

    try:
        val = float(raw_val)
        if not math.isfinite(val):
            flags.append(f"{field_name}_non_finite_rejected")
            return None
        if val < 0.0:
            flags.append(f"{field_name}_negative_rejected")
            return None
        return val
    except (ValueError, TypeError):
        flags.append(f"{field_name}_invalid_type")
        return None


def prepare_zone_data(raw_zone: Dict[str, Any]) -> Dict[str, Any]:
    """Prepares and validates a single zone's hydrological and exposure data.

    Returns a standardized dictionary:
    - zone_id, name
    - status: 'COMPLETE', 'PARTIAL_OPTIONAL_MISSING', 'DATA_INSUFFICIENT'
    - is_scorable: bool
    - flags: list of missing, rejected, or warning annotations
    - normalized: dict of normalized factors [0.0 - 1.0] for Algorithm 1
    - raw_exposure: dict of raw counts for Algorithm 3
    - normalized_exposure: dict of normalized components [0.0 - 1.0] for Algorithm 3
    - raw: original raw inputs preserved
    """
    zone_id = str(raw_zone.get("zone_id", "")).strip()
    flags: List[str] = []

    if not zone_id:
        zone_id = "UNKNOWN"
        flags.append("missing_zone_identifier")

    name = str(raw_zone.get("name", zone_id))

    # 1. Required Fields (Rainfall and Drainage Capacity)
    rainfall = _extract_finite_non_negative_float(
        raw_zone, ["rainfall", "rainfall_mm"], "rainfall", flags
    )
    drainage = _extract_finite_non_negative_float(
        raw_zone, ["drainage", "drainage_capacity_cms", "drainage_capacity"], "drainage", flags
    )

    if rainfall is None or drainage is None:
        missing_req = []
        if rainfall is None:
            missing_req.append("rainfall")
            flags.append("missing_required_rainfall")
        if drainage is None:
            missing_req.append("drainage")
            flags.append("missing_required_drainage")

        return {
            "zone_id": zone_id,
            "name": name,
            "status": "DATA_INSUFFICIENT",
            "is_scorable": False,
            "flags": flags,
            "normalized": {},
            "raw_exposure": {},
            "normalized_exposure": {},
            "raw": raw_zone,
        }

    # 2. Optional Fields (Elevation, Water Level, History/Soil Saturation)
    # Elevation: can be 0 or positive; negative below sea level is theoretically possible
    # in geography, but reference range is [0.0, 40.0]. We check finite float.
    elevation_val = None
    for k in ["elevation", "elevation_m"]:
        if k in raw_zone and raw_zone[k] is not None:
            elevation_val = raw_zone[k]
            break

    elevation = None
    if elevation_val is not None:
        try:
            val = float(elevation_val)
            if math.isfinite(val):
                elevation = val
            else:
                flags.append("elevation_non_finite_rejected")
        except (ValueError, TypeError):
            flags.append("elevation_invalid_type")
    else:
        flags.append("missing_optional_elevation")

    water_level = _extract_finite_non_negative_float(
        raw_zone, ["water_level", "water_level_m"], "water_level", flags
    )
    if water_level is None and "water_level" not in raw_zone and "water_level_m" not in raw_zone:
        flags.append("missing_optional_water_level")

    # History: events per year or soil saturation index proxy
    history = _extract_finite_non_negative_float(
        raw_zone, ["history", "historical_flood_frequency"], "history", flags
    )
    if history is None and ("soil_saturation_index" in raw_zone or "soil_saturation" in raw_zone):
        sat_val = raw_zone.get("soil_saturation_index")
        if sat_val is None:
            sat_val = raw_zone.get("soil_saturation")
        try:
            sat = float(sat_val)
            if math.isfinite(sat) and 0.0 <= sat <= 1.0:
                # Soil saturation [0.0 - 1.0] maps proportionally to history range [0.0 - 5.0]
                history = sat * REF_RANGES["history"][1]
            elif sat < 0.0 or sat > 1.0:
                flags.append("soil_saturation_out_of_bounds")
        except (ValueError, TypeError):
            flags.append("soil_saturation_invalid_type")

    if history is None and "missing_optional_history" not in flags:
        flags.append("missing_optional_history")

    # Determine status
    optional_missing_count = sum(
        1 for k in [elevation, water_level, history] if k is None
    )
    status = "PARTIAL_OPTIONAL_MISSING" if optional_missing_count > 0 else "COMPLETE"

    # 3. Normalized factors for Algorithm 1
    norm_factors: Dict[str, Optional[float]] = {
        "R": normalize(rainfall, *REF_RANGES["rainfall"]),
        "D": normalize(drainage, *REF_RANGES["drainage"]),
        "W": normalize(water_level, *REF_RANGES["water_level"]) if water_level is not None else None,
        "E": normalize(elevation, *REF_RANGES["elevation"]) if elevation is not None else None,
        "H": normalize(history, *REF_RANGES["history"]) if history is not None else None,
    }

    # 4. Exposure components for Algorithm 3
    # Note: NO undocumented nominal fallbacks! If missing, remain None and flag.
    population = _extract_finite_non_negative_float(
        raw_zone, ["population", "resident_population"], "population", flags
    )
    if population is None:
        flags.append("missing_exposure_population")

    critical_infra = _extract_finite_non_negative_float(
        raw_zone, ["critical_infra", "critical_infrastructure_count", "critical_assets_count"], "critical_infra", flags
    )
    if critical_infra is None:
        flags.append("missing_exposure_critical_infra")

    road_length = _extract_finite_non_negative_float(
        raw_zone, ["road_length", "road_length_km"], "road_length", flags
    )
    if road_length is None:
        flags.append("missing_exposure_road_length")

    emergency_routes = _extract_finite_non_negative_float(
        raw_zone, ["emergency_routes", "emergency_routes_count"], "emergency_routes", flags
    )
    if emergency_routes is None:
        flags.append("missing_exposure_emergency_routes")

    raw_exposure: Dict[str, Optional[float]] = {
        "P": population,
        "I": critical_infra,
        "Rd": road_length,
        "Em": emergency_routes,
    }

    norm_exposure: Dict[str, Optional[float]] = {
        "P": normalize(population, *REF_RANGES["population"]) if population is not None else None,
        "I": normalize(critical_infra, *REF_RANGES["critical_infra"]) if critical_infra is not None else None,
        "Rd": normalize(road_length, *REF_RANGES["road_length"]) if road_length is not None else None,
        "Em": normalize(emergency_routes, *REF_RANGES["emergency_routes"]) if emergency_routes is not None else None,
    }

    return {
        "zone_id": zone_id,
        "name": name,
        "status": status,
        "is_scorable": True,
        "flags": flags,
        "normalized": norm_factors,
        "raw_exposure": raw_exposure,
        "normalized_exposure": norm_exposure,
        "raw": raw_zone,
    }


def prepare_all_zones(raw_zones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Prepares a list of raw zone records in batch."""
    return [prepare_zone_data(z) for z in raw_zones]
