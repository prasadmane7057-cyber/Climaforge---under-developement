"""Algorithm 1 — Flood Risk Score.

Canonical Report Page 11:
Computes a deterministic 0–100 score and severity label per zone.
Formulas:
  sR = norm(Rainfall)
  sD = 1 - norm(DrainageCapacity)
  sW = norm(WaterLevel)
  sE = 1 - norm(Elevation)
  sH = norm(HistoricalFloodFrequency)
  FloodRisk = 100 * ( wRsR + wDsD + wWsW + wEsE + wHsH ) / SUM(w_avail)
Severity bands: >=75 CRITICAL, >=50 HIGH, >=25 MEDIUM, else LOW.
"""

from typing import Any, Dict, List, Optional
from app.engine.constants import SEVERITY_BANDS, WEIGHTS_ALG1

FACTOR_NAMES = {
    "R": "Rainfall Inundation",
    "D": "Drainage Constriction",
    "W": "River Water Stage",
    "E": "Low Ground Elevation",
    "H": "Historical Flood Vulnerability",
}


def compute_flood_risk(prepared_zone: Dict[str, Any]) -> Dict[str, Any]:
    """Calculates deterministic Flood Risk Score (0-100) and severity band.

    If zone status is DATA_INSUFFICIENT, returns an explicit un-scored record.
    Never manufactures or invents a risk score for insufficient data.
    """
    zone_id = prepared_zone.get("zone_id", "UNKNOWN")
    name = prepared_zone.get("name", zone_id)
    flags = list(prepared_zone.get("flags", []))

    if not prepared_zone.get("is_scorable") or prepared_zone.get("status") == "DATA_INSUFFICIENT":
        return {
            "zone_id": zone_id,
            "name": name,
            "score": None,
            "raw_score": None,
            "normalized_score": None,
            "severity": "DATA_INSUFFICIENT",
            "dominant_cause": None,
            "breakdown": {},
            "flags": flags,
            "status": "DATA_INSUFFICIENT",
            "is_scorable": False,
            "is_hotspot": False,
        }

    norm = prepared_zone.get("normalized", {})

    # Compute raw factors (each in [0.0, 1.0], where higher = higher risk)
    factors: Dict[str, float] = {}

    # Rainfall (higher rainfall = higher risk)
    if norm.get("R") is not None:
        factors["R"] = norm["R"]

    # Drainage Capacity (lower capacity = higher risk -> invert: 1 - norm)
    if norm.get("D") is not None:
        factors["D"] = 1.0 - norm["D"]

    # Water Level (higher stage = higher risk)
    if norm.get("W") is not None:
        factors["W"] = norm["W"]

    # Elevation (lower ground = higher risk -> invert: 1 - norm)
    if norm.get("E") is not None:
        factors["E"] = 1.0 - norm["E"]

    # History (higher frequency/saturation = higher risk)
    if norm.get("H") is not None:
        factors["H"] = norm["H"]

    avail_keys = list(factors.keys())
    weight_sum = sum(WEIGHTS_ALG1[k] for k in avail_keys)

    if weight_sum <= 0.0 or len(avail_keys) == 0:
        flags.append("no_available_risk_factors")
        return {
            "zone_id": zone_id,
            "name": name,
            "score": None,
            "raw_score": None,
            "normalized_score": None,
            "severity": "DATA_INSUFFICIENT",
            "dominant_cause": None,
            "breakdown": {},
            "flags": flags,
            "status": "DATA_INSUFFICIENT",
            "is_scorable": False,
            "is_hotspot": False,
        }

    # Compute weighted score with dynamic re-scaling for missing optional fields
    weighted_sum = sum((WEIGHTS_ALG1[k] / weight_sum) * factors[k] for k in avail_keys)
    raw_score = 100.0 * weighted_sum
    score = round(raw_score, 1)
    normalized_score = round(score / 100.0, 4)

    # Classify Severity Band
    if score >= SEVERITY_BANDS["CRITICAL"]:
        severity = "CRITICAL"
    elif score >= SEVERITY_BANDS["HIGH"]:
        severity = "HIGH"
    elif score >= SEVERITY_BANDS["MEDIUM"]:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    # Explainable factor breakdown (critical cause)
    breakdown = {
        k: {
            "factor_name": FACTOR_NAMES.get(k, k),
            "factor_value": round(factors[k], 4),
            "effective_weight": round(WEIGHTS_ALG1[k] / weight_sum, 4),
            "weighted_contribution": round(100.0 * (WEIGHTS_ALG1[k] / weight_sum) * factors[k], 2),
        }
        for k in avail_keys
    }

    # Find dominant critical cause
    dominant_key = max(
        breakdown.items(), key=lambda item: item[1]["weighted_contribution"]
    )[0]
    dominant_cause = FACTOR_NAMES.get(dominant_key, dominant_key)

    is_hotspot = score >= 50.0

    return {
        "zone_id": zone_id,
        "name": name,
        "score": score,
        "raw_score": round(raw_score, 3),
        "normalized_score": normalized_score,
        "severity": severity,
        "dominant_cause": dominant_cause,
        "breakdown": breakdown,
        "flags": flags,
        "status": prepared_zone.get("status", "COMPLETE"),
        "is_scorable": True,
        "is_hotspot": is_hotspot,
    }


def compute_all_flood_risks(prepared_zones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculates flood risks for a collection of prepared zones."""
    return [compute_flood_risk(z) for z in prepared_zones]
