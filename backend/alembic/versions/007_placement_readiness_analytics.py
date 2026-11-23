"""Placement Readiness Prediction & Historical Analytics table (readiness_snapshots).

Revision ID: 007_placement_readiness_analytics
Revises: 006_ai_mock_interview_studio
Create Date: 2026-11-12 15:25:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "007_placement_readiness_analytics"
down_revision: Union[str, None] = "006_ai_mock_interview_studio"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA_NAME = "placement_app_v2"


def upgrade() -> None:
    category_enum = postgresql.ENUM(
        "excellent_preparation",
        "placement_ready",
        "needs_improvement",
        "requires_significant_preparation",
        name="readiness_category_enum",
        schema=SCHEMA_NAME,
    )
    category_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "readiness_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("target_role", sa.String(length=200), nullable=True),
        sa.Column("formula_version", sa.String(length=32), server_default="v1.0", nullable=False),
        sa.Column("overall_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column(
            "category",
            postgresql.ENUM(
                "excellent_preparation",
                "placement_ready",
                "needs_improvement",
                "requires_significant_preparation",
                name="readiness_category_enum",
                schema=SCHEMA_NAME,
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("weights_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("indicators_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("academic_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("missing_data_fields_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("limitations_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("remaining_skill_gaps_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommendations_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ai_provider", sa.String(length=50), nullable=True),
        sa.Column("ai_model", sa.String(length=100), nullable=True),
        sa.Column("transparency_notice", sa.Text(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], [f"{SCHEMA_NAME}.student_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], [f"{SCHEMA_NAME}.jobs.id"], ondelete="SET NULL"),
        sa.CheckConstraint("overall_score >= 0 AND overall_score <= 100", name="chk_readiness_overall_score_range"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_readiness_snapshots_student_id", "readiness_snapshots", ["student_id"], schema=SCHEMA_NAME)
    op.create_index("ix_readiness_snapshots_job_id", "readiness_snapshots", ["job_id"], schema=SCHEMA_NAME)
    op.create_index("ix_readiness_snapshots_formula_version", "readiness_snapshots", ["formula_version"], schema=SCHEMA_NAME)
    op.create_index("ix_readiness_snapshots_category", "readiness_snapshots", ["category"], schema=SCHEMA_NAME)
    op.create_index("ix_readiness_snapshots_calculated_at", "readiness_snapshots", ["calculated_at"], schema=SCHEMA_NAME)


def downgrade() -> None:
    op.drop_table("readiness_snapshots", schema=SCHEMA_NAME)
    sa.Enum(name="readiness_category_enum", schema=SCHEMA_NAME).drop(op.get_bind(), checkfirst=True)

