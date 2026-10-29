"""CLIMAFORGE Deterministic Calculation Engine (Algorithms 0–13)."""

from app.engine.constants import (
    CASCADE_THRESHOLD_TAU,
    DATA_LABEL,
    DEFAULT_EMERGENCY_IMPORTANCE,
    DEFAULT_RESOURCE_INVENTORY,
    HOTSPOT_THRESHOLD,
    INTERVENTION_CATALOGUE,
    PRIORITY_EPSILON,
    REF_RANGES,
    SEVERITY_BANDS,
    SPEC_VERSION,
    TOP_K_ALTERNATIVES,
    WEIGHTS_ALG1,
    WEIGHTS_ALG3,
    WEIGHTS_ALG6,
    WEIGHTS_ALG10,
)
from app.engine.alg0_data_prep import clamp, normalize, prepare_all_zones, prepare_zone_data
from app.engine.alg1_flood_risk import compute_all_flood_risks, compute_flood_risk
from app.engine.alg2_hotspots import detect_hotspots
from app.engine.alg3_exposure import compute_hotspot_exposures, compute_zone_exposure
from app.engine.alg4_graph import (
    build_consequence_graph,
    build_illustrative_chain_graph,
    build_zone_a_graph,
    dict_to_graph,
    graph_to_dict,
)
from app.engine.alg5_cascade import break_cycles_deterministic, cascade, simulate
from app.engine.alg6_critical_nodes import identify_critical_nodes
from app.engine.alg7_break_points import evaluate_break_points
from app.engine.alg8_resources import allocate_resources, compute_zone_priority_score
from app.engine.alg10_ranking import (
    check_feasibility,
    compute_intervention_score,
    rank_interventions,
)
from app.engine.alg11_what_if import compute_measures, run_what_if
from app.engine.alg12_comparison import compare_alternatives
from app.engine.alg13_decision import generate_decision_card, verify_candidate
from app.engine.pipeline import execute_risk_engine

__all__ = [
    # Constants
    "CASCADE_THRESHOLD_TAU",
    "DATA_LABEL",
    "DEFAULT_EMERGENCY_IMPORTANCE",
    "DEFAULT_RESOURCE_INVENTORY",
    "PRIORITY_EPSILON",
    "SPEC_VERSION",
    "REF_RANGES",
    "WEIGHTS_ALG1",
    "WEIGHTS_ALG3",
    "WEIGHTS_ALG6",
    "WEIGHTS_ALG10",
    "SEVERITY_BANDS",
    "HOTSPOT_THRESHOLD",
    "INTERVENTION_CATALOGUE",
    "TOP_K_ALTERNATIVES",
    # Alg 0
    "clamp",
    "normalize",
    "prepare_zone_data",
    "prepare_all_zones",
    # Alg 1
    "compute_flood_risk",
    "compute_all_flood_risks",
    # Alg 2
    "detect_hotspots",
    # Alg 3
    "compute_zone_exposure",
    "compute_hotspot_exposures",
    # Alg 4
    "build_consequence_graph",
    "build_zone_a_graph",
    "build_illustrative_chain_graph",
    "graph_to_dict",
    "dict_to_graph",
    # Alg 5
    "break_cycles_deterministic",
    "cascade",
    "simulate",
    # Alg 6
    "identify_critical_nodes",
    # Alg 7
    "evaluate_break_points",
    # Alg 8
    "allocate_resources",
    "compute_zone_priority_score",
    # Alg 10
    "check_feasibility",
    "compute_intervention_score",
    "rank_interventions",
    # Alg 11
    "compute_measures",
    "run_what_if",
    # Alg 12
    "compare_alternatives",
    # Alg 13
    "generate_decision_card",
    "verify_candidate",
    # Pipeline
    "execute_risk_engine",
]

