from datetime import datetime
from typing import Any
from sqlalchemy import DateTime, Integer, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import get_settings

settings = get_settings()

# Define schema-scoped metadata for complete database isolation
metadata = MetaData(schema=settings.DB_SCHEMA)


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models scoped to settings.DB_SCHEMA."""
    metadata = metadata


class TimestampMixin:
    """Mixin adding standard auto-populating timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class IntegerIdMixin:
    """Mixin adding standard integer primary key."""
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

