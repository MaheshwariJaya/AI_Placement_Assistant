"""Company and job management module: companies, recruiter_profiles, jobs, job_skills, and job_eligible_departments.

Revision ID: 004_company_and_job_management
Revises: 003_resume_intelligence
Create Date: 2026-11-05 11:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004_company_and_job_management"
down_revision: Union[str, None] = "003_resume_intelligence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA_NAME = "placement_app_v2"


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. Create Enums in placement_app_v2
    # -------------------------------------------------------------------------
    employment_type_enum = postgresql.ENUM(
        "full_time", "internship", "intern_to_full_time",
        name="job_employment_type_enum",
        schema=SCHEMA_NAME,
    )
    employment_type_enum.create(op.get_bind(), checkfirst=True)

    work_mode_enum = postgresql.ENUM(
        "on_site", "hybrid", "remote",
        name="job_work_mode_enum",
        schema=SCHEMA_NAME,
    )
    work_mode_enum.create(op.get_bind(), checkfirst=True)

    job_status_enum = postgresql.ENUM(
        "draft", "published", "closed", "cancelled",
        name="job_status_enum",
        schema=SCHEMA_NAME,
    )
    job_status_enum.create(op.get_bind(), checkfirst=True)

    # -------------------------------------------------------------------------
    # 2. Create companies table
    # -------------------------------------------------------------------------
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("industry", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("location", sa.String(length=150), nullable=True),
        sa.Column("company_size", sa.String(length=50), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=30), nullable=True),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            [f"{SCHEMA_NAME}.institutions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_companies_name"),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_companies_institution_id",
        "companies",
        ["institution_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_companies_industry",
        "companies",
        ["industry"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_companies_is_verified",
        "companies",
        ["is_verified"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_companies_is_active",
        "companies",
        ["is_active"],
        unique=False,
        schema=SCHEMA_NAME,
    )

    # -------------------------------------------------------------------------
    # 3. Create recruiter_profiles table
    # -------------------------------------------------------------------------
    op.create_table(
        "recruiter_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("designation", sa.String(length=100), nullable=True),
        sa.Column("corporate_phone", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{SCHEMA_NAME}.users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            [f"{SCHEMA_NAME}.companies.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_recruiter_profiles_user_id"),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_recruiter_profiles_company_id",
        "recruiter_profiles",
        ["company_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )

    # -------------------------------------------------------------------------
    # 4. Create jobs table
    # -------------------------------------------------------------------------
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "employment_type",
            postgresql.ENUM("full_time", "internship", "intern_to_full_time", name="job_employment_type_enum", schema=SCHEMA_NAME, create_type=False),
            nullable=False,
        ),
        sa.Column(
            "work_mode",
            postgresql.ENUM("on_site", "hybrid", "remote", name="job_work_mode_enum", schema=SCHEMA_NAME, create_type=False),
            nullable=False,
        ),
        sa.Column("location", sa.String(length=150), nullable=False),
        sa.Column("salary_range", sa.String(length=100), nullable=True),
        sa.Column("ctc_lpa", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("base_salary_lpa", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("stipend_monthly", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("min_cgpa", sa.Numeric(precision=4, scale=2), server_default="0.0", nullable=False),
        sa.Column("target_graduation_year", sa.Integer(), nullable=True),
        sa.Column("max_active_backlogs", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_total_backlogs", sa.Integer(), server_default="0", nullable=False),
        sa.Column("application_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("draft", "published", "closed", "cancelled", name="job_status_enum", schema=SCHEMA_NAME, create_type=False),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            [f"{SCHEMA_NAME}.companies.id"],
            ondelete="RESTRICT",
        ),
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
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_jobs_company_id",
        "jobs",
        ["company_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_jobs_institution_id",
        "jobs",
        ["institution_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_jobs_created_by_user_id",
        "jobs",
        ["created_by_user_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_jobs_title",
        "jobs",
        ["title"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_jobs_status",
        "jobs",
        ["status"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_jobs_employment_type",
        "jobs",
        ["employment_type"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_jobs_target_graduation_year",
        "jobs",
        ["target_graduation_year"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_jobs_application_deadline",
        "jobs",
        ["application_deadline"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_jobs_is_active",
        "jobs",
        ["is_active"],
        unique=False,
        schema=SCHEMA_NAME,
    )

    # -------------------------------------------------------------------------
    # 5. Create job_skills table
    # -------------------------------------------------------------------------
    op.create_table(
        "job_skills",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("skill_name", sa.String(length=100), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("weight_factor", sa.Numeric(precision=3, scale=2), server_default="1.0", nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"],
            [f"{SCHEMA_NAME}.jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "skill_name", name="uq_job_skill_name"),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_job_skills_skill_name",
        "job_skills",
        ["skill_name"],
        unique=False,
        schema=SCHEMA_NAME,
    )

    # -------------------------------------------------------------------------
    # 6. Create job_eligible_departments table
    # -------------------------------------------------------------------------
    op.create_table(
        "job_eligible_departments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"],
            [f"{SCHEMA_NAME}.jobs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            [f"{SCHEMA_NAME}.departments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "department_id", name="uq_job_department"),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_job_eligible_departments_department_id",
        "job_eligible_departments",
        ["department_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    op.drop_table("job_eligible_departments", schema=SCHEMA_NAME)
    op.drop_table("job_skills", schema=SCHEMA_NAME)
    op.drop_table("jobs", schema=SCHEMA_NAME)
    op.drop_table("recruiter_profiles", schema=SCHEMA_NAME)
    op.drop_table("companies", schema=SCHEMA_NAME)

    sa.Enum(name="job_status_enum", schema=SCHEMA_NAME).drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="job_work_mode_enum", schema=SCHEMA_NAME).drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="job_employment_type_enum", schema=SCHEMA_NAME).drop(op.get_bind(), checkfirst=True)
