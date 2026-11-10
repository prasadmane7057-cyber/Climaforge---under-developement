"""Tests for M16A.2 database models, SQLAlchemy infrastructure, and Alembic migrations."""

from datetime import datetime, timedelta, timezone
import io
import os
from pathlib import Path
import tempfile
import uuid

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import (
    SessionLocal,
    create_db_engine,
    get_db,
    get_session_factory,
    reset_default_engine,
)
from app.models.token import RefreshToken
from app.models.user import User


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Fixture providing a temporary SQLite database file path."""
    db_file = tmp_path / f"test_{uuid.uuid4().hex}.db"
    return db_file


@pytest.fixture
def temp_db_url(temp_db_path: Path) -> str:
    """Fixture providing a temporary SQLite connection URL."""
    return f"sqlite:///{temp_db_path.as_posix()}"


@pytest.fixture
def alembic_config(temp_db_url: str) -> Config:
    """Fixture configuring Alembic to point to the temporary test database."""
    backend_dir = Path(__file__).resolve().parent.parent
    ini_path = backend_dir / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", temp_db_url)
    return cfg


def test_models_representation_and_defaults():
    """Verify string representations and initial default fields of ORM models."""
    user = User(
        email="operator@climaforge.test",
        hashed_password="hashed_pw_argon2",
        full_name="Emergency Operator",
    )
    assert user.role == "operator"
    assert user.is_active is True
    assert user.is_superuser is False
    assert "<User" in repr(user)
    assert "operator@climaforge.test" in repr(user)

    token = RefreshToken(
        user_id=user.id,
        token_hash="sample_token_hash_value",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    assert token.revoked is False
    assert "<RefreshToken" in repr(token)
    assert "sample_token_hash_value" not in repr(token)  # Sensitive hash should not leak in repr


def test_sqlite_engine_enforces_foreign_keys(temp_db_url: str):
    """Verify that SQLite engine automatically configures PRAGMA foreign_keys=ON."""
    engine = create_db_engine(temp_db_url)
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys;")).scalar()
        assert result == 1
    engine.dispose()


def test_user_and_token_crud_and_relationships(temp_db_url: str):
    """Verify full CRUD lifecycle and bidirectional relationship navigation."""
    engine = create_db_engine(temp_db_url)
    Base.metadata.create_all(bind=engine)
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        user = User(
            email="dispatch@climaforge.test",
            hashed_password="secure_argon2_hash",
            full_name="Regional Dispatcher",
            role="dispatcher",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        user_id = user.id
        assert user_id is not None
        assert user.created_at is not None
        assert user.updated_at is not None

        # Add refresh token
        token = RefreshToken(
            user_id=user_id,
            token_hash="hash_token_12345",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        session.add(token)
        session.commit()

    # Query back in a clean session
    with session_factory() as session:
        queried_user = session.execute(
            select(User).where(User.email == "dispatch@climaforge.test")
        ).scalar_one()

        assert queried_user.id == user_id
        assert queried_user.full_name == "Regional Dispatcher"
        assert len(queried_user.refresh_tokens) == 1
        assert queried_user.refresh_tokens[0].token_hash == "hash_token_12345"
        assert queried_user.refresh_tokens[0].user.email == "dispatch@climaforge.test"

    engine.dispose()


def test_user_unique_email_constraint(temp_db_url: str):
    """Verify that attempting to create two users with identical emails fails with IntegrityError."""
    engine = create_db_engine(temp_db_url)
    Base.metadata.create_all(bind=engine)
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        user1 = User(
            email="duplicate@climaforge.test",
            hashed_password="hash1",
        )
        session.add(user1)
        session.commit()

        user2 = User(
            email="duplicate@climaforge.test",
            hashed_password="hash2",
        )
        session.add(user2)
        with pytest.raises(IntegrityError):
            session.commit()

    engine.dispose()


def test_token_unique_hash_constraint(temp_db_url: str):
    """Verify that attempting to store two refresh tokens with identical hashes raises IntegrityError."""
    engine = create_db_engine(temp_db_url)
    Base.metadata.create_all(bind=engine)
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        user = User(
            email="token_owner@climaforge.test",
            hashed_password="hash",
        )
        session.add(user)
        session.commit()

        token1 = RefreshToken(
            user_id=user.id,
            token_hash="shared_hash_collision",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        token2 = RefreshToken(
            user_id=user.id,
            token_hash="shared_hash_collision",
            expires_at=datetime.now(timezone.utc) + timedelta(days=2),
        )
        session.add(token1)
        session.commit()

        session.add(token2)
        with pytest.raises(IntegrityError):
            session.commit()

    engine.dispose()


def test_cascade_delete_user_removes_tokens(temp_db_url: str):
    """Verify that deleting a User cascades to their associated RefreshToken records."""
    engine = create_db_engine(temp_db_url)
    Base.metadata.create_all(bind=engine)
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        user = User(
            email="delete_target@climaforge.test",
            hashed_password="hash",
        )
        session.add(user)
        session.commit()

        token = RefreshToken(
            user_id=user.id,
            token_hash="token_to_cascade",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        session.add(token)
        session.commit()
        token_id = token.id

    with session_factory() as session:
        user_to_delete = session.get(User, user.id)
        assert user_to_delete is not None
        session.delete(user_to_delete)
        session.commit()

    with session_factory() as session:
        remaining_token = session.get(RefreshToken, token_id)
        assert remaining_token is None

    engine.dispose()


def test_get_db_generator_lifecycle(monkeypatch, temp_db_url: str):
    """Verify FastAPI get_db dependency yields an active session and closes it upon exit."""
    engine = create_db_engine(temp_db_url)
    session_factory = get_session_factory(engine)

    # Patch SessionLocal to use the test session factory
    monkeypatch.setattr("app.db.session.SessionLocal", session_factory)

    generator = get_db()
    session = next(generator)
    assert isinstance(session, Session)
    assert session.is_active

    closed = False
    original_close = session.close

    def tracking_close():
        nonlocal closed
        closed = True
        original_close()

    session.close = tracking_close

    # Closing generator closes the session
    with pytest.raises(StopIteration):
        next(generator)

    # Verify session.close() was executed
    assert closed is True
    engine.dispose()


def test_alembic_migrations_full_lifecycle_on_temporary_database(alembic_config: Config, temp_db_url: str):
    """Verify Alembic migration upgrade to head, schema verification, downgrade to base, and re-upgrade."""
    engine = create_db_engine(temp_db_url)

    # 1. Initially, no tables exist
    inspector = inspect(engine)
    assert "users" not in inspector.get_table_names()
    assert "refresh_tokens" not in inspector.get_table_names()

    # 2. Run migration upgrade to head
    command.upgrade(alembic_config, "head")

    # 3. Verify tables and columns created by migration
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "alembic_version" in tables
    assert "users" in tables
    assert "refresh_tokens" in tables
    assert "auth_roles" in tables
    assert "auth_permissions" in tables
    assert "auth_role_permissions" in tables
    assert "auth_user_roles" in tables
    assert "scenario_access_grants" in tables

    user_cols = {col["name"] for col in inspector.get_columns("users")}
    expected_user_cols = {
        "id", "email", "hashed_password", "full_name",
        "role", "is_active", "is_superuser", "created_at", "updated_at",
    }
    assert expected_user_cols.issubset(user_cols)

    token_cols = {col["name"] for col in inspector.get_columns("refresh_tokens")}
    expected_token_cols = {
        "id", "user_id", "family_id", "token_hash", "expires_at",
        "created_at", "revoked", "revoked_at",
    }
    assert expected_token_cols.issubset(token_cols)

    # Verify seed roles and permissions
    with engine.connect() as conn:
        role_count = conn.execute(text("SELECT count(*) FROM auth_roles")).scalar()
        assert role_count == 5
        perm_count = conn.execute(text("SELECT count(*) FROM auth_permissions")).scalar()
        assert perm_count == 15

    # 4. Verify data can be inserted into the migrated database
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, role, is_active, is_superuser) "
                "VALUES ('u-1', 'migrated@climaforge.test', 'migrated_pw', 'operator', 1, 0)"
            )
        )
        count = conn.execute(text("SELECT count(*) FROM users")).scalar()
        assert count == 1

    # 5. Run downgrade to base
    command.downgrade(alembic_config, "base")

    # 6. Verify tables dropped
    inspector = inspect(engine)
    tables_after_downgrade = inspector.get_table_names()
    assert "users" not in tables_after_downgrade
    assert "refresh_tokens" not in tables_after_downgrade
    assert "auth_roles" not in tables_after_downgrade
    assert "auth_permissions" not in tables_after_downgrade
    assert "auth_role_permissions" not in tables_after_downgrade
    assert "auth_user_roles" not in tables_after_downgrade
    assert "scenario_access_grants" not in tables_after_downgrade

    # 7. Re-run upgrade to head (ensures clean idempotent re-application)
    command.upgrade(alembic_config, "head")
    inspector = inspect(engine)
    tables_reapplied = inspector.get_table_names()
    assert "users" in tables_reapplied
    assert "refresh_tokens" in tables_reapplied
    assert "auth_roles" in tables_reapplied
    assert "auth_permissions" in tables_reapplied
    assert "auth_role_permissions" in tables_reapplied
    assert "auth_user_roles" in tables_reapplied
    assert "scenario_access_grants" in tables_reapplied

    engine.dispose()
