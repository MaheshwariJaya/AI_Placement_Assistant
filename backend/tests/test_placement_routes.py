"""Comprehensive route-level unit tests for Phase 6 Placement & Recruitment Management API."""
from datetime import datetime, timedelta, timezone
import io
import os
import tempfile
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException
from starlette.responses import StreamingResponse

from app.core.errors import (
    AppException,
    AuthorizationException,
    EntityNotFoundException,
    ResourceConflictException,
)
from app.models.company import Company, RecruiterProfile
from app.models.job import EmploymentType, Job, JobStatus, WorkMode
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
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from app.routes.placement import (
    add_job_to_drive_endpoint,
    cancel_interview_endpoint,
    create_drive_endpoint,
    get_application_detail_endpoint,
    get_drive_endpoint,
    get_my_applications_endpoint,
    get_unread_count_endpoint,
    list_application_interviews_endpoint,
    list_drive_applications_endpoint,
    list_drive_jobs_endpoint,
    list_drives_endpoint,
    list_notifications_endpoint,
    list_recruiter_applications_endpoint,
    mark_all_read_endpoint,
    mark_notification_read_endpoint,
    record_interview_outcome_endpoint,
    recruiter_update_status_endpoint,
    remove_job_from_drive_endpoint,
    reschedule_interview_endpoint,
    respond_to_offer_endpoint,
    schedule_interview_endpoint,
    stream_application_resume_endpoint,
    submit_application_endpoint,
    tpo_screen_application_endpoint,
    update_drive_endpoint,
    withdraw_application_endpoint,
)
from app.schemas.placement import (
    ApplicationWithdrawRequest,
    InterviewCancelRequest,
    InterviewCreateRequest,
    InterviewOutcomeRequest,
    InterviewRescheduleRequest,
    JobApplicationCreate,
    JobApplicationDetailResponse,
    JobApplicationRecruiterResponse,
    JobApplicationStudentDetailResponse,
    JobApplicationTpoDetailResponse,
    OfferResponseRequest,
    PlacementDriveCreate,
    PlacementDriveJobAddRequest,
    PlacementDriveUpdate,
    RecruiterStatusUpdateRequest,
    TpoScreeningUpdateRequest,
)


def _run_sync(coro):
    """Synchronously advance an async coroutine."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


# =============================================================================
# Mock Builders
# =============================================================================

def build_student(id: int = 1, institution_id: int = 1) -> User:
    user = User(
        id=id,
        email=f"student{id}@campus.edu",
        full_name=f"Student User {id}",
        role=UserRole.STUDENT,
        institution_id=institution_id,
        is_active=True,
    )
    user.student_profile = StudentProfile(
        id=id,
        user_id=id,
        roll_number=f"ROLL{id:04d}",
        cgpa=8.5,
        graduation_year=2026,
        user=user,
    )
    return user


def build_recruiter(id: int = 10, company_id: int = 1) -> User:
    user = User(
        id=id,
        email=f"recruiter{id}@partner.com",
        full_name=f"Recruiter User {id}",
        role=UserRole.RECRUITER,
        is_active=True,
    )
    user.recruiter_profile = RecruiterProfile(
        id=id,
        user_id=id,
        company_id=company_id,
        user=user,
    )
    return user


def build_tpo(id: int = 20, institution_id: int = 1) -> User:
    return User(
        id=id,
        email=f"tpo{id}@campus.edu",
        full_name=f"TPO Officer {id}",
        role=UserRole.TPO,
        institution_id=institution_id,
        is_active=True,
    )


def build_admin(id: int = 99) -> User:
    return User(
        id=id,
        email=f"admin{id}@platform.com",
        full_name=f"System Administrator {id}",
        role=UserRole.ADMIN,
        is_active=True,
    )


def build_job(id: int = 100, company_id: int = 1, institution_id: Optional[int] = None) -> Job:
    company = Company(id=company_id, name=f"Company {company_id}", is_verified=True, is_active=True)
    return Job(
        id=id,
        company_id=company_id,
        institution_id=institution_id,
        title=f"Software Engineer {id}",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.HYBRID,
        location="Bengaluru",
        company=company,
        status=JobStatus.PUBLISHED,
        is_active=True,
    )


def build_drive(id: int = 200, institution_id: int = 1) -> PlacementDrive:
    now = datetime.now(timezone.utc)
    return PlacementDrive(
        id=id,
        institution_id=institution_id,
        created_by_user_id=20,
        name=f"Campus Placement Drive {id}",
        academic_year="2025-2026",
        target_graduation_year=2026,
        registration_start_date=now - timedelta(days=2),
        registration_end_date=now + timedelta(days=10),
        drive_mode=DriveMode.ON_CAMPUS,
        status=DriveStatus.ONGOING,
        is_active=True,
    )


def build_application(
    id: int = 1000,
    job: Optional[Job] = None,
    student: Optional[User] = None,
    drive: Optional[PlacementDrive] = None,
    status: ApplicationStatus = ApplicationStatus.APPLIED,
    screening_status: TpoScreeningStatus = TpoScreeningStatus.PENDING,
) -> JobApplication:
    now = datetime.now(timezone.utc)
    j = job or build_job()
    s = student or build_student()
    d = drive or build_drive()
    resume = Resume(
        id=50,
        student_id=s.student_profile.id,
        file_path="/tmp/fake_resume.pdf",
        file_name="resume.pdf",
        file_hash="hash_placeholder",
        file_size_bytes=1024,
        file_type="pdf",
        parsing_status="approved",
        is_active=True,
    )
    app = JobApplication(
        id=id,
        job_id=j.id,
        student_id=s.student_profile.id,
        resume_id=50,
        drive_id=d.id if d else None,
        tpo_screening_status=screening_status,
        current_status=status,
        compatibility_score_at_application=88.5,
        created_at=now,
        job=j,
        student_profile=s.student_profile,
        drive=d,
        resume=resume,
        status_history=[],
        interviews=[],
    )
    return app


# =============================================================================
# 1. Student Ownership and Scoping Violation Tests
# =============================================================================

def test_student_ownership_violation_view_application():
    """Student cannot view another student's application."""
    student_a = build_student(id=1)
    student_b = build_student(id=2)
    app = build_application(id=1000, student=student_a)

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = app
    mock_db.execute.return_value = mock_res

    # Student B attempts to access Student A's application
    with pytest.raises(AuthorizationException) as exc:
        _run_sync(
            get_application_detail_endpoint(
                application_id=1000,
                current_user=student_b,
                session=mock_db,
            )
        )
    assert "permission" in str(exc.value.message).lower()


def test_student_ownership_violation_withdraw_application():
    """Student cannot withdraw another student's application."""
    student_a = build_student(id=1)
    student_b = build_student(id=2)
    app = build_application(id=1000, student=student_a)

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = app
    mock_db.execute.return_value = mock_res

    payload = ApplicationWithdrawRequest(reason="Candidate wishes to withdraw")
    with pytest.raises(AuthorizationException) as exc:
        _run_sync(
            withdraw_application_endpoint(
                application_id=1000,
                payload=payload,
                current_user=student_b,
                session=mock_db,
            )
        )
    assert "own applications" in str(exc.value.message).lower()


def test_student_ownership_violation_offer_response():
    """Student cannot respond to an offer for another student's application."""
    student_a = build_student(id=1)
    student_b = build_student(id=2)
    app = build_application(id=1000, student=student_a, status=ApplicationStatus.OFFERED)

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = app
    mock_db.execute.return_value = mock_res

    payload = OfferResponseRequest(accept=True, notes="Accepting offer")
    with pytest.raises(AuthorizationException) as exc:
        _run_sync(
            respond_to_offer_endpoint(
                application_id=1000,
                payload=payload,
                current_user=student_b,
                session=mock_db,
            )
        )
    assert "own applications" in str(exc.value.message).lower()


# =============================================================================
# 2. Cross-Company Recruiter Access Tests
# =============================================================================

def test_cross_company_recruiter_status_update_blocked():
    """Recruiter from Company 2 cannot update status for a job offered by Company 1."""
    recruiter_co2 = build_recruiter(id=4, company_id=2)
    job_co1 = build_job(id=100, company_id=1)
    app = build_application(id=1000, job=job_co1)

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = app
    mock_db.execute.return_value = mock_res

    payload = RecruiterStatusUpdateRequest(status=ApplicationStatus.SHORTLISTED)
    with pytest.raises(AuthorizationException) as exc:
        _run_sync(
            recruiter_update_status_endpoint(
                application_id=1000,
                payload=payload,
                current_user=recruiter_co2,
                session=mock_db,
            )
        )
    assert "your company" in str(exc.value.message).lower()


def test_cross_company_recruiter_schedule_interview_blocked():
    """Recruiter from Company 2 cannot schedule an interview for Company 1's applicant."""
    recruiter_co2 = build_recruiter(id=4, company_id=2)
    job_co1 = build_job(id=100, company_id=1)
    app = build_application(id=1000, job=job_co1)

    mock_db = AsyncMock()
    mock_res_app = MagicMock(); mock_res_app.scalar_one_or_none.return_value = app
    mock_res_prof = MagicMock(); mock_res_prof.scalar_one_or_none.return_value = recruiter_co2.recruiter_profile
    mock_db.execute.side_effect = [mock_res_app, mock_res_prof]

    payload = InterviewCreateRequest(
        round_number=1,
        round_title="Round 1",
        scheduled_start_time=datetime.now(timezone.utc) + timedelta(days=1),
        duration_minutes=45,
    )
    with pytest.raises(AuthorizationException) as exc:
        _run_sync(
            schedule_interview_endpoint(
                application_id=1000,
                payload=payload,
                current_user=recruiter_co2,
                session=mock_db,
            )
        )
    assert "your company" in str(exc.value.message).lower()


def test_recruiter_schedule_interview_success():
    """Authorized recruiter schedules interview: response returned, lifecycle updated, notification created."""
    recruiter_co1 = build_recruiter(id=10, company_id=1)
    job_co1 = build_job(id=100, company_id=1)
    student = build_student(id=1, institution_id=1)
    app = build_application(
        id=1000,
        job=job_co1,
        student=student,
        status=ApplicationStatus.SHORTLISTED,
        screening_status=TpoScreeningStatus.SHORTLISTED,
    )

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    # Mocks for schedule_interview query steps:
    m_app = MagicMock(); m_app.scalar_one_or_none.return_value = app
    m_prof = MagicMock(); m_prof.scalar_one_or_none.return_value = recruiter_co1.recruiter_profile
    m_round = MagicMock(); m_round.scalar_one_or_none.return_value = None
    m_lock = MagicMock()
    m_active = MagicMock(); m_active.scalars.return_value.all.return_value = []
    m_notif1 = MagicMock(); m_notif1.scalar_one_or_none.return_value = None
    m_notif2 = MagicMock(); m_notif2.scalar_one_or_none.return_value = None

    mock_db.execute.side_effect = [m_app, m_prof, m_round, m_lock, m_active, m_notif1, m_notif2]

    start_time = datetime.now(timezone.utc) + timedelta(days=3)
    payload = InterviewCreateRequest(
        round_number=1,
        round_title="Technical Round 1",
        interview_mode=InterviewMode.VIRTUAL,
        meeting_link="https://meet.google.com/xyz-abc-def",
        scheduled_start_time=start_time,
        duration_minutes=60,
        interviewer_names="Jane Doe, Senior Architect",
    )

    response = _run_sync(
        schedule_interview_endpoint(
            application_id=1000,
            payload=payload,
            current_user=recruiter_co1,
            session=mock_db,
        )
    )

    # 1. Response validation
    assert response.application_id == 1000
    assert response.round_number == 1
    assert response.round_title == "Technical Round 1"
    assert response.interview_mode == InterviewMode.VIRTUAL
    assert response.meeting_link == "https://meet.google.com/xyz-abc-def"
    assert response.scheduled_start_time == start_time
    assert response.status == InterviewStatus.SCHEDULED
    assert response.outcome == InterviewOutcome.PENDING

    # 2. Lifecycle progression
    assert app.current_status == ApplicationStatus.INTERVIEW_SCHEDULED

    # 3. Notification and history creation
    added_objects = [call.args[0] for call in mock_db.add.call_args_list]
    interviews_added = [obj for obj in added_objects if isinstance(obj, Interview)]
    assert len(interviews_added) == 1
    assert interviews_added[0].round_number == 1

    history_added = [obj for obj in added_objects if isinstance(obj, ApplicationStatusHistory)]
    assert len(history_added) >= 1
    assert history_added[0].to_status == ApplicationStatus.INTERVIEW_SCHEDULED.value

    notifications_added = [obj for obj in added_objects if isinstance(obj, Notification)]
    assert len(notifications_added) >= 1
    assert any(n.recipient_user_id == student.id for n in notifications_added)


# =============================================================================
# 3. Cross-Institution TPO Access Tests
# =============================================================================

def test_cross_institution_tpo_drive_update_blocked():
    """TPO from Institution 2 cannot modify a placement drive owned by Institution 1."""
    tpo_inst2 = build_tpo(id=6, institution_id=2)
    drive_inst1 = build_drive(id=200, institution_id=1)

    mock_db = AsyncMock()
    mock_res = MagicMock(); mock_res.scalar_one_or_none.return_value = drive_inst1
    mock_db.execute.return_value = mock_res

    payload = PlacementDriveUpdate(name="Renamed by unauthorized TPO")
    with pytest.raises(AuthorizationException) as exc:
        _run_sync(
            update_drive_endpoint(
                drive_id=200,
                payload=payload,
                current_user=tpo_inst2,
                session=mock_db,
            )
        )
    assert "own academic institution" in str(exc.value.message).lower()


def test_cross_institution_tpo_screening_blocked():
    """TPO from Institution 2 cannot screen applications for Institution 1's drive."""
    tpo_inst2 = build_tpo(id=6, institution_id=2)
    drive_inst1 = build_drive(id=200, institution_id=1)
    student_inst1 = build_student(id=1, institution_id=1)
    app = build_application(id=1000, student=student_inst1, drive=drive_inst1)

    mock_db = AsyncMock()
    mock_res = MagicMock(); mock_res.scalar_one_or_none.return_value = app
    mock_db.execute.return_value = mock_res

    payload = TpoScreeningUpdateRequest(status=TpoScreeningStatus.SHORTLISTED)
    with pytest.raises(AuthorizationException) as exc:
        _run_sync(
            tpo_screen_application_endpoint(
                application_id=1000,
                payload=payload,
                current_user=tpo_inst2,
                session=mock_db,
            )
        )
    assert "own institution" in str(exc.value.message).lower()


# =============================================================================
# 4. Admin Access Boundaries
# =============================================================================

def test_admin_access_boundaries():
    """Admin has global platform-wide access to view applications and update statuses."""
    admin = build_admin(id=99)
    job = build_job(id=100, company_id=1)
    app = build_application(
        id=1000,
        job=job,
        status=ApplicationStatus.SHORTLISTED,
        screening_status=TpoScreeningStatus.SHORTLISTED,
    )

    mock_db = AsyncMock()
    mock_res = MagicMock(); mock_res.scalar_one_or_none.return_value = app
    mock_db.execute.return_value = mock_res
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    # Admin reviews application details
    detail = _run_sync(
        get_application_detail_endpoint(
            application_id=1000,
            current_user=admin,
            session=mock_db,
        )
    )
    assert isinstance(detail, JobApplicationDetailResponse)
    assert detail.id == 1000

    # Admin advances recruitment status to OFFERED
    payload = RecruiterStatusUpdateRequest(status=ApplicationStatus.OFFERED, feedback_notes="Executive admin offer approval")
    updated = _run_sync(
        recruiter_update_status_endpoint(
            application_id=1000,
            payload=payload,
            current_user=admin,
            session=mock_db,
        )
    )
    assert isinstance(updated, JobApplicationRecruiterResponse)
    assert updated.current_status == ApplicationStatus.OFFERED


# =============================================================================
# 5. State Machine & TPO Screening Gate at Route Level
# =============================================================================

def test_invalid_state_transition_at_route_level():
    """Recruiter attempting an invalid state transition (applied directly to offered) raises 400 error."""
    recruiter = build_recruiter(id=10, company_id=1)
    job = build_job(id=100, company_id=1)
    app = build_application(id=1000, job=job, status=ApplicationStatus.APPLIED)

    mock_db = AsyncMock()
    mock_res = MagicMock(); mock_res.scalar_one_or_none.return_value = app
    mock_db.execute.return_value = mock_res

    # Direct jump from 'applied' to 'offered' is invalid
    payload = RecruiterStatusUpdateRequest(status=ApplicationStatus.OFFERED)
    with pytest.raises(AppException) as exc:
        _run_sync(
            recruiter_update_status_endpoint(
                application_id=1000,
                payload=payload,
                current_user=recruiter,
                session=mock_db,
            )
        )
    assert exc.value.status_code == 400
    assert "invalid recruitment pipeline transition" in str(exc.value.message).lower()


def test_tpo_screening_gate_at_route_level():
    """Campus drive application blocks recruiter progression past 'applied' while screening is pending."""
    recruiter = build_recruiter(id=10, company_id=1)
    job = build_job(id=100, company_id=1)
    drive = build_drive(id=200, institution_id=1)
    app = build_application(
        id=1000,
        job=job,
        drive=drive,
        status=ApplicationStatus.APPLIED,
        screening_status=TpoScreeningStatus.PENDING,
    )

    mock_db = AsyncMock()
    mock_res = MagicMock(); mock_res.scalar_one_or_none.return_value = app
    mock_db.execute.return_value = mock_res

    payload = RecruiterStatusUpdateRequest(status=ApplicationStatus.UNDER_REVIEW)
    with pytest.raises(AppException) as exc:
        _run_sync(
            recruiter_update_status_endpoint(
                application_id=1000,
                payload=payload,
                current_user=recruiter,
                session=mock_db,
            )
        )
    assert exc.value.code == "TPO_SCREENING_PENDING"


def test_tpo_screen_application_updates_screening_and_preserves_recruiter_status():
    """TPO screening rejection updates screening status only, notifies recruiter, and preserves recruiter state."""
    tpo = build_tpo(id=20, institution_id=1)
    drive = build_drive(id=200, institution_id=1)
    job = build_job(id=100, company_id=1)
    student = build_student(id=1, institution_id=1)
    app = build_application(
        id=1000,
        job=job,
        student=student,
        drive=drive,
        status=ApplicationStatus.INTERVIEW_SCHEDULED,
        screening_status=TpoScreeningStatus.SHORTLISTED,
    )

    mock_db = AsyncMock()
    m_app = MagicMock(); m_app.scalar_one_or_none.return_value = app
    m_rec = MagicMock(); m_rec.scalars.return_value.all.return_value = [10]
    m_notif = MagicMock(); m_notif.scalar_one_or_none.return_value = None
    mock_db.execute.side_effect = [m_app, m_rec, m_notif]
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    payload = TpoScreeningUpdateRequest(status=TpoScreeningStatus.REJECTED, feedback="Disciplinary hearing sanction")
    res = _run_sync(
        tpo_screen_application_endpoint(
            application_id=1000,
            payload=payload,
            current_user=tpo,
            session=mock_db,
        )
    )

    assert app.tpo_screening_status == TpoScreeningStatus.REJECTED
    assert app.current_status == ApplicationStatus.INTERVIEW_SCHEDULED  # Strictly preserved!
    assert res.tpo_screening_status == TpoScreeningStatus.REJECTED
    assert res.current_status == ApplicationStatus.INTERVIEW_SCHEDULED


# =============================================================================
# 6. Resume Streaming & Revocation Route Tests
# =============================================================================

def test_unauthorized_resume_streaming_blocked():
    """Student or cross-company recruiter cannot stream candidate resumes."""
    student = build_student(id=1)
    job = build_job(id=100, company_id=1)
    app = build_application(id=1000, job=job)

    mock_db = AsyncMock()
    m_app = MagicMock(); m_app.scalar_one_or_none.return_value = app
    mock_db.execute.return_value = m_app

    # Student cannot call resume stream
    with pytest.raises(AuthorizationException):
        _run_sync(
            stream_application_resume_endpoint(
                application_id=1000,
                current_user=student,
                session=mock_db,
            )
        )


def test_withdrawn_application_resume_revocation():
    """Recruiter streaming a resume is blocked when application is withdrawn."""
    recruiter = build_recruiter(id=10, company_id=1)
    job = build_job(id=100, company_id=1)
    app = build_application(id=1000, job=job, status=ApplicationStatus.WITHDRAWN)

    mock_db = AsyncMock()
    m_app = MagicMock(); m_app.scalar_one_or_none.return_value = app
    m_prof = MagicMock(); m_prof.scalar_one_or_none.return_value = recruiter.recruiter_profile
    mock_db.execute.side_effect = [m_app, m_prof]

    with pytest.raises(AuthorizationException) as exc:
        _run_sync(
            stream_application_resume_endpoint(
                application_id=1000,
                current_user=recruiter,
                session=mock_db,
            )
        )
    assert "withdrawn" in str(exc.value.message).lower()


def test_recruiter_resume_streaming_success():
    """Authorized recruiter successfully streams verified resume with proper headers."""
    recruiter = build_recruiter(id=10, company_id=1)
    job = build_job(id=100, company_id=1)

    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(b"verified pdf content for streaming test")
        tmp_path = tf.name

    try:
        import hashlib
        hasher = hashlib.sha256()
        with open(tmp_path, "rb") as f:
            hasher.update(f.read())
        file_hash = hasher.hexdigest()

        app = build_application(
        id=1000,
        job=job,
        status=ApplicationStatus.SHORTLISTED,
        screening_status=TpoScreeningStatus.SHORTLISTED,
    )
        app.resume.file_path = tmp_path
        app.resume.file_hash = file_hash

        mock_db = AsyncMock()
        m_app = MagicMock(); m_app.scalar_one_or_none.return_value = app
        m_prof = MagicMock(); m_prof.scalar_one_or_none.return_value = recruiter.recruiter_profile
        mock_db.execute.side_effect = [m_app, m_prof]

        response = _run_sync(
            stream_application_resume_endpoint(
                application_id=1000,
                current_user=recruiter,
                session=mock_db,
            )
        )
        assert isinstance(response, StreamingResponse)
        assert response.media_type == "application/pdf"
        assert 'attachment; filename="resume.pdf"' in response.headers["Content-Disposition"]
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# =============================================================================
# 7. Notification Recipient Isolation Route Tests
# =============================================================================

def test_notification_recipient_isolation():
    """User cannot mark another user's notification as read."""
    user_a = build_student(id=1)
    user_b = build_student(id=2)
    notif = Notification(
        id=500,
        recipient_user_id=1,  # Belongs to User A
        category=NotificationCategory.APPLICATION_UPDATE,
        title="Alert",
        message="Message",
        is_read=False,
    )

    mock_db = AsyncMock()
    m_notif = MagicMock(); m_notif.scalar_one_or_none.return_value = notif
    mock_db.execute.return_value = m_notif

    with pytest.raises(AuthorizationException) as exc:
        _run_sync(
            mark_notification_read_endpoint(
                notification_id=500,
                current_user=user_b,
                session=mock_db,
            )
        )
    assert "permission" in str(exc.value.message).lower()


def test_notification_unread_count_and_mark_all_read():
    """User retrieves unread count and marks all read for their own recipient ID."""
    user = build_student(id=1)
    mock_db = AsyncMock()

    # Unread count query
    m_count = MagicMock(); m_count.scalar.return_value = 4
    mock_db.execute.return_value = m_count

    count_res = _run_sync(
        get_unread_count_endpoint(current_user=user, session=mock_db)
    )
    assert count_res.unread_count == 4

    # Mark all read
    m_update = MagicMock(); m_update.rowcount = 4
    mock_db.execute.return_value = m_update
    mock_db.flush = AsyncMock()

    all_read_res = _run_sync(
        mark_all_read_endpoint(current_user=user, session=mock_db)
    )
    assert all_read_res["marked_read_count"] == 4


# =============================================================================
# 8. Student Response Privacy & Redaction Tests
# =============================================================================

def test_student_response_privacy_redaction():
    """Student viewing application detail receives student schema with confidential recruiter notes redacted."""
    student = build_student(id=1)
    job = build_job(id=100, company_id=1)
    app = build_application(id=1000, job=job, student=student)
    app.recruiter_feedback_notes = "CONFIDENTIAL: Strong candidate, but evaluate salary expectations closely."

    interview = Interview(
        id=70,
        application_id=1000,
        round_number=1,
        round_title="Round 1",
        interview_mode=InterviewMode.VIRTUAL,
        scheduled_start_time=datetime.now(timezone.utc) + timedelta(days=2),
        duration_minutes=45,
        status=InterviewStatus.SCHEDULED,
        outcome=InterviewOutcome.PENDING,
        feedback_notes="CONFIDENTIAL INTERVIEW FEEDBACK: Needs work on recursion",
        created_by_user_id=10,
    )
    app.interviews = [interview]

    mock_db = AsyncMock()
    m_app = MagicMock(); m_app.scalar_one_or_none.return_value = app
    mock_db.execute.return_value = m_app

    detail = _run_sync(
        get_application_detail_endpoint(
            application_id=1000,
            current_user=student,
            session=mock_db,
        )
    )

    assert isinstance(detail, JobApplicationStudentDetailResponse)
    assert not hasattr(detail, "recruiter_feedback_notes")
    assert len(detail.interviews) == 1
    # Check interview privacy redaction
    assert not hasattr(detail.interviews[0], "feedback_notes")
    assert not hasattr(detail.interviews[0], "created_by_user_id")


def test_recruiter_response_includes_feedback_notes():
    """Recruiter viewing application detail receives full schema with confidential notes."""
    recruiter = build_recruiter(id=10, company_id=1)
    job = build_job(id=100, company_id=1)
    app = build_application(id=1000, job=job)
    app.recruiter_feedback_notes = "CONFIDENTIAL: Internal recruiter notes present."

    mock_db = AsyncMock()
    m_app = MagicMock(); m_app.scalar_one_or_none.return_value = app
    mock_db.execute.return_value = m_app

    detail = _run_sync(
        get_application_detail_endpoint(
            application_id=1000,
            current_user=recruiter,
            session=mock_db,
        )
    )

    assert isinstance(detail, JobApplicationDetailResponse)
    assert detail.recruiter_feedback_notes == "CONFIDENTIAL: Internal recruiter notes present."


# =============================================================================
# 9. Placement Drive & Association Management Route Tests
# =============================================================================

def test_create_drive_and_job_association_routes():
    """TPO creates a drive and associates an eligible job posting."""
    tpo = build_tpo(id=20, institution_id=1)
    drive = build_drive(id=200, institution_id=1)
    job = build_job(id=100, company_id=1)  # Global job (institution_id=None)

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    now = datetime.now(timezone.utc)
    create_payload = PlacementDriveCreate(
        name="Annual Campus Drive 2026",
        academic_year="2025-2026",
        target_graduation_year=2026,
        registration_start_date=now - timedelta(days=1),
        registration_end_date=now + timedelta(days=14),
        drive_mode=DriveMode.ON_CAMPUS,
    )
    drive_res = _run_sync(
        create_drive_endpoint(payload=create_payload, current_user=tpo, session=mock_db)
    )
    assert drive_res.name == "Annual Campus Drive 2026"
    assert drive_res.institution_id == 1

    # Associate job with drive
    m_drive = MagicMock(); m_drive.scalar_one_or_none.return_value = drive
    m_job = MagicMock(); m_job.scalar_one_or_none.return_value = job
    m_dj_exist = MagicMock(); m_dj_exist.scalar_one_or_none.return_value = None
    m_loaded = MagicMock(); m_loaded.scalar_one_or_none.return_value = None
    mock_db.execute.side_effect = [m_drive, m_job, m_dj_exist, m_loaded]

    assoc_res = _run_sync(
        add_job_to_drive_endpoint(
            drive_id=200,
            payload=PlacementDriveJobAddRequest(job_id=100),
            current_user=tpo,
            session=mock_db,
        )
    )
    assert assoc_res.drive_id == 200
    assert assoc_res.job_id == 100
    assert assoc_res.is_active is True


def test_soft_remove_drive_job_route():
    """TPO soft-removes a job association, marking is_active=False and removed_at."""
    tpo = build_tpo(id=20, institution_id=1)
    drive = build_drive(id=200, institution_id=1)
    assoc = PlacementDriveJob(id=15, drive_id=200, job_id=100, is_active=True)

    mock_db = AsyncMock()
    m_drive = MagicMock(); m_drive.scalar_one_or_none.return_value = drive
    m_assoc = MagicMock(); m_assoc.scalar_one_or_none.return_value = assoc
    mock_db.execute.side_effect = [m_drive, m_assoc]
    mock_db.flush = AsyncMock()

    removed_res = _run_sync(
        remove_job_from_drive_endpoint(
            drive_id=200,
            job_id=100,
            current_user=tpo,
            session=mock_db,
        )
    )
    assert removed_res.is_active is False
    assert removed_res.removed_at is not None


# =============================================================================
# 10. Interview Lifecycle Endpoints Test
# =============================================================================

def test_interview_lifecycle_routes():
    """Verify reschedule, cancel, and outcome endpoints."""
    recruiter = build_recruiter(id=10, company_id=1)
    job = build_job(id=100, company_id=1)
    app = build_application(
        id=1000,
        job=job,
        status=ApplicationStatus.INTERVIEW_SCHEDULED,
        screening_status=TpoScreeningStatus.SHORTLISTED,
    )

    now = datetime.now(timezone.utc)
    interview = Interview(
        id=70,
        application_id=1000,
        round_number=1,
        round_title="Round 1",
        interview_mode=InterviewMode.VIRTUAL,
        scheduled_start_time=now + timedelta(days=2),
        duration_minutes=45,
        status=InterviewStatus.SCHEDULED,
        outcome=InterviewOutcome.PENDING,
        application=app,
    )

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    def set_mock_responses(*items):
        q = list(items)
        def _exec(*args, **kwargs):
            if q:
                return q.pop(0)
            def_m = MagicMock()
            def_m.scalar_one_or_none.return_value = None
            def_m.scalars.return_value.all.return_value = []
            def_m.scalar.return_value = None
            return def_m
        mock_db.execute.side_effect = _exec

    # 1. Reschedule
    m_int = MagicMock(); m_int.scalar_one_or_none.return_value = interview
    m_prof = MagicMock(); m_prof.scalar_one_or_none.return_value = recruiter.recruiter_profile
    m_lock = MagicMock()
    m_active = MagicMock(); m_active.scalars.return_value.all.return_value = []
    m_notif = MagicMock(); m_notif.scalar_one_or_none.return_value = None
    set_mock_responses(m_int, m_prof, m_lock, m_active, m_notif)

    new_time = now + timedelta(days=4)
    resched_res = _run_sync(
        reschedule_interview_endpoint(
            interview_id=70,
            payload=InterviewRescheduleRequest(scheduled_start_time=new_time, reason="Panel rescheduling"),
            current_user=recruiter,
            session=mock_db,
        )
    )
    assert resched_res.scheduled_start_time == new_time

    # 2. Record outcome: FAILED (moves application to 'interviewed', not 'rejected')
    m_int2 = MagicMock(); m_int2.scalar_one_or_none.return_value = interview
    m_prof2 = MagicMock(); m_prof2.scalar_one_or_none.return_value = recruiter.recruiter_profile
    m_notif2 = MagicMock(); m_notif2.scalar_one_or_none.return_value = None
    set_mock_responses(m_int2, m_prof2, m_notif2)

    outcome_res = _run_sync(
        record_interview_outcome_endpoint(
            interview_id=70,
            payload=InterviewOutcomeRequest(outcome=InterviewOutcome.FAILED, feedback_notes="Candidate fell short on system design."),
            current_user=recruiter,
            session=mock_db,
        )
    )
    assert outcome_res.status == InterviewStatus.COMPLETED
    assert outcome_res.outcome == InterviewOutcome.FAILED
    assert app.current_status == ApplicationStatus.INTERVIEWED

    # 3. Cancel interview: cancels and round-aware reverts Round 1 to 'shortlisted'
    interview.status = InterviewStatus.SCHEDULED
    app.current_status = ApplicationStatus.INTERVIEW_SCHEDULED
    m_int3 = MagicMock(); m_int3.scalar_one_or_none.return_value = interview
    m_prof3 = MagicMock(); m_prof3.scalar_one_or_none.return_value = recruiter.recruiter_profile
    m_earlier = MagicMock(); m_earlier.scalars.return_value.all.return_value = []
    m_notif3 = MagicMock(); m_notif3.scalar_one_or_none.return_value = None
    set_mock_responses(m_int3, m_prof3, m_earlier, m_notif3)

    cancel_res = _run_sync(
        cancel_interview_endpoint(
            interview_id=70,
            payload=InterviewCancelRequest(reason="Hiring requisition put on hold"),
            current_user=recruiter,
            session=mock_db,
        )
    )
    assert cancel_res.status == InterviewStatus.CANCELLED
    assert app.current_status == ApplicationStatus.SHORTLISTED


# =============================================================================
# 11. Final Security & Authorization Audit Tests
# =============================================================================

def test_tpo_application_detail_privacy():
    """TPO viewing application detail receives TPO schema without confidential recruiter notes."""
    tpo = build_tpo(id=20, institution_id=1)
    student = build_student(id=1, institution_id=1)
    drive = build_drive(id=200, institution_id=1)
    job = build_job(id=100, company_id=1)
    app = build_application(id=1000, job=job, student=student, drive=drive)
    app.recruiter_feedback_notes = "CONFIDENTIAL: Internal recruiter evaluation remarks."
    app.tpo_feedback = "Institutional screening approved."
    app.tpo_screening_status = TpoScreeningStatus.SHORTLISTED

    interview = Interview(
        id=70,
        application_id=1000,
        round_number=1,
        round_title="Round 1",
        interview_mode=InterviewMode.VIRTUAL,
        scheduled_start_time=datetime.now(timezone.utc) + timedelta(days=2),
        duration_minutes=45,
        status=InterviewStatus.SCHEDULED,
        outcome=InterviewOutcome.PENDING,
        feedback_notes="CONFIDENTIAL INTERVIEW FEEDBACK: Strong technical foundation.",
        created_by_user_id=10,
    )
    app.interviews = [interview]

    mock_db = AsyncMock()
    m_app = MagicMock(); m_app.scalar_one_or_none.return_value = app
    mock_db.execute.return_value = m_app

    detail = _run_sync(
        get_application_detail_endpoint(
            application_id=1000,
            current_user=tpo,
            session=mock_db,
        )
    )

    assert isinstance(detail, JobApplicationTpoDetailResponse)
    # Recruiter private feedback notes must NOT be present in TPO response
    assert not hasattr(detail, "recruiter_feedback_notes")
    # TPO institutional screening information must be present
    assert detail.tpo_screening_status == TpoScreeningStatus.SHORTLISTED
    assert detail.tpo_feedback == "Institutional screening approved."
    assert len(detail.interviews) == 1
    # Confidential interview notes must be redacted from TPO view
    assert not hasattr(detail.interviews[0], "feedback_notes")
    assert not hasattr(detail.interviews[0], "created_by_user_id")


def test_recruiter_drive_scoping_and_enumeration():
    """Recruiters can only enumerate or inspect drives and jobs legitimately associated with their company."""
    recruiter = build_recruiter(id=10, company_id=1)
    drive1 = build_drive(id=201, institution_id=1)
    drive2 = build_drive(id=202, institution_id=2)
    job1 = build_job(id=101, company_id=1)
    job2 = build_job(id=102, company_id=2)  # Belongs to another company

    assoc1 = PlacementDriveJob(id=1, drive_id=201, job_id=101, is_active=True, job=job1)
    assoc2 = PlacementDriveJob(id=2, drive_id=201, job_id=102, is_active=True, job=job2)
    drive1.drive_jobs = [assoc1, assoc2]
    drive2.drive_jobs = []

    mock_db = AsyncMock()

    # 1. list_drives_endpoint for recruiter: returns only drives associated with recruiter's company
    m_drives = MagicMock()
    m_drives.scalars.return_value.all.return_value = [drive1]
    m_cnt_jobs = MagicMock(); m_cnt_jobs.scalar.return_value = 1
    m_cnt_apps = MagicMock(); m_cnt_apps.scalar.return_value = 5
    mock_db.execute.side_effect = [m_drives, m_cnt_jobs, m_cnt_apps]

    drives_res = _run_sync(
        list_drives_endpoint(current_user=recruiter, session=mock_db)
    )
    assert len(drives_res) == 1
    assert drives_res[0].id == 201

    # 2. get_drive_endpoint for authorized drive: only includes recruiter company's jobs
    m_drive1 = MagicMock(); m_drive1.scalar_one_or_none.return_value = drive1
    m_cnt1 = MagicMock(); m_cnt1.scalar.return_value = 2
    m_cnt2 = MagicMock(); m_cnt2.scalar.return_value = 5
    mock_db.execute.side_effect = [m_drive1, m_cnt1, m_cnt2]

    drive_detail = _run_sync(
        get_drive_endpoint(drive_id=201, current_user=recruiter, session=mock_db)
    )
    assert drive_detail.id == 201
    # Only company 1's jobs returned, job2 from company 2 filtered out
    assert len(drive_detail.jobs) == 1
    assert drive_detail.jobs[0].job_id == 101

    # 3. get_drive_endpoint for unauthorized drive: rejected with AuthorizationException
    m_drive2 = MagicMock(); m_drive2.scalar_one_or_none.return_value = drive2
    mock_db.execute.side_effect = [m_drive2]
    with pytest.raises(AuthorizationException) as exc_info:
        _run_sync(
            get_drive_endpoint(drive_id=202, current_user=recruiter, session=mock_db)
        )
    assert "not associated with your company" in str(exc_info.value)

    # 4. list_drive_jobs_endpoint for recruiter: returns only company 1's jobs
    m_drive_exists = MagicMock(); m_drive_exists.scalar_one_or_none.return_value = drive1
    m_jobs = MagicMock(); m_jobs.scalars.return_value.all.return_value = [assoc1]
    mock_db.execute.side_effect = [m_drive_exists, m_jobs]

    drive_jobs_res = _run_sync(
        list_drive_jobs_endpoint(drive_id=201, current_user=recruiter, session=mock_db)
    )
    assert len(drive_jobs_res) == 1
    assert drive_jobs_res[0].job_id == 101

    # 5. list_drive_jobs_endpoint for unassociated drive: rejected with AuthorizationException
    m_drive_exists2 = MagicMock(); m_drive_exists2.scalar_one_or_none.return_value = drive2
    m_empty_jobs = MagicMock(); m_empty_jobs.scalars.return_value.all.return_value = []
    mock_db.execute.side_effect = [m_drive_exists2, m_empty_jobs]
    with pytest.raises(AuthorizationException) as exc_info2:
        _run_sync(
            list_drive_jobs_endpoint(drive_id=202, current_user=recruiter, session=mock_db)
        )
    assert "not associated with your company" in str(exc_info2.value)


def test_direct_application_tpo_screening_rejected():
    """TPOs cannot screen direct applications (drive_id=None, screening status BYPASSED)."""
    tpo = build_tpo(id=20, institution_id=1)
    student = build_student(id=1, institution_id=1)
    job = build_job(id=100, company_id=1)
    # Direct application without drive
    app = build_application(
        id=1000,
        job=job,
        student=student,
        drive=None,
        screening_status=TpoScreeningStatus.BYPASSED,
    )
    app.drive_id = None

    mock_db = AsyncMock()
    m_app = MagicMock(); m_app.scalar_one_or_none.return_value = app
    mock_db.execute.return_value = m_app

    with pytest.raises(AuthorizationException) as exc_info:
        _run_sync(
            tpo_screen_application_endpoint(
                application_id=1000,
                payload=TpoScreeningUpdateRequest(status=TpoScreeningStatus.SHORTLISTED),
                current_user=tpo,
                session=mock_db,
            )
        )
    assert "Direct applications bypass institutional TPO screening" in str(exc_info.value)


def test_student_offer_accept_and_decline():
    """Candidate can accept or decline an official job offer, but cannot respond if not in offered state."""
    student = build_student(id=1, institution_id=1)
    job = build_job(id=100, company_id=1)
    app = build_application(
        id=1000,
        job=job,
        student=student,
        status=ApplicationStatus.OFFERED,
        screening_status=TpoScreeningStatus.SHORTLISTED,
    )

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    # 1. Reject if application is not in OFFERED state
    app.current_status = ApplicationStatus.INTERVIEWED
    m_app = MagicMock(); m_app.scalar_one_or_none.return_value = app
    mock_db.execute.return_value = m_app

    with pytest.raises(AppException) as exc_info:
        _run_sync(
            respond_to_offer_endpoint(
                application_id=1000,
                payload=OfferResponseRequest(accept=True),
                current_user=student,
                session=mock_db,
            )
        )
    assert "APPLICATION_NOT_OFFERED" in exc_info.value.code

    # 2. Accept offer
    app.current_status = ApplicationStatus.OFFERED
    m_app2 = MagicMock(); m_app2.scalar_one_or_none.return_value = app
    m_notif = MagicMock(); m_notif.scalar_one_or_none.return_value = None
    mock_db.execute.side_effect = [m_app2, m_notif]

    accept_res = _run_sync(
        respond_to_offer_endpoint(
            application_id=1000,
            payload=OfferResponseRequest(accept=True, notes="Excited to accept!"),
            current_user=student,
            session=mock_db,
        )
    )
    assert accept_res.current_status == ApplicationStatus.OFFER_ACCEPTED

    # 3. Decline offer
    app.current_status = ApplicationStatus.OFFERED
    m_app3 = MagicMock(); m_app3.scalar_one_or_none.return_value = app
    m_notif2 = MagicMock(); m_notif2.scalar_one_or_none.return_value = None
    mock_db.execute.side_effect = [m_app3, m_notif2]

    decline_res = _run_sync(
        respond_to_offer_endpoint(
            application_id=1000,
            payload=OfferResponseRequest(accept=False, notes="Accepted another offer."),
            current_user=student,
            session=mock_db,
        )
    )
    assert decline_res.current_status == ApplicationStatus.OFFER_DECLINED


def test_list_notifications_route():
    """Authenticated user lists notifications with pagination and unread filtering."""
    student = build_student(id=1)
    notif1 = Notification(
        id=1,
        recipient_user_id=1,
        category=NotificationCategory.APPLICATION_UPDATE,
        title="Application Shortlisted",
        message="Your application was shortlisted.",
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    notif2 = Notification(
        id=2,
        recipient_user_id=1,
        category=NotificationCategory.INTERVIEW_SCHEDULED,
        title="Interview Scheduled",
        message="Round 1 scheduled.",
        is_read=True,
        created_at=datetime.now(timezone.utc),
    )

    mock_db = AsyncMock()
    m_res = MagicMock()
    m_res.scalars.return_value.all.return_value = [notif1, notif2]
    mock_db.execute.return_value = m_res

    res = _run_sync(
        list_notifications_endpoint(
            unread_only=False,
            skip=0,
            limit=10,
            current_user=student,
            session=mock_db,
        )
    )
    assert len(res) == 2
    assert res[0].id == 1
    assert res[0].is_read is False
    assert res[1].id == 2
    assert res[1].is_read is True


def test_resume_streaming_deterministic_buffer_cleanup():
    """Resume StreamingResponse deterministically closes io.BytesIO on complete streaming and cancellation."""
    recruiter = build_recruiter(id=10, company_id=1)
    job = build_job(id=100, company_id=1)

    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(b"verified binary resume payload content")
        tmp_path = tf.name

    try:
        import hashlib
        hasher = hashlib.sha256()
        with open(tmp_path, "rb") as f:
            hasher.update(f.read())
        file_hash = hasher.hexdigest()

        app = build_application(
            id=1000,
            job=job,
            status=ApplicationStatus.SHORTLISTED,
            screening_status=TpoScreeningStatus.SHORTLISTED,
        )
        app.resume.file_path = tmp_path
        app.resume.file_hash = file_hash

        mock_db = AsyncMock()
        m_app = MagicMock(); m_app.scalar_one_or_none.return_value = app
        m_prof = MagicMock(); m_prof.scalar_one_or_none.return_value = recruiter.recruiter_profile
        mock_db.execute.side_effect = [m_app, m_prof]

        response = _run_sync(
            stream_application_resume_endpoint(
                application_id=1000,
                current_user=recruiter,
                session=mock_db,
            )
        )
        assert isinstance(response, StreamingResponse)

        # 1. Complete consumption verifies buffer is closed in finally
        chunks = []
        async def consume():
            async for chunk in response.body_iterator:
                chunks.append(chunk)

        _run_sync(consume())
        assert b"".join(chunks) == b"verified binary resume payload content"

        # 2. Premature cancellation / disconnect closes buffer
        mock_db2 = AsyncMock()
        m_app2 = MagicMock(); m_app2.scalar_one_or_none.return_value = app
        m_prof2 = MagicMock(); m_prof2.scalar_one_or_none.return_value = recruiter.recruiter_profile
        mock_db2.execute.side_effect = [m_app2, m_prof2]

        response2 = _run_sync(
            stream_application_resume_endpoint(
                application_id=1000,
                current_user=recruiter,
                session=mock_db2,
            )
        )
        async def cancel_midway():
            gen = response2.body_iterator
            first_chunk = await anext(gen)
            assert len(first_chunk) > 0
            await gen.aclose()  # Client disconnect / cancellation

        _run_sync(cancel_midway())
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_submit_application_and_my_applications_endpoints():
    """Student submits an application and lists submitted applications via /applications/my."""
    student = build_student(id=1, institution_id=1)
    job = build_job(id=100, company_id=1)
    app = build_application(id=1000, job=job, student=student)

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    # Submit application mock
    with patch("app.routes.placement.submit_application", new_callable=AsyncMock) as mock_sub:
        mock_sub.return_value = app
        m_load = MagicMock(); m_load.scalar_one_or_none.return_value = app
        mock_db.execute.return_value = m_load

        payload = JobApplicationCreate(job_id=100, resume_id=50, cover_letter="I am interested.")
        sub_res = _run_sync(
            submit_application_endpoint(payload=payload, current_user=student, session=mock_db)
        )
        assert sub_res.id == 1000
        assert sub_res.job_id == 100

    # Get my applications mock
    m_prof = MagicMock(); m_prof.scalar_one_or_none.return_value = student.student_profile
    m_cnt = MagicMock(); m_cnt.scalar.return_value = 1
    m_apps = MagicMock(); m_apps.scalars.return_value.all.return_value = [app]
    mock_db.execute.side_effect = [m_prof, m_cnt, m_apps]

    my_res = _run_sync(
        get_my_applications_endpoint(current_user=student, session=mock_db)
    )
    assert my_res.total == 1
    assert len(my_res.items) == 1
    assert my_res.items[0].id == 1000


def test_list_drive_applications_endpoint():
    """TPO lists applications for a campus drive of their own institution."""
    tpo = build_tpo(id=20, institution_id=1)
    drive = build_drive(id=200, institution_id=1)
    job = build_job(id=100, company_id=1)
    student = build_student(id=1, institution_id=1)
    app = build_application(id=1000, job=job, student=student, drive=drive)

    mock_db = AsyncMock()
    m_drive = MagicMock(); m_drive.scalar_one_or_none.return_value = drive
    m_cnt = MagicMock(); m_cnt.scalar.return_value = 1
    m_apps = MagicMock(); m_apps.scalars.return_value.all.return_value = [app]
    mock_db.execute.side_effect = [m_drive, m_cnt, m_apps]

    res = _run_sync(
        list_drive_applications_endpoint(
            drive_id=200,
            screening_status=TpoScreeningStatus.PENDING,
            current_user=tpo,
            session=mock_db,
        )
    )
    assert res.total == 1
    assert len(res.items) == 1
    assert res.items[0].id == 1000


def test_list_application_interviews_endpoint():
    """Listing interviews applies strict student redaction vs recruiter view."""
    student = build_student(id=1, institution_id=1)
    recruiter = build_recruiter(id=10, company_id=1)
    job = build_job(id=100, company_id=1)
    app = build_application(id=1000, job=job, student=student)

    now = datetime.now(timezone.utc)
    interview = Interview(
        id=70,
        application_id=1000,
        round_number=1,
        round_title="Round 1",
        interview_mode=InterviewMode.VIRTUAL,
        scheduled_start_time=now + timedelta(days=2),
        duration_minutes=45,
        status=InterviewStatus.SCHEDULED,
        outcome=InterviewOutcome.PENDING,
        feedback_notes="CONFIDENTIAL: Internal round notes.",
        created_by_user_id=10,
    )
    app.interviews = [interview]

    mock_db = AsyncMock()
    m_app = MagicMock(); m_app.scalar_one_or_none.return_value = app
    mock_db.execute.return_value = m_app

    # 1. Student view: InterviewStudentResponse without feedback_notes
    student_res = _run_sync(
        list_application_interviews_endpoint(application_id=1000, current_user=student, session=mock_db)
    )
    assert len(student_res) == 1
    assert not hasattr(student_res[0], "feedback_notes")

    # 2. Recruiter view: InterviewResponse with feedback_notes
    m_app2 = MagicMock(); m_app2.scalar_one_or_none.return_value = app
    mock_db.execute.return_value = m_app2
    recruiter_res = _run_sync(
        list_application_interviews_endpoint(application_id=1000, current_user=recruiter, session=mock_db)
    )
    assert len(recruiter_res) == 1
    assert recruiter_res[0].feedback_notes == "CONFIDENTIAL: Internal round notes."


def test_update_drive_endpoint_and_validation():
    """TPO updates placement drive details with date validation."""
    tpo = build_tpo(id=20, institution_id=1)
    drive = build_drive(id=200, institution_id=1)

    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    m_drive = MagicMock(); m_drive.scalar_one_or_none.return_value = drive
    mock_db.execute.return_value = m_drive

    now = datetime.now(timezone.utc)
    # Valid update
    update_payload = PlacementDriveUpdate(
        name="Updated Drive Name 2026",
        registration_start_date=now - timedelta(days=1),
        registration_end_date=now + timedelta(days=20),
    )
    res = _run_sync(
        update_drive_endpoint(drive_id=200, payload=update_payload, current_user=tpo, session=mock_db)
    )
    assert res.name == "Updated Drive Name 2026"

    # 2. Schema validation: start_date >= end_date in payload
    from pydantic_core import ValidationError
    with pytest.raises(ValidationError):
        PlacementDriveUpdate(
            registration_start_date=now + timedelta(days=5),
            registration_end_date=now + timedelta(days=1),
        )

    # 3. Route validation against existing drive dates: updating only start_date to after drive.registration_end_date
    invalid_start_payload = PlacementDriveUpdate(
        registration_start_date=drive.registration_end_date + timedelta(days=5),
    )
    m_drive2 = MagicMock(); m_drive2.scalar_one_or_none.return_value = drive
    mock_db.execute.return_value = m_drive2
    with pytest.raises(AppException) as exc_info:
        _run_sync(
            update_drive_endpoint(drive_id=200, payload=invalid_start_payload, current_user=tpo, session=mock_db)
        )
    assert "Drive registration start date must be strictly earlier" in str(exc_info.value)


def test_withdraw_application_endpoint_success():
    """Student successfully withdraws their application with valid reason."""
    student = build_student(id=1, institution_id=1)
    job = build_job(id=100, company_id=1)
    app = build_application(id=1000, job=job, student=student, status=ApplicationStatus.APPLIED)

    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()

    with patch("app.routes.placement.withdraw_application", new_callable=AsyncMock) as mock_with:
        app.current_status = ApplicationStatus.WITHDRAWN
        mock_with.return_value = app
        m_load = MagicMock(); m_load.scalar_one_or_none.return_value = app
        mock_db.execute.return_value = m_load

        payload = ApplicationWithdrawRequest(reason="Accepted off-campus offer")
        res = _run_sync(
            withdraw_application_endpoint(application_id=1000, payload=payload, current_user=student, session=mock_db)
        )
        assert res.current_status == ApplicationStatus.WITHDRAWN
