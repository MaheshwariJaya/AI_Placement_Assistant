"""Advanced Candidate Evaluation Workspace: candidate_evaluations and candidate_notes tables.

Revision ID: 012_advanced_candidate_evaluation_workspace
Revises: 011_automated_placement_report_generator
Create Date: 2026-11-13 15:55:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "012_advanced_candidate_evaluation_workspace"
down_revision: Union[str, None] = "011_automated_placement_report_generator"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA_NAME = "placement_app_v2"

STAGE_VALUES = (
    "technical",
    "hr",
    "communication",
    "problem_solving",
    "project_discussion",
    "overall",
)
RECOMMENDATION_VALUES = (
    "strong_hire",
    "hire",
    "hold",
    "no_hire",
    "strong_no_hire",
)
NOTE_CATEGORY_VALUES = (
    "general",
    "interview",
    "compensation",
    "decision",
    "reference",
)


def upgrade() -> None:
    # 1. Enums
    stage_enum = postgresql.ENUM(*STAGE_VALUES, name="evaluation_stage_enum", schema=SCHEMA_NAME)
    stage_enum.create(op.get_bind(), checkfirst=True)

    rec_enum = postgresql.ENUM(*RECOMMENDATION_VALUES, name="evaluation_recommendation_enum", schema=SCHEMA_NAME)
    rec_enum.create(op.get_bind(), checkfirst=True)

    cat_enum = postgresql.ENUM(*NOTE_CATEGORY_VALUES, name="candidate_note_category_enum", schema=SCHEMA_NAME)
    cat_enum.create(op.get_bind(), checkfirst=True)

    # 2. Table: candidate_evaluations
    op.create_table(
        "candidate_evaluations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("interview_id", sa.Integer(), nullable=True),
        sa.Column("interviewer_user_id", sa.Integer(), nullable=False),
        sa.Column("interviewer_name", sa.String(length=200), nullable=False),
        sa.Column(
            "stage",
            postgresql.ENUM(*STAGE_VALUES, name="evaluation_stage_enum", schema=SCHEMA_NAME, create_type=False),
            nullable=False,
        ),
        sa.Column("technical_rating", sa.Integer(), nullable=True),
        sa.Column("problem_solving_rating", sa.Integer(), nullable=True),
        sa.Column("communication_rating", sa.Integer(), nullable=True),
        sa.Column("project_depth_rating", sa.Integer(), nullable=True),
        sa.Column("cultural_fit_rating", sa.Integer(), nullable=True),
        sa.Column("overall_rating", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column(
            "recommendation",
            postgresql.ENUM(*RECOMMENDATION_VALUES, name="evaluation_recommendation_enum", schema=SCHEMA_NAME, create_type=False),
            nullable=False,
        ),
        sa.Column("strengths", sa.Text(), nullable=True),
        sa.Column("weaknesses", sa.Text(), nullable=True),
        sa.Column("written_feedback", sa.Text(), nullable=False),
        sa.Column("criteria_ratings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_candidate_evaluations"),
        sa.ForeignKeyConstraint(
            ["application_id"],
            [f"{SCHEMA_NAME}.job_applications.id"],
            name="fk_candidate_evaluations_application",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["interview_id"],
            [f"{SCHEMA_NAME}.interviews.id"],
            name="fk_candidate_evaluations_interview",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["interviewer_user_id"],
            [f"{SCHEMA_NAME}.users.id"],
            name="fk_candidate_evaluations_interviewer",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "technical_rating IS NULL OR (technical_rating >= 1 AND technical_rating <= 5)",
            name="chk_cand_eval_tech_rating",
        ),
        sa.CheckConstraint(
            "problem_solving_rating IS NULL OR (problem_solving_rating >= 1 AND problem_solving_rating <= 5)",
            name="chk_cand_eval_problem_solving_rating",
        ),
        sa.CheckConstraint(
            "communication_rating IS NULL OR (communication_rating >= 1 AND communication_rating <= 5)",
            name="chk_cand_eval_comm_rating",
        ),
        sa.CheckConstraint(
            "project_depth_rating IS NULL OR (project_depth_rating >= 1 AND project_depth_rating <= 5)",
            name="chk_cand_eval_project_rating",
        ),
        sa.CheckConstraint(
            "cultural_fit_rating IS NULL OR (cultural_fit_rating >= 1 AND cultural_fit_rating <= 5)",
            name="chk_cand_eval_cultural_fit_rating",
        ),
        sa.CheckConstraint(
            "overall_rating >= 1.0 AND overall_rating <= 5.0",
            name="chk_cand_eval_overall_rating",
        ),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_candidate_evaluations_app_id",
        "candidate_evaluations",
        ["application_id"],
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_candidate_evaluations_interview_id",
        "candidate_evaluations",
        ["interview_id"],
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_candidate_evaluations_interviewer_id",
        "candidate_evaluations",
        ["interviewer_user_id"],
        schema=SCHEMA_NAME,
    )

    # 3. Table: candidate_notes
    op.create_table(
        "candidate_notes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("author_user_id", sa.Integer(), nullable=False),
        sa.Column("author_name", sa.String(length=200), nullable=False),
        sa.Column(
            "category",
            postgresql.ENUM(*NOTE_CATEGORY_VALUES, name="candidate_note_category_enum", schema=SCHEMA_NAME, create_type=False),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_candidate_notes"),
        sa.ForeignKeyConstraint(
            ["application_id"],
            [f"{SCHEMA_NAME}.job_applications.id"],
            name="fk_candidate_notes_application",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"],
            [f"{SCHEMA_NAME}.users.id"],
            name="fk_candidate_notes_author",
            ondelete="RESTRICT",
        ),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_candidate_notes_app_id",
        "candidate_notes",
        ["application_id"],
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_candidate_notes_author_id",
        "candidate_notes",
        ["author_user_id"],
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    op.drop_table("candidate_notes", schema=SCHEMA_NAME)
    op.drop_table("candidate_evaluations", schema=SCHEMA_NAME)
    op.execute(f"DROP TYPE IF EXISTS {SCHEMA_NAME}.candidate_note_category_enum")
    op.execute(f"DROP TYPE IF EXISTS {SCHEMA_NAME}.evaluation_recommendation_enum")
    op.execute(f"DROP TYPE IF EXISTS {SCHEMA_NAME}.evaluation_stage_enum")
