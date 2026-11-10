"""Database models for Role-Based Access Control (RBAC) and Scenario Access Grants."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Role(Base):
    """Server-controlled RBAC role entity."""

    __tablename__ = "auth_roles"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
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

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary="auth_role_permissions",
        back_populates="roles",
        overlaps="role_permissions",
    )
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="role",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="auth_user_roles",
        back_populates="roles",
        viewonly=True,
        overlaps="user_roles",
    )

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Role id={self.id!r} name={self.name!r}>"


class Permission(Base):
    """Granular action permission entity."""

    __tablename__ = "auth_permissions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="auth_role_permissions",
        back_populates="permissions",
        viewonly=True,
        overlaps="role_permissions,permissions",
    )

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Permission id={self.id!r} name={self.name!r}>"


class RolePermission(Base):
    """Many-to-many association mapping roles to permissions."""

    __tablename__ = "auth_role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_auth_role_permissions_role_perm"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    role_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("auth_roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    permission_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("auth_permissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    role: Mapped["Role"] = relationship("Role", back_populates="role_permissions", overlaps="permissions,roles")
    permission: Mapped["Permission"] = relationship("Permission", back_populates="role_permissions", overlaps="permissions,roles")

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<RolePermission role_id={self.role_id!r} permission_id={self.permission_id!r}>"


class UserRole(Base):
    """Many-to-many association mapping users to server-controlled roles."""

    __tablename__ = "auth_user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_auth_user_roles_user_role"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("auth_roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="user_roles", overlaps="roles,users")
    role: Mapped["Role"] = relationship("Role", back_populates="user_roles", overlaps="roles,users")

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<UserRole user_id={self.user_id!r} role_id={self.role_id!r}>"


class ScenarioAccessGrant(Base):
    """Scenario-scoped access grant providing explicit or temporal scenario permissions."""

    __tablename__ = "scenario_access_grants"
    __table_args__ = (
        UniqueConstraint("user_id", "scenario_id", "permission", name="uq_scenario_grants_user_scenario_perm"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    permission: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    granted_by: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="scenario_grants",
    )
    granter: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[granted_by],
    )

    def __init__(self, **kwargs: object) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        super().__init__(**kwargs)

    def is_expired(self, at_time: datetime | None = None) -> bool:
        """Check whether this grant has expired."""
        if self.expires_at is None:
            return False
        now = at_time or datetime.now(timezone.utc)
        expires = self.expires_at if self.expires_at.tzinfo is not None else self.expires_at.replace(tzinfo=timezone.utc)
        return expires <= now

    def __repr__(self) -> str:
        return f"<ScenarioAccessGrant user_id={self.user_id!r} scenario_id={self.scenario_id!r} perm={self.permission!r}>"
