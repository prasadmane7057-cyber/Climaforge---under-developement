"""Pydantic data contracts for Milestone 7: Incident Synchronization and SOS Outbox."""

from datetime import datetime, timezone
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from app.schemas.contracts import IncidentRecord, IncidentStatus, UrgencyLevel


class IncidentSyncItem(BaseModel):
    """Client-submitted emergency SOS incident report."""

    incident_id: str = Field(..., description="Client-generated RFC 4122 UUID string")
    reported_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC time the report was originally logged offline",
    )
    zone_id: str = Field(..., min_length=1, max_length=64, description="Associated catchment zone")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Optional GPS latitude")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Optional GPS longitude")
    incident_type: str = Field(
        ...,
        description="Category: 'RISING_WATER', 'MEDICAL_EMERGENCY', 'STRANDED_PERSONS', 'ROAD_BLOCKED'",
    )
    urgency: UrgencyLevel = Field(default=UrgencyLevel.MEDIUM, description="Urgency level")
    status: IncidentStatus = Field(
        default=IncidentStatus.NOT_SENT,
        description="Sync status. Outbox items start as NOT_SENT until server acknowledgment.",
    )
    description: str = Field(..., min_length=1, max_length=2000, description="Observation or distress details")

    @field_validator("incident_id")
    @classmethod
    def validate_uuid_format(cls, value: str) -> str:
        """Validate that incident_id is a valid UUID format."""
        try:
            UUID(value)
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(f"Invalid incident_id '{value}'. Must be a valid UUID.") from exc
        return value

    @field_validator("incident_type")
    @classmethod
    def validate_incident_type(cls, value: str) -> str:
        """Ensure incident_type belongs to canonical categories."""
        allowed = {"RISING_WATER", "MEDICAL_EMERGENCY", "STRANDED_PERSONS", "ROAD_BLOCKED"}
        normalized = value.strip().upper()
        if normalized not in allowed:
            raise ValueError(f"Invalid incident_type '{value}'. Must be one of: {sorted(allowed)}")
        return normalized


class IncidentSyncRequest(BaseModel):
    """Batch payload for synchronizing client-queued emergency incident reports."""

    incidents: List[IncidentSyncItem] = Field(default_factory=list, description="List of queued incident records")


class IncidentSyncResponse(BaseModel):
    """Server acknowledgment receipt for synchronized emergency incident reports."""

    scenario_id: str
    synced_incident_ids: List[str] = Field(default_factory=list, description="IDs of newly stored incidents")
    duplicate_incident_ids: List[str] = Field(default_factory=list, description="IDs of previously stored incidents")
    rejected_incident_ids: List[str] = Field(default_factory=list, description="IDs rejected due to validation errors")
    total_received: int = Field(..., ge=0)
    total_synced: int = Field(..., ge=0)
    total_duplicates: int = Field(..., ge=0)
    acknowledged_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: Literal["ACKNOWLEDGED", "PARTIAL_SUCCESS", "NO_NEW_DATA"]
    disclaimer: str = Field(
        default="SIMULATED CITIZEN SOS RECEIPT. Prototype outbox synchronization only. In a real life-threatening emergency, call local emergency services immediately.",
    )


class ScenarioIncidentsResponse(BaseModel):
    """List of all durably acknowledged incidents for a scenario."""

    scenario_id: str
    total_count: int
    incidents: List[IncidentRecord]
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

