"""Scenarios API router for CLIMAFORGE backend."""

from typing import List
from fastapi import APIRouter, HTTPException, status

from app.schemas.scenarios import ScenarioDetail, ScenarioSummaryItem
from app.schemas.scenario_data import get_scenario_by_id, list_scenario_summaries

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


@router.get(
    "",
    response_model=List[ScenarioSummaryItem],
    summary="List Scenarios",
    description="List all available synthetic demonstration scenarios for the operations dashboard.",
)
async def get_scenarios() -> List[ScenarioSummaryItem]:
    """Retrieve catalog of demo scenarios."""
    return list_scenario_summaries()


@router.get(
    "/{scenario_id}",
    response_model=ScenarioDetail,
    summary="Get Scenario Detail",
    description="Retrieve comprehensive zone telemetry and risk metrics for a specific scenario.",
)
async def get_scenario(scenario_id: str) -> ScenarioDetail:
    """Retrieve full details of the requested scenario."""
    scenario = get_scenario_by_id(scenario_id)
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_id}' was not found in the demonstrator catalog.",
        )
    return scenario
