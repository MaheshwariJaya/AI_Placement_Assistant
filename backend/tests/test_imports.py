"""Test module imports across the stack."""
import pytest


def test_core_imports():
    import fastapi
    import pydantic
    import pydantic_settings
    import sqlalchemy
    import alembic
    import asyncpg
    import fitz  # PyMuPDF
    import docx  # python-docx
    import jwt
    import passlib

    assert fastapi.__version__ is not None
    assert pydantic.__version__ is not None
    assert sqlalchemy.__version__ is not None
    assert fitz.__version__ is not None


def test_app_imports():
    from app.config import get_settings
    from app.core.base import Base
    from app.core.database import engine, get_async_session, check_database_connection
    from app.models import (
        User,
        Institution,
        Department,
        StudentProfile,
        RefreshToken,
        PlacementDrive,
        PlacementDriveJob,
        JobApplication,
        ApplicationStatusHistory,
        Interview,
        Notification,
    )
    from app.main import app

    settings = get_settings()
    assert settings.APP_NAME == "AI-Powered Placement Intelligence System"
    assert app.title == settings.APP_NAME
    table_names = [t.name for t in Base.metadata.tables.values()]
    assert "users" in table_names
    assert "institutions" in table_names
    assert "departments" in table_names
    assert "student_profiles" in table_names
    assert "refresh_tokens" in table_names
    assert "placement_drives" in table_names
    assert "placement_drive_jobs" in table_names
    assert "job_applications" in table_names
    assert "application_status_history" in table_names
    assert "interviews" in table_names
    assert "notifications" in table_names
    assert User.__tablename__ == "users"
    assert Institution.__tablename__ == "institutions"
    assert Department.__tablename__ == "departments"
    assert StudentProfile.__tablename__ == "student_profiles"
    assert RefreshToken.__tablename__ == "refresh_tokens"
    assert PlacementDrive.__tablename__ == "placement_drives"
    assert PlacementDriveJob.__tablename__ == "placement_drive_jobs"
    assert JobApplication.__tablename__ == "job_applications"
    assert ApplicationStatusHistory.__tablename__ == "application_status_history"
    assert Interview.__tablename__ == "interviews"
    assert Notification.__tablename__ == "notifications"

