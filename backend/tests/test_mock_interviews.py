"""
Tests for TASK 01: AI Mock Interview & Assessment Studio.

Covers:
1. RBAC enforcement (students only) & cross-student session isolation.
2. Target job visibility (published-only & institution scoping).
3. Interview creation across categories, difficulties, and configurable lengths.
4. Grounding in verified student skills, projects, experiences, and approved resume.
5. One-question-at-a-time progression & spoiler protection while active.
6. Answer submission (text & voice modes), duplicate rejection, and adaptive follow-ups.
7. Pause/resume state transitions and elapsed timer tracking.
8. Incomplete interviews (0 answers -> ABANDONED; partial -> COMPLETED with 0 for unanswered).
9. Structured 7-criteria evaluation & advisory compliance disclaimer.
10. AI failure handling (session creation/evaluation failure vs. resilient follow-up skip).
11. Concurrent answer submission serialization via session lock.
12. History deltas across attempts & analytics aggregation.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.dependencies import require_student
from app.core.errors import (
    AppException,
    AuthorizationException,
    EntityNotFoundException,
    ResourceConflictException,
)
from app.models.company import Company
from app.models.job import EmploymentType, Job, JobSkill, JobStatus, WorkMode
from app.models.mock_interview import (
    MockInterviewAnswer,
    MockInterviewCategory,
    MockInterviewDifficulty,
    MockInterviewEvaluation,
    MockInterviewQuestion,
    MockInterviewSession,
    MockInterviewStatus,
)
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
from app.routes import mock_interviews as mock_routes
from app.schemas.ai import AIUsageMetadata
from app.schemas.mock_interview import (
    ADVISORY_MOCK_INTERVIEW_DISCLAIMER,
    CriteriaBreakdownScores,
    FollowUpDecisionAIOutput,
    GeneratedInterviewPlan,
    GeneratedMockQuestion,
    MockInterviewAnswerSubmitRequest,
    MockInterviewCreateRequest,
    MockInterviewEvaluationAIOutput,
    MockInterviewTimerSyncRequest,
    QuestionEvaluationAIItem,
)
from app.services.ai_provider import AIServiceError, MockAIProvider
from app.services.mock_interview_service import (
    complete_mock_interview_session,
    create_mock_interview_session,
    get_mock_interview_analytics,
    get_mock_interview_session_detail,
    list_mock_interview_sessions,
    pause_mock_interview_session,
    resume_mock_interview_session,
    submit_mock_interview_answer,
)


# =============================================================================
# Helper Model Builders & Stateful Fake AsyncSession
# =============================================================================


def build_student_user(
    user_id: int = 1,
    institution_id: int = 1,
    with_portfolio: bool = True,
) -> User:
    dept = Department(id=10, institution_id=institution_id, name="Computer Science", code="CSE")
    user = User(
        id=user_id,
        email=f"student{user_id}@campus.edu",
        full_name=f"Student {user_id}",
        role=UserRole.STUDENT,
        institution_id=institution_id,
        department_id=10,
        is_active=True,
    )
    user.department = dept
    profile = StudentProfile(
        id=user_id,
        user_id=user_id,
        roll_number=f"CS2026{user_id:03d}",
        cgpa=8.6,
        active_backlogs=0,
        graduation_year=2026,
        user=user,
    )
    if with_portfolio:
        profile.skills = [
            StudentSkill(id=1, student_id=user_id, skill_name="Python", category="language", proficiency_level="advanced", is_verified=True),
            StudentSkill(id=2, student_id=user_id, skill_name="FastAPI", category="framework", proficiency_level="intermediate", is_verified=True),
            StudentSkill(id=3, student_id=user_id, skill_name="PostgreSQL", category="tool", proficiency_level="intermediate", is_verified=True),
        ]
        profile.projects = [
            StudentProject(
                id=1,
                student_id=user_id,
                title="Placement Telemetry Engine",
                description="Built async REST services and matching rules.",
                technologies="Python, FastAPI, PostgreSQL",
            )
        ]
        profile.experiences = [
            StudentExperience(
                id=1,
                student_id=user_id,
                company_name="Acme Cloud Labs",
                role_title="Backend Intern",
                description="Optimized SQL queries and FastAPI endpoints.",
            )
        ]
        profile.certifications = [
            StudentCertification(
                id=1,
                student_id=user_id,
                certificate_name="AWS Certified Cloud Practitioner",
                issuing_organization="Amazon Web Services",
            )
        ]
    else:
        profile.skills = []
        profile.projects = []
        profile.experiences = []
        profile.certifications = []

    user.student_profile = profile
    return user


def build_approved_resume(student_id: int = 1) -> Resume:
    return Resume(
        id=99,
        student_id=student_id,
        file_name="resume_cs2026.pdf",
        file_path="/uploads/resume_cs2026.pdf",
        file_type="pdf",
        file_size_bytes=123456,
        file_hash="a" * 64,
        parsing_status="approved",
        is_active=True,
        raw_extracted_text="Built Placement Telemetry Engine using Python, FastAPI, PostgreSQL with sub-50ms p95 API latency.",
        updated_at=datetime.now(timezone.utc),
    )


def build_published_job(
    job_id: int = 50,
    institution_id: Optional[int] = 1,
    status: JobStatus = JobStatus.PUBLISHED,
) -> Job:
    company = Company(id=5, name="CloudScale Systems", industry="Software", is_active=True)
    job = Job(
        id=job_id,
        company_id=5,
        institution_id=institution_id,
        created_by_user_id=10,
        title="Backend Software Engineer",
        description="Design resilient FastAPI microservices and PostgreSQL schemas.",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.HYBRID,
        location="Bengaluru",
        min_cgpa=7.0,
        max_active_backlogs=0,
        max_total_backlogs=0,
        application_deadline=datetime.now(timezone.utc) + timedelta(days=30),
        status=status,
        is_active=True,
    )
    job.company = company
    job.skills = [
        JobSkill(id=1, job_id=job_id, skill_name="Python", is_mandatory=True, weight_factor=1.5),
        JobSkill(id=2, job_id=job_id, skill_name="FastAPI", is_mandatory=True, weight_factor=1.5),
        JobSkill(id=3, job_id=job_id, skill_name="Docker", is_mandatory=False, weight_factor=1.0),
    ]
    job.eligible_departments = []
    return job


class ScalarResult:
    def __init__(self, items: List[Any]):
        self._items = list(items)

    def all(self) -> List[Any]:
        return list(self._items)


class FakeExecuteResult:
    def __init__(self, items: List[Any]):
        self._items = list(items)

    def scalar_one_or_none(self) -> Any:
        return self._items[0] if self._items else None

    def scalars(self) -> ScalarResult:
        return ScalarResult(self._items)


class InMemoryMockInterviewDB:
    """Lightweight stateful session simulating ORM persistence for mock interview entities."""

    def __init__(
        self,
        users: List[User],
        resumes: Optional[List[Resume]] = None,
        jobs: Optional[List[Job]] = None,
        arena_questions: Optional[List[Any]] = None,
    ):
        self.users_by_id: Dict[int, User] = {u.id: u for u in users}
        self.profiles_by_user_id: Dict[int, StudentProfile] = {
            u.id: u.student_profile for u in users if getattr(u, "student_profile", None) is not None
        }
        self.resumes: List[Resume] = list(resumes or [])
        self.jobs: Dict[int, Job] = {j.id: j for j in (jobs or [])}
        self.sessions: Dict[int, MockInterviewSession] = {}
        self.questions: Dict[int, MockInterviewQuestion] = {}
        self.answers: Dict[int, MockInterviewAnswer] = {}
        self.evaluations: Dict[int, MockInterviewEvaluation] = {}
        self._next_id: Dict[type, int] = {
            MockInterviewSession: 1,
            MockInterviewQuestion: 1,
            MockInterviewAnswer: 1,
            MockInterviewEvaluation: 1,
        }
        self._pending: List[Any] = []
        self.committed_count = 0
        if arena_questions is not None:
            self.arena_questions = list(arena_questions)
        else:
            from app.models.arena import ArenaQuestion, ArenaQuestionType, ArenaCategory, ArenaDifficulty
            self.arena_questions = [
                ArenaQuestion(
                    id=i,
                    title=f"Sample Question {i}",
                    prompt_text=f"Which option represents correct answer for test question {i}?",
                    category=ArenaCategory.TECHNICAL_MCQS if i % 2 == 0 else ArenaCategory.QUANTITATIVE,
                    difficulty=ArenaDifficulty.MEDIUM,
                    question_type=ArenaQuestionType.MCQ,
                    options_json=[
                        {"key": "A", "text": "Option Alpha"},
                        {"key": "B", "text": "Option Beta"},
                        {"key": "C", "text": "Option Gamma"},
                        {"key": "D", "text": "Option Delta"},
                    ],
                    correct_option_key="B",
                    explanation_text=f"Option B is the correct explanation for question {i}.",
                    role_tags_json=["civil", "aptitude", "quant"],
                    is_active=True,
                )
                for i in range(1, 15)
            ]

    def add(self, obj: Any) -> None:
        if obj not in self._pending:
            self._pending.append(obj)

    def _assign_id_if_needed(self, obj: Any) -> None:
        if getattr(obj, "id", None) is None:
            cls = type(obj)
            nxt = self._next_id.get(cls, 1)
            obj.id = nxt
            self._next_id[cls] = nxt + 1

    async def flush(self) -> None:
        now = datetime.now(timezone.utc)
        for obj in list(self._pending):
            self._assign_id_if_needed(obj)
            if isinstance(obj, MockInterviewSession):
                if getattr(obj, "created_at", None) is None:
                    obj.created_at = now
                if getattr(obj, "questions", None) is None:
                    obj.questions = []
                if obj.job_id and obj.job_id in self.jobs:
                    obj.job = self.jobs[obj.job_id]
                self.sessions[obj.id] = obj
            elif isinstance(obj, MockInterviewQuestion):
                self.questions[obj.id] = obj
                sess = self.sessions.get(obj.session_id)
                if sess is not None and obj not in sess.questions:
                    sess.questions.append(obj)
            elif isinstance(obj, MockInterviewAnswer):
                self.answers[obj.id] = obj
                q = self.questions.get(obj.question_id)
                if q is not None:
                    q.answer = obj
            elif isinstance(obj, MockInterviewEvaluation):
                self.evaluations[obj.id] = obj
                sess = self.sessions.get(obj.session_id)
                if sess is not None:
                    sess.evaluation = obj
        self._pending.clear()

    async def commit(self) -> None:
        await self.flush()
        self.committed_count += 1

    async def execute(self, stmt: Any) -> FakeExecuteResult:
        stmt_text = str(stmt)
        if "FROM placement_app_v2.arena_questions" in stmt_text or "FROM arena_questions" in stmt_text:
            return FakeExecuteResult(list(self.arena_questions))

        if "FROM placement_app_v2.student_profiles" in stmt_text or "FROM student_profiles" in stmt_text:
            params = stmt.compile().params
            uid = next(iter(params.values()), None)
            prof = self.profiles_by_user_id.get(uid)
            return FakeExecuteResult([prof] if prof else [])

        if "FROM placement_app_v2.resumes" in stmt_text or "FROM resumes" in stmt_text:
            params = stmt.compile().params
            sid = params.get("student_id_1")
            matches = [
                r for r in self.resumes
                if (sid is None or r.student_id == sid)
                and r.parsing_status == "approved"
                and r.is_active
            ]
            return FakeExecuteResult(matches[:1])

        if "FROM placement_app_v2.jobs" in stmt_text or "FROM jobs" in stmt_text:
            params = stmt.compile().params
            jid = params.get("id_1")
            if jid is not None:
                job = self.jobs.get(jid)
                return FakeExecuteResult([job] if job and job.is_active else [])
            return FakeExecuteResult([j for j in self.jobs.values() if j.is_active and j.status == JobStatus.PUBLISHED])

        if "FROM placement_app_v2.mock_interview_questions" in stmt_text or "FROM mock_interview_questions" in stmt_text:
            params = stmt.compile().params
            sid = params.get("session_id_1")
            qs = sorted(
                [q for q in self.questions.values() if sid is None or q.session_id == sid],
                key=lambda q: q.question_order,
            )
            return FakeExecuteResult(qs)

        if "FROM placement_app_v2.mock_interview_sessions" in stmt_text or "FROM mock_interview_sessions" in stmt_text:
            params = stmt.compile().params
            if "mock_interview_sessions.id =" in stmt_text or "id_1" in params:
                sess_id = params.get("id_1")
                sess = self.sessions.get(sess_id)
                return FakeExecuteResult([sess] if sess else [])
            student_id = params.get("student_id_1")
            matches = [
                s for s in self.sessions.values()
                if student_id is None or s.student_id == student_id
            ]
            if "category_1" in params:
                cat_val = params["category_1"]
                matches = [s for s in matches if s.category == cat_val or s.category.value == cat_val]
            if "status_1" in params:
                st_val = params["status_1"]
                matches = [s for s in matches if s.status == st_val or s.status.value == st_val]
            if "created_at DESC" in stmt_text:
                matches.sort(key=lambda s: s.created_at, reverse=True)
            else:
                matches.sort(key=lambda s: s.created_at)
            return FakeExecuteResult(matches)

        return FakeExecuteResult([])


# =============================================================================
# 1. RBAC, Visibility & Grounding Tests
# =============================================================================


@pytest.mark.asyncio
async def test_rbac_blocks_non_student_and_missing_profile():
    recruiter = User(id=20, email="recruiter@co.com", full_name="Recruiter", role=UserRole.RECRUITER, is_active=True)
    with pytest.raises(HTTPException) as exc_info:
        await require_student(current_user=recruiter)
    assert exc_info.value.status_code == 403

    student_no_profile = User(id=21, email="noprofile@campus.edu", full_name="No Profile", role=UserRole.STUDENT, is_active=True)
    db = InMemoryMockInterviewDB(users=[student_no_profile])
    with patch("app.services.mock_interview_service.get_ai_provider", return_value=MockAIProvider()):
        with pytest.raises(AppException) as app_err:
            await create_mock_interview_session(
                req=MockInterviewCreateRequest(category=MockInterviewCategory.TECHNICAL, question_count=3),
                current_user=student_no_profile,
                db=db,
            )
    assert app_err.value.code == "STUDENT_PROFILE_REQUIRED"


@pytest.mark.asyncio
async def test_job_visibility_blocks_draft_and_cross_institution_jobs():
    student = build_student_user(user_id=1, institution_id=1)
    draft_job = build_published_job(job_id=51, institution_id=1, status=JobStatus.DRAFT)
    other_inst_job = build_published_job(job_id=52, institution_id=999, status=JobStatus.PUBLISHED)
    db = InMemoryMockInterviewDB(users=[student], jobs=[draft_job, other_inst_job])

    with patch("app.services.mock_interview_service.get_ai_provider", return_value=MockAIProvider()):
        with pytest.raises(AppException) as draft_err:
            await create_mock_interview_session(
                req=MockInterviewCreateRequest(category=MockInterviewCategory.TECHNICAL, job_id=51, question_count=3),
                current_user=student,
                db=db,
            )
        assert draft_err.value.code == "JOB_NOT_PUBLISHED"

        with pytest.raises(AuthorizationException):
            await create_mock_interview_session(
                req=MockInterviewCreateRequest(category=MockInterviewCategory.TECHNICAL, job_id=52, question_count=3),
                current_user=student,
                db=db,
            )


@pytest.mark.asyncio
async def test_cross_student_session_isolation():
    student_a = build_student_user(user_id=1, institution_id=1)
    student_b = build_student_user(user_id=2, institution_id=1)
    db = InMemoryMockInterviewDB(users=[student_a, student_b])

    with patch("app.services.mock_interview_service.get_ai_provider", return_value=MockAIProvider()):
        created = await create_mock_interview_session(
            req=MockInterviewCreateRequest(category=MockInterviewCategory.HR, question_count=3),
            current_user=student_a,
            db=db,
        )
        with pytest.raises(AuthorizationException):
            await get_mock_interview_session_detail(session_id=created.id, current_user=student_b, db=db)


# =============================================================================
# 2. Creation Across Categories, Grounding & Spoiler Protection Tests
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "category,difficulty,q_count",
    [
        (MockInterviewCategory.TECHNICAL, MockInterviewDifficulty.BEGINNER, 3),
        (MockInterviewCategory.HR, MockInterviewDifficulty.INTERMEDIATE, 4),
        (MockInterviewCategory.BEHAVIORAL, MockInterviewDifficulty.ADVANCED, 5),
        (MockInterviewCategory.APTITUDE, MockInterviewDifficulty.INTERMEDIATE, 3),
        (MockInterviewCategory.PROJECT_BASED, MockInterviewDifficulty.ADVANCED, 4),
    ],
)
async def test_create_interview_all_categories_grounding_and_spoiler_protection(
    category: MockInterviewCategory,
    difficulty: MockInterviewDifficulty,
    q_count: int,
):
    student = build_student_user(user_id=1, institution_id=1, with_portfolio=True)
    resume = build_approved_resume(student_id=1)
    job = build_published_job(job_id=50, institution_id=1)
    db = InMemoryMockInterviewDB(users=[student], resumes=[resume], jobs=[job])

    provider = MockAIProvider()
    with patch("app.services.mock_interview_service.get_ai_provider", return_value=provider):
        detail = await create_mock_interview_session(
            req=MockInterviewCreateRequest(
                category=category,
                difficulty=difficulty,
                question_count=q_count,
                job_id=50,
                include_followups=True,
                time_limit_minutes=25,
            ),
            current_user=student,
            db=db,
        )

    assert detail.status == MockInterviewStatus.IN_PROGRESS
    assert detail.category == category
    assert detail.difficulty == difficulty
    assert detail.question_count == q_count
    assert len(detail.questions) == q_count
    assert detail.current_question is not None
    assert detail.current_question.question_order == 1

    # Grounded in verified portfolio + approved resume + target job
    assert detail.context_snapshot["approved_resume_id"] == 99
    assert "Python" in detail.context_snapshot["skills_used"]
    assert "Placement Telemetry Engine" in detail.context_snapshot["projects_used"]
    assert detail.context_snapshot["target_job"]["job_title"] == "Backend Software Engineer"

    # Spoiler protection while session is active
    for q in detail.questions:
        assert q.model_answer is None
        assert q.expected_key_points is None


# =============================================================================
# 3. Full Interview Lifecycle, Follow-ups, Pause/Resume & 7-Criteria Evaluation
# =============================================================================


@pytest.mark.asyncio
async def test_full_interview_flow_with_voice_followup_pause_and_evaluation():
    student = build_student_user(user_id=1)
    resume = build_approved_resume(student_id=1)
    job = build_published_job(job_id=50)
    db = InMemoryMockInterviewDB(users=[student], resumes=[resume], jobs=[job])
    provider = MockAIProvider()

    with patch("app.services.mock_interview_service.get_ai_provider", return_value=provider):
        created = await create_mock_interview_session(
            req=MockInterviewCreateRequest(
                category=MockInterviewCategory.PROJECT_BASED,
                difficulty=MockInterviewDifficulty.INTERMEDIATE,
                question_count=3,
                job_id=50,
                include_followups=True,
            ),
            current_user=student,
            db=db,
        )

        # Pause & fail answer while paused
        paused = await pause_mock_interview_session(
            session_id=created.id, elapsed_seconds=45, current_user=student, db=db
        )
        assert paused.status == MockInterviewStatus.PAUSED
        assert paused.elapsed_seconds == 45

        with pytest.raises(AppException) as paused_err:
            await submit_mock_interview_answer(
                session_id=created.id,
                question_id=created.questions[0].id,
                answer_text="Attempt while paused",
                input_mode="text",
                response_time_seconds=10,
                elapsed_seconds=50,
                current_user=student,
                db=db,
            )
        assert paused_err.value.code == "MOCK_SESSION_PAUSED"

        # Resume & answer short Q1 -> MockAIProvider triggers a follow-up question
        resumed = await resume_mock_interview_session(session_id=created.id, current_user=student, db=db)
        assert resumed.status == MockInterviewStatus.IN_PROGRESS

        first_res = await submit_mock_interview_answer(
            session_id=created.id,
            question_id=created.questions[0].id,
            answer_text="Used FastAPI with PostgreSQL indexes for performance.",
            input_mode="voice",
            response_time_seconds=22,
            elapsed_seconds=70,
            current_user=student,
            db=db,
        )
        assert first_res.submitted_answer.input_mode == "voice"
        assert first_res.followup_generated is True
        assert len(first_res.session.questions) == 4
        assert [q.question_order for q in first_res.session.questions] == [1, 2, 3, 4]
        assert first_res.session.questions[1].is_followup is True
        assert first_res.next_question is not None
        assert first_res.next_question.id == first_res.session.questions[1].id

        # Duplicate answer rejected cleanly
        with pytest.raises(ResourceConflictException) as dup_err:
            await submit_mock_interview_answer(
                session_id=created.id,
                question_id=created.questions[0].id,
                answer_text="Trying to overwrite Q1",
                input_mode="text",
                response_time_seconds=5,
                elapsed_seconds=75,
                current_user=student,
                db=db,
            )
        assert dup_err.value.code == "ANSWER_ALREADY_SUBMITTED"

        # Answer remaining questions (detailed STAR/technical responses)
        while True:
            cur = await get_mock_interview_session_detail(session_id=created.id, current_user=student, db=db)
            if cur.current_question is None:
                break
            ans_res = await submit_mock_interview_answer(
                session_id=created.id,
                question_id=cur.current_question.id,
                answer_text=(
                    "In the Placement Telemetry Engine project, I analyzed query bottlenecks with EXPLAIN ANALYZE, "
                    "added composite B-tree indexes in PostgreSQL, and structured async FastAPI handlers with strict "
                    "Pydantic validation, reducing p95 latency by 45% under concurrent student portal load."
                ),
                input_mode="text",
                response_time_seconds=35,
                elapsed_seconds=180,
                current_user=student,
                db=db,
            )
            if ans_res.ready_to_complete:
                break

        # Complete & verify 7-criteria evaluation + revealed model answers
        completed = await complete_mock_interview_session(
            session_id=created.id, elapsed_seconds=210, current_user=student, db=db
        )

    assert completed.status == MockInterviewStatus.COMPLETED
    assert completed.evaluation is not None
    assert 0.0 <= completed.evaluation.overall_score <= 100.0
    assert completed.evaluation.criteria_scores.project_knowledge is not None
    assert completed.evaluation.advisory_disclaimer == ADVISORY_MOCK_INTERVIEW_DISCLAIMER
    assert len(completed.evaluation.question_evaluations) == len(completed.questions)
    assert completed.evaluation.strengths
    assert completed.evaluation.recommended_topics
    # Model answers unlocked after completion
    assert all(q.model_answer for q in completed.questions)


# =============================================================================
# 4. Incomplete / Abandoned Sessions & Early Finish Tests
# =============================================================================


@pytest.mark.asyncio
async def test_incomplete_zero_answers_becomes_abandoned_and_partial_answers_score_honestly():
    student = build_student_user(user_id=1)
    db = InMemoryMockInterviewDB(users=[student])
    provider = MockAIProvider()

    with patch("app.services.mock_interview_service.get_ai_provider", return_value=provider):
        # Case A: ended with 0 answers -> ABANDONED, no fabricated evaluation
        s_zero = await create_mock_interview_session(
            req=MockInterviewCreateRequest(category=MockInterviewCategory.APTITUDE, question_count=3),
            current_user=student,
            db=db,
        )
        ended_zero = await complete_mock_interview_session(
            session_id=s_zero.id, elapsed_seconds=15, current_user=student, db=db
        )
        assert ended_zero.status == MockInterviewStatus.ABANDONED
        assert ended_zero.evaluation is None

        # Cannot re-complete an abandoned interview
        with pytest.raises(AppException) as aband_err:
            await complete_mock_interview_session(
                session_id=s_zero.id, elapsed_seconds=20, current_user=student, db=db
            )
        assert aband_err.value.code == "MOCK_SESSION_ABANDONED"

        # Case B: ended early with 1 of 3 answered -> COMPLETED, unanswered items score 0.0
        s_partial = await create_mock_interview_session(
            req=MockInterviewCreateRequest(
                category=MockInterviewCategory.TECHNICAL,
                question_count=3,
                include_followups=False,
            ),
            current_user=student,
            db=db,
        )
        await submit_mock_interview_answer(
            session_id=s_partial.id,
            question_id=s_partial.questions[0].id,
            answer_text="Hash maps provide O(1) average lookup time via bucket hashing and handle collisions via chaining or open addressing.",
            input_mode="text",
            response_time_seconds=25,
            elapsed_seconds=40,
            current_user=student,
            db=db,
        )
        ended_partial = await complete_mock_interview_session(
            session_id=s_partial.id, elapsed_seconds=45, current_user=student, db=db
        )

    assert ended_partial.status == MockInterviewStatus.COMPLETED
    assert ended_partial.evaluation is not None
    q_evals = ended_partial.evaluation.question_evaluations
    assert q_evals[0].score > 0.0
    assert q_evals[1].score == 0.0
    assert q_evals[2].score == 0.0


# =============================================================================
# 5. AI Failure & Concurrent Submission Safety Tests
# =============================================================================


class FailingPlanProvider:
    async def generate_structured(self, schema, **kwargs):
        raise AIServiceError("Simulated upstream LLM outage")


class FlakyFollowupProvider(MockAIProvider):
    async def generate_structured(self, schema, **kwargs):
        if schema is FollowUpDecisionAIOutput:
            raise AIServiceError("Transient follow-up timeout")
        return await super().generate_structured(schema, **kwargs)


@pytest.mark.asyncio
async def test_ai_failures_on_create_and_graceful_followup_skip():
    student = build_student_user(user_id=1)
    db = InMemoryMockInterviewDB(users=[student])

    # When live AI fails, the service falls back to branch-cognizant curated synthesis
    with patch("app.services.mock_interview_service.get_ai_provider", return_value=FailingPlanProvider()):
        fallback_session = await create_mock_interview_session(
            req=MockInterviewCreateRequest(category=MockInterviewCategory.TECHNICAL, question_count=3),
            current_user=student,
            db=db,
        )
        assert fallback_session is not None
        assert len(fallback_session.questions) == 3
        assert fallback_session.ai_provider == "synthesizer"

    with patch("app.services.mock_interview_service.get_ai_provider", return_value=FlakyFollowupProvider()):
        created = await create_mock_interview_session(
            req=MockInterviewCreateRequest(category=MockInterviewCategory.HR, question_count=3, include_followups=True),
            current_user=student,
            db=db,
        )
        res = await submit_mock_interview_answer(
            session_id=created.id,
            question_id=created.questions[0].id,
            answer_text="Short answer",
            input_mode="text",
            response_time_seconds=12,
            elapsed_seconds=20,
            current_user=student,
            db=db,
        )
    # Answer persisted even when follow-up generation failed
    assert res.followup_generated is False
    assert res.submitted_answer.answer_text == "Short answer"
    assert len(res.session.questions) == 3


@pytest.mark.asyncio
async def test_concurrent_duplicate_answer_submissions_are_serialized():
    student = build_student_user(user_id=1)
    db = InMemoryMockInterviewDB(users=[student])
    provider = MockAIProvider()

    with patch("app.services.mock_interview_service.get_ai_provider", return_value=provider):
        created = await create_mock_interview_session(
            req=MockInterviewCreateRequest(
                category=MockInterviewCategory.BEHAVIORAL,
                question_count=3,
                include_followups=False,
            ),
            current_user=student,
            db=db,
        )
        q1_id = created.questions[0].id

        results = await asyncio.gather(
            submit_mock_interview_answer(
                session_id=created.id,
                question_id=q1_id,
                answer_text="First concurrent answer via STAR method with quantified outcome.",
                input_mode="text",
                response_time_seconds=15,
                elapsed_seconds=30,
                current_user=student,
                db=db,
            ),
            submit_mock_interview_answer(
                session_id=created.id,
                question_id=q1_id,
                answer_text="Second racing answer for same question.",
                input_mode="text",
                response_time_seconds=15,
                elapsed_seconds=31,
                current_user=student,
                db=db,
            ),
            return_exceptions=True,
        )

    successes = [r for r in results if not isinstance(r, Exception)]
    conflicts = [r for r in results if isinstance(r, ResourceConflictException)]
    assert len(successes) == 1
    assert len(conflicts) == 1
    assert conflicts[0].code == "ANSWER_ALREADY_SUBMITTED"


# =============================================================================
# 6. History Score Deltas, Analytics & Route Handler Tests
# =============================================================================


@pytest.mark.asyncio
async def test_history_comparison_and_analytics_trends():
    student = build_student_user(user_id=1)
    db = InMemoryMockInterviewDB(users=[student])

    # Pre-seed two chronological completed interviews (attempt 1: 68.0, attempt 2: 84.5)
    t1 = datetime.now(timezone.utc) - timedelta(days=2)
    t2 = datetime.now(timezone.utc) - timedelta(days=1)

    s1 = MockInterviewSession(
        id=101,
        student_id=1,
        target_role="Backend Engineer",
        category=MockInterviewCategory.TECHNICAL,
        difficulty=MockInterviewDifficulty.BEGINNER,
        status=MockInterviewStatus.COMPLETED,
        question_count=3,
        include_followups=False,
        elapsed_seconds=300,
        current_question_order=3,
        started_at=t1,
        completed_at=t1 + timedelta(minutes=5),
        created_at=t1,
    )
    e1 = MockInterviewEvaluation(
        id=201,
        session_id=101,
        overall_score=68.0,
        technical_correctness_score=70.0,
        conceptual_understanding_score=69.0,
        problem_solving_score=66.0,
        communication_clarity_score=68.0,
        answer_structure_score=64.0,
        relevance_score=72.0,
        project_knowledge_score=None,
        question_evaluations_json=[],
        strengths_json=["Clear basics"],
        weaknesses_json=["Needs deeper complexity analysis"],
        suggested_improvements_json=["Discuss edge cases upfront"],
        recommended_topics_json=["Indexing & Query Plans"],
        executive_summary="Solid foundational attempt.",
        advisory_disclaimer=ADVISORY_MOCK_INTERVIEW_DISCLAIMER,
        evaluated_at=t1 + timedelta(minutes=5),
    )
    s1.evaluation = e1
    s1.questions = []

    s2 = MockInterviewSession(
        id=102,
        student_id=1,
        target_role="Backend Engineer",
        category=MockInterviewCategory.PROJECT_BASED,
        difficulty=MockInterviewDifficulty.INTERMEDIATE,
        status=MockInterviewStatus.COMPLETED,
        question_count=3,
        include_followups=True,
        elapsed_seconds=420,
        current_question_order=3,
        started_at=t2,
        completed_at=t2 + timedelta(minutes=7),
        created_at=t2,
    )
    e2 = MockInterviewEvaluation(
        id=202,
        session_id=102,
        overall_score=84.5,
        technical_correctness_score=86.0,
        conceptual_understanding_score=85.0,
        problem_solving_score=84.0,
        communication_clarity_score=83.0,
        answer_structure_score=82.0,
        relevance_score=88.0,
        project_knowledge_score=85.0,
        question_evaluations_json=[],
        strengths_json=["Strong metrics and project depth"],
        weaknesses_json=["Needs deeper complexity analysis"],
        suggested_improvements_json=["Quantify scalability limits"],
        recommended_topics_json=["Distributed Caching"],
        executive_summary="Strong improvement across criteria.",
        advisory_disclaimer=ADVISORY_MOCK_INTERVIEW_DISCLAIMER,
        evaluated_at=t2 + timedelta(minutes=7),
    )
    s2.evaluation = e2
    s2.questions = []

    db.sessions[101] = s1
    db.sessions[102] = s2
    db.evaluations[201] = e1
    db.evaluations[202] = e2

    history = await list_mock_interview_sessions(current_user=student, db=db)
    assert len(history) == 2
    by_id = {item.id: item for item in history}
    assert by_id[101].score_delta_from_previous is None
    assert by_id[102].score_delta_from_previous == 16.5

    analytics = await get_mock_interview_analytics(current_user=student, db=db)
    assert analytics.total_sessions == 2
    assert analytics.completed_sessions == 2
    assert analytics.best_score == 84.5
    assert analytics.latest_score == 84.5
    assert analytics.improvement_delta == 16.5
    assert analytics.average_score == 76.2 or analytics.average_score == 76.3
    assert len(analytics.score_trend) == 2
    assert analytics.score_trend[0].attempt_number == 1
    assert analytics.score_trend[1].attempt_number == 2
    assert "Needs deeper complexity analysis" in analytics.areas_requiring_improvement
    assert analytics.advisory_disclaimer == ADVISORY_MOCK_INTERVIEW_DISCLAIMER


@pytest.mark.asyncio
async def test_route_handlers_wire_to_service_layer():
    student = build_student_user(user_id=1)
    job = build_published_job(job_id=50)
    db = InMemoryMockInterviewDB(users=[student], jobs=[job])

    with patch("app.services.mock_interview_service.get_ai_provider", return_value=MockAIProvider()):
        jobs = await mock_routes.get_target_jobs_for_mock_interview(current_user=student, db=db)
        assert len(jobs) == 1
        assert jobs[0].id == 50

        created = await mock_routes.create_mock_interview(
            req=MockInterviewCreateRequest(category=MockInterviewCategory.TECHNICAL, job_id=50, question_count=3),
            current_user=student,
            db=db,
        )
        paused = await mock_routes.pause_mock_interview(
            session_id=created.id,
            req=MockInterviewTimerSyncRequest(elapsed_seconds=12),
            current_user=student,
            db=db,
        )
        assert paused.status == MockInterviewStatus.PAUSED
        resumed = await mock_routes.resume_mock_interview(
            session_id=created.id,
            current_user=student,
            db=db,
        )
        assert resumed.status == MockInterviewStatus.IN_PROGRESS
        ans = await mock_routes.submit_mock_answer(
            session_id=created.id,
            req=MockInterviewAnswerSubmitRequest(
                question_id=resumed.questions[0].id,
                answer_text="Detailed explanation with time complexity O(n log n) and memory trade-offs.",
                input_mode="text",
                response_time_seconds=20,
                elapsed_seconds=32,
            ),
            current_user=student,
            db=db,
        )
        assert ans.submitted_answer.question_id == resumed.questions[0].id
        finished = await mock_routes.complete_mock_interview(
            session_id=created.id,
            req=MockInterviewTimerSyncRequest(elapsed_seconds=60),
            current_user=student,
            db=db,
        )
        assert finished.status == MockInterviewStatus.COMPLETED


@pytest.mark.asyncio
async def test_gemini_provider_handles_json_list_extraction():
    """Verify that if Gemini returns a JSON list instead of a dict, GeminiProvider gracefully maps it to the schema."""
    import json
    import httpx
    from app.services.ai_provider import GeminiAIProvider
    from app.schemas.mock_interview import GeneratedInterviewPlan

    # Mock response from Gemini containing a bare list of question objects
    raw_list_json = json.dumps([
        {
            "topic": "Data Structures",
            "question_text": "Explain the difference between a binary search tree and a heap.",
            "expected_key_points": ["BST order property", "Heap heap-order property", "Search complexity"],
            "model_answer": "A BST maintains left < root < right ordering...",
            "difficulty_hint": "intermediate",
        },
        {
            "topic": "Algorithms",
            "question_text": "How does Dijkstra's algorithm work with negative edge weights?",
            "expected_key_points": ["Cannot handle negative edges", "Bellman-Ford alternative"],
            "model_answer": "Dijkstra fails because greedy choice assumption breaks...",
            "difficulty_hint": "advanced",
        },
    ])

    fake_response = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": raw_list_json}]
                },
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 100,
            "candidatesTokenCount": 150,
            "totalTokenCount": 250,
        },
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = fake_response
    mock_client.post.return_value = mock_post_resp

    provider = GeminiAIProvider(api_key="fake-test-key", client=mock_client)
    plan, usage = await provider.generate_structured(
        schema=GeneratedInterviewPlan,
        system_instruction="Generate questions",
        user_prompt="Give me 2 questions",
    )

    assert isinstance(plan, GeneratedInterviewPlan)
    assert len(plan.questions) == 2
    assert plan.questions[0].topic == "Data Structures"
    assert plan.questions[1].topic == "Algorithms"


@pytest.mark.asyncio
async def test_mcq_aptitude_and_technical_tests_with_30_and_50_questions():
    student = build_student_user(user_id=1)
    resume = build_approved_resume(student_id=1)
    db = InMemoryMockInterviewDB(users=[student], resumes=[resume])

    # 1. Create Aptitude MCQ Test with 30 Questions (45 Minutes)
    apt_req = MockInterviewCreateRequest(
        category=MockInterviewCategory.APTITUDE,
        difficulty=MockInterviewDifficulty.INTERMEDIATE,
        question_format="mcq",
        question_count=30,
        time_limit_minutes=45,
        include_followups=False,
    )
    apt_session = await create_mock_interview_session(req=apt_req, current_user=student, db=db)
    assert apt_session.question_format == "mcq"
    assert apt_session.question_count == 30
    assert len(apt_session.questions) == 30
    assert apt_session.time_limit_minutes == 45
    for q in apt_session.questions:
        assert q.question_type == "mcq"
        assert q.options is not None and len(q.options) >= 2
        assert q.correct_option_key is None  # Spoiler protected

    # 2. Create Technical MCQ Test with 50 Questions (60 Minutes)
    tech_req = MockInterviewCreateRequest(
        category=MockInterviewCategory.TECHNICAL,
        difficulty=MockInterviewDifficulty.INTERMEDIATE,
        question_format="mcq",
        question_count=50,
        time_limit_minutes=60,
        include_followups=False,
    )
    tech_session = await create_mock_interview_session(req=tech_req, current_user=student, db=db)
    assert tech_session.question_format == "mcq"
    assert tech_session.question_count == 50
    assert len(tech_session.questions) == 50
    assert tech_session.time_limit_minutes == 60

    # 3. Test submitting, updating choice, and completing MCQ evaluation
    q1 = apt_session.questions[0]
    first_opt = q1.options[0]["key"]
    second_opt = q1.options[1]["key"]

    # Submit first option
    sub1 = await submit_mock_interview_answer(
        session_id=apt_session.id,
        question_id=q1.id,
        answer_text="",
        selected_option_key=first_opt,
        input_mode="text",
        response_time_seconds=20,
        elapsed_seconds=20,
        current_user=student,
        db=db,
    )
    assert sub1.submitted_answer.selected_option_key == first_opt
    assert sub1.followup_generated is False

    # Re-select / change option before finishing
    sub2 = await submit_mock_interview_answer(
        session_id=apt_session.id,
        question_id=q1.id,
        answer_text="",
        selected_option_key=second_opt,
        input_mode="text",
        response_time_seconds=10,
        elapsed_seconds=30,
        current_user=student,
        db=db,
    )
    assert sub2.submitted_answer.selected_option_key == second_opt

    # Complete session and check objective grading
    completed = await complete_mock_interview_session(
        session_id=apt_session.id,
        elapsed_seconds=600,
        current_user=student,
        db=db,
    )
    assert completed.status == MockInterviewStatus.COMPLETED
    assert completed.evaluation is not None
    assert completed.evaluation.overall_score >= 0.0
    assert "screening exam" in completed.evaluation.executive_summary.lower()
    # Spoiler protection lifted
    assert completed.questions[0].correct_option_key is not None
    assert completed.questions[0].model_answer is not None


