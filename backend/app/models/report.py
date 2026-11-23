import enum
from typing import Any, Dict, Optional, TYPE_CHECKING
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import get_settings
from app.core.base import Base, IntegerIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.organization import Institution
    from app.models.user import User

settings = get_settings()


class ReportType(str, enum.Enum):
    """Categorization of automated institutional placement reports."""
    OVERALL_INSTITUTIONAL = "overall_institutional"
    ACADEMIC_YEAR_WISE = "academic_year_wise"
    DEPARTMENT_WISE = "department_wise"
    GRADUATION_BATCH = "graduation_batch"
    COMPANY_WISE = "company_wise"
    PLACEMENT_DRIVE = "placement_drive"
    STUDENT_PLACEMENT_STATUS = "student_placement_status"
    SALARY_PACKAGE_ANALYSIS = "salary_package_analysis"
    UNPLACED_STUDENTS = "unplaced_students"
    OFFER_ACCEPTANCE = "offer_acceptance"


class ReportFormat(str, enum.Enum):
    """Output document format for generated placement reports."""
    PDF = "pdf"
    XLSX = "xlsx"
    CSV = "csv"
    JSON = "json"


class ReportStatus(str, enum.Enum):
    """Lifecycle state of an asynchronous or synchronous report generation task."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PlacementReport(Base, IntegerIdMixin, TimestampMixin):
    """Historical archive of generated placement reports with metadata and file references."""
    __tablename__ = "placement_reports"

    institution_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    generated_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    report_type: Mapped[ReportType] = mapped_column(
        SQLAlchemyEnum(
            ReportType,
            name="placement_report_type_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    parameters: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    file_format: Mapped[ReportFormat] = mapped_column(
        SQLAlchemyEnum(
            ReportFormat,
            name="placement_report_format_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        nullable=False,
        default=ReportFormat.PDF,
    )
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    status: Mapped[ReportStatus] = mapped_column(
        SQLAlchemyEnum(
            ReportStatus,
            name="placement_report_status_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        nullable=False,
        default=ReportStatus.COMPLETED,
        index=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    summary_snapshot: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Relationships
    institution: Mapped["Institution"] = relationship(
        "Institution",
        foreign_keys=[institution_id],
    )
    generated_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[generated_by_user_id],
    )

