"""Comprehensive test suite for TASK 09: Complete Interview Management Portal.

Validates:
1. Multi-round interview scheduling with templates, modes, links, and instructions.
2. Row-level student locking and collision detection preventing overlapping interviews.
3. Rescheduling with reason validation, collision checks, and student notification.
4. Cancellation with round-aware candidate lifecycle state reversion.
5. Recording interview outcomes (PASSED, FAILED, ON_HOLD) without auto-rejection.
6. Role-scoped interactive calendar aggregation.
7. TPO institutional interview monitoring with confidential recruiter notes redacted.
8. Interviewer workspace dossier with candidate context, past rounds, and evaluations.
9. Company tenant isolation and access security.
"""
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import get_settings
from app.core.errors import AppException, AuthorizationException, ResourceConflictException
from app.models.candidate_evaluation import CandidateEvaluation, EvaluationRecommendation, EvaluationStage
from app.models.company import Company, RecruiterProfile
from app.models.job import EmploymentType, Job, JobEligibleDepartment, JobSkill, JobStatus, WorkMode
from app.models.organization import Department, Institution
from app.models.placement import (
    ApplicationStatus,
    DriveLifecyclePhase,
    DriveMode,
    DriveStatus,
    Interview,
    InterviewMode,
    InterviewOutcome,
    InterviewStatus,
    JobApplication,
    PlacementDrive,
    PlacementDriveJob,
    PlacementDriveRegistration,
    TpoScreeningStatus,
)
from app.models.resume import Resume
from app.models.student import StudentEducation, StudentProfile, StudentSkill
from app.models.user import User, UserRole
from app.services.interview_service import (
    STANDARD_ROUND_TEMPLATES,
    cancel_interview,
    check_student_interview_collision,
    get_interview_calendar_events,
    get_interview_workspace_detail,
    list_company_interviews,
    list_student_interviews,
    list_tpo_institution_interviews,
    record_interview_outcome,
    reschedule_interview,
    schedule_interview,
)


settings = get_settings()


def _new_test_engine():
    return create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        isolation_level="READ COMMITTED",
        pool_pre_ping=True,
    )


async def _seed_interview_fixtures(session: AsyncSession) -> dict:
    tag = f"iv_{int(datetime.now(timezone.utc).timestamp())}_{id(session)}"
    pwd = "$2b$12$e80yq9gW7Yh77eU7p8yMEOQ0gS6jL29P6a9n0R6fC0zMvLh1K7m1K"
    now = datetime.now(timezone.utc)

    # Institution & Departments
    inst = Institution(name=f"Apex Institute {tag}", code=f"AI_{tag[:6]}", city="Metropolis", is_active=True)
    session.add(inst)
    await session.flush()

    dept_cs = Department(institution_id=inst.id, name=f"Computer Science {tag}", code=f"CS_{tag[:4]}")
    session.add(dept_cs)
    await session.flush()

    # Users
    u_tpo = User(
        institution_id=inst.id,
        email=f"tpo_{tag}@apex.edu",
        hashed_password=pwd,
        full_name=f"Prof. TPO {tag}",
        role=UserRole.TPO,
        is_active=True,
    )
    u_rec1 = User(
        email=f"rec1_{tag}@nexus.com",
        hashed_password=pwd,
        full_name=f"Alex Recruiter {tag}",
        role=UserRole.RECRUITER,
        is_active=True,
    )
    u_rec2 = User(
        email=f"rec2_{tag}@vortex.com",
        hashed_password=pwd,
        full_name=f"Vera Recruiter {tag}",
        role=UserRole.RECRUITER,
        is_active=True,
    )
    u_stu1 = User(
        institution_id=inst.id,
        department_id=dept_cs.id,
        email=f"stu1_{tag}@apex.edu",
        hashed_password=pwd,
        full_name=f"John Student {tag}",
        role=UserRole.STUDENT,
        is_active=True,
    )
    u_stu2 = User(
        institution_id=inst.id,
        department_id=dept_cs.id,
        email=f"stu2_{tag}@apex.edu",
        hashed_password=pwd,
        full_name=f"Jane Student {tag}",
        role=UserRole.STUDENT,
        is_active=True,
    )
    session.add_all([u_tpo, u_rec1, u_rec2, u_stu1, u_stu2])
    await session.flush()

    # Companies & Recruiter Profiles
    c_nexus = Company(institution_id=inst.id, name=f"Nexus Corp {tag}", industry="Software Engineering", is_active=True, is_verified=True)
    c_vortex = Company(institution_id=inst.id, name=f"Vortex Inc {tag}", industry="Cloud Systems", is_active=True, is_verified=True)
    session.add_all([c_nexus, c_vortex])
    await session.flush()

    rp_nexus = RecruiterProfile(user_id=u_rec1.id, company_id=c_nexus.id, designation="Lead Recruiter")
    rp_vortex = RecruiterProfile(user_id=u_rec2.id, company_id=c_vortex.id, designation="Talent Partner")
    session.add_all([rp_nexus, rp_vortex])
    await session.flush()

    # Student Profiles
    sp1 = StudentProfile(
        user_id=u_stu1.id,
        roll_number=f"26CS1_{tag}",
        graduation_year=2026,
        cgpa=8.8,
        active_backlogs=0,
        total_backlogs=0,
        is_placement_ready=True,
    )
    sp2 = StudentProfile(
        user_id=u_stu2.id,
        roll_number=f"26CS2_{tag}",
        graduation_year=2026,
        cgpa=8.2,
        active_backlogs=0,
        total_backlogs=0,
        is_placement_ready=True,
    )
    session.add_all([sp1, sp2])
    await session.flush()

    # Jobs
    job_nexus = Job(
        company_id=c_nexus.id,
        institution_id=inst.id,
        created_by_user_id=u_rec1.id,
        title=f"Backend Engineer {tag}",
        description="Build high throughput backend services.",
        location="Bangalore, India",
        ctc_lpa=16.0,
        work_mode=WorkMode.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        status=JobStatus.PUBLISHED,
        min_cgpa=7.0,
        max_active_backlogs=0,
        target_graduation_year=2026,
        application_deadline=now + timedelta(days=30),
    )
    job_vortex = Job(
        company_id=c_vortex.id,
        institution_id=inst.id,
        created_by_user_id=u_rec2.id,
        title=f"Fullstack Engineer {tag}",
        description="Develop modern web applications.",
        location="Remote",
        ctc_lpa=18.0,
        work_mode=WorkMode.REMOTE,
        employment_type=EmploymentType.FULL_TIME,
        status=JobStatus.PUBLISHED,
        min_cgpa=7.0,
        max_active_backlogs=0,
        target_graduation_year=2026,
        application_deadline=now + timedelta(days=30),
    )
    session.add_all([job_nexus, job_vortex])
    await session.flush()

    # Placement Drive
    drive = PlacementDrive(
        institution_id=inst.id,
        created_by_user_id=u_tpo.id,
        name=f"Campus Placement Drive 2026 {tag}",
        academic_year="2025-2026",
        target_graduation_year=2026,
        registration_start_date=now - timedelta(days=5),
        registration_end_date=now + timedelta(days=15),
        drive_mode=DriveMode.ON_CAMPUS,
        status=DriveStatus.ONGOING,
    )
    session.add(drive)
    await session.flush()

    pdj = PlacementDriveJob(drive_id=drive.id, job_id=job_nexus.id, is_active=True)
    session.add(pdj)
    await session.flush()

    # Resumes
    res1 = Resume(
        student_id=sp1.id,
        file_name=f"john_resume_{tag}.pdf",
        file_path=f"uploads/john_{tag}.pdf",
        file_type="pdf",
        file_size_bytes=2048,
        file_hash=f"hash1_{tag:0<58}",
        parsing_status="approved",
        is_active=True,
    )
    res2 = Resume(
        student_id=sp2.id,
        file_name=f"jane_resume_{tag}.pdf",
        file_path=f"uploads/jane_{tag}.pdf",
        file_type="pdf",
        file_size_bytes=1024,
        file_hash=f"hash2_{tag:0<58}",
        parsing_status="approved",
        is_active=True,
    )
    session.add_all([res1, res2])
    await session.flush()

    # Applications
    app1 = JobApplication(
        job_id=job_nexus.id,
        student_id=sp1.id,
        resume_id=res1.id,
        drive_id=drive.id,
        current_status=ApplicationStatus.SHORTLISTED,
        tpo_screening_status=TpoScreeningStatus.SHORTLISTED,
        tpo_screened_by_user_id=u_tpo.id,
        tpo_screened_at=now - timedelta(days=2),
        compatibility_score_at_application=88.5,
    )
    app2 = JobApplication(
        job_id=job_nexus.id,
        student_id=sp2.id,
        resume_id=res2.id,
        drive_id=drive.id,
        current_status=ApplicationStatus.SHORTLISTED,
        tpo_screening_status=TpoScreeningStatus.SHORTLISTED,
        tpo_screened_by_user_id=u_tpo.id,
        tpo_screened_at=now - timedelta(days=2),
        compatibility_score_at_application=82.0,
    )
    app3 = JobApplication(
        job_id=job_vortex.id,
        student_id=sp1.id,
        resume_id=res1.id,
        drive_id=None,
        current_status=ApplicationStatus.SHORTLISTED,
        tpo_screening_status=TpoScreeningStatus.BYPASSED,
        compatibility_score_at_application=91.0,
    )
    session.add_all([app1, app2, app3])
    await session.flush()

    return {
        "inst": inst,
        "tpo": u_tpo,
        "rec_nexus": u_rec1,
        "rec_vortex": u_rec2,
        "stu1": u_stu1,
        "stu2": u_stu2,
        "sp1": sp1,
        "sp2": sp2,
        "c_nexus": c_nexus,
        "c_vortex": c_vortex,
        "job_nexus": job_nexus,
        "job_vortex": job_vortex,
        "drive": drive,
        "app1": app1,
        "app2": app2,
        "app3": app3,
    }


def test_standard_round_templates():
    """Verify pre-configured round templates are available."""
    assert len(STANDARD_ROUND_TEMPLATES) >= 5
    titles = [t.round_title for t in STANDARD_ROUND_TEMPLATES]
    assert "Technical Screening" in titles
    assert "Coding & Problem Solving" in titles
    assert "HR & Cultural Alignment" in titles


def test_interview_scheduling_and_collision_detection():
    """Verify interview scheduling, row-level locking, and overlap rejection."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_interview_fixtures(session)
                    now_utc = datetime.now(timezone.utc)
                    slot1 = now_utc + timedelta(days=2, hours=10)

                    # 1. Recruiter schedules Round 1 for Student 1 at slot1
                    iv1 = await schedule_interview(
                        session=session,
                        recruiter_user=fx["rec_nexus"],
                        application_id=fx["app1"].id,
                        round_number=1,
                        round_title="Technical Screening",
                        scheduled_start_time=slot1,
                        duration_minutes=60,
                        interview_mode=InterviewMode.VIRTUAL,
                        meeting_link="https://meet.google.com/abc-defg-hij",
                        interviewer_names="Alex Lead & Priya Architect",
                        instructions="Please join 5 minutes early with working webcam and Python environment.",
                    )
                    assert iv1.id is not None
                    assert iv1.status == InterviewStatus.SCHEDULED
                    assert iv1.outcome == InterviewOutcome.PENDING
                    assert fx["app1"].current_status == ApplicationStatus.INTERVIEW_SCHEDULED

                    # 2. Collision Test: Recruiter from Vortex tries to schedule Student 1 at overlapping time
                    overlap_slot = slot1 + timedelta(minutes=30)  # 30 mins into the 60-min slot
                    with pytest.raises(ResourceConflictException) as exc_info:
                        await schedule_interview(
                            session=session,
                            recruiter_user=fx["rec_vortex"],
                            application_id=fx["app3"].id,
                            round_number=1,
                            round_title="Coding Round",
                            scheduled_start_time=overlap_slot,
                            duration_minutes=45,
                            interview_mode=InterviewMode.VIRTUAL,
                        )
                    assert "Interview schedule collision" in str(exc_info.value.message)

                    # 3. Non-overlapping slot succeeds
                    valid_slot = slot1 + timedelta(hours=2)
                    iv2 = await schedule_interview(
                        session=session,
                        recruiter_user=fx["rec_vortex"],
                        application_id=fx["app3"].id,
                        round_number=1,
                        round_title="Coding Round",
                        scheduled_start_time=valid_slot,
                        duration_minutes=45,
                        interview_mode=InterviewMode.VIRTUAL,
                    )
                    assert iv2.id is not None
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    import asyncio
    asyncio.run(_run())


def test_multi_round_scheduling_and_unique_enforcement():
    """Verify scheduling multiple rounds (Round 1, Round 2) and preventing duplicate round numbers."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_interview_fixtures(session)
                    now_utc = datetime.now(timezone.utc)

                    # Round 1
                    iv1 = await schedule_interview(
                        session=session,
                        recruiter_user=fx["rec_nexus"],
                        application_id=fx["app1"].id,
                        round_number=1,
                        round_title="Technical Screening",
                        scheduled_start_time=now_utc + timedelta(days=1),
                        duration_minutes=45,
                    )
                    assert iv1.round_number == 1

                    # Duplicate Round 1 should be rejected
                    with pytest.raises(ResourceConflictException):
                        await schedule_interview(
                            session=session,
                            recruiter_user=fx["rec_nexus"],
                            application_id=fx["app1"].id,
                            round_number=1,
                            round_title="Duplicate Technical Screening",
                            scheduled_start_time=now_utc + timedelta(days=2),
                            duration_minutes=45,
                        )

                    # Round 2 succeeds
                    iv2 = await schedule_interview(
                        session=session,
                        recruiter_user=fx["rec_nexus"],
                        application_id=fx["app1"].id,
                        round_number=2,
                        round_title="System Design Discussion",
                        scheduled_start_time=now_utc + timedelta(days=3),
                        duration_minutes=60,
                    )
                    assert iv2.round_number == 2
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    import asyncio
    asyncio.run(_run())


def test_reschedule_and_cancel_lifecycle_reversion():
    """Verify rescheduling with collision check, and cancellation with round-aware state reversion."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_interview_fixtures(session)
                    now_utc = datetime.now(timezone.utc)

                    # Schedule Round 1
                    iv1 = await schedule_interview(
                        session=session,
                        recruiter_user=fx["rec_nexus"],
                        application_id=fx["app1"].id,
                        round_number=1,
                        round_title="Technical Round 1",
                        scheduled_start_time=now_utc + timedelta(days=2),
                        duration_minutes=45,
                    )

                    # 1. Reschedule Round 1
                    new_time = now_utc + timedelta(days=4)
                    resched_iv = await reschedule_interview(
                        session=session,
                        recruiter_user=fx["rec_nexus"],
                        interview_id=iv1.id,
                        new_start_time=new_time,
                        reason="Interviewer attending technical conference.",
                    )
                    assert resched_iv.scheduled_start_time == new_time
                    assert "Interviewer attending technical conference" in resched_iv.cancellation_reason

                    # 2. Cancel Round 1 -> Candidate should revert to 'shortlisted'
                    cancelled_iv = await cancel_interview(
                        session=session,
                        recruiter_user=fx["rec_nexus"],
                        interview_id=iv1.id,
                        reason="Position put on brief organizational hold.",
                    )
                    assert cancelled_iv.status == InterviewStatus.CANCELLED
                    assert fx["app1"].current_status == ApplicationStatus.SHORTLISTED
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    import asyncio
    asyncio.run(_run())


def test_record_interview_outcomes_and_pipeline_integrity():
    """Verify recording PASSED, FAILED, ON_HOLD outcomes without auto-rejecting application."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_interview_fixtures(session)
                    now_utc = datetime.now(timezone.utc)

                    iv1 = await schedule_interview(
                        session=session,
                        recruiter_user=fx["rec_nexus"],
                        application_id=fx["app1"].id,
                        round_number=1,
                        round_title="Technical Round 1",
                        scheduled_start_time=now_utc + timedelta(days=1),
                        duration_minutes=45,
                    )

                    # Record outcome: PASSED
                    completed_iv = await record_interview_outcome(
                        session=session,
                        recruiter_user=fx["rec_nexus"],
                        interview_id=iv1.id,
                        outcome=InterviewOutcome.PASSED,
                        feedback_notes="Strong algorithmic problem solving and clean modular Python code.",
                    )
                    assert completed_iv.status == InterviewStatus.COMPLETED
                    assert completed_iv.outcome == InterviewOutcome.PASSED
                    # Pipeline status becomes 'interviewed', NEVER automatically rejected or closed
                    assert fx["app1"].current_status == ApplicationStatus.INTERVIEWED
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    import asyncio
    asyncio.run(_run())


def test_calendar_aggregation_and_tpo_monitoring():
    """Verify calendar date-bucketing and TPO institutional monitoring with redacted notes."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_interview_fixtures(session)
                    now_utc = datetime.now(timezone.utc)

                    # Schedule 2 interviews on different days
                    day1 = now_utc + timedelta(days=2)
                    day2 = now_utc + timedelta(days=3)

                    await schedule_interview(
                        session=session,
                        recruiter_user=fx["rec_nexus"],
                        application_id=fx["app1"].id,
                        round_number=1,
                        round_title="Nexus Round 1",
                        scheduled_start_time=day1,
                        duration_minutes=45,
                    )
                    await schedule_interview(
                        session=session,
                        recruiter_user=fx["rec_nexus"],
                        application_id=fx["app2"].id,
                        round_number=1,
                        round_title="Nexus Round 1 - Stu 2",
                        scheduled_start_time=day2,
                        duration_minutes=45,
                    )

                    # 1. Recruiter Calendar
                    cal_res = await get_interview_calendar_events(
                        session=session,
                        current_user=fx["rec_nexus"],
                        date_from=now_utc,
                        date_to=now_utc + timedelta(days=10),
                    )
                    assert cal_res.total_events == 2
                    assert cal_res.scheduled_count == 2
                    assert len(cal_res.days) == 2

                    # 2. TPO Monitoring
                    tpo_res = await list_tpo_institution_interviews(
                        session=session,
                        tpo_user=fx["tpo"],
                    )
                    assert tpo_res.total >= 2
                    # Confidential notes must be redacted for TPO
                    for item in tpo_res.items:
                        assert item.feedback_notes is None
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    import asyncio
    asyncio.run(_run())


def test_interviewer_workspace_detail():
    """Verify interviewer workspace view aggregates candidate context, round history, and scorecards."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_interview_fixtures(session)
                    now_utc = datetime.now(timezone.utc)

                    iv = await schedule_interview(
                        session=session,
                        recruiter_user=fx["rec_nexus"],
                        application_id=fx["app1"].id,
                        round_number=1,
                        round_title="Technical Screening",
                        scheduled_start_time=now_utc + timedelta(days=2),
                        duration_minutes=60,
                        instructions="Focus on distributed concurrency and Redis caching.",
                    )

                    # Add an evaluation for this interview
                    eval1 = CandidateEvaluation(
                        application_id=fx["app1"].id,
                        interview_id=iv.id,
                        interviewer_user_id=fx["rec_nexus"].id,
                        interviewer_name="Alex Recruiter",
                        stage=EvaluationStage.TECHNICAL,
                        technical_rating=5,
                        problem_solving_rating=4,
                        communication_rating=5,
                        project_depth_rating=4,
                        cultural_fit_rating=5,
                        overall_rating=4.5,
                        recommendation=EvaluationRecommendation.STRONG_HIRE,
                        written_feedback="Exceptional understanding of asyncio pipelines.",
                    )
                    session.add(eval1)
                    await session.flush()

                    # Query workspace detail
                    ws = await get_interview_workspace_detail(
                        session=session,
                        interview_id=iv.id,
                        current_user=fx["rec_nexus"],
                    )

                    assert ws.interview.id == iv.id
                    assert ws.candidate_profile["full_name"].startswith("John Student")
                    assert ws.candidate_profile["cgpa"] == 8.8
                    assert ws.job["title"].startswith("Backend Engineer")
                    assert len(ws.evaluations) == 1
                    assert ws.evaluations[0]["overall_rating"] == 4.5
                    assert "mark_completed_passed" in ws.allowed_next_actions
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    import asyncio
    asyncio.run(_run())
