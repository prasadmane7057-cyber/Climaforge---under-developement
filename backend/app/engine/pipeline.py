"""CLIMAFORGE Deterministic Risk Engine Pipeline (Algorithms 0–13).

Executes Algorithms 0 through 13 in strict documented sequence:
- Algorithm 0:  Input validation & fixed reference range normalization
- Algorithm 1:  FloodRisk (0-100) and severity band classification
- Algorithm 2:  Hotspot ranking and detection (threshold >= 50.0)
- Algorithm 3:  Flood impact & exposure calculation for hotspots only
- Algorithm 4:  Consequence dependency graph construction
- Algorithm 5:  Cascade detection & Noisy-OR probability propagation
- Algorithm 6:  Critical node identification (max-scaled features + weights v)
- Algorithm 7:  Cascade-break point detection & simulation (shared simulate())
- Algorithm 8:  Resource priority optimization & depot allocation
- Algorithm 10: Intervention priority ranking (multi-criteria score)
- Algorithm 11: Counterfactual / what-if simulation (before/after measures)
- Algorithm 12: Alternative intervention comparison (top-K + no-action)
- Algorithm 13: Final decision engine & Command Decision Card
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.engine.alg0_data_prep import prepare_all_zones
from app.engine.alg1_flood_risk import compute_all_flood_risks
from app.engine.alg2_hotspots import detect_hotspots
from app.engine.alg3_exposure import compute_hotspot_exposures
from app.engine.alg4_graph import (
    build_consequence_graph,
    dict_to_graph,
    graph_to_dict,
)
from app.engine.alg5_cascade import cascade
from app.engine.alg6_critical_nodes import identify_critical_nodes
from app.engine.alg7_break_points import evaluate_break_points
from app.engine.alg8_resources import allocate_resources
from app.engine.alg10_ranking import rank_interventions
from app.engine.alg11_what_if import run_what_if
from app.engine.alg12_comparison import compare_alternatives
from app.engine.alg13_decision import generate_decision_card
from app.engine.constants import (
    CASCADE_THRESHOLD_TAU,
    DATA_LABEL,
    DEFAULT_RESOURCE_INVENTORY,
    HOTSPOT_THRESHOLD,
    INTERVENTION_CATALOGUE,
    SPEC_VERSION,
)


def execute_risk_engine(
    raw_zones: List[Dict[str, Any]],
    scenario_id: Optional[str] = None,
    scenario_name: Optional[str] = None,
    hotspot_threshold: float = HOTSPOT_THRESHOLD,
    custom_graph_data: Optional[Dict[str, Any]] = None,
    tau: float = CASCADE_THRESHOLD_TAU,
    resource_inventory: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """Runs the complete deterministic calculation pipeline for Algorithms 0–13.

    Guarantees:
    - Pure deterministic repeatability for identical inputs.
    - Missing required fields produce DATA_INSUFFICIENT and skip scoring.
    - 0 hotspots sets MONITORING_ONLY and skips downstream cascade analysis.
    - Clearly documents provenance and synthetic prototype disclaimer.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # 1. Algorithm 0: System Input & Data Preparation
    prepared_zones = prepare_all_zones(raw_zones)
    prepared_map = {z["zone_id"]: z for z in prepared_zones}

    # 2. Algorithm 1: Flood Risk Calculation
    scored_zones = compute_all_flood_risks(prepared_zones)

    # 3. Algorithm 2: Hotspot Detection
    hotspot_analysis = detect_hotspots(scored_zones, threshold=hotspot_threshold)
    hotspots = hotspot_analysis["hotspots"]
    is_monitoring_only = hotspot_analysis["is_monitoring_only"]

    # 4. Algorithm 3: Flood Impact / Exposure (runs only for hotspots)
    exposure_analysis = compute_hotspot_exposures(
        hotspot_zones=hotspots,
        prepared_zones_map=prepared_map,
        is_monitoring_only=is_monitoring_only,
    )
    exposure_results = exposure_analysis.get("exposures", [])
    exposure_by_zone = {e["zone_id"]: e for e in exposure_results}

    # 5. Algorithms 4–13: Cascade Analysis, Break Points & Decision Support
    #    (runs only when hotspots exist)
    cascade_status: str
    consequence_graph_dict: Optional[Dict[str, Any]] = None
    cascade_result: Optional[Dict[str, Any]] = None
    critical_nodes_result: Optional[Dict[str, Any]] = None
    break_points_result: Optional[Dict[str, Any]] = None
    resource_allocation_result: Optional[Dict[str, Any]] = None
    intervention_ranking_result: Optional[Dict[str, Any]] = None
    what_if_result: Optional[Dict[str, Any]] = None
    alternative_comparison_result: Optional[Dict[str, Any]] = None
    decision_card_result: Optional[Dict[str, Any]] = None

    if is_monitoring_only or not hotspots:
        cascade_status = "SKIPPED_MONITORING_ONLY"
    else:
        cascade_status = "SUCCESS"
        primary_hotspot = hotspots[0]
        hotspot_score = float(primary_hotspot.get("score") or 50.0)
        primary_exposure = exposure_by_zone.get(primary_hotspot["zone_id"])

        # Algorithm 4: Consequence Graph Construction
        if custom_graph_data:
            G = dict_to_graph(custom_graph_data)
        else:
            G = build_consequence_graph(
                hotspot_zone=primary_hotspot,
                exposure=primary_exposure,
            )
        consequence_graph_dict = graph_to_dict(G)

        # Algorithm 5: Cascade Detection & Noisy-OR Probability Propagation
        cascade_result = cascade(G, flood_risk=hotspot_score, tau=tau)

        # Algorithm 6: Critical Node Identification
        critical_nodes_result = identify_critical_nodes(
            G,
            p_risks=cascade_result["node_risks"],
        )

        # Algorithm 7: Cascade-Break Point Detection & Simulation
        break_points_result = evaluate_break_points(
            G,
            flood_risk=hotspot_score,
            catalogue=INTERVENTION_CATALOGUE,
            tau=tau,
        )

        # ------------------------------------------------------------------ #
        # Milestone 4: Algorithms 8, 10–13                                    #
        # ------------------------------------------------------------------ #

        # Algorithm 8: Resource Priority Optimization & Depot Allocation
        inventory = resource_inventory or DEFAULT_RESOURCE_INVENTORY
        resource_allocation_result = allocate_resources(
            hotspot_zones=hotspots,
            resource_inventory=inventory,
            catalogue=INTERVENTION_CATALOGUE,
            cascade_results_by_zone={
                primary_hotspot["zone_id"]: cascade_result
            },
            critical_node_results_by_zone={
                primary_hotspot["zone_id"]: critical_nodes_result
            },
        )

        primary_zone_id = primary_hotspot["zone_id"]
        zone_budget = resource_allocation_result["zone_budgets"].get(
            primary_zone_id, {}
        )

        # Algorithm 10: Intervention Priority Ranking
        intervention_ranking_result = rank_interventions(
            G=G,
            flood_risk=hotspot_score,
            zone_budget=zone_budget,
            catalogue=INTERVENTION_CATALOGUE,
            tau=tau,
        )

        ranked_feasible = intervention_ranking_result.get("feasible", [])
        top_action = intervention_ranking_result.get("top_action")

        # Algorithm 11: What-If Simulation (for top action if available)
        if top_action:
            # Merge with catalogue for mitigation_m / target_node
            cat_map = {e["intervention_id"]: e for e in INTERVENTION_CATALOGUE}
            top_full = {**cat_map.get(top_action["intervention_id"], {}), **top_action}
            what_if_result = run_what_if(
                G=G,
                flood_risk=hotspot_score,
                intervention=top_full,
                tau=tau,
            )
        else:
            what_if_result = run_what_if(
                G=G, flood_risk=hotspot_score, intervention=None, tau=tau
            )

        # Algorithm 12: Alternative Intervention Comparison
        alternative_comparison_result = compare_alternatives(
            G=G,
            flood_risk=hotspot_score,
            ranked_feasible=ranked_feasible,
            zone_budget=zone_budget,
            catalogue=INTERVENTION_CATALOGUE,
            tau=tau,
        )

        # Algorithm 13: Final Decision Card
        top_critical_node = (
            critical_nodes_result.get("critical_nodes", [None])[0]
            if critical_nodes_result
            else None
        )
        nugen_rec = intervention_ranking_result.get("nugen_recommendation")
        decision_card_result = generate_decision_card(
            ranked_feasible=ranked_feasible,
            zone_budget=zone_budget,
            G=G,
            flood_risk=hotspot_score,
            hotspot_zone=primary_hotspot,
            cascade_result=cascade_result,
            critical_node=top_critical_node,
            nugen_result=nugen_rec,
            catalogue=INTERVENTION_CATALOGUE,
            tau=tau,
        )


    # Compute overall scenario summary metrics
    valid_scores = [z["score"] for z in scored_zones if z.get("score") is not None]
    if valid_scores:
        highest_risk_score = max(valid_scores)
        top_zone = next(z for z in scored_zones if z.get("score") == highest_risk_score)
        highest_risk_zone_name = top_zone.get("name", top_zone.get("zone_id", "UNKNOWN"))
    else:
        highest_risk_score = 0.0
        highest_risk_zone_name = "N/A (All zones insufficient)"

    insufficient_count = sum(
        1 for z in prepared_zones if z.get("status") == "DATA_INSUFFICIENT"
    )

    if insufficient_count == len(prepared_zones) and len(prepared_zones) > 0:
        pipeline_status = "DATA_INSUFFICIENT"
    elif is_monitoring_only:
        pipeline_status = "MONITORING_ONLY"
    elif insufficient_count > 0:
        pipeline_status = "PARTIAL_DATA"
    else:
        pipeline_status = "SUCCESS"

    all_flags = []
    for z in prepared_zones:
        for f in z.get("flags", []):
            all_flags.append(f"{z['zone_id']}: {f}")

    executed_algorithms = [
        "Algorithm 0: System Input & Data Preparation",
        "Algorithm 1: Flood Risk Score (0-100)",
        "Algorithm 2: Flood Hotspot Detection",
        "Algorithm 3: Flood Impact & Exposure Calculation",
    ]
    if cascade_status == "SUCCESS":
        executed_algorithms.extend([
            "Algorithm 4: Consequence Dependency Graph Construction",
            "Algorithm 5: Cascade Detection & Noisy-OR Propagation",
            "Algorithm 6: Critical Node Identification",
            "Algorithm 7: Cascade-Break Point Detection & Simulation",
            "Algorithm 8: Resource Priority Optimization & Depot Allocation",
            "Algorithm 10: Intervention Priority Ranking",
            "Algorithm 11: Counterfactual / What-If Simulation",
            "Algorithm 12: Alternative Intervention Comparison",
            "Algorithm 13: Final Decision Engine & Command Decision Card",
        ])

    return {
        "scenario_id": scenario_id or "adhoc-evaluation",
        "scenario_name": scenario_name or "Ad-hoc Catchment Evaluation",
        "execution_timestamp": timestamp,
        "spec_version": SPEC_VERSION,
        "data_label": DATA_LABEL,
        "pipeline_status": pipeline_status,
        "is_monitoring_only": is_monitoring_only,
        "hotspot_threshold_applied": hotspot_threshold,
        "zone_count": len(prepared_zones),
        "scorable_zone_count": len(valid_scores),
        "insufficient_zone_count": insufficient_count,
        "hotspot_count": len(hotspots),
        "highest_risk_score": highest_risk_score,
        "highest_risk_zone_name": highest_risk_zone_name,
        "executed_algorithms": executed_algorithms,
        "zones": scored_zones,
        "hotspots": hotspots,
        "exposure_results": exposure_results,
        "exposure_status": exposure_analysis.get("status"),
        "cascade_status": cascade_status,
        "consequence_graph": consequence_graph_dict,
        "cascade_analysis": cascade_result,
        "critical_nodes": critical_nodes_result,
        "break_points": break_points_result,
        "resource_allocation": resource_allocation_result,
        "intervention_ranking": intervention_ranking_result,
        "what_if_analysis": what_if_result,
        "alternative_comparison": alternative_comparison_result,
        "decision_card": decision_card_result,
        "data_quality_flags": all_flags,
    }

