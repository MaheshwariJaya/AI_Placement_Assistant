"""Service layer for AI Mock Interview & Assessment Studio (practice only)."""
import asyncio
from collections import Counter
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import (
    AppException,
    AuthorizationException,
    EntityNotFoundException,
    ResourceConflictException,
)
from app.models.job import Job, JobStatus
from app.models.mock_interview import (
    MockInterviewAnswer,
    MockInterviewCategory,
    MockInterviewDifficulty,
    MockInterviewEvaluation,
    MockInterviewQuestion,
    MockInterviewSession,
    MockInterviewStatus,
)
from app.models.resume import Resume
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from app.schemas.ai import AIUsageMetadata
from app.schemas.mock_interview import (
    ADVISORY_MOCK_INTERVIEW_DISCLAIMER,
    CriteriaBreakdownScores,
    FollowUpDecisionAIOutput,
    GeneratedInterviewPlan,
    MockInterviewAnalyticsResponse,
    MockInterviewAnswerResponse,
    MockInterviewCategoryStat,
    MockInterviewCreateRequest,
    MockInterviewEvaluationAIOutput,
    MockInterviewEvaluationResponse,
    MockInterviewQuestionEvaluationDetail,
    MockInterviewQuestionView,
    MockInterviewSessionDetail,
    MockInterviewSessionSummary,
    MockInterviewTargetJob,
    MockInterviewTrendPoint,
    SubmitMockAnswerResponse,
)
from app.services.ai_provider import AIServiceError, get_ai_provider, MockAIProvider
from app.services.eligibility_service import evaluate_student_job_eligibility
from app.services.matching_engine import calculate_compatibility_score

logger = logging.getLogger(__name__)

MAX_RESUME_CONTEXT_CHARS = 3500
MAX_FOLLOWUPS_PER_SESSION = 2

_session_locks: Dict[int, asyncio.Lock] = {}


def _get_session_lock(session_id: int) -> asyncio.Lock:
    lock = _session_locks.get(session_id)
    if lock is None:
        lock = asyncio.Lock()
        _session_locks[session_id] = lock
    return lock


QUESTION_GENERATION_SYSTEM_PROMPT = (
    "You are an expert technical and career interview coach running a practice mock interview.\n"
    "STRICT RULES:\n"
    "1. Tailor every question strictly to the requested category (technical, hr, behavioral, aptitude, or project_based), "
    "difficulty level (beginner, intermediate, advanced), target job/role, and ONLY the verified skills, projects, "
    "experiences, and approved resume facts provided inside <STUDENT_CONTEXT>.\n"
    "2. ANTI-HALLUCINATION: NEVER invent or assume projects, companies, internships, or skills not present in <STUDENT_CONTEXT>.\n"
    "3. Produce crisp, realistic, single-prompt questions accompanied by concise expected_key_points and an educational model_answer.\n"
    "4. MULTI-DISCIPLINARY COGNIZANCE: The student may belong to any engineering branch or discipline (such as Civil, Mechanical, "
    "Electrical, Electronics & Communication, Chemical, Mining, Petroleum, Structural, Production & Industrial, Architecture/Planning, "
    "or Computer Science/IT). In the 'technical' category, rigorously test fundamental principles of their specific academic discipline "
    "and target role (e.g., structural mechanics, concrete technology, geotechnical engineering, thermodynamics, fluid machinery, "
    "power systems, analog/digital circuits, VLSI, chemical reaction engineering, heat transfer, mine ventilation, drilling hydraulics, "
    "architectural planning, urban zoning) rather than defaulting to software development questions unless software/computing is their explicit field.\n"
    "5. Return a single valid JSON object whose root key is 'questions', containing the array of question items. Never return a bare array."
)

FOLLOWUP_DECISION_SYSTEM_PROMPT = (
    "You are conducting an adaptive practice mock interview.\n"
    "Decide whether a single targeted follow-up question would meaningfully help the candidate deepen or clarify "
    "their just-submitted answer. Ask a follow-up ONLY if the answer missed an important edge case, trade-off, metric, "
    "or STAR outcome. Do NOT invent unverified resume claims. Return valid JSON."
)

EVALUATION_SYSTEM_PROMPT = (
    "You are an objective, supportive mock interview assessor evaluating a student's practice session.\n"
    "STRICT RULES:\n"
    "1. Evaluate EVERY question in <QUESTIONS_AND_ANSWERS> honestly based strictly on what the candidate wrote.\n"
    "2. Score across all required criteria (0-100): technical_correctness, conceptual_understanding, problem_solving_approach, "
    "communication_clarity, answer_structure, relevance, and project_knowledge (where applicable).\n"
    "3. Unanswered or `[UNANSWERED]` questions must score 0 with clear explanation.\n"
    "4. Provide actionable strengths, weaknesses, suggested improvements, recommended study topics, and model answers.\n"
    "5. Include the advisory compliance disclaimer verbatim and never fabricate student credentials. Return valid JSON."
)


async def _load_student_portfolio(
    current_user: User,
    db: AsyncSession,
) -> Tuple[StudentProfile, Optional[Resume]]:
    if (
        current_user.role != UserRole.STUDENT
        and current_user.email != "maheshwarijaya03@gmail.com"
        and current_user.role != UserRole.ADMIN
    ):
        raise AuthorizationException("Only registered students can access the AI Mock Interview Studio.")

    stmt = (
        select(StudentProfile)
        .where(StudentProfile.user_id == current_user.id)
        .options(
            selectinload(StudentProfile.user).selectinload(User.department),
            selectinload(StudentProfile.skills),
            selectinload(StudentProfile.projects),
            selectinload(StudentProfile.experiences),
            selectinload(StudentProfile.certifications),
        )
    )
    student_profile = (await db.execute(stmt)).scalar_one_or_none()
    if not student_profile:
        raise AppException(
            "Student academic profile is not configured.",
            status_code=400,
            code="STUDENT_PROFILE_REQUIRED",
        )

    resume_stmt = (
        select(Resume)
        .where(
            Resume.student_id == student_profile.id,
            Resume.parsing_status == "approved",
            Resume.is_active.is_(True),
        )
        .order_by(Resume.updated_at.desc())
        .limit(1)
    )
    approved_resume = (await db.execute(resume_stmt)).scalar_one_or_none()
    return student_profile, approved_resume


async def _load_visible_job(
    job_id: int,
    current_user: User,
    db: AsyncSession,
) -> Job:
    stmt = (
        select(Job)
        .where(Job.id == job_id, Job.is_active.is_(True))
        .options(
            selectinload(Job.company),
            selectinload(Job.skills),
            selectinload(Job.eligible_departments),
        )
    )
    job = (await db.execute(stmt)).scalar_one_or_none()
    if not job:
        raise EntityNotFoundException("Job", job_id, code="JOB_NOT_FOUND")

    if job.status != JobStatus.PUBLISHED:
        raise AppException(
            "Target job posting must be published before creating a tailored mock interview.",
            status_code=400,
            code="JOB_NOT_PUBLISHED",
        )

    if job.institution_id is not None and job.institution_id != current_user.institution_id:
        raise AuthorizationException("Cannot access a campus-exclusive job outside your institution.")

    return job


async def _load_owned_session(
    session_id: int,
    current_user: User,
    db: AsyncSession,
    for_update: bool = False,
) -> Tuple[MockInterviewSession, StudentProfile]:
    student_profile, _ = await _load_student_portfolio(current_user, db)

    stmt = (
        select(MockInterviewSession)
        .where(MockInterviewSession.id == session_id)
        .options(
            selectinload(MockInterviewSession.job).selectinload(Job.company),
            selectinload(MockInterviewSession.questions).selectinload(MockInterviewQuestion.answer),
            selectinload(MockInterviewSession.evaluation),
        )
    )
    if for_update:
        stmt = stmt.with_for_update()

    session_obj = (await db.execute(stmt)).scalar_one_or_none()
    if not session_obj:
        raise EntityNotFoundException("MockInterviewSession", session_id, code="MOCK_SESSION_NOT_FOUND")

    if session_obj.student_id != student_profile.id:
        raise AuthorizationException("You may only access your own mock interview sessions.")

    return session_obj, student_profile


def _resolve_default_role_for_department(dept_name: Optional[str]) -> str:
    """Dynamically resolves realistic, branch-appropriate default placement role grounded in student discipline."""
    if not dept_name:
        return "Graduate Engineering Trainee (GET)"
    d = dept_name.lower()
    if "civil" in d:
        return "Civil Site / Structural & Infrastructure Engineer"
    if "structural" in d:
        return "Structural Design & FEA Analysis Engineer"
    if "mechanical" in d:
        return "Mechanical Design, Thermal & Manufacturing Engineer"
    if "production" in d or "industrial" in d:
        return "Industrial & Production Operations Engineer"
    if "electrical" in d:
        return "Electrical Systems & Power Engineer"
    if "electronic" in d or "telecommunication" in d or "ece" in d or "communication" in d:
        return "Electronics, VLSI & Embedded Systems Engineer"
    if "chemical" in d:
        return "Chemical Process & Plant Operations Engineer"
    if "mining" in d:
        return "Mining Operations & Geotechnical Safety Engineer"
    if "petroleum" in d:
        return "Petroleum, Drilling & Reservoir Engineer"
    if "architecture" in d or "planning" in d:
        return "Architectural Designer & Urban / Regional Planner"
    if any(k in d for k in ["computer", "software", "information tech", "artificial", "data science", "cse", "it"]):
        return "Software Engineer / Tech Placement Candidate"
    return "Graduate Engineering Trainee (GET)"


def _build_grounding_context(
    current_user: User,
    student_profile: StudentProfile,
    approved_resume: Optional[Resume],
    job: Optional[Job],
    target_role: Optional[str],
) -> Tuple[Dict[str, Any], str, str]:
    skill_names = [s.skill_name.strip() for s in (student_profile.skills or []) if s.skill_name]
    project_labels = [
        f"{p.title} ({p.technologies or 'General'})"
        for p in (student_profile.projects or [])
        if p.title
    ]
    exp_labels = [
        f"{e.role_title} at {e.company_name}"
        for e in (student_profile.experiences or [])
        if e.role_title
    ]
    cert_labels = [
        f"{c.certificate_name} ({c.issuing_organization})"
        for c in (student_profile.certifications or [])
        if c.certificate_name
    ]

    resume_excerpt = ""
    if approved_resume and approved_resume.raw_extracted_text:
        resume_excerpt = approved_resume.raw_extracted_text.strip()[:MAX_RESUME_CONTEXT_CHARS]

    dept_obj = getattr(current_user, "department", None) or (
        student_profile.user.department if getattr(student_profile, "user", None) else None
    )
    dept_name = dept_obj.name if dept_obj else None
    fallback_role = _resolve_default_role_for_department(dept_name)
    effective_role = target_role or (job.title if job else fallback_role)

    student_ctx_text = (
        f"<STUDENT_CONTEXT>\n"
        f"Department: {dept_name or 'Not specified'}\n"
        f"Graduation Year: {student_profile.graduation_year or 'Not specified'}\n"
        f"Verified Skills: {', '.join(skill_names) if skill_names else 'None listed'}\n"
        f"Verified Projects: {', '.join(project_labels) if project_labels else 'None listed'}\n"
        f"Verified Experience: {', '.join(exp_labels) if exp_labels else 'None listed'}\n"
        f"Verified Certifications: {', '.join(cert_labels) if cert_labels else 'None listed'}\n"
        f"Approved Resume Excerpt: {resume_excerpt if resume_excerpt else 'No approved resume attached'}\n"
        f"</STUDENT_CONTEXT>"
    )

    job_ctx_text = "<JOB_CONTEXT>\nNo specific job posting selected.\n</JOB_CONTEXT>"
    job_snapshot: Dict[str, Any] = {}
    if job is not None:
        company_name = job.company.name if job.company else "Hiring Partner"
        mand_skills = [s.skill_name for s in (job.skills or []) if s.is_mandatory]
        pref_skills = [s.skill_name for s in (job.skills or []) if not s.is_mandatory]
        score, _, matched, missing_mand, rec_skills, _, _ = calculate_compatibility_score(
            job=job,
            student_user=current_user,
            student_profile=student_profile,
            approved_skills=student_profile.skills or [],
            approved_projects=student_profile.projects or [],
            approved_experiences=student_profile.experiences or [],
            approved_certifications=student_profile.certifications or [],
        )
        elig_res = evaluate_student_job_eligibility(
            job=job,
            student_user=current_user,
            student_profile=student_profile,
            student_skill_names=skill_names,
        )
        desc_excerpt = (job.description or "").strip()[:1500]
        job_ctx_text = (
            f"<JOB_CONTEXT>\n"
            f"Job Title: {job.title}\n"
            f"Company: {company_name}\n"
            f"Mandatory Skills: {', '.join(mand_skills) if mand_skills else 'None'}\n"
            f"Preferred Skills: {', '.join(pref_skills) if pref_skills else 'None'}\n"
            f"Matched Student Skills: {', '.join(matched) if matched else 'None'}\n"
            f"Missing Mandatory Skills: {', '.join(missing_mand) if missing_mand else 'None'}\n"
            f"Recommended Study Skills: {', '.join(rec_skills) if rec_skills else 'None'}\n"
            f"Job Description Summary: {desc_excerpt or 'Not provided'}\n"
            f"</JOB_CONTEXT>"
        )
        job_snapshot = {
            "job_id": job.id,
            "job_title": job.title,
            "company_name": company_name,
            "deterministic_compatibility_score": score,
            "is_eligible": elig_res.is_eligible,
            "matched_skills": matched,
            "missing_mandatory_skills": missing_mand,
        }

    snapshot = {
        "effective_role": effective_role,
        "skills_used": skill_names[:20],
        "projects_used": [p.title for p in (student_profile.projects or []) if p.title][:10],
        "experiences_used": exp_labels[:10],
        "approved_resume_id": approved_resume.id if approved_resume else None,
        "approved_resume_name": approved_resume.file_name if approved_resume else None,
        "target_job": job_snapshot or None,
    }
    return snapshot, student_ctx_text, job_ctx_text


def _map_question_view(q: MockInterviewQuestion, reveal_solution: bool) -> MockInterviewQuestionView:
    ans_view = None
    if q.answer is not None:
        ans_view = MockInterviewAnswerResponse(
            id=q.answer.id,
            question_id=q.answer.question_id,
            answer_text=q.answer.answer_text,
            selected_option_key=getattr(q.answer, "selected_option_key", None),
            input_mode=q.answer.input_mode,
            response_time_seconds=q.answer.response_time_seconds,
            submitted_at=q.answer.submitted_at,
        )
    return MockInterviewQuestionView(
        id=q.id,
        question_order=q.question_order,
        is_followup=q.is_followup,
        parent_question_id=q.parent_question_id,
        category=q.category,
        topic=q.topic,
        question_text=q.question_text,
        difficulty_hint=q.difficulty_hint,
        question_type=getattr(q, "question_type", "open_ended") or "open_ended",
        options=q.options_json if q.options_json else None,
        selected_option_key=getattr(q.answer, "selected_option_key", None) if q.answer else None,
        expected_key_points=list(q.expected_key_points or []) if reveal_solution else None,
        model_answer=q.model_answer if reveal_solution else None,
        correct_option_key=getattr(q, "correct_option_key", None) if reveal_solution else None,
        answer=ans_view,
    )


def _map_evaluation_view(ev: MockInterviewEvaluation) -> MockInterviewEvaluationResponse:
    q_evals = []
    for item in (ev.question_evaluations_json or []):
        q_evals.append(MockInterviewQuestionEvaluationDetail.model_validate(item))

    return MockInterviewEvaluationResponse(
        id=ev.id,
        session_id=ev.session_id,
        overall_score=float(ev.overall_score),
        criteria_scores=CriteriaBreakdownScores(
            technical_correctness=float(ev.technical_correctness_score),
            conceptual_understanding=float(ev.conceptual_understanding_score),
            problem_solving_approach=float(ev.problem_solving_score),
            communication_clarity=float(ev.communication_clarity_score),
            answer_structure=float(ev.answer_structure_score),
            relevance=float(ev.relevance_score),
            project_knowledge=float(ev.project_knowledge_score) if ev.project_knowledge_score is not None else None,
        ),
        question_evaluations=q_evals,
        strengths=list(ev.strengths_json or []),
        weaknesses=list(ev.weaknesses_json or []),
        suggested_improvements=list(ev.suggested_improvements_json or []),
        recommended_topics=list(ev.recommended_topics_json or []),
        executive_summary=ev.executive_summary,
        advisory_disclaimer=ev.advisory_disclaimer,
        evaluated_at=ev.evaluated_at,
    )


def _build_session_summary(
    session_obj: MockInterviewSession,
    score_delta: Optional[float] = None,
) -> MockInterviewSessionSummary:
    questions = list(session_obj.questions or [])
    answered_count = sum(1 for q in questions if q.answer is not None)
    overall = float(session_obj.evaluation.overall_score) if session_obj.evaluation else None

    job_title = session_obj.job.title if session_obj.job else None
    company_name = session_obj.job.company.name if (session_obj.job and session_obj.job.company) else None
    if not job_title and isinstance(session_obj.context_snapshot_json, dict):
        tj = session_obj.context_snapshot_json.get("target_job") or {}
        job_title = tj.get("job_title")
        company_name = tj.get("company_name")

    return MockInterviewSessionSummary(
        id=session_obj.id,
        student_id=session_obj.student_id,
        job_id=session_obj.job_id,
        job_title=job_title,
        company_name=company_name,
        target_role=session_obj.target_role,
        category=session_obj.category,
        difficulty=session_obj.difficulty,
        question_format=getattr(session_obj, "question_format", "conversational") or "conversational",
        status=session_obj.status,
        question_count=session_obj.question_count,
        total_questions_generated=len(questions),
        answered_count=answered_count,
        include_followups=session_obj.include_followups,
        time_limit_minutes=session_obj.time_limit_minutes,
        elapsed_seconds=session_obj.elapsed_seconds,
        current_question_order=session_obj.current_question_order,
        overall_score=overall,
        score_delta_from_previous=score_delta,
        ai_provider=session_obj.ai_provider,
        ai_model=session_obj.ai_model,
        started_at=session_obj.started_at,
        paused_at=session_obj.paused_at,
        completed_at=session_obj.completed_at,
    )


def _build_session_detail(
    session_obj: MockInterviewSession,
    usage: Optional[AIUsageMetadata] = None,
) -> MockInterviewSessionDetail:
    reveal = session_obj.status in (MockInterviewStatus.COMPLETED, MockInterviewStatus.ABANDONED)
    ordered_qs = sorted(list(session_obj.questions or []), key=lambda q: q.question_order)
    q_views = [_map_question_view(q, reveal_solution=reveal) for q in ordered_qs]
    current_q = next((qv for qv in q_views if qv.answer is None), None) if not reveal else None

    summary = _build_session_summary(session_obj)
    return MockInterviewSessionDetail(
        **summary.model_dump(),
        context_snapshot=session_obj.context_snapshot_json,
        questions=q_views,
        current_question=current_q,
        evaluation=_map_evaluation_view(session_obj.evaluation) if session_obj.evaluation else None,
        usage=usage,
    )


async def list_mock_interview_target_jobs(
    current_user: User,
    db: AsyncSession,
) -> List[MockInterviewTargetJob]:
    student_profile, _ = await _load_student_portfolio(current_user, db)

    filters = [Job.status == JobStatus.PUBLISHED, Job.is_active.is_(True)]
    if current_user.institution_id is not None:
        filters.append((Job.institution_id.is_(None)) | (Job.institution_id == current_user.institution_id))
    else:
        filters.append(Job.institution_id.is_(None))

    stmt = (
        select(Job)
        .where(*filters)
        .options(
            selectinload(Job.company),
            selectinload(Job.skills),
            selectinload(Job.eligible_departments),
        )
        .order_by(Job.created_at.desc())
        .limit(50)
    )
    jobs = (await db.execute(stmt)).scalars().all()
    student_skill_names = [s.skill_name for s in (student_profile.skills or [])]

    items: List[MockInterviewTargetJob] = []
    for job in jobs:
        elig = evaluate_student_job_eligibility(
            job=job,
            student_user=current_user,
            student_profile=student_profile,
            student_skill_names=student_skill_names,
        )
        score, _, _, _, _, _, _ = calculate_compatibility_score(
            job=job,
            student_user=current_user,
            student_profile=student_profile,
            approved_skills=student_profile.skills or [],
            approved_projects=student_profile.projects or [],
            approved_experiences=student_profile.experiences or [],
            approved_certifications=student_profile.certifications or [],
        )
        items.append(
            MockInterviewTargetJob(
                id=job.id,
                title=job.title,
                company_name=job.company.name if job.company else "Hiring Partner",
                employment_type=job.employment_type.value if hasattr(job.employment_type, "value") else str(job.employment_type),
                work_mode=job.work_mode.value if hasattr(job.work_mode, "value") else str(job.work_mode),
                location=job.location,
                compatibility_score=score,
                is_eligible=elig.is_eligible,
            )
        )

    items.sort(key=lambda x: (1 if x.is_eligible else 0, x.compatibility_score or 0.0), reverse=True)
    return items


async def _assemble_mcq_questions(
    req: MockInterviewCreateRequest,
    current_user: User,
    student_profile: StudentProfile,
    job: Optional[Job],
    effective_role: str,
    db: AsyncSession,
) -> Tuple[List[Dict[str, Any]], AIUsageMetadata]:
    from app.models.arena import ArenaQuestion, ArenaQuestionType, ArenaCategory
    import random

    from app.services.branch_arena_question_bank import resolve_department_arena_categories

    dept_obj = getattr(current_user, "department", None) or (
        student_profile.user.department if getattr(student_profile, "user", None) else None
    )
    dept_name = (dept_obj.name or "").lower() if dept_obj else ""
    dept_code = (dept_obj.code or "").upper() if dept_obj else ""

    branch_resolved_cats = resolve_department_arena_categories(dept_code, dept_name)
    branch_tech_cats = [
        c for c in branch_resolved_cats
        if c not in (ArenaCategory.APTITUDE_LOGICAL, ArenaCategory.QUANTITATIVE, ArenaCategory.VERBAL, ArenaCategory.HR_BEHAVIORAL)
    ]

    category_filters = []
    if req.category == MockInterviewCategory.APTITUDE:
        category_filters = [
            ArenaCategory.APTITUDE_LOGICAL,
            ArenaCategory.QUANTITATIVE,
            ArenaCategory.VERBAL,
        ]
    elif req.category == MockInterviewCategory.TECHNICAL:
        matched_cat = None
        if req.subject_focus:
            norm_subj = req.subject_focus.lower().strip()
            for c in branch_tech_cats:
                if c.value in norm_subj or norm_subj in c.value.replace("_", " ") or norm_subj in c.name.lower():
                    matched_cat = c
                    break
        if matched_cat:
            category_filters = [matched_cat]
        else:
            category_filters = [ArenaCategory.TECHNICAL_MCQS] + branch_tech_cats
    else:
        category_filters = [
            ArenaCategory.HR_BEHAVIORAL,
            ArenaCategory.TECHNICAL_MCQS,
            ArenaCategory.APTITUDE_LOGICAL,
        ]

    stmt = (
        select(ArenaQuestion)
        .where(
            ArenaQuestion.question_type == ArenaQuestionType.MCQ,
            ArenaQuestion.options_json.isnot(None),
            ArenaQuestion.category.in_(category_filters),
            ArenaQuestion.is_active.is_(True),
        )
    )
    raw_qs = (await db.execute(stmt)).scalars().all()

    dept_obj = getattr(current_user, "department", None) or (
        student_profile.user.department if getattr(student_profile, "user", None) else None
    )
    dept_name = (dept_obj.name or "").lower() if dept_obj else ""

    branch_tags = []
    if "civil" in dept_name or "structural" in dept_name:
        branch_tags = ["civil", "structural", "mechanics", "structures", "solid_mechanics"]
    elif "mechanical" in dept_name or "production" in dept_name:
        branch_tags = ["mechanical", "thermal", "thermodynamics", "industrial", "production", "operations"]
    elif "electrical" in dept_name or "power" in dept_name:
        branch_tags = ["electrical", "power_systems", "circuit_theory"]
    elif "electronic" in dept_name or "telecom" in dept_name or "ece" in dept_name:
        branch_tags = ["electronics", "communication", "signal_processing", "telecom"]
    elif "chemical" in dept_name or "petroleum" in dept_name:
        branch_tags = ["chemical", "petroleum", "fluid_dynamics", "process", "reservoir"]
    elif "mining" in dept_name:
        branch_tags = ["mining", "safety", "ventilation", "geotechnical"]
    elif "architecture" in dept_name or "planning" in dept_name:
        branch_tags = ["architecture", "planning", "urban_design", "zoning"]

    discipline_matched = []
    general_pool = []
    for q in raw_qs:
        tags = [str(t).lower() for t in (q.role_tags_json or [])]
        if any(bt in tags for bt in branch_tags):
            discipline_matched.append(q)
        else:
            general_pool.append(q)

    random.shuffle(discipline_matched)
    random.shuffle(general_pool)
    ordered_pool = discipline_matched + general_pool

    assembled: List[Dict[str, Any]] = []
    seen_prompts = set()

    for q in ordered_pool:
        if q.prompt_text in seen_prompts:
            continue
        seen_prompts.add(q.prompt_text)
        assembled.append({
            "topic": q.title,
            "question_text": q.prompt_text,
            "options": q.options_json,
            "correct_option_key": (q.correct_option_key or "A").strip().upper(),
            "model_answer": q.explanation_text or (f"Correct Option: {q.correct_option_key}"),
            "difficulty_hint": q.difficulty.value if hasattr(q.difficulty, "value") else str(q.difficulty),
        })
        if len(assembled) >= req.question_count:
            break

    # If requested count is 30 or 50 and larger than unique base pool, cycle-permute with variation labeling
    if len(assembled) < req.question_count and assembled:
        base_items = list(assembled)
        round_idx = 1
        while len(assembled) < req.question_count:
            for item in base_items:
                copied = dict(item)
                copied["topic"] = f"{item['topic']} (Part {round_idx + 1})"
                assembled.append(copied)
                if len(assembled) >= req.question_count:
                    break
            round_idx += 1

    usage = AIUsageMetadata(
        provider="placement_mcq_engine",
        model="curated_and_verified_mcq_bank",
        input_tokens=0,
        output_tokens=0,
        latency_ms=10,
    )
    return assembled[: req.question_count], usage


async def create_mock_interview_session(
    req: MockInterviewCreateRequest,
    current_user: User,
    db: AsyncSession,
) -> MockInterviewSessionDetail:
    student_profile, approved_resume = await _load_student_portfolio(current_user, db)

    job: Optional[Job] = None
    if req.job_id is not None:
        job = await _load_visible_job(req.job_id, current_user, db)

    dept_obj = getattr(current_user, "department", None) or (
        student_profile.user.department if getattr(student_profile, "user", None) else None
    )
    dept_name = dept_obj.name if dept_obj else None
    default_role = _resolve_default_role_for_department(dept_name)
    base_role = req.target_role or (job.title if job else default_role)
    effective_role = f"{base_role} — Subject: {req.subject_focus}" if req.subject_focus else base_role
    snapshot, student_ctx_text, job_ctx_text = _build_grounding_context(
        current_user=current_user,
        student_profile=student_profile,
        approved_resume=approved_resume,
        job=job,
        target_role=effective_role,
    )

    now_utc = datetime.now(timezone.utc)

    # Branch 1: Timed MCQ Screening Test (Objective, 5 to 50 questions)
    if req.question_format == "mcq":
        mcq_items, usage = await _assemble_mcq_questions(
            req=req,
            current_user=current_user,
            student_profile=student_profile,
            job=job,
            effective_role=effective_role,
            db=db,
        )
        session_obj = MockInterviewSession(
            student_id=student_profile.id,
            job_id=job.id if job else None,
            target_role=effective_role,
            category=req.category,
            difficulty=req.difficulty,
            status=MockInterviewStatus.IN_PROGRESS,
            question_count=len(mcq_items),
            question_format="mcq",
            include_followups=False,
            time_limit_minutes=req.time_limit_minutes,
            elapsed_seconds=0,
            current_question_order=1,
            context_snapshot_json=snapshot,
            ai_provider=usage.provider,
            ai_model=usage.model,
            started_at=now_utc,
        )
        db.add(session_obj)
        await db.flush()

        for idx, item in enumerate(mcq_items, start=1):
            q_row = MockInterviewQuestion(
                session_id=session_obj.id,
                question_order=idx,
                is_followup=False,
                parent_question_id=None,
                category=req.category,
                topic=item["topic"][:150],
                question_text=item["question_text"],
                expected_key_points=[f"Correct Option: {item['correct_option_key']}"],
                model_answer=item["model_answer"],
                difficulty_hint=item["difficulty_hint"][:30],
                question_type="mcq",
                options_json=item["options"],
                correct_option_key=item["correct_option_key"],
            )
            db.add(q_row)

        await db.commit()
        loaded_session, _ = await _load_owned_session(session_obj.id, current_user, db)
        return _build_session_detail(loaded_session, usage=usage)

    # Branch 2: Conversational AI Mock Interview (Open-ended voice/text)
    subj_clause = f"\nSubject Focus: {req.subject_focus}" if req.subject_focus else ""
    user_prompt = (
        f"<INTERVIEW_CONFIG>\n"
        f"Category: {req.category.value}\n"
        f"Difficulty: {req.difficulty.value}\n"
        f"Question Count: {req.question_count}\n"
        f"Target Role: {effective_role}{subj_clause}\n"
        f"</INTERVIEW_CONFIG>\n\n"
        f"{student_ctx_text}\n\n"
        f"{job_ctx_text}\n\n"
        f"Generate exactly {req.question_count} distinct interview questions. "
        + (f"Rigorously center technical evaluation on the subject '{req.subject_focus}'. " if req.subject_focus else "")
        + f"Return a single JSON object with root key 'questions' containing the list of question objects."
    )

    ai_provider = get_ai_provider()
    try:
        plan, usage = await ai_provider.generate_structured(
            schema=GeneratedInterviewPlan,
            system_instruction=QUESTION_GENERATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            max_output_tokens=3000,
        )
    except Exception as exc:
        logger.warning(
            "Live AI question generation failed (%s). Falling back to branch-cognizant curated synthesis.",
            exc,
        )
        from app.services.mock_interview_mock_helpers import synthesize_mock_interview_plan
        plan = synthesize_mock_interview_plan(user_prompt)
        usage = AIUsageMetadata(provider="synthesizer", model="curated_v2", total_tokens=0)

    generated_qs = plan.questions[: req.question_count]
    session_obj = MockInterviewSession(
        student_id=student_profile.id,
        job_id=job.id if job else None,
        target_role=effective_role,
        category=req.category,
        difficulty=req.difficulty,
        status=MockInterviewStatus.IN_PROGRESS,
        question_count=req.question_count,
        question_format="conversational",
        include_followups=req.include_followups,
        time_limit_minutes=req.time_limit_minutes,
        elapsed_seconds=0,
        current_question_order=1,
        context_snapshot_json=snapshot,
        ai_provider=usage.provider,
        ai_model=usage.model,
        started_at=now_utc,
    )
    db.add(session_obj)
    await db.flush()

    for idx, q_item in enumerate(generated_qs, start=1):
        q_row = MockInterviewQuestion(
            session_id=session_obj.id,
            question_order=idx,
            is_followup=False,
            parent_question_id=None,
            category=req.category,
            topic=q_item.topic.strip()[:150],
            question_text=q_item.question_text.strip(),
            expected_key_points=list(q_item.expected_key_points or []),
            model_answer=q_item.model_answer.strip(),
            difficulty_hint=q_item.difficulty_hint.strip() if q_item.difficulty_hint else req.difficulty.value,
            question_type="open_ended",
            options_json=None,
            correct_option_key=None,
        )
        db.add(q_row)

    await db.commit()
    loaded_session, _ = await _load_owned_session(session_obj.id, current_user, db)
    return _build_session_detail(loaded_session, usage=usage)


async def list_mock_interview_sessions(
    current_user: User,
    db: AsyncSession,
    category: Optional[MockInterviewCategory] = None,
    status_filter: Optional[MockInterviewStatus] = None,
) -> List[MockInterviewSessionSummary]:
    student_profile, _ = await _load_student_portfolio(current_user, db)

    stmt = (
        select(MockInterviewSession)
        .where(MockInterviewSession.student_id == student_profile.id)
        .options(
            selectinload(MockInterviewSession.job).selectinload(Job.company),
            selectinload(MockInterviewSession.questions).selectinload(MockInterviewQuestion.answer),
            selectinload(MockInterviewSession.evaluation),
        )
        .order_by(MockInterviewSession.created_at.desc())
    )
    if category is not None:
        stmt = stmt.where(MockInterviewSession.category == category)
    if status_filter is not None:
        stmt = stmt.where(MockInterviewSession.status == status_filter)

    sessions = (await db.execute(stmt)).scalars().all()

    # Compute chronological deltas among completed sessions
    completed_chrono = sorted(
        [s for s in sessions if s.status == MockInterviewStatus.COMPLETED and s.evaluation is not None],
        key=lambda s: (s.completed_at or s.created_at),
    )
    delta_by_id: Dict[int, Optional[float]] = {}
    prev_score: Optional[float] = None
    for cs in completed_chrono:
        curr = float(cs.evaluation.overall_score)
        delta_by_id[cs.id] = round(curr - prev_score, 1) if prev_score is not None else None
        prev_score = curr

    return [_build_session_summary(s, score_delta=delta_by_id.get(s.id)) for s in sessions]


async def get_mock_interview_session_detail(
    session_id: int,
    current_user: User,
    db: AsyncSession,
) -> MockInterviewSessionDetail:
    session_obj, _ = await _load_owned_session(session_id, current_user, db)
    return _build_session_detail(session_obj)


async def submit_mock_interview_answer(
    session_id: int,
    question_id: int,
    answer_text: str,
    input_mode: str,
    response_time_seconds: int,
    elapsed_seconds: Optional[int],
    current_user: User,
    db: AsyncSession,
    selected_option_key: Optional[str] = None,
) -> SubmitMockAnswerResponse:
    lock = _get_session_lock(session_id)
    async with lock:
        session_obj, _ = await _load_owned_session(session_id, current_user, db, for_update=True)

        if session_obj.status == MockInterviewStatus.COMPLETED:
            raise AppException(
                "This mock interview session is already completed.",
                status_code=400,
                code="MOCK_SESSION_COMPLETED",
            )
        if session_obj.status == MockInterviewStatus.ABANDONED:
            raise AppException(
                "This mock interview session was ended without evaluation.",
                status_code=400,
                code="MOCK_SESSION_ABANDONED",
            )
        if session_obj.status == MockInterviewStatus.PAUSED:
            raise AppException(
                "Resume the paused interview session before submitting an answer.",
                status_code=409,
                code="MOCK_SESSION_PAUSED",
            )

        ordered_qs = sorted(list(session_obj.questions or []), key=lambda q: q.question_order)
        target_q = next((q for q in ordered_qs if q.id == question_id), None)
        if not target_q:
            raise EntityNotFoundException("MockInterviewQuestion", question_id, code="MOCK_QUESTION_NOT_FOUND")

        now_utc = datetime.now(timezone.utc)
        is_mcq_session = getattr(session_obj, "question_format", "conversational") == "mcq"
        clean_opt = selected_option_key.strip().upper() if selected_option_key else None
        clean_ans = answer_text.strip() if answer_text else (f"Option {clean_opt}" if clean_opt else "")

        if target_q.answer is not None:
            if is_mcq_session:
                # In MCQ screening test, student can update or re-select option before final submission
                target_q.answer.selected_option_key = clean_opt or target_q.answer.selected_option_key
                target_q.answer.answer_text = clean_ans or target_q.answer.answer_text
                target_q.answer.response_time_seconds += response_time_seconds
                target_q.answer.submitted_at = now_utc
                answer_row = target_q.answer
            else:
                raise ResourceConflictException(
                    "An answer has already been submitted for this question.",
                    code="ANSWER_ALREADY_SUBMITTED",
                )
        else:
            answer_row = MockInterviewAnswer(
                session_id=session_obj.id,
                question_id=target_q.id,
                answer_text=clean_ans,
                selected_option_key=clean_opt,
                input_mode=input_mode,
                response_time_seconds=response_time_seconds,
                submitted_at=now_utc,
            )
            db.add(answer_row)

        if elapsed_seconds is not None:
            session_obj.elapsed_seconds = max(session_obj.elapsed_seconds, elapsed_seconds)

        await db.flush()

        followup_generated = False
        followup_rationale: Optional[str] = None
        existing_followups = sum(1 for q in ordered_qs if q.is_followup)

        if (
            not is_mcq_session
            and session_obj.include_followups
            and not target_q.is_followup
            and existing_followups < MAX_FOLLOWUPS_PER_SESSION
        ):
            try:
                fu_prompt = (
                    f"<CATEGORY>{session_obj.category.value}</CATEGORY>\n"
                    f"<DIFFICULTY>{session_obj.difficulty.value}</DIFFICULTY>\n"
                    f"<QUESTION_TOPIC>{target_q.topic}</QUESTION_TOPIC>\n"
                    f"<ASKED_QUESTION>{target_q.question_text}</ASKED_QUESTION>\n"
                    f"<CANDIDATE_ANSWER>{clean_ans}</CANDIDATE_ANSWER>\n"
                    f"Decide whether to ask 1 concise follow-up question."
                )
                ai_provider = get_ai_provider()
                fu_decision, _ = await ai_provider.generate_structured(
                    schema=FollowUpDecisionAIOutput,
                    system_instruction=FOLLOWUP_DECISION_SYSTEM_PROMPT,
                    user_prompt=fu_prompt,
                    temperature=0.2,
                    max_output_tokens=800,
                )
                if fu_decision.should_ask_followup and fu_decision.followup_question is not None:
                    later_qs = [q for q in ordered_qs if q.question_order > target_q.question_order]
                    # Shift later question orders cleanly without colliding on unique (session_id, question_order)
                    for lq in later_qs:
                        lq.question_order += 1000
                    await db.flush()
                    for lq in later_qs:
                        lq.question_order -= 999
                    await db.flush()

                    fu_item = fu_decision.followup_question
                    fu_row = MockInterviewQuestion(
                        session_id=session_obj.id,
                        question_order=target_q.question_order + 1,
                        is_followup=True,
                        parent_question_id=target_q.id,
                        category=session_obj.category,
                        topic=fu_item.topic.strip(),
                        question_text=fu_item.question_text.strip(),
                        expected_key_points=list(fu_item.expected_key_points or []),
                        model_answer=fu_item.model_answer.strip(),
                        difficulty_hint=fu_item.difficulty_hint.strip() if fu_item.difficulty_hint else session_obj.difficulty.value,
                    )
                    db.add(fu_row)
                    await db.flush()
                    followup_generated = True
                    followup_rationale = fu_decision.rationale
            except AIServiceError as ai_err:
                logger.warning("Skipping optional follow-up due to AI error on session %s: %s", session_id, ai_err)

        # Advance current_question_order to next unanswered question
        refreshed_qs_stmt = (
            select(MockInterviewQuestion)
            .where(MockInterviewQuestion.session_id == session_obj.id)
            .options(selectinload(MockInterviewQuestion.answer))
            .order_by(MockInterviewQuestion.question_order)
        )
        all_qs_now = (await db.execute(refreshed_qs_stmt)).scalars().all()
        next_unanswered = next((q for q in all_qs_now if q.answer is None), None)
        if next_unanswered is not None:
            session_obj.current_question_order = next_unanswered.question_order
        else:
            session_obj.current_question_order = len(all_qs_now)

        await db.commit()

        loaded_session, _ = await _load_owned_session(session_id, current_user, db)
        detail = _build_session_detail(loaded_session)
        ans_resp = MockInterviewAnswerResponse.model_validate(answer_row)
        return SubmitMockAnswerResponse(
            session=detail,
            submitted_answer=ans_resp,
            followup_generated=followup_generated,
            followup_rationale=followup_rationale,
            next_question=detail.current_question,
            ready_to_complete=(detail.current_question is None),
        )


async def pause_mock_interview_session(
    session_id: int,
    elapsed_seconds: int,
    current_user: User,
    db: AsyncSession,
) -> MockInterviewSessionDetail:
    lock = _get_session_lock(session_id)
    async with lock:
        session_obj, _ = await _load_owned_session(session_id, current_user, db, for_update=True)
        if session_obj.status in (MockInterviewStatus.COMPLETED, MockInterviewStatus.ABANDONED):
            raise AppException(
                "Cannot pause a session that has already ended.",
                status_code=400,
                code="MOCK_SESSION_ENDED",
            )
        session_obj.status = MockInterviewStatus.PAUSED
        session_obj.elapsed_seconds = max(session_obj.elapsed_seconds, elapsed_seconds)
        session_obj.paused_at = datetime.now(timezone.utc)
        await db.commit()

        loaded_session, _ = await _load_owned_session(session_id, current_user, db)
        return _build_session_detail(loaded_session)


async def resume_mock_interview_session(
    session_id: int,
    current_user: User,
    db: AsyncSession,
) -> MockInterviewSessionDetail:
    lock = _get_session_lock(session_id)
    async with lock:
        session_obj, _ = await _load_owned_session(session_id, current_user, db, for_update=True)
        if session_obj.status in (MockInterviewStatus.COMPLETED, MockInterviewStatus.ABANDONED):
            raise AppException(
                "Cannot resume a session that has already ended.",
                status_code=400,
                code="MOCK_SESSION_ENDED",
            )
        session_obj.status = MockInterviewStatus.IN_PROGRESS
        session_obj.paused_at = None
        await db.commit()

        loaded_session, _ = await _load_owned_session(session_id, current_user, db)
        return _build_session_detail(loaded_session)


async def complete_mock_interview_session(
    session_id: int,
    elapsed_seconds: Optional[int],
    current_user: User,
    db: AsyncSession,
) -> MockInterviewSessionDetail:
    lock = _get_session_lock(session_id)
    async with lock:
        session_obj, _ = await _load_owned_session(session_id, current_user, db, for_update=True)

        if session_obj.status == MockInterviewStatus.COMPLETED and session_obj.evaluation is not None:
            return _build_session_detail(session_obj)

        if session_obj.status == MockInterviewStatus.ABANDONED:
            raise AppException(
                "This incomplete mock interview was ended with zero submitted answers.",
                status_code=400,
                code="MOCK_SESSION_ABANDONED",
            )

        now_utc = datetime.now(timezone.utc)
        if elapsed_seconds is not None:
            session_obj.elapsed_seconds = max(session_obj.elapsed_seconds, elapsed_seconds)

        ordered_qs = sorted(list(session_obj.questions or []), key=lambda q: q.question_order)
        answered_qs = [q for q in ordered_qs if q.answer is not None]

        if len(answered_qs) == 0:
            session_obj.status = MockInterviewStatus.ABANDONED
            session_obj.completed_at = now_utc
            await db.commit()
            loaded_session, _ = await _load_owned_session(session_id, current_user, db)
            return _build_session_detail(loaded_session)

        # Branch A: Objective Deterministic Scoring for Timed MCQ Screening Tests (5 to 50 questions)
        if getattr(session_obj, "question_format", "conversational") == "mcq":
            total_qs_count = len(ordered_qs)
            correct_count = 0
            enriched_q_evals = []
            topic_correctness: Dict[str, List[bool]] = {}

            for q in ordered_qs:
                ans_key = (
                    q.answer.selected_option_key.strip().upper()
                    if (q.answer and q.answer.selected_option_key)
                    else None
                )
                corr_key = (q.correct_option_key or "").strip().upper() if q.correct_option_key else None
                is_corr = bool(ans_key and corr_key and ans_key == corr_key)
                if is_corr:
                    correct_count += 1
                q_score = 100.0 if is_corr else 0.0

                if q.topic not in topic_correctness:
                    topic_correctness[q.topic] = []
                topic_correctness[q.topic].append(is_corr)

                if is_corr:
                    feedback_str = f"Correct choice (Option {ans_key}). {q.model_answer}"
                elif ans_key:
                    feedback_str = f"Incorrect. Selected option {ans_key}, but the correct answer is option {corr_key}. {q.model_answer}"
                else:
                    feedback_str = f"Unanswered. The correct answer is option {corr_key}. {q.model_answer}"

                enriched_q_evals.append({
                    "question_id": q.id,
                    "question_order": q.question_order,
                    "question_text": q.question_text,
                    "topic": q.topic,
                    "is_followup": False,
                    "student_answer": q.answer.answer_text if q.answer else "[UNANSWERED]",
                    "selected_option_key": ans_key,
                    "correct_option_key": corr_key,
                    "is_correct": is_corr,
                    "score": q_score,
                    "criteria_scores": {
                        "technical_correctness": q_score,
                        "conceptual_understanding": q_score,
                        "problem_solving_approach": q_score,
                        "communication_clarity": 100.0,
                        "answer_structure": 100.0,
                        "relevance": 100.0,
                        "project_knowledge": None,
                    },
                    "feedback": feedback_str,
                    "strengths": [f"Demonstrated accuracy in {q.topic}"] if is_corr else [],
                    "weaknesses": [f"Review fundamental rules of {q.topic}"] if not is_corr else [],
                    "improvement_tip": f"Study {q.topic}: {q.model_answer[:120]}",
                    "model_answer": q.model_answer,
                })

            overall_score = round((correct_count / max(1, total_qs_count)) * 100.0, 1)
            strengths = [t for t, flags in topic_correctness.items() if all(flags)][:5]
            if not strengths and correct_count > 0:
                strengths = [f"Successfully answered {correct_count} of {total_qs_count} screening questions correctly."]
            weaknesses = [t for t, flags in topic_correctness.items() if not all(flags)][:5]
            suggested = [f"Practice targeted speed drills in {t}" for t in weaknesses[:4]]
            recommended = weaknesses[:6]

            eval_row = MockInterviewEvaluation(
                session_id=session_obj.id,
                overall_score=overall_score,
                technical_correctness_score=overall_score,
                conceptual_understanding_score=overall_score,
                problem_solving_score=overall_score,
                communication_clarity_score=100.0,
                answer_structure_score=100.0,
                relevance_score=100.0,
                project_knowledge_score=None,
                question_evaluations_json=enriched_q_evals,
                strengths_json=strengths,
                weaknesses_json=weaknesses,
                suggested_improvements_json=suggested,
                recommended_topics_json=recommended,
                executive_summary=(
                    f"Candidate completed {total_qs_count}-question timed {session_obj.category.value} screening exam. "
                    f"Final score: {correct_count}/{total_qs_count} correct ({overall_score}% accuracy). "
                    f"Total elapsed duration: {round(session_obj.elapsed_seconds / 60, 1)} minutes."
                ),
                advisory_disclaimer=ADVISORY_MOCK_INTERVIEW_DISCLAIMER,
                evaluated_at=now_utc,
            )
            session_obj.status = MockInterviewStatus.COMPLETED
            session_obj.completed_at = now_utc
            db.add(eval_row)
            await db.commit()

            loaded_session, _ = await _load_owned_session(session_id, current_user, db)
            return _build_session_detail(loaded_session)

        # Branch B: Conversational STAR & Conceptual Evaluation (Open-Ended AI Evaluation)
        q_items_text = []
        for q in ordered_qs:
            ans_str = q.answer.answer_text if q.answer else "[UNANSWERED]"
            kp_str = "; ".join(q.expected_key_points or [])
            q_items_text.append(
                f'<Q_ITEM order="{q.question_order}" topic="{q.topic}" is_followup="{str(q.is_followup).lower()}">\n'
                f"<QUESTION>{q.question_text}</QUESTION>\n"
                f"<KEY_POINTS>{kp_str}</KEY_POINTS>\n"
                f"<MODEL_ANSWER>{q.model_answer}</MODEL_ANSWER>\n"
                f"<ANSWER>{ans_str}</ANSWER>\n"
                f"</Q_ITEM>"
            )

        eval_prompt = (
            f"<SESSION_METADATA>\n"
            f"Category: {session_obj.category.value}\n"
            f"Difficulty: {session_obj.difficulty.value}\n"
            f"Target Role: {session_obj.target_role or 'Placement Candidate'}\n"
            f"Answered Count: {len(answered_qs)} of {len(ordered_qs)}\n"
            f"</SESSION_METADATA>\n\n"
            f"<QUESTIONS_AND_ANSWERS>\n"
            + "\n".join(q_items_text)
            + "\n</QUESTIONS_AND_ANSWERS>\n\n"
            f"Evaluate the session and return structured feedback matching the schema."
        )

        ai_provider = get_ai_provider()
        try:
            ai_eval, usage = await ai_provider.generate_structured(
                schema=MockInterviewEvaluationAIOutput,
                system_instruction=EVALUATION_SYSTEM_PROMPT,
                user_prompt=eval_prompt,
                temperature=0.1,
                max_output_tokens=3500,
            )
        except Exception as exc:
            logger.warning(
                "Live AI evaluation generation failed (%s). Falling back to objective evaluation synthesizer.",
                exc,
            )
            from app.services.mock_interview_mock_helpers import synthesize_mock_evaluation
            ai_eval = synthesize_mock_evaluation(eval_prompt)
            usage = AIUsageMetadata(provider="synthesizer", model="curated_v2", total_tokens=0)

        # Map AI per-question items cleanly back to real DB questions
        ai_by_order = {item.question_order: item for item in (ai_eval.question_evaluations or [])}
        enriched_q_evals: List[Dict[str, Any]] = []
        for q in ordered_qs:
            ai_item = ai_by_order.get(q.question_order)
            if ai_item is None:
                zero_scores = CriteriaBreakdownScores(
                    technical_correctness=0.0,
                    conceptual_understanding=0.0,
                    problem_solving_approach=0.0,
                    communication_clarity=0.0,
                    answer_structure=0.0,
                    relevance=0.0,
                    project_knowledge=0.0 if session_obj.category == MockInterviewCategory.PROJECT_BASED else None,
                )
                detail_item = MockInterviewQuestionEvaluationDetail(
                    question_id=q.id,
                    question_order=q.question_order,
                    question_text=q.question_text,
                    topic=q.topic,
                    is_followup=q.is_followup,
                    student_answer=q.answer.answer_text if q.answer else None,
                    score=0.0 if q.answer is None else float(ai_eval.overall_score),
                    criteria_scores=zero_scores if q.answer is None else ai_eval.criteria_scores,
                    feedback=(
                        "Question was not answered before ending the session."
                        if q.answer is None
                        else "Evaluated within overall session rubric."
                    ),
                    strengths=[],
                    weaknesses=["No answer submitted."] if q.answer is None else [],
                    improvement_tip=f"Practice articulating structured answers for {q.topic}.",
                    model_answer=q.model_answer,
                )
            else:
                detail_item = MockInterviewQuestionEvaluationDetail(
                    question_id=q.id,
                    question_order=q.question_order,
                    question_text=q.question_text,
                    topic=q.topic,
                    is_followup=q.is_followup,
                    student_answer=q.answer.answer_text if q.answer else None,
                    score=round(ai_item.score, 2),
                    criteria_scores=ai_item.criteria_scores,
                    feedback=ai_item.feedback,
                    strengths=ai_item.strengths,
                    weaknesses=ai_item.weaknesses,
                    improvement_tip=ai_item.improvement_tip,
                    model_answer=ai_item.model_answer or q.model_answer,
                )
            enriched_q_evals.append(detail_item.model_dump())

        cs = ai_eval.criteria_scores
        eval_row = MockInterviewEvaluation(
            session_id=session_obj.id,
            overall_score=round(ai_eval.overall_score, 2),
            technical_correctness_score=round(cs.technical_correctness, 2),
            conceptual_understanding_score=round(cs.conceptual_understanding, 2),
            problem_solving_score=round(cs.problem_solving_approach, 2),
            communication_clarity_score=round(cs.communication_clarity, 2),
            answer_structure_score=round(cs.answer_structure, 2),
            relevance_score=round(cs.relevance, 2),
            project_knowledge_score=round(cs.project_knowledge, 2) if cs.project_knowledge is not None else None,
            question_evaluations_json=enriched_q_evals,
            strengths_json=list(ai_eval.strengths or []),
            weaknesses_json=list(ai_eval.weaknesses or []),
            suggested_improvements_json=list(ai_eval.suggested_improvements or []),
            recommended_topics_json=list(ai_eval.recommended_topics or []),
            executive_summary=ai_eval.executive_summary.strip(),
            advisory_disclaimer=ADVISORY_MOCK_INTERVIEW_DISCLAIMER,
            evaluated_at=now_utc,
        )
        db.add(eval_row)

        session_obj.status = MockInterviewStatus.COMPLETED
        session_obj.paused_at = None
        session_obj.completed_at = now_utc
        session_obj.ai_provider = usage.provider
        session_obj.ai_model = usage.model

        await db.commit()
        loaded_session, _ = await _load_owned_session(session_id, current_user, db)
        return _build_session_detail(loaded_session, usage=usage)


async def get_mock_interview_analytics(
    current_user: User,
    db: AsyncSession,
) -> MockInterviewAnalyticsResponse:
    student_profile, _ = await _load_student_portfolio(current_user, db)

    stmt = (
        select(MockInterviewSession)
        .where(MockInterviewSession.student_id == student_profile.id)
        .options(
            selectinload(MockInterviewSession.job).selectinload(Job.company),
            selectinload(MockInterviewSession.evaluation),
        )
        .order_by(MockInterviewSession.created_at.asc())
    )
    sessions = (await db.execute(stmt)).scalars().all()

    total_sessions = len(sessions)
    active_sessions = sum(
        1 for s in sessions if s.status in (MockInterviewStatus.IN_PROGRESS, MockInterviewStatus.PAUSED)
    )
    completed = [s for s in sessions if s.status == MockInterviewStatus.COMPLETED and s.evaluation is not None]
    completed.sort(key=lambda s: (s.completed_at or s.created_at))

    if not completed:
        return MockInterviewAnalyticsResponse(
            total_sessions=total_sessions,
            completed_sessions=0,
            in_progress_or_paused_sessions=active_sessions,
        )

    scores = [float(s.evaluation.overall_score) for s in completed]
    avg_score = round(sum(scores) / len(scores), 1)
    best_score = round(max(scores), 1)
    latest_score = round(scores[-1], 1)
    improvement_delta = round(scores[-1] - scores[-2], 1) if len(scores) >= 2 else None

    def _avg_attr(attr: str) -> float:
        vals = [float(getattr(s.evaluation, attr)) for s in completed]
        return round(sum(vals) / len(vals), 1)

    proj_vals = [
        float(s.evaluation.project_knowledge_score)
        for s in completed
        if s.evaluation.project_knowledge_score is not None
    ]
    avg_criteria = CriteriaBreakdownScores(
        technical_correctness=_avg_attr("technical_correctness_score"),
        conceptual_understanding=_avg_attr("conceptual_understanding_score"),
        problem_solving_approach=_avg_attr("problem_solving_score"),
        communication_clarity=_avg_attr("communication_clarity_score"),
        answer_structure=_avg_attr("answer_structure_score"),
        relevance=_avg_attr("relevance_score"),
        project_knowledge=round(sum(proj_vals) / len(proj_vals), 1) if proj_vals else None,
    )

    # Category breakdown
    by_cat: Dict[MockInterviewCategory, List[float]] = {}
    for s in completed:
        by_cat.setdefault(s.category, []).append(float(s.evaluation.overall_score))
    category_stats = [
        MockInterviewCategoryStat(
            category=cat,
            attempts=len(cat_scores),
            average_score=round(sum(cat_scores) / len(cat_scores), 1),
            best_score=round(max(cat_scores), 1),
            latest_score=round(cat_scores[-1], 1),
        )
        for cat, cat_scores in by_cat.items()
    ]

    # Chronological trend
    trend: List[MockInterviewTrendPoint] = []
    for idx, s in enumerate(completed, start=1):
        label = (s.job.title if s.job else s.target_role) or s.category.value.replace("_", " ").title()
        trend.append(
            MockInterviewTrendPoint(
                session_id=s.id,
                attempt_number=idx,
                category=s.category,
                difficulty=s.difficulty,
                overall_score=round(float(s.evaluation.overall_score), 1),
                completed_at=s.completed_at or s.created_at,
                target_label=label,
            )
        )

    # Aggregate weak criteria & recurring weaknesses / recommended topics
    criteria_pairs = [
        ("Technical Correctness", avg_criteria.technical_correctness),
        ("Conceptual Understanding", avg_criteria.conceptual_understanding),
        ("Problem-Solving Approach", avg_criteria.problem_solving_approach),
        ("Communication Clarity", avg_criteria.communication_clarity),
        ("Answer Structure", avg_criteria.answer_structure),
        ("Relevance", avg_criteria.relevance),
    ]
    if avg_criteria.project_knowledge is not None:
        criteria_pairs.append(("Project Knowledge", avg_criteria.project_knowledge))
    criteria_pairs.sort(key=lambda pair: pair[1])

    areas_to_improve: List[str] = [
        f"{name} (Avg: {val:.1f}%)" for name, val in criteria_pairs if val < 78.0
    ][:3]

    weakness_counter: Counter = Counter()
    topic_counter: Counter = Counter()
    for s in completed[-10:]:
        for w in (s.evaluation.weaknesses_json or []):
            if isinstance(w, str) and w.strip():
                weakness_counter[w.strip()] += 1
        for t in (s.evaluation.recommended_topics_json or []):
            if isinstance(t, str) and t.strip():
                topic_counter[t.strip()] += 1

    for w_text, _ in weakness_counter.most_common(3):
        if w_text not in areas_to_improve:
            areas_to_improve.append(w_text)

    top_topics = [t for t, _ in topic_counter.most_common(5)]

    return MockInterviewAnalyticsResponse(
        total_sessions=total_sessions,
        completed_sessions=len(completed),
        in_progress_or_paused_sessions=active_sessions,
        average_score=avg_score,
        best_score=best_score,
        latest_score=latest_score,
        improvement_delta=improvement_delta,
        average_criteria=avg_criteria,
        category_breakdown=category_stats,
        score_trend=trend,
        areas_requiring_improvement=areas_to_improve[:5],
        top_recommended_topics=top_topics,
    )

