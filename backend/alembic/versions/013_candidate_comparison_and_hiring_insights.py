"""Candidate Comparison & Hiring Insights: candidate_comparison_sessions table.

Revision ID: 013_candidate_comparison_and_hiring_insights
Revises: 012_advanced_candidate_evaluation_workspace
Create Date: 2026-11-13 17:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "013_candidate_comparison_and_hiring_insights"
down_revision: Union[str, None] = "012_advanced_candidate_evaluation_workspace"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA_NAME = "placement_app_v2"


def upgrade() -> None:
    op.create_table(
        "candidate_comparison_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("application_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("ai_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            [f"{SCHEMA_NAME}.companies.id"],
            name="fk_candidate_comparison_sessions_company",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            [f"{SCHEMA_NAME}.jobs.id"],
            name="fk_candidate_comparison_sessions_job",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            [f"{SCHEMA_NAME}.users.id"],
            name="fk_candidate_comparison_sessions_created_by",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_candidate_comparison_sessions"),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_cand_comp_sessions_company_id",
        "candidate_comparison_sessions",
        ["company_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_cand_comp_sessions_job_id",
        "candidate_comparison_sessions",
        ["job_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_cand_comp_sessions_created_by",
        "candidate_comparison_sessions",
        ["created_by_user_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    op.drop_index("ix_cand_comp_sessions_created_by", table_name="candidate_comparison_sessions", schema=SCHEMA_NAME)
    op.drop_index("ix_cand_comp_sessions_job_id", table_name="candidate_comparison_sessions", schema=SCHEMA_NAME)
    op.drop_index("ix_cand_comp_sessions_company_id", table_name="candidate_comparison_sessions", schema=SCHEMA_NAME)
    op.drop_table("candidate_comparison_sessions", schema=SCHEMA_NAME)

