"""Declarative base and metadata naming conventions for SQLAlchemy ORM models."""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Standard constraint naming conventions for deterministic migrations across SQLite & PostgreSQL
POSTGRES_SQLITE_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_`%(constraint_name)s`",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=POSTGRES_SQLITE_NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Base class for all persistent SQLAlchemy models in CLIMAFORGE."""

    metadata = metadata

