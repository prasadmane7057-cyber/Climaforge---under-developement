"""CLIMAFORGE Algorithm 13: Final Decision Engine.

Iterates through the ranked feasible interventions from Algorithm 10/12 and
performs a final re-verification of each candidate before issuing the Command
Decision Card.  If all candidates fail re-verification, the card status is
set to NO_FEASIBLE_INTERVENTION.

Implements Section 6.5 (Algorithm 13) of the CLIMAFORGE Algorithm Design &
Implementation Report v2.

Final verification checks (per candidate):
    1. Target node exists in the consequence graph G.
    2. Required resources are still available in the zone budget.
    3. RiskReduction > 0  (intervention must reduce cascade risk).

Decision Card fields:
    status, priority, zone_id, target_node, action, intervention_id,
    required_resources, reason, expected_impact (before/after/reductions),
    modelled_relative_change, quality_flags, ai_status, nugen_recommendation,
    nugen_agreement, human_review_warning, run_id, blockers (NO_FEASIBLE only),
    rejected_candidates.
"""

import uuid
from typing import Any, Dict, List, Optional

import networkx as nx

from app.engine.alg5_cascade import simulate
from app.engine.alg11_what_if import run_what_if
from app.engine.constants import CASCADE_THRESHOLD_TAU, DATA_LABEL


# ---------------------------------------------------------------------------
# Human-review warning text (always included per M4 spec)
# ---------------------------------------------------------------------------
_HUMAN_REVIEW_WARNING = (
    "SYNTHETIC / ILLUSTRATIVE DATA ONLY — This decision card is produced by a "
    "prototype model using simulated zone data. All outputs must be reviewed and "
    "verified by qualified emergency management personnel before any operational "
    "action is taken. Model indices are indicative only and do not constitute "
    "professional engineering advice."
)


# ---------------------------------------------------------------------------
# Re-verification
# ---------------------------------------------------------------------------


def verify_candidate(
    action: Dict[str, Any],
    zone_budget: Dict[str, int],
    G: nx.DiGraph,
    flood_risk: float,
    baseline_sim: Optional[Dict[str, Any]] = None,
    tau: float = CASCADE_THRESHOLD_TAU,
) -> tuple:
    """Final re-check of a candidate intervention before issuing the Decision Card.

    Checks (in order):
        1. Target node exists in G.
        2. Every required resource has sufficient remaining budget.
        3. RiskReduction > 0  (post-intervention cascade_risk < baseline).

    Args:
        action: Catalogue entry to verify.
        zone_budget: Remaining resource budget {resource_type: count}.
        G: Consequence graph.
        flood_risk: FloodRisk score (0–100).
        baseline_sim: Pre-computed baseline simulate() result.  If None, it is
            computed internally (slightly slower).
        tau: Cascade threshold.

    Returns:
        (passed: bool, blockers: List[str])
    """
    blockers: List[str] = []

    # Check 1: target node exists
    target_node = action.get("target_node")
    if not target_node or target_node not in G.nodes:
        blockers.append(
            f"Target node '{target_node}' not found in consequence graph."
        )

    # Check 2: resources available
    for resource, needed in action.get("required_resources", {}).items():
        granted = zone_budget.get(resource, 0)
        if granted < needed:
            blockers.append(
                f"Resource '{resource}': need {needed}, budget has {granted}."
            )

    # Check 3: positive risk reduction
    if not blockers:  # only simulate if structural checks pass
        if baseline_sim is None:
            baseline_sim = simulate(G, flood_risk=flood_risk, intervention=None, tau=tau)
        post_sim = simulate(G, flood_risk=flood_risk, intervention=action, tau=tau)

        baseline_risk = float(baseline_sim.get("cascade_risk", 0.0))
        post_risk = float(post_sim.get("cascade_risk", 0.0))
        if not (post_risk < baseline_risk):
            blockers.append(
                f"RiskReduction ≤ 0 (baseline={baseline_risk:.4f}, "
                f"post={post_risk:.4f}). Intervention offers no modelled benefit."
            )

    return (len(blockers) == 0, blockers)


# ---------------------------------------------------------------------------
# Decision Card generation
# ---------------------------------------------------------------------------


def generate_decision_card(
    ranked_feasible: List[Dict[str, Any]],
    zone_budget: Dict[str, int],
    G: nx.DiGraph,
    flood_risk: float,
    hotspot_zone: Optional[Dict[str, Any]] = None,
    cascade_result: Optional[Dict[str, Any]] = None,
    critical_node: Optional[Dict[str, Any]] = None,
    nugen_result: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
    catalogue: Optional[List[Dict[str, Any]]] = None,
    tau: float = CASCADE_THRESHOLD_TAU,
) -> Dict[str, Any]:
    """Generate the Command Decision Card from the ranked feasible interventions.

    Iterates through ``ranked_feasible`` in order; applies verify_candidate()
    to each.  The first passing candidate becomes the recommended action.
    If none pass, returns a NO_FEASIBLE_INTERVENTION card.

    Args:
        ranked_feasible: Ordered feasible list from Algorithm 10.
        zone_budget: Remaining resource budget for this zone.
        G: Consequence graph (not mutated).
        flood_risk: FloodRisk score (0–100) for the zone.
        hotspot_zone: Primary hotspot zone dict from Algorithm 2.
        cascade_result: Algorithm 5 result dict for the zone.
        critical_node: Top critical node dict from Algorithm 6.
        nugen_result: Nugen recommendation dict (mock in M4).
        run_id: Optional caller-provided run identifier; generated if None.
        catalogue: Full catalogue for resolving action details if needed.
        tau: Cascade threshold.

    Returns:
        Decision card dict (see module docstring for field list).
    """
    if run_id is None:
        run_id = str(uuid.uuid4())

    zone_id = (hotspot_zone or {}).get("zone_id", "UNKNOWN")
    zone_severity = (hotspot_zone or {}).get("severity", "MODERATE")

    # Build catalogue lookup
    catalogue_by_id: Dict[str, Dict[str, Any]] = {}
    if catalogue:
        for entry in catalogue:
            catalogue_by_id[entry["intervention_id"]] = entry

    # Pre-compute shared baseline
    baseline_sim = simulate(G, flood_risk=flood_risk, intervention=None, tau=tau)

    rejected_candidates: List[Dict[str, Any]] = []

    for candidate in ranked_feasible:
        iid = candidate["intervention_id"]
        # Merge catalogue entry (for mitigation_m, target_node) with candidate
        full_action = {**catalogue_by_id.get(iid, {}), **candidate}

        passed, blockers = verify_candidate(
            action=full_action,
            zone_budget=zone_budget,
            G=G,
            flood_risk=flood_risk,
            baseline_sim=baseline_sim,
            tau=tau,
        )

        if not passed:
            rejected_candidates.append({"intervention_id": iid, "blockers": blockers})
            continue

        # ---- This candidate passes — build the Decision Card ----
        what_if = run_what_if(
            G=G,
            flood_risk=flood_risk,
            intervention=full_action,
            tau=tau,
        )

        baseline_risk = float(baseline_sim.get("cascade_risk", 0.0))
        post_risk = float(what_if["after"]["impact_index"])
        modelled_relative_change = round(
            (post_risk - baseline_risk) / baseline_risk if baseline_risk > 0 else 0.0,
            4,
        )

        # Cascade chain narrative for reason field
        cascade_chain = (cascade_result or {}).get("cascade_chain", [])
        chain_str = " → ".join(cascade_chain) if cascade_chain else "N/A"

        # Build reason text
        crit_label = ""
        if critical_node:
            crit_label = critical_node.get("node_id", "")
        nugen_reason = ""
        if nugen_result:
            nugen_reason = nugen_result.get("reason", "")

        reason_parts = [
            f"Zone {zone_id} — Severity: {zone_severity}.",
            f"Cascade chain: {chain_str}.",
            (f"Critical node: {crit_label}." if crit_label else ""),
            f"Top-ranked feasible action by InterventionScore.",
            (f"AI note: {nugen_reason}" if nugen_reason else ""),
        ]
        reason = " ".join(p for p in reason_parts if p)

        # Nugen agreement
        nugen_action_id = (nugen_result or {}).get("recommended_action")
        nugen_agreement_flag = (
            nugen_action_id == iid if nugen_action_id else None
        )

        quality_flags = [DATA_LABEL, "AI_STATUS:MOCK", "REQUIRES_HUMAN_REVIEW"]

        return {
            "status": "FEASIBLE",
            "priority": zone_severity,
            "zone_id": zone_id,
            "target_node": full_action.get("target_node"),
            "action": full_action.get("action", ""),
            "intervention_id": iid,
            "required_resources": full_action.get("required_resources", {}),
            "reason": reason,
            "expected_impact": {
                "before": what_if["before"],
                "after": what_if["after"],
                "reductions": what_if["reductions"],
            },
            "modelled_relative_change": modelled_relative_change,
            "quality_flags": quality_flags,
            "ai_status": "MOCK",
            "nugen_recommendation": nugen_action_id,
            "nugen_agreement": nugen_agreement_flag,
            "human_review_warning": _HUMAN_REVIEW_WARNING,
            "run_id": run_id,
            "blockers": [],
            "rejected_candidates": rejected_candidates,
        }

    # ---- All candidates failed — NO_FEASIBLE_INTERVENTION card ----
    return {
        "status": "NO_FEASIBLE_INTERVENTION",
        "priority": zone_severity,
        "zone_id": zone_id,
        "target_node": None,
        "action": None,
        "intervention_id": None,
        "required_resources": {},
        "reason": (
            "No feasible intervention passed final verification. "
            "Either resources are insufficient, target nodes are absent, or "
            "no intervention offers a positive modelled risk reduction."
        ),
        "expected_impact": None,
        "modelled_relative_change": None,
        "quality_flags": [DATA_LABEL, "AI_STATUS:MOCK", "REQUIRES_HUMAN_REVIEW"],
        "ai_status": "MOCK",
        "nugen_recommendation": (nugen_result or {}).get("recommended_action"),
        "nugen_agreement": None,
        "human_review_warning": _HUMAN_REVIEW_WARNING,
        "run_id": run_id,
        "blockers": [
            b
            for rc in rejected_candidates
            for b in rc.get("blockers", [])
        ],
        "rejected_candidates": rejected_candidates,
    }
