"""ORM models for Placement Readiness Prediction & Historical Analytics."""
import enum
from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import get_settings
from app.core.base import Base, IntegerIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.student import StudentProfile

settings = get_settings()


class ReadinessCategory(str, enum.Enum):
    EXCELLENT_PREPARATION = "excellent_preparation"
    PLACEMENT_READY = "placement_ready"
    NEEDS_IMPROVEMENT = "needs_improvement"
    REQUIRES_SIGNIFICANT_PREPARATION = "requires_significant_preparation"


class ReadinessSnapshot(Base, IntegerIdMixin, TimestampMixin):
    """
    Versioned historical snapshot of a student's preparation readiness index.
    Strictly advisory: kept separate from deterministic academic eligibility and never used to rank or auto-reject candidates.
    """

    __tablename__ = "readiness_snapshots"
    __table_args__ = (
        CheckConstraint("overall_score >= 0 AND overall_score <= 100", name="chk_readiness_overall_score_range"),
    )

    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional target job context when snapshot was computed for a specific role",
    )
    target_role: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )
    formula_version: Mapped[str] = mapped_column(
        String(32),
        default="v1.0",
        nullable=False,
        index=True,
    )
    overall_score: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    category: Mapped[ReadinessCategory] = mapped_column(
        SQLAlchemyEnum(
            ReadinessCategory,
            name="readiness_category_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        nullable=False,
        index=True,
    )
    weights_json: Mapped[Any] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=False,
    )
    indicators_json: Mapped[Any] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=False,
        doc="List of 8 transparent indicator score breakdowns with evidence counts and missing-data flags",
    )
    academic_summary_json: Mapped[Any] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=False,
        doc="Read-only verified academic metrics snapshot kept separate from preparation readiness score",
    )
    missing_data_fields_json: Mapped[Any] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    limitations_json: Mapped[Any] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    remaining_skill_gaps_json: Mapped[Any] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    recommendations_json: Mapped[Any] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    ai_provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    ai_model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    transparency_notice: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    student_profile: Mapped["StudentProfile"] = relationship(
        "StudentProfile",
        back_populates="readiness_snapshots",
    )
    job: Mapped[Optional["Job"]] = relationship("Job")

