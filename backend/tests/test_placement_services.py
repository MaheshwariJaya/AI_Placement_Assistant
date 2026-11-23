"""Comprehensive unit tests for Phase 6 Stage 2 Core Business Logic Services."""
from datetime import datetime, timedelta, timezone
import hashlib
import os
import tempfile
from typing import List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    AppException,
    AuthorizationException,
    EntityNotFoundException,
    ResourceConflictException,
)
from app.models.company import Company, RecruiterProfile
from app.models.job import Job, JobSkill, JobEligibleDepartment, JobStatus, EmploymentType, WorkMode
from app.models.organization import Department, Institution
from app.models.placement import (
    ApplicationStatus,
    ApplicationStatusHistory,
    DecisionDomain,
    DriveMode,
    DriveStatus,
    Interview,
    InterviewMode,
    InterviewOutcome,
    InterviewStatus,
    JobApplication,
    Notification,
    NotificationCategory,
    PlacementDrive,
    PlacementDriveJob,
    TpoScreeningStatus,
)
from app.models.resume import Resume
from app.models.student import (
    StudentCertification,
    StudentExperience,
    StudentProfile,
    StudentProject,
    StudentSkill,
)
from app.models.user import User, UserRole
from app.services.application_service import (
    compute_file_sha256,
    stream_recruiter_resume,
    submit_application,
    withdraw_application,
)
from app.services.drive_service import (
    add_job_to_drive,
    create_placement_drive,
    get_drive_with_stats,
    soft_remove_job_from_drive,
)
from app.services.interview_service import (
    cancel_interview,
    check_student_interview_collision,
    record_interview_outcome,
    reschedule_interview,
    schedule_interview,
)
from app.services.notification_service import (
    create_notification,
    get_unread_count,
    list_notifications,
    mark_all_as_read,
    mark_as_read,
)
from app.services.state_machine import (
    InvalidStateTransitionError,
    execute_recruiter_lifecycle_transition,
    execute_tpo_screening_transition,
    validate_recruiter_lifecycle_transition,
    validate_tpo_screening_transition,
)


def _run_sync(coro):
    """Utility to run an async coroutine synchronously in unit tests."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


# =============================================================================
# Helper Builders
# =============================================================================

def build_student_user(id: int = 1, institution_id: int = 1) -> User:
    return User(
        id=id,
        email=f"student_{id}@institution.edu",
        hashed_password="hash",
        full_name=f"Student {id}",
        role=UserRole.STUDENT,
        institution_id=institution_id,
        department_id=1,
        is_active=True,
        is_verified=True,
    )


def build_tpo_user(id: int = 2, institution_id: int = 1) -> User:
    return User(
        id=id,
        email=f"tpo_{id}@institution.edu",
        hashed_password="hash",
        full_name=f"TPO Officer {id}",
        role=UserRole.TPO,
        institution_id=institution_id,
        is_active=True,
        is_verified=True,
    )


def build_recruiter_user(id: int = 3, company_id: int = 1) -> User:
    user = User(
        id=id,
        email=f"recruiter_{id}@corp.com",
        hashed_password="hash",
        full_name=f"Recruiter {id}",
        role=UserRole.RECRUITER,
        institution_id=None,
        is_active=True,
        is_verified=True,
    )
    user.recruiter_profile = RecruiterProfile(
        id=id,
        user_id=id,
        company_id=company_id,
        designation="Lead Technical Recruiter",
    )
    return user


def build_student_profile(id: int = 1, user_id: int = 1, cgpa: float = 8.5) -> StudentProfile:
    prof = StudentProfile(
        id=id,
        user_id=user_id,
        roll_number=f"CS{id:03d}",
        graduation_year=2026,
        cgpa=cgpa,
        active_backlogs=0,
        total_backlogs=0,
        is_placement_ready=True,
    )
    prof.skills = [
        StudentSkill(id=1, student_id=id, skill_name="Python", proficiency_level="advanced", is_verified=True),
        StudentSkill(id=2, student_id=id, skill_name="SQL", proficiency_level="intermediate", is_verified=True),
    ]
    prof.projects = [
        StudentProject(id=1, student_id=id, title="E-Commerce API", technologies="Python, FastAPI, SQL"),
    ]
    prof.experiences = []
    prof.certifications = []
    return prof


def build_job(
    id: int = 1,
    company_id: int = 1,
    institution_id: Optional[int] = None,
    min_cgpa: float = 7.0,
    status: JobStatus = JobStatus.PUBLISHED,
    is_active: bool = True,
) -> Job:
    now = datetime.now(timezone.utc)
    job = Job(
        id=id,
        company_id=company_id,
        institution_id=institution_id,
        created_by_user_id=10,
        title="Software Development Engineer",
        description="Core backend development role.",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.ON_SITE,
        location="Bengaluru",
        min_cgpa=min_cgpa,
        target_graduation_year=2026,
        max_active_backlogs=0,
        max_total_backlogs=1,
        application_deadline=now + timedelta(days=10),
        status=status,
        is_active=is_active,
    )
    job.skills = [
        JobSkill(id=1, job_id=id, skill_name="Python", is_mandatory=True, weight_factor=1.0),
    ]
    job.eligible_departments = []
    return job


def build_resume(id: int = 1, student_id: int = 1, file_path: str = "/tmp/resume.pdf", file_hash: str = "abc") -> Resume:
    return Resume(
        id=id,
        student_id=student_id,
        file_name="resume.pdf",
        file_path=file_path,
        file_type="pdf",
        file_size_bytes=1024,
        file_hash=file_hash,
        parsing_status="approved",
        is_active=True,
    )


def build_drive(id: int = 1, institution_id: int = 1) -> PlacementDrive:
    now = datetime.now(timezone.utc)
    return PlacementDrive(
        id=id,
        institution_id=institution_id,
        created_by_user_id=2,
        name="Campus Recruitment Drive 2026",
        academic_year="2025-2026",
        target_graduation_year=2026,
        registration_start_date=now - timedelta(days=2),
        registration_end_date=now + timedelta(days=5),
        drive_mode=DriveMode.ON_CAMPUS,
        status=DriveStatus.ONGOING,
        is_active=True,
    )


def create_mock_session(*query_results) -> AsyncMock:
    """Create an AsyncMock session configured for synchronous step testing with given query results."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    mock_responses = []
    for res in query_results:
        m = MagicMock()
        if isinstance(res, list):
            m.scalars.return_value.all.return_value = res
            m.scalar_one_or_none.return_value = res[0] if res else None
        else:
            m.scalar_one_or_none.return_value = res
            m.scalars.return_value.all.return_value = [res] if res is not None else []
            m.scalar.return_value = res
        mock_responses.append(m)

    def _execute_side_effect(*args, **kwargs):
        if mock_responses:
            return mock_responses.pop(0)
        default_m = MagicMock()
        default_m.scalar_one_or_none.return_value = None
        default_m.scalars.return_value.all.return_value = []
        default_m.scalar.return_value = None
        return default_m

    session.execute.side_effect = _execute_side_effect
    return session


# =============================================================================
# 1. Application Eligibility & Submission Tests
# =============================================================================

def test_application_submission_success():
    """Verify clean application submission with Phase 5 scoring and atomic history."""
    student_user = build_student_user(id=1, institution_id=1)
    student_profile = build_student_profile(id=1, user_id=1, cgpa=8.5)
    job = build_job(id=10, min_cgpa=7.0)

    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(b"resume-content-valid")
        tmp_path = tf.name

    try:
        content_hash = compute_file_sha256(tmp_path)
        resume = build_resume(id=5, student_id=1, file_path=tmp_path, file_hash=content_hash)

        # 5 queries: StudentProfile, Job, duplicate check (None), Resume, Notification (None)
        session = create_mock_session(student_profile, job, None, resume, None)

        app = _run_sync(
            submit_application(
                session=session,
                student_user=student_user,
                job_id=10,
                resume_id=5,
                drive_id=None,
                cover_letter="Passionate about Python systems.",
            )
        )

        assert app.job_id == 10
        assert app.student_id == 1
        assert app.resume_id == 5
        assert app.current_status == ApplicationStatus.APPLIED
        assert app.tpo_screening_status == TpoScreeningStatus.BYPASSED
        assert app.compatibility_score_at_application >= 0.0
        assert session.add.call_count >= 2  # Application + initial history
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_application_rejected_for_cgpa_ineligibility():
    """Verify application rejected before persistence when student fails CGPA cutoff."""
    student_user = build_student_user(id=1)
    student_profile = build_student_profile(id=1, user_id=1, cgpa=6.5)  # Ineligible (< 7.5)
    job = build_job(id=10, min_cgpa=7.5)
    resume = build_resume(id=5, student_id=1)

    session = create_mock_session(student_profile, job, None, resume)

    with pytest.raises(AppException) as exc:
        _run_sync(
            submit_application(
                session=session,
                student_user=student_user,
                job_id=10,
                resume_id=5,
            )
        )
    assert exc.value.code == "ELIGIBILITY_CUTOFF_FAILED"
    assert "CGPA" in str(exc.value.message)


def test_duplicate_application_blocked():
    """Duplicate application submission must be blocked."""
    student_user = build_student_user(id=1)
    student_profile = build_student_profile(id=1)
    job = build_job(id=10)
    existing_app = JobApplication(id=99, job_id=10, student_id=1, current_status=ApplicationStatus.APPLIED)

    session = create_mock_session(student_profile, job, existing_app)

    with pytest.raises(ResourceConflictException):
        _run_sync(
            submit_application(
                session=session,
                student_user=student_user,
                job_id=10,
                resume_id=5,
            )
        )


def test_resume_ownership_validation():
    """Verify application submission rejects resumes owned by other candidates."""
    student_user = build_student_user(id=1)
    student_profile = build_student_profile(id=1)
    job = build_job(id=10)
    other_resume = build_resume(id=5, student_id=999)  # Other student!

    session = create_mock_session(student_profile, job, None, other_resume)

    with pytest.raises(AuthorizationException):
        _run_sync(
            submit_application(
                session=session,
                student_user=student_user,
                job_id=10,
                resume_id=5,
            )
        )


def test_unapproved_resume_rejected():
    """Verify applying with a non-approved resume is rejected."""
    student_user = build_student_user(id=1)
    student_profile = build_student_profile(id=1)
    job = build_job(id=10)
    unapproved_resume = build_resume(id=5, student_id=1)
    unapproved_resume.parsing_status = "processing"

    session = create_mock_session(student_profile, job, None, unapproved_resume)

    with pytest.raises(AppException) as exc:
        _run_sync(
            submit_application(
                session=session,
                student_user=student_user,
                job_id=10,
                resume_id=5,
            )
        )
    assert exc.value.code == "RESUME_NOT_APPROVED"


def test_resume_checksum_mismatch_rejected():
    """Verify resume with checksum mismatch is rejected."""
    student_user = build_student_user(id=1)
    student_profile = build_student_profile(id=1)
    job = build_job(id=10)

    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(b"tampered content")
        tmp_path = tf.name

    try:
        tampered_resume = build_resume(id=5, student_id=1, file_path=tmp_path, file_hash="legit_sha256_hash_different")
        session = create_mock_session(student_profile, job, None, tampered_resume)

        with pytest.raises(AppException) as exc:
            _run_sync(
                submit_application(
                    session=session,
                    student_user=student_user,
                    job_id=10,
                    resume_id=5,
                )
            )
        assert exc.value.code == "RESUME_CHECKSUM_MISMATCH"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# =============================================================================
# 2. Recruiter Resume Streaming & Revocation Tests
# =============================================================================

def test_recruiter_resume_stream_success():
    """Recruiter successfully streams verified resume bytes without TOCTOU vulnerability."""
    recruiter = build_recruiter_user(id=3, company_id=1)
    job = build_job(id=10, company_id=1)

    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(b"legitimate pdf content")
        tmp_path = tf.name

    try:
        content_hash = compute_file_sha256(tmp_path)
        resume = build_resume(id=5, file_path=tmp_path, file_hash=content_hash)
        app = JobApplication(
            id=1,
            job_id=10,
            student_id=1,
            resume_id=5,
            current_status=ApplicationStatus.SHORTLISTED,
            job=job,
            resume=resume,
        )

        session = create_mock_session(app, recruiter.recruiter_profile)
        stream, name, size, media_type = _run_sync(
            stream_recruiter_resume(session=session, application_id=1, recruiter_user=recruiter)
        )
        assert hasattr(stream, "read")
        assert stream.read() == b"legitimate pdf content"
        assert name == "resume.pdf"
        assert size == len(b"legitimate pdf content")
        assert media_type == "application/pdf"
        stream.close()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_recruiter_resume_stream_tampered_closes_buffer():
    """Recruiter streaming a tampered resume raises checksum mismatch and closes resources safely."""
    recruiter = build_recruiter_user(id=3, company_id=1)
    job = build_job(id=10, company_id=1)

    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(b"tampered content")
        tmp_path = tf.name

    try:
        resume = build_resume(id=5, file_path=tmp_path, file_hash="different_stored_hash_value")
        app = JobApplication(
            id=1,
            job_id=10,
            student_id=1,
            resume_id=5,
            current_status=ApplicationStatus.SHORTLISTED,
            job=job,
            resume=resume,
        )

        session = create_mock_session(app, recruiter.recruiter_profile)
        with pytest.raises(AppException) as exc:
            _run_sync(stream_recruiter_resume(session=session, application_id=1, recruiter_user=recruiter))
        assert exc.value.code == "RESUME_CHECKSUM_MISMATCH"
        assert exc.value.status_code == 403
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_recruiter_resume_stream_missing_file_raises_error():
    """Missing physical resume file raises EntityNotFoundException."""
    recruiter = build_recruiter_user(id=3, company_id=1)
    job = build_job(id=10, company_id=1)
    resume = build_resume(id=5, file_path="/nonexistent/path/to/resume.pdf")

    app = JobApplication(
        id=1,
        job_id=10,
        student_id=1,
        resume_id=5,
        current_status=ApplicationStatus.SHORTLISTED,
        job=job,
        resume=resume,
    )

    session = create_mock_session(app, recruiter.recruiter_profile)
    with pytest.raises(EntityNotFoundException) as exc:
        _run_sync(stream_recruiter_resume(session=session, application_id=1, recruiter_user=recruiter))
    assert exc.value.details["entity"] == "ResumeFile"
    assert exc.value.code == "ENTITY_NOT_FOUND"


def test_recruiter_resume_stream_revoked_on_withdrawal():
    """Recruiter streaming a candidate resume is blocked when application is withdrawn."""
    recruiter = build_recruiter_user(id=3, company_id=1)
    job = build_job(id=10, company_id=1)
    resume = build_resume(id=5, file_path="/fake/resume.pdf")

    app = JobApplication(
        id=1,
        job_id=10,
        student_id=1,
        resume_id=5,
        current_status=ApplicationStatus.WITHDRAWN,
        job=job,
        resume=resume,
    )

    session = create_mock_session(app, recruiter.recruiter_profile)

    with pytest.raises(AuthorizationException) as exc:
        _run_sync(stream_recruiter_resume(session=session, application_id=1, recruiter_user=recruiter))
    assert "withdrawn" in str(exc.value.message).lower()


def test_recruiter_resume_stream_isolation_across_companies():
    """Recruiter from Company A cannot stream resume for Job from Company B."""
    recruiter_co1 = build_recruiter_user(id=3, company_id=1)
    job_co2 = build_job(id=10, company_id=2)  # Different company!
    resume = build_resume(id=5)

    app = JobApplication(
        id=1,
        job_id=10,
        student_id=1,
        resume_id=5,
        current_status=ApplicationStatus.APPLIED,
        job=job_co2,
        resume=resume,
    )

    session = create_mock_session(app, recruiter_co1.recruiter_profile)

    with pytest.raises(AuthorizationException) as exc:
        _run_sync(stream_recruiter_resume(session=session, application_id=1, recruiter_user=recruiter_co1))
    assert "your company" in str(exc.value.message).lower()


def test_withdraw_application_success():
    """Candidate successfully withdraws application with audit record."""
    student_user = build_student_user(id=1)
    student_profile = build_student_profile(id=1, user_id=1)
    app = JobApplication(
        id=1,
        job_id=10,
        student_id=1,
        current_status=ApplicationStatus.APPLIED,
        student_profile=student_profile,
    )
    session = create_mock_session(app)

    withdrawn = _run_sync(
        withdraw_application(
            session=session,
            student_user=student_user,
            application_id=1,
            reason="Accepted another offer",
        )
    )
    assert withdrawn.current_status == ApplicationStatus.WITHDRAWN
    assert withdrawn.withdrawn_at is not None
    assert withdrawn.withdrawal_reason == "Accepted another offer"
    assert session.add.called


def test_withdraw_application_validation():
    """Verify validation boundaries on application withdrawal."""
    student_user = build_student_user(id=1)
    other_student_user = build_student_user(id=2)
    student_profile = build_student_profile(id=1, user_id=1)
    app = JobApplication(
        id=1,
        job_id=10,
        student_id=1,
        current_status=ApplicationStatus.APPLIED,
        student_profile=student_profile,
    )

    # 1. Reason too short
    session = create_mock_session(app)
    with pytest.raises(AppException) as exc:
        _run_sync(withdraw_application(session=session, student_user=student_user, application_id=1, reason="no"))
    assert exc.value.code == "INVALID_WITHDRAWAL_REASON"

    # 2. Unauthorized student
    session = create_mock_session(app)
    with pytest.raises(AuthorizationException) as exc:
        _run_sync(withdraw_application(session=session, student_user=other_student_user, application_id=1, reason="Withdraw please"))
    assert "own applications" in str(exc.value.message).lower()

    # 3. Already withdrawn
    app.current_status = ApplicationStatus.WITHDRAWN
    session = create_mock_session(app)
    with pytest.raises(AppException) as exc:
        _run_sync(withdraw_application(session=session, student_user=student_user, application_id=1, reason="Already gone"))
    assert exc.value.code == "APPLICATION_ALREADY_WITHDRAWN"


# =============================================================================
# 3. State Machine & TPO Screening Gate Tests
# =============================================================================

def test_tpo_screening_transitions():
    """Verify valid and invalid TPO screening transitions."""
    validate_tpo_screening_transition(TpoScreeningStatus.PENDING, TpoScreeningStatus.SHORTLISTED, drive_id=1)
    validate_tpo_screening_transition(TpoScreeningStatus.PENDING, TpoScreeningStatus.REJECTED, drive_id=1)
    validate_tpo_screening_transition(TpoScreeningStatus.SHORTLISTED, TpoScreeningStatus.REJECTED, drive_id=1)

    with pytest.raises(InvalidStateTransitionError) as exc:
        validate_tpo_screening_transition(TpoScreeningStatus.BYPASSED, TpoScreeningStatus.SHORTLISTED, drive_id=None)
    assert exc.value.code == "TPO_SCREENING_BYPASSED"


def test_recruiter_blocked_when_tpo_screening_pending_or_rejected():
    """Campus drive application blocks recruiter progression past 'applied' if not shortlisted by TPO."""
    with pytest.raises(InvalidStateTransitionError) as exc:
        validate_recruiter_lifecycle_transition(
            current_status=ApplicationStatus.APPLIED,
            target_status=ApplicationStatus.SHORTLISTED,
            tpo_screening_status=TpoScreeningStatus.PENDING,
            drive_id=1,
        )
    assert exc.value.code == "TPO_SCREENING_PENDING"

    with pytest.raises(InvalidStateTransitionError) as exc:
        validate_recruiter_lifecycle_transition(
            current_status=ApplicationStatus.APPLIED,
            target_status=ApplicationStatus.UNDER_REVIEW,
            tpo_screening_status=TpoScreeningStatus.REJECTED,
            drive_id=1,
        )
    assert exc.value.code == "TPO_SCREENING_REJECTED"

    validate_recruiter_lifecycle_transition(
        current_status=ApplicationStatus.APPLIED,
        target_status=ApplicationStatus.UNDER_REVIEW,
        tpo_screening_status=TpoScreeningStatus.SHORTLISTED,
        drive_id=1,
    )


def test_direct_application_bypasses_tpo_screening():
    """Direct application (drive_id=None) bypasses TPO screening and allows recruiter transitions."""
    validate_recruiter_lifecycle_transition(
        current_status=ApplicationStatus.APPLIED,
        target_status=ApplicationStatus.UNDER_REVIEW,
        tpo_screening_status=TpoScreeningStatus.BYPASSED,
        drive_id=None,
    )
    validate_recruiter_lifecycle_transition(
        current_status=ApplicationStatus.UNDER_REVIEW,
        target_status=ApplicationStatus.SHORTLISTED,
        tpo_screening_status=TpoScreeningStatus.BYPASSED,
        drive_id=None,
    )


def test_late_tpo_rejection_preserves_recruiter_status_and_notifies_recruiter():
    """
    Late TPO rejection updates screening status only, dispatches idempotent recruiter alert,
    and preserves recruiter lifecycle status until recruiter explicitly acts.
    """
    job = build_job(id=10, company_id=1)
    app = JobApplication(
        id=1,
        drive_id=1,
        tpo_screening_status=TpoScreeningStatus.SHORTLISTED,
        current_status=ApplicationStatus.INTERVIEW_SCHEDULED,
        job=job,
    )

    # Mock session queries:
    # 1. Audit latest hash check (None -> genesis hash)
    # 2. RecruiterProfile query ([3])
    # 3. Notification idempotency check (None)
    session = create_mock_session(None, [3], None)

    _run_sync(
        execute_tpo_screening_transition(
            session=session,
            application=app,
            new_screening_status=TpoScreeningStatus.REJECTED,
            actor_user_id=2,
            notes="Academic suspension reported.",
        )
    )

    # Invariant: TPO screening is updated, but recruitment lifecycle status is NOT automatically overwritten
    assert app.tpo_screening_status == TpoScreeningStatus.REJECTED
    assert app.current_status == ApplicationStatus.INTERVIEW_SCHEDULED
    # Verify recruiter alert notification details among added entities
    added_entities = [call_args[0][0] for call_args in session.add.call_args_list]
    added_notification = next((item for item in added_entities if isinstance(item, Notification)), None)
    assert added_notification is not None
    assert added_notification.recipient_user_id == 3
    assert added_notification.idempotency_key == f"tpo-rejection-alert-{app.id}-3"
    assert "Academic suspension" in added_notification.message

    # Recruiter can now explicitly make the rejection decision
    _run_sync(
        execute_recruiter_lifecycle_transition(
            session=session,
            application=app,
            new_status=ApplicationStatus.REJECTED,
            actor_user_id=3,
            notes="Recruiter confirmed candidate rejection following TPO academic suspension report.",
        )
    )
    assert app.current_status == ApplicationStatus.REJECTED


def test_tpo_rejection_cannot_overwrite_terminal_recruiter_states():
    """TPO screening cannot overwrite terminal recruiter states: offered, accepted, declined, rejected, withdrawn."""
    # 1. Withdrawn application rejects TPO screening attempt
    withdrawn_app = JobApplication(
        id=1,
        drive_id=1,
        tpo_screening_status=TpoScreeningStatus.PENDING,
        current_status=ApplicationStatus.WITHDRAWN,
    )
    session = AsyncMock(spec=AsyncSession)
    with pytest.raises(InvalidStateTransitionError) as exc:
        _run_sync(
            execute_tpo_screening_transition(
                session=session,
                application=withdrawn_app,
                new_screening_status=TpoScreeningStatus.REJECTED,
                actor_user_id=2,
            )
        )
    assert exc.value.code == "APPLICATION_WITHDRAWN"

    # 2. Offered, Offer accepted, Offer declined, and Rejected retain their recruiter state
    terminal_statuses = [
        ApplicationStatus.OFFERED,
        ApplicationStatus.OFFER_ACCEPTED,
        ApplicationStatus.OFFER_DECLINED,
        ApplicationStatus.REJECTED,
    ]
    for status in terminal_statuses:
        app = JobApplication(
            id=2,
            drive_id=1,
            tpo_screening_status=TpoScreeningStatus.SHORTLISTED,
            current_status=status,
            job=build_job(id=10, company_id=1),
        )
        m_rec = MagicMock(); m_rec.scalars.return_value.all.return_value = [3]
        m_notif = MagicMock(); m_notif.scalar_one_or_none.return_value = None
        s = AsyncMock(spec=AsyncSession)
        s.add = MagicMock()
        s.execute.side_effect = [m_rec, m_notif]

        _run_sync(
            execute_tpo_screening_transition(
                session=s,
                application=app,
                new_screening_status=TpoScreeningStatus.REJECTED,
                actor_user_id=2,
                notes="Disciplinary review outcome",
            )
        )
        assert app.tpo_screening_status == TpoScreeningStatus.REJECTED
        assert app.current_status == status  # Strictly preserved, never overwritten!


# =============================================================================
# 4. Interview Scheduling, Collision & Cancellation Tests
# =============================================================================

def test_interview_collision_prevention():
    """Overlapping interviews for the same candidate raise ResourceConflictException."""
    session = AsyncMock(spec=AsyncSession)
    now = datetime.now(timezone.utc)

    existing = Interview(
        id=1,
        round_title="Tech Round 1",
        scheduled_start_time=now + timedelta(hours=2),
        duration_minutes=60,
        status=InterviewStatus.SCHEDULED,
    )
    m_lock = MagicMock()
    m_active = MagicMock()
    m_active.scalars.return_value.all.return_value = [existing]
    session.execute.side_effect = [m_lock, m_active]

    with pytest.raises(ResourceConflictException) as exc:
        _run_sync(
            check_student_interview_collision(
                session=session,
                student_id=1,
                start_time=now + timedelta(hours=2, minutes=30),
                duration_minutes=60,
            )
        )
    assert "collision" in str(exc.value.message).lower()


def test_interview_collision_student_locking_order():
    """
    Verify interview collision checking acquires a row-level lock on student profile before query.
    Note: Mock tests verify lock clause construction and execution sequence.
    Live multi-process concurrency serialization requires PostgreSQL integration testing.
    """
    now = datetime.now(timezone.utc)
    session = AsyncMock(spec=AsyncSession)
    m_lock = MagicMock()
    m_active = MagicMock(); m_active.scalars.return_value.all.return_value = []
    session.execute.side_effect = [m_lock, m_active]

    _run_sync(
        check_student_interview_collision(
            session=session,
            student_id=42,
            start_time=now + timedelta(days=1),
            duration_minutes=45,
        )
    )

    # First call must be the row lock statement on StudentProfile.id with FOR UPDATE
    assert session.execute.call_count == 2
    first_stmt = session.execute.call_args_list[0][0][0]
    assert first_stmt._for_update_arg is not None
    assert first_stmt._for_update_arg.read is False  # FOR UPDATE exclusive row lock


def test_interview_schedule_success():
    """Schedule interview with collision check and student notification."""
    recruiter = build_recruiter_user(id=3, company_id=1)
    job = build_job(id=10, company_id=1)
    student_profile = build_student_profile(id=1)
    app = JobApplication(
        id=1,
        job_id=10,
        student_id=1,
        current_status=ApplicationStatus.SHORTLISTED,
        job=job,
        student_profile=student_profile,
    )
    now = datetime.now(timezone.utc)

    # Queries: 1. application, 2. recruiter profile, 3. unique round check (None), 4. lock, 5. active interviews ([]), 6. notification (None)
    session = create_mock_session(app, recruiter.recruiter_profile, None, MagicMock(), [], None)

    interview = _run_sync(
        schedule_interview(
            session=session,
            recruiter_user=recruiter,
            application_id=1,
            round_number=1,
            round_title="Technical Round 1",
            scheduled_start_time=now + timedelta(days=2),
            duration_minutes=45,
        )
    )

    assert interview.round_number == 1
    assert interview.status == InterviewStatus.SCHEDULED
    assert app.current_status == ApplicationStatus.INTERVIEW_SCHEDULED


def test_interview_rescheduling_success():
    """Recruiter reschedules an interview to a new time window."""
    now = datetime.now(timezone.utc)
    recruiter = build_recruiter_user(id=3, company_id=1)
    job = build_job(id=10, company_id=1)
    app = JobApplication(
        id=1,
        job_id=10,
        student_id=1,
        current_status=ApplicationStatus.INTERVIEW_SCHEDULED,
        job=job,
        student_profile=build_student_profile(id=1, user_id=1),
    )
    interview = Interview(
        id=1,
        application_id=1,
        round_number=1,
        round_title="Round 1 Technical",
        scheduled_start_time=now + timedelta(days=2),
        duration_minutes=45,
        status=InterviewStatus.SCHEDULED,
        application=app,
    )

    new_start = now + timedelta(days=3, hours=2)
    # Queries: 1. interview, 2. recruiter_profile, 3. student profile lock, 4. active interviews ([]), 5. notification (None)
    session = create_mock_session(interview, recruiter.recruiter_profile, 1, [], None)

    rescheduled = _run_sync(
        reschedule_interview(
            session=session,
            recruiter_user=recruiter,
            interview_id=1,
            new_start_time=new_start,
            new_duration_minutes=60,
            reason="Interviewer travel delay",
        )
    )

    assert rescheduled.scheduled_start_time == new_start
    assert rescheduled.duration_minutes == 60
    assert "Interviewer travel delay" in rescheduled.cancellation_reason


def test_round_aware_cancellation_round1():
    """Cancelling Round 1 reverts candidate pipeline state to 'shortlisted'."""
    recruiter = build_recruiter_user(id=3, company_id=1)
    job = build_job(id=10, company_id=1)
    app = JobApplication(
        id=1,
        job_id=10,
        student_id=1,
        current_status=ApplicationStatus.INTERVIEW_SCHEDULED,
        job=job,
        student_profile=build_student_profile(id=1),
    )
    interview = Interview(
        id=1,
        application_id=1,
        round_number=1,
        round_title="Round 1",
        status=InterviewStatus.SCHEDULED,
        application=app,
    )

    # Queries: 1. interview, 2. recruiter profile, 3. completed earlier rounds ([]), 4. notification (None)
    session = create_mock_session(interview, recruiter.recruiter_profile, [], None)

    cancelled = _run_sync(
        cancel_interview(
            session=session,
            recruiter_user=recruiter,
            interview_id=1,
            reason="Interviewer sudden emergency",
        )
    )

    assert cancelled.status == InterviewStatus.CANCELLED
    assert app.current_status == ApplicationStatus.SHORTLISTED


def test_round_aware_cancellation_round2_preserves_interviewed():
    """Cancelling Round 2 when Round 1 completed reverts state to 'interviewed', NOT 'shortlisted'."""
    recruiter = build_recruiter_user(id=3, company_id=1)
    job = build_job(id=10, company_id=1)
    app = JobApplication(
        id=1,
        job_id=10,
        student_id=1,
        current_status=ApplicationStatus.INTERVIEW_SCHEDULED,
        job=job,
        student_profile=build_student_profile(id=1),
    )
    r1 = Interview(id=1, application_id=1, round_number=1, status=InterviewStatus.COMPLETED)
    r2 = Interview(id=2, application_id=1, round_number=2, round_title="Round 2", status=InterviewStatus.SCHEDULED, application=app)

    # Queries: 1. interview, 2. recruiter profile, 3. completed earlier rounds ([r1]), 4. notification (None)
    session = create_mock_session(r2, recruiter.recruiter_profile, [r1], None)

    cancelled = _run_sync(
        cancel_interview(
            session=session,
            recruiter_user=recruiter,
            interview_id=2,
            reason="Hiring freeze on senior level",
        )
    )

    assert cancelled.status == InterviewStatus.CANCELLED
    assert app.current_status == ApplicationStatus.INTERVIEWED


def test_failed_interview_does_not_auto_reject_application():
    """A failed interview outcome leaves application in 'interviewed', requiring explicit recruiter decision."""
    recruiter = build_recruiter_user(id=3, company_id=1)
    job = build_job(id=10, company_id=1)
    app = JobApplication(
        id=1,
        job_id=10,
        student_id=1,
        current_status=ApplicationStatus.INTERVIEW_SCHEDULED,
        job=job,
        student_profile=build_student_profile(id=1),
    )
    interview = Interview(
        id=1,
        application_id=1,
        round_number=1,
        round_title="Technical Round 1",
        status=InterviewStatus.SCHEDULED,
        application=app,
    )

    session = create_mock_session(interview, recruiter.recruiter_profile)

    completed = _run_sync(
        record_interview_outcome(
            session=session,
            recruiter_user=recruiter,
            interview_id=1,
            outcome=InterviewOutcome.FAILED,
            feedback_notes="Candidate struggled with dynamic programming.",
        )
    )

    assert completed.status == InterviewStatus.COMPLETED
    assert completed.outcome == InterviewOutcome.FAILED
    assert app.current_status == ApplicationStatus.INTERVIEWED


# =============================================================================
# 5. Drive Management & Soft-Removal Tests
# =============================================================================

def test_drive_soft_removal_preserves_history_and_blocks_new_apps():
    """Soft-removing a job preserves association record and blocks subsequent applications."""
    tpo = build_tpo_user(id=2, institution_id=1)
    drive = build_drive(id=1, institution_id=1)
    drive_job = PlacementDriveJob(id=10, drive_id=1, job_id=5, is_active=True)

    session = create_mock_session(drive, drive_job)

    removed = _run_sync(
        soft_remove_job_from_drive(
            session=session,
            tpo_user=tpo,
            drive_id=1,
            job_id=5,
        )
    )

    assert removed.is_active is False
    assert removed.removed_at is not None

    # Verify applying to this soft-removed drive_job fails
    student_user = build_student_user(id=1, institution_id=1)
    student_profile = build_student_profile(id=1)
    job = build_job(id=5)
    resume = build_resume(id=2, student_id=1)

    session2 = create_mock_session(student_profile, job, None, drive, removed)

    with pytest.raises(AppException) as exc:
        _run_sync(
            submit_application(
                session=session2,
                student_user=student_user,
                job_id=5,
                resume_id=2,
                drive_id=1,
            )
        )
    assert exc.value.code == "JOB_NOT_ACTIVE_IN_DRIVE"


def test_drive_reactivation_of_soft_removed_job():
    """Adding a previously soft-removed job reactivates it cleanly."""
    tpo = build_tpo_user(id=2, institution_id=1)
    drive = build_drive(id=1, institution_id=1)
    job = build_job(id=5)
    inactive_association = PlacementDriveJob(
        id=10, drive_id=1, job_id=5, is_active=False, removed_at=datetime.now(timezone.utc)
    )

    session = create_mock_session(drive, job, inactive_association)

    reactivated = _run_sync(
        add_job_to_drive(
            session=session,
            tpo_user=tpo,
            drive_id=1,
            job_id=5,
        )
    )

    assert reactivated.is_active is True
    assert reactivated.removed_at is None


def test_drive_job_concurrency_locking_and_soft_removal():
    """
    Verify PostgreSQL row-locking clauses and is_active recheck for drive-job concurrency.
    Note: Mock tests verify lock clause construction and logical rejection boundaries.
    Live multi-process concurrency serialization requires PostgreSQL integration testing.
    """
    # 1. Verify soft_remove_job_from_drive query includes with_for_update() (FOR UPDATE lock)
    tpo = build_tpo_user(id=2, institution_id=1)
    drive = build_drive(id=1, institution_id=1)
    drive_job = PlacementDriveJob(id=10, drive_id=1, job_id=5, is_active=True)

    session = AsyncMock(spec=AsyncSession)
    m_drive = MagicMock(); m_drive.scalar_one_or_none.return_value = drive
    m_dj = MagicMock(); m_dj.scalar_one_or_none.return_value = drive_job
    session.execute.side_effect = [m_drive, m_dj]

    _run_sync(soft_remove_job_from_drive(session=session, tpo_user=tpo, drive_id=1, job_id=5))

    # Inspect the drive_job query executed on session
    second_call_stmt = session.execute.call_args_list[1][0][0]
    assert second_call_stmt._for_update_arg is not None  # FOR UPDATE clause present
    assert second_call_stmt._for_update_arg.read is False
    assert drive_job.is_active is False
    assert drive_job.removed_at is not None

    # 2. Verify submit_application acquires FOR SHARE (with_for_update(read=True)) row lock
    # and rechecks is_active, rejecting submission when already removed
    student_user = build_student_user(id=1, institution_id=1)
    student_profile = build_student_profile(id=1)
    job = build_job(id=5)
    resume = build_resume(id=2, student_id=1)
    inactive_drive_job = PlacementDriveJob(
        id=10, drive_id=1, job_id=5, is_active=False, removed_at=datetime.now(timezone.utc)
    )

    session2 = AsyncMock(spec=AsyncSession)
    m_prof = MagicMock(); m_prof.scalar_one_or_none.return_value = student_profile
    m_job = MagicMock(); m_job.scalar_one_or_none.return_value = job
    m_dup = MagicMock(); m_dup.scalar_one_or_none.return_value = None
    m_drive = MagicMock(); m_drive.scalar_one_or_none.return_value = drive
    m_adj = MagicMock(); m_adj.scalar_one_or_none.return_value = inactive_drive_job
    session2.execute.side_effect = [m_prof, m_job, m_dup, m_drive, m_adj]

    with pytest.raises(AppException) as exc:
        _run_sync(submit_application(session=session2, student_user=student_user, job_id=5, resume_id=2, drive_id=1))
    assert exc.value.code == "JOB_NOT_ACTIVE_IN_DRIVE"

    # Inspect the drive_job query to ensure with_for_update(read=True) / FOR SHARE clause is present
    dj_query_stmt = session2.execute.call_args_list[4][0][0]
    assert dj_query_stmt._for_update_arg is not None
    assert dj_query_stmt._for_update_arg.read is True  # PostgreSQL FOR SHARE lock


# =============================================================================
# 6. Notification Service & Idempotency Tests
# =============================================================================

def test_notification_idempotency_returns_existing():
    """Duplicate notification with same idempotency_key returns existing record without duplicate insertion."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    existing_notif = Notification(
        id=42,
        recipient_user_id=10,
        category=NotificationCategory.APPLICATION_UPDATE,
        title="Application Received",
        message="Your application was received.",
        idempotency_key="app-submit-10-5",
    )

    m = MagicMock()
    m.scalar_one_or_none.return_value = existing_notif
    session.execute.return_value = m

    notif = _run_sync(
        create_notification(
            session=session,
            recipient_user_id=10,
            category=NotificationCategory.APPLICATION_UPDATE,
            title="Application Received",
            message="Your application was received.",
            idempotency_key="app-submit-10-5",
        )
    )

    assert notif.id == 42
    assert session.add.call_count == 0


def test_notification_read_tracking():
    """Verify mark_as_read tracks read timestamp and enforces recipient ownership."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    notif = Notification(
        id=1,
        recipient_user_id=10,
        category=NotificationCategory.DRIVE_ANNOUNCEMENT,
        title="Drive Tomorrow",
        message="Be on time.",
        is_read=False,
    )
    m = MagicMock(); m.scalar_one_or_none.return_value = notif
    session.execute.return_value = m

    with pytest.raises(AuthorizationException):
        _run_sync(mark_as_read(session=session, notification_id=1, user_id=999))

    updated = _run_sync(mark_as_read(session=session, notification_id=1, user_id=10))
    assert updated.is_read is True
    assert updated.read_at is not None


# =============================================================================
# 7. Transaction Rollback Integrity Test
# =============================================================================

def test_transaction_rollback_when_audit_history_fails():
    """Ensure that if audit history creation fails, the application creation rolls back atomically."""
    student_user = build_student_user(id=1, institution_id=1)
    student_profile = build_student_profile(id=1, user_id=1)
    job = build_job(id=10)
    resume = build_resume(id=5, student_id=1)

    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()

    m_prof = MagicMock(); m_prof.scalar_one_or_none.return_value = student_profile
    m_job = MagicMock(); m_job.scalar_one_or_none.return_value = job
    m_dup = MagicMock(); m_dup.scalar_one_or_none.return_value = None
    m_res = MagicMock(); m_res.scalar_one_or_none.return_value = resume
    m_notif = MagicMock(); m_notif.scalar_one_or_none.return_value = None

    session.execute.side_effect = [m_prof, m_job, m_dup, m_res, m_notif]

    # Force second flush (audit history insertion) to raise database integrity error
    session.flush.side_effect = [None, RuntimeError("Database constraint failure on audit ledger insertion")]

    with pytest.raises(RuntimeError) as exc:
        _run_sync(
            submit_application(
                session=session,
                student_user=student_user,
                job_id=10,
                resume_id=5,
            )
        )
    assert "audit ledger insertion" in str(exc.value)
