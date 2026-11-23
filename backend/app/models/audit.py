"""Database models for TASK 11: Centralized Audit Logging & Activity Monitoring.

Provides tamper-evident, append-only audit trail for authentication,
academic governance, recruitment, resume lifecycle, and system administration.
"""
from datetime import datetime, timezone
import enum
from typing import Any, Dict, Optional, TYPE_CHECKING
from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import get_settings
from app.core.base import Base

if TYPE_CHECKING:
    from app.models.organization import Institution
    from app.models.user import User

settings = get_settings()


class AuditCategory(str, enum.Enum):
    """High-level audit classification domains."""
    AUTHENTICATION = "AUTHENTICATION"
    ACADEMIC = "ACADEMIC"
    RECRUITMENT = "RECRUITMENT"
    RESUME = "RESUME"
    ADMINISTRATION = "ADMINISTRATION"


class AuditStatus(str, enum.Enum):
    """Execution status result of the audited operation."""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    WARNING = "WARNING"


class AuditLog(Base):
    """Centralized, append-only, tamper-evident audit record."""
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": settings.DB_SCHEMA}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    
    # User Context (nullable to support unauthenticated attempts like failed logins)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey(f"{settings.DB_SCHEMA}.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    user_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    user_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Institution / Tenancy Context
    institution_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey(f"{settings.DB_SCHEMA}.institutions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Categorization and Action
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SUCCESS", index=True)
    
    # Request Tracing & Correlation
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    
    # Structured Audit Payloads & Diffs (Strictly Sanitized)
    previous_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    updated_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True)
    
    # Cryptographic Hash Chaining for Tamper Evidence
    prev_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Audit Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id], lazy="selectin")
    institution: Mapped[Optional["Institution"]] = relationship(
        "Institution",
        foreign_keys=[institution_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, event_id='{self.event_id}', category='{self.category}', "
            f"action='{self.action}', entity='{self.entity_type}:{self.entity_id}', status='{self.status}')>"
        )

