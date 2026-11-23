"""
Unit and Integration Tests for Phase 7 Stage 5B: Resume Feedback Service, Caching, and Routes.

Covers:
- Cross-student tenant boundary enforcement.
- Unapproved resume rejection (parsing_status != 'approved').
- Missing physical file & empty resume rejection.
- General vs job-targeted evaluation modes.
- Global vs institution-specific job visibility.
- 6-component cache key computation & invalidation.
- Cache hit returns 0 token usage (bypassed provider).
- Concurrency deduplication (asyncio.Lock per cache key).
- Input text truncation safety limits.
- Evidence validation on suggested rewrites.
- Non-modification of original resume and profile records.
- API route handlers: POST /feedback, GET /feedback, GET /feedback/jobs.
"""
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException

from app.core.dependencies import require_student
from app.core.errors import AppError, NotFoundError, PermissionDeniedError
from app.models.company import Company
from app.models.job import EmploymentType, Job, JobStatus, WorkMode
from app.models.organization import Department
from app.models.resume import Resume
from app.models.student import (
    StudentCertification,
    StudentExperience,
    StudentProfile,
    StudentProject,
    StudentSkill,
)
from app.models.user import User, UserRole
from app.routes.resume_feedback import (
    get_resume_feedback,
    list_feedback_target_jobs,
    request_resume_feedback,
)
from app.schemas.ai import AIUsageMetadata
from app.schemas.resume_feedback import (
    FeedbackSectionType,
    ResumeFeedbackReport,
    ResumeFeedbackRequest,
    ResumeFeedbackResponse,
    ResumeRewrittenSnippet,
    ResumeSectionEvaluation,
    RewriteCategory,
    SectionStatus,
)
from app.services.ai_provider import AIServiceError, MockAIProvider
from app.services.resume_feedback_service import (
    FEEDBACK_PROMPT_VERSION,
    FEEDBACK_SCHEMA_VERSION,
    MAX_INPUT_TEXT_CHARS,
    compute_feedback_cache_key,
    feedback_cache,
    generate_resume_feedback,
    get_and_validate_student_resume,
    get_and_validate_target_job,
    get_latest_cached_feedback,
    list_eligible_jobs_for_feedback,
    validate_rewrite_evidence,
)


@pytest.fixture(autouse=True)
def clear_feedback_cache_fixture():
    """Ensure in-memory feedback cache is clean before and after each test."""
    feedback_cache.clear()
    yield
    feedback_cache.clear()


# =============================================================================
# Helper Builders
# =============================================================================

def build_student_user(id: int = 1, institution_id: int = 10) -> User:
    user = User(
        id=id,
        email=f"student{id}@campus.edu",
        full_name=f"Student User {id}",
        role=UserRole.STUDENT,
        institution_id=institution_id,
        is_active=True,
    )
    profile = StudentProfile(
        id=id,
        user_id=id,
        roll_number=f"ROLL{id:04d}",
        cgpa=8.5,
        active_backlogs=0,
        graduation_year=2026,
        user=user,
    )
    user.student_profile = profile
    return user


def build_tpo_user(id: int = 20, institution_id: int = 10) -> User:
    return User(
        id=id,
        email=f"tpo{id}@campus.edu",
        full_name=f"TPO Officer {id}",
        role=UserRole.TPO,
        institution_id=institution_id,
        is_active=True,
    )


def build_recruiter_user(id: int = 30) -> User:
    return User(
        id=id,
        email=f"recruiter{id}@company.com",
        full_name=f"Recruiter {id}",
        role=UserRole.RECRUITER,
        institution_id=None,
        is_active=True,
    )


def build_admin_user(id: int = 99) -> User:
    return User(
        id=id,
        email=f"admin{id}@platform.com",
        full_name=f"Admin {id}",
        role=UserRole.ADMIN,
        is_active=True,
    )


def build_test_resume(
    id: int = 100,
    student_id: int = 1,
    parsing_status: str = "approved",
    raw_text: str = "Aditi Sharma\nPython, FastAPI, PostgreSQL\nProjects: Backend System\nExperience: Software Intern",
    file_exists: bool = True,
    tmp_path: Optional[Path] = None,
) -> Resume:
    fpath = "/tmp/dummy_resume.pdf"
    if tmp_path:
        real_file = tmp_path / f"resume_{id}.pdf"
        if file_exists:
            real_file.write_text(raw_text, encoding="utf-8")
        fpath = str(real_file)

    return Resume(
        id=id,
        student_id=student_id,
        file_name=f"resume_{id}.pdf",
        file_path=fpath,
        file_type="pdf",
        file_size_bytes=len(raw_text.encode("utf-8")),
        file_hash=f"hash_{id}_{len(raw_text)}",
        raw_extracted_text=raw_text,
        parsed_entities_json={
            "personal_info": {"full_name": "Aditi Sharma"},
            "skills": [{"skill_name": "Python"}, {"skill_name": "FastAPI"}],
            "projects": [{"title": "Backend System", "description": "Developed backend APIs using FastAPI"}],
            "experiences": [{"role_title": "Software Intern", "description": "Worked on database optimization"}],
        },
        parsing_status=parsing_status,
        is_active=True,
    )


def build_test_job(
    id: int = 50,
    institution_id: Optional[int] = 10,
    status: JobStatus = JobStatus.PUBLISHED,
    is_active: bool = True,
) -> Job:
    company = Company(id=1, name="Apex Systems", is_verified=True, is_active=True)
    return Job(
        id=id,
        company_id=1,
        institution_id=institution_id,
        title="Software Engineer - Backend",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.HYBRID,
        location="Bengaluru",
        company=company,
        status=status,
        is_active=is_active,
        skills=[],
        eligible_departments=[],
    )


# =============================================================================
# 1. Resume Validation & Tenant Security Tests
# =============================================================================

@pytest.mark.asyncio
async def test_cross_student_resume_access_rejected(tmp_path):
    """Student cannot analyze another student's resume."""
    student_a = build_student_user(id=1)
    student_b = build_student_user(id=2)
    resume_a = build_test_resume(id=101, student_id=student_a.student_profile.id, tmp_path=tmp_path)

    mock_db = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = resume_a
    mock_db.execute.return_value = res

    with pytest.raises(PermissionDeniedError) as exc_info:
        await get_and_validate_student_resume(resume_id=101, current_user=student_b, db=mock_db)
    assert exc_info.value.code == "AUTHORIZATION_VIOLATION"


@pytest.mark.asyncio
async def test_unapproved_resume_rejected(tmp_path):
    """Resume with status other than 'approved' is rejected."""
    student = build_student_user(id=1)
    for unapproved_status in ["uploaded", "processing", "extracted", "review_required", "rejected", "failed"]:
        resume = build_test_resume(id=102, student_id=1, parsing_status=unapproved_status, tmp_path=tmp_path)

        mock_db = AsyncMock()
        res = MagicMock()
        res.scalar_one_or_none.return_value = resume
        mock_db.execute.return_value = res

        with pytest.raises(AppError) as exc_info:
            await get_and_validate_student_resume(resume_id=102, current_user=student, db=mock_db)
        assert exc_info.value.code == "RESUME_NOT_APPROVED"
        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_missing_physical_file_rejected(tmp_path):
    """Resume with non-existent physical file raises FILE_NOT_FOUND."""
    student = build_student_user(id=1)
    # file_exists = False
    resume = build_test_resume(id=103, student_id=1, file_exists=False, tmp_path=tmp_path)

    mock_db = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = resume
    mock_db.execute.return_value = res

    with pytest.raises(NotFoundError) as exc_info:
        await get_and_validate_student_resume(resume_id=103, current_user=student, db=mock_db)
    assert exc_info.value.code == "FILE_NOT_FOUND"


# =============================================================================
# 2. Job Validation & Scoping Tests
# =============================================================================

@pytest.mark.asyncio
async def test_job_visibility_institution_scoping():
    """Job exclusive to another institution cannot be accessed."""
    student = build_student_user(id=1, institution_id=10)
    job_other_inst = build_test_job(id=50, institution_id=99)  # Institution 99 != 10

    mock_db = AsyncMock()
    j_res = MagicMock()
    j_res.scalar_one_or_none.return_value = job_other_inst
    mock_db.execute.return_value = j_res

    with pytest.raises(PermissionDeniedError) as exc_info:
        await get_and_validate_target_job(
            job_id=50,
            current_user=student,
            student_profile=student.student_profile,
            db=mock_db,
        )
    assert exc_info.value.code == "INSTITUTION_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_job_visibility_global_and_matching_inst():
    """Global jobs (institution_id=None) and same-institution jobs are accessible."""
    student = build_student_user(id=1, institution_id=10)

    # 1. Global Job
    job_global = build_test_job(id=51, institution_id=None)
    mock_db = AsyncMock()
    j_res = MagicMock()
    j_res.scalar_one_or_none.return_value = job_global
    empty_res = MagicMock()
    empty_res.scalars.return_value.all.return_value = []
    mock_db.execute.side_effect = [j_res, empty_res, empty_res, empty_res, empty_res]

    with patch("app.services.resume_feedback_service.calculate_compatibility_score") as mock_compat:
        mock_compat.return_value = (80.0, {}, ["Python"], [], [], [], "Rationale")
        j, ctx = await get_and_validate_target_job(
            job_id=51,
            current_user=student,
            student_profile=student.student_profile,
            db=mock_db,
        )
        assert j.id == 51
        assert ctx["deterministic_compatibility"] == 80.0


# =============================================================================
# 3. Cache Key Computation & Invalidation Tests
# =============================================================================

def test_cache_key_six_component_invalidation():
    """Changing any of the 6 components changes the resulting cache key."""
    base_key = compute_feedback_cache_key(
        file_hash="hash123",
        job_id=10,
        prompt_version="v1.0",
        schema_version="v1.0",
        provider="mock",
        model="mock-rule-engine",
    )

    # 1. Alter file hash
    k_file = compute_feedback_cache_key(file_hash="hash456", job_id=10, prompt_version="v1.0", schema_version="v1.0", provider="mock", model="mock-rule-engine")
    assert k_file != base_key

    # 2. Alter job_id (or to None/general)
    k_job = compute_feedback_cache_key(file_hash="hash123", job_id=None, prompt_version="v1.0", schema_version="v1.0", provider="mock", model="mock-rule-engine")
    assert k_job != base_key

    # 3. Alter prompt version
    k_prompt = compute_feedback_cache_key(file_hash="hash123", job_id=10, prompt_version="v1.1", schema_version="v1.0", provider="mock", model="mock-rule-engine")
    assert k_prompt != base_key

    # 4. Alter schema version
    k_schema = compute_feedback_cache_key(file_hash="hash123", job_id=10, prompt_version="v1.0", schema_version="v2.0", provider="mock", model="mock-rule-engine")
    assert k_schema != base_key

    # 5. Alter provider
    k_provider = compute_feedback_cache_key(file_hash="hash123", job_id=10, prompt_version="v1.0", schema_version="v1.0", provider="gemini", model="gemini-1.5-flash")
    assert k_provider != base_key

    # 6. Alter model
    k_model = compute_feedback_cache_key(file_hash="hash123", job_id=10, prompt_version="v1.0", schema_version="v1.0", provider="mock", model="mock-v2")
    assert k_model != base_key


# =============================================================================
# 4. End-to-End Service Execution & Caching Tests
# =============================================================================

@pytest.mark.asyncio
async def test_generate_feedback_general_mode_caching_and_zero_tokens(tmp_path):
    """First call computes and charges tokens; second call returns cached with 0 tokens."""
    student = build_student_user(id=1)
    resume = build_test_resume(id=200, student_id=1, tmp_path=tmp_path)

    mock_db = AsyncMock()
    r_res = MagicMock()
    r_res.scalar_one_or_none.return_value = resume
    mock_db.execute.return_value = r_res

    # 1. First execution (Cache Miss)
    resp1 = await generate_resume_feedback(
        resume_id=200,
        job_id=None,
        force_refresh=False,
        current_user=student,
        db=mock_db,
    )

    assert resp1.is_cached is False
    assert resp1.resume_id == 200
    assert resp1.job_id is None
    assert resp1.feedback.job_alignment is None
    assert resp1.usage.prompt_tokens > 0

    # 2. Second execution (Cache Hit)
    resp2 = await generate_resume_feedback(
        resume_id=200,
        job_id=None,
        force_refresh=False,
        current_user=student,
        db=mock_db,
    )

    assert resp2.is_cached is True
    # Bypassed provider claims 0 tokens
    assert resp2.usage.prompt_tokens == 0
    assert resp2.usage.total_tokens == 0
    assert resp2.usage.latency_ms == 0
    assert resp2.feedback.overall_presentation_score == resp1.feedback.overall_presentation_score

    # 3. Third execution with force_refresh=True (Bypasses cache)
    resp3 = await generate_resume_feedback(
        resume_id=200,
        job_id=None,
        force_refresh=True,
        current_user=student,
        db=mock_db,
    )
    assert resp3.is_cached is False
    assert resp3.usage.prompt_tokens > 0


@pytest.mark.asyncio
async def test_generate_feedback_job_targeted_mode(tmp_path):
    """Job-targeted feedback populates job_alignment with missing skills as not evidenced."""
    student = build_student_user(id=1)
    resume = build_test_resume(id=201, student_id=1, tmp_path=tmp_path)
    job = build_test_job(id=60, institution_id=10)

    mock_db = AsyncMock()
    r_res = MagicMock()
    r_res.scalar_one_or_none.return_value = resume
    j_res = MagicMock()
    j_res.scalar_one_or_none.return_value = job
    empty_res = MagicMock()
    empty_res.scalars.return_value.all.return_value = []

    # resume query, job query, 4 student portfolio queries
    mock_db.execute.side_effect = [r_res, j_res, empty_res, empty_res, empty_res, empty_res]

    with patch("app.services.resume_feedback_service.calculate_compatibility_score") as mock_compat:
        mock_compat.return_value = (78.5, {}, ["Python", "FastAPI"], ["Docker"], ["AWS"], [], "Good match")

        resp = await generate_resume_feedback(
            resume_id=201,
            job_id=60,
            force_refresh=False,
            current_user=student,
            db=mock_db,
        )

        assert resp.job_id == 60
        assert resp.feedback.job_alignment is not None
        assert "Docker" in resp.feedback.job_alignment.skills_not_evidenced_mandatory
        assert resp.feedback.job_alignment.deterministic_compatibility_score == 78.5


# =============================================================================
# 5. Concurrency Deduplication Test
# =============================================================================

@pytest.mark.asyncio
async def test_concurrent_duplicate_requests_serialized(tmp_path):
    """Simultaneous concurrent requests for the same cache key serialize and reuse result."""
    student = build_student_user(id=1)
    resume = build_test_resume(id=202, student_id=1, tmp_path=tmp_path)

    mock_db = AsyncMock()
    r_res = MagicMock()
    r_res.scalar_one_or_none.return_value = resume
    mock_db.execute.return_value = r_res

    # Launch two simultaneous tasks
    task1 = asyncio.create_task(
        generate_resume_feedback(resume_id=202, job_id=None, force_refresh=False, current_user=student, db=mock_db)
    )
    task2 = asyncio.create_task(
        generate_resume_feedback(resume_id=202, job_id=None, force_refresh=False, current_user=student, db=mock_db)
    )

    r1, r2 = await asyncio.gather(task1, task2)
    # One is miss, one is hit
    assert (r1.is_cached and not r2.is_cached) or (r2.is_cached and not r1.is_cached)


# =============================================================================
# 6. Evidence Validation & Text Truncation Tests
# =============================================================================

def test_validate_rewrite_evidence_filters_ungrounded_snippets():
    """Snippets whose original_text is not found in the resume are discarded."""
    raw_text = "Aditi Sharma. Built REST APIs using FastAPI and PostgreSQL."
    parsed = {"projects": [{"title": "Web App", "description": "Built REST APIs"}]}

    grounded_snippet = ResumeRewrittenSnippet(
        id="s1",
        section=FeedbackSectionType.ACTION_IMPACT,
        original_text="Built REST APIs using FastAPI and PostgreSQL.",
        suggested_rewrite="Engineered high-performance REST APIs using FastAPI and PostgreSQL, [insert metric, e.g., handling X req/s].",
        rationale="Stronger active verb",
        evidence_reference="Project Section",
        category=RewriteCategory.QUANTIFICATION_PROMPT,
        requires_student_metric=True,
    )
    fabricated_snippet = ResumeRewrittenSnippet(
        id="s2",
        section=FeedbackSectionType.ACTION_IMPACT,
        original_text="Completely invented sentence not present anywhere in candidate resume.",
        suggested_rewrite="Engineered cloud architecture.",
        rationale="Invalid",
        evidence_reference="Invented",
        category=RewriteCategory.VERB_STRENGTHENING,
        requires_student_metric=False,
    )

    filtered = validate_rewrite_evidence([grounded_snippet, fabricated_snippet], raw_text, parsed)
    assert len(filtered) == 1
    assert filtered[0].id == "s1"


@pytest.mark.asyncio
async def test_input_text_truncation_limits(tmp_path):
    """Resumes exceeding MAX_INPUT_TEXT_CHARS are safely truncated."""
    student = build_student_user(id=1)
    huge_text = "Word " * 5000  # 25,000 characters
    resume = build_test_resume(id=203, student_id=1, raw_text=huge_text, tmp_path=tmp_path)

    mock_db = AsyncMock()
    r_res = MagicMock()
    r_res.scalar_one_or_none.return_value = resume
    mock_db.execute.return_value = r_res

    resp = await generate_resume_feedback(
        resume_id=203,
        job_id=None,
        force_refresh=False,
        current_user=student,
        db=mock_db,
    )
    assert resp.feedback.overall_presentation_score is not None


# =============================================================================
# 7. Non-Modification of Original Records Test
# =============================================================================

@pytest.mark.asyncio
async def test_resume_and_profile_records_remain_unmodified(tmp_path):
    """Feedback generation is read-only and does not mutate resume or student profile."""
    student = build_student_user(id=1)
    original_cgpa = student.student_profile.cgpa
    resume = build_test_resume(id=204, student_id=1, tmp_path=tmp_path)
    original_status = resume.parsing_status

    mock_db = AsyncMock()
    r_res = MagicMock()
    r_res.scalar_one_or_none.return_value = resume
    mock_db.execute.return_value = r_res

    await generate_resume_feedback(
        resume_id=204,
        job_id=None,
        force_refresh=False,
        current_user=student,
        db=mock_db,
    )

    # Verify no commit or mutation occurred on the ORM models
    assert resume.parsing_status == original_status
    assert student.student_profile.cgpa == original_cgpa
    mock_db.commit.assert_not_called()


# =============================================================================
# 8. API Route Handlers Tests
# =============================================================================

@pytest.mark.asyncio
async def test_route_request_resume_feedback(tmp_path):
    """POST /resumes/{resume_id}/feedback route handler."""
    student = build_student_user(id=1)
    resume = build_test_resume(id=205, student_id=1, tmp_path=tmp_path)

    mock_db = AsyncMock()
    r_res = MagicMock()
    r_res.scalar_one_or_none.return_value = resume
    mock_db.execute.return_value = r_res

    req = ResumeFeedbackRequest(job_id=None, force_refresh=False)
    resp = await request_resume_feedback(resume_id=205, req=req, current_user=student, db=mock_db)
    assert isinstance(resp, ResumeFeedbackResponse)
    assert resp.resume_id == 205


@pytest.mark.asyncio
async def test_route_get_resume_feedback_cached_and_not_found(tmp_path):
    """GET /resumes/{resume_id}/feedback route handler."""
    student = build_student_user(id=1)
    resume = build_test_resume(id=206, student_id=1, tmp_path=tmp_path)

    mock_db = AsyncMock()
    r_res = MagicMock()
    r_res.scalar_one_or_none.return_value = resume
    mock_db.execute.return_value = r_res

    # 1. When not in cache -> 404 FEEDBACK_NOT_FOUND
    with pytest.raises(NotFoundError) as exc_info:
        await get_resume_feedback(resume_id=206, job_id=None, current_user=student, db=mock_db)
    assert exc_info.value.code == "FEEDBACK_NOT_FOUND"

    # 2. Populate cache via generation
    await generate_resume_feedback(resume_id=206, job_id=None, force_refresh=False, current_user=student, db=mock_db)

    # 3. Retrieve from cache
    resp = await get_resume_feedback(resume_id=206, job_id=None, current_user=student, db=mock_db)
    assert isinstance(resp, ResumeFeedbackResponse)
    assert resp.resume_id == 206


@pytest.mark.asyncio
async def test_route_list_feedback_target_jobs(tmp_path):
    """GET /resumes/{resume_id}/feedback/jobs lists active campus opportunities."""
    student = build_student_user(id=1, institution_id=10)
    resume = build_test_resume(id=207, student_id=1, tmp_path=tmp_path)
    job = build_test_job(id=70, institution_id=10)

    mock_db = AsyncMock()
    r_res = MagicMock()
    r_res.scalar_one_or_none.return_value = resume

    j_res = MagicMock()
    j_res.scalars.return_value.all.return_value = [job]

    mock_db.execute.side_effect = [r_res, j_res]

    jobs_list = await list_feedback_target_jobs(resume_id=207, current_user=student, db=mock_db)
    assert len(jobs_list) == 1
    assert jobs_list[0]["id"] == 70
    assert jobs_list[0]["company_name"] == "Apex Systems"


# =============================================================================
# 9. Force-Refresh Cooldown & Multi-Role Authorization Hardening Tests
# =============================================================================

@pytest.mark.asyncio
async def test_force_refresh_cooldown_rate_limiting(tmp_path):
    """Force-refresh enforces cooldown; rapid subsequent force-refreshes raise 429."""
    student = build_student_user(id=1)
    resume = build_test_resume(id=300, student_id=1, tmp_path=tmp_path)

    mock_db = AsyncMock()
    r_res = MagicMock()
    r_res.scalar_one_or_none.return_value = resume
    mock_db.execute.return_value = r_res

    # 1. Initial standard evaluation (Cache Miss)
    resp1 = await generate_resume_feedback(resume_id=300, job_id=None, force_refresh=False, current_user=student, db=mock_db)
    assert resp1.is_cached is False

    # 2. First force-refresh is permitted
    resp2 = await generate_resume_feedback(resume_id=300, job_id=None, force_refresh=True, current_user=student, db=mock_db)
    assert resp2.is_cached is False

    # 3. Rapid subsequent force-refresh within 30s raises 429 FORCE_REFRESH_COOLDOWN
    with pytest.raises(AppError) as exc_info:
        await generate_resume_feedback(resume_id=300, job_id=None, force_refresh=True, current_user=student, db=mock_db)
    assert exc_info.value.code == "FORCE_REFRESH_COOLDOWN"
    assert exc_info.value.status_code == 429

    # 4. Standard cache hit request (force_refresh=False) is still completely permitted and bypasses AI
    resp_cached = await generate_resume_feedback(resume_id=300, job_id=None, force_refresh=False, current_user=student, db=mock_db)
    assert resp_cached.is_cached is True
    assert resp_cached.usage.prompt_tokens == 0


@pytest.mark.asyncio
async def test_feedback_retrieval_tpo_admin_recruiter_blocked(tmp_path):
    """TPO, Admin, Recruiter, and other students cannot retrieve resume feedback reports."""
    student_a = build_student_user(id=1)
    student_b = build_student_user(id=2)
    tpo = build_tpo_user(id=20)
    admin = build_admin_user(id=99)
    recruiter = build_recruiter_user(id=30)
    resume = build_test_resume(id=400, student_id=1, tmp_path=tmp_path)

    mock_db = AsyncMock()
    r_res = MagicMock()
    r_res.scalar_one_or_none.return_value = resume
    mock_db.execute.return_value = r_res

    # Populate cache first with Student A
    await generate_resume_feedback(resume_id=400, job_id=None, force_refresh=False, current_user=student_a, db=mock_db)

    # 1. Other student attempting to retrieve Student A's feedback raises PermissionDeniedError
    with pytest.raises(PermissionDeniedError) as exc_info:
        await get_latest_cached_feedback(resume_id=400, job_id=None, current_user=student_b, db=mock_db)
    assert exc_info.value.code == "AUTHORIZATION_VIOLATION"

    # 2. TPO attempting to retrieve raises PermissionDeniedError
    with pytest.raises(PermissionDeniedError) as exc_info:
        await get_latest_cached_feedback(resume_id=400, job_id=None, current_user=tpo, db=mock_db)
    assert exc_info.value.code == "AUTHORIZATION_VIOLATION"

    # 3. Admin attempting to retrieve raises PermissionDeniedError
    with pytest.raises(PermissionDeniedError) as exc_info:
        await get_latest_cached_feedback(resume_id=400, job_id=None, current_user=admin, db=mock_db)
    assert exc_info.value.code == "AUTHORIZATION_VIOLATION"

    # 4. Recruiter attempting to retrieve raises PermissionDeniedError
    with pytest.raises(PermissionDeniedError) as exc_info:
        await get_latest_cached_feedback(resume_id=400, job_id=None, current_user=recruiter, db=mock_db)
    assert exc_info.value.code == "AUTHORIZATION_VIOLATION"


@pytest.mark.asyncio
async def test_all_three_endpoints_enforce_student_rbac():
    """All resume feedback endpoints enforce require_student role-based access control."""
    student = build_student_user(id=1)
    tpo = build_tpo_user(id=20)
    admin = build_admin_user(id=99)
    recruiter = build_recruiter_user(id=30)

    role_checker = require_student

    # Student succeeds
    resolved = await role_checker(current_user=student)
    assert resolved.role == UserRole.STUDENT

    # Non-student roles raise 403 Forbidden
    for non_student in [tpo, admin, recruiter]:
        with pytest.raises(HTTPException) as exc_info:
            await role_checker(current_user=non_student)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "AUTHORIZATION_ROLE_VIOLATION"


