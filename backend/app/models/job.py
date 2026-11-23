from datetime import datetime
import enum
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import get_settings
from app.core.base import Base, IntegerIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.organization import Department, Institution
    from app.models.user import User
    from app.models.placement import JobApplication, PlacementDriveJob

settings = get_settings()


class JobStatus(str, enum.Enum):
    """Lifecycle states of a campus hiring opportunity."""
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class EmploymentType(str, enum.Enum):
    """Categorization of employment contract."""
    FULL_TIME = "full_time"
    INTERNSHIP = "internship"
    INTERN_TO_FULL_TIME = "intern_to_full_time"


class WorkMode(str, enum.Enum):
    """Physical work arrangement."""
    ON_SITE = "on_site"
    HYBRID = "hybrid"
    REMOTE = "remote"


class Job(Base, IntegerIdMixin, TimestampMixin):
    """Campus placement job posting with explicit deterministic eligibility criteria."""
    __tablename__ = "jobs"

    company_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    institution_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
        doc="Optional institutional scoping: when specified, this drive is dedicated to the institution",
    )
    created_by_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    employment_type: Mapped[EmploymentType] = mapped_column(
        SQLAlchemyEnum(
            EmploymentType,
            name="job_employment_type_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        nullable=False,
        index=True,
    )
    work_mode: Mapped[WorkMode] = mapped_column(
        SQLAlchemyEnum(
            WorkMode,
            name="job_work_mode_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        nullable=False,
    )
    location: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    salary_range: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Human-friendly compensation range e.g. '12 - 16 LPA', '₹40,000/month'",
    )
    ctc_lpa: Mapped[Optional[float]] = mapped_column(
        Numeric(6, 2),
        nullable=True,
        doc="Annual CTC in Lakhs Per Annum for full-time offers",
    )
    base_salary_lpa: Mapped[Optional[float]] = mapped_column(
        Numeric(6, 2),
        nullable=True,
    )
    stipend_monthly: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 2),
        nullable=True,
        doc="Monthly stipend in INR for internships",
    )
    min_cgpa: Mapped[float] = mapped_column(
        Numeric(4, 2),
        default=0.0,
        nullable=False,
        doc="Minimum cumulative GPA cutoff on 0.0 - 10.0 scale",
    )
    target_graduation_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        doc="Eligible graduating batch e.g. 2026",
    )
    max_active_backlogs: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Maximum permissible currently pending academic backlogs",
    )
    max_total_backlogs: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Maximum permissible historical total backlogs",
    )
    application_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[JobStatus] = mapped_column(
        SQLAlchemyEnum(
            JobStatus,
            name="job_status_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        default=JobStatus.DRAFT,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    # Relationships
    company: Mapped["Company"] = relationship(
        "Company",
        back_populates="jobs",
    )
    institution: Mapped[Optional["Institution"]] = relationship(
        "Institution",
    )
    created_by: Mapped["User"] = relationship(
        "User",
    )
    skills: Mapped[List["JobSkill"]] = relationship(
        "JobSkill",
        back_populates="job",
        cascade="all, delete-orphan",
    )
    eligible_departments: Mapped[List["JobEligibleDepartment"]] = relationship(
        "JobEligibleDepartment",
        back_populates="job",
        cascade="all, delete-orphan",
    )
    applications: Mapped[List["JobApplication"]] = relationship(
        "JobApplication",
        back_populates="job",
    )
    drive_associations: Mapped[List["PlacementDriveJob"]] = relationship(
        "PlacementDriveJob",
        back_populates="job",
    )


class JobSkill(Base, IntegerIdMixin):
    """Normalized technical or soft skill requirement for a job posting."""
    __tablename__ = "job_skills"
    __table_args__ = (
        UniqueConstraint("job_id", "skill_name", name="uq_job_skill_name"),
    )

    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="True for Required Skills; False for Preferred/Bonus Skills",
    )
    weight_factor: Mapped[float] = mapped_column(
        Numeric(3, 2),
        default=1.0,
        nullable=False,
        doc="Relative weight factor (0.1 to 3.0) for Phase 5 scoring engine",
    )

    # Relationships
    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="skills",
    )


class JobEligibleDepartment(Base, IntegerIdMixin):
    """Explicit junction associating jobs to authorized academic branches/departments."""
    __tablename__ = "job_eligible_departments"
    __table_args__ = (
        UniqueConstraint("job_id", "department_id", name="uq_job_department"),
    )

    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    department_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="eligible_departments",
    )
    department: Mapped["Department"] = relationship(
        "Department",
    )

