"""AI Mock Interview & Assessment Studio tables: sessions, questions, answers, and evaluations.

Revision ID: 006_ai_mock_interview_studio
Revises: 005_placement_and_recruitment_management
Create Date: 2026-11-12 13:35:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "006_ai_mock_interview_studio"
down_revision: Union[str, None] = "005_placement_and_recruitment_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA_NAME = "placement_app_v2"


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. Create Enums in placement_app_v2
    # -------------------------------------------------------------------------
    category_enum = postgresql.ENUM(
        "technical", "hr", "behavioral", "aptitude", "project_based",
        name="mock_interview_category_enum",
        schema=SCHEMA_NAME,
    )
    category_enum.create(op.get_bind(), checkfirst=True)

    difficulty_enum = postgresql.ENUM(
        "beginner", "intermediate", "advanced",
        name="mock_interview_difficulty_enum",
        schema=SCHEMA_NAME,
    )
    difficulty_enum.create(op.get_bind(), checkfirst=True)

    status_enum = postgresql.ENUM(
        "in_progress", "paused", "completed", "abandoned",
        name="mock_interview_status_enum",
        schema=SCHEMA_NAME,
    )
    status_enum.create(op.get_bind(), checkfirst=True)

    # -------------------------------------------------------------------------
    # 2. Table: mock_interview_sessions
    # -------------------------------------------------------------------------
    op.create_table(
        "mock_interview_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("target_role", sa.String(length=200), nullable=True),
        sa.Column(
            "category",
            postgresql.ENUM(
                "technical", "hr", "behavioral", "aptitude", "project_based",
                name="mock_interview_category_enum",
                schema=SCHEMA_NAME,
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "difficulty",
            postgresql.ENUM(
                "beginner", "intermediate", "advanced",
                name="mock_interview_difficulty_enum",
                schema=SCHEMA_NAME,
                create_type=False,
            ),
            server_default="intermediate",
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "in_progress", "paused", "completed", "abandoned",
                name="mock_interview_status_enum",
                schema=SCHEMA_NAME,
                create_type=False,
            ),
            server_default="in_progress",
            nullable=False,
        ),
        sa.Column("question_count", sa.Integer(), server_default="5", nullable=False),
        sa.Column("include_followups", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("time_limit_minutes", sa.Integer(), nullable=True),
        sa.Column("elapsed_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("current_question_order", sa.Integer(), server_default="1", nullable=False),
        sa.Column("context_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ai_provider", sa.String(length=50), nullable=True),
        sa.Column("ai_model", sa.String(length=100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], [f"{SCHEMA_NAME}.student_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], [f"{SCHEMA_NAME}.jobs.id"], ondelete="SET NULL"),
        sa.CheckConstraint("question_count >= 1 AND question_count <= 20", name="chk_mock_session_question_count"),
        sa.CheckConstraint("elapsed_seconds >= 0", name="chk_mock_session_elapsed_non_negative"),
        sa.CheckConstraint("current_question_order >= 1", name="chk_mock_session_current_order"),
        sa.CheckConstraint(
            "time_limit_minutes IS NULL OR (time_limit_minutes >= 1 AND time_limit_minutes <= 180)",
            name="chk_mock_session_time_limit",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_mock_interview_sessions_student_id", "mock_interview_sessions", ["student_id"], schema=SCHEMA_NAME)
    op.create_index("ix_mock_interview_sessions_job_id", "mock_interview_sessions", ["job_id"], schema=SCHEMA_NAME)
    op.create_index("ix_mock_interview_sessions_category", "mock_interview_sessions", ["category"], schema=SCHEMA_NAME)
    op.create_index("ix_mock_interview_sessions_difficulty", "mock_interview_sessions", ["difficulty"], schema=SCHEMA_NAME)
    op.create_index("ix_mock_interview_sessions_status", "mock_interview_sessions", ["status"], schema=SCHEMA_NAME)

    # -------------------------------------------------------------------------
    # 3. Table: mock_interview_questions
    # -------------------------------------------------------------------------
    op.create_table(
        "mock_interview_questions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("question_order", sa.Integer(), nullable=False),
        sa.Column("is_followup", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("parent_question_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            postgresql.ENUM(
                "technical", "hr", "behavioral", "aptitude", "project_based",
                name="mock_interview_category_enum",
                schema=SCHEMA_NAME,
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("topic", sa.String(length=150), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("expected_key_points", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_answer", sa.Text(), nullable=False),
        sa.Column("difficulty_hint", sa.String(length=30), server_default="intermediate", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], [f"{SCHEMA_NAME}.mock_interview_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_question_id"], [f"{SCHEMA_NAME}.mock_interview_questions.id"], ondelete="SET NULL"),
        sa.CheckConstraint("question_order >= 1", name="chk_mock_question_order_positive"),
        sa.UniqueConstraint("session_id", "question_order", name="uq_mock_question_session_order"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_mock_interview_questions_session_id", "mock_interview_questions", ["session_id"], schema=SCHEMA_NAME)

    # -------------------------------------------------------------------------
    # 4. Table: mock_interview_answers
    # -------------------------------------------------------------------------
    op.create_table(
        "mock_interview_answers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("input_mode", sa.String(length=20), server_default="text", nullable=False),
        sa.Column("response_time_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], [f"{SCHEMA_NAME}.mock_interview_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], [f"{SCHEMA_NAME}.mock_interview_questions.id"], ondelete="CASCADE"),
        sa.CheckConstraint("input_mode IN ('text', 'voice')", name="chk_mock_answer_input_mode"),
        sa.CheckConstraint("response_time_seconds >= 0", name="chk_mock_answer_response_time"),
        sa.UniqueConstraint("question_id", name="uq_mock_answers_question_id"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_mock_interview_answers_session_id", "mock_interview_answers", ["session_id"], schema=SCHEMA_NAME)
    op.create_index("ix_mock_interview_answers_question_id", "mock_interview_answers", ["question_id"], unique=True, schema=SCHEMA_NAME)

    # -------------------------------------------------------------------------
    # 5. Table: mock_interview_evaluations
    # -------------------------------------------------------------------------
    op.create_table(
        "mock_interview_evaluations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("overall_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("technical_correctness_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("conceptual_understanding_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("problem_solving_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("communication_clarity_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("answer_structure_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("relevance_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("project_knowledge_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("question_evaluations_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("strengths_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("weaknesses_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("suggested_improvements_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommended_topics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("advisory_disclaimer", sa.Text(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], [f"{SCHEMA_NAME}.mock_interview_sessions.id"], ondelete="CASCADE"),
        sa.CheckConstraint("overall_score >= 0 AND overall_score <= 100", name="chk_mock_eval_overall"),
        sa.CheckConstraint("technical_correctness_score >= 0 AND technical_correctness_score <= 100", name="chk_mock_eval_tech"),
        sa.CheckConstraint("conceptual_understanding_score >= 0 AND conceptual_understanding_score <= 100", name="chk_mock_eval_concept"),
        sa.CheckConstraint("problem_solving_score >= 0 AND problem_solving_score <= 100", name="chk_mock_eval_problem"),
        sa.CheckConstraint("communication_clarity_score >= 0 AND communication_clarity_score <= 100", name="chk_mock_eval_comm"),
        sa.CheckConstraint("answer_structure_score >= 0 AND answer_structure_score <= 100", name="chk_mock_eval_structure"),
        sa.CheckConstraint("relevance_score >= 0 AND relevance_score <= 100", name="chk_mock_eval_relevance"),
        sa.CheckConstraint(
            "project_knowledge_score IS NULL OR (project_knowledge_score >= 0 AND project_knowledge_score <= 100)",
            name="chk_mock_eval_project",
        ),
        sa.UniqueConstraint("session_id", name="uq_mock_evaluations_session_id"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_mock_interview_evaluations_session_id", "mock_interview_evaluations", ["session_id"], unique=True, schema=SCHEMA_NAME)


def downgrade() -> None:
    op.drop_table("mock_interview_evaluations", schema=SCHEMA_NAME)
    op.drop_table("mock_interview_answers", schema=SCHEMA_NAME)
    op.drop_table("mock_interview_questions", schema=SCHEMA_NAME)
    op.drop_table("mock_interview_sessions", schema=SCHEMA_NAME)

    sa.Enum(name="mock_interview_status_enum", schema=SCHEMA_NAME).drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="mock_interview_difficulty_enum", schema=SCHEMA_NAME).drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="mock_interview_category_enum", schema=SCHEMA_NAME).drop(op.get_bind(), checkfirst=True)

