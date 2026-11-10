"""User account database model for authentication and access control."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.token import RefreshToken
    from app.models.rbac import Role, UserRole, ScenarioAccessGrant


class User(Base):
    """User account entity storing credentials, role, and operational state."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="operator",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="auth_user_roles",
        back_populates="users",
        viewonly=True,
        overlaps="user_roles",
    )
    scenario_grants: Mapped[list["ScenarioAccessGrant"]] = relationship(
        "ScenarioAccessGrant",
        foreign_keys="ScenarioAccessGrant.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "role" not in kwargs:
            kwargs["role"] = "operator"
        if "is_active" not in kwargs:
            kwargs["is_active"] = True
        if "is_superuser" not in kwargs:
            kwargs["is_superuser"] = False
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<User id={self.id!r} email={self.email!r} role={self.role!r} active={self.is_active}>"
