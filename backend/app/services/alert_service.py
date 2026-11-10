"""CLIMAFORGE Milestone 6 Pre-Calamity Alert Service.

Generates citizen-facing pre-calamity emergency warnings grounded in authoritative
deterministic risk calculations from Algorithm 1 and Algorithm 2.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.engine.constants import SEVERITY_BANDS
from app.engine.pipeline import execute_risk_engine
from app.schemas.routing import CitizenAlertItem, ScenarioAlertsResponse
from app.schemas.scenarios import ScenarioDetail


ALERT_SEVERITY_THRESHOLDS = SEVERITY_BANDS

ALERT_ACTION_RECOMMENDATIONS = {
    "CRITICAL": "Immediate evacuation required. Proceed along designated safe evacuation corridors to confirmed shelters.",
    "HIGH": "Prepare emergency go-kits and stage for potential evacuation. Monitor local flood routes and avoid low ground.",
    "MEDIUM": "Maintain elevated situational awareness. Verify household emergency plans and confirm shelter locations.",
    "LOW": "Normal emergency preparedness. Continue monitoring weather bulletins and drainage conditions.",
    "DATA_INSUFFICIENT": "Telemetry incomplete for this catchment. Ground verification and precautionary vigilance advised.",
}


def classify_alert_severity(score: Optional[float], is_scorable: bool = True) -> str:
    """Classify risk score into authoritative severity band."""
    if not is_scorable or score is None:
        return "DATA_INSUFFICIENT"
    if score >= ALERT_SEVERITY_THRESHOLDS["CRITICAL"]:
        return "CRITICAL"
    if score >= ALERT_SEVERITY_THRESHOLDS["HIGH"]:
        return "HIGH"
    if score >= ALERT_SEVERITY_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    return "LOW"


def generate_zone_headline(zone_name: str, severity: str) -> str:
    """Generate concise, high-contrast headline for citizen alerts."""
    if severity == "CRITICAL":
        return f"CRITICAL EVACUATION WARNING: Severe Inundation Threat in {zone_name}"
    if severity == "HIGH":
        return f"HIGH FLOOD ADVISORY: Significant Flood Threat in {zone_name}"
    if severity == "MEDIUM":
        return f"MEDIUM FLOOD WATCH: Elevated Inundation Potential in {zone_name}"
    if severity == "LOW":
        return f"LOW FLOOD ADVISORY: Normal Baseline Monitoring in {zone_name}"
    return f"DATA NOTICE: Incomplete Telemetry in {zone_name}"


def generate_zone_description(zone_name: str, score: Optional[float], severity: str, dominant_cause: Optional[str]) -> str:
    """Generate clear, non-alarmist, citizen-facing explanation grounded in engine evidence."""
    cause_phrase = f"Primary hazard driver: {dominant_cause}." if dominant_cause else "Hydrological indicators within monitored threshold."
    if severity == "CRITICAL":
        score_text = f"{score:.1f}/100" if score is not None else "CRITICAL"
        return (
            f"Immediate pre-calamity warning for {zone_name}. Deterministic risk index is {score_text}. "
            f"{cause_phrase} Ground saturation and expected rainfall exceed local drainage capacity. "
            f"Residents should prepare for orderly evacuation to designated safe shelters."
        )
    if severity == "HIGH":
        score_text = f"{score:.1f}/100" if score is not None else "HIGH"
        return (
            f"High flood risk detected for {zone_name} (risk index: {score_text}). {cause_phrase} "
            f"Localized surface ponding and roadway sheetflow are likely. Review evacuation routes and secure valuables."
        )
    if severity == "MEDIUM":
        score_text = f"{score:.1f}/100" if score is not None else "MEDIUM"
        return (
            f"Flood watch in effect for {zone_name} (risk index: {score_text}). {cause_phrase} "
            f"Catchment capacity is moderately stressed. Avoid low-lying riverfront corridors."
        )
    if severity == "LOW":
        score_text = f"{score:.1f}/100" if score is not None else "LOW"
        return (
            f"Catchment conditions in {zone_name} are within normal baseline capacity (risk index: {score_text}). {cause_phrase}"
        )
    return (
        f"Sensor telemetry is currently incomplete for {zone_name}. Precautionary monitoring is advised."
    )


def generate_scenario_alerts(
    scenario: ScenarioDetail,
    deterministic_analysis: Optional[Dict[str, Any]] = None,
) -> ScenarioAlertsResponse:
    """Generates authoritative pre-calamity citizen alerts from scenario risk output.

    Guarantees:
    - Never fabricates readings; uses actual Algorithm 1/2 outputs.
    - Dominant cause directly reflects highest weighted risk contributor.
    - Strict classification thresholds: CRITICAL >= 75, HIGH >= 50, MEDIUM >= 25, LOW < 25.
    - Explicit simulated label: is_live_confirmed=False, is_simulated=True.
    """
    now = datetime.now(timezone.utc)

    # If analysis is not provided, execute the authoritative deterministic pipeline
    if deterministic_analysis is None:
        raw_zones = [
            {
                "zone_id": z.zone_id,
                "name": z.name,
                "rainfall_mm": z.rainfall_mm,
                "drainage_capacity_cms": z.drainage_capacity_cms,
                "elevation_m": z.elevation_m,
                "soil_saturation_index": z.soil_saturation_index,
                "water_level_m": z.water_level_m,
                "population": z.population,
                "critical_infrastructure_count": z.critical_infrastructure_count,
                "road_length_km": z.road_length_km,
                "emergency_routes_count": z.emergency_routes_count,
            }
            for z in scenario.zones
        ]
        deterministic_analysis = execute_risk_engine(
            raw_zones=raw_zones,
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
        )

    zones_data = deterministic_analysis.get("zones", [])
    alerts: List[CitizenAlertItem] = []
    severity_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "DATA_INSUFFICIENT": 0}
    highest_severity = "LOW"

    for z in zones_data:
        zone_id = z.get("zone_id", "UNKNOWN")
        zone_name = z.get("name", zone_id)
        score = z.get("score")
        is_scorable = z.get("is_scorable", True)
        dominant_cause = z.get("dominant_cause") or "Hydrological Baseline"

        severity = classify_alert_severity(score, is_scorable)
        if severity_order.get(severity, 0) > severity_order.get(highest_severity, 0):
            highest_severity = severity

        headline = generate_zone_headline(zone_name, severity)
        description = generate_zone_description(zone_name, score, severity, dominant_cause)
        action = ALERT_ACTION_RECOMMENDATIONS.get(severity, ALERT_ACTION_RECOMMENDATIONS["LOW"])

        alert_id = f"ALERT-{scenario.scenario_id}-{zone_id}"
        alerts.append(
            CitizenAlertItem(
                alert_id=alert_id,
                scenario_id=scenario.scenario_id,
                zone_id=zone_id,
                zone_name=zone_name,
                severity=severity,
                risk_score=float(score) if score is not None else 0.0,
                dominant_cause=dominant_cause,
                headline=headline,
                description=description,
                action_recommendation=action,
                is_simulated=True,
                is_live_confirmed=False,
                disclaimer=(
                    "SIMULATED / ILLUSTRATIVE ALERT ONLY. Authoritative emergency directions "
                    "require official civil defense verification."
                ),
                generated_at=now,
            )
        )

    # Sort alerts so CRITICAL and HIGH appear at top
    alerts.sort(key=lambda item: severity_order.get(item.severity, 0), reverse=True)

    affected_zones = sum(1 for a in alerts if a.severity in ("CRITICAL", "HIGH", "MEDIUM"))

    return ScenarioAlertsResponse(
        scenario_id=scenario.scenario_id,
        scenario_name=scenario.name,
        generated_at=now,
        alerts=alerts,
        highest_severity=highest_severity,
        affected_zone_count=affected_zones,
        is_simulated=True,
        is_live_confirmed=False,
        disclaimer="SIMULATED / ILLUSTRATIVE ALERTS ONLY. For demonstrator and emergency planning purposes.",
    )

