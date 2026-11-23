"""FastAPI routes for Placement Preparation Arena."""
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import require_institutional_staff, require_student
from app.models.arena import (
    ArenaAssessmentMode,
    ArenaCategory,
    ArenaDifficulty,
    ArenaQuestionType,
)
from app.models.user import User
from app.schemas.arena import (
    ArenaAssessmentSummary,
    ArenaAttemptDetail,
    ArenaAttemptSummary,
    ArenaCategorySummary,
    ArenaLeaderboardResponse,
    ArenaPerformanceAnalytics,
    ArenaPersonalizedPracticeResponse,
    ArenaQuestionPublicView,
    ArenaQuestionReviewView,
    ArenaRunCodeRequest,
    ArenaStartAttemptRequest,
    ArenaSubmitAnswerRequest,
    ArenaSubmitAnswerResponse,
    ArenaSubmitAttemptRequest,
    ArenaTpoAnalyticsResponse,
    ArenaTpoQuestionCreateRequest,
    ArenaTpoAssessmentCreateRequest,
    ArenaStudentPerformanceItem,
    ArenaTpoStudentRosterResponse,
    ArenaUserPreferenceResponse,
    ArenaUserPreferenceUpdate,
    SandboxRunResponse,
)
from app.services.arena_service import (
    create_tpo_assessment,
    create_tpo_question,
    get_arena_analytics,
    get_arena_attempt_detail,
    get_arena_categories,
    get_arena_leaderboard,
    get_or_create_arena_preferences,
    get_personalized_practice_recommendations,
    get_tpo_arena_analytics,
    get_tpo_students_arena_roster,
    get_tpo_student_arena_detail,
    list_arena_assessments,
    list_arena_attempts,
    list_arena_questions,
    list_tpo_assessments,
    list_tpo_questions,
    run_sandbox_code_for_attempt,
    start_arena_attempt,
    submit_arena_answer,
    submit_arena_attempt,
    update_arena_preferences,
)

router = APIRouter(prefix="/arena", tags=["Placement Preparation Arena"])


# =============================================================================
# Student Practice, Coding Sandbox, Timed Tests & Company-Style Prep
# =============================================================================


@router.get(
    "/categories",
    response_model=List[ArenaCategorySummary],
    status_code=status.HTTP_200_OK,
)
async def list_categories_endpoint(
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """List all 11 Placement Preparation Arena categories with question counts and student proficiency."""
    return await get_arena_categories(current_user=current_user, db=db)


@router.get(
    "/questions",
    response_model=List[ArenaQuestionPublicView],
    status_code=status.HTTP_200_OK,
)
async def list_questions_endpoint(
    category: Optional[ArenaCategory] = Query(None),
    difficulty: Optional[ArenaDifficulty] = Query(None),
    question_type: Optional[ArenaQuestionType] = Query(None),
    company_tag: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Browse active Arena questions without exposing unreleased answer keys or hidden tests."""
    return await list_arena_questions(
        current_user=current_user,
        db=db,
        category=category,
        difficulty=difficulty,
        question_type=question_type,
        company_tag=company_tag,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/assessments",
    response_model=List[ArenaAssessmentSummary],
    status_code=status.HTTP_200_OK,
)
async def list_assessments_endpoint(
    mode: Optional[ArenaAssessmentMode] = Query(None),
    category: Optional[ArenaCategory] = Query(None),
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """List published timed tests, company-style prep tracks, and institutional assessments."""
    return await list_arena_assessments(current_user=current_user, db=db, mode=mode, category=category)


@router.post(
    "/attempts",
    response_model=ArenaAttemptDetail,
    status_code=status.HTTP_201_CREATED,
)
async def start_attempt_endpoint(
    req: ArenaStartAttemptRequest,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Start a topic practice session, timed test, company-style prep, or institutional assessment."""
    return await start_arena_attempt(req=req, current_user=current_user, db=db)


@router.get(
    "/attempts",
    response_model=List[ArenaAttemptSummary],
    status_code=status.HTTP_200_OK,
)
async def list_my_attempts_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Retrieve paginated Arena practice and assessment history for the current student."""
    return await list_arena_attempts(current_user=current_user, db=db, skip=skip, limit=limit)


@router.get(
    "/attempts/{attempt_id}",
    response_model=ArenaAttemptDetail,
    status_code=status.HTTP_200_OK,
)
async def get_attempt_detail_endpoint(
    attempt_id: int,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Retrieve attempt questions, answers, and post-submission explanations (when unlocked)."""
    return await get_arena_attempt_detail(attempt_id=attempt_id, current_user=current_user, db=db)


@router.post(
    "/attempts/{attempt_id}/run-code",
    response_model=SandboxRunResponse,
    status_code=status.HTTP_200_OK,
)
async def run_sandbox_code_endpoint(
    attempt_id: int,
    req: ArenaRunCodeRequest,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Execute coding solution strictly in an isolated sandbox against sample test cases / custom stdin."""
    return await run_sandbox_code_for_attempt(attempt_id=attempt_id, req=req, current_user=current_user, db=db)


@router.post(
    "/attempts/{attempt_id}/answer",
    response_model=ArenaSubmitAnswerResponse,
    status_code=status.HTTP_200_OK,
)
async def submit_answer_endpoint(
    attempt_id: int,
    req: ArenaSubmitAnswerRequest,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Submit and evaluate an MCQ, sandboxed coding, or behavioral response within an active attempt."""
    return await submit_arena_answer(attempt_id=attempt_id, req=req, current_user=current_user, db=db)


@router.post(
    "/attempts/{attempt_id}/submit",
    response_model=ArenaAttemptDetail,
    status_code=status.HTTP_200_OK,
)
async def submit_attempt_endpoint(
    attempt_id: int,
    req: Optional[ArenaSubmitAttemptRequest] = None,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Finalize an Arena attempt, compute score metrics, and unlock all answer explanations."""
    return await submit_arena_attempt(attempt_id=attempt_id, req=req, current_user=current_user, db=db)


# =============================================================================
# Analytics, Personalized Recommendations & Privacy-Preserving Leaderboard
# =============================================================================


@router.get(
    "/analytics",
    response_model=ArenaPerformanceAnalytics,
    status_code=status.HTTP_200_OK,
)
async def get_analytics_endpoint(
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Retrieve student practice analytics, topic proficiency, solving times, and score trends."""
    return await get_arena_analytics(current_user=current_user, db=db)


@router.get(
    "/recommendations",
    response_model=ArenaPersonalizedPracticeResponse,
    status_code=status.HTTP_200_OK,
)
async def get_recommendations_endpoint(
    job_id: Optional[int] = Query(None),
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Get personalized practice recommendations derived from skill gaps, readiness, and weak topics."""
    return await get_personalized_practice_recommendations(current_user=current_user, db=db, job_id=job_id)


@router.get(
    "/preferences",
    response_model=ArenaUserPreferenceResponse,
    status_code=status.HTTP_200_OK,
)
async def get_preferences_endpoint(
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Fetch student's Arena leaderboard opt-in, anonymization, and coding language preferences."""
    return await get_or_create_arena_preferences(current_user=current_user, db=db)


@router.put(
    "/preferences",
    response_model=ArenaUserPreferenceResponse,
    status_code=status.HTTP_200_OK,
)
async def update_preferences_endpoint(
    req: ArenaUserPreferenceUpdate,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Update student's Arena privacy controls and preferred coding language."""
    return await update_arena_preferences(req=req, current_user=current_user, db=db)


@router.get(
    "/leaderboard",
    response_model=ArenaLeaderboardResponse,
    status_code=status.HTTP_200_OK,
)
async def get_leaderboard_endpoint(
    scope: Literal["department", "batch", "institution"] = Query("department"),
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Privacy-preserving department/batch/institution leaderboard of opted-in students only."""
    return await get_arena_leaderboard(scope=scope, current_user=current_user, db=db)


# =============================================================================
# TPO & Admin Institutional Assessment Controls
# =============================================================================


@router.post(
    "/tpo/questions",
    response_model=ArenaQuestionReviewView,
    status_code=status.HTTP_201_CREATED,
)
async def create_tpo_question_endpoint(
    req: ArenaTpoQuestionCreateRequest,
    current_user: User = Depends(require_institutional_staff),
    db: AsyncSession = Depends(get_async_session),
):
    """Create an institution-scoped Arena question (TPO/Admin only)."""
    return await create_tpo_question(req=req, current_user=current_user, db=db)


@router.get(
    "/tpo/questions",
    response_model=List[ArenaQuestionReviewView],
    status_code=status.HTTP_200_OK,
)
async def list_tpo_questions_endpoint(
    institution_id: Optional[int] = Query(None),
    current_user: User = Depends(require_institutional_staff),
    db: AsyncSession = Depends(get_async_session),
):
    """List curated and institution-specific Arena questions available to institutional staff."""
    return await list_tpo_questions(current_user=current_user, db=db, institution_id=institution_id)


@router.post(
    "/tpo/assessments",
    response_model=ArenaAssessmentSummary,
    status_code=status.HTTP_201_CREATED,
)
async def create_tpo_assessment_endpoint(
    req: ArenaTpoAssessmentCreateRequest,
    current_user: User = Depends(require_institutional_staff),
    db: AsyncSession = Depends(get_async_session),
):
    """Publish or draft an institution-specific Arena assessment for students (TPO/Admin only)."""
    return await create_tpo_assessment(req=req, current_user=current_user, db=db)


@router.get(
    "/tpo/assessments",
    response_model=List[ArenaAssessmentSummary],
    status_code=status.HTTP_200_OK,
)
async def list_tpo_assessments_endpoint(
    institution_id: Optional[int] = Query(None),
    current_user: User = Depends(require_institutional_staff),
    db: AsyncSession = Depends(get_async_session),
):
    """List institution-specific Arena assessments managed by TPO/Admin staff."""
    return await list_tpo_assessments(current_user=current_user, db=db, institution_id=institution_id)


@router.get(
    "/tpo/analytics",
    response_model=ArenaTpoAnalyticsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_tpo_analytics_endpoint(
    institution_id: Optional[int] = Query(None),
    current_user: User = Depends(require_institutional_staff),
    db: AsyncSession = Depends(get_async_session),
):
    """View aggregated, institution-scoped Arena test participation and category performance."""
    return await get_tpo_arena_analytics(current_user=current_user, db=db, institution_id=institution_id)


@router.get(
    "/tpo/students",
    response_model=ArenaTpoStudentRosterResponse,
    status_code=status.HTTP_200_OK,
)
async def get_tpo_student_roster_endpoint(
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    graduation_year: Optional[int] = Query(None, description="Filter by graduation year batch"),
    search: Optional[str] = Query(None, description="Search by student full name or roll number"),
    institution_id: Optional[int] = Query(None, description="Admin institution override"),
    current_user: User = Depends(require_institutional_staff),
    db: AsyncSession = Depends(get_async_session),
):
    """View individual student Arena assessment participation, attempts, and diagnostic statistics across the institution."""
    return await get_tpo_students_arena_roster(
        current_user=current_user,
        db=db,
        department_id=department_id,
        graduation_year=graduation_year,
        search=search,
        institution_id=institution_id,
    )


@router.get(
    "/tpo/students/{student_id}",
    response_model=ArenaPerformanceAnalytics,
    status_code=status.HTTP_200_OK,
)
async def get_tpo_student_detail_endpoint(
    student_id: int,
    institution_id: Optional[int] = Query(None, description="Admin institution override"),
    current_user: User = Depends(require_institutional_staff),
    db: AsyncSession = Depends(get_async_session),
):
    """View detailed Arena category proficiencies, weak topics, and attempt history for a specific student."""
    return await get_tpo_student_arena_detail(
        student_id=student_id,
        current_user=current_user,
        db=db,
        institution_id=institution_id,
    )

