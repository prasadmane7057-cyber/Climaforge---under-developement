"""Canonical parameters and configuration register for CLIMAFORGE Algorithms 0-5.

All values are derived directly from Section 6, Section 9.1, and Section 12
of the CLIMAFORGE Algorithm Design & Implementation Report v2.
"""

from typing import Dict, Tuple

DATA_LABEL: str = "SYNTHETIC / ILLUSTRATIVE DATA ONLY"
SPEC_VERSION: str = "CLIMAFORGE-ALGORITHMS-0-5-v2.0"

# Fixed Reference Ranges (lo, hi) for Normalization
# Formula: clamp((x - lo) / (hi - lo), 0.0, 1.0)
# Never use per-run min-max normalization!
REF_RANGES: Dict[str, Tuple[float, float]] = {
    "rainfall": (0.0, 150.0),        # mm
    "drainage": (0.0, 100.0),        # cms (m³/s)
    "water_level": (0.0, 3.0),       # meters
    "elevation": (0.0, 40.0),        # meters
    "history": (0.0, 5.0),           # flood events per year (or soil saturation proxy)
    "population": (0.0, 25000.0),    # resident count
    "critical_infra": (0.0, 5.0),    # count of hospitals, substations, water plants
    "road_length": (0.0, 10.0),      # km of arterial roads
    "emergency_routes": (0.0, 3.0),  # count of designated emergency access corridors
}

# Required vs Optional fields for Algorithm 0 validation
REQUIRED_FIELDS = ["rainfall", "drainage"]
OPTIONAL_FIELDS = ["water_level", "elevation", "history"]

# Algorithm 1: Flood Risk Factor Weights (w), summing to 1.0
WEIGHTS_ALG1: Dict[str, float] = {
    "R": 0.30,  # Rainfall
    "D": 0.25,  # Inverse Drainage Throughput (1 - norm(drainage))
    "W": 0.20,  # River Water Level Stage
    "E": 0.15,  # Inverse Elevation (1 - norm(elevation), low ground = high risk)
    "H": 0.10,  # Historical Frequency / Soil Saturation
}

# Algorithm 1: Severity Classification Bands
SEVERITY_BANDS = {
    "CRITICAL": 75.0,
    "HIGH": 50.0,
    "MEDIUM": 25.0,
}

# Algorithm 2: Hotspot Qualification Threshold
HOTSPOT_THRESHOLD: float = 50.0

# Algorithm 3: Exposure Component Weights (u), summing to 1.0
WEIGHTS_ALG3: Dict[str, float] = {
    "P": 0.35,   # Population Score
    "I": 0.25,   # Critical Infrastructure Score
    "Rd": 0.20,  # Road Exposure Score
    "Em": 0.20,  # Emergency Route Exposure Score
}

# Algorithm 5: Cascade Propagation Failure Threshold (tau)
CASCADE_THRESHOLD_TAU: float = 0.30

# Algorithm 6: Critical Node Feature Weights (v), summing to 1.0
# Direct, Pop, Infra, Emerg, Downstream, DepCount
WEIGHTS_ALG6: Dict[str, float] = {
    "Direct": 0.15,
    "Pop": 0.20,
    "Infra": 0.15,
    "Emerg": 0.20,
    "Downstream": 0.20,
    "DepCount": 0.10,
}

# Algorithm 8: Resource Priority Floor (epsilon)
PRIORITY_EPSILON: float = 0.01

# Algorithm 8: Baseline Synthetic Resource Inventory (Depot Stock)
# Canonical stock levels from Section 9.1 of Report v2
DEFAULT_RESOURCE_INVENTORY: Dict[str, int] = {
    "pumps": 2,
    "rescue_teams": 1,
    "barricades": 0,
    "vehicles": 0,
}

# Algorithm 8: Default Emergency Importance per zone
# Derived from Section 12 of Report v2
DEFAULT_EMERGENCY_IMPORTANCE: float = 0.80

# Algorithm 10: Intervention Scoring Weights (a), summing to 1.0
# Score = a1*RiskRed + a2*CascRed + a3*PopProt + a4*EmergProt - a5*ResourceCost
WEIGHTS_ALG10: Dict[str, float] = {
    "RiskReduction": 0.30,
    "CascadeReduction": 0.25,
    "PopulationProtection": 0.20,
    "EmergencyProtection": 0.15,
    "ResourceCost": 0.10,
}

# Algorithm 12: Comparison Window Size (top-K alternatives + no-action baseline)
TOP_K_ALTERNATIVES: int = 3


# Intervention Catalogue (Section 5.3 of Report v2)
# Canonical candidate actions evaluated by Algorithm 7 and shared simulate()
INTERVENTION_CATALOGUE = [
    {
        "intervention_id": "I1",
        "action": "Deploy pumps at the drainage outlet",
        "name": "Mobile Pumping Units at Drainage Outlet",
        "target_node": "Drainage",
        "mitigation_m": 0.60,
        "required_resources": {"pumps": 2},
        "cost_usd": 50000.0,
        "lead_time_minutes": 120,
        "description": "High-capacity diesel dewatering pumps installed at primary drainage culverts to relieve hydrostatic head.",
    },
    {
        "intervention_id": "I2",
        "action": "Junction traffic control and alternate emergency route",
        "name": "Traffic Diversion & Staging at Main Junction",
        "target_node": "Main Junction A",
        "mitigation_m": 0.50,
        "required_resources": {"rescue_teams": 1},
        "cost_usd": 35000.0,
        "lead_time_minutes": 60,
        "description": "Active traffic control and emergency route diversion around vulnerable junction chokepoint.",
    },
    {
        "intervention_id": "I3",
        "action": "Pre-position rescue team at emergency-access staging point",
        "name": "Pre-position Emergency Rescue Staging",
        "target_node": "Emergency Access",
        "mitigation_m": 0.50,
        "required_resources": {"rescue_teams": 1},
        "cost_usd": 20000.0,
        "lead_time_minutes": 180,
        "description": "Pre-deployment of amphibious rescue craft and paramedic teams to safeguard hospital access corridors.",
    },
    {
        "intervention_id": "I4",
        "action": "Barricade and divert at the flooded road segment",
        "name": "Flood Barricades & Road Diversion",
        "target_node": "Road",
        "mitigation_m": 0.60,
        "required_resources": {"barricades": 2},
        "cost_usd": 15000.0,
        "lead_time_minutes": 240,
        "description": "Rapid physical floodwall barriers deployed along arterial road segment to isolate overflow channels.",
    },
]

