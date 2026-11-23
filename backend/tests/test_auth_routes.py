import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.dependencies import require_roles
from app.core.security import validate_password_strength
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    StudentRegistrationData,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.schemas.organization import InstitutionCreate, DepartmentCreate
from app.schemas.student import StudentPortfolioUpdate, StudentAcademicUpdate


def _run_coroutine_sync(coro):
    """Step a coroutine that does not perform pending I/O to completion."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


def test_password_strength_validation_rules():
    """Verify password complexity requirements."""
    # Too short (< 8 chars)
    assert validate_password_strength("Short1!") is not None
    # No digit
    assert "at least one number" in validate_password_strength("NoDigitsHere!")
    # No special char
    assert "at least one special character" in validate_password_strength("NoSpecialChar123")
    # Valid strong passwords
    assert validate_password_strength("ValidPassword123!") is None
    assert validate_password_strength("AnotherStrong@Pass1") is None


def test_student_registration_schema_validation():
    """Verify StudentRegistrationData field constraints."""
    # Valid student academic data
    student_data = StudentRegistrationData(
        roll_number="CS2026-001",
        graduation_year=2026,
        cgpa=9.15,
        active_backlogs=0,
        total_backlogs=0,
    )
    assert student_data.roll_number == "CS2026-001"
    assert student_data.cgpa == 9.15

    # Invalid CGPA (> 10.0)
    with pytest.raises(ValidationError):
        StudentRegistrationData(
            roll_number="CS2026-002",
            graduation_year=2026,
            cgpa=10.5,
        )

    # Invalid CGPA (< 0.0)
    with pytest.raises(ValidationError):
        StudentRegistrationData(
            roll_number="CS2026-003",
            graduation_year=2026,
            cgpa=-1.0,
        )

    # Negative backlogs
    with pytest.raises(ValidationError):
        StudentRegistrationData(
            roll_number="CS2026-004",
            graduation_year=2026,
            cgpa=7.5,
            active_backlogs=-1,
        )


def test_register_request_schema():
    """Verify top-level RegisterRequest schema and role scoping."""
    # Valid Student Registration payload
    req = RegisterRequest(
        email="student@univ.edu",
        password="SecurePassword123!",
        full_name="John Student",
        role=UserRole.STUDENT,
        institution_id=1,
        department_id=2,
        student_data=StudentRegistrationData(
            roll_number="ROLL-123",
            graduation_year=2026,
            cgpa=8.2,
        ),
    )
    assert req.email == "student@univ.edu"
    assert req.role == UserRole.STUDENT
    assert req.institution_id == 1
    assert req.department_id == 2

    # Valid Recruiter payload (department_id and student_data omitted)
    recruiter_req = RegisterRequest(
        email="recruiter@techcorp.com",
        password="SecurePassword123!",
        full_name="Jane Recruiter",
        role=UserRole.RECRUITER,
    )
    assert recruiter_req.role == UserRole.RECRUITER
    assert recruiter_req.department_id is None
    assert recruiter_req.student_data is None

    # Invalid Email format
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="invalid-email-format",
            password="SecurePassword123!",
            full_name="Invalid Email",
            role=UserRole.STUDENT,
        )


def test_role_based_access_control_dependency_tpo_guard():
    """Verify require_roles guard protects TPO/Admin routes from student access."""
    student_user = User(
        id=1,
        email="student@univ.edu",
        full_name="Student User",
        role=UserRole.STUDENT,
        institution_id=1,
        department_id=1,
        is_active=True,
    )
    tpo_user = User(
        id=2,
        email="tpo@univ.edu",
        full_name="TPO Officer",
        role=UserRole.TPO,
        institution_id=1,
        department_id=None,
        is_active=True,
    )
    admin_user = User(
        id=3,
        email="admin@system.local",
        full_name="System Admin",
        role=UserRole.ADMIN,
        institution_id=None,
        department_id=None,
        is_active=True,
    )

    staff_guard = require_roles(UserRole.TPO, UserRole.ADMIN)

    # 1. Student attempting staff action -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(staff_guard(current_user=student_user))
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "AUTHORIZATION_ROLE_VIOLATION"

    # 2. TPO attempting staff action -> Allowed
    result_tpo = _run_coroutine_sync(staff_guard(current_user=tpo_user))
    assert result_tpo.role == UserRole.TPO

    # 3. Admin attempting staff action -> Allowed
    result_admin = _run_coroutine_sync(staff_guard(current_user=admin_user))
    assert result_admin.role == UserRole.ADMIN


def test_role_based_access_control_dependency_student_guard():
    """Verify require_roles guard permits students and blocks recruiters."""
    student_user = User(
        id=1,
        email="student@univ.edu",
        full_name="Student User",
        role=UserRole.STUDENT,
        institution_id=1,
        department_id=1,
        is_active=True,
    )
    recruiter_user = User(
        id=4,
        email="recruiter@company.com",
        full_name="Company Recruiter",
        role=UserRole.RECRUITER,
        institution_id=None,
        department_id=None,
        is_active=True,
    )

    student_guard = require_roles(UserRole.STUDENT)

    # Student allowed
    allowed = _run_coroutine_sync(student_guard(current_user=student_user))
    assert allowed.role == UserRole.STUDENT

    # Recruiter rejected
    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(student_guard(current_user=recruiter_user))
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "AUTHORIZATION_ROLE_VIOLATION"


def test_academic_and_portfolio_update_schemas():
    """Verify student portfolio vs TPO academic update schemas."""
    # Student portfolio update
    portfolio = StudentPortfolioUpdate(
        linkedin_url="https://linkedin.com/in/teststudent",
        github_url="https://github.com/teststudent",
    )
    assert portfolio.linkedin_url == "https://linkedin.com/in/teststudent"
    assert portfolio.portfolio_url is None

    # TPO academic update
    academic = StudentAcademicUpdate(
        cgpa=8.75,
        active_backlogs=0,
        total_backlogs=1,
        is_placement_ready=True,
    )
    assert academic.cgpa == 8.75
    assert academic.is_placement_ready is True

    # Invalid CGPA update
    with pytest.raises(ValidationError):
        StudentAcademicUpdate(cgpa=11.0)


def test_registration_blocks_privileged_role_self_creation():
    """Verify public registration strictly rejects self-creation of TPO and Admin roles."""
    from app.routes.auth import register

    # 1. Attempting to register as TPO
    tpo_payload = RegisterRequest(
        email="attempt_tpo@college.edu",
        password="SecurePassword123!",
        full_name="Attacker TPO",
        role=UserRole.TPO,
        institution_id=1,
    )
    with pytest.raises(HTTPException) as exc_tpo:
        _run_coroutine_sync(register(payload=tpo_payload, session=None))
    assert exc_tpo.value.status_code == 403
    assert exc_tpo.value.detail["code"] == "PRIVILEGED_ROLE_SELF_REGISTRATION_DENIED"

    # 2. Attempting to register as ADMIN
    admin_payload = RegisterRequest(
        email="attempt_admin@college.edu",
        password="SecurePassword123!",
        full_name="Attacker Admin",
        role=UserRole.ADMIN,
    )
    with pytest.raises(HTTPException) as exc_admin:
        _run_coroutine_sync(register(payload=admin_payload, session=None))
    assert exc_admin.value.status_code == 403
    assert exc_admin.value.detail["code"] == "PRIVILEGED_ROLE_SELF_REGISTRATION_DENIED"


def test_registration_enforces_student_institutional_scoping():
    """Verify students cannot register without institution, department, and academic data."""
    from app.routes.auth import register

    # Missing institution
    p1 = RegisterRequest(
        email="s1@college.edu",
        password="SecurePassword123!",
        full_name="Student 1",
        role=UserRole.STUDENT,
        institution_id=None,
        department_id=1,
        student_data=StudentRegistrationData(roll_number="R1", graduation_year=2026, cgpa=8.0),
    )
    with pytest.raises(HTTPException) as exc1:
        _run_coroutine_sync(register(payload=p1, session=None))
    assert exc1.value.status_code == 400
    assert exc1.value.detail["code"] == "INSTITUTION_REQUIRED"

    # Missing department
    p2 = RegisterRequest(
        email="s2@college.edu",
        password="SecurePassword123!",
        full_name="Student 2",
        role=UserRole.STUDENT,
        institution_id=1,
        department_id=None,
        student_data=StudentRegistrationData(roll_number="R2", graduation_year=2026, cgpa=8.0),
    )
    with pytest.raises(HTTPException) as exc2:
        _run_coroutine_sync(register(payload=p2, session=None))
    assert exc2.value.status_code == 400
    assert exc2.value.detail["code"] == "DEPARTMENT_REQUIRED"

    # Missing student academic details
    p3 = RegisterRequest(
        email="s3@college.edu",
        password="SecurePassword123!",
        full_name="Student 3",
        role=UserRole.STUDENT,
        institution_id=1,
        department_id=1,
        student_data=None,
    )
    with pytest.raises(HTTPException) as exc3:
        _run_coroutine_sync(register(payload=p3, session=None))
    assert exc3.value.status_code == 400
    assert exc3.value.detail["code"] == "STUDENT_DATA_REQUIRED"


def test_recruiter_direct_student_profile_access_denied():
    """Verify recruiters cannot browse student academic profiles directly."""
    from app.routes.users import get_student_profile

    recruiter_user = User(
        id=99,
        email="recruiter@tech.com",
        full_name="Tech Recruiter",
        role=UserRole.RECRUITER,
        is_active=True,
    )
    with pytest.raises(HTTPException) as exc:
        _run_coroutine_sync(get_student_profile(student_id=1, current_user=recruiter_user, session=None))
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "RECRUITER_DIRECT_ACCESS_DENIED"


def test_tpo_cross_institution_department_creation_violation():
    """Verify TPOs cannot create departments in institutions other than their authorized institution."""
    from app.routes.organizations import create_department

    tpo_user = User(
        id=10,
        email="tpo@inst1.edu",
        full_name="TPO Inst 1",
        role=UserRole.TPO,
        institution_id=1,
        is_active=True,
    )
    dept_payload = DepartmentCreate(name="Mechanical Engineering", code="ME")

    # TPO from Inst 1 attempting to create department in Inst 2
    with pytest.raises(HTTPException) as exc:
        _run_coroutine_sync(create_department(
            institution_id=2,
            payload=dept_payload,
            current_user=tpo_user,
            session=None,
        ))
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "INSTITUTION_SCOPING_VIOLATION"


def test_jwt_token_type_separation():
    """Verify access and refresh tokens have distinct types and cannot be transposed."""
    from app.core.security import create_access_token, create_refresh_token, decode_token

    access_token = create_access_token({"sub": "123", "role": "student"})
    refresh_token = create_refresh_token({"sub": "123"})

    access_claims = decode_token(access_token)
    refresh_claims = decode_token(refresh_token)

    assert access_claims["type"] == "access"
    assert refresh_claims["type"] == "refresh"
    assert access_claims["type"] != refresh_claims["type"]


def test_user_role_enum_values_and_model_mapping():
    """Verify UserRole enum values match database representation (lowercase)."""
    from app.models.user import User, UserRole

    # Python enum values must be lowercase to match PostgreSQL user_role_enum
    assert [e.value for e in UserRole] == ["student", "tpo", "recruiter", "admin"]

    # Verify User.role column uses values_callable mapping to lowercase
    user_role_col = User.__table__.columns["role"]
    assert hasattr(user_role_col.type, "enums")
    assert user_role_col.type.enums == ["student", "tpo", "recruiter", "admin"]


def test_change_password_validation_and_update():
    """Verify authenticated password change validates current password, distinctness, strength, and hashes."""
    from unittest.mock import AsyncMock
    from app.core.security import hash_password, verify_password
    from app.routes.auth import change_password
    from app.schemas.auth import ChangePasswordRequest

    user = User(
        id=50,
        email="user@univ.edu",
        full_name="Test User",
        hashed_password=hash_password("OldPass123!"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    session = AsyncMock()

    # Wrong current password
    with pytest.raises(HTTPException) as exc1:
        _run_coroutine_sync(
            change_password(
                payload=ChangePasswordRequest(current_password="Wrong123!", new_password="NewPass456!"),
                current_user=user,
                session=session,
            )
        )
    assert exc1.value.status_code == 400
    assert exc1.value.detail["code"] == "INVALID_CURRENT_PASSWORD"

    # Identical password
    with pytest.raises(HTTPException) as exc2:
        _run_coroutine_sync(
            change_password(
                payload=ChangePasswordRequest(current_password="OldPass123!", new_password="OldPass123!"),
                current_user=user,
                session=session,
            )
        )
    assert exc2.value.status_code == 400
    assert exc2.value.detail["code"] == "SAME_PASSWORD"

    # Weak new password
    with pytest.raises(HTTPException) as exc3:
        _run_coroutine_sync(
            change_password(
                payload=ChangePasswordRequest(current_password="OldPass123!", new_password="weakpassonly"),
                current_user=user,
                session=session,
            )
        )
    assert exc3.value.status_code == 400
    assert exc3.value.detail["code"] == "WEAK_PASSWORD"

    # Valid update
    res = _run_coroutine_sync(
        change_password(
            payload=ChangePasswordRequest(current_password="OldPass123!", new_password="NewStrong789!"),
            current_user=user,
            session=session,
        )
    )
    assert res["success"] is True
    assert verify_password("NewStrong789!", user.hashed_password)
    assert session.commit.called


def test_update_my_user_profile_updates_fields():
    """Verify PUT /users/me updates trimmed full_name and optional cleared phone cleanly."""
    from datetime import datetime, timezone
    from unittest.mock import AsyncMock
    from app.routes.users import update_my_user_profile
    from app.schemas.user import UserUpdateRequest

    user = User(
        id=51,
        email="tpo@univ.edu",
        full_name="Initial Name",
        phone="9999999999",
        role=UserRole.TPO,
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )
    session = AsyncMock()
    res = _run_coroutine_sync(
        update_my_user_profile(
            payload=UserUpdateRequest(full_name="  Updated Officer  ", phone="   "),
            current_user=user,
            session=session,
        )
    )
    assert res.full_name == "Updated Officer"
    assert res.phone is None
    assert session.commit.called



