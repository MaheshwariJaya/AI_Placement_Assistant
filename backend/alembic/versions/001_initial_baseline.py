"""Initial baseline schema: institutions, departments, users

Revision ID: 001_initial_baseline
Revises: 
Create Date: 2026-11-04 16:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_baseline'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "placement_app_v2"


def upgrade() -> None:
    # 1. Create user_role_enum in dedicated schema
    user_role_enum = postgresql.ENUM(
        'student', 'tpo', 'recruiter', 'admin',
        name='user_role_enum',
        schema=SCHEMA,
        create_type=False,
    )
    user_role_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create institutions table
    op.create_table(
        'institutions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index(op.f('ix_institutions_code'), 'institutions', ['code'], unique=True, schema=SCHEMA)
    op.create_index(op.f('ix_institutions_id'), 'institutions', ['id'], unique=False, schema=SCHEMA)

    # 3. Create departments table
    op.create_table(
        'departments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('institution_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.ForeignKeyConstraint(['institution_id'], [f'{SCHEMA}.institutions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('institution_id', 'code', name='uq_department_institution_code'),
        schema=SCHEMA,
    )
    op.create_index(op.f('ix_departments_id'), 'departments', ['id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_departments_institution_id'), 'departments', ['institution_id'], unique=False, schema=SCHEMA)

    # 4. Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column(
            'role',
            postgresql.ENUM(
                'student', 'tpo', 'recruiter', 'admin',
                name='user_role_enum',
                schema=SCHEMA,
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('institution_id', sa.Integer(), nullable=True),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('is_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], [f'{SCHEMA}.departments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['institution_id'], [f'{SCHEMA}.institutions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True, schema=SCHEMA)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_users_institution_id'), 'users', ['institution_id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_users_department_id'), 'users', ['department_id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False, schema=SCHEMA)

    # 5. Create student_profiles table
    op.create_table(
        'student_profiles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('roll_number', sa.String(length=50), nullable=False),
        sa.Column('graduation_year', sa.Integer(), nullable=False),
        sa.Column('cgpa', sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column('active_backlogs', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_backlogs', sa.Integer(), server_default='0', nullable=False),
        sa.Column('linkedin_url', sa.String(length=255), nullable=True),
        sa.Column('github_url', sa.String(length=255), nullable=True),
        sa.Column('portfolio_url', sa.String(length=255), nullable=True),
        sa.Column('is_placement_ready', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('cgpa >= 0.0 AND cgpa <= 10.0', name='chk_student_cgpa_range'),
        sa.CheckConstraint('active_backlogs >= 0', name='chk_student_active_backlogs_non_negative'),
        sa.CheckConstraint('total_backlogs >= 0', name='chk_student_total_backlogs_non_negative'),
        sa.ForeignKeyConstraint(['user_id'], [f'{SCHEMA}.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        schema=SCHEMA,
    )
    op.create_index(op.f('ix_student_profiles_id'), 'student_profiles', ['id'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_student_profiles_roll_number'), 'student_profiles', ['roll_number'], unique=True, schema=SCHEMA)
    op.create_index(op.f('ix_student_profiles_graduation_year'), 'student_profiles', ['graduation_year'], unique=False, schema=SCHEMA)
    op.create_index(op.f('ix_student_profiles_user_id'), 'student_profiles', ['user_id'], unique=True, schema=SCHEMA)


def downgrade() -> None:
    op.drop_index(op.f('ix_student_profiles_user_id'), table_name='student_profiles', schema=SCHEMA)
    op.drop_index(op.f('ix_student_profiles_graduation_year'), table_name='student_profiles', schema=SCHEMA)
    op.drop_index(op.f('ix_student_profiles_roll_number'), table_name='student_profiles', schema=SCHEMA)
    op.drop_index(op.f('ix_student_profiles_id'), table_name='student_profiles', schema=SCHEMA)
    op.drop_table('student_profiles', schema=SCHEMA)

    op.drop_index(op.f('ix_users_id'), table_name='users', schema=SCHEMA)
    op.drop_index(op.f('ix_users_department_id'), table_name='users', schema=SCHEMA)
    op.drop_index(op.f('ix_users_institution_id'), table_name='users', schema=SCHEMA)
    op.drop_index(op.f('ix_users_role'), table_name='users', schema=SCHEMA)
    op.drop_index(op.f('ix_users_email'), table_name='users', schema=SCHEMA)
    op.drop_table('users', schema=SCHEMA)

    op.drop_index(op.f('ix_departments_institution_id'), table_name='departments', schema=SCHEMA)
    op.drop_index(op.f('ix_departments_id'), table_name='departments', schema=SCHEMA)
    op.drop_table('departments', schema=SCHEMA)

    op.drop_index(op.f('ix_institutions_id'), table_name='institutions', schema=SCHEMA)
    op.drop_index(op.f('ix_institutions_code'), table_name='institutions', schema=SCHEMA)
    op.drop_table('institutions', schema=SCHEMA)

    user_role_enum = postgresql.ENUM('student', 'tpo', 'recruiter', 'admin', name='user_role_enum', schema=SCHEMA)
    user_role_enum.drop(op.get_bind(), checkfirst=True)

