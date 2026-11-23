"""Unit and Integration Tests for TASK 10: Candidate Comparison & Hiring Insights.

Validates:
1. Candidate selection bounds (2 to 5 candidates, rejection of <2 or >5).
2. Cross-job candidate comparison rejection.
3. Strict company tenant isolation and recruiter authorization.
4. Deterministic comparison accuracy across academics, skills, projects, experiences, and evaluations.
5. Historical compatibility score snapshot integrity.
6. Skill coverage matrix and relative metric rankings.
7. Evidence-grounded AI hiring insights synthesis.
8. Saved comparison session CRUD lifecycle (create, list, get, update, delete).
"""
import asyncio
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import get_settings
from app.core.errors import AppException, AuthorizationException, EntityNotFoundException
from app.models.candidate_evaluation import (
    CandidateComparisonSession,
    CandidateEvaluation,
    CandidateNote,
    EvaluationRecommendation,
    EvaluationStage,
)
from app.models.company import Company, RecruiterProfile
from app.models.job import EmploymentType, Job, JobEligibleDepartment, JobSkill, JobStatus, WorkMode
from app.models.organization import Department, Institution
from app.models.placement import (
    ApplicationStatus,
    Interview,
    InterviewMode,
    InterviewOutcome,
    InterviewStatus,
    JobApplication,
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
from app.schemas.candidate_comparison import (
    CandidateComparisonRequest,
    ComparisonSessionCreateRequest,
    ComparisonSessionUpdateRequest,
)
from app.services.candidate_comparison_service import (
    compare_candidates_for_job,
    delete_comparison_session,
    generate_candidate_comparison_ai_insights,
    get_comparison_session,
    list_comparison_sessions,
    save_comparison_session,
    update_comparison_session,
)

settings = get_settings()


def _new_test_engine():
    return create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
    )


async def _seed_comparison_fixtures(session: AsyncSession):
    tag = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)
    pwd = "$2b$12$K8yR2V56ZvZ2eF5n5FhO.OaQx7r2XpD1T6YgE7P2R2Y2Q2W2E2R2e"

    # Institution & Dept
    inst = Institution(name=f"IIT Nexus {tag}", code=f"IITN_{tag}", city="Bangalore")
    session.add(inst)
    await session.flush()

    dept = Department(institution_id=inst.id, name=f"Computer Science {tag}", code=f"CS_{tag}")
    session.add(dept)
    await session.flush()

    # Users
    u_rec1 = User(
        email=f"rec1_{tag}@alphacorp.com",
        hashed_password=pwd,
        full_name=f"Alice Recruiter {tag}",
        role=UserRole.RECRUITER,
        is_active=True,
    )
    u_rec2 = User(
        email=f"rec2_{tag}@betacorp.com",
        hashed_password=pwd,
        full_name=f"Bob Recruiter {tag}",
        role=UserRole.RECRUITER,
        is_active=True,
    )
    u_admin = User(
        email=f"admin_{tag}@platform.com",
        hashed_password=pwd,
        full_name=f"Admin User {tag}",
        role=UserRole.ADMIN,
        is_active=True,
    )
    session.add_all([u_rec1, u_rec2, u_admin])
    await session.flush()

    # Companies
    c_alpha = Company(
        institution_id=inst.id,
        name=f"Alpha Corp {tag}",
        industry="Enterprise Cloud",
        is_active=True,
        is_verified=True,
    )
    c_beta = Company(
        institution_id=inst.id,
        name=f"Beta Corp {tag}",
        industry="Fintech",
        is_active=True,
        is_verified=True,
    )
    session.add_all([c_alpha, c_beta])
    await session.flush()

    # Recruiter profiles
    rp1 = RecruiterProfile(user_id=u_rec1.id, company_id=c_alpha.id, designation="Talent Director")
    rp2 = RecruiterProfile(user_id=u_rec2.id, company_id=c_beta.id, designation="Lead Recruiter")
    session.add_all([rp1, rp2])
    await session.flush()

    # Jobs
    job_alpha = Job(
        company_id=c_alpha.id,
        institution_id=inst.id,
        created_by_user_id=u_rec1.id,
        title=f"Senior Backend Engineer {tag}",
        description="Design scalable microservices using Python and PostgreSQL.",
        location="Bangalore",
        ctc_lpa=20.0,
        work_mode=WorkMode.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        status=JobStatus.PUBLISHED,
        min_cgpa=7.5,
        max_active_backlogs=0,
        target_graduation_year=2026,
        application_deadline=now + timedelta(days=30),
    )
    job_beta = Job(
        company_id=c_beta.id,
        institution_id=inst.id,
        created_by_user_id=u_rec2.id,
        title=f"Data Platform Engineer {tag}",
        description="Build distributed data ingestion pipelines.",
        location="Remote",
        ctc_lpa=22.0,
        work_mode=WorkMode.REMOTE,
        employment_type=EmploymentType.FULL_TIME,
        status=JobStatus.PUBLISHED,
        min_cgpa=7.0,
        max_active_backlogs=0,
        target_graduation_year=2026,
        application_deadline=now + timedelta(days=30),
    )
    session.add_all([job_alpha, job_beta])
    await session.flush()

    # Job Skills
    js1 = JobSkill(job_id=job_alpha.id, skill_name="Python", is_mandatory=True, weight_factor=1.0)
    js2 = JobSkill(job_id=job_alpha.id, skill_name="PostgreSQL", is_mandatory=True, weight_factor=1.0)
    js3 = JobSkill(job_id=job_alpha.id, skill_name="Docker", is_mandatory=False, weight_factor=0.8)
    js4 = JobSkill(job_id=job_alpha.id, skill_name="Redis", is_mandatory=False, weight_factor=0.6)
    session.add_all([js1, js2, js3, js4])
    await session.flush()

    # 4 Students & Profiles
    students = []
    student_profiles = []
    resumes = []
    applications = []

    c_configs = [
        {"name": "Devin HighCGPA", "cgpa": 9.2, "skills": ["Python", "PostgreSQL", "Docker", "Redis"], "exp_months": 6},
        {"name": "Liam Practical", "cgpa": 8.1, "skills": ["Python", "PostgreSQL"], "exp_months": 12},
        {"name": "Maya MissingMandatory", "cgpa": 8.7, "skills": ["Python", "Docker"], "exp_months": 0},
        {"name": "Noah LowCGPA", "cgpa": 7.2, "skills": ["Python", "PostgreSQL", "Docker"], "exp_months": 3},
    ]

    for i, cfg in enumerate(c_configs, start=1):
        u_stu = User(
            institution_id=inst.id,
            department_id=dept.id,
            email=f"stu{i}_{tag}@apex.edu",
            hashed_password=pwd,
            full_name=f"{cfg['name']} {tag}",
            role=UserRole.STUDENT,
            is_active=True,
        )
        session.add(u_stu)
        await session.flush()
        students.append(u_stu)

        sp = StudentProfile(
            user_id=u_stu.id,
            roll_number=f"26CS0{i}_{tag}",
            graduation_year=2026,
            cgpa=cfg["cgpa"],
            active_backlogs=0,
            total_backlogs=0,
            is_placement_ready=True,
        )
        session.add(sp)
        await session.flush()
        student_profiles.append(sp)

        # Skills
        for sk_name in cfg["skills"]:
            session.add(StudentSkill(student_id=sp.id, skill_name=sk_name, proficiency_level="expert", is_verified=True))

        # Project
        session.add(StudentProject(
            student_id=sp.id,
            title=f"Scalable Pipeline by {cfg['name']}",
            description=f"Engineered microservice with {', '.join(cfg['skills'][:2])}",
            technologies=",".join(cfg["skills"]),
        ))

        # Experience
        if cfg["exp_months"] > 0:
            start_d = (now.date() - timedelta(days=cfg["exp_months"] * 30)).isoformat()
            end_d = now.date().isoformat()
            session.add(StudentExperience(
                student_id=sp.id,
                company_name=f"Tech Interns {i}",
                role_title="Software Intern",
                start_date=start_d,
                end_date=end_d,
                is_current=False,
                description="Built automated test pipelines and async handlers.",
            ))

        # Resume
        res = Resume(
            student_id=sp.id,
            file_name=f"resume_{i}_{tag}.pdf",
            file_path=f"uploads/res_{i}_{tag}.pdf",
            file_type="pdf",
            file_size_bytes=4096,
            file_hash=f"hash_{i}_{tag:0<56}",
            parsing_status="approved",
            is_active=True,
        )
        session.add(res)
        await session.flush()
        resumes.append(res)

        # Application to Alpha Corp's Job
        app = JobApplication(
            job_id=job_alpha.id,
            student_id=sp.id,
            resume_id=res.id,
            drive_id=None,
            current_status=ApplicationStatus.SHORTLISTED,
            tpo_screening_status=TpoScreeningStatus.BYPASSED,
            compatibility_score_at_application=85.0 + i,  # Distinct historical scores: 86, 87, 88, 89
        )
        session.add(app)
        await session.flush()
        applications.append(app)

    # Add an evaluation for Candidate 1
    eval1 = CandidateEvaluation(
        application_id=applications[0].id,
        interviewer_user_id=u_rec1.id,
        interviewer_name="Alice Recruiter",
        stage=EvaluationStage.TECHNICAL,
        technical_rating=5,
        problem_solving_rating=5,
        communication_rating=4,
        project_depth_rating=5,
        cultural_fit_rating=5,
        overall_rating=4.8,
        recommendation=EvaluationRecommendation.STRONG_HIRE,
        written_feedback="Exemplary systems design and clean concurrency primitives.",
    )
    session.add(eval1)
    await session.flush()

    return {
        "inst": inst,
        "dept": dept,
        "rec_alpha": u_rec1,
        "rec_beta": u_rec2,
        "admin": u_admin,
        "c_alpha": c_alpha,
        "c_beta": c_beta,
        "job_alpha": job_alpha,
        "job_beta": job_beta,
        "students": students,
        "profiles": student_profiles,
        "apps": applications,
    }


def test_candidate_selection_bounds_validation():
    """Verify that comparisons enforce between 2 and 5 candidates, and unique application IDs."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_comparison_fixtures(session)
                    job_id = fx["job_alpha"].id

                    # 1. Reject fewer than 2 candidates
                    with pytest.raises(AppException) as exc_info:
                        await compare_candidates_for_job(
                            session=session,
                            job_id=job_id,
                            application_ids=[fx["apps"][0].id],
                            current_user=fx["rec_alpha"],
                        )
                    assert exc_info.value.status_code == 400
                    assert "at least two distinct candidates" in str(exc_info.value.message)

                    # 2. Reject duplicate candidate list collapsing to <2
                    with pytest.raises(AppException) as exc_info2:
                        await compare_candidates_for_job(
                            session=session,
                            job_id=job_id,
                            application_ids=[fx["apps"][0].id, fx["apps"][0].id],
                            current_user=fx["rec_alpha"],
                        )
                    assert exc_info2.value.status_code == 400

                    # 3. Reject more than 5 candidates
                    with pytest.raises(AppException) as exc_info3:
                        await compare_candidates_for_job(
                            session=session,
                            job_id=job_id,
                            application_ids=[1, 2, 3, 4, 5, 6],
                            current_user=fx["rec_alpha"],
                        )
                    assert exc_info3.value.status_code == 400
                    assert "maximum of five candidates" in str(exc_info3.value.message)
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_cross_job_and_non_existent_candidate_rejection():
    """Verify that candidates from mismatched jobs or invalid IDs are rejected."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_comparison_fixtures(session)

                    # 1. Non-existent candidate application ID
                    with pytest.raises(EntityNotFoundException):
                        await compare_candidates_for_job(
                            session=session,
                            job_id=fx["job_alpha"].id,
                            application_ids=[fx["apps"][0].id, 999999],
                            current_user=fx["rec_alpha"],
                        )

                    # 2. Candidate from different job (Beta Corp application)
                    app_beta = JobApplication(
                        job_id=fx["job_beta"].id,
                        student_id=fx["profiles"][0].id,
                        resume_id=fx["apps"][0].resume_id,
                        current_status=ApplicationStatus.SHORTLISTED,
                        tpo_screening_status=TpoScreeningStatus.BYPASSED,
                        compatibility_score_at_application=80.0,
                    )
                    session.add(app_beta)
                    await session.flush()

                    with pytest.raises(AppException) as exc_info:
                        await compare_candidates_for_job(
                            session=session,
                            job_id=fx["job_alpha"].id,
                            application_ids=[fx["apps"][0].id, app_beta.id],
                            current_user=fx["rec_alpha"],
                        )
                    assert exc_info.value.status_code == 400
                    assert "belongs to a different job" in str(exc_info.value.message)
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_recruiter_tenant_isolation_and_admin_bypass():
    """Verify company boundaries: recruiter B cannot compare recruiter A's candidates."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_comparison_fixtures(session)
                    app_ids = [fx["apps"][0].id, fx["apps"][1].id]

                    # 1. Recruiter Beta unauthorized to compare Alpha's job
                    with pytest.raises(AuthorizationException) as exc_auth:
                        await compare_candidates_for_job(
                            session=session,
                            job_id=fx["job_alpha"].id,
                            application_ids=app_ids,
                            current_user=fx["rec_beta"],
                        )
                    assert "Access denied" in str(exc_auth.value.message)

                    # 2. Recruiter Alpha authorized
                    res_alpha = await compare_candidates_for_job(
                        session=session,
                        job_id=fx["job_alpha"].id,
                        application_ids=app_ids,
                        current_user=fx["rec_alpha"],
                    )
                    assert len(res_alpha.candidates) == 2

                    # 3. Admin can compare across any company
                    res_admin = await compare_candidates_for_job(
                        session=session,
                        job_id=fx["job_alpha"].id,
                        application_ids=app_ids,
                        current_user=fx["admin"],
                    )
                    assert len(res_admin.candidates) == 2
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_comparison_dimensions_accuracy_and_historical_integrity():
    """Verify side-by-side dimensions: academics, skills, projects, experience, evaluations, and historical score preservation."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_comparison_fixtures(session)
                    app_ids = [fx["apps"][0].id, fx["apps"][1].id, fx["apps"][2].id, fx["apps"][3].id]

                    res = await compare_candidates_for_job(
                        session=session,
                        job_id=fx["job_alpha"].id,
                        application_ids=app_ids,
                        current_user=fx["rec_alpha"],
                        generate_ai_insights=False,
                    )

                    assert len(res.candidates) == 4
                    c0, c1, c2, c3 = res.candidates[0], res.candidates[1], res.candidates[2], res.candidates[3]

                    # Check historical score preservation (seeded as 86.0, 87.0, 88.0, 89.0)
                    assert c0.compatibility_score_at_application == 86.0
                    assert c1.compatibility_score_at_application == 87.0
                    assert c2.compatibility_score_at_application == 88.0
                    assert c3.compatibility_score_at_application == 89.0

                    # Check CGPA values
                    assert c0.academics.cgpa == 9.2
                    assert c1.academics.cgpa == 8.1
                    assert c2.academics.cgpa == 8.7
                    assert c3.academics.cgpa == 7.2

                    # Check Mandatory Skill Coverage (Python + PostgreSQL)
                    # Candidate 0 has both: 100%
                    assert c0.mandatory_skills_coverage["coverage_percentage"] == 100.0
                    assert "Python" in c0.mandatory_skills_coverage["matched"]
                    assert "PostgreSQL" in c0.mandatory_skills_coverage["matched"]

                    # Candidate 2 (Maya) is missing PostgreSQL
                    assert "PostgreSQL" in c2.mandatory_skills_coverage["missing"]
                    assert c2.mandatory_skills_coverage["coverage_percentage"] == 50.0

                    # Check Work Experience months calculation
                    assert c0.total_experience_months == 6
                    assert c1.total_experience_months == 12
                    assert c2.total_experience_months == 0

                    # Check Evaluation aggregation on candidate 0
                    assert c0.evaluations_count == 1
                    assert c0.average_rating == 4.8
                    assert c0.latest_recommendation == "strong_hire"
                    assert c1.evaluations_count == 0
                    assert c1.average_rating is None
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_skill_matrix_mapping_and_rankings():
    """Verify skill matrix generation and multi-metric rankings."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_comparison_fixtures(session)
                    app_ids = [fx["apps"][0].id, fx["apps"][1].id, fx["apps"][2].id]

                    res = await compare_candidates_for_job(
                        session=session,
                        job_id=fx["job_alpha"].id,
                        application_ids=app_ids,
                        current_user=fx["rec_alpha"],
                    )

                    # Matrix has rows for mandatory Python & PostgreSQL
                    matrix_map = {r.skill_name.lower(): r for r in res.skill_matrix}
                    assert "python" in matrix_map
                    assert matrix_map["python"].is_mandatory is True
                    assert matrix_map["python"].candidate_coverage[str(fx["apps"][0].id)] is True
                    assert matrix_map["python"].candidate_coverage[str(fx["apps"][1].id)] is True
                    assert matrix_map["python"].candidate_coverage[str(fx["apps"][2].id)] is True

                    assert "postgresql" in matrix_map
                    assert matrix_map["postgresql"].candidate_coverage[str(fx["apps"][0].id)] is True
                    assert matrix_map["postgresql"].candidate_coverage[str(fx["apps"][2].id)] is False

                    # Rankings: CGPA (Devin: 9.2 > Maya: 8.7 > Liam: 8.1)
                    by_cgpa = res.rankings["by_cgpa"]
                    assert by_cgpa[0] == fx["apps"][0].id
                    assert by_cgpa[1] == fx["apps"][2].id
                    assert by_cgpa[2] == fx["apps"][1].id

                    # Highlights
                    assert res.highlights["highest_cgpa"]["candidate_name"].startswith("Devin")
                    assert res.highlights["highest_cgpa"]["cgpa"] == 9.2
                    assert res.highlights["most_experience"]["candidate_name"].startswith("Liam")
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_evidence_grounded_ai_insights_synthesis():
    """Verify AI hiring insights are anchored to verified records without hallucinations."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_comparison_fixtures(session)
                    app_ids = [fx["apps"][0].id, fx["apps"][1].id, fx["apps"][2].id]

                    res = await compare_candidates_for_job(
                        session=session,
                        job_id=fx["job_alpha"].id,
                        application_ids=app_ids,
                        current_user=fx["rec_alpha"],
                        generate_ai_insights=True,
                    )

                    insights = res.ai_insights
                    assert insights is not None
                    assert len(insights.shared_strengths) > 0
                    assert len(insights.candidate_strengths) == 3
                    assert len(insights.missing_requirements) == 3
                    assert len(insights.recommended_interview_focus) == 3

                    # Disclaimers
                    assert "does not make automated selection or rejection decisions" in insights.evidence_grounding_notes
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_saved_comparison_session_lifecycle():
    """Verify saving, listing, getting, updating, and deleting comparison sessions."""
    async def _run():
        engine = _new_test_engine()
        try:
            async with engine.connect() as conn:
                outer_tx = await conn.begin()
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    fx = await _seed_comparison_fixtures(session)
                    app_ids = [fx["apps"][0].id, fx["apps"][1].id]

                    # 1. Save Session
                    saved = await save_comparison_session(
                        session=session,
                        job_id=fx["job_alpha"].id,
                        title="Top 2 Backend Finalists",
                        application_ids=app_ids,
                        current_user=fx["rec_alpha"],
                        notes="Candidate 1 is stronger in academics, candidate 2 has more practical experience.",
                        include_ai_insights=True,
                    )
                    assert saved.id is not None
                    assert saved.title == "Top 2 Backend Finalists"
                    assert saved.application_ids == app_ids
                    assert saved.ai_summary is not None

                    # 2. List Sessions for Company
                    list_res = await list_comparison_sessions(
                        session=session,
                        current_user=fx["rec_alpha"],
                        job_id=fx["job_alpha"].id,
                    )
                    assert list_res.total >= 1
                    assert any(s.id == saved.id for s in list_res.items)

                    # 3. Other company cannot view this session
                    with pytest.raises(AuthorizationException):
                        await get_comparison_session(
                            session=session,
                            session_id=saved.id,
                            current_user=fx["rec_beta"],
                        )

                    # 4. Get Session with live comparison reload
                    sess_view, live_comp = await get_comparison_session(
                        session=session,
                        session_id=saved.id,
                        current_user=fx["rec_alpha"],
                    )
                    assert sess_view.id == saved.id
                    assert len(live_comp.candidates) == 2

                    # 5. Update Session
                    updated = await update_comparison_session(
                        session=session,
                        session_id=saved.id,
                        current_user=fx["rec_alpha"],
                        title="Top 2 Finalists - Reviewed with Hiring Manager",
                        notes="Hiring Manager agrees to schedule Candidate 1 for final round.",
                    )
                    assert updated.title == "Top 2 Finalists - Reviewed with Hiring Manager"
                    assert "Hiring Manager agrees" in updated.notes

                    # 6. Delete Session
                    del_res = await delete_comparison_session(
                        session=session,
                        session_id=saved.id,
                        current_user=fx["rec_alpha"],
                    )
                    assert del_res["deleted_id"] == saved.id

                    # Verify gone
                    with pytest.raises(EntityNotFoundException):
                        await get_comparison_session(
                            session=session,
                            session_id=saved.id,
                            current_user=fx["rec_alpha"],
                        )
                finally:
                    await outer_tx.rollback()
        finally:
            await engine.dispose()

    asyncio.run(_run())
