"""Algorithm 3 — Flood Impact / Exposure Calculation.

Canonical Report Page 12:
Measures how much of the city (people, key buildings, roads, emergency routes)
sits inside each qualified hotspot.

Formulas:
  scP  = norm(Population)
  scI  = norm(CriticalInfrastructure)
  scRd = norm(RoadLength)
  scEm = norm(EmergencyRoutes)
  ImpactScore = uP*scP + uI*scI + uRd*scRd + uEm*scEm,  SUM(u) = 1.0

Weights (u):
  P: 0.35, I: 0.25, Rd: 0.20, Em: 0.20
"""

from typing import Any, Dict, List, Optional
from app.engine.constants import REF_RANGES, WEIGHTS_ALG3
from app.engine.alg0_data_prep import normalize


def compute_zone_exposure(prepared_zone: Dict[str, Any]) -> Dict[str, Any]:
    """Calculates normalized exposure components and weighted ImpactScore for a single zone.

    Clearly separates normalized component indices [0.0 - 1.0] from raw physical counts.
    If exposure fields are missing, re-scales available weights and logs flags;
    never invents undocumented fallbacks.
    """
    zone_id = prepared_zone.get("zone_id", "UNKNOWN")
    name = prepared_zone.get("name", zone_id)
    raw_exp = prepared_zone.get("raw_exposure", {})
    flags = list(prepared_zone.get("flags", []))

    pop_raw = raw_exp.get("P")
    infra_raw = raw_exp.get("I")
    road_raw = raw_exp.get("Rd")
    emerg_raw = raw_exp.get("Em")

    # Compute normalized component scores [0.0 - 1.0]
    components: Dict[str, float] = {}

    if pop_raw is not None:
        components["P"] = normalize(pop_raw, *REF_RANGES["population"])
    else:
        flags.append("missing_exposure_population")

    if infra_raw is not None:
        components["I"] = normalize(infra_raw, *REF_RANGES["critical_infra"])
    else:
        flags.append("missing_exposure_critical_infra")

    if road_raw is not None:
        components["Rd"] = normalize(road_raw, *REF_RANGES["road_length"])
    else:
        flags.append("missing_exposure_road_length")

    if emerg_raw is not None:
        components["Em"] = normalize(emerg_raw, *REF_RANGES["emergency_routes"])
    else:
        flags.append("missing_exposure_emergency_routes")

    avail_keys = list(components.keys())
    weight_sum = sum(WEIGHTS_ALG3[k] for k in avail_keys)

    if weight_sum <= 0.0 or len(avail_keys) == 0:
        flags.append("all_exposure_components_missing")
        return {
            "zone_id": zone_id,
            "name": name,
            "impact_score": None,
            "status": "DATA_INSUFFICIENT",
            "flags": flags,
            "population_score": None,
            "infrastructure_score": None,
            "road_score": None,
            "emergency_score": None,
            "raw_counts": {
                "population": pop_raw,
                "critical_infra": infra_raw,
                "road_length_km": road_raw,
                "emergency_routes": emerg_raw,
            },
            "effective_weights": {},
        }

    # Weighted combination with dynamic rescaling for missing components
    weighted_sum = sum((WEIGHTS_ALG3[k] / weight_sum) * components[k] for k in avail_keys)
    impact_score = round(weighted_sum, 3)

    is_partial = len(avail_keys) < len(WEIGHTS_ALG3)
    status = "PARTIAL_RESCALED" if is_partial else "COMPLETE"

    effective_weights = {
        k: round(WEIGHTS_ALG3[k] / weight_sum, 4) for k in avail_keys
    }

    return {
        "zone_id": zone_id,
        "name": name,
        "impact_score": impact_score,
        "status": status,
        "flags": flags,
        "population_score": round(components["P"], 4) if "P" in components else None,
        "infrastructure_score": round(components["I"], 4) if "I" in components else None,
        "road_score": round(components["Rd"], 4) if "Rd" in components else None,
        "emergency_score": round(components["Em"], 4) if "Em" in components else None,
        "raw_counts": {
            "population": pop_raw,
            "critical_infra": infra_raw,
            "road_length_km": road_raw,
            "emergency_routes": emerg_raw,
        },
        "effective_weights": effective_weights,
    }


def compute_hotspot_exposures(
    hotspot_zones: List[Dict[str, Any]],
    prepared_zones_map: Dict[str, Dict[str, Any]],
    is_monitoring_only: bool = False,
) -> Dict[str, Any]:
    """Calculates exposure for all detected hotspots.

    Per Canonical Report Page 12:
    Algorithm 3 runs only for hotspots. If is_monitoring_only is True (0 hotspots),
    downstream analysis is skipped.
    """
    if is_monitoring_only or len(hotspot_zones) == 0:
        return {
            "status": "SKIPPED_MONITORING_ONLY",
            "exposures": [],
            "message": "Zero hotspots detected; Algorithm 3 exposure analysis skipped under MONITORING_ONLY.",
        }

    exposures: List[Dict[str, Any]] = []
    for h in hotspot_zones:
        zid = h["zone_id"]
        prep = prepared_zones_map.get(zid)
        if prep:
            exp = compute_zone_exposure(prep)
            exposures.append(exp)

    return {
        "status": "COMPLETE",
        "exposures": exposures,
        "count": len(exposures),
    }
