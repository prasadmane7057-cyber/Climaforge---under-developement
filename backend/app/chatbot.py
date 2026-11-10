"""Grounded, read-only chatbot service for CLIMAFORGE outputs."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from app.config import settings
from app.engine.pipeline import execute_risk_engine
from app.routers.audit import SESSION_AUDIT_LOGS
from app.schemas.scenario_data import get_scenario_by_id
from app.services.alert_service import generate_scenario_alerts


READ_ONLY_SAFETY = (
    "You are the CLIMAFORGE Grounded Assistant. Use only the supplied JSON context. "
    "Do not invent values, locations, timestamps, populations, costs, interventions, "
    "forecasts or sources. Distinguish deterministic engine outputs from general explanations. "
    "Rainfall ML experiments are not reliable flood forecasts and must not be cited as flood evidence. "
    "Recommended interventions are recommendations, not deployed actions. "
    "If information is unavailable, say so clearly. Never provide commands to replace official emergency services."
)


def build_grounded_context(scenario_id: str, question: str) -> dict[str, Any]:
    del question  # Context availability is scenario-wide; relevance is selected in fallback/LLM.
    detail = get_scenario_by_id(scenario_id)
    if detail is None:
        return {"status": "unavailable", "error": "Scenario not found", "scenario_id": scenario_id}

    raw_zones = [
        {
            "zone_id": zone.zone_id,
            "name": zone.name,
            "rainfall_mm": zone.rainfall_mm,
            "drainage_capacity_cms": zone.drainage_capacity_cms,
            "elevation_m": zone.elevation_m,
            "soil_saturation_index": zone.soil_saturation_index,
            "water_level_m": zone.water_level_m,
            "population": zone.population,
            "critical_infrastructure_count": zone.critical_infrastructure_count,
            "road_length_km": zone.road_length_km,
            "emergency_routes_count": zone.emergency_routes_count,
        }
        for zone in detail.zones
    ]
    analysis = execute_risk_engine(
        raw_zones=raw_zones,
        scenario_id=detail.scenario_id,
        scenario_name=detail.name,
    )

    zones = sorted(
        analysis.get("zones", []),
        key=lambda zone: zone.get("score") if zone.get("score") is not None else -1,
        reverse=True,
    )
    recent_audit = [
        {
            "event_id": event.event_id,
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "source": event.source,
            "description": event.description,
            "details": event.details,
        }
        for event in sorted(SESSION_AUDIT_LOGS, key=lambda event: event.timestamp, reverse=True)[:5]
    ]

    return {
        "status": "available",
        "scenario": {
            "scenario_id": detail.scenario_id,
            "name": detail.name,
            "description": detail.description,
            "data_label": detail.data_label,
        },
        "deterministic_analysis": {
            "execution_timestamp": analysis["execution_timestamp"],
            "spec_version": analysis["spec_version"],
            "data_label": analysis["data_label"],
            "pipeline_status": analysis["pipeline_status"],
            "is_monitoring_only": analysis["is_monitoring_only"],
            "zone_count": analysis["zone_count"],
            "scorable_zone_count": analysis["scorable_zone_count"],
            "insufficient_zone_count": analysis["insufficient_zone_count"],
            "hotspot_count": analysis["hotspot_count"],
            "highest_risk_score": analysis["highest_risk_score"],
            "highest_risk_zone_name": analysis["highest_risk_zone_name"],
            "zones": zones,
            "exposure_results": analysis.get("exposure_results", []),
            "cascade_status": analysis.get("cascade_status"),
            "cascade_analysis": analysis.get("cascade_analysis"),
            "critical_nodes": analysis.get("critical_nodes"),
            "resource_allocation": analysis.get("resource_allocation"),
            "intervention_ranking": analysis.get("intervention_ranking"),
            "what_if_analysis": analysis.get("what_if_analysis"),
            "alternative_comparison": analysis.get("alternative_comparison"),
            "decision_card": analysis.get("decision_card"),
            "data_quality_flags": analysis.get("data_quality_flags", []),
        },
        "scenario_definitions": {
            "zones": [
                {
                    "zone_id": zone.zone_id,
                    "name": zone.name,
                    "population": zone.population,
                    "rainfall_mm": zone.rainfall_mm,
                    "elevation_m": zone.elevation_m,
                    "data_provenance": zone.data_provenance,
                }
                for zone in detail.zones
            ],
            "intervention_catalogue": [
                {
                    "intervention_id": intervention.intervention_id,
                    "name": intervention.name,
                    "target_zone_id": intervention.target_zone_id,
                    "target_node_id": intervention.target_node_id,
                    "required_resources": intervention.required_resources,
                    "cost_estimate_usd": intervention.cost_estimate_usd,
                    "lead_time_minutes": intervention.lead_time_minutes,
                }
                for intervention in detail.interventions
            ],
            "safe_points": detail.safe_points,
        },
        "safe_points": detail.safe_points,
        "alerts": [
            alert.model_dump(mode="json")
            for alert in generate_scenario_alerts(detail, analysis).alerts
        ],
        "recent_audit_events": recent_audit,
        "experimental_models": {
            "status": "not_authoritative",
            "notice": "M11-M14 rainfall experiments are research-only and must not be described as reliable flood predictions.",
        },
        "unavailable_information": [
            "Live sensors",
            "Confirmed flood occurrences",
            "Official evacuation status",
            "Real-time intervention deployment status",
        ],
    }


def deterministic_fallback(question: str, context: dict[str, Any]) -> str:
    if context["status"] != "available":
        return "I cannot answer that from the current CLIMAFORGE data because the requested scenario is unavailable. No fallback values were invented."

    analysis = context["deterministic_analysis"]
    lower = question.lower()
    zones = analysis["zones"]

    if any(term in lower for term in ("missing", "unavailable", "data quality", "information")):
        missing = analysis["data_quality_flags"]
        unavailable = context["unavailable_information"]
        pieces = []
        if missing:
            pieces.append("Data-quality flags: " + "; ".join(str(flag) for flag in missing[:6]) + ".")
        pieces.append("Unavailable from this system: " + ", ".join(unavailable) + ".")
        return "Grounded deterministic context:\n\n" + "\n".join(pieces)

    if any(term in lower for term in ("evacuat", "route", "shelter", "safe point", "safe-point", "safe points", "alert", "warning")):
        safe_points = context.get("safe_points") or context.get("scenario_definitions", {}).get("safe_points", [])
        alerts = context.get("alerts", [])
        lines = []
        if alerts:
            lines.append("Active pre-calamity alerts (simulated):")
            for a in alerts[:4]:
                lines.append(f"- [{a.get('severity')}] {a.get('zone_name')}: {a.get('headline')} (Cause: {a.get('dominant_cause')})")
        if safe_points:
            lines.append("\nDesignated emergency safe points / shelters:")
            for sp in safe_points[:3]:
                lines.append(f"- {sp.get('name')} (Zone: {sp.get('zone_id')}, Capacity: {sp.get('capacity_persons')}, Elevation: {sp.get('elevation_m')}m)")
        lines.append("\nEvacuation routing must strictly avoid flooded and failing infrastructure nodes. Simulated guidance only; not live confirmed.")
        return "Grounded evacuation & alert context:\n\n" + "\n".join(lines)

    if any(term in lower for term in ("intervention", "recommend", "compare", "resource", "what happens", "what-if")):
        ranking = analysis.get("intervention_ranking") or {}
        feasible = ranking.get("feasible", [])
        if not feasible:
            return "No feasible intervention ranking is available in the current deterministic analysis. Recommendations or deployments have not been inferred."
        lines = []
        for item in feasible[:5]:
            lines.append(
                f"- {item.get('name', item.get('action', 'Unknown action'))}: score "
                f"{item.get('score', 'unavailable')}; target {item.get('target_node', 'unavailable')}; "
                f"required resources {item.get('required_resources', {})}."
            )
        allocation = analysis.get("resource_allocation") or {}
        if allocation.get("remaining_inventory") is not None:
            lines.append(f"Remaining inventory from Algorithm 8: {allocation['remaining_inventory']}.")
        what_if = analysis.get("what_if_analysis")
        if what_if:
            lines.append(
                f"What-if before/after impact index: {what_if.get('before', {}).get('impact_index')} -> "
                f"{what_if.get('after', {}).get('impact_index')}."
            )
        return "Grounded deterministic intervention context:\n\n" + "\n".join(lines) + "\n\nThese are recommendations only; deployment is not implied."

    if any(term in lower for term in ("consequence", "cascade", "critical node", "dependency", "graph")):
        cascade = analysis.get("cascade_analysis")
        critical = analysis.get("critical_nodes") or {}
        if not cascade and not critical:
            return "The consequence analysis was not available. This assessment did not confirm downstream consequences or a critical node."
        parts = []
        if cascade:
            parts.append(
                f"Cascade status: {analysis.get('cascade_status', 'unavailable')}; "
                f"cascade risk {cascade.get('cascade_risk', 'unavailable')}; "
                f"chain {cascade.get('cascade_chain', []) or 'not reported'}."
            )
        critical_node = critical.get("critical_node")
        if critical_node:
            parts.append(f"Algorithm 6 critical node: {critical_node}.")
        return "Grounded consequence context:\n\n" + "\n".join(parts)

    if any(term in lower for term in ("location", "area", "zone", "affected", "which", "highest", "high risk")):
        if not zones:
            return "No zone-level deterministic risk results are available for this scenario."
        lines = [
            f"Scenario data label: {context['scenario']['data_label']}."
        ]
        for zone in zones[:5]:
            lines.append(
                f"- {zone.get('name', zone.get('zone_id', 'Unknown zone'))}: "
                f"score {zone.get('score', 'unavailable')}, severity {zone.get('severity', 'unavailable')}, "
                f"hotspot {zone.get('is_hotspot', 'unavailable')}, "
                f"dominant cause {zone.get('dominant_cause', 'not reported')}."
            )
        return "Grounded deterministic risk context:\n\n" + "\n".join(lines)

    if any(term in lower for term in ("risk", "why", "explain", "assessment", "simple")):
        if not zones:
            return "The current scenario has no scorable zone results. It is unsafe to explain a risk assessment as if values were available."
        highest = analysis["highest_risk_zone_name"]
        top = zones[0]
        return (
            "Grounded deterministic risk explanation:\n\n"
            f"The highest-risk named zone is {highest}, with score "
            f"{top.get('score', 'unavailable')} and severity {top.get('severity', 'unavailable')} "
            f"under {analysis['pipeline_status']} status. "
            f"The reported dominant cause is {top.get('dominant_cause', 'not reported')}."
        )

    return (
        "I can use the current scenario's deterministic zone risk, exposure, cascade, intervention, "
        "resource, alternative comparison and audit context. I could not identify a grounded answer "
        "for that wording. Try asking about risk, affected zones, consequences, interventions, "
        "what-if results, missing data, or the audit trail."
    )


def provider_is_configured() -> bool:
    provider = (settings.nugen_provider or "").strip().lower()
    legacy_provider = (settings.chatbot_provider or "").strip().lower()
    active_provider = provider if provider in {"nugen", "openai-compatible", "openai_compatible"} else legacy_provider
    api_key = settings.nugen_api_key or settings.chatbot_api_key
    endpoint = settings.nugen_api_url or settings.nugen_endpoint or settings.chatbot_endpoint
    return (
        settings.nugen_enabled
        and not settings.nugen_mock_mode
        and active_provider in {"nugen", "openai-compatible", "openai_compatible"}
        and bool(api_key)
        and bool(endpoint)
    )


def call_openai_compatible(question: str, history: list[dict[str, str]], context: dict[str, Any]) -> str:
    if not provider_is_configured():
        raise RuntimeError("No supported LLM provider is configured.")

    messages: list[dict[str, str]] = [{"role": "system", "content": READ_ONLY_SAFETY}]
    messages.append({
        "role": "system",
        "content": "Grounded CLIMAFORGE context JSON (authoritative only where labeled deterministic):\n" +
                   json.dumps(context, default=str, ensure_ascii=False, separators=(",", ":"))[:24000],
    })
    for item in history[-12:]:
        role = item.get("role")
        content = item.get("content", "")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content[:2000]})
    messages.append({"role": "user", "content": question[:2000]})

    model = settings.nugen_model or settings.chatbot_model or "Qwen/Qwen2.5-0.5B-Instruct"
    max_tokens = getattr(settings, "nugen_max_tokens", 500) or 500
    temperature = getattr(settings, "nugen_temperature", 0.1) or 0.1
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    api_key = settings.nugen_api_key or settings.chatbot_api_key
    endpoint = settings.nugen_api_url or settings.nugen_endpoint or settings.chatbot_endpoint
    timeout = settings.nugen_timeout_seconds if settings.nugen_timeout_seconds else settings.chatbot_timeout_seconds
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "CLIMAFORGE-Advisory-Client/1.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload_result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, Exception) as exc:
        raise RuntimeError("LLM provider request failed") from exc

    choices = payload_result.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("LLM provider returned an invalid response")
    content = choices[0].get("message", {}).get("content") if isinstance(choices[0], dict) else None
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("LLM provider returned empty content")
    return content.strip()[:8000]


def generate_answer(
    scenario_id: str,
    question: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    context = build_grounded_context(scenario_id, question)
    if provider_is_configured():
        try:
            return {
                "answer": call_openai_compatible(question, history or [], context),
                "source": "LLM",
                "mode": "grounded_llm",
                "scenario_id": scenario_id,
                "context_available": context["status"] == "available",
            }
        except RuntimeError:
            pass
    return {
        "answer": deterministic_fallback(question, context),
        "source": "DETERMINISTIC_FALLBACK",
        "mode": "deterministic_fallback",
        "scenario_id": scenario_id,
        "context_available": context["status"] == "available",
    }
