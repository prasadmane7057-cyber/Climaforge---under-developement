"""Alembic environment configuration for CLIMAFORGE database migrations."""

from logging.config import fileConfig
import sys
from typing import Any

from alembic import context
from sqlalchemy import pool

# Ensure backend root is on sys.path
sys.path.insert(0, ".")

from app.config import settings
from app.db.session import create_db_engine
from app.models import Base

# Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for autogenerate support
target_metadata = Base.metadata


def get_database_url() -> str:
    """Resolve database URL from config, settings, or CLI x-arguments."""
    x_args = context.get_x_argument(as_dictionary=True)
    if "db_url" in x_args and x_args["db_url"].strip():
        return x_args["db_url"].strip()

    # If config explicitly set a custom URL (e.g., in tests via set_main_option)
    custom_url = config.get_main_option("sqlalchemy.url")
    if custom_url and custom_url != "sqlite:///./climaforge.db":
        return custom_url

    # Check application configuration
    if settings.database_url and settings.database_url.strip():
        return settings.database_url

    return custom_url or "sqlite:///./climaforge.db"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures context with just a URL and not an Engine.
    Calls to context.execute() emit the SQL string to stdout.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context.
    """
    # Allow tests to inject an active connection directly
    provided_connection = config.attributes.get("connection", None)
    if provided_connection is not None:
        context.configure(
            connection=provided_connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    url = get_database_url()
    connectable = create_db_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
