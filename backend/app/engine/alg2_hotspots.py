"""Algorithm 2 — Flood Hotspot Detection.

Canonical Report Page 12:
Reads the stored FloodRisk from Algorithm 1.
Ranks zones descending by risk score.
Zones with score >= HOTSPOT_THRESHOLD (default 50.0) qualify as hotspots.
If no zone qualifies, returns an empty list triggering 'MONITORING_ONLY' status.
"""

from typing import Any, Dict, List
from app.engine.constants import HOTSPOT_THRESHOLD


def detect_hotspots(
    scored_zones: List[Dict[str, Any]],
    threshold: float = HOTSPOT_THRESHOLD,
) -> Dict[str, Any]:
    """Detects and ranks priority flood hotspots from stored Algorithm 1 scores.

    Does NOT recompute risk scores.
    """
    # Filter only scorable zones with valid non-null score
    valid_scored = [
        z for z in scored_zones
        if z is not None and z.get("is_scorable") and z.get("score") is not None
    ]

    # Sort descending by score
    ranked_all = sorted(valid_scored, key=lambda z: z["score"], reverse=True)

    # Hotspots exceeding threshold
    hotspots = [z for z in ranked_all if z["score"] >= threshold]

    is_monitoring_only = len(hotspots) == 0
    status = "MONITORING_ONLY" if is_monitoring_only else "HOTSPOTS_DETECTED"

    return {
        "hotspots": hotspots,
        "ranked_zones": ranked_all,
        "hotspot_count": len(hotspots),
        "is_monitoring_only": is_monitoring_only,
        "status": status,
        "threshold_applied": threshold,
    }
