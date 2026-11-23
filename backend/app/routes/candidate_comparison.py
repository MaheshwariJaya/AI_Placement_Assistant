"""FastAPI Routes for TASK 10: Candidate Comparison & Hiring Insights.

Provides endpoints for side-by-side comparative analysis of up to 5 candidates,
skill coverage matrices, evidence-grounded AI hiring insights,
and saved comparison sessions for recruiters.
"""
import logging
from typing import Annotated, Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.candidate_comparison import (
    CandidateComparisonRequest,
    CandidateComparisonResponse,
    ComparisonSessionCreateRequest,
    ComparisonSessionListResponse,
    ComparisonSessionResponse,
    ComparisonSessionUpdateRequest,
)
from app.services.candidate_comparison_service import (
    compare_candidates_for_job,
    delete_comparison_session,
    get_comparison_session,
    list_comparison_sessions,
    save_comparison_session,
    update_comparison_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recruiter/candidate-comparisons", tags=["Recruiter Candidate Comparison"])
require_recruiter_staff = require_roles(UserRole.RECRUITER, UserRole.ADMIN)


@router.post(
    "/compare",
    response_model=CandidateComparisonResponse,
    summary="Perform live side-by-side comparison of 2-5 candidates for a job",
)
async def compare_candidates_endpoint(
    payload: CandidateComparisonRequest,
    current_user: Annotated[User, Depends(require_recruiter_staff)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> CandidateComparisonResponse:
    """
    Compare up to 5 candidates side-by-side for a specific job posting.
    Validates company authorization, deterministic eligibility, compatibility scores,
    skill coverage, portfolio projects, and optional AI-assisted hiring insights.
    """
    return await compare_candidates_for_job(
        session=session,
        job_id=payload.job_id,
        application_ids=payload.application_ids,
        current_user=current_user,
        generate_ai_insights=payload.generate_ai_insights,
    )


@router.post(
    "/sessions",
    response_model=ComparisonSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a candidate comparison session with recruiter notes",
)
async def create_comparison_session_endpoint(
    payload: ComparisonSessionCreateRequest,
    current_user: Annotated[User, Depends(require_recruiter_staff)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ComparisonSessionResponse:
    """Save a recruiter candidate comparison session for collaborative deliberation."""
    return await save_comparison_session(
        session=session,
        job_id=payload.job_id,
        title=payload.title,
        application_ids=payload.application_ids,
        current_user=current_user,
        notes=payload.notes,
        include_ai_insights=payload.include_ai_insights,
    )


@router.get(
    "/sessions",
    response_model=ComparisonSessionListResponse,
    summary="List saved comparison sessions for recruiter's company",
)
async def list_comparison_sessions_endpoint(
    current_user: Annotated[User, Depends(require_recruiter_staff)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    job_id: Annotated[Optional[int], Query(description="Filter by specific job ID")] = None,
) -> ComparisonSessionListResponse:
    """Retrieve saved comparison sessions scoped to recruiter's corporate affiliation."""
    return await list_comparison_sessions(
        session=session,
        current_user=current_user,
        job_id=job_id,
    )


@router.get(
    "/sessions/{session_id}",
    summary="Get saved comparison session and live comparison payload",
)
async def get_comparison_session_endpoint(
    session_id: int,
    current_user: Annotated[User, Depends(require_recruiter_staff)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Dict[str, Any]:
    """Retrieve saved session details along with live refreshed comparison data."""
    sess_resp, comp_resp = await get_comparison_session(
        session=session,
        session_id=session_id,
        current_user=current_user,
    )
    return {
        "session": sess_resp,
        "comparison": comp_resp,
    }


@router.patch(
    "/sessions/{session_id}",
    response_model=ComparisonSessionResponse,
    summary="Update saved comparison session title or notes",
)
async def update_comparison_session_endpoint(
    session_id: int,
    payload: ComparisonSessionUpdateRequest,
    current_user: Annotated[User, Depends(require_recruiter_staff)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ComparisonSessionResponse:
    """Update title and/or notes for a saved comparison session."""
    return await update_comparison_session(
        session=session,
        session_id=session_id,
        current_user=current_user,
        title=payload.title,
        notes=payload.notes,
    )


@router.delete(
    "/sessions/{session_id}",
    summary="Delete a saved candidate comparison session",
)
async def delete_comparison_session_endpoint(
    session_id: int,
    current_user: Annotated[User, Depends(require_recruiter_staff)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Dict[str, Any]:
    """Delete a saved comparison session."""
    return await delete_comparison_session(
        session=session,
        session_id=session_id,
        current_user=current_user,
    )

