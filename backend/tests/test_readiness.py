"""
Tests for TASK 02: Placement Readiness Prediction & Historical Analytics.

Covers:
1. Transparent 8-indicator scoring calculation & boundary classification.
2. Separation of official academic eligibility (CGPA/backlogs) from preparation readiness.
3. Missing data handling, fairness limitations & zero sensitive attribute use.
4. Configurable indicator weights normalization.
5. Versioned historical snapshots, deltas & recommendation completion toggles.
6. Job-specific readiness diagnostic (reusing deterministic eligibility & compatibility).
7. AI recommendation generation & AIServiceError fallback resilience.
8. RBAC & strict institution-level isolation on TPO readiness analytics & filters.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.core.dependencies import require_institutional_staff, require_student
from app.core.errors import AppException, AuthorizationException, EntityNotFoundException
from app.models.company import Company
from app.models.job import EmploymentType, Job, JobSkill, JobStatus, WorkMode
from app.models.mock_interview import (
    MockInterviewCategory,
    MockInterviewDifficulty,
    MockInterviewEvaluation,
    MockInterviewSession,
    MockInterviewStatus,
)
from app.models.organization import Department
from app.models.readiness import ReadinessCategory, ReadinessSnapshot
from app.models.resume import Resume
from app.models.student import (
    StudentCertification,
    StudentExperience,
    StudentProfile,
    StudentProject,
    StudentSkill,
)
from app.models.user import User, UserRole
from app.routes import readiness as readiness_routes
from app.schemas.mock_interview import ADVISORY_MOCK_INTERVIEW_DISCLAIMER
from app.schemas.readiness import (
    READINESS_TRANSPARENCY_NOTICE,
    JobReadinessCheckRequest,
    ReadinessCalculateRequest,
    ReadinessIndicatorWeights,
    RecommendationToggleRequest,
)
from app.services.ai_provider import AIServiceError, MockAIProvider
from app.services.readiness_service import (
    calculate_and_save_readiness_snapshot,
    classify_readiness_category,
    evaluate_job_specific_readiness,
    get_student_readiness_history,
    get_student_readiness_overview,
    get_tpo_readiness_analytics,
    toggle_recommendation_completion,
)


# =============================================================================
# Helper Builders & Stateful In-Memory Session
# =============================================================================


def build_student(
    user_id: int = 1,
    institution_id: int = 1,
    department_id: int = 10,
    dept_code: str = "CSE",
    dept_name: str = "Computer Science",
    full_name: str = "Alice Student",
    graduation_year: int = 2026,
    cgpa: float = 8.6,
    active_backlogs: int = 0,
    populated: bool = True,
) -> User:
    dept = Department(id=department_id, institution_id=institution_id, name=dept_name, code=dept_code)
    user = User(
        id=user_id,
        email=f"student{user_id}@campus.edu",
        phone="+91-9876543210" if populated else None,
        full_name=full_name,
        role=UserRole.STUDENT,
        institution_id=institution_id,
        department_id=department_id,
        is_active=True,
    )
    user.department = dept
    profile = StudentProfile(
        id=user_id,
        user_id=user_id,
        roll_number=f"R2026{user_id:03d}",
        cgpa=cgpa,
        active_backlogs=active_backlogs,
        total_backlogs=active_backlogs,
        graduation_year=graduation_year,
        linkedin_url="https://linkedin.com/in/alice" if populated else None,
        github_url="https://github.com/alice" if populated else None,
        user=user,
    )
    if populated:
        profile.skills = [
            StudentSkill(id=user_id * 10 + 1, student_id=user_id, skill_name="Python", category="language", proficiency_level="advanced", is_verified=True),
            StudentSkill(id=user_id * 10 + 2, student_id=user_id, skill_name="FastAPI", category="framework", proficiency_level="advanced", is_verified=True),
            StudentSkill(id=user_id * 10 + 3, student_id=user_id, skill_name="PostgreSQL", category="tool", proficiency_level="intermediate", is_verified=True),
            StudentSkill(id=user_id * 10 + 4, student_id=user_id, skill_name="Docker", category="tool", proficiency_level="intermediate", is_verified=True),
            StudentSkill(id=user_id * 10 + 5, student_id=user_id, skill_name="React", category="framework", proficiency_level="intermediate", is_verified=False),
            StudentSkill(id=user_id * 10 + 6, student_id=user_id, skill_name="Communication", category="soft", proficiency_level="advanced", is_verified=False),
        ]
        profile.projects = [
            StudentProject(
                id=user_id * 10 + 1,
                student_id=user_id,
                title="Campus Analytics Platform",
                description="Built FastAPI and PostgreSQL analytics service with automated CI tests.",
                technologies="Python, FastAPI, PostgreSQL",
                project_url="https://github.com/alice/campus-analytics",
            ),
            StudentProject(
                id=user_id * 10 + 2,
                student_id=user_id,
                title="Real-Time Telemetry Dashboard",
                description="React and TypeScript visualization dashboard tracking placement trends cleanly.",
                technologies="React, TypeScript, Tailwind",
                project_url="https://github.com/alice/telemetry",
            ),
            StudentProject(
                id=user_id * 10 + 3,
                student_id=user_id,
                title="CLI Task Runner",
                description="Lightweight task scheduler using async Python workers and structured logging.",
                technologies="Python, Asyncio",
            ),
        ]
        profile.experiences = [
            StudentExperience(
                id=user_id * 10 + 1,
                student_id=user_id,
                company_name="CloudLabs",
                role_title="Backend Engineering Intern",
                description="Reduced SQL latency by 35% and built REST API endpoints in FastAPI.",
            ),
            StudentExperience(
                id=user_id * 10 + 2,
                student_id=user_id,
                company_name="Campus Tech Cell",
                role_title="Software Intern",
                description="Maintained student portal authentication and reporting scripts cleanly.",
            ),
        ]
        profile.certifications = [
            StudentCertification(
                id=user_id * 10 + 1,
                student_id=user_id,
                certificate_name="AWS Cloud Practitioner",
                issuing_organization="AWS",
                credential_url="https://aws.amazon.com/verify/123",
            ),
            StudentCertification(
                id=user_id * 10 + 2,
                student_id=user_id,
                certificate_name="PostgreSQL Professional",
                issuing_organization="EDB",
            ),
        ]
        res = Resume(
            id=user_id * 10 + 1,
            student_id=user_id,
            file_name="alice_resume.pdf",
            file_path="/uploads/alice_resume.pdf",
            file_type="pdf",
            file_size_bytes=102400,
            file_hash="b" * 64,
            parsing_status="approved",
            is_active=True,
            raw_extracted_text="Software Engineer skilled in Python, FastAPI, PostgreSQL, Docker, React. " * 25,
            parsed_entities_json={"skills": ["Python", "FastAPI", "PostgreSQL"]},
            updated_at=datetime.now(timezone.utc),
        )
        m1 = MockInterviewSession(
            id=user_id * 10 + 1,
            student_id=user_id,
            category=MockInterviewCategory.APTITUDE,
            difficulty=MockInterviewDifficulty.INTERMEDIATE,
            status=MockInterviewStatus.COMPLETED,
            question_count=3,
            elapsed_seconds=180,
            current_question_order=3,
            started_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        m1.evaluation = MockInterviewEvaluation(
            id=user_id * 10 + 1,
            session_id=m1.id,
            overall_score=88.0,
            technical_correctness_score=88.0,
            conceptual_understanding_score=88.0,
            problem_solving_score=88.0,
            communication_clarity_score=88.0,
            answer_structure_score=88.0,
            relevance_score=88.0,
            question_evaluations_json=[],
            strengths_json=[],
            weaknesses_json=[],
            suggested_improvements_json=[],
            recommended_topics_json=[],
            executive_summary="Great aptitude score",
            advisory_disclaimer=ADVISORY_MOCK_INTERVIEW_DISCLAIMER,
        )
        m2 = MockInterviewSession(
            id=user_id * 10 + 2,
            student_id=user_id,
            category=MockInterviewCategory.TECHNICAL,
            difficulty=MockInterviewDifficulty.INTERMEDIATE,
            status=MockInterviewStatus.COMPLETED,
            question_count=3,
            elapsed_seconds=210,
            current_question_order=3,
            started_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        m2.evaluation = MockInterviewEvaluation(
            id=user_id * 10 + 2,
            session_id=m2.id,
            overall_score=86.0,
            technical_correctness_score=86.0,
            conceptual_understanding_score=86.0,
            problem_solving_score=86.0,
            communication_clarity_score=86.0,
            answer_structure_score=86.0,
            relevance_score=86.0,
            question_evaluations_json=[],
            strengths_json=[],
            weaknesses_json=[],
            suggested_improvements_json=[],
            recommended_topics_json=[],
            executive_summary="Solid technical performance",
            advisory_disclaimer=ADVISORY_MOCK_INTERVIEW_DISCLAIMER,
        )
        profile.resumes = [res]
        profile.mock_interview_sessions = [m1, m2]
    else:
        profile.skills = []
        profile.projects = []
        profile.experiences = []
        profile.certifications = []
        profile.resumes = []
        profile.mock_interview_sessions = []

    user.student_profile = profile
    return user


def build_job(
    job_id: int = 70,
    institution_id: Optional[int] = 1,
    status: JobStatus = JobStatus.PUBLISHED,
    min_cgpa: float = 8.0,
) -> Job:
    comp = Company(id=1, name="NexaCorp", industry="Software", is_active=True)
    job = Job(
        id=job_id,
        company_id=1,
        institution_id=institution_id,
        created_by_user_id=99,
        title="Backend Platform Engineer",
        description="Build Python FastAPI services and Kubernetes deployments.",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.HYBRID,
        location="Pune",
        min_cgpa=min_cgpa,
        max_active_backlogs=0,
        max_total_backlogs=0,
        application_deadline=datetime.now(timezone.utc) + timedelta(days=20),
        status=status,
        is_active=True,
    )
    job.company = comp
    job.skills = [
        JobSkill(id=1, job_id=job_id, skill_name="Python", is_mandatory=True, weight_factor=1.5),
        JobSkill(id=2, job_id=job_id, skill_name="Kubernetes", is_mandatory=True, weight_factor=1.5),
        JobSkill(id=3, job_id=job_id, skill_name="Redis", is_mandatory=False, weight_factor=1.0),
    ]
    job.eligible_departments = []
    return job


class ScalarList:
    def __init__(self, items: List[Any]):
        self._items = list(items)

    def all(self) -> List[Any]:
        return list(self._items)


class FakeResult:
    def __init__(self, items: List[Any]):
        self._items = list(items)

    def scalar_one_or_none(self) -> Any:
        return self._items[0] if self._items else None

    def scalars(self) -> ScalarList:
        return ScalarList(self._items)


class InMemoryReadinessDB:
    def __init__(self, users: List[User], jobs: Optional[List[Job]] = None):
        self.users = list(users)
        self.profiles_by_user_id: Dict[int, StudentProfile] = {
            u.id: u.student_profile for u in users if getattr(u, "student_profile", None) is not None
        }
        self.jobs: Dict[int, Job] = {j.id: j for j in (jobs or [])}
        self.snapshots: Dict[int, ReadinessSnapshot] = {}
        self._next_snap_id = 1
        self._pending: List[Any] = []

    def add(self, obj: Any) -> None:
        if obj not in self._pending:
            self._pending.append(obj)

    async def flush(self) -> None:
        for obj in list(self._pending):
            if isinstance(obj, ReadinessSnapshot):
                if getattr(obj, "id", None) is None:
                    obj.id = self._next_snap_id
                    self._next_snap_id += 1
                self.snapshots[obj.id] = obj
        self._pending.clear()

    async def commit(self) -> None:
        await self.flush()

    async def execute(self, stmt: Any) -> FakeResult:
        sql = str(stmt)
        params = stmt.compile().params

        if "FROM placement_app_v2.student_profiles" in sql or "FROM student_profiles" in sql:
            # TPO institutional cohort query vs single student lookup
            if "institution_id_1" in params:
                inst_id = params["institution_id_1"]
                matches = [
                    u.student_profile
                    for u in self.users
                    if u.role == UserRole.STUDENT
                    and u.is_active
                    and u.institution_id == inst_id
                    and getattr(u, "student_profile", None) is not None
                ]
                matches.sort(key=lambda p: (p.user.full_name, p.roll_number))
                return FakeResult(matches)
            uid = params.get("user_id_1")
            prof = self.profiles_by_user_id.get(uid)
            return FakeResult([prof] if prof else [])

        if "FROM placement_app_v2.resumes" in sql or "FROM resumes" in sql:
            sid = params.get("student_id_1")
            for prof in self.profiles_by_user_id.values():
                if prof.id == sid:
                    return FakeResult(list(prof.resumes or []))
            return FakeResult([])

        if "FROM placement_app_v2.mock_interview_sessions" in sql or "FROM mock_interview_sessions" in sql:
            sid = params.get("student_id_1")
            for prof in self.profiles_by_user_id.values():
                if prof.id == sid:
                    return FakeResult(list(prof.mock_interview_sessions or []))
            return FakeResult([])

        if "FROM placement_app_v2.jobs" in sql or "FROM jobs" in sql:
            jid = params.get("id_1")
            job = self.jobs.get(jid)
            return FakeResult([job] if job and job.is_active else [])

        if "FROM placement_app_v2.readiness_snapshots" in sql or "FROM readiness_snapshots" in sql:
            if "readiness_snapshots.id =" in sql or "id_1" in params:
                snap = self.snapshots.get(params.get("id_1"))
                return FakeResult([snap] if snap else [])
            sid = params.get("student_id_1")
            matches = [s for s in self.snapshots.values() if sid is None or s.student_id == sid]
            if "calculated_at ASC" in sql:
                matches.sort(key=lambda s: (s.calculated_at, s.id))
            else:
                matches.sort(key=lambda s: (s.calculated_at, s.id), reverse=True)
            if "LIMIT" in sql:
                # Honor LIMIT 1 vs 2 cleanly
                limit_val = params.get("param_1", len(matches))
                if isinstance(limit_val, int):
                    matches = matches[:limit_val]
            return FakeResult(matches)

        return FakeResult([])


# =============================================================================
# 1. Boundaries, Scoring & Fairness Isolation Tests
# =============================================================================


def test_readiness_category_boundaries():
    assert classify_readiness_category(100.0)[0] == ReadinessCategory.EXCELLENT_PREPARATION
    assert classify_readiness_category(85.0)[0] == ReadinessCategory.EXCELLENT_PREPARATION
    assert classify_readiness_category(84.99)[0] == ReadinessCategory.PLACEMENT_READY
    assert classify_readiness_category(70.0)[0] == ReadinessCategory.PLACEMENT_READY
    assert classify_readiness_category(69.99)[0] == ReadinessCategory.NEEDS_IMPROVEMENT
    assert classify_readiness_category(50.0)[0] == ReadinessCategory.NEEDS_IMPROVEMENT
    assert classify_readiness_category(49.99)[0] == ReadinessCategory.REQUIRES_SIGNIFICANT_PREPARATION
    assert classify_readiness_category(0.0)[0] == ReadinessCategory.REQUIRES_SIGNIFICANT_PREPARATION


@pytest.mark.asyncio
async def test_scoring_calculation_and_academic_separation():
    high_cgpa_user = build_student(user_id=1, cgpa=9.8, active_backlogs=0, populated=True)
    low_cgpa_user = build_student(user_id=2, cgpa=5.1, active_backlogs=3, populated=True)

    db1 = InMemoryReadinessDB(users=[high_cgpa_user])
    db2 = InMemoryReadinessDB(users=[low_cgpa_user])

    with patch("app.services.readiness_service.get_ai_provider", return_value=MockAIProvider()):
        snap1 = await get_student_readiness_overview(current_user=high_cgpa_user, db=db1)
        snap2 = await get_student_readiness_overview(current_user=low_cgpa_user, db=db2)

    assert len(snap1.indicators) == 8
    assert snap1.overall_score >= 85.0
    assert snap1.category == ReadinessCategory.EXCELLENT_PREPARATION
    # Academic eligibility is displayed separately and never modifies preparation score
    assert snap1.overall_score == snap2.overall_score
    assert snap1.academic_summary.cgpa == 9.8
    assert snap2.academic_summary.cgpa == 5.1
    assert snap2.academic_summary.active_backlogs == 3
    assert snap1.transparency_notice == READINESS_TRANSPARENCY_NOTICE


@pytest.mark.asyncio
async def test_missing_data_fairness_and_custom_weights():
    sparse_user = build_student(user_id=1, populated=False)
    db = InMemoryReadinessDB(users=[sparse_user])

    with patch("app.services.readiness_service.get_ai_provider", return_value=MockAIProvider()):
        snap = await get_student_readiness_overview(current_user=sparse_user, db=db)

    assert snap.category == ReadinessCategory.REQUIRES_SIGNIFICANT_PREPARATION
    assert len(snap.missing_data_fields) >= 5
    assert any("missing data" in lim.lower() or "fresher" in lim.lower() or "unattempted" in lim.lower() for lim in snap.limitations)

    # Custom weights emphasizing profile completeness raise weighted score accordingly
    heavy_profile_weights = ReadinessIndicatorWeights(
        verified_skills=5.0,
        project_portfolio=5.0,
        internship_experience=0.0,
        certifications=0.0,
        resume_quality=5.0,
        mock_interview_performance=5.0,
        aptitude_technical_assessment=5.0,
        profile_completeness=40.0,
    )
    with patch("app.services.readiness_service.get_ai_provider", return_value=MockAIProvider()):
        custom_snap = await calculate_and_save_readiness_snapshot(
            req=ReadinessCalculateRequest(custom_weights=heavy_profile_weights, include_ai_recommendations=False),
            current_user=sparse_user,
            db=db,
        )

    assert sum(custom_snap.weights.values()) == pytest.approx(100.0, abs=0.1)
    assert custom_snap.overall_score > snap.overall_score


# =============================================================================
# 2. Historical Snapshots, Recommendation Toggles & AI Resilience
# =============================================================================


class OutageAIProvider:
    async def generate_structured(self, schema, **kwargs):
        raise AIServiceError("Simulated provider outage")


@pytest.mark.asyncio
async def test_historical_snapshots_recommendation_toggle_and_ai_fallback():
    student = build_student(user_id=1, populated=False)
    db = InMemoryReadinessDB(users=[student])

    # Snapshot 1: sparse profile + AI fallback resilience
    with patch("app.services.readiness_service.get_ai_provider", return_value=OutageAIProvider()):
        s1 = await calculate_and_save_readiness_snapshot(
            req=ReadinessCalculateRequest(include_ai_recommendations=True),
            current_user=student,
            db=db,
        )
    assert s1.ai_provider == "deterministic-fallback"
    assert len(s1.recommendations) >= 3

    # Student adds verified skills & a project, then saves Snapshot 2
    student.student_profile.skills = [
        StudentSkill(id=1, student_id=1, skill_name="Python", category="language", is_verified=True),
        StudentSkill(id=2, student_id=1, skill_name="SQL", category="tool", is_verified=True),
    ]
    student.student_profile.projects = [
        StudentProject(id=1, student_id=1, title="SQL Query Visualizer", description="Built interactive EXPLAIN analyzer in Python.", technologies="Python, PostgreSQL")
    ]
    with patch("app.services.readiness_service.get_ai_provider", return_value=MockAIProvider()):
        s2 = await calculate_and_save_readiness_snapshot(
            req=ReadinessCalculateRequest(include_ai_recommendations=True),
            current_user=student,
            db=db,
        )

    assert s2.score_delta_from_previous is not None
    assert s2.score_delta_from_previous > 0.0

    # Toggle first recommendation completed
    first_rec_id = s2.recommendations[0].id
    toggled = await toggle_recommendation_completion(
        snapshot_id=s2.id,
        recommendation_id=first_rec_id,
        completed=True,
        current_user=student,
        db=db,
    )
    assert toggled.completed_recommendations_count == 1
    assert toggled.recommendations[0].completed is True

    hist = await get_student_readiness_history(current_user=student, db=db)
    assert hist.total_snapshots == 2
    assert hist.net_change == pytest.approx(s2.overall_score - s1.overall_score, abs=0.05)
    assert hist.total_completed_recommendations == 1
    assert len(hist.trend) == 2


# =============================================================================
# 3. Job-Specific Readiness & Eligibility Separation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_job_specific_readiness_preserves_eligibility_separation_and_finds_gaps():
    # Student has strong portfolio but CGPA 7.2 < job min_cgpa 8.0, and lacks Kubernetes + Redis
    student = build_student(user_id=1, cgpa=7.2, active_backlogs=0, populated=True)
    pub_job = build_job(job_id=70, institution_id=1, status=JobStatus.PUBLISHED, min_cgpa=8.0)
    other_inst_job = build_job(job_id=71, institution_id=999, status=JobStatus.PUBLISHED, min_cgpa=6.0)
    db = InMemoryReadinessDB(users=[student], jobs=[pub_job, other_inst_job])

    with patch("app.services.readiness_service.get_ai_provider", return_value=MockAIProvider()):
        res = await evaluate_job_specific_readiness(
            req=JobReadinessCheckRequest(job_id=70),
            current_user=student,
            db=db,
        )

        # Cross-institution exclusive job blocked
        with pytest.raises(AuthorizationException):
            await evaluate_job_specific_readiness(
                req=JobReadinessCheckRequest(job_id=71),
                current_user=student,
                db=db,
            )

    assert res.academic_eligibility_checked is True
    assert res.is_academically_eligible is False  # Deterministic CGPA cutoff failed
    assert any("CGPA" in r or "cgpa" in r.lower() for r in res.eligibility_reasons)
    assert "Python" in res.matched_skills
    assert "Kubernetes" in res.missing_mandatory_skills
    assert "Redis" in res.missing_preferred_skills
    # Preparation readiness score remains high despite cutoff failure (not replaced or zeroed by CGPA)
    assert res.readiness_score >= 70.0


# =============================================================================
# 4. RBAC, TPO Institutional Isolation & Cohort Analytics Filters
# =============================================================================


@pytest.mark.asyncio
async def test_tpo_readiness_analytics_rbac_isolation_and_filters():
    s_cse = build_student(user_id=1, institution_id=1, department_id=10, dept_code="CSE", dept_name="Computer Science", full_name="Zara CSE", graduation_year=2026, populated=True)
    s_ece = build_student(user_id=2, institution_id=1, department_id=11, dept_code="ECE", dept_name="Electronics", full_name="Amit ECE", graduation_year=2027, populated=False)
    s_other_inst = build_student(user_id=3, institution_id=99, department_id=20, dept_code="IT", dept_name="IT", full_name="External Student", graduation_year=2026, populated=True)

    tpo_user = User(id=50, email="tpo@campus.edu", full_name="TPO Lead", role=UserRole.TPO, institution_id=1, is_active=True)
    recruiter_user = User(id=60, email="hr@corp.com", full_name="Recruiter", role=UserRole.RECRUITER, is_active=True)

    # RBAC checks
    with pytest.raises(HTTPException) as exc1:
        await require_institutional_staff(current_user=s_cse)
    assert exc1.value.status_code == 403
    with pytest.raises(HTTPException) as exc2:
        await require_institutional_staff(current_user=recruiter_user)
    assert exc2.value.status_code == 403
    with pytest.raises(AuthorizationException):
        await get_tpo_readiness_analytics(current_user=recruiter_user, db=InMemoryReadinessDB(users=[]))

    db = InMemoryReadinessDB(users=[s_cse, s_ece, s_other_inst])

    # Unfiltered institutional view sees 2 students from institution 1 only, ordered alphabetically (Amit before Zara, NOT ranked by score!)
    overview = await get_tpo_readiness_analytics(current_user=tpo_user, db=db)
    assert overview.institution_id == 1
    assert overview.total_students_evaluated == 2
    assert [r.full_name for r in overview.students] == ["Amit ECE", "Zara CSE"]
    assert overview.profiles_with_missing_data_count == 1
    assert len(overview.department_stats) == 2
    assert len(overview.batch_stats) == 2
    assert len(overview.skill_category_stats) >= 1

    # Filter by department_id=10 & skill_category='framework'
    filtered = await get_tpo_readiness_analytics(
        current_user=tpo_user,
        db=db,
        department_id=10,
        graduation_year=2026,
        skill_category="framework",
    )
    assert filtered.total_students_evaluated == 1
    assert filtered.students[0].full_name == "Zara CSE"


@pytest.mark.asyncio
async def test_route_handlers_wire_cleanly():
    student = build_student(user_id=1, populated=True)
    job = build_job(job_id=70)
    db = InMemoryReadinessDB(users=[student], jobs=[job])

    with patch("app.services.readiness_service.get_ai_provider", return_value=MockAIProvider()):
        me = await readiness_routes.get_my_readiness_overview(current_user=student, db=db)
        assert me.id == 1
        calc = await readiness_routes.calculate_my_readiness(
            req=ReadinessCalculateRequest(job_id=70),
            current_user=student,
            db=db,
        )
        assert calc.job_id == 70
        toggled = await readiness_routes.update_recommendation_status(
            snapshot_id=calc.id,
            recommendation_id=calc.recommendations[0].id,
            req=RecommendationToggleRequest(completed=True),
            current_user=student,
            db=db,
        )
        assert toggled.completed_recommendations_count == 1
        hist = await readiness_routes.get_my_readiness_history(current_user=student, db=db)
        assert hist.total_snapshots == 2

