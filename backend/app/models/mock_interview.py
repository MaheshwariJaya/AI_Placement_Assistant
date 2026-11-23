"""ORM models for AI Mock Interview & Assessment Studio (practice only, isolated from recruitment interviews)."""
import enum
from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
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


class MockInterviewCategory(str, enum.Enum):
    TECHNICAL = "technical"
    HR = "hr"
    BEHAVIORAL = "behavioral"
    APTITUDE = "aptitude"
    PROJECT_BASED = "project_based"


class MockInterviewDifficulty(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class MockInterviewStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class MockInterviewSession(Base, IntegerIdMixin, TimestampMixin):
    """Student practice mock interview session grounded in verified profile and optional target job."""

    __tablename__ = "mock_interview_sessions"
    __table_args__ = (
        CheckConstraint("question_count >= 1 AND question_count <= 100", name="chk_mock_session_question_count"),
        CheckConstraint("elapsed_seconds >= 0", name="chk_mock_session_elapsed_non_negative"),
        CheckConstraint("current_question_order >= 1", name="chk_mock_session_current_order"),
        CheckConstraint(
            "time_limit_minutes IS NULL OR (time_limit_minutes >= 1 AND time_limit_minutes <= 180)",
            name="chk_mock_session_time_limit",
        ),
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
    )
    target_role: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )
    category: Mapped[MockInterviewCategory] = mapped_column(
        SQLAlchemyEnum(
            MockInterviewCategory,
            name="mock_interview_category_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        nullable=False,
        index=True,
    )
    difficulty: Mapped[MockInterviewDifficulty] = mapped_column(
        SQLAlchemyEnum(
            MockInterviewDifficulty,
            name="mock_interview_difficulty_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        default=MockInterviewDifficulty.INTERMEDIATE,
        nullable=False,
        index=True,
    )
    status: Mapped[MockInterviewStatus] = mapped_column(
        SQLAlchemyEnum(
            MockInterviewStatus,
            name="mock_interview_status_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        default=MockInterviewStatus.IN_PROGRESS,
        nullable=False,
        index=True,
    )
    question_count: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
    )
    include_followups: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    time_limit_minutes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    elapsed_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    current_question_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    question_format: Mapped[str] = mapped_column(
        String(30),
        default="conversational",
        nullable=False,
        doc="Test style: 'conversational' (interactive text/voice) or 'mcq' (timed objective test).",
    )
    context_snapshot_json: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True,
        doc="Sanitized snapshot of student profile, resume, and target job used to ground questions.",
    )
    ai_provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    ai_model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    paused_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    student_profile: Mapped["StudentProfile"] = relationship(
        "StudentProfile",
        back_populates="mock_interview_sessions",
    )
    job: Mapped[Optional["Job"]] = relationship("Job")
    questions: Mapped[list["MockInterviewQuestion"]] = relationship(
        "MockInterviewQuestion",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="MockInterviewQuestion.question_order",
    )
    answers: Mapped[list["MockInterviewAnswer"]] = relationship(
        "MockInterviewAnswer",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    evaluation: Mapped[Optional["MockInterviewEvaluation"]] = relationship(
        "MockInterviewEvaluation",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )


class MockInterviewQuestion(Base, IntegerIdMixin):
    """Individual generated or follow-up prompt within a mock interview session."""

    __tablename__ = "mock_interview_questions"
    __table_args__ = (
        UniqueConstraint("session_id", "question_order", name="uq_mock_question_session_order"),
        CheckConstraint("question_order >= 1", name="chk_mock_question_order_positive"),
    )

    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mock_interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    is_followup: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    parent_question_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("mock_interview_questions.id", ondelete="SET NULL"),
        nullable=True,
    )
    category: Mapped[MockInterviewCategory] = mapped_column(
        SQLAlchemyEnum(
            MockInterviewCategory,
            name="mock_interview_category_enum",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
            schema=settings.DB_SCHEMA,
        ),
        nullable=False,
    )
    topic: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    expected_key_points: Mapped[Any] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=False,
        default=list,
    )
    model_answer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    difficulty_hint: Mapped[str] = mapped_column(
        String(30),
        default="intermediate",
        nullable=False,
    )
    question_type: Mapped[str] = mapped_column(
        String(30),
        default="open_ended",
        nullable=False,
        doc="'open_ended' for conversational interview prompts or 'mcq' for multiple-choice options.",
    )
    options_json: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=True,
        doc="List of options [{'key': 'A', 'text': '...'}, ...] for MCQ questions.",
    )
    correct_option_key: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        doc="Correct option key for MCQ questions (e.g. 'A', 'B', 'C', 'D').",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    session: Mapped["MockInterviewSession"] = relationship(
        "MockInterviewSession",
        back_populates="questions",
    )
    answer: Mapped[Optional["MockInterviewAnswer"]] = relationship(
        "MockInterviewAnswer",
        back_populates="question",
        uselist=False,
        cascade="all, delete-orphan",
    )


class MockInterviewAnswer(Base, IntegerIdMixin):
    """Student answer submitted for a specific mock interview question."""

    __tablename__ = "mock_interview_answers"
    __table_args__ = (
        CheckConstraint("input_mode IN ('text', 'voice')", name="chk_mock_answer_input_mode"),
        CheckConstraint("response_time_seconds >= 0", name="chk_mock_answer_response_time"),
    )

    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mock_interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mock_interview_questions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    answer_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    input_mode: Mapped[str] = mapped_column(
        String(20),
        default="text",
        nullable=False,
    )
    selected_option_key: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        doc="Candidate's selected option key for MCQ questions (e.g. 'A', 'B', 'C', 'D').",
    )
    response_time_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    session: Mapped["MockInterviewSession"] = relationship(
        "MockInterviewSession",
        back_populates="answers",
    )
    question: Mapped["MockInterviewQuestion"] = relationship(
        "MockInterviewQuestion",
        back_populates="answer",
    )


class MockInterviewEvaluation(Base, IntegerIdMixin, TimestampMixin):
    """Structured multi-criteria advisory evaluation for a completed mock interview session."""

    __tablename__ = "mock_interview_evaluations"
    __table_args__ = (
        CheckConstraint("overall_score >= 0 AND overall_score <= 100", name="chk_mock_eval_overall"),
        CheckConstraint("technical_correctness_score >= 0 AND technical_correctness_score <= 100", name="chk_mock_eval_tech"),
        CheckConstraint("conceptual_understanding_score >= 0 AND conceptual_understanding_score <= 100", name="chk_mock_eval_concept"),
        CheckConstraint("problem_solving_score >= 0 AND problem_solving_score <= 100", name="chk_mock_eval_problem"),
        CheckConstraint("communication_clarity_score >= 0 AND communication_clarity_score <= 100", name="chk_mock_eval_comm"),
        CheckConstraint("answer_structure_score >= 0 AND answer_structure_score <= 100", name="chk_mock_eval_structure"),
        CheckConstraint("relevance_score >= 0 AND relevance_score <= 100", name="chk_mock_eval_relevance"),
        CheckConstraint(
            "project_knowledge_score IS NULL OR (project_knowledge_score >= 0 AND project_knowledge_score <= 100)",
            name="chk_mock_eval_project",
        ),
    )

    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mock_interview_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    overall_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    technical_correctness_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    conceptual_understanding_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    problem_solving_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    communication_clarity_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    answer_structure_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    relevance_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    project_knowledge_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)

    question_evaluations_json: Mapped[Any] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=False,
        default=list,
    )
    strengths_json: Mapped[Any] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=False,
        default=list,
    )
    weaknesses_json: Mapped[Any] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=False,
        default=list,
    )
    suggested_improvements_json: Mapped[Any] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=False,
        default=list,
    )
    recommended_topics_json: Mapped[Any] = mapped_column(
        JSON().with_variant(postgresql.JSONB, "postgresql"),
        nullable=False,
        default=list,
    )
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    advisory_disclaimer: Mapped[str] = mapped_column(Text, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    session: Mapped["MockInterviewSession"] = relationship(
        "MockInterviewSession",
        back_populates="evaluation",
    )

