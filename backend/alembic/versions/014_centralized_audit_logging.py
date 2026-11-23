"""Centralized Audit Logging & Activity Monitoring: audit_logs table.

Revision ID: 014_centralized_audit_logging
Revises: 013_candidate_comparison_and_hiring_insights
Create Date: 2026-11-13 18:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "014_centralized_audit_logging"
down_revision: Union[str, None] = "013_candidate_comparison_and_hiring_insights"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA_NAME = "placement_app_v2"


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("user_role", sa.String(length=50), nullable=True),
        sa.Column("user_email", sa.String(length=255), nullable=True),
        sa.Column("user_name", sa.String(length=200), nullable=True),
        sa.Column("institution_id", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="SUCCESS", nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("user_agent", sa.String(length=300), nullable=True),
        sa.Column("previous_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("updated_values", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("prev_hash", sa.String(length=64), nullable=True),
        sa.Column("record_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            [f"{SCHEMA_NAME}.institutions.id"],
            name="fk_audit_logs_institution",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{SCHEMA_NAME}.users.id"],
            name="fk_audit_logs_user",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
        schema=SCHEMA_NAME,
    )

    op.create_index(
        "ix_audit_logs_event_id",
        "audit_logs",
        ["event_id"],
        unique=True,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_audit_logs_user_id",
        "audit_logs",
        ["user_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_audit_logs_institution_id",
        "audit_logs",
        ["institution_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_audit_logs_category",
        "audit_logs",
        ["category"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_audit_logs_action",
        "audit_logs",
        ["action"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_audit_logs_entity_type",
        "audit_logs",
        ["entity_type"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_audit_logs_status",
        "audit_logs",
        ["status"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_audit_logs_timestamp",
        "audit_logs",
        ["timestamp"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_audit_logs_inst_timestamp",
        "audit_logs",
        ["institution_id", "timestamp"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_audit_logs_cat_timestamp",
        "audit_logs",
        ["category", "timestamp"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_audit_logs_entity",
        "audit_logs",
        ["entity_type", "entity_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs", schema=SCHEMA_NAME)
    op.drop_index("ix_audit_logs_cat_timestamp", table_name="audit_logs", schema=SCHEMA_NAME)
    op.drop_index("ix_audit_logs_inst_timestamp", table_name="audit_logs", schema=SCHEMA_NAME)
    op.drop_index("ix_audit_logs_timestamp", table_name="audit_logs", schema=SCHEMA_NAME)
    op.drop_index("ix_audit_logs_status", table_name="audit_logs", schema=SCHEMA_NAME)
    op.drop_index("ix_audit_logs_entity_type", table_name="audit_logs", schema=SCHEMA_NAME)
    op.drop_index("ix_audit_logs_action", table_name="audit_logs", schema=SCHEMA_NAME)
    op.drop_index("ix_audit_logs_category", table_name="audit_logs", schema=SCHEMA_NAME)
    op.drop_index("ix_audit_logs_institution_id", table_name="audit_logs", schema=SCHEMA_NAME)
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs", schema=SCHEMA_NAME)
    op.drop_index("ix_audit_logs_event_id", table_name="audit_logs", schema=SCHEMA_NAME)
    op.drop_table("audit_logs", schema=SCHEMA_NAME)

