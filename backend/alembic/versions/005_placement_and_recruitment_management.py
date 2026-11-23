"""Placement and recruitment management module: placement_drives, placement_drive_jobs, job_applications, application_status_history, interviews, and notifications.

Revision ID: 005_placement_and_recruitment_management
Revises: 004_company_and_job_management
Create Date: 2026-11-05 19:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005_placement_and_recruitment_management"
down_revision: Union[str, None] = "004_company_and_job_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA_NAME = "placement_app_v2"


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 0. Widen alembic_version.version_num to support revision slug length > 32
    # -------------------------------------------------------------------------
    op.execute(
        sa.text(
            f"ALTER TABLE {SCHEMA_NAME}.alembic_version "
            "ALTER COLUMN version_num TYPE VARCHAR(64);"
        )
    )

    # -------------------------------------------------------------------------
    # 1. Create Enums in placement_app_v2 (9 enums)
    # -------------------------------------------------------------------------
    drive_mode_enum = postgresql.ENUM(
        "on_campus", "virtual", "hybrid",
        name="drive_mode_enum",
        schema=SCHEMA_NAME,
    )
    drive_mode_enum.create(op.get_bind(), checkfirst=True)

    drive_status_enum = postgresql.ENUM(
        "draft", "upcoming", "ongoing", "completed", "cancelled",
        name="drive_status_enum",
        schema=SCHEMA_NAME,
    )
    drive_status_enum.create(op.get_bind(), checkfirst=True)

    tpo_screening_status_enum = postgresql.ENUM(
        "bypassed", "pending", "shortlisted", "rejected",
        name="tpo_screening_status_enum",
        schema=SCHEMA_NAME,
    )
    tpo_screening_status_enum.create(op.get_bind(), checkfirst=True)

    application_status_enum = postgresql.ENUM(
        "applied", "under_review", "shortlisted", "interview_scheduled",
        "interviewed", "offered", "offer_accepted", "offer_declined",
        "rejected", "withdrawn",
        name="application_status_enum",
        schema=SCHEMA_NAME,
    )
    application_status_enum.create(op.get_bind(), checkfirst=True)

    decision_domain_enum = postgresql.ENUM(
        "tpo_screening", "recruitment_lifecycle",
        name="decision_domain_enum",
        schema=SCHEMA_NAME,
    )
    decision_domain_enum.create(op.get_bind(), checkfirst=True)

    interview_mode_enum = postgresql.ENUM(
        "virtual", "in_person",
        name="interview_mode_enum",
        schema=SCHEMA_NAME,
    )
    interview_mode_enum.create(op.get_bind(), checkfirst=True)

    interview_status_enum = postgresql.ENUM(
        "scheduled", "completed", "cancelled", "no_show",
        name="interview_status_enum",
        schema=SCHEMA_NAME,
    )
    interview_status_enum.create(op.get_bind(), checkfirst=True)

    interview_outcome_enum = postgresql.ENUM(
        "pending", "passed", "failed", "on_hold",
        name="interview_outcome_enum",
        schema=SCHEMA_NAME,
    )
    interview_outcome_enum.create(op.get_bind(), checkfirst=True)

    notification_category_enum = postgresql.ENUM(
        "application_update", "interview_scheduled", "interview_update",
        "drive_announcement", "offer_extended", "action_required",
        name="notification_category_enum",
        schema=SCHEMA_NAME,
    )
    notification_category_enum.create(op.get_bind(), checkfirst=True)

    # -------------------------------------------------------------------------
    # 2. Table: placement_drives (2 FKs, 1 CHECK)
    # -------------------------------------------------------------------------
    op.create_table(
        "placement_drives",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("academic_year", sa.String(length=20), nullable=False),
        sa.Column("target_graduation_year", sa.Integer(), nullable=False),
        sa.Column("registration_start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registration_end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "drive_mode",
            postgresql.ENUM("on_campus", "virtual", "hybrid", name="drive_mode_enum", schema=SCHEMA_NAME, create_type=False),
            server_default="on_campus",
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM("draft", "upcoming", "ongoing", "completed", "cancelled", name="drive_status_enum", schema=SCHEMA_NAME, create_type=False),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("guidelines", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            [f"{SCHEMA_NAME}.institutions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            [f"{SCHEMA_NAME}.users.id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "registration_start_date < registration_end_date",
            name="chk_drive_registration_dates",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_placement_drives_institution_id", "placement_drives", ["institution_id"], unique=False, schema=SCHEMA_NAME)
    op.create_index("ix_placement_drives_created_by_user_id", "placement_drives", ["created_by_user_id"], unique=False, schema=SCHEMA_NAME)
    op.create_index("ix_placement_drives_name", "placement_drives", ["name"], unique=False, schema=SCHEMA_NAME)
    op.create_index("ix_placement_drives_academic_year", "placement_drives", ["academic_year"], unique=False, schema=SCHEMA_NAME)
    op.create_index("ix_placement_drives_target_graduation_year", "placement_drives", ["target_graduation_year"], unique=False, schema=SCHEMA_NAME)
    op.create_index("ix_placement_drives_status", "placement_drives", ["status"], unique=False, schema=SCHEMA_NAME)
    op.create_index("ix_placement_drives_is_active", "placement_drives", ["is_active"], unique=False, schema=SCHEMA_NAME)

    # -------------------------------------------------------------------------
    # 3. Table: placement_drive_jobs (2 FKs, 1 UNIQUE, 1 CHECK)
    # -------------------------------------------------------------------------
    op.create_table(
        "placement_drive_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("drive_id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["drive_id"],
            [f"{SCHEMA_NAME}.placement_drives.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            [f"{SCHEMA_NAME}.jobs.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("drive_id", "job_id", name="uq_drive_jobs_drive_job"),
        sa.CheckConstraint(
            "((is_active = TRUE AND removed_at IS NULL) OR (is_active = FALSE AND removed_at IS NOT NULL))",
            name="chk_drive_job_removed_at",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_placement_drive_jobs_drive_id", "placement_drive_jobs", ["drive_id"], unique=False, schema=SCHEMA_NAME)
    op.create_index("ix_placement_drive_jobs_job_id", "placement_drive_jobs", ["job_id"], unique=False, schema=SCHEMA_NAME)
    op.create_index("ix_placement_drive_jobs_is_active", "placement_drive_jobs", ["is_active"], unique=False, schema=SCHEMA_NAME)

    # -------------------------------------------------------------------------
    # 4. Table: job_applications (6 FKs [5 single + 1 composite], 1 UNIQUE, 4 CHECK)
    # -------------------------------------------------------------------------
    op.create_table(
        "job_applications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("drive_id", sa.Integer(), nullable=True),
        sa.Column(
            "tpo_screening_status",
            postgresql.ENUM("bypassed", "pending", "shortlisted", "rejected", name="tpo_screening_status_enum", schema=SCHEMA_NAME, create_type=False),
            server_default="bypassed",
            nullable=False,
        ),
        sa.Column("tpo_screened_by_user_id", sa.Integer(), nullable=True),
        sa.Column("tpo_screened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tpo_feedback", sa.Text(), nullable=True),
        sa.Column(
            "current_status",
            postgresql.ENUM(
                "applied", "under_review", "shortlisted", "interview_scheduled",
                "interviewed", "offered", "offer_accepted", "offer_declined",
                "rejected", "withdrawn",
                name="application_status_enum",
                schema=SCHEMA_NAME,
                create_type=False,
            ),
            server_default="applied",
            nullable=False,
        ),
        sa.Column("recruiter_decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recruiter_feedback_notes", sa.Text(), nullable=True),
        sa.Column("compatibility_score_at_application", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("cover_letter", sa.Text(), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawal_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"],
            [f"{SCHEMA_NAME}.jobs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            [f"{SCHEMA_NAME}.student_profiles.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resume_id"],
            [f"{SCHEMA_NAME}.resumes.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["drive_id"],
            [f"{SCHEMA_NAME}.placement_drives.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tpo_screened_by_user_id"],
            [f"{SCHEMA_NAME}.users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["drive_id", "job_id"],
            [f"{SCHEMA_NAME}.placement_drive_jobs.drive_id", f"{SCHEMA_NAME}.placement_drive_jobs.job_id"],
            name="fk_job_applications_drive_job",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("job_id", "student_id", name="uq_job_applications_job_student"),
        sa.CheckConstraint(
            "((drive_id IS NULL AND tpo_screening_status = 'bypassed') OR (drive_id IS NOT NULL AND tpo_screening_status IN ('pending', 'shortlisted', 'rejected')))",
            name="chk_app_drive_tpo_screening",
        ),
        sa.CheckConstraint(
            "((tpo_screening_status = 'bypassed' AND tpo_screened_by_user_id IS NULL AND tpo_screened_at IS NULL) OR "
            "(tpo_screening_status = 'pending' AND tpo_screened_by_user_id IS NULL AND tpo_screened_at IS NULL) OR "
            "(tpo_screening_status IN ('shortlisted', 'rejected') AND tpo_screened_by_user_id IS NOT NULL AND tpo_screened_at IS NOT NULL))",
            name="chk_app_tpo_screening_audit",
        ),
        sa.CheckConstraint(
            "compatibility_score_at_application >= 0.0 AND compatibility_score_at_application <= 100.0",
            name="chk_app_compatibility_score",
        ),
        sa.CheckConstraint(
            "((current_status = 'withdrawn' AND withdrawn_at IS NOT NULL AND withdrawal_reason IS NOT NULL) OR (current_status != 'withdrawn' AND withdrawn_at IS NULL))",
            name="chk_app_withdrawn_state",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_job_applications_job_id", "job_applications", ["job_id"], unique=False, schema=SCHEMA_NAME)
    op.create_index("ix_job_applications_student_id", "job_applications", ["student_id"], unique=False, schema=SCHEMA_NAME)
    op.create_index("ix_job_applications_resume_id", "job_applications", ["resume_id"], unique=False, schema=SCHEMA_NAME)
    op.create_index("ix_job_applications_drive_id", "job_applications", ["drive_id"], unique=False, schema=SCHEMA_NAME)
    op.create_index("ix_job_applications_tpo_screening_status", "job_applications", ["tpo_screening_status"], unique=False, schema=SCHEMA_NAME)
    op.create_index("ix_job_applications_current_status", "job_applications", ["current_status"], unique=False, schema=SCHEMA_NAME)

    # -------------------------------------------------------------------------
    # 5. Table: application_status_history (2 FKs)
    # -------------------------------------------------------------------------
    op.create_table(
        "application_status_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "decision_domain",
            postgresql.ENUM("tpo_screening", "recruitment_lifecycle", name="decision_domain_enum", schema=SCHEMA_NAME, create_type=False),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(length=50), nullable=True),
        sa.Column("to_status", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            [f"{SCHEMA_NAME}.job_applications.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_user_id"],
            [f"{SCHEMA_NAME}.users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_application_status_history_application_id", "application_status_history", ["application_id"], unique=False, schema=SCHEMA_NAME)
    op.create_index("ix_application_status_history_created_at", "application_status_history", ["created_at"], unique=False, schema=SCHEMA_NAME)

    # -------------------------------------------------------------------------
    # 6. Immutable Audit Trigger Function & Trigger for application_status_history
    # -------------------------------------------------------------------------
    op.execute(
        sa.text(
            f"""
            CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.fn_prevent_history_modification()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'application_status_history records are immutable audit entries and cannot be updated or deleted.';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE TRIGGER trg_application_status_history_immutable
            BEFORE UPDATE OR DELETE ON {SCHEMA_NAME}.application_status_history
            FOR EACH ROW
            EXECUTE FUNCTION {SCHEMA_NAME}.fn_prevent_history_modification();
            """
        )
    )

    # -------------------------------------------------------------------------
    # 7. Table: interviews (2 FKs, 1 UNIQUE, 2 CHECK)
    # -------------------------------------------------------------------------
    op.create_table(
        "interviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("round_title", sa.String(length=100), nullable=False),
        sa.Column(
            "interview_mode",
            postgresql.ENUM("virtual", "in_person", name="interview_mode_enum", schema=SCHEMA_NAME, create_type=False),
            server_default="virtual",
            nullable=False,
        ),
        sa.Column("meeting_link", sa.String(length=500), nullable=True),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("scheduled_start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), server_default="45", nullable=False),
        sa.Column("interviewer_names", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("scheduled", "completed", "cancelled", "no_show", name="interview_status_enum", schema=SCHEMA_NAME, create_type=False),
            server_default="scheduled",
            nullable=False,
        ),
        sa.Column(
            "outcome",
            postgresql.ENUM("pending", "passed", "failed", "on_hold", name="interview_outcome_enum", schema=SCHEMA_NAME, create_type=False),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("feedback_notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            [f"{SCHEMA_NAME}.job_applications.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            [f"{SCHEMA_NAME}.users.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("application_id", "round_number", name="uq_interviews_app_round"),
        sa.CheckConstraint("round_number > 0", name="chk_interview_round_positive"),
        sa.CheckConstraint("duration_minutes >= 15 AND duration_minutes <= 240", name="chk_interview_duration_range"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_interviews_application_id", "interviews", ["application_id"], unique=False, schema=SCHEMA_NAME)
    op.create_index("ix_interviews_scheduled_start_time", "interviews", ["scheduled_start_time"], unique=False, schema=SCHEMA_NAME)
    op.create_index("ix_interviews_status", "interviews", ["status"], unique=False, schema=SCHEMA_NAME)
    op.create_index("ix_interviews_outcome", "interviews", ["outcome"], unique=False, schema=SCHEMA_NAME)

    # -------------------------------------------------------------------------
    # 8. Table: notifications (5 FKs, 1 PARTIAL UNIQUE INDEX)
    # -------------------------------------------------------------------------
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("recipient_user_id", sa.Integer(), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "category",
            postgresql.ENUM(
                "application_update", "interview_scheduled", "interview_update",
                "drive_announcement", "offer_extended", "action_required",
                name="notification_category_enum",
                schema=SCHEMA_NAME,
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("related_application_id", sa.Integer(), nullable=True),
        sa.Column("related_drive_id", sa.Integer(), nullable=True),
        sa.Column("related_interview_id", sa.Integer(), nullable=True),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=150), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            [f"{SCHEMA_NAME}.users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sender_user_id"],
            [f"{SCHEMA_NAME}.users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["related_application_id"],
            [f"{SCHEMA_NAME}.job_applications.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["related_drive_id"],
            [f"{SCHEMA_NAME}.placement_drives.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["related_interview_id"],
            [f"{SCHEMA_NAME}.interviews.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index("ix_notifications_recipient_user_id", "notifications", ["recipient_user_id"], unique=False, schema=SCHEMA_NAME)
    op.create_index("ix_notifications_category", "notifications", ["category"], unique=False, schema=SCHEMA_NAME)
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"], unique=False, schema=SCHEMA_NAME)
    op.create_index(
        "uq_notifications_recipient_idempotency",
        "notifications",
        ["recipient_user_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. Drop trigger and function for application_status_history
    # -------------------------------------------------------------------------
    op.execute(
        sa.text(
            f"DROP TRIGGER IF EXISTS trg_application_status_history_immutable ON {SCHEMA_NAME}.application_status_history;"
        )
    )
    op.execute(
        sa.text(
            f"DROP FUNCTION IF EXISTS {SCHEMA_NAME}.fn_prevent_history_modification();"
        )
    )

    # -------------------------------------------------------------------------
    # 2. Drop tables in reverse topological dependency order
    # -------------------------------------------------------------------------
    op.drop_table("notifications", schema=SCHEMA_NAME)
    op.drop_table("interviews", schema=SCHEMA_NAME)
    op.drop_table("application_status_history", schema=SCHEMA_NAME)
    op.drop_table("job_applications", schema=SCHEMA_NAME)
    op.drop_table("placement_drive_jobs", schema=SCHEMA_NAME)
    op.drop_table("placement_drives", schema=SCHEMA_NAME)

    # -------------------------------------------------------------------------
    # 3. Drop enums in placement_app_v2
    # -------------------------------------------------------------------------
    sa.Enum(name="notification_category_enum", schema=SCHEMA_NAME).drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="interview_outcome_enum", schema=SCHEMA_NAME).drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="interview_status_enum", schema=SCHEMA_NAME).drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="interview_mode_enum", schema=SCHEMA_NAME).drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="decision_domain_enum", schema=SCHEMA_NAME).drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="application_status_enum", schema=SCHEMA_NAME).drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="tpo_screening_status_enum", schema=SCHEMA_NAME).drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="drive_status_enum", schema=SCHEMA_NAME).drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="drive_mode_enum", schema=SCHEMA_NAME).drop(op.get_bind(), checkfirst=True)

