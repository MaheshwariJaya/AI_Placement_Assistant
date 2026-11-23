"""Add MCQ format support and 30/50 question test capacity to AI mock interview studio.

Revision ID: 015_add_mcq_support_to_mock_interview
Revises: 014_centralized_audit_logging
Create Date: 2026-11-14 11:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "015_add_mcq_support_to_mock_interview"
down_revision: Union[str, None] = "014_centralized_audit_logging"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA_NAME = "placement_app_v2"


def upgrade() -> None:
    # 1. Expand question_count check constraint on mock_interview_sessions to support up to 100 questions (30 & 50 ques)
    op.drop_constraint(
        "chk_mock_session_question_count",
        "mock_interview_sessions",
        schema=SCHEMA_NAME,
        type_="check",
    )
    op.create_check_constraint(
        "chk_mock_session_question_count",
        "mock_interview_sessions",
        "question_count >= 1 AND question_count <= 100",
        schema=SCHEMA_NAME,
    )

    # 2. Add question_format column to mock_interview_sessions ('conversational' or 'mcq')
    op.add_column(
        "mock_interview_sessions",
        sa.Column(
            "question_format",
            sa.String(length=30),
            server_default="conversational",
            nullable=False,
        ),
        schema=SCHEMA_NAME,
    )

    # 3. Add question_type, options_json, and correct_option_key to mock_interview_questions
    op.add_column(
        "mock_interview_questions",
        sa.Column(
            "question_type",
            sa.String(length=30),
            server_default="open_ended",
            nullable=False,
        ),
        schema=SCHEMA_NAME,
    )
    op.add_column(
        "mock_interview_questions",
        sa.Column(
            "options_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        schema=SCHEMA_NAME,
    )
    op.add_column(
        "mock_interview_questions",
        sa.Column(
            "correct_option_key",
            sa.String(length=10),
            nullable=True,
        ),
        schema=SCHEMA_NAME,
    )

    # 4. Add selected_option_key to mock_interview_answers
    op.add_column(
        "mock_interview_answers",
        sa.Column(
            "selected_option_key",
            sa.String(length=10),
            nullable=True,
        ),
        schema=SCHEMA_NAME,
    )


def downgrade() -> None:
    op.drop_column("mock_interview_answers", "selected_option_key", schema=SCHEMA_NAME)
    op.drop_column("mock_interview_questions", "correct_option_key", schema=SCHEMA_NAME)
    op.drop_column("mock_interview_questions", "options_json", schema=SCHEMA_NAME)
    op.drop_column("mock_interview_questions", "question_type", schema=SCHEMA_NAME)
    op.drop_column("mock_interview_sessions", "question_format", schema=SCHEMA_NAME)

    op.drop_constraint(
        "chk_mock_session_question_count",
        "mock_interview_sessions",
        schema=SCHEMA_NAME,
        type_="check",
    )
    op.create_check_constraint(
        "chk_mock_session_question_count",
        "mock_interview_sessions",
        "question_count >= 1 AND question_count <= 20",
        schema=SCHEMA_NAME,
    )

