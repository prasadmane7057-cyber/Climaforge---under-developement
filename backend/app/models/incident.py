"""SQLAlchemy model for emergency incident reports and SOS outbox records."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Incident(Base):
    """Emergency distress report or citizen field incident record.

    Stored durably with a unique primary key constraint on `incident_id` to guarantee
    idempotent synchronization across client offline reconnects.
    """

    __tablename__ = "incidents"

    incident_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        index=True,
        nullable=False,
        doc="Client-generated RFC 4122 UUID",
    )
    scenario_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Associated scenario identifier",
    )
    zone_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Catchment zone identifier",
    )
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Original client timestamp when logged offline",
    )
    latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        doc="Optional GPS latitude",
    )
    longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        doc="Optional GPS longitude",
    )
    incident_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="Category: RISING_WATER, MEDICAL_EMERGENCY, STRANDED_PERSONS, ROAD_BLOCKED",
    )
    urgency: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="MEDIUM",
        doc="Urgency priority level (LOW, MEDIUM, HIGH, CRITICAL)",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACKNOWLEDGED",
        doc="Synchronization status",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Distress observation description",
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="UTC time the server committed the incident record",
    )

