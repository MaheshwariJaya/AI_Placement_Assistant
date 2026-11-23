"""FastAPI routes for Placement Readiness Prediction & Institutional Analytics."""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import require_institutional_staff, require_student
from app.models.readiness import ReadinessCategory
from app.models.user import User
from app.schemas.readiness import (
    JobReadinessCheckRequest,
    JobReadinessCheckResponse,
    ReadinessCalculateRequest,
    ReadinessHistoryResponse,
    ReadinessSnapshotResponse,
    RecommendationToggleRequest,
    TpoReadinessAnalyticsResponse,
)
from app.services.readiness_service import (
    calculate_and_save_readiness_snapshot,
    evaluate_job_specific_readiness,
    get_student_readiness_history,
    get_student_readiness_overview,
    get_tpo_readiness_analytics,
    toggle_recommendation_completion,
)

router = APIRouter(prefix="/readiness", tags=["Placement Readiness Intelligence"])


@router.get(
    "/me",
    response_model=ReadinessSnapshotResponse,
    status_code=status.HTTP_200_OK,
)
async def get_my_readiness_overview(
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Retrieve the student's latest placement readiness index, transparent breakdown, and criteria."""
    return await get_student_readiness_overview(current_user=current_user, db=db)


@router.post(
    "/calculate",
    response_model=ReadinessSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
async def calculate_my_readiness(
    req: ReadinessCalculateRequest,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Recalculate and persist a new versioned readiness snapshot (supports custom indicator weights)."""
    return await calculate_and_save_readiness_snapshot(req=req, current_user=current_user, db=db)


@router.get(
    "/history",
    response_model=ReadinessHistoryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_my_readiness_history(
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Retrieve historical readiness snapshots, score trends, completed actions, and remaining skill gaps."""
    return await get_student_readiness_history(current_user=current_user, db=db)


@router.post(
    "/job-check",
    response_model=JobReadinessCheckResponse,
    status_code=status.HTTP_200_OK,
)
async def check_job_specific_readiness(
    req: JobReadinessCheckRequest,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Analyze job/role readiness gaps alongside separate deterministic academic eligibility."""
    return await evaluate_job_specific_readiness(req=req, current_user=current_user, db=db)


@router.patch(
    "/snapshots/{snapshot_id}/recommendations/{recommendation_id}",
    response_model=ReadinessSnapshotResponse,
    status_code=status.HTTP_200_OK,
)
async def update_recommendation_status(
    snapshot_id: int,
    recommendation_id: str,
    req: RecommendationToggleRequest,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Mark a personalized recommendation item completed or pending on a student's readiness snapshot."""
    return await toggle_recommendation_completion(
        snapshot_id=snapshot_id,
        recommendation_id=recommendation_id,
        completed=req.completed,
        current_user=current_user,
        db=db,
    )


@router.get(
    "/tpo/analytics",
    response_model=TpoReadinessAnalyticsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_institutional_tpo_readiness_analytics(
    department_id: Optional[int] = Query(None),
    graduation_year: Optional[int] = Query(None),
    category: Optional[ReadinessCategory] = Query(None),
    skill_category: Optional[str] = Query(None),
    current_user: User = Depends(require_institutional_staff),
    db: AsyncSession = Depends(get_async_session),
):
    """Retrieve institutional aggregated readiness statistics filtered by department, batch, category, and skill category."""
    return await get_tpo_readiness_analytics(
        current_user=current_user,
        db=db,
        department_id=department_id,
        graduation_year=graduation_year,
        category=category,
        skill_category=skill_category,
    )

