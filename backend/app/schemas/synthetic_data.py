"""Synthetic and illustrative demo data for CLIMAFORGE Milestone 0.

=============================================================================
LABEL: SYNTHETIC / ILLUSTRATIVE DATA ONLY
NOT FOR REAL-WORLD EVACUATION, EMERGENCY DISPATCH, OR FLOOD PREDICTION.
=============================================================================
"""

from typing import Dict, List
from .contracts import (
    ZoneInput,
    GraphNode,
    Intervention,
    ResourceInventory,
)

DATA_DISCLAIMER: str = (
    "SYNTHETIC / ILLUSTRATIVE DATA — For CLIMAFORGE prototype demonstration only. "
    "Do not use for operational flood response or real-world dispatch."
)

# 4 Synthetic Zones
SYNTHETIC_ZONES: List[ZoneInput] = [
    ZoneInput(
        zone_id="ZONE-001",
        name="Riverside Industrial District",
        area_sq_km=14.2,
        population=32000,
        elevation_m=4.5,
        rainfall_mm=135.0,
        drainage_capacity_cms=45.0,
        soil_saturation_index=0.88,
        critical_infrastructure_count=4,
        river_proximity_m=120.0,
    ),
    ZoneInput(
        zone_id="ZONE-002",
        name="Central Ward & Commercial Core",
        area_sq_km=8.6,
        population=78000,
        elevation_m=9.2,
        rainfall_mm=75.0,
        drainage_capacity_cms=65.0,
        soil_saturation_index=0.62,
        critical_infrastructure_count=7,
        river_proximity_m=850.0,
    ),
    ZoneInput(
        zone_id="ZONE-003",
        name="Valley Residential Heights",
        area_sq_km=18.5,
        population=45000,
        elevation_m=18.0,
        rainfall_mm=45.0,
        drainage_capacity_cms=80.0,
        soil_saturation_index=0.35,
        critical_infrastructure_count=2,
        river_proximity_m=2400.0,
    ),
    ZoneInput(
        zone_id="ZONE-004",
        name="Harbor & Estuary Basin",
        area_sq_km=12.0,
        population=21000,
        elevation_m=2.1,
        rainfall_mm=160.0,
        drainage_capacity_cms=30.0,
        soil_saturation_index=0.94,
        critical_infrastructure_count=3,
        river_proximity_m=50.0,
    ),
]

# 5 Synthetic Graph Nodes
SYNTHETIC_NODES: List[GraphNode] = [
    GraphNode(
        node_id="NODE-SUB-01",
        zone_id="ZONE-001",
        name="Substation North Grid 110kV",
        node_type="substation",
        baseline_capacity=110.0,
        current_operational_ratio=1.0,
        flood_threshold_m=1.2,
        criticality_weight=0.92,
        recovery_latency_hours=18.0,
    ),
    GraphNode(
        node_id="NODE-HOSP-01",
        zone_id="ZONE-002",
        name="General Emergency Hospital",
        node_type="hospital",
        baseline_capacity=650.0,
        current_operational_ratio=1.0,
        flood_threshold_m=1.8,
        criticality_weight=0.98,
        recovery_latency_hours=36.0,
    ),
    GraphNode(
        node_id="NODE-WTR-01",
        zone_id="ZONE-001",
        name="Municipal Water Treatment Facility",
        node_type="water_treatment",
        baseline_capacity=250000.0,
        current_operational_ratio=1.0,
        flood_threshold_m=0.9,
        criticality_weight=0.85,
        recovery_latency_hours=24.0,
    ),
    GraphNode(
        node_id="NODE-BRG-01",
        zone_id="ZONE-002",
        name="East River Arterial Bridge",
        node_type="bridge",
        baseline_capacity=4500.0,
        current_operational_ratio=1.0,
        flood_threshold_m=2.5,
        criticality_weight=0.78,
        recovery_latency_hours=72.0,
    ),
    GraphNode(
        node_id="NODE-SHELTER-01",
        zone_id="ZONE-003",
        name="Highland Sports Complex Refuge",
        node_type="shelter",
        baseline_capacity=3000.0,
        current_operational_ratio=1.0,
        flood_threshold_m=5.0,
        criticality_weight=0.65,
        recovery_latency_hours=6.0,
    ),
]

# 3 Synthetic Safe Points / Shelters
SYNTHETIC_SAFE_POINTS: List[Dict[str, str | float]] = [
    {
        "safe_point_id": "SP-01",
        "name": "Highland Sports Arena Shelter",
        "zone_id": "ZONE-003",
        "capacity_persons": 3000,
        "elevation_m": 22.0,
        "label": "SYNTHETIC / ILLUSTRATIVE",
    },
    {
        "safe_point_id": "SP-02",
        "name": "Civic Center Evacuation Hall",
        "zone_id": "ZONE-002",
        "capacity_persons": 1500,
        "elevation_m": 12.5,
        "label": "SYNTHETIC / ILLUSTRATIVE",
    },
    {
        "safe_point_id": "SP-03",
        "name": "Northern Technical Institute High Ground",
        "zone_id": "ZONE-003",
        "capacity_persons": 2200,
        "elevation_m": 26.0,
        "label": "SYNTHETIC / ILLUSTRATIVE",
    },
]

# 3 Synthetic Interventions
SYNTHETIC_INTERVENTIONS: List[Intervention] = [
    Intervention(
        intervention_id="INTV-SANDBAG-01",
        name="Deploy Temporary Inundation Barriers",
        target_zone_id="ZONE-001",
        target_node_id="NODE-SUB-01",
        intervention_type="deploy_barriers",
        required_resources={"sandbags": 1500, "crew_teams": 3},
        cost_estimate_usd=12500.0,
        lead_time_minutes=45,
        risk_reduction_factor=0.65,
    ),
    Intervention(
        intervention_id="INTV-PUMP-01",
        name="Dispatch High-Flow Mobile Pumps",
        target_zone_id="ZONE-001",
        target_node_id="NODE-WTR-01",
        intervention_type="mobile_pumps",
        required_resources={"mobile_pumps": 4, "fuel_liters": 800, "crew_teams": 2},
        cost_estimate_usd=8200.0,
        lead_time_minutes=30,
        risk_reduction_factor=0.55,
    ),
    Intervention(
        intervention_id="INTV-DIVERSION-01",
        name="Traffic Diversion & Causeway Access Control",
        target_zone_id="ZONE-002",
        target_node_id="NODE-BRG-01",
        intervention_type="traffic_diversion",
        required_resources={"traffic_barriers": 40, "police_units": 4},
        cost_estimate_usd=3000.0,
        lead_time_minutes=20,
        risk_reduction_factor=0.40,
    ),
]

# Synthetic Resource Inventory
SYNTHETIC_RESOURCES: List[ResourceInventory] = [
    ResourceInventory(
        resource_id="RES-SANDBAGS",
        name="Quick-Deploy Flood Sandbags",
        total_quantity=5000,
        allocated_quantity=1500,
        depot_zone_id="ZONE-002",
    ),
    ResourceInventory(
        resource_id="RES-PUMPS",
        name="High-Capacity Diesel Mobile Pumps",
        total_quantity=10,
        allocated_quantity=4,
        depot_zone_id="ZONE-002",
    ),
    ResourceInventory(
        resource_id="RES-CREW",
        name="Emergency Response Crew Teams",
        total_quantity=12,
        allocated_quantity=5,
        depot_zone_id="ZONE-003",
    ),
]
