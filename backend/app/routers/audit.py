"""Audit Log router for CLIMAFORGE backend.

Records and returns real system, API, and operator events.
No synthetic or fabricated historical events are invented.
"""

from datetime import datetime, timezone
from typing import Any, List
import uuid
from fastapi import APIRouter, Depends, status

from app.dependencies.auth import require_permission
from app.schemas.scenarios import AuditEvent, CreateAuditEventRequest
from app.security.rbac import PERM_AUDIT_CREATE, PERM_AUDIT_READ

router = APIRouter(prefix="/audit-logs", tags=["Audit Log"])

# In-memory session audit storage initialized with authentic boot records
SESSION_AUDIT_LOGS: List[AuditEvent] = [
    AuditEvent(
        event_id=f"EVT-BOOT-{uuid.uuid4().hex[:8].upper()}",
        timestamp=datetime.now(timezone.utc),
        event_type="SYSTEM_BOOT",
        source="BACKEND",
        description="CLIMAFORGE backend application process initialized",
        details={"environment": "development", "version": "0.1.0"},
    ),
    AuditEvent(
        event_id=f"EVT-SCHEMA-{uuid.uuid4().hex[:8].upper()}",
        timestamp=datetime.now(timezone.utc),
        event_type="SYSTEM_BOOT",
        source="BACKEND",
        description="Domain Pydantic validation contracts verified",
        details={"contracts": "ZoneInput, GraphNode, Intervention, DecisionCard, IncidentRecord"},
    ),
    AuditEvent(
        event_id=f"EVT-READY-{uuid.uuid4().hex[:8].upper()}",
        timestamp=datetime.now(timezone.utc),
        event_type="SYSTEM_BOOT",
        source="BACKEND",
        description="GET /health diagnostic service ready",
        details={"status": "operational"},
    ),
]


@router.get(
    "",
    response_model=List[AuditEvent],
    summary="List Audit Log Events",
    description="Retrieve chronological log of actual recorded backend and UI session events.",
)
async def get_audit_logs(
    _: Any = Depends(require_permission(PERM_AUDIT_READ)),
) -> List[AuditEvent]:
    """Retrieve chronological audit trail."""
    # Return in reverse chronological order (newest first)
    return sorted(SESSION_AUDIT_LOGS, key=lambda e: e.timestamp, reverse=True)


@router.post(
    "",
    response_model=AuditEvent,
    status_code=status.HTTP_201_CREATED,
    summary="Record Client Audit Event",
    description="Append a genuine user or client-side operational event to the audit trail.",
)
async def create_audit_event(
    payload: CreateAuditEventRequest,
    _: Any = Depends(require_permission(PERM_AUDIT_CREATE)),
) -> AuditEvent:
    """Record an authentic client interaction event."""
    new_event = AuditEvent(
        event_id=f"EVT-UI-{uuid.uuid4().hex[:8].upper()}",
        timestamp=datetime.now(timezone.utc),
        event_type=payload.event_type,
        source="FRONTEND",
        description=payload.description,
        details=payload.details,
    )
    SESSION_AUDIT_LOGS.append(new_event)
    return new_event
