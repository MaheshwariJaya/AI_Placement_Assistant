"""Complete Placement Drive Management: extended drive metadata, registrations, activities, attendance audit, announcements.

Revision ID: 010_complete_placement_drive_management
Revises: 009_placement_preparation_arena
Create Date: 2026-11-12 17:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "010_complete_placement_drive_management"
down_revision: Union[str, None] = "009_placement_preparation_arena"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA_NAME = "placement_app_v2"

LIFECYCLE_PHASE_VALUES = (
    "draft",
    "scheduled",
    "registration_open",
    "registration_closed",
    "ongoing",
    "completed",
    "cancelled",
)
REG_STATUS_VALUES = ("registered", "withdrawn", "disqualified")
ACTIVITY_TYPE_VALUES = (
    "pre_placement_talk",
    "company_presentation",
    "online_assessment",
    "offline_assessment",
    "interview_round",
    "other",
)
ACTIVITY_STATUS_VALUES = ("scheduled", "in_progress", "completed", "cancelled")
ATTENDANCE_STATUS_VALUES = ("present", "absent", "late", "excused")


def upgrade() -> None:
    bind = op.get_bind()

    postgresql.ENUM(*LIFECYCLE_PHASE_VALUES, name="drive_lifecycle_phase_enum", schema=SCHEMA_NAME).create(bind, checkfirst=True)
    postgresql.ENUM(*REG_STATUS_VALUES, name="drive_registration_status_enum", schema=SCHEMA_NAME).create(bind, checkfirst=True)
    postgresql.ENUM(*ACTIVITY_TYPE_VALUES, name="drive_activity_type_enum", schema=SCHEMA_NAME).create(bind, checkfirst=True)
    postgresql.ENUM(*ACTIVITY_STATUS_VALUES, name="drive_activity_status_enum", schema=SCHEMA_NAME).create(bind, checkfirst=True)
    postgresql.ENUM(*ATTENDANCE_STATUS_VALUES, name="drive_attendance_status_enum", schema=SCHEMA_NAME).create(bind, checkfirst=True)

    # 1. Extend placement_drives safely with nullable / defaulted columns
    op.add_column(
        "placement_drives",
        sa.Column(
            "lifecycle_phase",
            postgresql.ENUM(*LIFECYCLE_PHASE_VALUES, name="drive_lifecycle_phase_enum", schema=SCHEMA_NAME, create_type=False),
            nullable=False,
            server_default="draft",
        ),
        schema=SCHEMA_NAME,
    )
    op.add_column("placement_drives", sa.Column("drive_start_date", sa.DateTime(timezone=True), nullable=True), schema=SCHEMA_NAME)
    op.add_column("placement_drives", sa.Column("drive_end_date", sa.DateTime(timezone=True), nullable=True), schema=SCHEMA_NAME)
    op.add_column("placement_drives", sa.Column("venue_location", sa.String(length=255), nullable=True), schema=SCHEMA_NAME)
    op.add_column("placement_drives", sa.Column("instructions", sa.Text(), nullable=True), schema=SCHEMA_NAME)
    op.add_column(
        "placement_drives",
        sa.Column("required_documents", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        schema=SCHEMA_NAME,
    )
    op.add_column(
        "placement_drives",
        sa.Column("target_graduation_batches", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        schema=SCHEMA_NAME,
    )
    op.add_column(
        "placement_drives",
        sa.Column("participating_company_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        schema=SCHEMA_NAME,
    )
    op.add_column(
        "placement_drives",
        sa.Column("eligible_department_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        op.f(f"ix_{SCHEMA_NAME}_placement_drives_lifecycle_phase"),
        "placement_drives",
        ["lifecycle_phase"],
        schema=SCHEMA_NAME,
    )

    # Backfill existing rows cleanly
    op.execute(
        sa.text(
            f"""
            UPDATE {SCHEMA_NAME}.placement_drives
            SET lifecycle_phase = (
                CASE status::text
                    WHEN 'draft' THEN 'draft'
                    WHEN 'upcoming' THEN 'registration_open'
                    WHEN 'ongoing' THEN 'ongoing'
                    WHEN 'completed' THEN 'completed'
                    WHEN 'cancelled' THEN 'cancelled'
                    ELSE 'draft'
                END
            )::{SCHEMA_NAME}.drive_lifecycle_phase_enum,
            target_graduation_batches = jsonb_build_array(target_graduation_year);
            """
        )
    )

    # 2. placement_drive_registrations
    op.create_table(
        "placement_drive_registrations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("drive_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("registered_by_user_id", sa.Integer(), nullable=False),
        sa.Column("registration_source", sa.String(length=30), nullable=False, server_default="student_self"),
        sa.Column(
            "status",
            postgresql.ENUM(*REG_STATUS_VALUES, name="drive_registration_status_enum", schema=SCHEMA_NAME, create_type=False),
            nullable=False,
            server_default="registered",
        ),
        sa.Column("eligibility_passed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("eligibility_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["drive_id"], [f"{SCHEMA_NAME}.placement_drives.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], [f"{SCHEMA_NAME}.student_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["registered_by_user_id"], [f"{SCHEMA_NAME}.users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("drive_id", "student_id", name="uq_drive_registrations_drive_student"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_drive_regs_drive", "placement_drive_registrations", ["drive_id"], schema=SCHEMA_NAME)
    op.create_index("ix_drive_regs_student", "placement_drive_registrations", ["student_id"], schema=SCHEMA_NAME)
    op.create_index("ix_drive_regs_status", "placement_drive_registrations", ["status"], schema=SCHEMA_NAME)

    # 3. placement_drive_activities
    op.create_table(
        "placement_drive_activities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("drive_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("coordinator_user_id", sa.Integer(), nullable=True),
        sa.Column("coordinator_name", sa.String(length=150), nullable=False),
        sa.Column("coordinator_contact", sa.String(length=150), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column(
            "activity_type",
            postgresql.ENUM(*ACTIVITY_TYPE_VALUES, name="drive_activity_type_enum", schema=SCHEMA_NAME, create_type=False),
            nullable=False,
        ),
        sa.Column(
            "mode",
            postgresql.ENUM("on_campus", "virtual", "hybrid", name="drive_mode_enum", schema=SCHEMA_NAME, create_type=False),
            nullable=False,
            server_default="on_campus",
        ),
        sa.Column("venue", sa.String(length=255), nullable=True),
        sa.Column("meeting_link", sa.String(length=500), nullable=True),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(*ACTIVITY_STATUS_VALUES, name="drive_activity_status_enum", schema=SCHEMA_NAME, create_type=False),
            nullable=False,
            server_default="scheduled",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("scheduled_start < scheduled_end", name="chk_drive_activity_time_window"),
        sa.ForeignKeyConstraint(["drive_id"], [f"{SCHEMA_NAME}.placement_drives.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["job_id"], [f"{SCHEMA_NAME}.jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], [f"{SCHEMA_NAME}.companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], [f"{SCHEMA_NAME}.users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["coordinator_user_id"], [f"{SCHEMA_NAME}.users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_drive_act_drive", "placement_drive_activities", ["drive_id"], schema=SCHEMA_NAME)
    op.create_index("ix_drive_act_type", "placement_drive_activities", ["activity_type"], schema=SCHEMA_NAME)
    op.create_index("ix_drive_act_coord", "placement_drive_activities", ["coordinator_user_id"], schema=SCHEMA_NAME)

    # 4. placement_drive_attendance
    op.create_table(
        "placement_drive_attendance",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.Column("drive_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column(
            "attendance_status",
            postgresql.ENUM(*ATTENDANCE_STATUS_VALUES, name="drive_attendance_status_enum", schema=SCHEMA_NAME, create_type=False),
            nullable=False,
        ),
        sa.Column("marked_by_user_id", sa.Integer(), nullable=False),
        sa.Column("marked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["activity_id"], [f"{SCHEMA_NAME}.placement_drive_activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], [f"{SCHEMA_NAME}.placement_drives.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], [f"{SCHEMA_NAME}.student_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["marked_by_user_id"], [f"{SCHEMA_NAME}.users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("activity_id", "student_id", name="uq_drive_attendance_activity_student"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_drive_att_activity", "placement_drive_attendance", ["activity_id"], schema=SCHEMA_NAME)
    op.create_index("ix_drive_att_drive", "placement_drive_attendance", ["drive_id"], schema=SCHEMA_NAME)
    op.create_index("ix_drive_att_student", "placement_drive_attendance", ["student_id"], schema=SCHEMA_NAME)

    # 5. placement_drive_attendance_audit
    op.create_table(
        "placement_drive_attendance_audit",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("attendance_id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.Column("drive_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=False),
        sa.Column("previous_status", sa.String(length=30), nullable=True),
        sa.Column("new_status", sa.String(length=30), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["attendance_id"], [f"{SCHEMA_NAME}.placement_drive_attendance.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["activity_id"], [f"{SCHEMA_NAME}.placement_drive_activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drive_id"], [f"{SCHEMA_NAME}.placement_drives.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], [f"{SCHEMA_NAME}.student_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], [f"{SCHEMA_NAME}.users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_drive_att_audit_att", "placement_drive_attendance_audit", ["attendance_id"], schema=SCHEMA_NAME)
    op.create_index("ix_drive_att_audit_act", "placement_drive_attendance_audit", ["activity_id"], schema=SCHEMA_NAME)

    # 6. placement_drive_announcements
    op.create_table(
        "placement_drive_announcements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("drive_id", sa.Integer(), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("target_audience", sa.String(length=50), nullable=False, server_default="all_registered"),
        sa.Column("recipients_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["drive_id"], [f"{SCHEMA_NAME}.placement_drives.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sender_user_id"], [f"{SCHEMA_NAME}.users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["job_id"], [f"{SCHEMA_NAME}.jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_drive_ann_drive", "placement_drive_announcements", ["drive_id"], schema=SCHEMA_NAME)


def downgrade() -> None:
    op.drop_table("placement_drive_announcements", schema=SCHEMA_NAME)
    op.drop_table("placement_drive_attendance_audit", schema=SCHEMA_NAME)
    op.drop_table("placement_drive_attendance", schema=SCHEMA_NAME)
    op.drop_table("placement_drive_activities", schema=SCHEMA_NAME)
    op.drop_table("placement_drive_registrations", schema=SCHEMA_NAME)

    op.drop_index(op.f(f"ix_{SCHEMA_NAME}_placement_drives_lifecycle_phase"), table_name="placement_drives", schema=SCHEMA_NAME)
    op.drop_column("placement_drives", "eligible_department_ids", schema=SCHEMA_NAME)
    op.drop_column("placement_drives", "participating_company_ids", schema=SCHEMA_NAME)
    op.drop_column("placement_drives", "target_graduation_batches", schema=SCHEMA_NAME)
    op.drop_column("placement_drives", "required_documents", schema=SCHEMA_NAME)
    op.drop_column("placement_drives", "instructions", schema=SCHEMA_NAME)
    op.drop_column("placement_drives", "venue_location", schema=SCHEMA_NAME)
    op.drop_column("placement_drives", "drive_end_date", schema=SCHEMA_NAME)
    op.drop_column("placement_drives", "drive_start_date", schema=SCHEMA_NAME)
    op.drop_column("placement_drives", "lifecycle_phase", schema=SCHEMA_NAME)

    bind = op.get_bind()
    postgresql.ENUM(*ATTENDANCE_STATUS_VALUES, name="drive_attendance_status_enum", schema=SCHEMA_NAME).drop(bind, checkfirst=True)
    postgresql.ENUM(*ACTIVITY_STATUS_VALUES, name="drive_activity_status_enum", schema=SCHEMA_NAME).drop(bind, checkfirst=True)
    postgresql.ENUM(*ACTIVITY_TYPE_VALUES, name="drive_activity_type_enum", schema=SCHEMA_NAME).drop(bind, checkfirst=True)
    postgresql.ENUM(*REG_STATUS_VALUES, name="drive_registration_status_enum", schema=SCHEMA_NAME).drop(bind, checkfirst=True)
    postgresql.ENUM(*LIFECYCLE_PHASE_VALUES, name="drive_lifecycle_phase_enum", schema=SCHEMA_NAME).drop(bind, checkfirst=True)

