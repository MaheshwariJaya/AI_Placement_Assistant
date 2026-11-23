"""Resume intelligence module schema: resumes, education, skills, projects, experiences, and certifications.

Revision ID: 003_resume_intelligence
Revises: 002_refresh_token_revocation
Create Date: 2026-11-04 21:55:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_resume_intelligence"
down_revision: Union[str, None] = "002_refresh_token_revocation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA_NAME = "placement_app_v2"


def upgrade() -> None:
    # 1. Create student_education table
    op.create_table(
        "student_education",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("institution_name", sa.String(length=200), nullable=False),
        sa.Column("degree", sa.String(length=150), nullable=False),
        sa.Column("field_of_study", sa.String(length=150), nullable=True),
        sa.Column("start_year", sa.Integer(), nullable=True),
        sa.Column("end_year", sa.Integer(), nullable=True),
        sa.Column("cgpa_or_percentage", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"],
            [f"{SCHEMA_NAME}.student_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_student_education_student_id",
        "student_education",
        ["student_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )

    # 2. Create student_skills table
    op.create_table(
        "student_skills",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("skill_name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), server_default="technical", nullable=False),
        sa.Column("proficiency_level", sa.String(length=20), server_default="intermediate", nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"],
            [f"{SCHEMA_NAME}.student_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "skill_name", name="uq_student_skills_student_skill"),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_student_skills_student_id",
        "student_skills",
        ["student_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_student_skills_skill_name",
        "student_skills",
        ["skill_name"],
        unique=False,
        schema=SCHEMA_NAME,
    )

    # 3. Create student_projects table
    op.create_table(
        "student_projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("technologies", sa.Text(), nullable=True),
        sa.Column("project_url", sa.String(length=255), nullable=True),
        sa.Column("start_date", sa.String(length=30), nullable=True),
        sa.Column("end_date", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"],
            [f"{SCHEMA_NAME}.student_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_student_projects_student_id",
        "student_projects",
        ["student_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )

    # 4. Create student_experiences table
    op.create_table(
        "student_experiences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("role_title", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.String(length=30), nullable=True),
        sa.Column("end_date", sa.String(length=30), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"],
            [f"{SCHEMA_NAME}.student_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_student_experiences_student_id",
        "student_experiences",
        ["student_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )

    # 5. Create student_certifications table
    op.create_table(
        "student_certifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("certificate_name", sa.String(length=255), nullable=False),
        sa.Column("issuing_organization", sa.String(length=200), nullable=False),
        sa.Column("issue_date", sa.String(length=30), nullable=True),
        sa.Column("credential_url", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"],
            [f"{SCHEMA_NAME}.student_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_student_certifications_student_id",
        "student_certifications",
        ["student_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )

    # 6. Create resumes table
    op.create_table(
        "resumes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_type", sa.String(length=10), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_extracted_text", sa.Text(), nullable=True),
        sa.Column("parsed_entities_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("parsing_status", sa.String(length=50), server_default="uploaded", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("file_size_bytes <= 5242880", name="chk_resume_file_size_limit"),
        sa.CheckConstraint("file_type IN ('pdf', 'docx')", name="chk_resume_file_type"),
        sa.ForeignKeyConstraint(
            ["student_id"],
            [f"{SCHEMA_NAME}.student_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_resumes_student_id",
        "resumes",
        ["student_id"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_resumes_file_hash",
        "resumes",
        ["file_hash"],
        unique=False,
        schema=SCHEMA_NAME,
    )
    op.create_index(
        "ix_resumes_parsing_status",
        "resumes",
        ["parsing_status"],
        unique=False,
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index("ix_resumes_parsing_status", table_name="resumes", schema=SCHEMA_NAME)
    op.drop_index("ix_resumes_file_hash", table_name="resumes", schema=SCHEMA_NAME)
    op.drop_index("ix_resumes_student_id", table_name="resumes", schema=SCHEMA_NAME)
    op.drop_table("resumes", schema=SCHEMA_NAME)

    op.drop_index("ix_student_certifications_student_id", table_name="student_certifications", schema=SCHEMA_NAME)
    op.drop_table("student_certifications", schema=SCHEMA_NAME)

    op.drop_index("ix_student_experiences_student_id", table_name="student_experiences", schema=SCHEMA_NAME)
    op.drop_table("student_experiences", schema=SCHEMA_NAME)

    op.drop_index("ix_student_projects_student_id", table_name="student_projects", schema=SCHEMA_NAME)
    op.drop_table("student_projects", schema=SCHEMA_NAME)

    op.drop_index("ix_student_skills_skill_name", table_name="student_skills", schema=SCHEMA_NAME)
    op.drop_index("ix_student_skills_student_id", table_name="student_skills", schema=SCHEMA_NAME)
    op.drop_table("student_skills", schema=SCHEMA_NAME)

    op.drop_index("ix_student_education_student_id", table_name="student_education", schema=SCHEMA_NAME)
    op.drop_table("student_education", schema=SCHEMA_NAME)
