"""Verify Alembic configuration and migration generation."""
import subprocess
import sys
from pathlib import Path


def test_alembic_offline_sql_generation():
    root_dir = Path(__file__).resolve().parents[2]
    alembic_ini = root_dir / "backend" / "alembic.ini"
    python_exe = sys.executable

    cmd = [
        python_exe,
        "-m",
        "alembic",
        "-c",
        str(alembic_ini),
        "upgrade",
        "head",
        "--sql",
    ]

    result = subprocess.run(
        cmd,
        cwd=str(root_dir),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Alembic failed with error:\n{result.stderr}"
    sql_output = result.stdout
    assert "CREATE TABLE placement_app_v2.institutions" in sql_output or "CREATE TABLE institutions" in sql_output
    assert "CREATE TABLE placement_app_v2.departments" in sql_output or "CREATE TABLE departments" in sql_output
    assert "CREATE TABLE placement_app_v2.users" in sql_output or "CREATE TABLE users" in sql_output
    assert "CREATE TABLE placement_app_v2.student_profiles" in sql_output or "CREATE TABLE student_profiles" in sql_output
    assert "placement_app_v2.alembic_version" in sql_output
    assert "001_initial_baseline" in sql_output
    assert "002_refresh_token_revocation" in sql_output
    assert "refresh_tokens" in sql_output
    assert "003_resume_intelligence" in sql_output
    assert "student_education" in sql_output
    assert "student_skills" in sql_output
    assert "student_projects" in sql_output
    assert "student_experiences" in sql_output
    assert "student_certifications" in sql_output
    assert "resumes" in sql_output
    assert "006_ai_mock_interview_studio" in sql_output
    assert "mock_interview_sessions" in sql_output
    assert "mock_interview_questions" in sql_output
    assert "mock_interview_answers" in sql_output
    assert "mock_interview_evaluations" in sql_output
    assert "007_placement_readiness_analytics" in sql_output
    assert "readiness_snapshots" in sql_output
    assert "readiness_category_enum" in sql_output

