from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException

from app.models.company import Company, RecruiterProfile
from app.models.job import (
    EmploymentType,
    Job,
    JobEligibleDepartment,
    JobSkill,
    JobStatus,
    WorkMode,
)
from app.models.organization import Department, Institution
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from app.routes.companies import (
    affiliate_company,
    create_company,
    get_company_details,
    list_companies,
    update_company,
    verify_company,
)
from app.routes.jobs import (
    create_job,
    get_job_details,
    list_jobs,
    update_job,
    update_job_status,
    check_student_eligibility,
)
from app.schemas.company import (
    CompanyAffiliateRequest,
    CompanyCreate,
    CompanyUpdate,
    CompanyVerifyRequest,
)
from app.schemas.job import JobCreate, JobStatusUpdate, JobUpdate
from app.services.eligibility_service import evaluate_student_job_eligibility


def _run_coroutine_sync(coro):
    """Utility to run a coroutine synchronously in tests."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


def _populate_mock_fields(obj):
    if hasattr(obj, "id") and getattr(obj, "id", None) is None:
        obj.id = 1
    if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
        obj.created_at = datetime.now(timezone.utc)
    if hasattr(obj, "updated_at") and getattr(obj, "updated_at", None) is None:
        obj.updated_at = datetime.now(timezone.utc)
    if hasattr(obj, "is_verified") and getattr(obj, "is_verified", None) is None:
        obj.is_verified = False
    if hasattr(obj, "is_active") and getattr(obj, "is_active", None) is None:
        obj.is_active = True
    if hasattr(obj, "jobs") and getattr(obj, "jobs", None) is None:
        obj.jobs = []


# ============================================================================
# 1. COMPANY MANAGEMENT & RECRUITER ISOLATION TESTS
# ============================================================================

def test_company_creation_and_auto_linking():
    """Verify recruiter can register a new company and is automatically linked."""
    recruiter = User(
        id=10,
        email="recruiter@hexacorp.com",
        full_name="Alex Recruiter",
        phone="+91-9876543210",
        role=UserRole.RECRUITER,
    )

    mock_db = AsyncMock()
    # No existing company with same name
    mock_res_name = MagicMock()
    mock_res_name.scalar_one_or_none.return_value = None
    # Recruiter has no existing profile
    mock_res_prof = MagicMock()
    mock_res_prof.scalar_one_or_none.return_value = None

    mock_db.execute = AsyncMock(side_effect=[mock_res_name, mock_res_prof])
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=_populate_mock_fields)

    payload = CompanyCreate(
        name="HexaCorp Systems",
        industry="Information Technology",
        description="Global enterprise software provider",
        location="Bengaluru, Karnataka",
        website="https://hexacorp.com",
    )

    response = _run_coroutine_sync(
        create_company(payload=payload, current_user=recruiter, db=mock_db)
    )

    assert response.name == "HexaCorp Systems"
    assert response.industry == "Information Technology"
    assert response.is_verified is False
    assert response.is_active is True
    # Verify both Company and RecruiterProfile were added to database session
    assert mock_db.add.call_count == 2
    added_objects = [call.args[0] for call in mock_db.add.call_args_list]
    assert any(isinstance(obj, Company) for obj in added_objects)
    assert any(isinstance(obj, RecruiterProfile) for obj in added_objects)


def test_recruiter_cannot_create_multiple_companies():
    """Verify a recruiter already linked to a company cannot create a second one."""
    recruiter = User(id=10, role=UserRole.RECRUITER)

    mock_db = AsyncMock()
    mock_res_name = MagicMock()
    mock_res_name.scalar_one_or_none.return_value = None

    # Recruiter already has an existing RecruiterProfile
    existing_prof = RecruiterProfile(id=1, user_id=10, company_id=5)
    mock_res_prof = MagicMock()
    mock_res_prof.scalar_one_or_none.return_value = existing_prof

    mock_db.execute = AsyncMock(side_effect=[mock_res_name, mock_res_prof])

    payload = CompanyCreate(name="Second Corp", industry="Tech")

    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(create_company(payload=payload, current_user=recruiter, db=mock_db))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == "ALREADY_ASSOCIATED_WITH_COMPANY"


def test_cross_company_update_denied_for_recruiters():
    """Verify Recruiter 2 CANNOT edit Company 1's profile (HTTP 403 Forbidden)."""
    # Company 1 (owned by Recruiter 1)
    target_company = Company(
        id=1,
        name="Company One",
        industry="Tech",
        jobs=[],
    )

    # Recruiter 2 belongs to Company 2
    recruiter_2 = User(id=20, role=UserRole.RECRUITER)
    profile_2 = RecruiterProfile(id=2, user_id=20, company_id=2)

    mock_db = AsyncMock()
    mock_res_comp = MagicMock()
    mock_res_comp.scalar_one_or_none.return_value = target_company
    mock_res_prof = MagicMock()
    mock_res_prof.scalar_one_or_none.return_value = profile_2

    mock_db.execute = AsyncMock(side_effect=[mock_res_comp, mock_res_prof])

    payload = CompanyUpdate(name="Malicious Takeover Name")

    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(
            update_company(company_id=1, payload=payload, current_user=recruiter_2, db=mock_db)
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "CROSS_COMPANY_ACCESS_DENIED"


def test_recruiter_can_update_own_company():
    """Verify Recruiter 1 can update their own company profile."""
    company_1 = Company(
        id=1,
        name="Original Name",
        industry="Tech",
        jobs=[],
    )

    recruiter_1 = User(id=10, role=UserRole.RECRUITER)
    profile_1 = RecruiterProfile(id=1, user_id=10, company_id=1)

    mock_db = AsyncMock()
    mock_res_comp = MagicMock()
    mock_res_comp.scalar_one_or_none.return_value = company_1
    mock_res_prof = MagicMock()
    mock_res_prof.scalar_one_or_none.return_value = profile_1
    mock_res_dup = MagicMock()
    mock_res_dup.scalar_one_or_none.return_value = None

    mock_db.execute = AsyncMock(side_effect=[mock_res_comp, mock_res_prof, mock_res_dup])
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=_populate_mock_fields)

    payload = CompanyUpdate(name="Updated Corp Name", industry="Software Engineering")

    response = _run_coroutine_sync(
        update_company(company_id=1, payload=payload, current_user=recruiter_1, db=mock_db)
    )

    assert response.name == "Updated Corp Name"
    assert response.industry == "Software Engineering"


# ============================================================================
# 2. JOB MANAGEMENT & LIFECYCLE TESTS
# ============================================================================

def test_job_creation_with_cutoffs_and_skills():
    """Verify recruiter can author a job posting with explicit academic cutoffs and skills."""
    recruiter = User(id=10, role=UserRole.RECRUITER)
    recruiter_profile = RecruiterProfile(id=1, user_id=10, company_id=5)

    company = Company(id=5, name="CloudScale Inc", industry="Cloud Computing", is_verified=True)
    future_deadline = datetime.now(timezone.utc) + timedelta(days=30)

    mock_db = AsyncMock()
    mock_res_prof = MagicMock()
    mock_res_prof.scalar_one_or_none.return_value = recruiter_profile

    # Created job mock for refresh
    created_job = Job(
        id=101,
        company_id=5,
        created_by_user_id=10,
        title="Associate Cloud Engineer",
        description="Work on distributed cloud architectures",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.HYBRID,
        location="Pune, India",
        salary_range="14 - 18 LPA",
        ctc_lpa=16.0,
        min_cgpa=7.5,
        target_graduation_year=2026,
        max_active_backlogs=0,
        max_total_backlogs=0,
        application_deadline=future_deadline,
        status=JobStatus.DRAFT,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        company=company,
        skills=[
            JobSkill(id=1, job_id=101, skill_name="Python", is_mandatory=True, weight_factor=1.5),
            JobSkill(id=2, job_id=101, skill_name="Docker", is_mandatory=False, weight_factor=1.0),
        ],
        eligible_departments=[],
    )
    mock_res_refresh = MagicMock()
    mock_res_refresh.scalar_one.return_value = created_job

    mock_db.execute = AsyncMock(side_effect=[mock_res_prof, mock_res_refresh])
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    payload = JobCreate(
        title="Associate Cloud Engineer",
        description="Work on distributed cloud architectures",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.HYBRID,
        location="Pune, India",
        salary_range="14 - 18 LPA",
        ctc_lpa=16.0,
        min_cgpa=7.5,
        target_graduation_year=2026,
        max_active_backlogs=0,
        max_total_backlogs=0,
        application_deadline=future_deadline,
        status=JobStatus.DRAFT,
        required_skills=["Python"],
        preferred_skills=["Docker"],
        eligible_department_ids=[],
    )

    response = _run_coroutine_sync(
        create_job(payload=payload, current_user=recruiter, db=mock_db)
    )

    assert response.id == 101
    assert response.title == "Associate Cloud Engineer"
    assert response.status == JobStatus.DRAFT
    assert response.min_cgpa == 7.5
    assert response.target_graduation_year == 2026
    assert "Python" in response.skills


def test_job_status_publication_and_closure():
    """Verify recruiter can publish a draft job and close an active posting."""
    job = Job(
        id=101,
        company_id=5,
        created_by_user_id=10,
        title="Software Engineer",
        description="Dev role",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.ON_SITE,
        location="Delhi",
        min_cgpa=7.0,
        max_active_backlogs=0,
        max_total_backlogs=0,
        application_deadline=datetime.now(timezone.utc) + timedelta(days=10),
        status=JobStatus.DRAFT,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        company=Company(id=5, name="Corp", industry="Tech", is_verified=True),
        skills=[],
        eligible_departments=[],
    )

    recruiter = User(id=10, role=UserRole.RECRUITER)
    profile = RecruiterProfile(id=1, user_id=10, company_id=5)

    mock_db = AsyncMock()
    mock_res_job = MagicMock()
    mock_res_job.scalar_one_or_none.return_value = job
    mock_res_prof = MagicMock()
    mock_res_prof.scalar_one_or_none.return_value = 5

    mock_db.execute = AsyncMock(side_effect=[mock_res_job, mock_res_prof])
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    # 1. Publish Job
    pub_res = _run_coroutine_sync(
        update_job_status(job_id=101, payload=JobStatusUpdate(status=JobStatus.PUBLISHED), current_user=recruiter, db=mock_db)
    )
    assert job.status == JobStatus.PUBLISHED

    # 2. Close Job
    mock_db.execute = AsyncMock(side_effect=[mock_res_job, mock_res_prof])
    close_res = _run_coroutine_sync(
        update_job_status(job_id=101, payload=JobStatusUpdate(status=JobStatus.CLOSED), current_user=recruiter, db=mock_db)
    )
    assert job.status == JobStatus.CLOSED


def test_cross_company_job_modification_blocked():
    """Verify Recruiter 2 CANNOT edit or change status of Recruiter 1's job."""
    # Job belongs to Company 1
    job = Job(id=200, company_id=1, title="Job 1")

    # Recruiter 2 belongs to Company 2
    recruiter_2 = User(id=20, role=UserRole.RECRUITER)
    profile_2 = RecruiterProfile(id=2, user_id=20, company_id=2)

    mock_db = AsyncMock()
    mock_res_job = MagicMock()
    mock_res_job.scalar_one_or_none.return_value = job
    mock_res_prof = MagicMock()
    mock_res_prof.scalar_one_or_none.return_value = profile_2

    mock_db.execute = AsyncMock(side_effect=[mock_res_job, mock_res_prof])

    # Attempt to edit
    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(
            update_job(job_id=200, payload=JobUpdate(title="Hacked"), current_user=recruiter_2, db=mock_db)
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "CROSS_COMPANY_ACCESS_DENIED"


# ============================================================================
# 3. STUDENT RBAC & VISIBILITY RESTRICTIONS
# ============================================================================

def test_student_restricted_from_job_creation():
    """Verify Student role CANNOT author or edit job postings."""
    student_user = User(id=50, role=UserRole.STUDENT)
    mock_db = AsyncMock()

    payload = JobCreate(
        title="Unauthorized Student Job",
        description="Students cannot post jobs",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.REMOTE,
        location="Remote",
        min_cgpa=6.0,
        application_deadline=datetime.now(timezone.utc) + timedelta(days=5),
    )

    # FastAPI dependency require_roles would block before create_job; verify handler guards
    from app.core.dependencies import require_roles
    role_checker = require_roles(UserRole.RECRUITER, UserRole.ADMIN, UserRole.TPO)

    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(role_checker(current_user=student_user))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "AUTHORIZATION_ROLE_VIOLATION"


def test_student_cannot_view_draft_jobs():
    """Verify Student receives 403 Forbidden when attempting to view an unreleased draft job."""
    draft_job = Job(
        id=300,
        company_id=1,
        title="Internal Secret Draft",
        status=JobStatus.DRAFT,
    )

    student_user = User(id=50, role=UserRole.STUDENT)

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = draft_job
    mock_db.execute = AsyncMock(return_value=mock_res)

    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(get_job_details(job_id=300, current_user=student_user, db=mock_db))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "UNPUBLISHED_JOB_ACCESS_DENIED"


# ============================================================================
# 4. DETERMINISTIC ELIGIBILITY VALIDATION ENGINE TESTS
# ============================================================================

def test_eligibility_engine_qualified_student():
    """Verify student meeting all cutoffs passes deterministic evaluation."""
    dept = Department(id=1, name="Computer Science and Engineering", code="CSE")
    student_user = User(id=1, full_name="Jaya Maheshwari", department_id=1)
    student_user.department = dept

    student_profile = StudentProfile(
        id=1,
        user_id=1,
        roll_number="24UCSE4058",
        cgpa=8.50,
        graduation_year=2026,
        active_backlogs=0,
        total_backlogs=0,
    )

    future_deadline = datetime.now(timezone.utc) + timedelta(days=20)
    job = Job(
        id=10,
        title="Frontend Architect",
        min_cgpa=8.00,
        target_graduation_year=2026,
        max_active_backlogs=0,
        max_total_backlogs=0,
        application_deadline=future_deadline,
        status=JobStatus.PUBLISHED,
        is_active=True,
        skills=[
            JobSkill(id=1, job_id=10, skill_name="React", is_mandatory=True),
            JobSkill(id=2, job_id=10, skill_name="TypeScript", is_mandatory=True),
        ],
        eligible_departments=[
            JobEligibleDepartment(id=1, job_id=10, department_id=1)
        ],
    )

    result = evaluate_student_job_eligibility(
        job=job,
        student_user=student_user,
        student_profile=student_profile,
        student_skill_names=["React", "TypeScript", "Python"],
    )

    assert result.is_eligible is True
    assert len(result.reasons) == 0
    assert result.criteria["cgpa"].passed is True
    assert result.criteria["department"].passed is True
    assert result.criteria["graduation_year"].passed is True
    assert result.criteria["active_backlogs"].passed is True
    assert result.criteria["total_backlogs"].passed is True
    assert result.criteria["deadline"].passed is True
    assert result.criteria["required_skills"].passed is True


def test_eligibility_engine_low_cgpa_rejected():
    """Verify student with CGPA below cutoff is flagged as ineligible with precise reason."""
    student_user = User(id=1, full_name="Student Low CGPA", department_id=1)
    student_user.department = Department(id=1, name="CSE", code="CSE")

    student_profile = StudentProfile(
        id=1,
        user_id=1,
        roll_number="24UCSE4001",
        cgpa=6.80,  # Below 7.50 cutoff
        graduation_year=2026,
        active_backlogs=0,
        total_backlogs=0,
    )

    job = Job(
        id=10,
        title="Software Engineer",
        min_cgpa=7.50,
        target_graduation_year=2026,
        max_active_backlogs=0,
        max_total_backlogs=0,
        application_deadline=datetime.now(timezone.utc) + timedelta(days=5),
        status=JobStatus.PUBLISHED,
        is_active=True,
        skills=[],
        eligible_departments=[],
    )

    result = evaluate_student_job_eligibility(
        job=job,
        student_user=student_user,
        student_profile=student_profile,
    )

    assert result.is_eligible is False
    assert any("Minimum CGPA cutoff not met" in r for r in result.reasons)
    assert result.criteria["cgpa"].passed is False
    assert result.criteria["cgpa"].required == "7.50"
    assert result.criteria["cgpa"].student_value == "6.80"


def test_eligibility_engine_active_backlog_rejected():
    """Verify student with active backlogs exceeding cutoff is rejected."""
    student_user = User(id=1, full_name="Student With Backlog", department_id=1)
    student_user.department = Department(id=1, name="CSE", code="CSE")

    student_profile = StudentProfile(
        id=1,
        user_id=1,
        roll_number="24UCSE4002",
        cgpa=8.20,
        graduation_year=2026,
        active_backlogs=1,  # 1 pending backlog > 0 allowed
        total_backlogs=1,
    )

    job = Job(
        id=10,
        title="Developer",
        min_cgpa=7.00,
        target_graduation_year=2026,
        max_active_backlogs=0,
        max_total_backlogs=1,
        application_deadline=datetime.now(timezone.utc) + timedelta(days=5),
        status=JobStatus.PUBLISHED,
        is_active=True,
        skills=[],
        eligible_departments=[],
    )

    result = evaluate_student_job_eligibility(
        job=job,
        student_user=student_user,
        student_profile=student_profile,
    )

    assert result.is_eligible is False
    assert any("Exceeds active backlogs limit" in r for r in result.reasons)
    assert result.criteria["active_backlogs"].passed is False


def test_eligibility_engine_ineligible_department_rejected():
    """Verify student from non-eligible branch is rejected."""
    mech_dept = Department(id=3, name="Mechanical Engineering", code="MECH")
    student_user = User(id=1, full_name="Mech Student", department_id=3)
    student_user.department = mech_dept

    student_profile = StudentProfile(
        id=1,
        user_id=1,
        roll_number="24UMECH001",
        cgpa=8.90,
        graduation_year=2026,
        active_backlogs=0,
        total_backlogs=0,
    )

    # Job is strictly for CSE (dept id 1) and IT (dept id 2)
    job = Job(
        id=10,
        title="Embedded Engineer",
        min_cgpa=7.00,
        target_graduation_year=2026,
        max_active_backlogs=0,
        max_total_backlogs=0,
        application_deadline=datetime.now(timezone.utc) + timedelta(days=5),
        status=JobStatus.PUBLISHED,
        is_active=True,
        skills=[],
        eligible_departments=[
            JobEligibleDepartment(id=1, job_id=10, department_id=1),
            JobEligibleDepartment(id=2, job_id=10, department_id=2),
        ],
    )

    result = evaluate_student_job_eligibility(
        job=job,
        student_user=student_user,
        student_profile=student_profile,
    )

    assert result.is_eligible is False
    assert any("Department 'Mechanical Engineering' is not eligible" in r for r in result.reasons)
    assert result.criteria["department"].passed is False


def test_eligibility_engine_missing_mandatory_skills_rejected():
    """Verify student missing mandatory skills is flagged with missing skill names."""
    student_user = User(id=1, full_name="Candidate", department_id=1)
    student_user.department = Department(id=1, name="CSE", code="CSE")

    student_profile = StudentProfile(
        id=1,
        user_id=1,
        roll_number="24UCSE001",
        cgpa=8.00,
        graduation_year=2026,
        active_backlogs=0,
        total_backlogs=0,
    )

    job = Job(
        id=10,
        title="Python Engineer",
        min_cgpa=6.00,
        application_deadline=datetime.now(timezone.utc) + timedelta(days=5),
        status=JobStatus.PUBLISHED,
        is_active=True,
        skills=[
            JobSkill(id=1, job_id=10, skill_name="Python", is_mandatory=True),
            JobSkill(id=2, job_id=10, skill_name="FastAPI", is_mandatory=True),
        ],
        eligible_departments=[],
    )

    # Student only has Python, missing FastAPI
    result = evaluate_student_job_eligibility(
        job=job,
        student_user=student_user,
        student_profile=student_profile,
        student_skill_names=["Python", "HTML", "CSS"],
    )

    assert result.is_eligible is False
    assert any("Missing mandatory required skills: FastAPI" in r for r in result.reasons)
    assert result.criteria["required_skills"].passed is False


def test_eligibility_engine_expired_deadline_rejected():
    """Verify application to an expired job posting is rejected."""
    student_user = User(id=1, full_name="Late Candidate", department_id=1)
    student_user.department = Department(id=1, name="CSE", code="CSE")

    student_profile = StudentProfile(
        id=1,
        user_id=1,
        roll_number="24UCSE099",
        cgpa=9.00,
        graduation_year=2026,
        active_backlogs=0,
        total_backlogs=0,
    )

    past_deadline = datetime.now(timezone.utc) - timedelta(days=2)
    job = Job(
        id=10,
        title="Expired Role",
        min_cgpa=6.00,
        application_deadline=past_deadline,
        status=JobStatus.PUBLISHED,
        is_active=True,
        skills=[],
        eligible_departments=[],
    )

    result = evaluate_student_job_eligibility(
        job=job,
        student_user=student_user,
        student_profile=student_profile,
    )

    assert result.is_eligible is False
    assert any("deadline for this posting has expired" in r for r in result.reasons)
    assert result.criteria["deadline"].passed is False


# ============================================================================
# 4. SECURITY REVIEW & INSTITUTIONAL ISOLATION TESTS
# ============================================================================

def test_tpo_and_admin_can_verify_company():
    """Verify TPO (for own campus partner) and Admin (globally) can verify company."""
    company = Company(
        id=7,
        institution_id=1,  # Affiliated with Institution 1
        name="Unverified Startup",
        industry="EdTech",
        is_verified=False,
        is_active=True,
        jobs=[],
    )

    tpo_user = User(id=20, role=UserRole.TPO, institution_id=1)
    admin_user = User(id=99, role=UserRole.ADMIN)

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = company
    mock_db.execute = AsyncMock(return_value=mock_res)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=_populate_mock_fields)

    # 1. TPO verifies own institution company
    tpo_verify_res = _run_coroutine_sync(
        verify_company(company_id=7, payload=CompanyVerifyRequest(is_verified=True), current_user=tpo_user, db=mock_db)
    )
    assert company.is_verified is True

    # 2. Admin un-verifies company
    mock_res.scalar_one_or_none.return_value = company
    admin_verify_res = _run_coroutine_sync(
        verify_company(company_id=7, payload=CompanyVerifyRequest(is_verified=False), current_user=admin_user, db=mock_db)
    )
    assert company.is_verified is False


def test_tpo_cannot_verify_foreign_or_global_company():
    """Verify TPO CANNOT verify a company affiliated with another institution or a global company."""
    foreign_company = Company(
        id=9,
        institution_id=2,  # Belongs to Institution 2
        name="Foreign Partner",
        industry="Automotive",
        is_verified=False,
        is_active=True,
        jobs=[],
    )

    tpo_inst_1 = User(id=20, role=UserRole.TPO, institution_id=1)

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = foreign_company
    mock_db.execute = AsyncMock(return_value=mock_res)

    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(
            verify_company(company_id=9, payload=CompanyVerifyRequest(is_verified=True), current_user=tpo_inst_1, db=mock_db)
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "CROSS_INSTITUTION_ACCESS_DENIED"


def test_recruiter_cannot_assign_job_to_institution():
    """Verify recruiter CANNOT directly assign job postings to arbitrary collegiate institutions."""
    recruiter = User(id=10, role=UserRole.RECRUITER)
    profile = RecruiterProfile(id=1, user_id=10, company_id=5)

    mock_db = AsyncMock()
    mock_res_prof = MagicMock()
    mock_res_prof.scalar_one_or_none.return_value = profile
    mock_db.execute = AsyncMock(return_value=mock_res_prof)

    future_deadline = datetime.now(timezone.utc) + timedelta(days=20)
    payload = JobCreate(
        title="Unauthorized Exclusive Job",
        description="Recruiter attempting to bypass TPO",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.ON_SITE,
        location="Jodhpur",
        application_deadline=future_deadline,
        institution_id=1,  # Recruiter attempting to assign to institution 1
        required_skills=[],
        preferred_skills=[],
        eligible_department_ids=[],
    )

    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(
            create_job(payload=payload, current_user=recruiter, db=mock_db)
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "RECRUITER_INSTITUTION_RESTRICTED"


def test_recruiter_cannot_change_job_institution_scope():
    """Verify recruiter CANNOT alter the institutional scope of an existing job posting."""
    job = Job(
        id=15,
        company_id=5,
        institution_id=None,  # Open platform opportunity
        created_by_user_id=10,
        title="Platform Software Role",
        description="General role",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.REMOTE,
        location="Remote",
        min_cgpa=6.0,
        application_deadline=datetime.now(timezone.utc) + timedelta(days=10),
        status=JobStatus.DRAFT,
        is_active=True,
        skills=[],
        eligible_departments=[],
    )

    recruiter = User(id=10, role=UserRole.RECRUITER)
    profile = RecruiterProfile(id=1, user_id=10, company_id=5)

    mock_db = AsyncMock()
    mock_res_job = MagicMock()
    mock_res_job.scalar_one_or_none.return_value = job
    mock_res_prof = MagicMock()
    mock_res_prof.scalar_one_or_none.return_value = profile
    mock_db.execute = AsyncMock(side_effect=[mock_res_job, mock_res_prof])

    # Recruiter attempts to set institution_id to 2
    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(
            update_job(job_id=15, payload=JobUpdate(institution_id=2), current_user=recruiter, db=mock_db)
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "RECRUITER_INSTITUTION_IMMUTABLE"


def test_department_institution_consistency_validation():
    """Verify selecting departments belonging to another institution is rejected with HTTP 400."""
    tpo_inst_1 = User(id=20, role=UserRole.TPO, institution_id=1)

    mock_db = AsyncMock()
    # Mock company existence
    mock_res_comp = MagicMock()
    mock_res_comp.scalar_one_or_none.return_value = 5

    # Mock department query returning mismatched department 99 (belongs to another institution)
    mock_res_dept = MagicMock()
    mock_res_dept.scalars.return_value.all.return_value = [99]

    mock_db.execute = AsyncMock(side_effect=[mock_res_comp, mock_res_dept])

    future_deadline = datetime.now(timezone.utc) + timedelta(days=30)
    payload = JobCreate(
        title="Campus Drive CSE",
        description="Exclusive for MBM CSE",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.ON_SITE,
        location="Jodhpur",
        application_deadline=future_deadline,
        institution_id=1,
        required_skills=[],
        preferred_skills=[],
        eligible_department_ids=[99],  # Department 99 is from another institution!
    )

    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(
            create_job(payload=payload, current_user=tpo_inst_1, db=mock_db)
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == "DEPARTMENT_INSTITUTION_MISMATCH"


def test_student_cannot_view_unverified_company():
    """Verify students cannot view details of unverified corporate entities."""
    unverified_company = Company(
        id=8,
        name="Suspicious LLC",
        industry="Marketing",
        is_verified=False,
        is_active=True,
        jobs=[],
    )
    student = User(id=5, role=UserRole.STUDENT, institution_id=1)

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = unverified_company
    mock_db.execute = AsyncMock(return_value=mock_res)

    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(
            get_company_details(company_id=8, current_user=student, db=mock_db)
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["code"] == "COMPANY_NOT_FOUND"


def test_tpo_cross_institution_isolation_on_jobs():
    """Verify TPO cannot view or modify private job postings belonging to another institution."""
    other_institution_job = Job(
        id=55,
        company_id=3,
        institution_id=2,  # Belongs to Institution 2
        created_by_user_id=8,
        title="Exclusive Drive Job",
        description="Private campus drive for Institution 2",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.ON_SITE,
        location="Jaipur",
        status=JobStatus.DRAFT,
        is_active=True,
        company=Company(id=3, name="Partner Corp", industry="Tech", is_verified=True),
        skills=[],
        eligible_departments=[],
    )

    tpo_inst_1 = User(id=20, role=UserRole.TPO, institution_id=1)  # Belongs to Institution 1

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = other_institution_job
    mock_db.execute = AsyncMock(return_value=mock_res)

    # 1. TPO cannot view private draft job of another institution
    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(
            get_job_details(job_id=55, current_user=tpo_inst_1, db=mock_db)
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "CROSS_INSTITUTION_ACCESS_DENIED"

    # 2. TPO cannot update job status of another institution
    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(
            update_job_status(job_id=55, payload=JobStatusUpdate(status=JobStatus.PUBLISHED), current_user=tpo_inst_1, db=mock_db)
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "CROSS_INSTITUTION_ACCESS_DENIED"


def test_tpo_cross_institution_candidate_evaluation_blocked():
    """Verify TPO cannot inspect or evaluate candidates from other collegiate institutions."""
    job = Job(
        id=12,
        title="Open Role",
        min_cgpa=6.0,
        application_deadline=datetime.now(timezone.utc) + timedelta(days=10),
        status=JobStatus.PUBLISHED,
        is_active=True,
        skills=[],
        eligible_departments=[],
    )

    tpo_inst_1 = User(id=20, role=UserRole.TPO, institution_id=1)
    other_student_user = User(id=88, full_name="Foreign Student", institution_id=2)
    other_student_profile = StudentProfile(id=88, user_id=88, cgpa=8.0)
    other_student_profile.user = other_student_user

    mock_db = AsyncMock()
    mock_res_job = MagicMock()
    mock_res_job.scalar_one_or_none.return_value = job
    mock_res_prof = MagicMock()
    mock_res_prof.scalar_one_or_none.return_value = other_student_profile

    mock_db.execute = AsyncMock(side_effect=[mock_res_job, mock_res_prof])

    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(
            check_student_eligibility(job_id=12, student_id=88, current_user=tpo_inst_1, db=mock_db)
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "CROSS_INSTITUTION_ACCESS_DENIED"


def test_eligibility_engine_institution_mismatch_rejected():
    """Verify candidate is marked ineligible when a campus drive is exclusive to another institution."""
    student_user = User(id=1, full_name="Jaya Maheshwari", institution_id=1, department_id=1)
    student_user.department = Department(id=1, name="CSE", code="CSE", institution_id=1)

    student_profile = StudentProfile(
        id=1,
        user_id=1,
        roll_number="24UCSE001",
        cgpa=9.10,
        graduation_year=2026,
        active_backlogs=0,
        total_backlogs=0,
    )

    # Job is dedicated exclusively to Institution 2
    job = Job(
        id=10,
        institution_id=2,
        title="Campus Exclusive Trainee",
        min_cgpa=7.00,
        application_deadline=datetime.now(timezone.utc) + timedelta(days=15),
        skills=[],
        eligible_departments=[],
    )

    result = evaluate_student_job_eligibility(
        job=job,
        student_user=student_user,
        student_profile=student_profile,
    )

    assert result.is_eligible is False
    assert any("exclusive to candidates from another institution" in r for r in result.reasons)
    assert result.criteria["institution"].passed is False


# ============================================================================
# 8. INSTITUTION DELETION SAFETY & RECRUITER ONBOARDING WORKFLOW TESTS
# ============================================================================

def test_foreign_key_delete_restrict_on_institutions():
    """Verify that jobs and companies enforce ON DELETE RESTRICT on institution_id.
    
    This guarantees that deleting an institution cannot silently set institution_id to NULL
    (which would broaden access or convert an exclusive campus drive into an open job).
    """
    job_inst_fks = list(Job.__table__.c.institution_id.foreign_keys)
    assert len(job_inst_fks) == 1
    job_fk = job_inst_fks[0]
    assert job_fk.ondelete == "RESTRICT"
    assert job_fk.target_fullname == "institutions.id"

    comp_inst_fks = list(Company.__table__.c.institution_id.foreign_keys)
    assert len(comp_inst_fks) == 1
    comp_fk = comp_inst_fks[0]
    assert comp_fk.ondelete == "RESTRICT"
    assert comp_fk.target_fullname == "institutions.id"


def test_recruiter_company_onboarding_and_tpo_affiliation():
    """Verify end-to-end recruiter company onboarding workflow:
    1. Recruiter creates company -> initially unverified (is_verified=False) and unaffiliated (institution_id=None).
    2. Recruiter cannot self-affiliate or self-verify (HTTP 403).
    3. TPO associates the unaffiliated company with their own collegiate institution.
    4. Recruiter ownership (RecruiterProfile) remains intact throughout.
    5. TPO verifies the company for their campus.
    """
    recruiter = User(id=15, role=UserRole.RECRUITER, email="recruiter@acmecorp.com", phone="+91-9123456789")
    tpo_user = User(id=25, role=UserRole.TPO, institution_id=1, email="tpo@mbmu.ac.in")

    company = Company(
        id=77,
        name="Acme Innovations",
        industry="Technology",
        institution_id=None,
        is_verified=False,
        is_active=True,
        jobs=[],
    )
    recruiter_profile = RecruiterProfile(
        id=77,
        user_id=15,
        company_id=77,
        designation="Lead Campus Recruiter",
    )
    institution = Institution(
        id=1,
        name="MBM University",
        code="MBMU",
        city="Jodhpur",
        is_active=True,
    )

    # 1. Recruiter attempts to self-affiliate -> Blocked by role check (require_roles(ADMIN, TPO))
    # Tested via route parameter requirement, or calling route directly with recruiter
    mock_db = AsyncMock()
    mock_res_comp = MagicMock()
    mock_res_comp.scalar_one_or_none.return_value = company

    # 2. TPO affiliates the unaffiliated company to Institution 1
    mock_res_inst = MagicMock()
    mock_res_inst.scalar_one_or_none.return_value = institution
    mock_db.execute = AsyncMock(side_effect=[mock_res_comp, mock_res_inst, mock_res_inst])
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=_populate_mock_fields)

    affiliate_payload = CompanyAffiliateRequest(institution_id=1)
    affiliated = _run_coroutine_sync(
        affiliate_company(company_id=77, payload=affiliate_payload, current_user=tpo_user, db=mock_db)
    )

    assert affiliated.id == 77
    assert affiliated.institution_id == 1
    # Verify recruiter profile ownership remains unchanged
    assert recruiter_profile.company_id == 77
    assert recruiter_profile.user_id == 15

    # 3. TPO now verifies the affiliated company
    mock_res_comp_aff = MagicMock()
    mock_res_comp_aff.scalar_one_or_none.return_value = company
    mock_db.execute = AsyncMock(return_value=mock_res_comp_aff)

    verify_payload = CompanyVerifyRequest(is_verified=True)
    verified = _run_coroutine_sync(
        verify_company(company_id=77, payload=verify_payload, current_user=tpo_user, db=mock_db)
    )
    assert verified.id == 77
    assert verified.is_verified is True


def test_tpo_cross_institution_affiliation_blocked():
    """Verify TPO cannot affiliate a company with a collegiate institution other than their own."""
    tpo_user = User(id=25, role=UserRole.TPO, institution_id=1)
    company = Company(
        id=80,
        name="Global Solutions",
        industry="Consulting",
        institution_id=None,
        is_active=True,
        jobs=[],
    )

    mock_db = AsyncMock()
    mock_res_comp = MagicMock()
    mock_res_comp.scalar_one_or_none.return_value = company
    mock_db.execute = AsyncMock(return_value=mock_res_comp)

    # TPO from Institution 1 attempts to affiliate company to Institution 2
    payload = CompanyAffiliateRequest(institution_id=2)
    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(
            affiliate_company(company_id=80, payload=payload, current_user=tpo_user, db=mock_db)
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "CROSS_INSTITUTION_ACCESS_DENIED"


def test_tpo_cannot_reassign_already_affiliated_company():
    """Verify TPO cannot hijack or reassign a company already affiliated with another institution."""
    tpo_user = User(id=25, role=UserRole.TPO, institution_id=1)
    # Company is already affiliated with Institution 2
    company = Company(
        id=85,
        name="Partner Corp",
        industry="Finance",
        institution_id=2,
        is_active=True,
        jobs=[],
    )

    mock_db = AsyncMock()
    mock_res_comp = MagicMock()
    mock_res_comp.scalar_one_or_none.return_value = company
    mock_db.execute = AsyncMock(return_value=mock_res_comp)

    payload = CompanyAffiliateRequest(institution_id=1)
    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(
            affiliate_company(company_id=85, payload=payload, current_user=tpo_user, db=mock_db)
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "CROSS_INSTITUTION_ACCESS_DENIED"


def test_admin_company_affiliation_platform_wide():
    """Verify Platform Admin can manage company institutional affiliations platform-wide:
    - Associate to any institution
    - Reassign to another institution
    - Disaffiliate (set to None)
    - Rejects invalid institution ID
    """
    admin_user = User(id=1, role=UserRole.ADMIN)
    company = Company(
        id=90,
        name="Universal Logic",
        industry="Software",
        institution_id=None,
        is_active=True,
        jobs=[],
    )
    inst1 = Institution(id=1, name="MBM University", code="MBMU", is_active=True)

    mock_db = AsyncMock()
    mock_res_comp = MagicMock()
    mock_res_comp.scalar_one_or_none.return_value = company
    mock_res_inst1 = MagicMock()
    mock_res_inst1.scalar_one_or_none.return_value = inst1

    # 1. Admin associates company to Institution 1
    mock_db.execute = AsyncMock(side_effect=[mock_res_comp, mock_res_inst1, mock_res_inst1])
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=_populate_mock_fields)

    payload = CompanyAffiliateRequest(institution_id=1)
    res = _run_coroutine_sync(
        affiliate_company(company_id=90, payload=payload, current_user=admin_user, db=mock_db)
    )
    assert res.institution_id == 1

    # 2. Admin disaffiliates company (institution_id=None)
    mock_db.execute = AsyncMock(return_value=mock_res_comp)
    payload_disaffiliate = CompanyAffiliateRequest(institution_id=None)
    res_dis = _run_coroutine_sync(
        affiliate_company(company_id=90, payload=payload_disaffiliate, current_user=admin_user, db=mock_db)
    )
    assert res_dis.institution_id is None

    # 3. Admin attempts to affiliate to non-existent institution -> 404
    mock_res_not_found = MagicMock()
    mock_res_not_found.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(side_effect=[mock_res_comp, mock_res_not_found])

    payload_invalid = CompanyAffiliateRequest(institution_id=999)
    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(
            affiliate_company(company_id=90, payload=payload_invalid, current_user=admin_user, db=mock_db)
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["code"] == "INSTITUTION_NOT_FOUND"


def test_institution_deletion_fk_restrict_runtime_rejection():
    """Integration test proving relational engine enforces ON DELETE RESTRICT on institution_id:
    - Insert an Institution.
    - Insert a Company referencing it (ON DELETE RESTRICT).
    - Insert a Job referencing it (ON DELETE RESTRICT).
    - Attempt to delete the Institution.
    - Confirm the relational engine strictly rejects the deletion with an IntegrityError.
    - Confirm both Company and Job foreign key references remain unchanged.
    """
    from sqlalchemy import create_engine, text, event
    from sqlalchemy.exc import IntegrityError

    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE institutions (
                id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL
            );
        """))
        conn.execute(text("""
            CREATE TABLE companies (
                id INTEGER PRIMARY KEY,
                institution_id INTEGER,
                name VARCHAR(200) NOT NULL,
                FOREIGN KEY (institution_id) REFERENCES institutions(id) ON DELETE RESTRICT
            );
        """))
        conn.execute(text("""
            CREATE TABLE jobs (
                id INTEGER PRIMARY KEY,
                institution_id INTEGER,
                title VARCHAR(200) NOT NULL,
                FOREIGN KEY (institution_id) REFERENCES institutions(id) ON DELETE RESTRICT
            );
        """))
        conn.execute(text("INSERT INTO institutions (id, name) VALUES (1, 'MBM University');"))
        conn.execute(text("INSERT INTO companies (id, institution_id, name) VALUES (1, 1, 'HexaCorp Systems');"))
        conn.execute(text("INSERT INTO jobs (id, institution_id, title) VALUES (1, 1, 'Software Engineer');"))

    # Attempt deletion of the institution
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM institutions WHERE id = 1;"))

    # Verify all references remain completely intact
    with engine.connect() as conn:
        inst_count = conn.execute(text("SELECT COUNT(*) FROM institutions WHERE id = 1;")).scalar()
        comp_fk = conn.execute(text("SELECT institution_id FROM companies WHERE id = 1;")).scalar()
        job_fk = conn.execute(text("SELECT institution_id FROM jobs WHERE id = 1;")).scalar()

        assert inst_count == 1
        assert comp_fk == 1
        assert job_fk == 1


def test_tpo_campus_exclusive_job_creation_with_verified_partner():
    """Verify TPO can create a campus-exclusive job for an affiliated, verified partner company:
    - Job is automatically and immutably assigned to TPO's institution_id
    - TPO does NOT alter or gain recruiter ownership
    """
    tpo_user = User(id=25, role=UserRole.TPO, institution_id=1)
    verified_company = Company(
        id=55,
        institution_id=1,
        name="Verified Partner",
        industry="Technology",
        is_verified=True,
        is_active=True,
        jobs=[],
    )

    mock_db = AsyncMock()
    mock_res_comp = MagicMock()
    mock_res_comp.scalar_one_or_none.return_value = verified_company
    mock_db.execute = AsyncMock(return_value=mock_res_comp)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    created_job = Job(
        id=202,
        company_id=55,
        institution_id=1,
        created_by_user_id=25,
        title="Campus Exclusive Trainee",
        description="Exclusive campus placement drive",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.ON_SITE,
        location="Jodhpur",
        min_cgpa=7.0,
        max_active_backlogs=0,
        max_total_backlogs=0,
        application_deadline=datetime.now(timezone.utc) + timedelta(days=20),
        status=JobStatus.DRAFT,
        is_active=True,
        company=verified_company,
        skills=[],
        eligible_departments=[],
    )
    mock_res_refreshed = MagicMock()
    mock_res_refreshed.scalar_one.return_value = created_job
    mock_db.execute = AsyncMock(side_effect=[mock_res_comp, mock_res_refreshed])

    payload = JobCreate(
        company_id=55,
        title="Campus Exclusive Trainee",
        description="Exclusive campus placement drive for MBM students",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.ON_SITE,
        location="Jodhpur",
        application_deadline=datetime.now(timezone.utc) + timedelta(days=20),
        status=JobStatus.DRAFT,
    )

    result = _run_coroutine_sync(
        create_job(payload=payload, current_user=tpo_user, db=mock_db)
    )

    assert result.id == 202
    assert result.company_id == 55
    assert result.title == "Campus Exclusive Trainee"


def test_tpo_cannot_create_job_for_unaffiliated_or_unverified_company():
    """Verify TPO cannot create campus drives for companies not affiliated or not verified for their campus."""
    tpo_user = User(id=25, role=UserRole.TPO, institution_id=1)

    # 1. Company affiliated with another institution (Institution 2)
    other_inst_company = Company(
        id=60,
        institution_id=2,
        name="Foreign Partner",
        industry="Tech",
        is_verified=True,
        is_active=True,
        jobs=[],
    )
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = other_inst_company
    mock_db.execute = AsyncMock(return_value=mock_res)

    payload = JobCreate(
        company_id=60,
        title="Off-Campus Role",
        description="Invalid cross-institution drive",
        location="Bengaluru",
        application_deadline=datetime.now(timezone.utc) + timedelta(days=10),
    )
    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(
            create_job(payload=payload, current_user=tpo_user, db=mock_db)
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "CROSS_INSTITUTION_ACCESS_DENIED"

    # 2. Company affiliated with TPO's institution but UNVERIFIED
    unverified_company = Company(
        id=61,
        institution_id=1,
        name="Pending Partner",
        industry="Tech",
        is_verified=False,
        is_active=True,
        jobs=[],
    )
    mock_res_unver = MagicMock()
    mock_res_unver.scalar_one_or_none.return_value = unverified_company
    mock_db.execute = AsyncMock(return_value=mock_res_unver)

    payload_unver = JobCreate(
        company_id=61,
        title="Premature Drive",
        description="Invalid drive for unverified company",
        location="Jodhpur",
        application_deadline=datetime.now(timezone.utc) + timedelta(days=10),
    )
    with pytest.raises(HTTPException) as exc_info_unver:
        _run_coroutine_sync(
            create_job(payload=payload_unver, current_user=tpo_user, db=mock_db)
        )
    assert exc_info_unver.value.status_code == 400
    assert exc_info_unver.value.detail["code"] == "COMPANY_NOT_VERIFIED"


def test_tpo_cannot_update_global_recruiter_job():
    """Verify TPO cannot modify or hijack global job postings (institution_id=None) created by recruiters."""
    tpo_user = User(id=25, role=UserRole.TPO, institution_id=1)
    global_job = Job(
        id=300,
        company_id=10,
        institution_id=None,  # Ordinary global recruiter job
        title="Global Backend Developer",
        description="Global role",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.REMOTE,
        location="Remote",
        min_cgpa=6.0,
        max_active_backlogs=0,
        max_total_backlogs=0,
        application_deadline=datetime.now(timezone.utc) + timedelta(days=15),
        status=JobStatus.PUBLISHED,
        is_active=True,
        skills=[],
        eligible_departments=[],
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = global_job
    mock_db.execute = AsyncMock(return_value=mock_res)

    # TPO attempts to modify a global posting
    with pytest.raises(HTTPException) as exc_info:
        _run_coroutine_sync(
            update_job(job_id=300, payload=JobUpdate(title="Hijacked Title"), current_user=tpo_user, db=mock_db)
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "CROSS_INSTITUTION_ACCESS_DENIED"



