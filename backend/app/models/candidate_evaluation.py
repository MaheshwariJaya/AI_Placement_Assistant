"""
Database models for TASK 08: Advanced Candidate Evaluation Workspace.
Provides structured interview evaluation forms, multi-interviewer ratings,
internal recruiter notes, and hiring recommendations.
"""
from datetime import datetime, timezone
import enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SQLAlchemyEnum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import get_settings
from app.core.base import Base, IntegerIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.job import Job
    from app.models.placement import Interview, JobApplication
    from app.models.user import User

settings = get_settings()


class EvaluationStage(str, enum.Enum):
    """Interview / evaluation round type classification."""
    TECHNICAL = "technical"
    HR = "hr"
    COMMUNICATION = "communication"
    PROBLEM_SOLVING = "problem_solving"
    PROJECT_DISCUSSION = "project_discussion"
    OVERALL = "overall"


class EvaluationRecommendation(str, enum.Enum):
    """Hiring decision recommendation submitted by an interviewer."""
    STRONG_HIRE = "strong_hire"
    HIRE = "hire"
    HOLD = "hold"
    NO_HIRE = "no_hire"
    STRONG_NO_HIRE = "strong_no_hire"


class NoteCategory(str, enum.Enum):
    """Internal recruiter candidate note categorization."""
    GENERAL = "general"
    INTERVIEW = "interview"
    COMPENSATION = "compensation"
    DECISION = "decision"
    REFERENCE = "reference"


class CandidateEvaluation(Base, IntegerIdMixin, TimestampMixin):
    """
    Structured interview evaluation record submitted by an individual interviewer.
    Supports multi-criteria ratings (technical, problem solving, communication, project depth, cultural fit),
    configurable custom criteria JSON, qualitative feedback, strengths/weaknesses, and hiring recommendation.
    """
    __tablename__ = "candidate_evaluations"
    __table_args__ = (
        CheckConstraint(
            "technical_rating IS NULL OR (technical_rating >= 1 AND technical_rating <= 5)",
            name="chk_cand_eval_tech_rating",
        ),
        CheckConstraint(
            "problem_solving_rating IS NULL OR (problem_solving_rating >= 1 AND problem_solving_rating <= 5)",
            name="chk_cand_eval_problem_solving_rating",
        ),
        CheckConstraint(
            "communication_rating IS NULL OR (communication_rating >= 1 AND communication_rating <= 5)",
            name="chk_cand_eval_comm_rating",
        ),
        CheckConstraint(
            "project_depth_rating IS NULL OR (project_depth_rating >= 1 AND project_depth_rating <= 5)",
            name="chk_cand_eval_project_rating",
        ),
        CheckConstraint(
            "cultural_fit_rating IS NULL OR (cultural_fit_rating >= 1 AND cultural_fit_rating <= 5)",
            name="chk_cand_eval_cultural_fit_rating",
        ),
        CheckConstraint(
            "overall_rating >= 1.0 AND overall_rating <= 5.0",
            name="chk_cand_eval_overall_rating",
        ),
    )

    application_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    interview_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("interviews.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    interviewer_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    interviewer_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    stage: Mapped[EvaluationStage] = mapped_column(
        SQLAlchemyEnum(
            EvaluationStage,
            name="evaluation_stage_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        default=EvaluationStage.TECHNICAL,
        nullable=False,
        index=True,
    )
    technical_rating: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="1-5 rating on technical fundamentals and domain expertise",
    )
    problem_solving_rating: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="1-5 rating on analytical and problem solving capability",
    )
    communication_rating: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="1-5 rating on communication clarity and articulation",
    )
    project_depth_rating: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="1-5 rating on project ownership, complexity and depth",
    )
    cultural_fit_rating: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="1-5 rating on teamwork, collaboration and culture alignment",
    )
    overall_rating: Mapped[float] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        doc="1.00 to 5.00 overall synthesized score by this interviewer",
    )
    recommendation: Mapped[EvaluationRecommendation] = mapped_column(
        SQLAlchemyEnum(
            EvaluationRecommendation,
            name="evaluation_recommendation_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        default=EvaluationRecommendation.HOLD,
        nullable=False,
        index=True,
    )
    strengths: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Key observed strengths and standout qualities",
    )
    weaknesses: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Identified concerns, weaknesses, or skill gaps",
    )
    written_feedback: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Detailed qualitative interview notes and summary",
    )
    criteria_ratings: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Flexible key-value map of rubric/custom evaluation criteria",
    )

    # Relationships
    application: Mapped["JobApplication"] = relationship(
        "JobApplication",
        back_populates="evaluations",
    )
    interview: Mapped[Optional["Interview"]] = relationship(
        "Interview",
        back_populates="evaluations",
    )
    interviewer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[interviewer_user_id],
    )


class CandidateNote(Base, IntegerIdMixin, TimestampMixin):
    """
    Job-specific confidential internal note created by recruiters/interviewers.
    Strictly private to the owning corporate partner; never exposed to candidates or students.
    """
    __tablename__ = "candidate_notes"

    application_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    author_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    category: Mapped[NoteCategory] = mapped_column(
        SQLAlchemyEnum(
            NoteCategory,
            name="candidate_note_category_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        default=NoteCategory.GENERAL,
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Internal recruiter notes and annotations",
    )
    is_pinned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    application: Mapped["JobApplication"] = relationship(
        "JobApplication",
        back_populates="notes",
    )
    author: Mapped["User"] = relationship(
        "User",
        foreign_keys=[author_user_id],
    )


class CandidateComparisonSession(Base, IntegerIdMixin, TimestampMixin):
    """
    Saved candidate comparison session created by recruiters.
    Preserves recruiter candidate shortlists, comparative deliberations,
    and hiring insights across up to 5 candidates for a specific job posting.
    """
    __tablename__ = "candidate_comparison_sessions"

    company_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
    )
    application_ids: Mapped[List[int]] = mapped_column(
        JSONB,
        nullable=False,
        doc="List of compared job_application IDs (2 to 5)",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Recruiter comparative deliberations and internal hiring notes",
    )
    ai_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Cached evidence-grounded AI comparison insights",
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company")
    job: Mapped["Job"] = relationship("Job")
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_user_id])


