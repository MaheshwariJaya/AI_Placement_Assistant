import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import require_student
from app.core.errors import NotFoundError
from app.models.user import User
from app.schemas.resume_feedback import (
    ResumeFeedbackRequest,
    ResumeFeedbackResponse,
)
from app.services.resume_feedback_service import (
    generate_resume_feedback,
    get_latest_cached_feedback,
    list_eligible_jobs_for_feedback,
    get_and_validate_student_resume,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["AI Resume Feedback"])


@router.post(
    "/{resume_id}/feedback",
    response_model=ResumeFeedbackResponse,
    status_code=status.HTTP_200_OK,
)
async def request_resume_feedback(
    resume_id: int,
    req: ResumeFeedbackRequest,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Evaluates resume presentation, ATS structure, STAR impact, and job alignment.
    Strictly isolated from placement eligibility cutoffs.
    Bypasses AI provider and returns instantly when identical cache key exists.
    """
    return await generate_resume_feedback(
        resume_id=resume_id,
        job_id=req.job_id,
        force_refresh=req.force_refresh,
        current_user=current_user,
        db=db,
    )


@router.get(
    "/{resume_id}/feedback",
    response_model=ResumeFeedbackResponse,
    status_code=status.HTTP_200_OK,
)
async def get_resume_feedback(
    resume_id: int,
    job_id: Optional[int] = Query(None, description="Optional target job ID"),
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Retrieves the latest cached feedback evaluation report for a resume.
    Strictly scoped to the authenticated student accessing their own resume.
    """
    cached = await get_latest_cached_feedback(
        resume_id=resume_id,
        job_id=job_id,
        current_user=current_user,
        db=db,
    )
    if not cached:
        raise NotFoundError(
            "No cached evaluation report found for this resume and job selection. Please generate analysis first.",
            code="FEEDBACK_NOT_FOUND",
        )
    return cached


@router.get(
    "/{resume_id}/feedback/jobs",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def list_feedback_target_jobs(
    resume_id: int,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Lists active, published campus opportunities that the student can target for resume tailoring.
    """
    # Enforce resume ownership first
    await get_and_validate_student_resume(
        resume_id=resume_id,
        current_user=current_user,
        db=db,
    )

    return await list_eligible_jobs_for_feedback(
        current_user=current_user,
        db=db,
    )

