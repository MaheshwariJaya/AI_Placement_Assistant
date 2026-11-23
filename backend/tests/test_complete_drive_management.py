"""
Comprehensive integration & security tests for TASK 06:
Complete Placement Drive Management Workspace.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import io
import uuid
import xml.etree.ElementTree as ET
import zipfile

import pymupdf
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import get_settings
from app.core.errors import AppException, AuthorizationException, ResourceConflictException
from app.core.security import hash_password
from app.models.company import Company, RecruiterProfile
from app.models.job import EmploymentType, Job, JobEligibleDepartment, JobSkill, JobStatus, WorkMode
from app.models.organization import Department, Institution
from app.models.placement import (
    ApplicationStatus,
    DriveActivityStatus,
    DriveActivityType,
    DriveAttendanceStatus,
    DriveLifecyclePhase,
    DriveMode,
    DriveStatus,
    Interview,
    InterviewMode,
    InterviewStatus,
    JobApplication,
    Notification,
    NotificationPreference,
    TpoScreeningStatus,
)
from app.models.resume import Resume
from app.models.student import StudentProfile, StudentSkill
from app.models.user import User, UserRole
from app.routes.drive_management import (
    create_drive_activity_endpoint,
    export_drive_report_excel_endpoint,
    export_drive_report_pdf_endpoint,
    get_drive_candidates_endpoint,
    get_drive_dashboard_endpoint,
    get_drive_form_options_endpoint,
    get_drive_report_endpoint,
    list_activity_attendance_audit_endpoint,
    list_activity_attendance_endpoint,
    list_drive_activities_endpoint,
    list_drive_announcements_endpoint,
    list_drive_registrations_endpoint,
    mark_activity_attendance_endpoint,
    send_drive_announcement_endpoint,
    student_register_drive_endpoint,
    tpo_register_students_endpoint,
    transition_drive_phase_endpoint,
    update_drive_activity_endpoint,
)
from app.routes.placement import create_drive_endpoint, update_drive_endpoint
from app.schemas.drive_workspace import (
    DriveActivityCreate,
    DriveActivityUpdate,
    DriveAnnouncementCreate,
    DriveAttendanceBatchRequest,
    DriveAttendanceMarkItem,
    DriveRegisterRequest,
    DriveTransitionRequest,
)
from app.schemas.placement import PlacementDriveCreate, PlacementDriveUpdate


def _new_test_engine():
    settings = get_settings()
    return create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        connect_args={"server_settings": {"search_path": f"{settings.DB_SCHEMA},public"}},
    )


async def _consume_streaming_body(resp) -> bytes:
    chunks = []
    async for chunk in resp.body_iterator:
        chunks.append(chunk if isinstance(chunk, (bytes, bytearray)) else chunk.encode("utf-8"))
    return b"".join(chunks)


async def _seed_drive_fixtures(session: AsyncSession):
    tag = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    pw_hash = hash_password("DrivePass123!")

    inst_a = Institution(name=f"Drive Alpha {tag}", code=f"DA{tag}".upper(), city="Jaipur", is_active=True)
    inst_b = Institution(name=f"Drive Beta {tag}", code=f"DB{tag}".upper(), city="Mumbai", is_active=True)
    session.add_all([inst_a, inst_b])
    await session.flush()

    dept_cs = Department(institution_id=inst_a.id, name="Computer Science", code=f"CS{tag[:4]}".upper(), is_active=True)
    dept_me = Department(institution_id=inst_a.id, name="Mechanical Engg", code=f"ME{tag[:4]}".upper(), is_active=True)
    dept_b = Department(institution_id=inst_b.id, name="Beta CS", code=f"BC{tag[:4]}".upper(), is_active=True)
    session.add_all([dept_cs, dept_me, dept_b])
    await session.flush()

    tpo_a = User(
        email=f"tpoa_{tag}@da.edu",
        hashed_password=pw_hash,
        full_name="TPO Alpha Coordinator",
        role=UserRole.TPO,
        institution_id=inst_a.id,
        is_active=True,
        is_verified=True,
    )
    coord_a = User(
        email=f"coorda_{tag}@da.edu",
        hashed_password=pw_hash,
        full_name="Faculty Coordinator Alpha",
        role=UserRole.TPO,
        institution_id=inst_a.id,
        is_active=True,
        is_verified=True,
    )
    tpo_b = User(
        email=f"tpob_{tag}@db.edu",
        hashed_password=pw_hash,
        full_name="TPO Beta",
        role=UserRole.TPO,
        institution_id=inst_b.id,
        is_active=True,
        is_verified=True,
    )
    rec_assoc_u = User(
        email=f"rec1_{tag}@corp.com",
        hashed_password=pw_hash,
        full_name="Recruiter Associated",
        role=UserRole.RECRUITER,
        is_active=True,
        is_verified=True,
    )
    rec_other_u = User(
        email=f"rec2_{tag}@othercorp.com",
        hashed_password=pw_hash,
        full_name="Recruiter Other",
        role=UserRole.RECRUITER,
        is_active=True,
        is_verified=True,
    )
    session.add_all([tpo_a, coord_a, tpo_b, rec_assoc_u, rec_other_u])
    await session.flush()

    comp1 = Company(name=f"Nimbus Systems {tag}", industry="Software", is_verified=True, is_active=True)
    comp2 = Company(name=f"Unrelated Corp {tag}", industry="Finance", is_verified=True, is_active=True)
    session.add_all([comp1, comp2])
    await session.flush()

    rp1 = RecruiterProfile(user_id=rec_assoc_u.id, company_id=comp1.id, designation="TA Lead")
    rp2 = RecruiterProfile(user_id=rec_other_u.id, company_id=comp2.id, designation="HR Manager")
    session.add_all([rp1, rp2])
    await session.flush()
    rec_assoc_u.recruiter_profile = rp1
    rec_other_u.recruiter_profile = rp2

    # Students:
    # s_elig1: CS batch 2026, CGPA 8.8 -> eligible
    # s_elig2: CS batch 2026, CGPA 8.1 -> eligible
    # s_low_cgpa: CS batch 2026, CGPA 6.0 -> ineligible (min_cgpa 7.5)
    # s_wrong_dept: ME batch 2026, CGPA 9.0 -> ineligible (only CS eligible)
    s_specs = [
        ("elig1", dept_cs.id, 2026, 8.8, 0),
        ("elig2", dept_cs.id, 2026, 8.1, 0),
        ("lowcgpa", dept_cs.id, 2026, 6.0, 0),
        ("wrongdept", dept_me.id, 2026, 9.0, 0),
    ]
    students = {}
    profiles = {}
    resumes = {}
    for key, dept_id, yr, cgpa, backs in s_specs:
        u = User(
            email=f"{key}_{tag}@da.edu",
            hashed_password=pw_hash,
            full_name=f"Candidate {key}",
            role=UserRole.STUDENT,
            institution_id=inst_a.id,
            department_id=dept_id,
            is_active=True,
            is_verified=True,
        )
        session.add(u)
        await session.flush()
        sp = StudentProfile(
            user_id=u.id,
            roll_number=f"26{key.upper()}_{tag[:4]}",
            graduation_year=yr,
            cgpa=cgpa,
            active_backlogs=backs,
            total_backlogs=backs,
            is_placement_ready=True,
        )
        session.add(sp)
        await session.flush()
        session.add(StudentSkill(student_id=sp.id, skill_name="Python", category="technical", is_verified=True))
        res = Resume(
            student_id=sp.id,
            file_name=f"{key}.pdf",
            file_path=f"/tmp/{key}_{tag}.pdf",
            file_type="pdf",
            file_size_bytes=2048,
            file_hash=uuid.uuid4().hex * 2,
            parsing_status="approved",
            is_active=True,
        )
        session.add(res)
        await session.flush()
        students[key] = u
        profiles[key] = sp
        resumes[key] = res

    job1 = Job(
        company_id=comp1.id,
        institution_id=inst_a.id,
        created_by_user_id=rec_assoc_u.id,
        title="Platform Software Engineer",
        description="Backend systems & APIs",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.HYBRID,
        location="Bengaluru",
        ctc_lpa=18.0,
        min_cgpa=7.5,
        target_graduation_year=2026,
        max_active_backlogs=0,
        max_total_backlogs=1,
        application_deadline=now + timedelta(days=20),
        status=JobStatus.PUBLISHED,
        is_active=True,
    )
    job_other = Job(
        company_id=comp2.id,
        institution_id=inst_b.id,
        created_by_user_id=rec_other_u.id,
        title="Other Institution Role",
        description="Restricted to Beta",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.ON_SITE,
        location="Mumbai",
        ctc_lpa=15.0,
        min_cgpa=7.0,
        target_graduation_year=2026,
        max_active_backlogs=0,
        max_total_backlogs=0,
        application_deadline=now + timedelta(days=20),
        status=JobStatus.PUBLISHED,
        is_active=True,
    )
    session.add_all([job1, job_other])
    await session.flush()

    session.add_all([
        JobEligibleDepartment(job_id=job1.id, department_id=dept_cs.id),
        JobSkill(job_id=job1.id, skill_name="Python", is_mandatory=True, weight_factor=1.5),
    ])
    await session.flush()

    return {
        "now": now,
        "inst_a": inst_a,
        "inst_b": inst_b,
        "dept_cs": dept_cs,
        "dept_me": dept_me,
        "tpo_a": tpo_a,
        "coord_a": coord_a,
        "tpo_b": tpo_b,
        "rec_assoc": rec_assoc_u,
        "rec_other": rec_other_u,
        "comp1": comp1,
        "comp2": comp2,
        "students": students,
        "profiles": profiles,
        "resumes": resumes,
        "job1": job1,
        "job_other": job_other,
    }


def test_drive_creation_form_options_and_lifecycle_transitions():
    """Verify rich drive creation, institution form-options scoping, and 7-stage lifecycle validation."""

    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_drive_fixtures(session)
                    now = fx["now"]

                    opts = await get_drive_form_options_endpoint(current_user=fx["tpo_a"], session=session)
                    assert opts.institution_id == fx["inst_a"].id
                    job_ids_in_opts = {j.id for j in opts.jobs}
                    assert fx["job1"].id in job_ids_in_opts
                    assert fx["job_other"].id not in job_ids_in_opts

                    payload = PlacementDriveCreate(
                        name="Nimbus Spring Recruitment Drive 2026",
                        academic_year="2025-2026",
                        target_graduation_year=2026,
                        registration_start_date=now - timedelta(days=1),
                        registration_end_date=now + timedelta(days=10),
                        drive_mode=DriveMode.HYBRID,
                        drive_start_date=now + timedelta(days=11),
                        drive_end_date=now + timedelta(days=14),
                        venue_location="Central Auditorium & Zoom",
                        instructions="Carry college ID and printed CV.",
                        required_documents=["Updated CV", "College ID", "Sem 1-6 Marksheet"],
                        target_graduation_batches=[2026],
                        participating_company_ids=[fx["comp1"].id],
                        eligible_department_ids=[fx["dept_cs"].id],
                        job_ids=[fx["job1"].id],
                    )
                    drive_res = await create_drive_endpoint(payload=payload, current_user=fx["tpo_a"], session=session)
                    assert drive_res.lifecycle_phase == DriveLifecyclePhase.DRAFT
                    assert drive_res.total_jobs == 1
                    assert drive_res.venue_location == "Central Auditorium & Zoom"
                    assert "Updated CV" in drive_res.required_documents

                    # Invalid direct jump: draft -> completed must be rejected
                    with pytest.raises(AppException) as exc:
                        await transition_drive_phase_endpoint(
                            drive_id=drive_res.id,
                            payload=DriveTransitionRequest(target_phase=DriveLifecyclePhase.COMPLETED),
                            current_user=fx["tpo_a"],
                            session=session,
                        )
                    assert "INVALID_DRIVE_LIFECYCLE_TRANSITION" in exc.value.code

                    # Valid lifecycle chain: draft -> scheduled -> registration_open -> registration_closed -> ongoing -> completed
                    for next_phase in (
                        DriveLifecyclePhase.SCHEDULED,
                        DriveLifecyclePhase.REGISTRATION_OPEN,
                        DriveLifecyclePhase.REGISTRATION_CLOSED,
                        DriveLifecyclePhase.ONGOING,
                        DriveLifecyclePhase.COMPLETED,
                    ):
                        tr = await transition_drive_phase_endpoint(
                            drive_id=drive_res.id,
                            payload=DriveTransitionRequest(target_phase=next_phase),
                            current_user=fx["tpo_a"],
                            session=session,
                        )
                        assert tr.lifecycle_phase == next_phase

                    # Completed drive is terminal: cannot reopen or mark ongoing
                    with pytest.raises(AppException):
                        await transition_drive_phase_endpoint(
                            drive_id=drive_res.id,
                            payload=DriveTransitionRequest(target_phase=DriveLifecyclePhase.ONGOING),
                            current_user=fx["tpo_a"],
                            session=session,
                        )

                    # Conflicting state check on PATCH: inactive drive cannot move to registration_open
                    draft_drive = await create_drive_endpoint(
                        payload=PlacementDriveCreate(
                            name="Draft Inactive Test",
                            academic_year="2025-2026",
                            target_graduation_year=2026,
                            registration_start_date=now - timedelta(days=1),
                            registration_end_date=now + timedelta(days=5),
                        ),
                        current_user=fx["tpo_a"],
                        session=session,
                    )
                    with pytest.raises(AppException):
                        await update_drive_endpoint(
                            drive_id=draft_drive.id,
                            payload=PlacementDriveUpdate(
                                is_active=False,
                                lifecycle_phase=DriveLifecyclePhase.REGISTRATION_OPEN,
                            ),
                            current_user=fx["tpo_a"],
                            session=session,
                        )
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_student_registration_eligibility_duplicate_and_candidates():
    """Verify student/TPO registration, deterministic eligibility enforcement, duplicate prevention & candidate audit."""

    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_drive_fixtures(session)
                    now = fx["now"]

                    drive_res = await create_drive_endpoint(
                        payload=PlacementDriveCreate(
                            name="Spring Placement Drive",
                            academic_year="2025-2026",
                            target_graduation_year=2026,
                            registration_start_date=now - timedelta(days=1),
                            registration_end_date=now + timedelta(days=7),
                            eligible_department_ids=[fx["dept_cs"].id],
                            job_ids=[fx["job1"].id],
                            lifecycle_phase=DriveLifecyclePhase.REGISTRATION_OPEN,
                        ),
                        current_user=fx["tpo_a"],
                        session=session,
                    )

                    # 1. Eligible student self-registers cleanly
                    reg1 = await student_register_drive_endpoint(
                        drive_id=drive_res.id,
                        payload=DriveRegisterRequest(notes="Looking forward to Backend track"),
                        current_user=fx["students"]["elig1"],
                        session=session,
                    )
                    assert reg1.eligibility_passed is True
                    assert reg1.registration_source == "student_self"

                    # 2. Duplicate registration must be rejected with ResourceConflictException
                    with pytest.raises(ResourceConflictException):
                        await student_register_drive_endpoint(
                            drive_id=drive_res.id,
                            payload=DriveRegisterRequest(),
                            current_user=fx["students"]["elig1"],
                            session=session,
                        )

                    # 3. Ineligible students (low CGPA & wrong department) blocked deterministically
                    with pytest.raises(AppException) as low_exc:
                        await student_register_drive_endpoint(
                            drive_id=drive_res.id,
                            payload=DriveRegisterRequest(),
                            current_user=fx["students"]["lowcgpa"],
                            session=session,
                        )
                    assert low_exc.value.code == "NOT_ELIGIBLE"

                    with pytest.raises(AppException) as dept_exc:
                        await student_register_drive_endpoint(
                            drive_id=drive_res.id,
                            payload=DriveRegisterRequest(),
                            current_user=fx["students"]["wrongdept"],
                            session=session,
                        )
                    assert dept_exc.value.code == "NOT_ELIGIBLE"

                    # 4. Authorized TPO registers elig2 cleanly via batch endpoint
                    batch_res = await tpo_register_students_endpoint(
                        drive_id=drive_res.id,
                        payload=DriveRegisterRequest(student_ids=[fx["profiles"]["elig2"].id], notes="TPO verified"),
                        current_user=fx["tpo_a"],
                        session=session,
                    )
                    assert len(batch_res) == 1
                    assert batch_res[0].registration_source == "tpo_enrolled"

                    # Student viewing registrations only sees their own row
                    stu_regs = await list_drive_registrations_endpoint(
                        drive_id=drive_res.id,
                        current_user=fx["students"]["elig1"],
                        session=session,
                    )
                    assert len(stu_regs) == 1
                    assert stu_regs[0].student_id == fx["profiles"]["elig1"].id

                    # Candidate management lists 2 eligible & 2 ineligible audit records with reasons
                    cands = await get_drive_candidates_endpoint(
                        drive_id=drive_res.id,
                        current_user=fx["tpo_a"],
                        session=session,
                    )
                    assert len(cands.eligible_candidates) == 2
                    assert len(cands.ineligible_audit_records) == 2
                    assert all(len(c.ineligible_reasons) >= 1 for c in cands.ineligible_audit_records)
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_scheduling_attendance_audit_communications_and_reports():
    """Verify activity scheduling, coordinator attendance + immutable audit trail, announcements, dashboard KPIs & exports."""

    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_drive_fixtures(session)
                    now = fx["now"]

                    drive_res = await create_drive_endpoint(
                        payload=PlacementDriveCreate(
                            name="Nimbus Comprehensive Drive",
                            academic_year="2025-2026",
                            target_graduation_year=2026,
                            registration_start_date=now - timedelta(days=2),
                            registration_end_date=now + timedelta(days=10),
                            eligible_department_ids=[fx["dept_cs"].id],
                            job_ids=[fx["job1"].id],
                            lifecycle_phase=DriveLifecyclePhase.ONGOING,
                        ),
                        current_user=fx["tpo_a"],
                        session=session,
                    )

                    # Register elig1 and elig2
                    await tpo_register_students_endpoint(
                        drive_id=drive_res.id,
                        payload=DriveRegisterRequest(
                            student_ids=[fx["profiles"]["elig1"].id, fx["profiles"]["elig2"].id]
                        ),
                        current_user=fx["tpo_a"],
                        session=session,
                    )

                    # Create application + interview + offer_accepted outcome for elig1
                    app1 = JobApplication(
                        job_id=fx["job1"].id,
                        student_id=fx["profiles"]["elig1"].id,
                        resume_id=fx["resumes"]["elig1"].id,
                        drive_id=drive_res.id,
                        tpo_screening_status=TpoScreeningStatus.SHORTLISTED,
                        tpo_screened_by_user_id=fx["tpo_a"].id,
                        tpo_screened_at=now - timedelta(hours=12),
                        current_status=ApplicationStatus.OFFER_ACCEPTED,
                        compatibility_score_at_application=91.5,
                        offer_package_lpa=18.5,
                        created_at=now - timedelta(days=1),
                    )
                    app2 = JobApplication(
                        job_id=fx["job1"].id,
                        student_id=fx["profiles"]["elig2"].id,
                        resume_id=fx["resumes"]["elig2"].id,
                        drive_id=drive_res.id,
                        tpo_screening_status=TpoScreeningStatus.SHORTLISTED,
                        tpo_screened_by_user_id=fx["tpo_a"].id,
                        tpo_screened_at=now - timedelta(hours=12),
                        current_status=ApplicationStatus.INTERVIEW_SCHEDULED,
                        compatibility_score_at_application=82.0,
                        created_at=now - timedelta(days=1),
                    )
                    session.add_all([app1, app2])
                    await session.flush()

                    session.add(
                        Interview(
                            application_id=app2.id,
                            round_number=1,
                            round_title="Technical Round 1",
                            scheduled_start_time=now + timedelta(hours=3),
                            duration_minutes=60,
                            interview_mode=InterviewMode.VIRTUAL,
                            status=InterviewStatus.SCHEDULED,
                            created_by_user_id=fx["tpo_a"].id,
                        )
                    )
                    await session.flush()

                    # Schedule PPT & Online Assessment assigned to coord_a
                    act_ppt = await create_drive_activity_endpoint(
                        drive_id=drive_res.id,
                        payload=DriveActivityCreate(
                            title="Nimbus Pre-Placement Talk",
                            activity_type=DriveActivityType.PRE_PLACEMENT_TALK,
                            mode=DriveMode.HYBRID,
                            scheduled_start=now + timedelta(hours=1),
                            scheduled_end=now + timedelta(hours=2),
                            venue="Seminar Hall A",
                            company_id=fx["comp1"].id,
                            coordinator_user_id=fx["coord_a"].id,
                            coordinator_name=fx["coord_a"].full_name,
                            coordinator_contact="ext-402",
                        ),
                        current_user=fx["tpo_a"],
                        session=session,
                    )
                    assert act_ppt.coordinator_user_id == fx["coord_a"].id

                    # Update activity status to completed
                    updated_act = await update_drive_activity_endpoint(
                        drive_id=drive_res.id,
                        activity_id=act_ppt.id,
                        payload=DriveActivityUpdate(status=DriveActivityStatus.COMPLETED),
                        current_user=fx["tpo_a"],
                        session=session,
                    )
                    assert updated_act.status == DriveActivityStatus.COMPLETED

                    # Assigned coordinator marks attendance, then updates elig2 from absent -> present -> excused
                    att_rows = await mark_activity_attendance_endpoint(
                        drive_id=drive_res.id,
                        activity_id=act_ppt.id,
                        payload=DriveAttendanceBatchRequest(
                            records=[
                                DriveAttendanceMarkItem(
                                    student_id=fx["profiles"]["elig1"].id,
                                    attendance_status=DriveAttendanceStatus.PRESENT,
                                    remarks="On time",
                                ),
                                DriveAttendanceMarkItem(
                                    student_id=fx["profiles"]["elig2"].id,
                                    attendance_status=DriveAttendanceStatus.ABSENT,
                                    remarks="Initially missing",
                                ),
                            ]
                        ),
                        current_user=fx["coord_a"],
                        session=session,
                    )
                    assert len(att_rows) == 2

                    await mark_activity_attendance_endpoint(
                        drive_id=drive_res.id,
                        activity_id=act_ppt.id,
                        payload=DriveAttendanceBatchRequest(
                            records=[
                                DriveAttendanceMarkItem(
                                    student_id=fx["profiles"]["elig2"].id,
                                    attendance_status=DriveAttendanceStatus.EXCUSED,
                                    remarks="Medical exemption verified",
                                ),
                            ]
                        ),
                        current_user=fx["tpo_a"],
                        session=session,
                    )

                    # Audit log preserves BOTH transitions for elig2 (None->absent and absent->excused) + 1 for elig1 = 3 audit rows
                    audits = await list_activity_attendance_audit_endpoint(
                        drive_id=drive_res.id,
                        activity_id=act_ppt.id,
                        current_user=fx["coord_a"],
                        session=session,
                    )
                    assert len(audits) == 3
                    elig2_audits = [au for au in audits if au.student_id == fx["profiles"]["elig2"].id]
                    assert elig2_audits[0].previous_status == "absent"
                    assert elig2_audits[0].new_status == "excused"
                    assert elig2_audits[1].previous_status is None
                    assert elig2_audits[1].new_status == "absent"

                    # Opt-out elig2 from placement announcements and test drive announcement delivery
                    session.add(
                        NotificationPreference(user_id=fx["students"]["elig2"].id, placement_announcements=False)
                    )
                    await session.flush()

                    ann = await send_drive_announcement_endpoint(
                        drive_id=drive_res.id,
                        payload=DriveAnnouncementCreate(
                            title="Reporting Time Update",
                            message="Report 15 minutes early at Seminar Hall A.",
                            target_audience="all_registered",
                        ),
                        current_user=fx["tpo_a"],
                        session=session,
                    )
                    assert ann.recipients_count == 1  # elig1 delivered, elig2 respected opt-out

                    anns = await list_drive_announcements_endpoint(
                        drive_id=drive_res.id,
                        current_user=fx["students"]["elig1"],
                        session=session,
                    )
                    assert len(anns) == 1

                    # Notification persisted for elig1
                    notif_cnt = len(
                        (
                            await session.execute(
                                select(Notification).where(
                                    Notification.recipient_user_id == fx["students"]["elig1"].id,
                                    Notification.related_drive_id == drive_res.id,
                                )
                            )
                        )
                        .scalars()
                        .all()
                    )
                    assert notif_cnt == 1

                    # Dashboard KPIs
                    dash = await get_drive_dashboard_endpoint(
                        drive_id=drive_res.id,
                        current_user=fx["tpo_a"],
                        session=session,
                    )
                    assert dash.total_registered_students == 2
                    assert dash.eligible_students == 2
                    assert dash.ineligible_students == 2
                    assert dash.applications_received == 2
                    assert dash.shortlisted_candidates == 2
                    assert dash.interview_scheduled_count == 1
                    assert dash.offers_released == 1
                    assert dash.final_placements == 1
                    assert dash.activities_total == 1
                    assert dash.activities_completed == 1
                    assert dash.announcements_count == 1

                    # Report JSON + PDF + Excel
                    rep = await get_drive_report_endpoint(
                        drive_id=drive_res.id,
                        current_user=fx["tpo_a"],
                        session=session,
                    )
                    assert len(rep.placed_outcomes) == 1
                    assert rep.placed_outcomes[0]["package_lpa"] == 18.5
                    assert rep.attendance_summary[0].present_count == 1
                    assert rep.attendance_summary[0].excused_count == 1

                    pdf_resp = await export_drive_report_pdf_endpoint(
                        drive_id=drive_res.id,
                        current_user=fx["tpo_a"],
                        session=session,
                    )
                    pdf_bytes = await _consume_streaming_body(pdf_resp)
                    assert pdf_bytes.startswith(b"%PDF-")
                    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
                    assert "Nimbus Comprehensive Drive" in "\n".join(p.get_text() for p in doc)
                    doc.close()

                    xlsx_resp = await export_drive_report_excel_endpoint(
                        drive_id=drive_res.id,
                        current_user=fx["tpo_a"],
                        session=session,
                    )
                    xlsx_bytes = await _consume_streaming_body(xlsx_resp)
                    assert xlsx_bytes.startswith(b"PK")
                    with zipfile.ZipFile(io.BytesIO(xlsx_bytes), "r") as zf:
                        for i in range(1, 5):
                            ET.fromstring(zf.read(f"xl/worksheets/sheet{i}.xml"))
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_drive_workspace_security_and_isolation():
    """Verify cross-institution TPO block, unauthorized attendance block, and recruiter scoping."""

    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_drive_fixtures(session)
                    now = fx["now"]

                    drive_res = await create_drive_endpoint(
                        payload=PlacementDriveCreate(
                            name="Security Scoped Drive",
                            academic_year="2025-2026",
                            target_graduation_year=2026,
                            registration_start_date=now - timedelta(days=1),
                            registration_end_date=now + timedelta(days=5),
                            job_ids=[fx["job1"].id],
                        ),
                        current_user=fx["tpo_a"],
                        session=session,
                    )
                    act = await create_drive_activity_endpoint(
                        drive_id=drive_res.id,
                        payload=DriveActivityCreate(
                            title="Tech Test",
                            activity_type=DriveActivityType.ONLINE_ASSESSMENT,
                            scheduled_start=now + timedelta(hours=1),
                            scheduled_end=now + timedelta(hours=2),
                            coordinator_user_id=fx["coord_a"].id,
                            coordinator_name=fx["coord_a"].full_name,
                        ),
                        current_user=fx["tpo_a"],
                        session=session,
                    )

                    # Cross-institution TPO Beta blocked on dashboard, candidates, activities, announcements, attendance
                    with pytest.raises(AuthorizationException):
                        await get_drive_dashboard_endpoint(
                            drive_id=drive_res.id, current_user=fx["tpo_b"], session=session
                        )
                    with pytest.raises(AuthorizationException):
                        await get_drive_candidates_endpoint(
                            drive_id=drive_res.id, current_user=fx["tpo_b"], session=session
                        )
                    with pytest.raises(AuthorizationException):
                        await list_activity_attendance_endpoint(
                            drive_id=drive_res.id, activity_id=act.id, current_user=fx["tpo_b"], session=session
                        )

                    # Unassociated recruiter blocked from activities; associated recruiter allowed read-only activities
                    with pytest.raises(AuthorizationException):
                        await list_drive_activities_endpoint(
                            drive_id=drive_res.id, current_user=fx["rec_other"], session=session
                        )
                    assoc_acts = await list_drive_activities_endpoint(
                        drive_id=drive_res.id, current_user=fx["rec_assoc"], session=session
                    )
                    assert len(assoc_acts) == 1

                    # Student cannot create activities or mark attendance
                    with pytest.raises(AuthorizationException):
                        await create_drive_activity_endpoint(
                            drive_id=drive_res.id,
                            payload=DriveActivityCreate(
                                title="Unauthorized Event",
                                activity_type=DriveActivityType.OTHER,
                                scheduled_start=now + timedelta(hours=3),
                                scheduled_end=now + timedelta(hours=4),
                                coordinator_name="Nobody",
                            ),
                            current_user=fx["students"]["elig1"],
                            session=session,
                        )
                    with pytest.raises(AuthorizationException):
                        await mark_activity_attendance_endpoint(
                            drive_id=drive_res.id,
                            activity_id=act.id,
                            payload=DriveAttendanceBatchRequest(
                                records=[
                                    DriveAttendanceMarkItem(
                                        student_id=fx["profiles"]["elig1"].id,
                                        attendance_status=DriveAttendanceStatus.PRESENT,
                                    )
                                ]
                            ),
                            current_user=fx["students"]["elig1"],
                            session=session,
                        )
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())
