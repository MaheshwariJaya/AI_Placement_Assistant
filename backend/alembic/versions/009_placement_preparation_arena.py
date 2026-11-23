"""Placement Preparation Arena tables (questions, assessments, attempts, answers, privacy preferences).

Revision ID: 009_placement_preparation_arena
Revises: 008_smart_application_tracker
Create Date: 2026-11-12 16:15:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "009_placement_preparation_arena"
down_revision: Union[str, None] = "008_smart_application_tracker"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA_NAME = "placement_app_v2"

CATEGORY_VALUES = (
    "dsa",
    "programming_fundamentals",
    "dbms",
    "operating_systems",
    "computer_networks",
    "oop",
    "aptitude_logical",
    "quantitative",
    "verbal",
    "technical_mcqs",
    "hr_behavioral",
)
DIFFICULTY_VALUES = ("easy", "medium", "hard")
QUESTION_TYPE_VALUES = ("mcq", "coding", "behavioral")
ASSESSMENT_MODE_VALUES = ("topic_practice", "timed_test", "company_prep", "institutional_test")
ATTEMPT_STATUS_VALUES = ("in_progress", "submitted", "expired")
CONTENT_SOURCE_VALUES = ("curated_original", "institutional_staff", "ai_generated_practice")


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(*CATEGORY_VALUES, name="arena_category_enum", schema=SCHEMA_NAME).create(bind, checkfirst=True)
    postgresql.ENUM(*DIFFICULTY_VALUES, name="arena_difficulty_enum", schema=SCHEMA_NAME).create(bind, checkfirst=True)
    postgresql.ENUM(*QUESTION_TYPE_VALUES, name="arena_question_type_enum", schema=SCHEMA_NAME).create(
        bind, checkfirst=True
    )
    postgresql.ENUM(*ASSESSMENT_MODE_VALUES, name="arena_assessment_mode_enum", schema=SCHEMA_NAME).create(
        bind, checkfirst=True
    )
    postgresql.ENUM(*ATTEMPT_STATUS_VALUES, name="arena_attempt_status_enum", schema=SCHEMA_NAME).create(
        bind, checkfirst=True
    )
    postgresql.ENUM(*CONTENT_SOURCE_VALUES, name="arena_content_source_enum", schema=SCHEMA_NAME).create(
        bind, checkfirst=True
    )

    cat_col = lambda: postgresql.ENUM(*CATEGORY_VALUES, name="arena_category_enum", schema=SCHEMA_NAME, create_type=False)
    diff_col = lambda: postgresql.ENUM(*DIFFICULTY_VALUES, name="arena_difficulty_enum", schema=SCHEMA_NAME, create_type=False)
    qtype_col = lambda: postgresql.ENUM(
        *QUESTION_TYPE_VALUES, name="arena_question_type_enum", schema=SCHEMA_NAME, create_type=False
    )
    mode_col = lambda: postgresql.ENUM(
        *ASSESSMENT_MODE_VALUES, name="arena_assessment_mode_enum", schema=SCHEMA_NAME, create_type=False
    )
    status_col = lambda: postgresql.ENUM(
        *ATTEMPT_STATUS_VALUES, name="arena_attempt_status_enum", schema=SCHEMA_NAME, create_type=False
    )
    source_col = lambda: postgresql.ENUM(
        *CONTENT_SOURCE_VALUES, name="arena_content_source_enum", schema=SCHEMA_NAME, create_type=False
    )

    op.create_table(
        "arena_questions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("category", cat_col(), nullable=False),
        sa.Column("difficulty", diff_col(), nullable=False),
        sa.Column("question_type", qtype_col(), nullable=False),
        sa.Column("content_source", source_col(), server_default="curated_original", nullable=False),
        sa.Column("company_tag", sa.String(length=120), nullable=True),
        sa.Column("role_tags_json", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("options_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("correct_option_key", sa.String(length=16), nullable=True),
        sa.Column("starter_code_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("test_cases_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("explanation_text", sa.Text(), nullable=False),
        sa.Column("sample_solution_text", sa.Text(), nullable=True),
        sa.Column("expected_time_seconds", sa.Integer(), server_default="90", nullable=False),
        sa.Column("max_marks", sa.Integer(), server_default="10", nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "expected_time_seconds >= 10 AND expected_time_seconds <= 7200",
            name="chk_arena_q_time_bounds",
        ),
        sa.CheckConstraint("max_marks >= 1 AND max_marks <= 100", name="chk_arena_q_marks_bounds"),
        sa.ForeignKeyConstraint(["institution_id"], [f"{SCHEMA_NAME}.institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], [f"{SCHEMA_NAME}.users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    for idx_col in ("category", "difficulty", "question_type", "content_source", "company_tag", "institution_id", "is_active"):
        op.create_index(f"ix_arena_questions_{idx_col}", "arena_questions", [idx_col], schema=SCHEMA_NAME)

    op.create_table(
        "arena_assessments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("mode", mode_col(), nullable=False),
        sa.Column("category", cat_col(), nullable=True),
        sa.Column("difficulty", diff_col(), server_default="medium", nullable=False),
        sa.Column("company_name_style", sa.String(length=120), nullable=True),
        sa.Column("provenance_notice", sa.String(length=500), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), server_default="30", nullable=False),
        sa.Column("question_ids_json", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("passing_percentage", sa.Numeric(precision=5, scale=2), server_default="60.0", nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=True),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("target_graduation_year", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("is_published", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("duration_minutes >= 1 AND duration_minutes <= 180", name="chk_arena_assess_duration"),
        sa.CheckConstraint(
            "passing_percentage >= 0 AND passing_percentage <= 100",
            name="chk_arena_assess_passing_pct",
        ),
        sa.ForeignKeyConstraint(["institution_id"], [f"{SCHEMA_NAME}.institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["department_id"], [f"{SCHEMA_NAME}.departments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], [f"{SCHEMA_NAME}.users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    for idx_col in (
        "mode",
        "category",
        "difficulty",
        "company_name_style",
        "institution_id",
        "department_id",
        "target_graduation_year",
        "is_published",
    ):
        op.create_index(f"ix_arena_assessments_{idx_col}", "arena_assessments", [idx_col], schema=SCHEMA_NAME)

    op.create_table(
        "arena_attempts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("mode", mode_col(), nullable=False),
        sa.Column("category", cat_col(), nullable=True),
        sa.Column("difficulty", diff_col(), nullable=True),
        sa.Column("company_name_style", sa.String(length=120), nullable=True),
        sa.Column("status", status_col(), server_default="in_progress", nullable=False),
        sa.Column("question_ids_json", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("time_limit_seconds", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("elapsed_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_questions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("attempted_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("correct_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("accuracy_pct", sa.Numeric(precision=5, scale=2), server_default="0.0", nullable=False),
        sa.Column("score_pct", sa.Numeric(precision=5, scale=2), server_default="0.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("elapsed_seconds >= 0", name="chk_arena_attempt_elapsed"),
        sa.CheckConstraint("accuracy_pct >= 0 AND accuracy_pct <= 100", name="chk_arena_attempt_accuracy"),
        sa.CheckConstraint("score_pct >= 0 AND score_pct <= 100", name="chk_arena_attempt_score"),
        sa.ForeignKeyConstraint(["student_id"], [f"{SCHEMA_NAME}.student_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assessment_id"], [f"{SCHEMA_NAME}.arena_assessments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    for idx_col in ("student_id", "assessment_id", "mode", "category", "status"):
        op.create_index(f"ix_arena_attempts_{idx_col}", "arena_attempts", [idx_col], schema=SCHEMA_NAME)

    op.create_table(
        "arena_attempt_answers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("question_order", sa.Integer(), server_default="1", nullable=False),
        sa.Column("selected_option_key", sa.String(length=16), nullable=True),
        sa.Column("submitted_code", sa.Text(), nullable=True),
        sa.Column("code_language", sa.String(length=32), nullable=True),
        sa.Column("behavioral_response", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("score_awarded", sa.Numeric(precision=5, scale=2), server_default="0.0", nullable=False),
        sa.Column("time_spent_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("execution_result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ai_feedback_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("time_spent_seconds >= 0", name="chk_arena_ans_time_non_negative"),
        sa.ForeignKeyConstraint(["attempt_id"], [f"{SCHEMA_NAME}.arena_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], [f"{SCHEMA_NAME}.arena_questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], [f"{SCHEMA_NAME}.student_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id", "question_id", name="uq_arena_attempt_question"),
        schema=SCHEMA_NAME,
    )
    for idx_col in ("attempt_id", "question_id", "student_id"):
        op.create_index(f"ix_arena_attempt_answers_{idx_col}", "arena_attempt_answers", [idx_col], schema=SCHEMA_NAME)

    op.create_table(
        "arena_user_preferences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("leaderboard_opt_in", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("anonymize_name", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("preferred_language", sa.String(length=32), server_default="python", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], [f"{SCHEMA_NAME}.student_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", name="uq_arena_pref_student"),
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    op.drop_table("arena_user_preferences", schema=SCHEMA_NAME)
    op.drop_table("arena_attempt_answers", schema=SCHEMA_NAME)
    op.drop_table("arena_attempts", schema=SCHEMA_NAME)
    op.drop_table("arena_assessments", schema=SCHEMA_NAME)
    op.drop_table("arena_questions", schema=SCHEMA_NAME)

    bind = op.get_bind()
    for name in (
        "arena_content_source_enum",
        "arena_attempt_status_enum",
        "arena_assessment_mode_enum",
        "arena_question_type_enum",
        "arena_difficulty_enum",
        "arena_category_enum",
    ):
        postgresql.ENUM(name=name, schema=SCHEMA_NAME).drop(bind, checkfirst=True)

