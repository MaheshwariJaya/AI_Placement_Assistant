"""
Unit and Integration Tests for TASK 08: Advanced Candidate Evaluation Workspace.
Tests candidate pipeline filtering, detailed dossier compilation, structured multi-interviewer evaluations,
internal recruiter notes, documented shortlisting with TPO screening gate enforcement, company tenant isolation,
and evidence-grounded AI summary generation.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.core.errors import AppException, AuthorizationException, EntityNotFoundException
from app.models.candidate_evaluation import (
    CandidateEvaluation,
    CandidateNote,
    EvaluationRecommendation,
    EvaluationStage,
    NoteCategory,
)
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
from app.models.student import (
    StudentCertification,
    StudentEducation,
    StudentExperience,
    StudentProfile,
    StudentProject,
    StudentSkill,
)
from app.models.user import User, UserRole
from app.routes.candidate_evaluation import (
    create_candidate_note_endpoint,
    delete_candidate_note_endpoint,
    execute_status_transition_endpoint,
    generate_ai_summary_endpoint,
    get_candidate_workspace_endpoint,
    list_candidate_evaluations_endpoint,
    list_candidate_notes_endpoint,
    list_candidates_endpoint,
    submit_candidate_evaluation_endpoint,
)
from app.schemas.candidate_evaluation import (
    CandidateEvaluationCreate,
    CandidateNoteCreate,
    CandidateStatusTransitionRequest,
)
from app.services.state_machine import InvalidStateTransitionError

settings = get_settings()


def _new_test_engine():
    return create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
    )


async def _seed_workspace_fixtures(session: AsyncSession):
    """Seed corporate partners, recruiters, jobs, drives, candidates, and applications."""
    tag = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    pwd = "$2b$12$K8yR2V56ZvZ2eF5n5FhO.OaQx7r2XpD1T6YgE7P2R2Y2Q2W2E2R2e"

    # 1. Institutions & Departments
    inst = Institution(name=f"Apex Institute {tag}", code=f"APX_{tag}", city="Metropolis")
    session.add(inst)
    await session.flush()

    dept_cs = Department(institution_id=inst.id, name=f"Computer Science {tag}", code=f"CS_{tag}")
    dept_ec = Department(institution_id=inst.id, name=f"Electronics {tag}", code=f"EC_{tag}")
    session.add_all([dept_cs, dept_ec])
    await session.flush()

    # 2. Companies
    comp_a = Company(
        institution_id=inst.id,
        name=f"Nexus Technologies {tag}",
        industry="Software Engineering",
        is_verified=True,
        is_active=True,
    )
    comp_b = Company(
        institution_id=inst.id,
        name=f"Vortex Systems {tag}",
        industry="Hardware Engineering",
        is_verified=True,
        is_active=True,
    )
    session.add_all([comp_a, comp_b])
    await session.flush()

    # 3. Users: Recruiters, TPO, Admin
    tpo = User(
        institution_id=inst.id,
        email=f"tpo_{tag}@apex.edu",
        hashed_password=pwd,
        full_name=f"Prof. TPO {tag}",
        role=UserRole.TPO,
        is_active=True,
    )
    recruiter_a1 = User(
        institution_id=inst.id,
        email=f"rec_a1_{tag}@nexus.com",
        hashed_password=pwd,
        full_name=f"Recruiter Alice {tag}",
        role=UserRole.RECRUITER,
        is_active=True,
    )
    recruiter_a2 = User(
        institution_id=inst.id,
        email=f"rec_a2_{tag}@nexus.com",
        hashed_password=pwd,
        full_name=f"Interviewer Bob {tag}",
        role=UserRole.RECRUITER,
        is_active=True,
    )
    recruiter_b = User(
        institution_id=inst.id,
        email=f"rec_b_{tag}@vortex.com",
        hashed_password=pwd,
        full_name=f"Recruiter Charlie {tag}",
        role=UserRole.RECRUITER,
        is_active=True,
    )
    admin = User(
        institution_id=inst.id,
        email=f"admin_{tag}@apex.edu",
        hashed_password=pwd,
        full_name="Admin Director",
        role=UserRole.ADMIN,
        is_active=True,
    )
    session.add_all([tpo, recruiter_a1, recruiter_a2, recruiter_b, admin])
    await session.flush()

    # Profiles for recruiters
    prof_a1 = RecruiterProfile(user_id=recruiter_a1.id, company_id=comp_a.id, designation="Lead Recruiter")
    prof_a2 = RecruiterProfile(user_id=recruiter_a2.id, company_id=comp_a.id, designation="Senior Tech Interviewer")
    prof_b = RecruiterProfile(user_id=recruiter_b.id, company_id=comp_b.id, designation="Talent Specialist")
    session.add_all([prof_a1, prof_a2, prof_b])
    await session.flush()

    # 4. Jobs
    job_nexus = Job(
        company_id=comp_a.id,
        institution_id=inst.id,
        created_by_user_id=recruiter_a1.id,
        title=f"Full Stack Software Engineer {tag}",
        description="Build scalable web applications and distributed cloud microservices.",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.HYBRID,
        location="Bangalore, India",
        status=JobStatus.PUBLISHED,
        min_cgpa=7.0,
        max_active_backlogs=0,
        max_total_backlogs=1,
        target_graduation_year=2026,
        ctc_lpa=14.5,
        application_deadline=now + timedelta(days=30),
        is_active=True,
    )
    job_vortex = Job(
        company_id=comp_b.id,
        institution_id=inst.id,
        created_by_user_id=recruiter_b.id,
        title=f"Embedded Firmware Engineer {tag}",
        description="Low level firmware development for RTOS microcontrollers.",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.ON_SITE,
        location="Bangalore, India",
        status=JobStatus.PUBLISHED,
        min_cgpa=6.5,
        target_graduation_year=2026,
        ctc_lpa=11.0,
        application_deadline=now + timedelta(days=30),
        is_active=True,
    )
    session.add_all([job_nexus, job_vortex])
    await session.flush()

    # Skills for job_nexus: Python (mandatory), React (mandatory), Docker (optional)
    js1 = JobSkill(job_id=job_nexus.id, skill_name="Python", is_mandatory=True)
    js2 = JobSkill(job_id=job_nexus.id, skill_name="React", is_mandatory=True)
    js3 = JobSkill(job_id=job_nexus.id, skill_name="Docker", is_mandatory=False)
    session.add_all([js1, js2, js3])

    # Eligible departments for job_nexus: CS and EC
    jed1 = JobEligibleDepartment(job_id=job_nexus.id, department_id=dept_cs.id)
    jed2 = JobEligibleDepartment(job_id=job_nexus.id, department_id=dept_ec.id)
    session.add_all([jed1, jed2])
    await session.flush()

    # 5. Placement Drive (Campus Drive)
    drive = PlacementDrive(
        institution_id=inst.id,
        created_by_user_id=tpo.id,
        name=f"Annual Tech Drive {tag}",
        academic_year="2025-2026",
        target_graduation_year=2026,
        registration_start_date=now - timedelta(days=5),
        registration_end_date=now + timedelta(days=15),
        drive_mode=DriveMode.ON_CAMPUS,
        status=DriveStatus.ONGOING,
        lifecycle_phase=DriveLifecyclePhase.ONGOING,
        venue_location="Main Auditorium",
        target_graduation_batches=[2026],
        participating_company_ids=[comp_a.id, comp_b.id],
        eligible_department_ids=[dept_cs.id, dept_ec.id],
    )
    session.add(drive)
    await session.flush()

    pdj = PlacementDriveJob(drive_id=drive.id, job_id=job_nexus.id, is_active=True)
    session.add(pdj)
    await session.flush()

    # 6. Students
    # Student 1: John Doe (CS, CGPA 8.6, Eligible, Has Python & React)
    u_stu1 = User(
        institution_id=inst.id,
        department_id=dept_cs.id,
        email=f"john_{tag}@apex.edu",
        hashed_password=pwd,
        full_name=f"John Doe {tag}",
        role=UserRole.STUDENT,
        is_active=True,
    )
    # Student 2: Jane Smith (EC, CGPA 6.4 -> Below 7.0 cutoff for Nexus -> Ineligible)
    u_stu2 = User(
        institution_id=inst.id,
        department_id=dept_ec.id,
        email=f"jane_{tag}@apex.edu",
        hashed_password=pwd,
        full_name=f"Jane Smith {tag}",
        role=UserRole.STUDENT,
        is_active=True,
    )
    session.add_all([u_stu1, u_stu2])
    await session.flush()

    sp1 = StudentProfile(
        user_id=u_stu1.id,
        roll_number=f"26CS_{tag}",
        graduation_year=2026,
        cgpa=8.6,
        active_backlogs=0,
        total_backlogs=0,
        is_placement_ready=True,
    )
    sp2 = StudentProfile(
        user_id=u_stu2.id,
        roll_number=f"26EC_{tag}",
        graduation_year=2026,
        cgpa=6.4,
        active_backlogs=1,
        total_backlogs=2,
        is_placement_ready=False,
    )
    session.add_all([sp1, sp2])
    await session.flush()

    # Student 1 Education
    edu_10th = StudentEducation(
        student_id=sp1.id,
        institution_name="St. Xavier High School",
        degree="Class X",
        cgpa_or_percentage="92.5%",
    )
    edu_12th = StudentEducation(
        student_id=sp1.id,
        institution_name="Apex Junior College",
        degree="Class XII",
        cgpa_or_percentage="89.0%",
    )
    session.add_all([edu_10th, edu_12th])

    # Student 1 Skills, Projects, Experiences, Certifications
    s_py = StudentSkill(student_id=sp1.id, skill_name="Python", category="technical", proficiency_level="advanced", is_verified=True)
    s_react = StudentSkill(student_id=sp1.id, skill_name="React", category="technical", proficiency_level="intermediate", is_verified=True)
    s_sql = StudentSkill(student_id=sp1.id, skill_name="PostgreSQL", category="technical", proficiency_level="intermediate", is_verified=True)
    session.add_all([s_py, s_react, s_sql])

    proj1 = StudentProject(
        student_id=sp1.id,
        title="Microservice Ecommerce Backend",
        description="High throughput inventory and order checkout engine built with FastAPI and Redis caching.",
        technologies="Python, FastAPI, Redis, Docker",
        project_url="https://github.com/apex/ecommerce",
    )
    exp1 = StudentExperience(
        student_id=sp1.id,
        role_title="Software Engineering Intern",
        company_name="CloudNine Labs",
        start_date=(now.date() - timedelta(days=180)).isoformat(),
        end_date=(now.date() - timedelta(days=60)).isoformat(),
        is_current=False,
        description="Developed asynchronous ingestion pipelines and unit tests.",
    )
    cert1 = StudentCertification(
        student_id=sp1.id,
        certificate_name="AWS Certified Cloud Practitioner",
        issuing_organization="Amazon Web Services",
        issue_date=(now.date() - timedelta(days=90)).isoformat(),
        credential_url="https://aws.amazon.com/verify/cert123",
    )
    session.add_all([proj1, exp1, cert1])

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
    # App 1: John -> Nexus (Campus drive, TPO screened = shortlisted, Status = APPLIED)
    app1 = JobApplication(
        job_id=job_nexus.id,
        student_id=sp1.id,
        resume_id=res1.id,
        drive_id=drive.id,
        tpo_screening_status=TpoScreeningStatus.SHORTLISTED,
        tpo_screened_by_user_id=tpo.id,
        tpo_screened_at=now - timedelta(days=3),
        tpo_feedback="Academics verified and approved for campus drive.",
        current_status=ApplicationStatus.APPLIED,
        compatibility_score_at_application=91.5,
        created_at=now - timedelta(days=4),
    )
    # App 2: Jane -> Nexus (Campus drive, TPO screening = pending)
    app2 = JobApplication(
        job_id=job_nexus.id,
        student_id=sp2.id,
        resume_id=res2.id,
        drive_id=drive.id,
        tpo_screening_status=TpoScreeningStatus.PENDING,
        current_status=ApplicationStatus.APPLIED,
        compatibility_score_at_application=58.0,
        created_at=now - timedelta(days=2),
    )
    # App 3: John -> Vortex (Direct application, TPO screening = bypassed)
    app3 = JobApplication(
        job_id=job_vortex.id,
        student_id=sp1.id,
        resume_id=res1.id,
        drive_id=None,
        tpo_screening_status=TpoScreeningStatus.BYPASSED,
        current_status=ApplicationStatus.APPLIED,
        compatibility_score_at_application=72.0,
        created_at=now - timedelta(days=1),
    )
    session.add_all([app1, app2, app3])
    await session.flush()

    # Interview Round for App 1
    interview1 = Interview(
        application_id=app1.id,
        round_number=1,
        round_title="Technical Architecture & Coding",
        interview_mode=InterviewMode.VIRTUAL,
        scheduled_start_time=now + timedelta(days=2),
        duration_minutes=60,
        interviewer_names=recruiter_a2.full_name,
        instructions="Prepare for live coding in Python and system design questions.",
        status=InterviewStatus.SCHEDULED,
        outcome=InterviewOutcome.PENDING,
        created_by_user_id=recruiter_a1.id,
    )
    session.add(interview1)
    await session.flush()

    return {
        "inst": inst,
        "comp_a": comp_a,
        "comp_b": comp_b,
        "tpo": tpo,
        "recruiter_a1": recruiter_a1,
        "recruiter_a2": recruiter_a2,
        "recruiter_b": recruiter_b,
        "admin": admin,
        "job_nexus": job_nexus,
        "job_vortex": job_vortex,
        "drive": drive,
        "student1": u_stu1,
        "profile1": sp1,
        "app1": app1,
        "app2": app2,
        "app3": app3,
        "interview1": interview1,
    }


def test_recruiter_candidate_filtering_and_pipeline():
    """Verify recruiter can list and filter candidate applications scoped to their company."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_workspace_fixtures(session)

                    # 1. Recruiter A lists candidates -> sees app1 and app2 for Nexus Technologies
                    res = await list_candidates_endpoint(
                        job_id=None,
                        department=None,
                        current_user=fx["recruiter_a1"],
                        session=session,
                    )
                    assert res.total == 2
                    app_ids = [c.application_id for c in res.items]
                    assert fx["app1"].id in app_ids
                    assert fx["app2"].id in app_ids
                    # App 3 belongs to Vortex Systems -> Recruiter A MUST NOT see it
                    assert fx["app3"].id not in app_ids

                    # 2. Filter by minimum compatibility score
                    high_compat_res = await list_candidates_endpoint(
                        min_compatibility_score=80.0,
                        current_user=fx["recruiter_a1"],
                        session=session,
                    )
                    assert high_compat_res.total == 1
                    assert high_compat_res.items[0].application_id == fx["app1"].id

                    # 3. Filter by department (CS)
                    cs_res = await list_candidates_endpoint(
                        department="Computer Science",
                        current_user=fx["recruiter_a1"],
                        session=session,
                    )
                    assert cs_res.total == 1
                    assert cs_res.items[0].roll_number.startswith("26CS")

                    # 4. Filter by eligibility: eligible_only
                    elig_res = await list_candidates_endpoint(
                        eligibility="eligible_only",
                        current_user=fx["recruiter_a1"],
                        session=session,
                    )
                    assert elig_res.total == 1
                    assert elig_res.items[0].is_eligible is True
                    assert elig_res.items[0].application_id == fx["app1"].id

                    # 5. Filter by specific skill
                    skill_res = await list_candidates_endpoint(
                        skill="Python",
                        current_user=fx["recruiter_a1"],
                        session=session,
                    )
                    assert skill_res.total == 1
                    assert skill_res.items[0].student_name.startswith("John")
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_candidate_workspace_dossier_detail():
    """Verify complete dossier retrieval: profile, academics, skills, eligibility checklist, score, timeline."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_workspace_fixtures(session)

                    dossier = await get_candidate_workspace_endpoint(
                        application_id=fx["app1"].id,
                        current_user=fx["recruiter_a1"],
                        session=session,
                    )
                    assert dossier.application_id == fx["app1"].id
                    assert dossier.job_title.startswith("Full Stack")
                    assert dossier.company_name.startswith("Nexus")

                    # Profile & Academics
                    assert dossier.profile["full_name"].startswith("John Doe")
                    assert dossier.academics.cgpa == 8.6
                    assert dossier.academics.is_placement_ready is True
                    assert len(dossier.skills) >= 2
                    assert any(s.skill_name == "Python" for s in dossier.skills)

                    # Projects & Experience
                    assert len(dossier.projects) == 1
                    assert dossier.projects[0].title == "Microservice Ecommerce Backend"
                    assert len(dossier.experiences) == 1
                    assert dossier.experiences[0].company_name == "CloudNine Labs"

                    # Deterministic Eligibility Checklist
                    assert dossier.eligibility_checklist.is_eligible is True
                    criteria_names = [c.criterion for c in dossier.eligibility_checklist.criteria]
                    assert any("CGPA" in c for c in criteria_names)
                    assert any("Backlog" in c for c in criteria_names)

                    # Deterministic Compatibility Breakdown
                    assert dossier.compatibility_score > 0
                    assert len(dossier.matched_skills) >= 2

                    # Timeline contains application submission and TPO screening
                    timeline_types = [t.activity_type for t in dossier.timeline]
                    assert "application_submitted" in timeline_types
                    assert "tpo_screening" in timeline_types
                    assert "interview" in timeline_types
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_evaluation_form_submission_and_multi_interviewer():
    """Verify structured evaluations submitted by multiple interviewers with rating bounds and rubric."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_workspace_fixtures(session)

                    # Interviewer 1: Bob (Technical Round)
                    eval_payload_1 = CandidateEvaluationCreate(
                        interview_id=fx["interview1"].id,
                        stage=EvaluationStage.TECHNICAL,
                        technical_rating=5,
                        problem_solving_rating=4,
                        communication_rating=4,
                        project_depth_rating=5,
                        cultural_fit_rating=4,
                        overall_rating=4.5,
                        recommendation=EvaluationRecommendation.STRONG_HIRE,
                        strengths="Exceptional understanding of asynchronous concurrency and database indexing.",
                        weaknesses="Slightly hesitant on Kubernetes ingress networking.",
                        written_feedback="Strongly recommend hire for senior backend track. Coding exercise solved in 20 minutes.",
                        criteria_ratings={"System Design": 5, "Coding Cleanliness": 5, "Edge Case Handling": 4},
                    )
                    eval_resp_1 = await submit_candidate_evaluation_endpoint(
                        application_id=fx["app1"].id,
                        payload=eval_payload_1,
                        current_user=fx["recruiter_a2"],
                        session=session,
                    )
                    assert eval_resp_1.id is not None
                    assert eval_resp_1.interviewer_name == fx["recruiter_a2"].full_name
                    assert eval_resp_1.stage == EvaluationStage.TECHNICAL
                    assert eval_resp_1.overall_rating == 4.5
                    assert eval_resp_1.recommendation == EvaluationRecommendation.STRONG_HIRE

                    # Interviewer 2: Alice (HR & Cultural Fit Round)
                    eval_payload_2 = CandidateEvaluationCreate(
                        interview_id=None,
                        stage=EvaluationStage.HR,
                        technical_rating=None,
                        problem_solving_rating=4,
                        communication_rating=5,
                        project_depth_rating=4,
                        cultural_fit_rating=5,
                        overall_rating=4.6,
                        recommendation=EvaluationRecommendation.HIRE,
                        strengths="Articulate communicator, collaborative mindset, clear career ambition.",
                        weaknesses="None observed.",
                        written_feedback="Culturally aligned with high energy and curiosity.",
                    )
                    eval_resp_2 = await submit_candidate_evaluation_endpoint(
                        application_id=fx["app1"].id,
                        payload=eval_payload_2,
                        current_user=fx["recruiter_a1"],
                        session=session,
                    )
                    assert eval_resp_2.id != eval_resp_1.id
                    assert eval_resp_2.interviewer_name == fx["recruiter_a1"].full_name

                    # List evaluations
                    eval_list = await list_candidate_evaluations_endpoint(
                        application_id=fx["app1"].id,
                        current_user=fx["recruiter_a1"],
                        session=session,
                    )
                    assert len(eval_list) == 2
                    eval_ids = [e.id for e in eval_list]
                    assert eval_resp_1.id in eval_ids
                    assert eval_resp_2.id in eval_ids
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_recruiter_internal_notes_management():
    """Verify internal confidential notes creation, pinning, ordering, and deletion."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_workspace_fixtures(session)

                    # Note 1: Standard note
                    n1 = await create_candidate_note_endpoint(
                        application_id=fx["app1"].id,
                        payload=CandidateNoteCreate(
                            category=NoteCategory.INTERVIEW,
                            content="Candidate requested to reschedule Round 2 to Friday afternoon.",
                            is_pinned=False,
                        ),
                        current_user=fx["recruiter_a1"],
                        session=session,
                    )
                    assert n1.id is not None
                    assert n1.is_pinned is False

                    # Note 2: Pinned decision note
                    n2 = await create_candidate_note_endpoint(
                        application_id=fx["app1"].id,
                        payload=CandidateNoteCreate(
                            category=NoteCategory.DECISION,
                            content="Executive hiring committee approved extending full-time offer at 15 LPA.",
                            is_pinned=True,
                        ),
                        current_user=fx["recruiter_a2"],
                        session=session,
                    )
                    assert n2.is_pinned is True

                    # List notes -> Pinned note n2 must appear first!
                    notes = await list_candidate_notes_endpoint(
                        application_id=fx["app1"].id,
                        current_user=fx["recruiter_a1"],
                        session=session,
                    )
                    assert len(notes) == 2
                    assert notes[0].id == n2.id
                    assert notes[1].id == n1.id

                    # Delete note n1
                    del_res = await delete_candidate_note_endpoint(
                        application_id=fx["app1"].id,
                        note_id=n1.id,
                        current_user=fx["recruiter_a1"],
                        session=session,
                    )
                    assert del_res["note_id"] == n1.id

                    remaining = await list_candidate_notes_endpoint(
                        application_id=fx["app1"].id,
                        current_user=fx["recruiter_a1"],
                        session=session,
                    )
                    assert len(remaining) == 1
                    assert remaining[0].id == n2.id
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_shortlisting_and_state_machine_enforcement():
    """Verify recruiter status decisions and enforcement of mandatory TPO screening gate for campus drives."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_workspace_fixtures(session)

                    # 1. App 2 has tpo_screening_status = PENDING!
                    # Recruiter attempt to shortlist App 2 MUST BE BLOCKED by state machine!
                    with pytest.raises(InvalidStateTransitionError) as exc_info:
                        await execute_status_transition_endpoint(
                            application_id=fx["app2"].id,
                            payload=CandidateStatusTransitionRequest(
                                to_status=ApplicationStatus.SHORTLISTED,
                                decision_notes="Shortlisting without TPO approval.",
                            ),
                            current_user=fx["recruiter_a1"],
                            session=session,
                        )
                    assert "TPO" in str(exc_info.value.message)

                    # 2. App 1 has tpo_screening_status = SHORTLISTED!
                    # Recruiter shortlisting App 1 succeeds!
                    sl_res = await execute_status_transition_endpoint(
                        application_id=fx["app1"].id,
                        payload=CandidateStatusTransitionRequest(
                            to_status=ApplicationStatus.SHORTLISTED,
                            decision_notes="Candidate demonstrated top tier qualification; shortlisting for technical interviews.",
                        ),
                        current_user=fx["recruiter_a1"],
                        session=session,
                    )
                    assert sl_res["new_status"] == ApplicationStatus.SHORTLISTED.value

                    # Check updated record in DB
                    updated_app = await session.get(JobApplication, fx["app1"].id)
                    assert updated_app.current_status == ApplicationStatus.SHORTLISTED
                    assert "technical interviews" in updated_app.recruiter_feedback_notes
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_company_access_permissions_and_student_isolation():
    """Verify cross-company access denial and student block from recruiter workspace."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_workspace_fixtures(session)

                    # 1. Recruiter B (Vortex) tries to view App 1 (Nexus) -> 403 Forbidden!
                    with pytest.raises(AuthorizationException):
                        await get_candidate_workspace_endpoint(
                            application_id=fx["app1"].id,
                            current_user=fx["recruiter_b"],
                            session=session,
                        )

                    # 2. Recruiter B tries to submit evaluation on App 1 -> 403 Forbidden!
                    with pytest.raises(AuthorizationException):
                        await submit_candidate_evaluation_endpoint(
                            application_id=fx["app1"].id,
                            payload=CandidateEvaluationCreate(
                                overall_rating=4.0,
                                written_feedback="Unauthorized evaluation attempt.",
                            ),
                            current_user=fx["recruiter_b"],
                            session=session,
                        )

                    # 3. Student tries to access recruiter workspace -> 403 Forbidden!
                    with pytest.raises(AuthorizationException):
                        await list_candidates_endpoint(
                            current_user=fx["student1"],
                            session=session,
                        )

                    # 4. Admin can view App 1
                    admin_dossier = await get_candidate_workspace_endpoint(
                        application_id=fx["app1"].id,
                        current_user=fx["admin"],
                        session=session,
                    )
                    assert admin_dossier.application_id == fx["app1"].id
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_evidence_grounded_ai_summary():
    """Verify AI summary generation clearly separates verified facts, calculated metrics, and AI observations."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_workspace_fixtures(session)

                    summary = await generate_ai_summary_endpoint(
                        application_id=fx["app1"].id,
                        current_user=fx["recruiter_a1"],
                        session=session,
                    )
                    assert summary.candidate_id == fx["profile1"].id
                    assert summary.candidate_name.startswith("John Doe")

                    # 1. Verified Facts
                    vf = summary.verified_facts
                    assert vf["cgpa"] == 8.6
                    assert "Python" in vf["confirmed_skills"]
                    assert "Microservice Ecommerce Backend" in vf["verified_projects"]

                    # 2. Calculated Metrics (Deterministic)
                    cm = summary.calculated_metrics
                    assert cm["compatibility_score"] > 0.0
                    assert cm["is_eligible"] is True

                    # 3. AI Observations
                    ao = summary.ai_observations
                    assert len(ao["synthesized_strengths"]) >= 1
                    assert len(ao["suggested_interview_probes"]) >= 1
                    assert len(ao["areas_for_development"]) >= 1

                    # 4. Safety Disclaimer
                    assert "advisory tool grounded strictly" in summary.safety_disclaimer
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())
