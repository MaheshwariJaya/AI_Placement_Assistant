"""Automated Placement Report Generator: placement_reports table, report enums, institution logo.

Revision ID: 011_automated_placement_report_generator
Revises: 010_complete_placement_drive_management
Create Date: 2026-11-13 10:45:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "011_automated_placement_report_generator"
down_revision: Union[str, None] = "010_complete_placement_drive_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA_NAME = "placement_app_v2"

REPORT_TYPE_VALUES = (
    "overall_institutional",
    "academic_year_wise",
    "department_wise",
    "graduation_batch",
    "company_wise",
    "placement_drive",
    "student_placement_status",
    "salary_package_analysis",
    "unplaced_students",
    "offer_acceptance",
)
REPORT_FORMAT_VALUES = ("pdf", "xlsx", "csv", "json")
REPORT_STATUS_VALUES = ("pending", "processing", "completed", "failed")


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Create Enums in schema
    postgresql.ENUM(*REPORT_TYPE_VALUES, name="placement_report_type_enum", schema=SCHEMA_NAME).create(bind, checkfirst=True)
    postgresql.ENUM(*REPORT_FORMAT_VALUES, name="placement_report_format_enum", schema=SCHEMA_NAME).create(bind, checkfirst=True)
    postgresql.ENUM(*REPORT_STATUS_VALUES, name="placement_report_status_enum", schema=SCHEMA_NAME).create(bind, checkfirst=True)

    # 2. Add logo_url to institutions if not present
    op.add_column(
        "institutions",
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        schema=SCHEMA_NAME,
    )

    # 3. Create placement_reports table
    op.create_table(
        "placement_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("generated_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "report_type",
            postgresql.ENUM(*REPORT_TYPE_VALUES, name="placement_report_type_enum", schema=SCHEMA_NAME, create_type=False),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "file_format",
            postgresql.ENUM(*REPORT_FORMAT_VALUES, name="placement_report_format_enum", schema=SCHEMA_NAME, create_type=False),
            nullable=False,
            server_default="pdf",
        ),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(*REPORT_STATUS_VALUES, name="placement_report_status_enum", schema=SCHEMA_NAME, create_type=False),
            nullable=False,
            server_default="completed",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("summary_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            [f"{SCHEMA_NAME}.institutions.id"],
            name="fk_placement_reports_institution_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["generated_by_user_id"],
            [f"{SCHEMA_NAME}.users.id"],
            name="fk_placement_reports_generated_by_user_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_placement_reports"),
        schema=SCHEMA_NAME,
    )

    op.create_index(
        "ix_placement_reports_institution_id",
        "placement_reports",
        ["institution_id"],
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_placement_reports_generated_by_user_id",
        "placement_reports",
        ["generated_by_user_id"],
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_placement_reports_report_type",
        "placement_reports",
        ["report_type"],
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_placement_reports_status",
        "placement_reports",
        ["status"],
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("ix_placement_reports_status", table_name="placement_reports", schema=SCHEMA_NAME)
    op.drop_index("ix_placement_reports_report_type", table_name="placement_reports", schema=SCHEMA_NAME)
    op.drop_index("ix_placement_reports_generated_by_user_id", table_name="placement_reports", schema=SCHEMA_NAME)
    op.drop_index("ix_placement_reports_institution_id", table_name="placement_reports", schema=SCHEMA_NAME)

    op.drop_table("placement_reports", schema=SCHEMA_NAME)

    op.drop_column("institutions", "logo_url", schema=SCHEMA_NAME)

    postgresql.ENUM(name="placement_report_status_enum", schema=SCHEMA_NAME).drop(bind, checkfirst=True)
    postgresql.ENUM(name="placement_report_format_enum", schema=SCHEMA_NAME).drop(bind, checkfirst=True)
    postgresql.ENUM(name="placement_report_type_enum", schema=SCHEMA_NAME).drop(bind, checkfirst=True)

