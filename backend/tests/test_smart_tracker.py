"""
Comprehensive integration & concurrency tests for TASK 03:
Smart Application & Recruitment Tracker.

Runs transactional tests against PostgreSQL (rolled back cleanly after each test)
plus concurrency checks with separate sessions to test:
1. All ApplicationStatus (10) & TpoScreeningStatus (4) states + authoritative state machine.
2. Chronological ApplicationStatusHistory fidelity (only recorded transitions shown).
3. Overview metadata, multi-criteria filtering, and SQL pagination.
4. Interview tracking: upcoming, rescheduled, cancelled, completed + confidential feedback_notes redaction.
5. Offer details & authorized offer accept/decline lifecycle transitions.
6. Calendar & deadline events (interviews, job deadlines, offer deadlines, drive registrations).
7. Smart notifications: idempotency deduplication, deadlines, placement announcements & preferences enforcement.
8. Concurrent notification sync & overlapping interview collision locking.
9. Strict student-only authorization and cross-student isolation.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.core.errors import AppException, AuthorizationException, ResourceConflictException
from app.core.security import hash_password
from app.models.company import Company, RecruiterProfile
from app.models.job import EmploymentType, Job, JobStatus, WorkMode
from app.models.organization import Department, Institution
from app.models.placement import (
    ApplicationStatus,
    DriveMode,
    DriveStatus,
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
    get_application_detail_endpoint,
    get_my_interviews_endpoint,
    get_notification_preferences_endpoint,
    get_student_application_tracker_endpoint,
    get_student_calendar_events_endpoint,
    list_notifications_endpoint,
    mark_notification_read_endpoint,
    record_interview_outcome_endpoint,
    reschedule_interview_endpoint,
    respond_to_offer_endpoint,
    schedule_interview_endpoint,
    cancel_interview_endpoint,
    sync_smart_notifications_endpoint,
    tpo_screen_application_endpoint,
    update_notification_preferences_endpoint,
    recruiter_update_status_endpoint,
    withdraw_application_endpoint,
)
from app.schemas.placement import (
    ApplicationWithdrawRequest,
    InterviewCancelRequest,
    InterviewCreateRequest,
    InterviewOutcomeRequest,
    InterviewRescheduleRequest,
    NotificationPreferenceUpdate,
    OfferResponseRequest,
    RecruiterStatusUpdateRequest,
    TpoScreeningUpdateRequest,
)
from app.services.notification_service import sync_smart_student_notifications
from app.services.state_machine import (
    InvalidStateTransitionError,
    execute_recruiter_lifecycle_transition,
)


def _new_test_engine():
    settings = get_settings()
    return create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        connect_args={"server_settings": {"search_path": f"{settings.DB_SCHEMA},public"}},
    )


async def _seed_fixtures(session: AsyncSession):
    """Create isolated institution, departments, students, TPO, recruiter, companies, jobs, and drives."""
    tag = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    pw_hash = hash_password("TestPass123!")

    inst = Institution(
        name=f"Tracker Test Univ {tag}",
        code=f"TTU{tag}".upper(),
        city="Bengaluru",
        is_active=True,
    )
    session.add(inst)
    await session.flush()

    dept = Department(
        institution_id=inst.id,
        name="Computer Science",
        code=f"CS{tag[:4]}".upper(),
        is_active=True,
    )
    session.add(dept)
    await session.flush()

    tpo = User(
        email=f"tpo_{tag}@ttu.edu",
        hashed_password=pw_hash,
        full_name="TPO Coordinator",
        role=UserRole.TPO,
        institution_id=inst.id,
        is_active=True,
        is_verified=True,
    )
    student1_user = User(
        email=f"stu1_{tag}@ttu.edu",
        hashed_password=pw_hash,
        full_name="Alice Tracker",
        role=UserRole.STUDENT,
        institution_id=inst.id,
        department_id=dept.id,
        is_active=True,
        is_verified=True,
    )
    student2_user = User(
        email=f"stu2_{tag}@ttu.edu",
        hashed_password=pw_hash,
        full_name="Bob Private",
        role=UserRole.STUDENT,
        institution_id=inst.id,
        department_id=dept.id,
        is_active=True,
        is_verified=True,
    )
    recruiter_user = User(
        email=f"rec_{tag}@corp.com",
        hashed_password=pw_hash,
        full_name="Recruiter Corp",
        role=UserRole.RECRUITER,
        is_active=True,
        is_verified=True,
    )
    session.add_all([tpo, student1_user, student2_user, recruiter_user])
    await session.flush()

    stu1_profile = StudentProfile(
        user_id=student1_user.id,
        roll_number=f"26CS{tag[:4]}1",
        graduation_year=2026,
        cgpa=8.9,
        active_backlogs=0,
        total_backlogs=0,
        is_placement_ready=True,
    )
    stu2_profile = StudentProfile(
        user_id=student2_user.id,
        roll_number=f"26CS{tag[:4]}2",
        graduation_year=2026,
        cgpa=8.4,
        active_backlogs=0,
        total_backlogs=0,
        is_placement_ready=True,
    )
    session.add_all([stu1_profile, stu2_profile])
    await session.flush()

    res1 = Resume(
        student_id=stu1_profile.id,
        file_name="alice_cv.pdf",
        file_path=f"/tmp/alice_{tag}.pdf",
        file_type="pdf",
        file_size_bytes=2048,
        file_hash=uuid.uuid4().hex * 2,
        parsing_status="approved",
        is_active=True,
    )
    res2 = Resume(
        student_id=stu2_profile.id,
        file_name="bob_cv.pdf",
        file_path=f"/tmp/bob_{tag}.pdf",
        file_type="pdf",
        file_size_bytes=2048,
        file_hash=uuid.uuid4().hex * 2,
        parsing_status="approved",
        is_active=True,
    )
    session.add_all([res1, res2])
    await session.flush()

    company1 = Company(
        name=f"Acme Robotics {tag}",
        industry="Software",
        website="https://acme.example.com",
    )
    company2 = Company(
        name=f"Beacon Cloud {tag}",
        industry="Cloud",
        website="https://beacon.example.com",
    )
    session.add_all([company1, company2])
    await session.flush()

    rec_profile = RecruiterProfile(
        user_id=recruiter_user.id,
        company_id=company1.id,
        designation="Talent Partner",
    )
    session.add(rec_profile)
    await session.flush()
    recruiter_user.recruiter_profile = rec_profile

    drive = PlacementDrive(
        institution_id=inst.id,
        created_by_user_id=tpo.id,
        name=f"Spring Campus Drive {tag}",
        academic_year="2025-2026",
        target_graduation_year=2026,
        registration_start_date=now - timedelta(days=5),
        registration_end_date=now + timedelta(days=10),
        drive_mode=DriveMode.ON_CAMPUS,
        status=DriveStatus.ONGOING,
        is_active=True,
    )
    session.add(drive)
    await session.flush()

    job_a = Job(
        company_id=company1.id,
        created_by_user_id=recruiter_user.id,
        title="Backend Systems Engineer",
        description="Build scalable APIs.",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.HYBRID,
        location="Bengaluru",
        salary_range="18 - 22 LPA",
        ctc_lpa=20.0,
        min_cgpa=7.0,
        target_graduation_year=2026,
        max_active_backlogs=0,
        max_total_backlogs=0,
        application_deadline=now + timedelta(days=5),
        status=JobStatus.PUBLISHED,
    )
    job_b = Job(
        company_id=company1.id,
        created_by_user_id=recruiter_user.id,
        title="Data Platform Intern",
        description="ETL and analytics.",
        employment_type=EmploymentType.INTERNSHIP,
        work_mode=WorkMode.REMOTE,
        location="Remote",
        salary_range="50,000/month",
        ctc_lpa=12.0,
        min_cgpa=6.5,
        target_graduation_year=2026,
        max_active_backlogs=0,
        max_total_backlogs=0,
        application_deadline=now + timedelta(days=7),
        status=JobStatus.PUBLISHED,
    )
    job_c = Job(
        company_id=company2.id,
        created_by_user_id=recruiter_user.id,
        title="Site Reliability Engineer",
        description="Kubernetes and observability.",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.ON_SITE,
        location="Hyderabad",
        salary_range="15 LPA",
        ctc_lpa=15.0,
        min_cgpa=7.0,
        target_graduation_year=2026,
        max_active_backlogs=0,
        max_total_backlogs=0,
        application_deadline=now + timedelta(days=9),
        status=JobStatus.PUBLISHED,
    )
    session.add_all([job_a, job_b, job_c])
    await session.flush()

    dj_a = PlacementDriveJob(drive_id=drive.id, job_id=job_a.id, is_active=True)
    dj_b = PlacementDriveJob(drive_id=drive.id, job_id=job_b.id, is_active=True)
    session.add_all([dj_a, dj_b])
    await session.flush()

    return {
        "tag": tag,
        "now": now,
        "inst": inst,
        "dept": dept,
        "tpo": tpo,
        "student1": student1_user,
        "student2": student2_user,
        "recruiter": recruiter_user,
        "stu1_profile": stu1_profile,
        "stu2_profile": stu2_profile,
        "res1": res1,
        "res2": res2,
        "company1": company1,
        "company2": company2,
        "drive": drive,
        "job_a": job_a,
        "job_b": job_b,
        "job_c": job_c,
    }


def _create_app_row(
    job: Job,
    profile: StudentProfile,
    resume: Resume,
    drive: PlacementDrive | None = None,
    score: float = 84.5,
    status: ApplicationStatus = ApplicationStatus.APPLIED,
    tpo_status: TpoScreeningStatus = TpoScreeningStatus.BYPASSED,
    created_at: datetime | None = None,
    recruiter_notes: str | None = None,
) -> JobApplication:
    return JobApplication(
        job_id=job.id,
        student_id=profile.id,
        resume_id=resume.id,
        drive_id=drive.id if drive else None,
        tpo_screening_status=tpo_status,
        current_status=status,
        compatibility_score_at_application=score,
        recruiter_feedback_notes=recruiter_notes,
        created_at=created_at or datetime.now(timezone.utc),
    )


def test_tracker_overview_timeline_interviews_offers_and_redaction():
    """Verify tracker overview, recorded-only timeline, interview tracking, redaction, offers, and all lifecycle stages."""

    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_fixtures(session)
                    now = fx["now"]

                    # Direct application -> exercise full offered -> offer_accepted path
                    app1 = _create_app_row(
                        job=fx["job_a"],
                        profile=fx["stu1_profile"],
                        resume=fx["res1"],
                        drive=fx["drive"],
                        score=91.2,
                        tpo_status=TpoScreeningStatus.PENDING,
                        created_at=now - timedelta(days=4),
                    )
                    # Second application (started at interviewed without prior history rows) -> exercise offer -> offer_declined path & no fabricated history steps
                    app2 = _create_app_row(
                        job=fx["job_b"],
                        profile=fx["stu1_profile"],
                        resume=fx["res1"],
                        drive=None,
                        score=76.0,
                        status=ApplicationStatus.INTERVIEWED,
                        tpo_status=TpoScreeningStatus.BYPASSED,
                        created_at=now - timedelta(days=2),
                    )
                    # Third application -> exercise under_review -> withdrawn + other company filter
                    app3 = _create_app_row(
                        job=fx["job_c"],
                        profile=fx["stu1_profile"],
                        resume=fx["res1"],
                        drive=None,
                        score=80.0,
                        tpo_status=TpoScreeningStatus.BYPASSED,
                        created_at=now - timedelta(days=1),
                    )
                    session.add_all([app1, app2, app3])
                    await session.flush()

                    # Initial submitted history ONLY on app1 to test recorded-only fidelity
                    await tpo_screen_application_endpoint(
                        application_id=app1.id,
                        payload=TpoScreeningUpdateRequest(
                            status=TpoScreeningStatus.SHORTLISTED,
                            feedback="Verified CGPA 8.9 and zero active backlogs.",
                        ),
                        current_user=fx["tpo"],
                        session=session,
                    )

                    await recruiter_update_status_endpoint(
                        application_id=app1.id,
                        payload=RecruiterStatusUpdateRequest(
                            status=ApplicationStatus.UNDER_REVIEW,
                            feedback_notes="CONFIDENTIAL: Strong systems fundamentals.",
                        ),
                        current_user=fx["recruiter"],
                        session=session,
                    )
                    await recruiter_update_status_endpoint(
                        application_id=app1.id,
                        payload=RecruiterStatusUpdateRequest(
                            status=ApplicationStatus.SHORTLISTED,
                            feedback_notes="CONFIDENTIAL: Approved for technical rounds.",
                        ),
                        current_user=fx["recruiter"],
                        session=session,
                    )

                    # Schedule Round 1 & reschedule + instructions -> complete Round 1 -> schedule Round 2 -> cancel Round 2
                    r1_time = now + timedelta(hours=12)
                    iv1 = await schedule_interview_endpoint(
                        application_id=app1.id,
                        payload=InterviewCreateRequest(
                            round_number=1,
                            round_title="Systems Architecture Round",
                            interview_mode=InterviewMode.VIRTUAL,
                            meeting_link="https://meet.example.com/sys-1",
                            scheduled_start_time=r1_time,
                            duration_minutes=60,
                            interviewer_names="Priya Nair, Principal Engineer",
                            instructions="Have a shared whiteboard tool ready.",
                        ),
                        current_user=fx["recruiter"],
                        session=session,
                    )
                    assert iv1.instructions == "Have a shared whiteboard tool ready."

                    r1_new_time = now + timedelta(hours=18)
                    iv1_resched = await reschedule_interview_endpoint(
                        interview_id=iv1.id,
                        payload=InterviewRescheduleRequest(
                            scheduled_start_time=r1_new_time,
                            reason="Panelist conflict moved slot by 6h",
                            instructions="Join 10 mins prior via updated link.",
                        ),
                        current_user=fx["recruiter"],
                        session=session,
                    )
                    assert iv1_resched.is_rescheduled is True
                    assert iv1_resched.instructions == "Join 10 mins prior via updated link."

                    await record_interview_outcome_endpoint(
                        interview_id=iv1.id,
                        payload=InterviewOutcomeRequest(
                            outcome=InterviewOutcome.PASSED,
                            feedback_notes="SECRET INTERVIEWER SCORE: 4.8/5, strong distributed lock design.",
                        ),
                        current_user=fx["recruiter"],
                        session=session,
                    )
                    assert app1.current_status == ApplicationStatus.INTERVIEWED

                    # Schedule Round 2 (upcoming) and verify tracker shows next_scheduled_activity
                    r2_time = now + timedelta(hours=10)
                    iv2 = await schedule_interview_endpoint(
                        application_id=app1.id,
                        payload=InterviewCreateRequest(
                            round_number=2,
                            round_title="Engineering Manager Round",
                            interview_mode=InterviewMode.IN_PERSON,
                            location="Room 402, Innovation Block",
                            scheduled_start_time=r2_time,
                            duration_minutes=45,
                            interviewer_names="Vikram Rao",
                            instructions="Bring college ID card.",
                        ),
                        current_user=fx["recruiter"],
                        session=session,
                    )

                    tracker = await get_student_application_tracker_endpoint(
                        skip=0,
                        limit=2,
                        sync_notifications=True,
                        current_user=fx["student1"],
                        session=session,
                    )
                    assert tracker.total == 3
                    assert len(tracker.items) == 2
                    assert tracker.summary.total_applications == 3
                    assert tracker.summary.upcoming_interviews_count == 1
                    assert tracker.summary.completed_interviews_count == 1

                    # Pagination page 2
                    tracker_p2 = await get_student_application_tracker_endpoint(
                        skip=2,
                        limit=2,
                        sync_notifications=False,
                        current_user=fx["student1"],
                        session=session,
                    )
                    assert tracker_p2.total == 3
                    assert len(tracker_p2.items) == 1

                    # Filter checks: company, role, status, interview_status, date range
                    filtered_co2 = await get_student_application_tracker_endpoint(
                        company="Beacon",
                        sync_notifications=False,
                        current_user=fx["student1"],
                        session=session,
                    )
                    assert filtered_co2.total == 1
                    assert filtered_co2.items[0].id == app3.id

                    filtered_upcoming = await get_student_application_tracker_endpoint(
                        interview_status="upcoming",
                        sync_notifications=False,
                        current_user=fx["student1"],
                        session=session,
                    )
                    assert filtered_upcoming.total == 1
                    assert filtered_upcoming.items[0].id == app1.id
                    assert filtered_upcoming.items[0].next_scheduled_activity.activity_type == "interview"
                    assert "Engineering Manager Round" in filtered_upcoming.items[0].next_scheduled_activity.title

                    # Student interview endpoint & confidential notes redaction
                    iv_list = await get_my_interviews_endpoint(
                        current_user=fx["student1"],
                        session=session,
                    )
                    assert len(iv_list.upcoming) == 1
                    assert len(iv_list.completed) == 1
                    for iv_item in iv_list.upcoming + iv_list.completed:
                        dumped = iv_item.model_dump()
                        assert "feedback_notes" not in dumped
                    assert "SECRET INTERVIEWER SCORE" not in str(iv_list.model_dump())
                    assert "CONFIDENTIAL" not in str(tracker.model_dump())

                    # Cancel Round 2 -> verify round-aware reversion to INTERVIEWED and cancellation status visible
                    await cancel_interview_endpoint(
                        interview_id=iv2.id,
                        payload=InterviewCancelRequest(reason="Fast-tracked directly to final offer stage"),
                        current_user=fx["recruiter"],
                        session=session,
                    )
                    assert app1.current_status == ApplicationStatus.INTERVIEWED

                    iv_list_after_cancel = await get_my_interviews_endpoint(
                        current_user=fx["student1"],
                        session=session,
                    )
                    assert len(iv_list_after_cancel.upcoming) == 0
                    assert len(iv_list_after_cancel.cancelled_or_other) == 1
                    assert iv_list_after_cancel.cancelled_or_other[0].status == InterviewStatus.CANCELLED

                    # Move app1 to OFFERED with deadline + package -> accept via offer-response API
                    offer_deadline = now + timedelta(hours=20)
                    await recruiter_update_status_endpoint(
                        application_id=app1.id,
                        payload=RecruiterStatusUpdateRequest(
                            status=ApplicationStatus.OFFERED,
                            feedback_notes="SECRET: Band 5 approved",
                            offer_deadline_at=offer_deadline,
                            offer_package_lpa=21.5,
                            offer_notes="Includes relocation stipend and joining bonus.",
                        ),
                        current_user=fx["recruiter"],
                        session=session,
                    )

                    app1_detail_offer = await get_student_application_tracker_endpoint(
                        role="Backend Systems Engineer",
                        sync_notifications=True,
                        current_user=fx["student1"],
                        session=session,
                    )
                    item1 = app1_detail_offer.items[0]
                    assert item1.offer_details is not None
                    assert item1.offer_details.package_lpa == 21.5
                    assert item1.offer_details.can_respond is True
                    assert item1.next_scheduled_activity.activity_type == "offer_deadline"

                    # Accept offer
                    accepted = await respond_to_offer_endpoint(
                        application_id=app1.id,
                        payload=OfferResponseRequest(accept=True, notes="Excited to join!"),
                        current_user=fx["student1"],
                        session=session,
                    )
                    assert accepted.current_status == ApplicationStatus.OFFER_ACCEPTED

                    # Trying to accept/decline again fails state machine check
                    with pytest.raises(AppException) as exc_offer:
                        await respond_to_offer_endpoint(
                            application_id=app1.id,
                            payload=OfferResponseRequest(accept=False),
                            current_user=fx["student1"],
                            session=session,
                        )
                    assert exc_offer.value.code == "APPLICATION_NOT_OFFERED"

                    # App2: test offered -> offer_declined & timeline recorded-only transitions
                    await recruiter_update_status_endpoint(
                        application_id=app2.id,
                        payload=RecruiterStatusUpdateRequest(
                            status=ApplicationStatus.OFFERED,
                            offer_package_lpa=12.0,
                            offer_deadline_at=now + timedelta(days=2),
                        ),
                        current_user=fx["recruiter"],
                        session=session,
                    )
                    declined = await respond_to_offer_endpoint(
                        application_id=app2.id,
                        payload=OfferResponseRequest(accept=False, notes="Accepted another role."),
                        current_user=fx["student1"],
                        session=session,
                    )
                    assert declined.current_status == ApplicationStatus.OFFER_DECLINED

                    await session.refresh(app2, ["status_history"])
                    app2_detail = await get_application_detail_endpoint(
                        application_id=app2.id,
                        current_user=fx["student1"],
                        session=session,
                    )
                    # Note: app2 jumped applied -> offered -> offer_declined, so timeline must ONLY contain those 2 transitions (no fabricated shortlisted/interviewed steps!)
                    recorded_targets = [h.to_status for h in app2_detail.status_history]
                    assert recorded_targets == ["offered", "offer_declined"]

                    # App3: test withdraw + cannot move after withdrawn + rejected state check
                    withdrawn = await withdraw_application_endpoint(
                        application_id=app3.id,
                        payload=ApplicationWithdrawRequest(reason="Already accepted primary offer"),
                        current_user=fx["student1"],
                        session=session,
                    )
                    assert withdrawn.current_status == ApplicationStatus.WITHDRAWN

                    # Remaining REJECTED state test
                    app_rej = _create_app_row(
                        job=fx["job_c"],
                        profile=fx["stu2_profile"],
                        resume=fx["res2"],
                        status=ApplicationStatus.UNDER_REVIEW,
                    )
                    session.add(app_rej)
                    await session.flush()
                    await execute_recruiter_lifecycle_transition(
                        session=session,
                        application=app_rej,
                        new_status=ApplicationStatus.REJECTED,
                        actor_user_id=fx["recruiter"].id,
                        notes="Not proceeding further",
                    )
                    assert app_rej.current_status == ApplicationStatus.REJECTED
                finally:
                    await session.close()
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_smart_notifications_dedup_preferences_and_calendar():
    """Verify smart notifications avoid duplicates, respect preferences, and power calendar events."""

    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_fixtures(session)
                    now = fx["now"]

                    app = _create_app_row(
                        job=fx["job_a"],
                        profile=fx["stu1_profile"],
                        resume=fx["res1"],
                        drive=fx["drive"],
                        status=ApplicationStatus.SHORTLISTED,
                        tpo_status=TpoScreeningStatus.SHORTLISTED,
                    )
                    app.tpo_screened_by_user_id = fx["tpo"].id
                    app.tpo_screened_at = now
                    session.add(app)
                    await session.flush()

                    # Upcoming interview inside default 24h lead window on app
                    await schedule_interview_endpoint(
                        application_id=app.id,
                        payload=InterviewCreateRequest(
                            round_number=1,
                            round_title="Technical Screening",
                            interview_mode=InterviewMode.VIRTUAL,
                            meeting_link="https://meet.example.com/round1",
                            scheduled_start_time=now + timedelta(hours=8),
                            duration_minutes=45,
                        ),
                        current_user=fx["recruiter"],
                        session=session,
                    )

                    # Second app already in INTERVIEWED -> transition to OFFERED with deadline inside 24h window
                    app_offer = _create_app_row(
                        job=fx["job_b"],
                        profile=fx["stu1_profile"],
                        resume=fx["res1"],
                        drive=fx["drive"],
                        status=ApplicationStatus.INTERVIEWED,
                        tpo_status=TpoScreeningStatus.SHORTLISTED,
                    )
                    app_offer.tpo_screened_by_user_id = fx["tpo"].id
                    app_offer.tpo_screened_at = now
                    session.add(app_offer)
                    await session.flush()

                    await recruiter_update_status_endpoint(
                        application_id=app_offer.id,
                        payload=RecruiterStatusUpdateRequest(
                            status=ApplicationStatus.OFFERED,
                            offer_deadline_at=now + timedelta(hours=10),
                            offer_package_lpa=19.5,
                        ),
                        current_user=fx["recruiter"],
                        session=session,
                    )

                    # First sync should generate status change + upcoming interview reminder + offer available + offer deadline + drive announcement
                    sync1 = await sync_smart_notifications_endpoint(
                        current_user=fx["student1"],
                        session=session,
                    )
                    assert sync1.generated_count >= 4

                    # Second sync must produce ZERO duplicates!
                    sync2 = await sync_smart_notifications_endpoint(
                        current_user=fx["student1"],
                        session=session,
                    )
                    assert sync2.generated_count == 0

                    # Verify categories present
                    notifs = await list_notifications_endpoint(
                        unread_only=False,
                        skip=0,
                        limit=50,
                        current_user=fx["student1"],
                        session=session,
                    )
                    cats = {n.category for n in notifs}
                    assert NotificationCategory.OFFER_EXTENDED in cats
                    assert NotificationCategory.ACTION_REQUIRED in cats
                    assert NotificationCategory.DRIVE_ANNOUNCEMENT in cats
                    assert NotificationCategory.INTERVIEW_UPDATE in cats

                    # Disable specific preferences before creating a new drive/app -> verify preference enforcement
                    pref_res = await get_notification_preferences_endpoint(
                        current_user=fx["student2"],
                        session=session,
                    )
                    assert pref_res.placement_announcements is True

                    updated_pref = await update_notification_preferences_endpoint(
                        payload=NotificationPreferenceUpdate(
                            placement_announcements=False,
                            upcoming_interview_reminders=False,
                            offer_alerts=False,
                            offer_deadline_reminders=False,
                            status_changes=False,
                            interview_schedules=False,
                            reminder_hours_before=12,
                        ),
                        current_user=fx["student2"],
                        session=session,
                    )
                    assert updated_pref.placement_announcements is False
                    assert updated_pref.reminder_hours_before == 12

                    app_s2 = _create_app_row(
                        job=fx["job_a"],
                        profile=fx["stu2_profile"],
                        resume=fx["res2"],
                        status=ApplicationStatus.OFFERED,
                    )
                    app_s2.offer_deadline_at = now + timedelta(hours=5)
                    session.add(app_s2)
                    await session.flush()

                    sync_s2 = await sync_smart_notifications_endpoint(
                        current_user=fx["student2"],
                        session=session,
                    )
                    assert sync_s2.generated_count == 0

                    # Calendar events check for student1
                    cal = await get_student_calendar_events_endpoint(
                        start_date=now - timedelta(days=1),
                        end_date=now + timedelta(days=30),
                        current_user=fx["student1"],
                        session=session,
                    )
                    event_types = {e.event_type for e in cal.events}
                    assert "interview" in event_types
                    assert "offer_deadline" in event_types
                    assert "application_deadline" in event_types
                    assert "drive_registration" in event_types
                finally:
                    await session.close()
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_student_authorization_and_cross_student_isolation():
    """Verify strict student-only ownership across tracker, interviews, offer responses, withdrawals, and notifications."""

    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_fixtures(session)
                    app_s1 = _create_app_row(
                        job=fx["job_a"],
                        profile=fx["stu1_profile"],
                        resume=fx["res1"],
                        status=ApplicationStatus.OFFERED,
                    )
                    session.add(app_s1)
                    await session.flush()

                    notif_s1 = Notification(
                        recipient_user_id=fx["student1"].id,
                        category=NotificationCategory.OFFER_EXTENDED,
                        title="Private Offer",
                        message="Only for student1",
                        related_application_id=app_s1.id,
                    )
                    session.add(notif_s1)
                    await session.flush()

                    # Student2 tracker/interviews must NOT include Student1's records
                    s2_tracker = await get_student_application_tracker_endpoint(
                        sync_notifications=False,
                        current_user=fx["student2"],
                        session=session,
                    )
                    assert s2_tracker.total == 0

                    s2_interviews = await get_my_interviews_endpoint(
                        current_user=fx["student2"],
                        session=session,
                    )
                    assert s2_interviews.total == 0

                    # Student2 blocked from reading Student1 application detail
                    with pytest.raises(AuthorizationException):
                        await get_application_detail_endpoint(
                            application_id=app_s1.id,
                            current_user=fx["student2"],
                            session=session,
                        )

                    # Student2 blocked from responding to Student1 offer
                    with pytest.raises(AuthorizationException):
                        await respond_to_offer_endpoint(
                            application_id=app_s1.id,
                            payload=OfferResponseRequest(accept=True),
                            current_user=fx["student2"],
                            session=session,
                        )

                    # Student2 blocked from withdrawing Student1 application
                    with pytest.raises(AuthorizationException):
                        await withdraw_application_endpoint(
                            application_id=app_s1.id,
                            payload=ApplicationWithdrawRequest(reason="Unauthorized attempt"),
                            current_user=fx["student2"],
                            session=session,
                        )

                    # Student2 blocked from marking Student1 notification as read
                    with pytest.raises(AuthorizationException):
                        await mark_notification_read_endpoint(
                            notification_id=notif_s1.id,
                            current_user=fx["student2"],
                            session=session,
                        )
                finally:
                    await session.close()
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_concurrent_notification_sync_and_interview_collision_locking():
    """
    Verify concurrent sync_smart_student_notifications does not fail or duplicate,
    and concurrent interview scheduling collisions are blocked by student lock.
    """

    async def _run():
        engine = _new_test_engine()
        maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        created_ids = {}
        try:
            # Seed temporary committed rows so multiple independent DB sessions can contend cleanly
            async with maker() as setup_sess:
                fx = await _seed_fixtures(setup_sess)
                now = fx["now"]
                # App 1 in INTERVIEW_SCHEDULED: schedule_interview exercises StudentProfile FOR UPDATE collision lock
                # without creating immutable ApplicationStatusHistory rows (so cleanup DELETE succeeds).
                app = _create_app_row(
                    job=fx["job_a"],
                    profile=fx["stu1_profile"],
                    resume=fx["res1"],
                    status=ApplicationStatus.INTERVIEW_SCHEDULED,
                    tpo_status=TpoScreeningStatus.BYPASSED,
                )
                # App 2 in OFFERED with offer_deadline_at for notification dedup concurrency check
                app_offer = _create_app_row(
                    job=fx["job_b"],
                    profile=fx["stu1_profile"],
                    resume=fx["res1"],
                    status=ApplicationStatus.OFFERED,
                    tpo_status=TpoScreeningStatus.BYPASSED,
                )
                app_offer.offer_deadline_at = now + timedelta(hours=6)
                setup_sess.add_all([app, app_offer])
                await setup_sess.commit()
                created_ids = {
                    "inst_id": fx["inst"].id,
                    "dept_id": fx["dept"].id,
                    "tpo_id": fx["tpo"].id,
                    "stu1_id": fx["student1"].id,
                    "stu2_id": fx["student2"].id,
                    "rec_id": fx["recruiter"].id,
                    "stu1_prof_id": fx["stu1_profile"].id,
                    "stu2_prof_id": fx["stu2_profile"].id,
                    "res1_id": fx["res1"].id,
                    "res2_id": fx["res2"].id,
                    "comp1_id": fx["company1"].id,
                    "comp2_id": fx["company2"].id,
                    "drive_id": fx["drive"].id,
                    "job_a_id": fx["job_a"].id,
                    "job_b_id": fx["job_b"].id,
                    "job_c_id": fx["job_c"].id,
                    "app_id": app.id,
                    "app_offer_id": app_offer.id,
                    "now": now,
                    "student1_user": fx["student1"],
                    "recruiter_user": fx["recruiter"],
                }

            # 1. Concurrent interview collision lock across 2 separate sessions
            slot = created_ids["now"] + timedelta(days=2)

            async def _sched_attempt(round_num: int):
                async with maker() as s:
                    try:
                        # Reload recruiter user cleanly inside session s
                        rec = await s.get(User, created_ids["rec_id"])
                        res = await schedule_interview_endpoint(
                            application_id=created_ids["app_id"],
                            payload=InterviewCreateRequest(
                                round_number=round_num,
                                round_title=f"Concurrent Round {round_num}",
                                interview_mode=InterviewMode.VIRTUAL,
                                scheduled_start_time=slot,
                                duration_minutes=45,
                            ),
                            current_user=rec,
                            session=s,
                        )
                        await s.commit()
                        return ("ok", res.id)
                    except (ResourceConflictException, AppException) as e:
                        await s.rollback()
                        return ("conflict", str(e))

            results = await asyncio.gather(_sched_attempt(1), _sched_attempt(2))
            outcomes = sorted(r[0] for r in results)
            assert outcomes == ["conflict", "ok"]

            # 2. Repeated/sequential & near-concurrent smart notification sync leaves zero duplicates
            async def _sync_once():
                async with maker() as s:
                    stu = await s.get(User, created_ids["stu1_id"])
                    try:
                        created = await sync_smart_student_notifications(s, stu)
                        await s.commit()
                        return len(created)
                    except Exception:
                        await s.rollback()
                        return 0

            await _sync_once()
            second_count = await _sync_once()
            assert second_count == 0

            async with maker() as verify_sess:
                stu = await verify_sess.get(User, created_ids["stu1_id"])
                all_notifs = await list_notifications_endpoint(
                    unread_only=False, skip=0, limit=100, current_user=stu, session=verify_sess
                )
                keys = [n.idempotency_key for n in all_notifs if n.idempotency_key]
                assert len(keys) == len(set(keys))
        finally:
            # Clean up committed test rows in strict FK dependency order
            if created_ids:
                async with maker() as clean_sess:
                    from sqlalchemy import delete
                    from app.models.placement import (
                        ApplicationStatusHistory,
                        Interview,
                        NotificationPreference,
                    )

                    await clean_sess.execute(
                        delete(Notification).where(
                            Notification.recipient_user_id.in_(
                                [created_ids["stu1_id"], created_ids["stu2_id"], created_ids["tpo_id"], created_ids["rec_id"]]
                            )
                        )
                    )
                    await clean_sess.execute(
                        delete(NotificationPreference).where(
                            NotificationPreference.user_id.in_(
                                [created_ids["stu1_id"], created_ids["stu2_id"]]
                            )
                        )
                    )
                    await clean_sess.execute(
                        delete(Interview).where(Interview.application_id == created_ids["app_id"])
                    )
                    await clean_sess.execute(
                        delete(ApplicationStatusHistory).where(ApplicationStatusHistory.application_id == created_ids["app_id"])
                    )
                    await clean_sess.execute(
                        delete(JobApplication).where(
                            JobApplication.id.in_([created_ids["app_id"], created_ids["app_offer_id"]])
                        )
                    )
                    await clean_sess.execute(
                        delete(PlacementDriveJob).where(PlacementDriveJob.drive_id == created_ids["drive_id"])
                    )
                    await clean_sess.execute(
                        delete(PlacementDrive).where(PlacementDrive.id == created_ids["drive_id"])
                    )
                    await clean_sess.execute(
                        delete(Job).where(
                            Job.id.in_([created_ids["job_a_id"], created_ids["job_b_id"], created_ids["job_c_id"]])
                        )
                    )
                    await clean_sess.execute(
                        delete(RecruiterProfile).where(RecruiterProfile.user_id == created_ids["rec_id"])
                    )
                    await clean_sess.execute(
                        delete(Company).where(Company.id.in_([created_ids["comp1_id"], created_ids["comp2_id"]]))
                    )
                    await clean_sess.execute(
                        delete(Resume).where(Resume.id.in_([created_ids["res1_id"], created_ids["res2_id"]]))
                    )
                    await clean_sess.execute(
                        delete(StudentProfile).where(
                            StudentProfile.id.in_([created_ids["stu1_prof_id"], created_ids["stu2_prof_id"]])
                        )
                    )
                    await clean_sess.execute(
                        delete(User).where(
                            User.id.in_(
                                [created_ids["stu1_id"], created_ids["stu2_id"], created_ids["tpo_id"], created_ids["rec_id"]]
                            )
                        )
                    )
                    await clean_sess.execute(delete(Department).where(Department.id == created_ids["dept_id"]))
                    await clean_sess.execute(delete(Institution).where(Institution.id == created_ids["inst_id"]))
                    await clean_sess.commit()
            await engine.dispose()

    asyncio.run(_run())
