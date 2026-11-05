"""SQLAlchemy database engine and session infrastructure."""

from collections.abc import Generator
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

_default_engine: Engine | None = None
_default_session_factory: sessionmaker[Session] | None = None


def _enable_sqlite_foreign_keys(dbapi_connection: Any, connection_record: Any) -> None:
    """Ensure SQLite enforces foreign key constraints and cascade actions."""
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()


def create_db_engine(database_url: str | None = None, **kwargs: Any) -> Engine:
    """Create a configured SQLAlchemy engine for SQLite or PostgreSQL."""
    url_str = database_url or settings.database_url or "sqlite:///./climaforge.db"
    parsed_url = make_url(url_str)

    engine_kwargs: dict[str, Any] = {
        "pool_pre_ping": True,
    }

    if parsed_url.drivername.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    engine_kwargs.update(kwargs)
    engine = create_engine(url_str, **engine_kwargs)

    if parsed_url.drivername.startswith("sqlite"):
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)

    return engine


def get_default_engine() -> Engine:
    """Get or initialize the process-wide default database engine."""
    global _default_engine
    if _default_engine is None:
        _default_engine = create_db_engine()
    return _default_engine


def reset_default_engine() -> None:
    """Dispose and reset the cached engine and sessionmaker (useful in testing)."""
    global _default_engine, _default_session_factory
    if _default_engine is not None:
        _default_engine.dispose()
        _default_engine = None
    _default_session_factory = None


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Get a session factory bound to the provided or default engine."""
    global _default_session_factory
    if engine is not None:
        return sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
    if _default_session_factory is None:
        _default_session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_default_engine(),
            expire_on_commit=False,
        )
    return _default_session_factory


class _SessionLocalProxy:
    """Lazy callable proxy for SessionLocal so it always uses the current session factory."""

    def __call__(self, **kwargs: Any) -> Session:
        factory = get_session_factory()
        return factory(**kwargs)


SessionLocal = _SessionLocalProxy()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a transactional database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

