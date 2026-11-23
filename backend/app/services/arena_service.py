"""Service layer for Placement Preparation Arena."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import (
    AppException,
    AuthorizationException,
    EntityNotFoundException,
)

ValidationException = AppException
from app.models.arena import (
    ArenaAssessment,
    ArenaAssessmentMode,
    ArenaAttempt,
    ArenaAttemptAnswer,
    ArenaAttemptStatus,
    ArenaCategory,
    ArenaContentSource,
    ArenaDifficulty,
    ArenaQuestion,
    ArenaQuestionType,
    ArenaUserPreference,
)
from app.models.job import Job, JobStatus
from app.models.organization import Department
from app.models.readiness import ReadinessSnapshot
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from app.services.academic_context_service import get_student_career_interests
from app.schemas.arena import (
    ArenaAssessmentSummary,
    ArenaAttemptAnswerView,
    ArenaAttemptDetail,
    ArenaAttemptSummary,
    ArenaCategorySummary,
    ArenaLeaderboardEntry,
    ArenaLeaderboardResponse,
    ArenaOptionItem,
    ArenaPerformanceAnalytics,
    ArenaPersonalizedPracticeResponse,
    ArenaQuestionPublicView,
    ArenaQuestionReviewView,
    ArenaQuestionSlot,
    ArenaRecommendedExercise,
    ArenaRunCodeRequest,
    ArenaSampleTestCase,
    ArenaStartAttemptRequest,
    ArenaSubmitAnswerRequest,
    ArenaSubmitAnswerResponse,
    ArenaSubmitAttemptRequest,
    ArenaTopicProficiencyItem,
    ArenaTpoAnalyticsResponse,
    ArenaTpoAssessmentAnalyticsItem,
    ArenaTpoAssessmentCreateRequest,
    ArenaTpoQuestionCreateRequest,
    ArenaStudentPerformanceItem,
    ArenaTpoStudentRosterResponse,
    ArenaTrendPoint,
    ArenaUserPreferenceResponse,
    ArenaUserPreferenceUpdate,
    SandboxRunResponse,
)
from app.services.ai_provider import AIServiceError, get_ai_provider
from app.services.arena_question_bank import (
    CATEGORY_METADATA,
    COMPANY_PROVENANCE_NOTICE,
    CURATED_PROVENANCE_NOTICE,
    STAFF_PROVENANCE_NOTICE,
    ensure_arena_seed_data,
)
from app.services.branch_arena_question_bank import (
    resolve_department_arena_categories,
    COMMON_ARENA_CATEGORIES,
    CS_ARENA_CATEGORIES,
)
from app.services.code_sandbox_service import code_sandbox_service
from app.services.matching_engine import normalize_skill

logger = logging.getLogger(__name__)

PRIVACY_GUARANTEE_TEXT = (
    "Privacy-preserving leaderboard: participation is strictly opt-in, display names can be anonymized, "
    "and sensitive academic data (CGPA, backlogs, roll number, email) is never exposed."
)


class _BehavioralAIReview(BaseModel):
    score_out_of_100: int
    strengths: List[str]
    improvements: List[str]
    summary: str


class _PersonalizedTipAI(BaseModel):
    study_tip: str


def _proficiency_band(attempted: int, accuracy: float) -> str:
    if attempted == 0:
        return "Not Started"
    if accuracy >= 80.0:
        return "Strong"
    if accuracy >= 55.0:
        return "Developing"
    return "Needs Focus"


def _question_provenance(q: ArenaQuestion) -> str:
    if q.content_source == ArenaContentSource.INSTITUTIONAL_STAFF:
        return STAFF_PROVENANCE_NOTICE
    if q.company_tag:
        return COMPANY_PROVENANCE_NOTICE
    return CURATED_PROVENANCE_NOTICE


def _to_public_question(q: ArenaQuestion) -> ArenaQuestionPublicView:
    opts = [
        ArenaOptionItem(key=str(o.get("key", "")), text=str(o.get("text", "")))
        for o in (q.options_json or [])
    ]
    sample_cases = [
        ArenaSampleTestCase(
            stdin=str(tc.get("stdin", "")),
            expected_stdout=str(tc.get("expected_stdout", "")),
        )
        for tc in (q.test_cases_json or [])
        if tc.get("is_sample")
    ]
    return ArenaQuestionPublicView(
        id=q.id,
        title=q.title,
        prompt_text=q.prompt_text,
        category=q.category,
        difficulty=q.difficulty,
        question_type=q.question_type,
        content_source=q.content_source,
        company_tag=q.company_tag,
        provenance_notice=_question_provenance(q),
        role_tags=[str(t) for t in (q.role_tags_json or [])],
        options=opts,
        starter_code={str(k): str(v) for k, v in (q.starter_code_json or {}).items()},
        sample_test_cases=sample_cases,
        expected_time_seconds=q.expected_time_seconds,
        max_marks=q.max_marks,
        institution_id=q.institution_id,
    )


def _to_review_question(q: ArenaQuestion) -> ArenaQuestionReviewView:
    pub = _to_public_question(q)
    return ArenaQuestionReviewView(
        **pub.model_dump(),
        correct_option_key=q.correct_option_key,
        explanation_text=q.explanation_text,
        sample_solution_text=q.sample_solution_text,
    )


def _to_attempt_summary(a: ArenaAttempt) -> ArenaAttemptSummary:
    return ArenaAttemptSummary(
        id=a.id,
        assessment_id=a.assessment_id,
        title=a.title,
        mode=a.mode,
        category=a.category,
        difficulty=a.difficulty,
        company_name_style=a.company_name_style,
        status=a.status,
        time_limit_seconds=a.time_limit_seconds,
        started_at=a.started_at,
        expires_at=a.expires_at,
        submitted_at=a.submitted_at,
        elapsed_seconds=int(a.elapsed_seconds or 0),
        total_questions=int(a.total_questions or 0),
        attempted_count=int(a.attempted_count or 0),
        correct_count=int(a.correct_count or 0),
        accuracy_pct=round(float(a.accuracy_pct or 0.0), 2),
        score_pct=round(float(a.score_pct or 0.0), 2),
    )


def _to_answer_view(ans: ArenaAttemptAnswer) -> ArenaAttemptAnswerView:
    exec_obj = None
    if ans.execution_result_json:
        try:
            exec_obj = SandboxRunResponse.model_validate(ans.execution_result_json)
        except Exception:
            exec_obj = None
    return ArenaAttemptAnswerView(
        id=ans.id,
        question_id=ans.question_id,
        question_order=ans.question_order,
        selected_option_key=ans.selected_option_key,
        submitted_code=ans.submitted_code,
        code_language=ans.code_language,
        behavioral_response=ans.behavioral_response,
        is_correct=bool(ans.is_correct),
        score_awarded=round(float(ans.score_awarded or 0.0), 2),
        time_spent_seconds=int(ans.time_spent_seconds or 0),
        execution_result=exec_obj,
        ai_feedback=ans.ai_feedback_json,
        answered_at=ans.answered_at,
    )


async def _require_student_profile(current_user: User, db: AsyncSession) -> StudentProfile:
    # Allow students, or multi-platform admin users (such as Jaya Maheshwari) who hold a StudentProfile
    if current_user.role != UserRole.STUDENT and current_user.email != "maheshwarijaya03@gmail.com" and current_user.role != UserRole.ADMIN:
        raise AuthorizationException("Only registered students can access student Placement Preparation Arena features.")
    stmt = (
        select(StudentProfile)
        .where(StudentProfile.user_id == current_user.id)
        .options(
            selectinload(StudentProfile.user).selectinload(User.department),
            selectinload(StudentProfile.skills),
        )
    )
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if not profile:
        raise AppException(
            "Student profile must be completed before accessing Placement Preparation Arena.",
            code="STUDENT_PROFILE_REQUIRED",
            status_code=400,
        )
    return profile


def _recalculate_attempt_metrics(attempt: ArenaAttempt, q_map: Dict[int, ArenaQuestion]) -> None:
    answers = attempt.answers or []
    total_q = max(len(attempt.question_ids_json or []), 1)
    max_possible_marks = sum(
        (q_map[qid].max_marks if qid in q_map else 10) for qid in (attempt.question_ids_json or [])
    )
    max_possible_marks = max(max_possible_marks, 1)

    attempted = len(answers)
    correct = sum(1 for a in answers if a.is_correct)
    earned = sum(float(a.score_awarded or 0.0) for a in answers)

    attempt.total_questions = len(attempt.question_ids_json or [])
    attempt.attempted_count = attempted
    attempt.correct_count = correct
    attempt.accuracy_pct = round((correct / attempted) * 100.0, 2) if attempted > 0 else 0.0
    attempt.score_pct = round(min(100.0, (earned / max_possible_marks) * 100.0), 2)


async def _sync_attempt_expiry(attempt: ArenaAttempt, db: AsyncSession) -> bool:
    """Marks timed attempt expired if past expires_at. Returns True if expired."""
    if attempt.status == ArenaAttemptStatus.EXPIRED:
        return True
    if attempt.status == ArenaAttemptStatus.SUBMITTED:
        return False
    if attempt.expires_at is not None:
        now = datetime.now(timezone.utc)
        exp = attempt.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now > exp:
            attempt.status = ArenaAttemptStatus.EXPIRED
            attempt.submitted_at = exp
            if attempt.started_at:
                started = attempt.started_at if attempt.started_at.tzinfo else attempt.started_at.replace(tzinfo=timezone.utc)
                attempt.elapsed_seconds = max(0, int((exp - started).total_seconds()))
            await db.commit()
            return True
    return False


def _evaluate_behavioral_answer(question: ArenaQuestion, response_text: str) -> Tuple[bool, float, Dict[str, Any]]:
    words = [w for w in response_text.strip().split() if w]
    word_count = len(words)
    lower = response_text.lower()
    star_hits = sum(
        1
        for cue_group in (
            ("situation", "context", "project", "team", "when"),
            ("task", "goal", "responsibility", "deadline", "problem"),
            ("action", "built", "fixed", "designed", "implemented", "communicated", "resolved"),
            ("result", "impact", "improved", "reduced", "delivered", "percent", "%"),
        )
        if any(c in lower for c in cue_group)
    )
    score_100 = min(100, int(30 + min(word_count, 80) * 0.5 + star_hits * 10))
    passed = score_100 >= 60 and word_count >= 15
    marks = round((score_100 / 100.0) * question.max_marks, 2)
    feedback = {
        "score_out_of_100": score_100,
        "star_components_detected": star_hits,
        "word_count": word_count,
        "strengths": [
            f"Covered {star_hits}/4 STAR narrative dimensions cleanly."
            if star_hits >= 2
            else "Included concrete response structure."
        ],
        "improvements": (
            []
            if star_hits >= 4 and word_count >= 35
            else ["Add explicit measurable results/metrics and clarify your individual engineering actions."]
        ),
        "summary": (
            "Strong structured STAR response suitable for HR and behavioral panels."
            if passed
            else "Expand your answer with clear Situation, Task, Action, and quantified Result details."
        ),
    }
    return passed, marks, feedback


# =============================================================================
# 1. Categories, Questions, Assessments
# =============================================================================


async def get_arena_categories(current_user: User, db: AsyncSession) -> List[ArenaCategorySummary]:
    await ensure_arena_seed_data(db)
    profile = await _require_student_profile(current_user, db)

    q_stmt = select(ArenaQuestion).where(
        ArenaQuestion.is_active.is_(True),
        or_(ArenaQuestion.institution_id.is_(None), ArenaQuestion.institution_id == current_user.institution_id),
    )
    questions = list((await db.execute(q_stmt)).scalars().all())

    ans_stmt = (
        select(ArenaAttemptAnswer)
        .where(ArenaAttemptAnswer.student_id == profile.id)
        .options(selectinload(ArenaAttemptAnswer.question))
    )
    answers = list((await db.execute(ans_stmt)).scalars().all())

    q_by_cat: Dict[ArenaCategory, List[ArenaQuestion]] = defaultdict(list)
    for q in questions:
        q_by_cat[q.category].append(q)

    ans_by_cat: Dict[ArenaCategory, List[ArenaAttemptAnswer]] = defaultdict(list)
    for ans in answers:
        if ans.question:
            ans_by_cat[ans.question.category].append(ans)

    dept_obj = getattr(current_user, "department", None)
    dept_name = dept_obj.name.strip() if dept_obj and dept_obj.name else None
    dept_code = (dept_obj.code or "").upper().strip() if dept_obj and dept_obj.code else ""
    is_cs = dept_code in ("CSE", "IT", "AIML", "AIDS") or (
        any(k in (dept_name or "").lower() for k in ("computer", "information technology", "software", "data science"))
    )

    # Strictly filter active categories: ONLY Placement Common (Aptitude & Reasoning) + Official Branch Core
    # CS categories are strictly excluded for all other engineering branches!
    active_categories = resolve_department_arena_categories(dept_code, dept_name or "")

    summaries: List[ArenaCategorySummary] = []
    for cat in active_categories:
        meta = CATEGORY_METADATA.get(cat, {
            "label": cat.value.replace("_", " ").title(),
            "description": f"Core technical placement preparation module for {cat.value}."
        })
        cat_qs = q_by_cat[cat]
        cat_ans = ans_by_cat[cat]
        attempted_qids = {a.question_id for a in cat_ans}
        correct_ans = sum(1 for a in cat_ans if a.is_correct)
        acc = round((correct_ans / len(cat_ans)) * 100.0, 1) if cat_ans else 0.0
        avg_t = round(sum(int(a.time_spent_seconds or 0) for a in cat_ans) / len(cat_ans), 1) if cat_ans else 0.0

        if cat in (ArenaCategory.QUANTITATIVE, ArenaCategory.APTITUDE_LOGICAL, ArenaCategory.VERBAL, ArenaCategory.HR_BEHAVIORAL):
            track_type = "common"
            is_rec = True
            label = meta["label"]
            desc = meta["description"]
        else:
            # Official Branch Core Subject
            track_type = "branch_core"
            is_rec = True
            label = meta["label"]
            desc = meta["description"]

        summaries.append(
            ArenaCategorySummary(
                category=cat,
                label=label,
                description=desc,
                total_questions=len(cat_qs),
                mcq_count=sum(1 for q in cat_qs if q.question_type == ArenaQuestionType.MCQ),
                coding_count=sum(1 for q in cat_qs if q.question_type == ArenaQuestionType.CODING),
                behavioral_count=sum(1 for q in cat_qs if q.question_type == ArenaQuestionType.BEHAVIORAL),
                easy_count=sum(1 for q in cat_qs if q.difficulty == ArenaDifficulty.EASY),
                medium_count=sum(1 for q in cat_qs if q.difficulty == ArenaDifficulty.MEDIUM),
                hard_count=sum(1 for q in cat_qs if q.difficulty == ArenaDifficulty.HARD),
                attempted_questions=len(attempted_qids),
                accuracy_pct=acc,
                avg_solving_seconds=avg_t,
                proficiency_label=_proficiency_band(len(cat_ans), acc),
                track_type=track_type,
                branch_name=dept_name,
                is_recommended_for_student=is_rec,
            )
        )

    # Sort: branch_core first, then common aptitude & reasoning
    sort_rank = {"branch_core": 0, "common": 1}
    summaries.sort(key=lambda s: (sort_rank.get(s.track_type, 9), s.label))
    return summaries


async def list_arena_questions(
    current_user: User,
    db: AsyncSession,
    category: Optional[ArenaCategory] = None,
    difficulty: Optional[ArenaDifficulty] = None,
    question_type: Optional[ArenaQuestionType] = None,
    company_tag: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[ArenaQuestionPublicView]:
    await ensure_arena_seed_data(db)
    await _require_student_profile(current_user, db)

    stmt = select(ArenaQuestion).where(
        ArenaQuestion.is_active.is_(True),
        or_(ArenaQuestion.institution_id.is_(None), ArenaQuestion.institution_id == current_user.institution_id),
    )
    if category is not None:
        stmt = stmt.where(ArenaQuestion.category == category)
    if difficulty is not None:
        stmt = stmt.where(ArenaQuestion.difficulty == difficulty)
    if question_type is not None:
        stmt = stmt.where(ArenaQuestion.question_type == question_type)
    if company_tag:
        stmt = stmt.where(ArenaQuestion.company_tag.ilike(f"%{company_tag.strip()}%"))
    if search:
        s = f"%{search.strip()}%"
        stmt = stmt.where(or_(ArenaQuestion.title.ilike(s), ArenaQuestion.prompt_text.ilike(s)))

    stmt = stmt.order_by(ArenaQuestion.id.asc()).offset(skip).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [_to_public_question(q) for q in rows]


async def list_arena_assessments(
    current_user: User,
    db: AsyncSession,
    mode: Optional[ArenaAssessmentMode] = None,
    category: Optional[ArenaCategory] = None,
) -> List[ArenaAssessmentSummary]:
    await ensure_arena_seed_data(db)
    profile = await _require_student_profile(current_user, db)

    stmt = (
        select(ArenaAssessment)
        .where(
            ArenaAssessment.is_published.is_(True),
            or_(ArenaAssessment.institution_id.is_(None), ArenaAssessment.institution_id == current_user.institution_id),
        )
        .options(selectinload(ArenaAssessment.department))
        .order_by(ArenaAssessment.mode.desc(), ArenaAssessment.id.asc())
    )
    if mode is not None:
        stmt = stmt.where(ArenaAssessment.mode == mode)
    if category is not None:
        stmt = stmt.where(ArenaAssessment.category == category)

    rows = (await db.execute(stmt)).scalars().all()
    filtered: List[ArenaAssessmentSummary] = []
    seen_titles = set()

    # Determine authenticated student's academic branch
    user_dept = profile.user.department if (profile.user and profile.user.department) else None
    student_dept_code = (user_dept.code or "").upper().strip() if user_dept else ""
    student_dept_name = (user_dept.name or "").lower().strip() if user_dept else ""
    cs_dept_codes = {"CSE", "IT", "AIML", "AIDS"}
    is_student_cs = (
        student_dept_code in cs_dept_codes
        or student_dept_code.startswith("CS")
        or student_dept_code.startswith("IT")
        or any(k in student_dept_name for k in ("computer", "information technology", "software", "data science", "artificial intelligence"))
    )

    for a in rows:
        if a.title in seen_titles:
            continue
        if a.target_graduation_year is not None and profile.graduation_year != a.target_graduation_year:
            continue

        assess_dept_code = (a.department.code or "").upper().strip() if (a.department and a.department.code) else ""
        assess_dept_name = (a.department.name or "").lower().strip() if (a.department and a.department.name) else ""
        is_cs_track = any(
            k in (a.title or "").lower() for k in ("software", "cs foundations", "quant pattern", "apexcloud", "fincore", "dsa", "dbms", "networks", "operating systems")
        )
        is_assess_cs = (
            assess_dept_code in cs_dept_codes
            or assess_dept_code.startswith("CS")
            or assess_dept_code.startswith("IT")
            or any(k in assess_dept_name for k in ("computer", "information technology", "software", "data science", "artificial intelligence"))
            or is_cs_track
        )

        # Branch isolation: ensure company-style and branch assessments strictly match student's branch
        if a.department_id is not None:
            if is_student_cs and is_assess_cs:
                pass  # Allow CS cluster
            elif a.department_id != current_user.department_id:
                continue
        elif a.mode == ArenaAssessmentMode.COMPANY_PREP:
            # Universal company prep must NOT leak CS company tracks to non-CS students
            if not is_student_cs and is_cs_track:
                continue
            if is_student_cs and not is_cs_track:
                continue
        else:
            # Timed tests without department_id
            if not is_student_cs and is_cs_track:
                continue

        seen_titles.add(a.title)
        filtered.append(
            ArenaAssessmentSummary(
                id=a.id,
                title=a.title,
                description=a.description,
                mode=a.mode,
                category=a.category,
                difficulty=a.difficulty,
                company_name_style=a.company_name_style,
                provenance_notice=a.provenance_notice,
                duration_minutes=a.duration_minutes,
                question_count=len(a.question_ids_json or []),
                passing_percentage=float(a.passing_percentage or 60.0),
                institution_id=a.institution_id,
                department_id=a.department_id,
                department_name=a.department.name if a.department else None,
                target_graduation_year=a.target_graduation_year,
                is_published=a.is_published,
                starts_at=a.starts_at,
                ends_at=a.ends_at,
            )
        )
    return filtered


# =============================================================================
# 2. Attempts, Coding Execution, Answer Submission & Review
# =============================================================================


async def start_arena_attempt(
    req: ArenaStartAttemptRequest,
    current_user: User,
    db: AsyncSession,
) -> ArenaAttemptDetail:
    await ensure_arena_seed_data(db)
    profile = await _require_student_profile(current_user, db)
    now = datetime.now(timezone.utc)

    assessment: Optional[ArenaAssessment] = None
    question_ids: List[int] = []
    time_limit_seconds: Optional[int] = None
    title = req.title or "Topic Practice Session"
    mode = req.mode
    category = req.category
    difficulty = req.difficulty
    company_style = req.company_name_style

    if req.assessment_id is not None:
        assess_stmt = select(ArenaAssessment).where(ArenaAssessment.id == req.assessment_id)
        assessment = (await db.execute(assess_stmt)).scalar_one_or_none()
        if not assessment:
            raise EntityNotFoundException("Assessment", req.assessment_id)
        if assessment.institution_id is not None and assessment.institution_id != current_user.institution_id:
            raise AuthorizationException("You cannot access an assessment belonging to another institution.")
        if not assessment.is_published:
            raise ValidationException("This assessment is not currently published.")
        if assessment.department_id is not None:
            assess_dept = (await db.execute(select(Department).where(Department.id == assessment.department_id))).scalar_one_or_none()
            assess_dept_code = (assess_dept.code or "").upper().strip() if (assess_dept and assess_dept.code) else ""
            assess_dept_name = (assess_dept.name or "").lower().strip() if (assess_dept and assess_dept.name) else ""
            user_dept = profile.user.department if (profile.user and profile.user.department) else None
            student_dept_code = (user_dept.code or "").upper().strip() if user_dept else ""
            student_dept_name = (user_dept.name or "").lower().strip() if user_dept else ""
            cs_codes = {"CSE", "IT", "AIML", "AIDS"}
            is_student_cs = (
                student_dept_code in cs_codes
                or student_dept_code.startswith("CS")
                or student_dept_code.startswith("IT")
                or any(k in student_dept_name for k in ("computer", "information technology", "software", "data science", "artificial intelligence"))
            )
            is_assess_cs = (
                assess_dept_code in cs_codes
                or assess_dept_code.startswith("CS")
                or assess_dept_code.startswith("IT")
                or any(k in assess_dept_name for k in ("computer", "information technology", "software", "data science", "artificial intelligence"))
            )
            if is_student_cs and is_assess_cs:
                pass
            elif assessment.department_id != current_user.department_id:
                raise AuthorizationException("This assessment is scoped to a different academic department.")
        if assessment.target_graduation_year is not None and assessment.target_graduation_year != profile.graduation_year:
            raise AuthorizationException("This institutional assessment is scoped to a different graduation batch.")
        if assessment.starts_at:
            st = assessment.starts_at if assessment.starts_at.tzinfo else assessment.starts_at.replace(tzinfo=timezone.utc)
            if now < st:
                raise ValidationException("This assessment window has not opened yet.")
        if assessment.ends_at:
            en = assessment.ends_at if assessment.ends_at.tzinfo else assessment.ends_at.replace(tzinfo=timezone.utc)
            if now > en:
                raise ValidationException("This assessment window has closed.")

        question_ids = [int(qid) for qid in (assessment.question_ids_json or [])]
        mode = assessment.mode
        category = assessment.category
        difficulty = assessment.difficulty
        company_style = assessment.company_name_style
        title = assessment.title
        time_limit_seconds = int(assessment.duration_minutes) * 60
    else:
        q_stmt = select(ArenaQuestion).where(
            ArenaQuestion.is_active.is_(True),
            or_(ArenaQuestion.institution_id.is_(None), ArenaQuestion.institution_id == current_user.institution_id),
        )
        if category is not None:
            q_stmt = q_stmt.where(ArenaQuestion.category == category)
        if difficulty is not None:
            q_stmt = q_stmt.where(ArenaQuestion.difficulty == difficulty)
        if company_style:
            q_stmt = q_stmt.where(ArenaQuestion.company_tag.ilike(f"%{company_style.strip()}%"))

        matched_qs = (await db.execute(q_stmt.order_by(ArenaQuestion.id.asc()).limit(req.question_count))).scalars().all()
        if not matched_qs and difficulty is not None:
            # Relax difficulty filter if category has questions at other levels
            relaxed_stmt = select(ArenaQuestion).where(
                ArenaQuestion.is_active.is_(True),
                or_(ArenaQuestion.institution_id.is_(None), ArenaQuestion.institution_id == current_user.institution_id),
            )
            if category is not None:
                relaxed_stmt = relaxed_stmt.where(ArenaQuestion.category == category)
            matched_qs = (
                await db.execute(relaxed_stmt.order_by(ArenaQuestion.id.asc()).limit(req.question_count))
            ).scalars().all()

        if not matched_qs and category is not None:
            # Fallback to technical or common questions if new branch category has not populated yet
            fb_stmt = select(ArenaQuestion).where(
                ArenaQuestion.is_active.is_(True),
                ArenaQuestion.category.in_([ArenaCategory.TECHNICAL_MCQS, ArenaCategory.APTITUDE_LOGICAL]),
            )
            matched_qs = (
                await db.execute(fb_stmt.order_by(ArenaQuestion.id.asc()).limit(req.question_count))
            ).scalars().all()

        if not matched_qs:
            raise ValidationException("No Arena questions matched the requested topic/filter criteria.")

        question_ids = [q.id for q in matched_qs]
        if req.time_limit_minutes is not None:
            time_limit_seconds = req.time_limit_minutes * 60
        elif mode == ArenaAssessmentMode.TIMED_TEST:
            time_limit_seconds = max(5, len(question_ids) * 2) * 60

        if not req.title:
            cat_label = CATEGORY_METADATA[category]["label"] if category else "Mixed Topics"
            if company_style:
                title = f"{company_style} Practice"
            elif mode == ArenaAssessmentMode.TIMED_TEST:
                title = f"{cat_label} Timed Test"
            else:
                title = f"{cat_label} Practice"

    expires_at = (now + timedelta(seconds=time_limit_seconds)) if time_limit_seconds else None

    attempt = ArenaAttempt(
        student_id=profile.id,
        assessment_id=assessment.id if assessment else None,
        title=title,
        mode=mode,
        category=category,
        difficulty=difficulty,
        company_name_style=company_style,
        status=ArenaAttemptStatus.IN_PROGRESS,
        question_ids_json=question_ids,
        time_limit_seconds=time_limit_seconds,
        started_at=now,
        expires_at=expires_at,
        total_questions=len(question_ids),
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return await get_arena_attempt_detail(attempt_id=attempt.id, current_user=current_user, db=db)


async def list_arena_attempts(
    current_user: User,
    db: AsyncSession,
    skip: int = 0,
    limit: int = 25,
) -> List[ArenaAttemptSummary]:
    profile = await _require_student_profile(current_user, db)
    stmt = (
        select(ArenaAttempt)
        .where(ArenaAttempt.student_id == profile.id)
        .order_by(ArenaAttempt.started_at.desc(), ArenaAttempt.id.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    for a in rows:
        await _sync_attempt_expiry(a, db)
    return [_to_attempt_summary(a) for a in rows]


async def _load_owned_attempt(attempt_id: int, profile: StudentProfile, db: AsyncSession) -> ArenaAttempt:
    stmt = (
        select(ArenaAttempt)
        .where(ArenaAttempt.id == attempt_id)
        .options(selectinload(ArenaAttempt.answers), selectinload(ArenaAttempt.assessment))
    )
    attempt = (await db.execute(stmt)).scalar_one_or_none()
    if not attempt:
        raise EntityNotFoundException("ArenaAttempt", attempt_id)
    if attempt.student_id != profile.id:
        raise AuthorizationException("You do not have permission to access another student's Arena attempt.")
    return attempt


async def get_arena_attempt_detail(
    attempt_id: int,
    current_user: User,
    db: AsyncSession,
) -> ArenaAttemptDetail:
    profile = await _require_student_profile(current_user, db)
    attempt = await _load_owned_attempt(attempt_id, profile, db)
    await _sync_attempt_expiry(attempt, db)

    q_ids = [int(qid) for qid in (attempt.question_ids_json or [])]
    q_rows = (
        await db.execute(select(ArenaQuestion).where(ArenaQuestion.id.in_(q_ids)))
    ).scalars().all() if q_ids else []
    q_map = {q.id: q for q in q_rows}
    ans_map = {a.question_id: a for a in (attempt.answers or [])}

    is_finalized = attempt.status in (ArenaAttemptStatus.SUBMITTED, ArenaAttemptStatus.EXPIRED)
    slots: List[ArenaQuestionSlot] = []
    for idx, qid in enumerate(q_ids, start=1):
        q = q_map.get(qid)
        if not q:
            continue
        ans = ans_map.get(qid)
        reveal_review = is_finalized or (
            attempt.mode == ArenaAssessmentMode.TOPIC_PRACTICE and ans is not None
        )
        slots.append(
            ArenaQuestionSlot(
                question_order=idx,
                answered=ans is not None,
                question=_to_review_question(q) if reveal_review else _to_public_question(q),
                answer=_to_answer_view(ans) if ans else None,
            )
        )

    provenance = (
        attempt.assessment.provenance_notice
        if attempt.assessment
        else (COMPANY_PROVENANCE_NOTICE if attempt.company_name_style else CURATED_PROVENANCE_NOTICE)
    )
    summary = _to_attempt_summary(attempt)
    return ArenaAttemptDetail(
        **summary.model_dump(),
        provenance_notice=provenance,
        questions=slots,
    )


async def run_sandbox_code_for_attempt(
    attempt_id: int,
    req: ArenaRunCodeRequest,
    current_user: User,
    db: AsyncSession,
) -> SandboxRunResponse:
    profile = await _require_student_profile(current_user, db)
    attempt = await _load_owned_attempt(attempt_id, profile, db)
    if await _sync_attempt_expiry(attempt, db):
        raise ValidationException("Assessment time limit has expired; code runs are locked.")
    if attempt.status == ArenaAttemptStatus.SUBMITTED:
        raise ValidationException("Attempt has already been submitted.")

    if req.question_id not in (attempt.question_ids_json or []):
        raise ValidationException("Requested question is not part of this Arena attempt.")

    question = (
        await db.execute(select(ArenaQuestion).where(ArenaQuestion.id == req.question_id))
    ).scalar_one_or_none()
    if not question:
        raise EntityNotFoundException("ArenaQuestion", req.question_id)
    if question.question_type != ArenaQuestionType.CODING:
        raise ValidationException("Code execution is only supported on coding questions.")

    # Only expose/execute SAMPLE test cases on interactive Run Code; hidden tests run on answer submission
    sample_cases = [tc for tc in (question.test_cases_json or []) if tc.get("is_sample")]
    return await code_sandbox_service.execute_code(
        language=req.language,
        source_code=req.source_code,
        test_cases=sample_cases,
        custom_stdin=req.custom_stdin,
    )


async def submit_arena_answer(
    attempt_id: int,
    req: ArenaSubmitAnswerRequest,
    current_user: User,
    db: AsyncSession,
) -> ArenaSubmitAnswerResponse:
    profile = await _require_student_profile(current_user, db)
    attempt = await _load_owned_attempt(attempt_id, profile, db)
    if await _sync_attempt_expiry(attempt, db):
        raise AppException("Timed assessment has expired; further answers cannot be recorded.", code="ATTEMPT_EXPIRED", status_code=400)
    if attempt.status == ArenaAttemptStatus.SUBMITTED:
        raise AppException("Attempt is already submitted.", code="ATTEMPT_ALREADY_SUBMITTED", status_code=400)

    q_ids = [int(qid) for qid in (attempt.question_ids_json or [])]
    if req.question_id not in q_ids:
        raise ValidationException("Submitted question_id does not belong to this Arena attempt.")

    q_rows = (
        await db.execute(select(ArenaQuestion).where(ArenaQuestion.id.in_(q_ids)))
    ).scalars().all()
    q_map = {q.id: q for q in q_rows}
    question = q_map[req.question_id]
    q_order = q_ids.index(req.question_id) + 1

    is_correct = False
    score_awarded = 0.0
    exec_json: Optional[Dict[str, Any]] = None
    ai_feedback_json: Optional[Dict[str, Any]] = None

    if question.question_type == ArenaQuestionType.MCQ:
        if not req.selected_option_key or not req.selected_option_key.strip():
            raise ValidationException("selected_option_key is required for MCQ questions.")
        valid_keys = {str(o.get("key", "")).upper() for o in (question.options_json or [])}
        chosen = req.selected_option_key.strip().upper()
        if valid_keys and chosen not in valid_keys:
            raise ValidationException(f"Invalid option '{chosen}'. Valid keys: {sorted(valid_keys)}.")
        expected_key = (question.correct_option_key or "").strip().upper()
        is_correct = bool(expected_key and chosen == expected_key)
        score_awarded = float(question.max_marks) if is_correct else 0.0

    elif question.question_type == ArenaQuestionType.CODING:
        if not req.submitted_code or not req.code_language:
            raise ValidationException("Both submitted_code and code_language are required for coding problems.")
        all_cases = list(question.test_cases_json or [])
        sandbox_res = await code_sandbox_service.execute_code(
            language=req.code_language,
            source_code=req.submitted_code,
            test_cases=all_cases,
        )
        exec_json = sandbox_res.model_dump()
        if sandbox_res.total_count > 0:
            ratio = sandbox_res.passed_count / sandbox_res.total_count
            is_correct = sandbox_res.all_passed
            score_awarded = round(question.max_marks * ratio, 2)
        else:
            is_correct = False
            score_awarded = 0.0

    elif question.question_type == ArenaQuestionType.BEHAVIORAL:
        if not req.behavioral_response or len(req.behavioral_response.strip()) < 5:
            raise ValidationException("Please provide a substantive behavioral response (at least 5 characters).")
        is_correct, score_awarded, ai_feedback_json = _evaluate_behavioral_answer(
            question, req.behavioral_response
        )
        try:
            provider = get_ai_provider()
            if provider.__class__.__name__ != "MockAIProvider":
                ai_out, _ = await provider.generate_structured(
                    schema=_BehavioralAIReview,
                    system_instruction=(
                        "Evaluate the student's STAR behavioral interview response constructively. "
                        "Provide score_out_of_100 (0-100), strengths, improvements, and summary."
                    ),
                    user_prompt=f"Prompt: {question.prompt_text}\nResponse: {req.behavioral_response[:2500]}",
                )
                ai_feedback_json = ai_out.model_dump()
                score_awarded = round((ai_out.score_out_of_100 / 100.0) * question.max_marks, 2)
                is_correct = ai_out.score_out_of_100 >= 60
        except AIServiceError:
            pass

    existing_ans = next((a for a in (attempt.answers or []) if a.question_id == req.question_id), None)
    now = datetime.now(timezone.utc)
    if existing_ans:
        existing_ans.selected_option_key = req.selected_option_key.strip().upper() if req.selected_option_key else None
        existing_ans.submitted_code = req.submitted_code
        existing_ans.code_language = req.code_language
        existing_ans.behavioral_response = req.behavioral_response
        existing_ans.is_correct = is_correct
        existing_ans.score_awarded = score_awarded
        existing_ans.time_spent_seconds = req.time_spent_seconds
        existing_ans.execution_result_json = exec_json
        existing_ans.ai_feedback_json = ai_feedback_json
        existing_ans.answered_at = now
        ans_obj = existing_ans
    else:
        ans_obj = ArenaAttemptAnswer(
            attempt_id=attempt.id,
            question_id=req.question_id,
            student_id=profile.id,
            question_order=q_order,
            selected_option_key=req.selected_option_key.strip().upper() if req.selected_option_key else None,
            submitted_code=req.submitted_code,
            code_language=req.code_language,
            behavioral_response=req.behavioral_response,
            is_correct=is_correct,
            score_awarded=score_awarded,
            time_spent_seconds=req.time_spent_seconds,
            execution_result_json=exec_json,
            ai_feedback_json=ai_feedback_json,
            answered_at=now,
        )
        db.add(ans_obj)
        attempt.answers.append(ans_obj)

    attempt.elapsed_seconds = sum(int(a.time_spent_seconds or 0) for a in attempt.answers)
    _recalculate_attempt_metrics(attempt, q_map)

    await db.commit()
    await db.refresh(attempt)
    await db.refresh(ans_obj)

    immediate_review = attempt.mode == ArenaAssessmentMode.TOPIC_PRACTICE
    return ArenaSubmitAnswerResponse(
        attempt=_to_attempt_summary(attempt),
        answer=_to_answer_view(ans_obj),
        immediate_review_unlocked=immediate_review,
        correct_option_key=question.correct_option_key if immediate_review else None,
        explanation_text=question.explanation_text if immediate_review else None,
        sample_solution_text=question.sample_solution_text if immediate_review else None,
    )


async def submit_arena_attempt(
    attempt_id: int,
    req: Optional[ArenaSubmitAttemptRequest],
    current_user: User,
    db: AsyncSession,
) -> ArenaAttemptDetail:
    profile = await _require_student_profile(current_user, db)
    attempt = await _load_owned_attempt(attempt_id, profile, db)
    await _sync_attempt_expiry(attempt, db)

    if attempt.status == ArenaAttemptStatus.IN_PROGRESS:
        now = datetime.now(timezone.utc)
        q_ids = [int(qid) for qid in (attempt.question_ids_json or [])]
        q_rows = (
            await db.execute(select(ArenaQuestion).where(ArenaQuestion.id.in_(q_ids)))
        ).scalars().all() if q_ids else []
        q_map = {q.id: q for q in q_rows}
        _recalculate_attempt_metrics(attempt, q_map)

        attempt.status = ArenaAttemptStatus.SUBMITTED
        attempt.submitted_at = now
        if req and req.elapsed_seconds is not None:
            attempt.elapsed_seconds = req.elapsed_seconds
        elif attempt.started_at:
            started = attempt.started_at if attempt.started_at.tzinfo else attempt.started_at.replace(tzinfo=timezone.utc)
            attempt.elapsed_seconds = max(attempt.elapsed_seconds or 0, int((now - started).total_seconds()))

        await db.commit()

    return await get_arena_attempt_detail(attempt_id=attempt.id, current_user=current_user, db=db)


# =============================================================================
# 3. Performance Analytics & Personalized Practice
# =============================================================================


async def get_arena_analytics(current_user: User, db: AsyncSession) -> ArenaPerformanceAnalytics:
    profile = await _require_student_profile(current_user, db)

    att_stmt = (
        select(ArenaAttempt)
        .where(ArenaAttempt.student_id == profile.id)
        .order_by(ArenaAttempt.started_at.asc(), ArenaAttempt.id.asc())
    )
    attempts = list((await db.execute(att_stmt)).scalars().all())
    for a in attempts:
        await _sync_attempt_expiry(a, db)

    ans_stmt = (
        select(ArenaAttemptAnswer)
        .where(ArenaAttemptAnswer.student_id == profile.id)
        .options(selectinload(ArenaAttemptAnswer.question))
    )
    answers = list((await db.execute(ans_stmt)).scalars().all())

    completed = [a for a in attempts if a.status in (ArenaAttemptStatus.SUBMITTED, ArenaAttemptStatus.EXPIRED)]
    total_q_attempted = len(answers)
    total_correct = sum(1 for a in answers if a.is_correct)
    total_incorrect = total_q_attempted - total_correct
    overall_acc = round((total_correct / total_q_attempted) * 100.0, 1) if total_q_attempted > 0 else 0.0
    avg_time = (
        round(sum(int(a.time_spent_seconds or 0) for a in answers) / total_q_attempted, 1)
        if total_q_attempted > 0
        else 0.0
    )
    coding_solved = len({
        a.question_id
        for a in answers
        if a.is_correct and a.question and a.question.question_type == ArenaQuestionType.CODING
    })

    ans_by_cat: Dict[ArenaCategory, List[ArenaAttemptAnswer]] = defaultdict(list)
    for a in answers:
        if a.question:
            ans_by_cat[a.question.category].append(a)

    topic_proficiency: List[ArenaTopicProficiencyItem] = []
    for cat in ArenaCategory:
        c_ans = ans_by_cat[cat]
        c_total = len(c_ans)
        c_correct = sum(1 for x in c_ans if x.is_correct)
        c_acc = round((c_correct / c_total) * 100.0, 1) if c_total > 0 else 0.0
        c_avg_t = round(sum(int(x.time_spent_seconds or 0) for x in c_ans) / c_total, 1) if c_total > 0 else 0.0
        topic_proficiency.append(
            ArenaTopicProficiencyItem(
                category=cat,
                label=CATEGORY_METADATA[cat]["label"],
                questions_attempted=c_total,
                correct_count=c_correct,
                incorrect_count=c_total - c_correct,
                accuracy_pct=c_acc,
                avg_solving_seconds=c_avg_t,
                proficiency_band=_proficiency_band(c_total, c_acc),
            )
        )

    trend = [
        ArenaTrendPoint(
            attempt_id=a.id,
            title=a.title,
            mode=a.mode,
            submitted_at=a.submitted_at or a.started_at,
            score_pct=round(float(a.score_pct or 0.0), 1),
            accuracy_pct=round(float(a.accuracy_pct or 0.0), 1),
            questions_attempted=int(a.attempted_count or 0),
        )
        for a in completed
    ]

    recent = [_to_attempt_summary(a) for a in reversed(attempts[-15:])]
    return ArenaPerformanceAnalytics(
        total_attempts=len(attempts),
        completed_attempts=len(completed),
        total_questions_attempted=total_q_attempted,
        total_correct=total_correct,
        total_incorrect=total_incorrect,
        overall_accuracy_pct=overall_acc,
        avg_solving_time_seconds=avg_time,
        coding_problems_solved=coding_solved,
        topic_proficiency=topic_proficiency,
        recent_attempts=recent,
        improvement_trend=trend,
        advisory_note=(
            "Arena analytics reflect saved practice and assessment history to help guide study priorities. "
            "Practice scores never alter verified academic records or deterministic eligibility cutoffs."
        ),
    )


async def get_personalized_practice_recommendations(
    current_user: User,
    db: AsyncSession,
    job_id: Optional[int] = None,
) -> ArenaPersonalizedPracticeResponse:
    await ensure_arena_seed_data(db)
    profile = await _require_student_profile(current_user, db)

    # Resolve student verified academic department context upfront
    user_dept = profile.user.department if (profile.user and profile.user.department) else None
    if not user_dept and profile.user and profile.user.department_id:
        user_dept = await db.get(Department, profile.user.department_id)
    if not user_dept and profile.roll_number:
        roll_u = profile.roll_number.upper()
        for c in ["CSE", "IT", "ECE", "EEE", "MECH", "CIVIL", "CHEM", "MINE", "PIE"]:
            if c in roll_u:
                dept_stmt = select(Department).where(Department.code == c)
                user_dept = (await db.execute(dept_stmt)).scalars().first()
                if user_dept:
                    break

    dept_id = user_dept.id if user_dept else None
    dept_code = (user_dept.code or "").upper().strip() if user_dept else ""
    dept_name = (user_dept.name or "").strip() if user_dept else ""
    active_branch_cats = resolve_department_arena_categories(dept_code, dept_name)

    student_skills_norm = {normalize_skill(s.skill_name) for s in (profile.skills or []) if s.skill_name}

    # 1. Inspect branch-eligible published target jobs to uncover discipline-accurate target roles and missing skills
    job_filters = [Job.status == JobStatus.PUBLISHED, Job.is_active.is_(True)]
    if current_user.institution_id is not None:
        job_filters.append((Job.institution_id.is_(None)) | (Job.institution_id == current_user.institution_id))
    else:
        job_filters.append(Job.institution_id.is_(None))

    if job_id is not None:
        job_stmt = (
            select(Job)
            .where(*job_filters, Job.id == job_id)
            .options(
                selectinload(Job.skills),
                selectinload(Job.eligible_departments),
            )
        )
        jobs = list((await db.execute(job_stmt)).scalars().all())
    else:
        job_stmt = (
            select(Job)
            .where(*job_filters)
            .options(
                selectinload(Job.skills),
                selectinload(Job.eligible_departments),
            )
            .order_by(Job.created_at.desc())
        )
        all_candidate_jobs = list((await db.execute(job_stmt)).scalars().all())

        # Strict Branch-Aware Filtering:
        # Prioritize jobs matching the student's department. Never inject unrelated branches when branch jobs exist.
        branch_specific_jobs: List[Job] = []
        open_to_all_jobs: List[Job] = []
        for j in all_candidate_jobs:
            elig_ids = [ed.department_id for ed in (j.eligible_departments or [])]
            if dept_id is not None and dept_id in elig_ids:
                branch_specific_jobs.append(j)
            elif not elig_ids:
                open_to_all_jobs.append(j)

        if branch_specific_jobs:
            jobs = branch_specific_jobs[:5]
        else:
            jobs = open_to_all_jobs[:5]

    target_roles = [j.title for j in jobs]
    if not target_roles:
        # Fallback to realistic branch-grounded placement role if no drives configured
        target_roles = [f"{dept_name or 'Engineering'} Placement Candidate"]

    missing_skills: List[str] = []
    for j in jobs:
        for js in (j.skills or []):
            if normalize_skill(js.skill_name) not in student_skills_norm and js.skill_name not in missing_skills:
                missing_skills.append(js.skill_name)

    # 2. Check latest ReadinessSnapshot if available
    snap_stmt = (
        select(ReadinessSnapshot)
        .where(ReadinessSnapshot.student_id == profile.id)
        .order_by(ReadinessSnapshot.created_at.desc())
        .limit(1)
    )
    latest_snap = (await db.execute(snap_stmt)).scalar_one_or_none()
    if latest_snap:
        for gap_list in (latest_snap.remaining_skill_gaps_json, latest_snap.missing_data_fields_json):
            if isinstance(gap_list, list):
                for g in gap_list:
                    if isinstance(g, str) and g not in missing_skills:
                        missing_skills.append(g)

    # 3. Inspect Arena answer proficiency per category
    analytics = await get_arena_analytics(current_user=current_user, db=db)
    weak_cats: List[ArenaCategory] = [
        item.category
        for item in analytics.topic_proficiency
        if item.questions_attempted > 0 and item.accuracy_pct < 70.0 and (item.category in active_branch_cats or item.category == ArenaCategory.TECHNICAL_MCQS)
    ]
    unstarted_cats: List[ArenaCategory] = [
        item.category for item in analytics.topic_proficiency if item.questions_attempted == 0 and item.category in active_branch_cats
    ]

    all_qs = (
        await db.execute(
            select(ArenaQuestion).where(
                ArenaQuestion.is_active.is_(True),
                or_(ArenaQuestion.institution_id.is_(None), ArenaQuestion.institution_id == current_user.institution_id),
                ArenaQuestion.category.in_(active_branch_cats),
            )
        )
    ).scalars().all()
    qs_by_cat: Dict[ArenaCategory, List[ArenaQuestion]] = defaultdict(list)
    for q in all_qs:
        qs_by_cat[q.category].append(q)

    recommendations: List[ArenaRecommendedExercise] = []

    # Prioritize weak categories from real attempts
    for cat in weak_cats[:3]:
        meta = CATEGORY_METADATA.get(cat, {"label": cat.value.replace("_", " ").title()})
        q_ids = [q.id for q in qs_by_cat[cat][:4]]
        recommendations.append(
            ArenaRecommendedExercise(
                recommendation_id=f"weak-{cat.value}",
                title=f"Strengthen {meta['label']}",
                reason="Recent Arena accuracy in this category is below 70%. Re-practicing core fundamentals builds speed and reliability.",
                source_signal="weak_category",
                category=cat,
                category_label=meta["label"],
                difficulty=ArenaDifficulty.EASY,
                suggested_question_ids=q_ids,
                target_role=target_roles[0] if target_roles else None,
            )
        )

    # Match missing skills / target roles to relevant Arena questions strictly within student branch
    skill_lower_set = {s.lower() for s in missing_skills}
    if skill_lower_set:
        matched_skill_qs = [
            q
            for q in all_qs
            if any(
                tag.lower() in s or s in tag.lower()
                for tag in (q.role_tags_json or [])
                for s in skill_lower_set
            )
        ]
        if matched_skill_qs:
            cat = matched_skill_qs[0].category
            recommendations.append(
                ArenaRecommendedExercise(
                    recommendation_id="skill-gap-target",
                    title=f"Bridge Target Role Skill Gaps ({', '.join(missing_skills[:3])})",
                    reason=f"Selected exercises aligned with gaps detected against active jobs ({', '.join(target_roles[:2])}).",
                    source_signal="skill_gap",
                    category=cat,
                    category_label=CATEGORY_METADATA.get(cat, {}).get("label", cat.value.replace("_", " ").title()),
                    difficulty=ArenaDifficulty.MEDIUM,
                    suggested_question_ids=[q.id for q in matched_skill_qs[:4]],
                    target_role=target_roles[0] if target_roles else None,
                )
            )

    # Ensure core unattempted branch-specific and aptitude categories are surfaced
    priority_unstarted = [c for c in active_branch_cats if c in unstarted_cats]
    seen_cats = {r.category for r in recommendations}
    for cat in priority_unstarted:
        if len(recommendations) >= 5:
            break
        if cat in seen_cats or not qs_by_cat[cat]:
            continue
        seen_cats.add(cat)
        meta = CATEGORY_METADATA.get(cat, {"label": cat.value.replace("_", " ").title()})
        recommendations.append(
            ArenaRecommendedExercise(
                recommendation_id=f"roadmap-{cat.value}",
                title=f"Start {meta['label']} Diagnostic",
                reason="Unattempted placement category recommended by your readiness & preparation roadmap.",
                source_signal="career_roadmap" if latest_snap else "target_job",
                category=cat,
                category_label=meta["label"],
                difficulty=ArenaDifficulty.EASY,
                suggested_question_ids=[q.id for q in qs_by_cat[cat][:4]],
                target_role=target_roles[0] if target_roles else None,
            )
        )

    branch_display = dept_name if dept_name else "Core"
    ai_tip = (
        f"Focus first on {recommendations[0].category_label} and review post-submission explanations carefully to lock in core patterns."
        if recommendations
        else f"Maintain steady timed drills across {branch_display} fundamentals and Aptitude to stay sharp for campus rounds."
    )
    try:
        provider = get_ai_provider()
        if provider.__class__.__name__ != "MockAIProvider" and recommendations:
            tip_out, _ = await provider.generate_structured(
                schema=_PersonalizedTipAI,
                system_instruction=f"Provide a 1-2 sentence encouraging placement study tip based on the student's academic branch ({branch_display}) and weak topics.",
                user_prompt=(
                    f"Academic Department: {branch_display}; "
                    f"Weak categories: {[c.value for c in weak_cats]}; "
                    f"Missing skills: {missing_skills[:5]}; Target roles: {target_roles[:3]}"
                ),
            )
            ai_tip = tip_out.study_tip
    except AIServiceError:
        pass

    return ArenaPersonalizedPracticeResponse(
        target_roles_considered=target_roles,
        missing_skills_detected=missing_skills[:8],
        weak_categories=weak_cats,
        recommendations=recommendations,
        ai_study_tip=ai_tip,
        advisory_notice=(
            "Personalized exercises are advisory recommendations derived from verified skill gaps, "
            "published job roles, readiness indicators, and your Arena accuracy."
        ),
    )


# =============================================================================
# 4. Privacy Controls & Department / Batch / Institution Leaderboards
# =============================================================================


async def get_or_create_arena_preferences(current_user: User, db: AsyncSession) -> ArenaUserPreferenceResponse:
    profile = await _require_student_profile(current_user, db)
    pref = (
        await db.execute(select(ArenaUserPreference).where(ArenaUserPreference.student_id == profile.id))
    ).scalar_one_or_none()
    if not pref:
        pref = ArenaUserPreference(
            student_id=profile.id,
            leaderboard_opt_in=False,
            anonymize_name=True,
            preferred_language="python",
        )
        db.add(pref)
        await db.commit()
        await db.refresh(pref)

    return ArenaUserPreferenceResponse(
        leaderboard_opt_in=bool(pref.leaderboard_opt_in),
        anonymize_name=bool(pref.anonymize_name),
        preferred_language=pref.preferred_language,
        privacy_notice=PRIVACY_GUARANTEE_TEXT,
    )


async def update_arena_preferences(
    req: ArenaUserPreferenceUpdate,
    current_user: User,
    db: AsyncSession,
) -> ArenaUserPreferenceResponse:
    profile = await _require_student_profile(current_user, db)
    pref = (
        await db.execute(select(ArenaUserPreference).where(ArenaUserPreference.student_id == profile.id))
    ).scalar_one_or_none()
    if not pref:
        pref = ArenaUserPreference(student_id=profile.id)
        db.add(pref)
    if req.leaderboard_opt_in is not None:
        pref.leaderboard_opt_in = req.leaderboard_opt_in
    if req.anonymize_name is not None:
        pref.anonymize_name = req.anonymize_name
    if req.preferred_language is not None:
        pref.preferred_language = req.preferred_language
    await db.commit()
    await db.refresh(pref)

    return ArenaUserPreferenceResponse(
        leaderboard_opt_in=bool(pref.leaderboard_opt_in),
        anonymize_name=bool(pref.anonymize_name),
        preferred_language=pref.preferred_language,
        privacy_notice=PRIVACY_GUARANTEE_TEXT,
    )


async def get_arena_leaderboard(
    scope: str,
    current_user: User,
    db: AsyncSession,
) -> ArenaLeaderboardResponse:
    if scope not in ("department", "batch", "institution"):
        raise ValidationException("Leaderboard scope must be one of: 'department', 'batch', 'institution'.")

    profile = await _require_student_profile(current_user, db)
    viewer_pref = (
        await db.execute(select(ArenaUserPreference).where(ArenaUserPreference.student_id == profile.id))
    ).scalar_one_or_none()
    viewer_opted_in = bool(viewer_pref and viewer_pref.leaderboard_opt_in)

    stmt = (
        select(ArenaUserPreference, StudentProfile, User)
        .join(StudentProfile, ArenaUserPreference.student_id == StudentProfile.id)
        .join(User, StudentProfile.user_id == User.id)
        .where(
            ArenaUserPreference.leaderboard_opt_in.is_(True),
            User.is_active.is_(True),
        )
        .options(selectinload(User.department))
    )
    if current_user.institution_id is not None:
        stmt = stmt.where(User.institution_id == current_user.institution_id)
    if scope == "department" and current_user.department_id is not None:
        stmt = stmt.where(User.department_id == current_user.department_id)
    elif scope == "batch":
        stmt = stmt.where(StudentProfile.graduation_year == profile.graduation_year)

    opted_rows = (await db.execute(stmt)).all()
    student_ids = [sp.id for _, sp, _ in opted_rows]
    if not student_ids:
        return ArenaLeaderboardResponse(
            scope=scope,  # type: ignore[arg-type]
            department_name=current_user.department.name if getattr(current_user, "department", None) else None,
            graduation_year=profile.graduation_year if scope == "batch" else None,
            viewer_opted_in=viewer_opted_in,
            total_opted_in_participants=0,
            privacy_guarantee=PRIVACY_GUARANTEE_TEXT,
            entries=[],
        )

    ans_rows = (
        await db.execute(select(ArenaAttemptAnswer).where(ArenaAttemptAnswer.student_id.in_(student_ids)))
    ).scalars().all()
    att_rows = (
        await db.execute(
            select(ArenaAttempt).where(
                ArenaAttempt.student_id.in_(student_ids),
                ArenaAttempt.status.in_([ArenaAttemptStatus.SUBMITTED, ArenaAttemptStatus.EXPIRED]),
            )
        )
    ).scalars().all()

    ans_by_sid: Dict[int, List[ArenaAttemptAnswer]] = defaultdict(list)
    for a in ans_rows:
        ans_by_sid[a.student_id].append(a)
    att_by_sid: Dict[int, List[ArenaAttempt]] = defaultdict(list)
    for t in att_rows:
        att_by_sid[t.student_id].append(t)

    scored_rows: List[Tuple[float, float, int, ArenaLeaderboardEntry]] = []
    for pref, sp, usr in opted_rows:
        s_ans = ans_by_sid[sp.id]
        s_att = att_by_sid[sp.id]
        q_count = len(s_ans)
        acc = round((sum(1 for x in s_ans if x.is_correct) / q_count) * 100.0, 1) if q_count > 0 else 0.0
        avg_score = round(sum(float(x.score_pct or 0.0) for x in s_att) / len(s_att), 1) if s_att else acc
        display_name = f"Scholar #{sp.id:03d}" if pref.anonymize_name else usr.full_name
        entry = ArenaLeaderboardEntry(
            rank=0,
            display_name=display_name,
            is_current_user=(sp.id == profile.id),
            is_anonymized=bool(pref.anonymize_name),
            department_name=usr.department.name if getattr(usr, "department", None) else None,
            graduation_year=sp.graduation_year,
            questions_attempted=q_count,
            accuracy_pct=acc,
            avg_score_pct=avg_score,
            completed_attempts=len(s_att),
        )
        scored_rows.append((avg_score, acc, q_count, entry))

    scored_rows.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    ranked: List[ArenaLeaderboardEntry] = []
    for idx, (_, _, _, entry) in enumerate(scored_rows, start=1):
        entry.rank = idx
        ranked.append(entry)

    return ArenaLeaderboardResponse(
        scope=scope,  # type: ignore[arg-type]
        department_name=current_user.department.name if getattr(current_user, "department", None) else None,
        graduation_year=profile.graduation_year if scope == "batch" else None,
        viewer_opted_in=viewer_opted_in,
        total_opted_in_participants=len(ranked),
        privacy_guarantee=PRIVACY_GUARANTEE_TEXT,
        entries=ranked,
    )


# =============================================================================
# 5. Institutional Staff (TPO / Admin) Test Publishing & Aggregated Analytics
# =============================================================================


def _resolve_staff_institution_id(current_user: User, requested_inst_id: Optional[int]) -> int:
    if current_user.email == "maheshwarijaya03@gmail.com":
        return requested_inst_id or current_user.institution_id or 1
    if current_user.role == UserRole.TPO:
        if current_user.institution_id is None:
            raise AuthorizationException("TPO user must belong to an institution.")
        if requested_inst_id is not None and requested_inst_id != current_user.institution_id:
            raise AuthorizationException("TPO staff cannot publish or query tests for another institution.")
        return current_user.institution_id
    if current_user.role == UserRole.ADMIN:
        return requested_inst_id or current_user.institution_id or 1
    raise AuthorizationException("Only authorized TPO or Admin staff can manage institutional assessments.")


async def create_tpo_question(
    req: ArenaTpoQuestionCreateRequest,
    current_user: User,
    db: AsyncSession,
) -> ArenaQuestionReviewView:
    inst_id = _resolve_staff_institution_id(current_user, req.institution_id)
    if req.question_type == ArenaQuestionType.MCQ:
        if len(req.options) < 2 or not req.correct_option_key:
            raise ValidationException("MCQ questions require at least 2 options and a correct_option_key.")

    q = ArenaQuestion(
        title=req.title.strip(),
        prompt_text=req.prompt_text.strip(),
        category=req.category,
        difficulty=req.difficulty,
        question_type=req.question_type,
        content_source=ArenaContentSource.INSTITUTIONAL_STAFF,
        company_tag=None,
        role_tags_json=req.role_tags,
        options_json=[o.model_dump() for o in req.options] if req.options else None,
        correct_option_key=req.correct_option_key.strip().upper() if req.correct_option_key else None,
        starter_code_json=req.starter_code,
        test_cases_json=req.test_cases,
        explanation_text=req.explanation_text.strip(),
        sample_solution_text=req.sample_solution_text,
        expected_time_seconds=req.expected_time_seconds,
        max_marks=req.max_marks,
        institution_id=inst_id,
        created_by_user_id=current_user.id,
        is_active=True,
    )
    db.add(q)
    await db.commit()
    await db.refresh(q)
    return _to_review_question(q)


async def list_tpo_questions(current_user: User, db: AsyncSession, institution_id: Optional[int] = None) -> List[ArenaQuestionReviewView]:
    await ensure_arena_seed_data(db)
    inst_id = _resolve_staff_institution_id(current_user, institution_id)
    rows = (
        await db.execute(
            select(ArenaQuestion)
            .where(
                ArenaQuestion.is_active.is_(True),
                or_(ArenaQuestion.institution_id.is_(None), ArenaQuestion.institution_id == inst_id),
            )
            .order_by(ArenaQuestion.institution_id.desc().nullslast(), ArenaQuestion.id.asc())
        )
    ).scalars().all()
    return [_to_review_question(q) for q in rows]


async def create_tpo_assessment(
    req: ArenaTpoAssessmentCreateRequest,
    current_user: User,
    db: AsyncSession,
) -> ArenaAssessmentSummary:
    inst_id = _resolve_staff_institution_id(current_user, req.institution_id)

    if req.department_id is not None:
        dept = (await db.execute(select(Department).where(Department.id == req.department_id))).scalar_one_or_none()
        if not dept or dept.institution_id != inst_id:
            raise ValidationException("Selected department does not belong to your institution.")

    q_rows = (
        await db.execute(
            select(ArenaQuestion).where(
                ArenaQuestion.id.in_(req.question_ids),
                ArenaQuestion.is_active.is_(True),
                or_(ArenaQuestion.institution_id.is_(None), ArenaQuestion.institution_id == inst_id),
            )
        )
    ).scalars().all()
    found_ids = {q.id for q in q_rows}
    if len(found_ids) != len(set(req.question_ids)):
        raise ValidationException("One or more question_ids are invalid or unavailable to your institution.")

    assess = ArenaAssessment(
        title=req.title.strip(),
        description=req.description.strip(),
        mode=ArenaAssessmentMode.INSTITUTIONAL_TEST,
        category=req.category,
        difficulty=req.difficulty,
        company_name_style=None,
        provenance_notice=STAFF_PROVENANCE_NOTICE,
        duration_minutes=req.duration_minutes,
        question_ids_json=req.question_ids,
        passing_percentage=req.passing_percentage,
        institution_id=inst_id,
        department_id=req.department_id,
        target_graduation_year=req.target_graduation_year,
        created_by_user_id=current_user.id,
        is_published=req.is_published,
        starts_at=req.starts_at,
        ends_at=req.ends_at,
    )
    db.add(assess)
    await db.commit()
    await db.refresh(assess)

    dept_name = None
    if assess.department_id:
        d = (await db.execute(select(Department).where(Department.id == assess.department_id))).scalar_one_or_none()
        dept_name = d.name if d else None

    return ArenaAssessmentSummary(
        id=assess.id,
        title=assess.title,
        description=assess.description,
        mode=assess.mode,
        category=assess.category,
        difficulty=assess.difficulty,
        company_name_style=assess.company_name_style,
        provenance_notice=assess.provenance_notice,
        duration_minutes=assess.duration_minutes,
        question_count=len(assess.question_ids_json or []),
        passing_percentage=float(assess.passing_percentage),
        institution_id=assess.institution_id,
        department_id=assess.department_id,
        department_name=dept_name,
        target_graduation_year=assess.target_graduation_year,
        is_published=assess.is_published,
        starts_at=assess.starts_at,
        ends_at=assess.ends_at,
    )


async def list_tpo_assessments(
    current_user: User,
    db: AsyncSession,
    institution_id: Optional[int] = None,
) -> List[ArenaAssessmentSummary]:
    inst_id = _resolve_staff_institution_id(current_user, institution_id)
    rows = (
        await db.execute(
            select(ArenaAssessment)
            .where(ArenaAssessment.institution_id == inst_id)
            .options(selectinload(ArenaAssessment.department))
            .order_by(ArenaAssessment.created_at.desc())
        )
    ).scalars().all()
    return [
        ArenaAssessmentSummary(
            id=a.id,
            title=a.title,
            description=a.description,
            mode=a.mode,
            category=a.category,
            difficulty=a.difficulty,
            company_name_style=a.company_name_style,
            provenance_notice=a.provenance_notice,
            duration_minutes=a.duration_minutes,
            question_count=len(a.question_ids_json or []),
            passing_percentage=float(a.passing_percentage),
            institution_id=a.institution_id,
            department_id=a.department_id,
            department_name=a.department.name if a.department else None,
            target_graduation_year=a.target_graduation_year,
            is_published=a.is_published,
            starts_at=a.starts_at,
            ends_at=a.ends_at,
        )
        for a in rows
    ]


async def get_tpo_arena_analytics(
    current_user: User,
    db: AsyncSession,
    institution_id: Optional[int] = None,
) -> ArenaTpoAnalyticsResponse:
    inst_id = _resolve_staff_institution_id(current_user, institution_id)

    assess_rows = (
        await db.execute(
            select(ArenaAssessment)
            .where(ArenaAssessment.institution_id == inst_id)
            .options(selectinload(ArenaAssessment.department))
            .order_by(ArenaAssessment.created_at.desc())
        )
    ).scalars().all()

    inst_q_count = (
        await db.execute(
            select(func.count(ArenaQuestion.id)).where(
                ArenaQuestion.institution_id == inst_id,
                ArenaQuestion.is_active.is_(True),
            )
        )
    ).scalar_one()

    # Institutional attempts across enrolled students of this institution
    att_rows = (
        await db.execute(
            select(ArenaAttempt)
            .join(StudentProfile, ArenaAttempt.student_id == StudentProfile.id)
            .join(User, StudentProfile.user_id == User.id)
            .where(User.institution_id == inst_id)
        )
    ).scalars().all()

    ans_rows = (
        await db.execute(
            select(ArenaAttemptAnswer)
            .join(StudentProfile, ArenaAttemptAnswer.student_id == StudentProfile.id)
            .join(User, StudentProfile.user_id == User.id)
            .where(User.institution_id == inst_id)
            .options(selectinload(ArenaAttemptAnswer.question))
        )
    ).scalars().all()

    submitted_atts = [a for a in att_rows if a.status in (ArenaAttemptStatus.SUBMITTED, ArenaAttemptStatus.EXPIRED)]
    participants = len({a.student_id for a in att_rows})
    avg_score = (
        round(sum(float(a.score_pct or 0.0) for a in submitted_atts) / len(submitted_atts), 1)
        if submitted_atts
        else 0.0
    )
    avg_acc = (
        round(sum(float(a.accuracy_pct or 0.0) for a in submitted_atts) / len(submitted_atts), 1)
        if submitted_atts
        else 0.0
    )

    ans_by_cat: Dict[ArenaCategory, List[ArenaAttemptAnswer]] = defaultdict(list)
    for ans in ans_rows:
        if ans.question:
            ans_by_cat[ans.question.category].append(ans)

    cat_perf: List[ArenaTopicProficiencyItem] = []
    for cat in ArenaCategory:
        c_ans = ans_by_cat[cat]
        tot = len(c_ans)
        corr = sum(1 for x in c_ans if x.is_correct)
        acc = round((corr / tot) * 100.0, 1) if tot > 0 else 0.0
        avg_t = round(sum(int(x.time_spent_seconds or 0) for x in c_ans) / tot, 1) if tot > 0 else 0.0
        cat_perf.append(
            ArenaTopicProficiencyItem(
                category=cat,
                label=CATEGORY_METADATA[cat]["label"],
                questions_attempted=tot,
                correct_count=corr,
                incorrect_count=tot - corr,
                accuracy_pct=acc,
                avg_solving_seconds=avg_t,
                proficiency_band=_proficiency_band(tot, acc),
            )
        )

    att_by_assess: Dict[int, List[ArenaAttempt]] = defaultdict(list)
    for a in att_rows:
        if a.assessment_id:
            att_by_assess[a.assessment_id].append(a)

    breakdown: List[ArenaTpoAssessmentAnalyticsItem] = []
    for assess in assess_rows:
        a_list = att_by_assess[assess.id]
        sub_list = [x for x in a_list if x.status in (ArenaAttemptStatus.SUBMITTED, ArenaAttemptStatus.EXPIRED)]
        s_avg = round(sum(float(x.score_pct or 0.0) for x in sub_list) / len(sub_list), 1) if sub_list else 0.0
        a_avg = round(sum(float(x.accuracy_pct or 0.0) for x in sub_list) / len(sub_list), 1) if sub_list else 0.0
        passed = sum(1 for x in sub_list if float(x.score_pct or 0.0) >= float(assess.passing_percentage))
        pass_rate = round((passed / len(sub_list)) * 100.0, 1) if sub_list else 0.0
        breakdown.append(
            ArenaTpoAssessmentAnalyticsItem(
                assessment_id=assess.id,
                title=assess.title,
                category=assess.category,
                difficulty=assess.difficulty,
                is_published=assess.is_published,
                department_name=assess.department.name if assess.department else None,
                target_graduation_year=assess.target_graduation_year,
                total_attempts=len(a_list),
                submitted_attempts=len(sub_list),
                avg_score_pct=s_avg,
                avg_accuracy_pct=a_avg,
                pass_rate_pct=pass_rate,
            )
        )

    return ArenaTpoAnalyticsResponse(
        institution_id=inst_id,
        total_published_assessments=sum(1 for a in assess_rows if a.is_published),
        total_institutional_questions=int(inst_q_count or 0),
        participating_students=participants,
        total_submitted_attempts=len(submitted_atts),
        institution_avg_score_pct=avg_score,
        institution_avg_accuracy_pct=avg_acc,
        category_performance=cat_perf,
        assessment_breakdown=breakdown,
    )


async def get_tpo_students_arena_roster(
    current_user: User,
    db: AsyncSession,
    department_id: Optional[int] = None,
    graduation_year: Optional[int] = None,
    search: Optional[str] = None,
    institution_id: Optional[int] = None,
) -> ArenaTpoStudentRosterResponse:
    """Retrieve all enrolled students in the institution with their Arena attempt counts and diagnostic statistics."""
    inst_id = _resolve_staff_institution_id(current_user, institution_id)

    # 1. Base query for students in staff's institution
    stu_stmt = (
        select(StudentProfile)
        .join(User, StudentProfile.user_id == User.id)
        .where(User.institution_id == inst_id)
        .options(
            selectinload(StudentProfile.user).selectinload(User.department),
        )
    )

    if department_id is not None:
        stu_stmt = stu_stmt.where(User.department_id == department_id)
    if graduation_year is not None:
        stu_stmt = stu_stmt.where(StudentProfile.graduation_year == graduation_year)
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        stu_stmt = stu_stmt.where(
            or_(
                func.lower(User.full_name).ilike(term),
                func.lower(StudentProfile.roll_number).ilike(term),
            )
        )

    students = list((await db.execute(stu_stmt)).scalars().all())
    if not students:
        return ArenaTpoStudentRosterResponse(
            institution_id=inst_id,
            total_students=0,
            participating_students=0,
            average_accuracy_pct=0.0,
            students=[],
        )

    stu_ids = [s.id for s in students]

    # 2. Fetch all attempts for these students
    att_stmt = (
        select(ArenaAttempt)
        .where(ArenaAttempt.student_id.in_(stu_ids))
        .order_by(ArenaAttempt.started_at.desc())
    )
    attempts = list((await db.execute(att_stmt)).scalars().all())
    for a in attempts:
        await _sync_attempt_expiry(a, db)

    att_by_student: Dict[int, List[ArenaAttempt]] = defaultdict(list)
    for a in attempts:
        att_by_student[a.student_id].append(a)

    # 3. Build student roster items
    roster_items: List[ArenaStudentPerformanceItem] = []
    total_acc_sum = 0.0
    participating_count = 0

    for s in students:
        s_user = s.user
        s_dept = s_user.department if s_user else None
        s_attempts = att_by_student.get(s.id, [])
        submitted_attempts = [
            a for a in s_attempts if a.status in (ArenaAttemptStatus.SUBMITTED, ArenaAttemptStatus.EXPIRED)
        ]

        tot_attempts = len(s_attempts)
        comp_attempts = len(submitted_attempts)
        tot_q = sum(int(a.attempted_count or 0) for a in submitted_attempts)
        tot_corr = sum(int(a.correct_count or 0) for a in submitted_attempts)

        if comp_attempts > 0:
            participating_count += 1
            avg_acc = round(sum(float(a.accuracy_pct or 0.0) for a in submitted_attempts) / comp_attempts, 1)
            avg_score = round(sum(float(a.score_pct or 0.0) for a in submitted_attempts) / comp_attempts, 1)
            total_acc_sum += avg_acc
        else:
            avg_acc = 0.0
            avg_score = 0.0

        # Determine category breakdown
        cat_counts: Dict[str, int] = defaultdict(int)
        for a in s_attempts:
            if a.category:
                cat_counts[CATEGORY_METADATA.get(a.category, {}).get("label", a.category.value)] += 1

        top_cat = max(cat_counts.items(), key=lambda x: x[1])[0] if cat_counts else None
        last_active = s_attempts[0].submitted_at or s_attempts[0].started_at if s_attempts else None
        latest_title = s_attempts[0].title if s_attempts else None

        roster_items.append(
            ArenaStudentPerformanceItem(
                student_id=s.id,
                user_id=s.user_id,
                full_name=s_user.full_name if s_user else "Unknown Student",
                roll_number=s.roll_number,
                department_id=s_dept.id if s_dept else None,
                department_name=s_dept.name if s_dept else None,
                graduation_year=s.graduation_year,
                cgpa=float(s.cgpa) if s.cgpa is not None else None,
                total_attempts=tot_attempts,
                completed_attempts=comp_attempts,
                questions_attempted=tot_q,
                questions_correct=tot_corr,
                overall_accuracy_pct=avg_acc,
                avg_score_pct=avg_score,
                top_category=top_cat,
                weakest_category=None,
                last_active_at=last_active,
                latest_attempt_title=latest_title,
            )
        )

    # Sort students: active participants first by accuracy desc, then unstarted by roll number
    roster_items.sort(
        key=lambda x: (
            0 if x.total_attempts > 0 else 1,
            -x.overall_accuracy_pct,
            -x.total_attempts,
            x.roll_number,
        )
    )

    inst_avg_acc = round(total_acc_sum / participating_count, 1) if participating_count > 0 else 0.0

    return ArenaTpoStudentRosterResponse(
        institution_id=inst_id,
        total_students=len(students),
        participating_students=participating_count,
        average_accuracy_pct=inst_avg_acc,
        students=roster_items,
    )


async def get_tpo_student_arena_detail(
    student_id: int,
    current_user: User,
    db: AsyncSession,
    institution_id: Optional[int] = None,
) -> ArenaPerformanceAnalytics:
    """Retrieve granular diagnostic analytics and category proficiencies for an individual student."""
    inst_id = _resolve_staff_institution_id(current_user, institution_id)

    # Validate student belongs to staff's authorized institution
    stu_stmt = (
        select(StudentProfile)
        .join(User, StudentProfile.user_id == User.id)
        .where(StudentProfile.id == student_id, User.institution_id == inst_id)
        .options(selectinload(StudentProfile.user))
    )
    profile = (await db.execute(stu_stmt)).scalar_one_or_none()
    if not profile:
        raise EntityNotFoundException("StudentProfile", student_id)

    att_stmt = (
        select(ArenaAttempt)
        .where(ArenaAttempt.student_id == profile.id)
        .order_by(ArenaAttempt.started_at.asc(), ArenaAttempt.id.asc())
    )
    attempts = list((await db.execute(att_stmt)).scalars().all())
    for a in attempts:
        await _sync_attempt_expiry(a, db)

    ans_stmt = (
        select(ArenaAttemptAnswer)
        .where(ArenaAttemptAnswer.student_id == profile.id)
        .options(selectinload(ArenaAttemptAnswer.question))
    )
    answers = list((await db.execute(ans_stmt)).scalars().all())

    completed = [a for a in attempts if a.status in (ArenaAttemptStatus.SUBMITTED, ArenaAttemptStatus.EXPIRED)]
    total_q_attempted = len(answers)
    total_correct = sum(1 for a in answers if a.is_correct)
    total_incorrect = total_q_attempted - total_correct
    overall_acc = round((total_correct / total_q_attempted) * 100.0, 1) if total_q_attempted > 0 else 0.0
    avg_time = (
        round(sum(int(a.time_spent_seconds or 0) for a in answers) / total_q_attempted, 1)
        if total_q_attempted > 0
        else 0.0
    )
    coding_solved = len({
        a.question_id
        for a in answers
        if a.is_correct and a.question and a.question.question_type == ArenaQuestionType.CODING
    })

    ans_by_cat: Dict[ArenaCategory, List[ArenaAttemptAnswer]] = defaultdict(list)
    for a in answers:
        if a.question:
            ans_by_cat[a.question.category].append(a)

    topic_proficiency: List[ArenaTopicProficiencyItem] = []
    for cat in ArenaCategory:
        c_ans = ans_by_cat[cat]
        c_total = len(c_ans)
        c_correct = sum(1 for x in c_ans if x.is_correct)
        c_acc = round((c_correct / c_total) * 100.0, 1) if c_total > 0 else 0.0
        c_avg_t = round(sum(int(x.time_spent_seconds or 0) for x in c_ans) / c_total, 1) if c_total > 0 else 0.0
        topic_proficiency.append(
            ArenaTopicProficiencyItem(
                category=cat,
                label=CATEGORY_METADATA[cat]["label"],
                questions_attempted=c_total,
                correct_count=c_correct,
                incorrect_count=c_total - c_correct,
                accuracy_pct=c_acc,
                avg_solving_seconds=c_avg_t,
                proficiency_band=_proficiency_band(c_total, c_acc),
            )
        )

    trend = [
        ArenaTrendPoint(
            attempt_id=a.id,
            title=a.title,
            mode=a.mode,
            submitted_at=a.submitted_at or a.started_at,
            score_pct=round(float(a.score_pct or 0.0), 1),
            accuracy_pct=round(float(a.accuracy_pct or 0.0), 1),
            questions_attempted=int(a.attempted_count or 0),
        )
        for a in completed
    ]

    recent = [_to_attempt_summary(a) for a in reversed(attempts[-15:])]
    return ArenaPerformanceAnalytics(
        total_attempts=len(attempts),
        completed_attempts=len(completed),
        total_questions_attempted=total_q_attempted,
        total_correct=total_correct,
        total_incorrect=total_incorrect,
        overall_accuracy_pct=overall_acc,
        avg_solving_time_seconds=avg_time,
        coding_problems_solved=coding_solved,
        topic_proficiency=topic_proficiency,
        recent_attempts=recent,
        improvement_trend=trend,
        advisory_note=(
            f"Institutional Arena performance audit for student {profile.roll_number} ({profile.user.full_name if profile.user else ''}). "
            "Diagnostics guide faculty mentoring and skill intervention priorities."
        ),
    )

