"""Sensible validation tests for CLIMAFORGE domain schemas and synthetic data."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from app.schemas.contracts import (
    ZoneInput,
    GraphNode,
    Intervention,
    DecisionCard,
    IncidentRecord,
    UrgencyLevel,
    IncidentStatus,
    AdvisoryStatus,
)
from app.schemas.synthetic_data import (
    SYNTHETIC_ZONES,
    SYNTHETIC_NODES,
    SYNTHETIC_INTERVENTIONS,
    SYNTHETIC_RESOURCES,
)


class TestZoneInputValidation:
    """Validation test suite for ZoneInput contract."""

    def test_valid_zone_input(self):
        zone = ZoneInput(
            zone_id="ZONE-01",
            name="North Marsh",
            area_sq_km=12.5,
            population=15000,
            elevation_m=5.0,
            rainfall_mm=80.0,
            drainage_capacity_cms=30.0,
            soil_saturation_index=0.75,
            critical_infrastructure_count=2,
        )
        assert zone.zone_id == "ZONE-01"
        assert zone.soil_saturation_index == 0.75

    def test_soil_saturation_bounds(self):
        # Must be between 0.0 and 1.0
        with pytest.raises(ValidationError):
            ZoneInput(
                zone_id="ZONE-ERR",
                name="Invalid Soil Zone",
                area_sq_km=10.0,
                population=5000,
                elevation_m=2.0,
                rainfall_mm=50.0,
                drainage_capacity_cms=20.0,
                soil_saturation_index=1.5,  # Exceeds max 1.0
            )

        with pytest.raises(ValidationError):
            ZoneInput(
                zone_id="ZONE-ERR",
                name="Invalid Soil Zone Negative",
                area_sq_km=10.0,
                population=5000,
                elevation_m=2.0,
                rainfall_mm=50.0,
                drainage_capacity_cms=20.0,
                soil_saturation_index=-0.1,  # Below min 0.0
            )

    def test_negative_population_rejected(self):
        with pytest.raises(ValidationError):
            ZoneInput(
                zone_id="ZONE-NEG-POP",
                name="Negative Pop Zone",
                area_sq_km=5.0,
                population=-100,  # Invalid
                elevation_m=10.0,
                rainfall_mm=10.0,
                drainage_capacity_cms=10.0,
                soil_saturation_index=0.5,
            )


class TestGraphNodeValidation:
    """Validation test suite for GraphNode contract."""

    def test_valid_graph_node(self):
        node = GraphNode(
            node_id="NODE-HOSP-01",
            zone_id="ZONE-01",
            name="General Hospital",
            node_type="hospital",
            baseline_capacity=500.0,
            current_operational_ratio=1.0,
            flood_threshold_m=1.5,
            criticality_weight=0.95,
        )
        assert node.node_id == "NODE-HOSP-01"
        assert node.current_operational_ratio == 1.0

    def test_criticality_weight_bounds(self):
        with pytest.raises(ValidationError):
            GraphNode(
                node_id="NODE-INV-WT",
                zone_id="ZONE-01",
                name="Invalid Node",
                node_type="substation",
                baseline_capacity=100.0,
                flood_threshold_m=1.0,
                criticality_weight=1.5,  # Exceeds 1.0
            )

    def test_operational_ratio_bounds(self):
        with pytest.raises(ValidationError):
            GraphNode(
                node_id="NODE-INV-RATIO",
                zone_id="ZONE-01",
                name="Invalid Node",
                node_type="substation",
                baseline_capacity=100.0,
                flood_threshold_m=1.0,
                criticality_weight=0.5,
                current_operational_ratio=-0.1,  # Below 0.0
            )


class TestInterventionValidation:
    """Validation test suite for Intervention contract."""

    def test_valid_intervention(self):
        intv = Intervention(
            intervention_id="INTV-01",
            name="Deploy Sandbag Berms",
            target_zone_id="ZONE-01",
            intervention_type="deploy_barriers",
            required_resources={"sandbags": 1000, "crews": 2},
            cost_estimate_usd=5000.0,
            lead_time_minutes=60,
            risk_reduction_factor=0.6,
        )
        assert intv.intervention_id == "INTV-01"
        assert intv.required_resources["sandbags"] == 1000

    def test_negative_resource_demand_rejected(self):
        with pytest.raises(ValidationError):
            Intervention(
                intervention_id="INTV-NEG-RES",
                name="Invalid Resource Demand",
                target_zone_id="ZONE-01",
                intervention_type="deploy_barriers",
                required_resources={"sandbags": -50},  # Negative quantity rejected
                cost_estimate_usd=1000.0,
                lead_time_minutes=30,
                risk_reduction_factor=0.5,
            )

    def test_risk_reduction_factor_bounds(self):
        with pytest.raises(ValidationError):
            Intervention(
                intervention_id="INTV-HIGH-FACTOR",
                name="Overstated Factor",
                target_zone_id="ZONE-01",
                intervention_type="deploy_barriers",
                cost_estimate_usd=1000.0,
                lead_time_minutes=30,
                risk_reduction_factor=1.2,  # Exceeds 1.0
            )


class TestDecisionCardValidation:
    """Validation test suite for DecisionCard contract."""

    def test_valid_decision_card(self):
        card = DecisionCard(
            card_id="DC-20261028-001",
            scenario_id="SCENARIO-A",
            headline="Execute Flood Barrier Deployment in Zone 1",
            primary_action_ids=["INTV-01"],
            total_estimated_cost_usd=12500.0,
            projected_impact="Reduces cascade failure probability by 65%",
            nugen_advisory_status=AdvisoryStatus.FALLBACK,
            nugen_rationale="Deterministic fallback active: Nugen mock mode",
            sign_off_status="PENDING_REVIEW",
        )
        assert card.card_id == "DC-20261028-001"
        assert card.nugen_advisory_status == AdvisoryStatus.FALLBACK

    def test_negative_cost_rejected(self):
        with pytest.raises(ValidationError):
            DecisionCard(
                card_id="DC-NEG-COST",
                scenario_id="SCENARIO-A",
                headline="Negative Cost",
                primary_action_ids=["INTV-01"],
                total_estimated_cost_usd=-500.0,
                projected_impact="Impact",
            )


class TestIncidentRecordValidation:
    """Validation test suite for IncidentRecord contract."""

    def test_valid_incident_record(self):
        incident = IncidentRecord(
            incident_id="INC-001",
            zone_id="ZONE-01",
            latitude=28.6139,
            longitude=77.2090,
            incident_type="RISING_WATER",
            urgency=UrgencyLevel.HIGH,
            status=IncidentStatus.NOT_SENT,
            description="Water depth reached 45cm near central market entrance.",
        )
        assert incident.status == IncidentStatus.NOT_SENT
        assert incident.urgency == UrgencyLevel.HIGH

    def test_invalid_coordinates_rejected(self):
        with pytest.raises(ValidationError):
            IncidentRecord(
                incident_id="INC-BAD-COORDS",
                zone_id="ZONE-01",
                latitude=95.0,  # Latitude > 90
                longitude=77.2090,
                incident_type="RISING_WATER",
                description="Invalid latitude",
            )


class TestSyntheticDataIntegrity:
    """Ensure all synthetic baseline objects pass schema validation."""

    def test_synthetic_zones_valid(self):
        assert len(SYNTHETIC_ZONES) >= 3
        for zone in SYNTHETIC_ZONES:
            assert isinstance(zone, ZoneInput)
            assert zone.soil_saturation_index <= 1.0

    def test_synthetic_nodes_valid(self):
        assert len(SYNTHETIC_NODES) >= 4
        for node in SYNTHETIC_NODES:
            assert isinstance(node, GraphNode)
            assert 0.0 <= node.criticality_weight <= 1.0

    def test_synthetic_interventions_valid(self):
        assert len(SYNTHETIC_INTERVENTIONS) >= 2
        for intv in SYNTHETIC_INTERVENTIONS:
            assert isinstance(intv, Intervention)
            assert intv.cost_estimate_usd >= 0.0

    def test_synthetic_resources_valid(self):
        assert len(SYNTHETIC_RESOURCES) >= 2
        for res in SYNTHETIC_RESOURCES:
            assert res.total_quantity >= res.allocated_quantity
