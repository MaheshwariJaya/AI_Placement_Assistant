"""Smart Application & Recruitment Tracker schema extensions.

Revision ID: 008_smart_application_tracker
Revises: 007_placement_readiness_analytics
Create Date: 2026-11-12 15:40:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "008_smart_application_tracker"
down_revision: Union[str, None] = "007_placement_readiness_analytics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA_NAME = "placement_app_v2"


def upgrade() -> None:
    op.add_column(
        "job_applications",
        sa.Column("offer_deadline_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA_NAME,
    )
    op.add_column(
        "job_applications",
        sa.Column("offer_package_lpa", sa.Numeric(precision=6, scale=2), nullable=True),
        schema=SCHEMA_NAME,
    )
    op.add_column(
        "job_applications",
        sa.Column("offer_notes", sa.Text(), nullable=True),
        schema=SCHEMA_NAME,
    )
    op.add_column(
        "interviews",
        sa.Column("instructions", sa.Text(), nullable=True),
        schema=SCHEMA_NAME,
    )

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("interview_schedules", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("upcoming_interview_reminders", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("status_changes", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("offer_alerts", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("offer_deadline_reminders", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("placement_announcements", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("reminder_hours_before", sa.Integer(), server_default=sa.text("24"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "reminder_hours_before >= 1 AND reminder_hours_before <= 168",
            name="chk_notif_pref_reminder_hours",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{SCHEMA_NAME}.users.id"],
            name="fk_notification_preferences_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_notification_preferences_user_id"),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_placement_app_v2_notification_preferences_user_id",
        "notification_preferences",
        ["user_id"],
        unique=True,
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_placement_app_v2_notification_preferences_user_id",
        table_name="notification_preferences",
        schema=SCHEMA_NAME,
    )
    op.drop_table("notification_preferences", schema=SCHEMA_NAME)
    op.drop_column("interviews", "instructions", schema=SCHEMA_NAME)
    op.drop_column("job_applications", "offer_notes", schema=SCHEMA_NAME)
    op.drop_column("job_applications", "offer_package_lpa", schema=SCHEMA_NAME)
    op.drop_column("job_applications", "offer_deadline_at", schema=SCHEMA_NAME)

