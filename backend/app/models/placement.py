from datetime import datetime
import enum
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import get_settings
from app.core.base import Base, IntegerIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.candidate_evaluation import CandidateEvaluation, CandidateNote
    from app.models.company import Company
    from app.models.job import Job
    from app.models.organization import Institution
    from app.models.resume import Resume
    from app.models.student import StudentProfile
    from app.models.user import User

settings = get_settings()


# =============================================================================
# Enums (9 enums)
# =============================================================================

class DriveMode(str, enum.Enum):
    """Execution modality of a placement drive."""
    ON_CAMPUS = "on_campus"
    VIRTUAL = "virtual"
    HYBRID = "hybrid"


class DriveStatus(str, enum.Enum):
    """Lifecycle states of an institutional campus placement drive."""
    DRAFT = "draft"
    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TpoScreeningStatus(str, enum.Enum):
    """Institutional screening gate managed exclusively by TPOs."""
    BYPASSED = "bypassed"
    PENDING = "pending"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"


class ApplicationStatus(str, enum.Enum):
    """Corporate hiring pipeline stages managed by Recruiters."""
    APPLIED = "applied"
    UNDER_REVIEW = "under_review"
    SHORTLISTED = "shortlisted"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEWED = "interviewed"
    OFFERED = "offered"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_DECLINED = "offer_declined"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class DecisionDomain(str, enum.Enum):
    """Audit domain distinguishing TPO institutional actions from Recruiter decisions."""
    TPO_SCREENING = "tpo_screening"
    RECRUITMENT_LIFECYCLE = "recruitment_lifecycle"


class InterviewMode(str, enum.Enum):
    """Execution format of an interview round."""
    VIRTUAL = "virtual"
    IN_PERSON = "in_person"


class InterviewStatus(str, enum.Enum):
    """Lifecycle states of an individual scheduled interview round."""
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class InterviewOutcome(str, enum.Enum):
    """Evaluation result for a completed interview round."""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    ON_HOLD = "on_hold"


class NotificationCategory(str, enum.Enum):
    """System notification classification."""
    APPLICATION_UPDATE = "application_update"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_UPDATE = "interview_update"
    DRIVE_ANNOUNCEMENT = "drive_announcement"
    OFFER_EXTENDED = "offer_extended"
    ACTION_REQUIRED = "action_required"


class DriveLifecyclePhase(str, enum.Enum):
    """Granular 7-stage placement drive lifecycle states."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    REGISTRATION_OPEN = "registration_open"
    REGISTRATION_CLOSED = "registration_closed"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DriveRegistrationStatus(str, enum.Enum):
    """Student drive registration states."""
    REGISTERED = "registered"
    WITHDRAWN = "withdrawn"
    DISQUALIFIED = "disqualified"


class DriveActivityType(str, enum.Enum):
    """Drive schedule activity classifications."""
    PRE_PLACEMENT_TALK = "pre_placement_talk"
    COMPANY_PRESENTATION = "company_presentation"
    ONLINE_ASSESSMENT = "online_assessment"
    OFFLINE_ASSESSMENT = "offline_assessment"
    INTERVIEW_ROUND = "interview_round"
    OTHER = "other"


class DriveActivityStatus(str, enum.Enum):
    """Status of an individual scheduled drive activity."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DriveAttendanceStatus(str, enum.Enum):
    """Student attendance states recorded during a drive activity."""
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"


# =============================================================================
# Models (6 tables)
# =============================================================================

class PlacementDrive(Base, IntegerIdMixin, TimestampMixin):
    """Institutional placement drive coordinating multiple campus hiring opportunities."""
    __tablename__ = "placement_drives"
    __table_args__ = (
        CheckConstraint(
            "registration_start_date < registration_end_date",
            name="chk_drive_registration_dates",
        ),
    )

    institution_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )
    academic_year: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        doc="e.g. '2025-2026'",
    )
    target_graduation_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        doc="Target graduating batch e.g. 2026",
    )
    registration_start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    registration_end_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    drive_mode: Mapped[DriveMode] = mapped_column(
        SQLAlchemyEnum(
            DriveMode,
            name="drive_mode_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        default=DriveMode.ON_CAMPUS,
        nullable=False,
    )
    status: Mapped[DriveStatus] = mapped_column(
        SQLAlchemyEnum(
            DriveStatus,
            name="drive_status_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        default=DriveStatus.DRAFT,
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    guidelines: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    lifecycle_phase: Mapped[DriveLifecyclePhase] = mapped_column(
        SQLAlchemyEnum(
            DriveLifecyclePhase,
            name="drive_lifecycle_phase_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        default=DriveLifecyclePhase.DRAFT,
        nullable=False,
        index=True,
    )
    drive_start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    drive_end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    venue_location: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    instructions: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    required_documents: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    target_graduation_batches: Mapped[List[int]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    participating_company_ids: Mapped[List[int]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    eligible_department_ids: Mapped[List[int]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    # Relationships - strictly no silent delete cascades
    institution: Mapped["Institution"] = relationship(
        "Institution",
    )
    created_by: Mapped["User"] = relationship(
        "User",
    )
    drive_jobs: Mapped[List["PlacementDriveJob"]] = relationship(
        "PlacementDriveJob",
        back_populates="drive",
    )
    applications: Mapped[List["JobApplication"]] = relationship(
        "JobApplication",
        back_populates="drive",
        foreign_keys="[JobApplication.drive_id]",
    )


class PlacementDriveJob(Base, IntegerIdMixin, TimestampMixin):
    """Junction linking a job posting to an institutional placement drive."""
    __tablename__ = "placement_drive_jobs"
    __table_args__ = (
        UniqueConstraint("drive_id", "job_id", name="uq_drive_jobs_drive_job"),
        CheckConstraint(
            "((is_active = TRUE AND removed_at IS NULL) OR (is_active = FALSE AND removed_at IS NOT NULL))",
            name="chk_drive_job_removed_at",
        ),
    )

    drive_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("placement_drives.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("jobs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    removed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    drive: Mapped["PlacementDrive"] = relationship(
        "PlacementDrive",
        back_populates="drive_jobs",
    )
    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="drive_associations",
    )
    applications: Mapped[List["JobApplication"]] = relationship(
        "JobApplication",
        back_populates="drive_job",
        foreign_keys="[JobApplication.drive_id, JobApplication.job_id]",
        viewonly=True,
    )


class JobApplication(Base, IntegerIdMixin, TimestampMixin):
    """Unified application record supporting both direct applications and campus drive pipelines."""
    __tablename__ = "job_applications"
    __table_args__ = (
        UniqueConstraint("job_id", "student_id", name="uq_job_applications_job_student"),
        ForeignKeyConstraint(
            ["drive_id", "job_id"],
            ["placement_drive_jobs.drive_id", "placement_drive_jobs.job_id"],
            name="fk_job_applications_drive_job",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "((drive_id IS NULL AND tpo_screening_status = 'bypassed') OR (drive_id IS NOT NULL AND tpo_screening_status IN ('pending', 'shortlisted', 'rejected')))",
            name="chk_app_drive_tpo_screening",
        ),
        CheckConstraint(
            "((tpo_screening_status = 'bypassed' AND tpo_screened_by_user_id IS NULL AND tpo_screened_at IS NULL) OR "
            "(tpo_screening_status = 'pending' AND tpo_screened_by_user_id IS NULL AND tpo_screened_at IS NULL) OR "
            "(tpo_screening_status IN ('shortlisted', 'rejected') AND tpo_screened_by_user_id IS NOT NULL AND tpo_screened_at IS NOT NULL))",
            name="chk_app_tpo_screening_audit",
        ),
        CheckConstraint(
            "compatibility_score_at_application >= 0.0 AND compatibility_score_at_application <= 100.0",
            name="chk_app_compatibility_score",
        ),
        CheckConstraint(
            "((current_status = 'withdrawn' AND withdrawn_at IS NOT NULL AND withdrawal_reason IS NOT NULL) OR (current_status != 'withdrawn' AND withdrawn_at IS NULL))",
            name="chk_app_withdrawn_state",
        ),
    )

    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("jobs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    resume_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("resumes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    drive_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("placement_drives.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    tpo_screening_status: Mapped[TpoScreeningStatus] = mapped_column(
        SQLAlchemyEnum(
            TpoScreeningStatus,
            name="tpo_screening_status_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        default=TpoScreeningStatus.BYPASSED,
        nullable=False,
        index=True,
    )
    tpo_screened_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    tpo_screened_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    tpo_feedback: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    current_status: Mapped[ApplicationStatus] = mapped_column(
        SQLAlchemyEnum(
            ApplicationStatus,
            name="application_status_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        default=ApplicationStatus.APPLIED,
        nullable=False,
        index=True,
    )
    recruiter_decision_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    recruiter_feedback_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Internal recruiter feedback notes (confidential - redacted from student views)",
    )
    compatibility_score_at_application: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        doc="Snapshot compatibility score (0.00 to 100.00) at moment of application",
    )
    cover_letter: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    withdrawn_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    withdrawal_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    offer_deadline_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Optional official deadline by which the student must accept or decline an extended offer",
    )
    offer_package_lpa: Mapped[Optional[float]] = mapped_column(
        Numeric(6, 2),
        nullable=True,
        doc="Explicit compensation package offered in LPA (falls back to job.ctc_lpa when omitted)",
    )
    offer_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Official student-visible offer summary or terms",
    )

    # Relationships - strictly no silent delete cascades
    job: Mapped["Job"] = relationship(
        "Job",
        back_populates="applications",
        foreign_keys=[job_id],
    )
    student_profile: Mapped["StudentProfile"] = relationship(
        "StudentProfile",
        back_populates="applications",
        foreign_keys=[student_id],
    )
    resume: Mapped["Resume"] = relationship(
        "Resume",
        back_populates="applications",
        foreign_keys=[resume_id],
    )
    drive: Mapped[Optional["PlacementDrive"]] = relationship(
        "PlacementDrive",
        back_populates="applications",
        foreign_keys=[drive_id],
    )
    drive_job: Mapped[Optional["PlacementDriveJob"]] = relationship(
        "PlacementDriveJob",
        back_populates="applications",
        foreign_keys=[drive_id, job_id],
        viewonly=True,
    )
    tpo_screened_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[tpo_screened_by_user_id],
    )
    status_history: Mapped[List["ApplicationStatusHistory"]] = relationship(
        "ApplicationStatusHistory",
        back_populates="application",
        order_by="ApplicationStatusHistory.created_at",
    )
    interviews: Mapped[List["Interview"]] = relationship(
        "Interview",
        back_populates="application",
        order_by="Interview.round_number",
    )
    evaluations: Mapped[List["CandidateEvaluation"]] = relationship(
        "CandidateEvaluation",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="CandidateEvaluation.created_at.desc()",
    )
    notes: Mapped[List["CandidateNote"]] = relationship(
        "CandidateNote",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="CandidateNote.created_at.desc()",
    )


class ApplicationStatusHistory(Base, IntegerIdMixin):
    """Immutable audit trail for all application lifecycle and screening state transitions."""
    __tablename__ = "application_status_history"

    application_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_applications.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    changed_by_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    decision_domain: Mapped[DecisionDomain] = mapped_column(
        SQLAlchemyEnum(
            DecisionDomain,
            name="decision_domain_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        nullable=False,
    )
    from_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    to_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    application: Mapped["JobApplication"] = relationship(
        "JobApplication",
        back_populates="status_history",
    )
    changed_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[changed_by_user_id],
    )


class Interview(Base, IntegerIdMixin, TimestampMixin):
    """Interview round scheduled within the recruitment pipeline."""
    __tablename__ = "interviews"
    __table_args__ = (
        UniqueConstraint("application_id", "round_number", name="uq_interviews_app_round"),
        CheckConstraint("round_number > 0", name="chk_interview_round_positive"),
        CheckConstraint(
            "duration_minutes >= 15 AND duration_minutes <= 240",
            name="chk_interview_duration_range",
        ),
    )

    application_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_applications.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    round_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    round_title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="e.g. 'Technical Round 1', 'HR Discussion'",
    )
    interview_mode: Mapped[InterviewMode] = mapped_column(
        SQLAlchemyEnum(
            InterviewMode,
            name="interview_mode_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        default=InterviewMode.VIRTUAL,
        nullable=False,
    )
    meeting_link: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    location: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )
    scheduled_start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        default=45,
        nullable=False,
    )
    interviewer_names: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    instructions: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Candidate-visible preparation notes, reporting room, or link instructions",
    )
    status: Mapped[InterviewStatus] = mapped_column(
        SQLAlchemyEnum(
            InterviewStatus,
            name="interview_status_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        default=InterviewStatus.SCHEDULED,
        nullable=False,
        index=True,
    )
    outcome: Mapped[InterviewOutcome] = mapped_column(
        SQLAlchemyEnum(
            InterviewOutcome,
            name="interview_outcome_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        default=InterviewOutcome.PENDING,
        nullable=False,
        index=True,
    )
    feedback_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Internal recruiter feedback notes (confidential - redacted from student)",
    )
    created_by_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cancellation_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    application: Mapped["JobApplication"] = relationship(
        "JobApplication",
        back_populates="interviews",
    )
    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_user_id],
    )
    evaluations: Mapped[List["CandidateEvaluation"]] = relationship(
        "CandidateEvaluation",
        back_populates="interview",
        order_by="CandidateEvaluation.created_at.desc()",
    )


class Notification(Base, IntegerIdMixin):
    """In-app alert and update notification for users."""
    __tablename__ = "notifications"
    __table_args__ = (
        Index(
            "uq_notifications_recipient_idempotency",
            "recipient_user_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    recipient_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    category: Mapped[NotificationCategory] = mapped_column(
        SQLAlchemyEnum(
            NotificationCategory,
            name="notification_category_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    related_application_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("job_applications.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_drive_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("placement_drives.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_interview_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("interviews.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        doc="Ensures duplicate triggers don't send duplicate notifications",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    recipient: Mapped["User"] = relationship(
        "User",
        back_populates="notifications",
        foreign_keys=[recipient_user_id],
    )
    sender: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[sender_user_id],
    )
    related_application: Mapped[Optional["JobApplication"]] = relationship(
        "JobApplication",
        foreign_keys=[related_application_id],
    )
    related_drive: Mapped[Optional["PlacementDrive"]] = relationship(
        "PlacementDrive",
        foreign_keys=[related_drive_id],
    )
    related_interview: Mapped[Optional["Interview"]] = relationship(
        "Interview",
        foreign_keys=[related_interview_id],
    )


class NotificationPreference(Base, IntegerIdMixin, TimestampMixin):
    """Per-user smart notification preferences controlling alert delivery and lead time."""
    __tablename__ = "notification_preferences"
    __table_args__ = (
        CheckConstraint(
            "reminder_hours_before >= 1 AND reminder_hours_before <= 168",
            name="chk_notif_pref_reminder_hours",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    interview_schedules: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    upcoming_interview_reminders: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    status_changes: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    offer_alerts: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    offer_deadline_reminders: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    placement_announcements: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    reminder_hours_before: Mapped[int] = mapped_column(
        Integer,
        default=24,
        nullable=False,
    )

    user: Mapped["User"] = relationship("User")


class PlacementDriveRegistration(Base, IntegerIdMixin, TimestampMixin):
    """Tracks verified eligible student registrations in an institutional placement drive."""
    __tablename__ = "placement_drive_registrations"
    __table_args__ = (
        UniqueConstraint("drive_id", "student_id", name="uq_drive_registrations_drive_student"),
    )

    drive_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("placement_drives.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    registered_by_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    registration_source: Mapped[str] = mapped_column(
        String(30),
        default="student_self",
        nullable=False,
        doc="student_self or tpo_enrolled",
    )
    status: Mapped[DriveRegistrationStatus] = mapped_column(
        SQLAlchemyEnum(
            DriveRegistrationStatus,
            name="drive_registration_status_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        default=DriveRegistrationStatus.REGISTERED,
        nullable=False,
        index=True,
    )
    eligibility_passed: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    eligibility_snapshot: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )

    drive: Mapped["PlacementDrive"] = relationship("PlacementDrive")
    student_profile: Mapped["StudentProfile"] = relationship("StudentProfile")
    registered_by: Mapped["User"] = relationship("User", foreign_keys=[registered_by_user_id])


class PlacementDriveActivity(Base, IntegerIdMixin, TimestampMixin):
    """Scheduled drive event: PPT, company presentation, assessments, interview rounds, venue & coordinator."""
    __tablename__ = "placement_drive_activities"
    __table_args__ = (
        CheckConstraint(
            "scheduled_start < scheduled_end",
            name="chk_drive_activity_time_window",
        ),
    )

    drive_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("placement_drives.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    company_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    coordinator_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    coordinator_name: Mapped[str] = mapped_column(String(150), nullable=False)
    coordinator_contact: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    activity_type: Mapped[DriveActivityType] = mapped_column(
        SQLAlchemyEnum(
            DriveActivityType,
            name="drive_activity_type_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        nullable=False,
        index=True,
    )
    mode: Mapped[DriveMode] = mapped_column(
        SQLAlchemyEnum(
            DriveMode,
            name="drive_mode_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
            create_type=False,
        ),
        default=DriveMode.ON_CAMPUS,
        nullable=False,
    )
    venue: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    meeting_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[DriveActivityStatus] = mapped_column(
        SQLAlchemyEnum(
            DriveActivityStatus,
            name="drive_activity_status_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        default=DriveActivityStatus.SCHEDULED,
        nullable=False,
        index=True,
    )

    drive: Mapped["PlacementDrive"] = relationship("PlacementDrive")
    company: Mapped[Optional["Company"]] = relationship("Company")
    job: Mapped[Optional["Job"]] = relationship("Job")
    coordinator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[coordinator_user_id])
    attendance_records: Mapped[List["PlacementDriveAttendance"]] = relationship(
        "PlacementDriveAttendance",
        back_populates="activity",
        cascade="all, delete-orphan",
    )


class PlacementDriveAttendance(Base, IntegerIdMixin, TimestampMixin):
    """Attendance record for a student in a scheduled placement drive activity."""
    __tablename__ = "placement_drive_attendance"
    __table_args__ = (
        UniqueConstraint("activity_id", "student_id", name="uq_drive_attendance_activity_student"),
    )

    activity_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("placement_drive_activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    drive_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("placement_drives.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    attendance_status: Mapped[DriveAttendanceStatus] = mapped_column(
        SQLAlchemyEnum(
            DriveAttendanceStatus,
            name="drive_attendance_status_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        nullable=False,
    )
    marked_by_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    marked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    activity: Mapped["PlacementDriveActivity"] = relationship(
        "PlacementDriveActivity",
        back_populates="attendance_records",
    )
    student_profile: Mapped["StudentProfile"] = relationship("StudentProfile")
    marked_by: Mapped["User"] = relationship("User", foreign_keys=[marked_by_user_id])


class PlacementDriveAttendanceAudit(Base, IntegerIdMixin, TimestampMixin):
    """Append-only audit trail preserving every attendance creation and modification."""
    __tablename__ = "placement_drive_attendance_audit"

    attendance_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("placement_drive_attendance.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("placement_drive_activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    drive_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("placement_drives.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    changed_by_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    previous_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )

    changed_by: Mapped["User"] = relationship("User", foreign_keys=[changed_by_user_id])
    student_profile: Mapped["StudentProfile"] = relationship("StudentProfile")


class PlacementDriveAnnouncement(Base, IntegerIdMixin, TimestampMixin):
    """Persistent log of drive-specific announcements sent by TPOs."""
    __tablename__ = "placement_drive_announcements"

    drive_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("placement_drives.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sender_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    job_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    target_audience: Mapped[str] = mapped_column(String(50), default="all_registered", nullable=False)
    recipients_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    drive: Mapped["PlacementDrive"] = relationship("PlacementDrive")
    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_user_id])
