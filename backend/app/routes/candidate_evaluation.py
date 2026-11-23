"""
FastAPI Routes for TASK 08: Advanced Candidate Evaluation Workspace.
Provides recruiter candidate pipeline filtering, detailed evaluation dossiers,
structured multi-interviewer evaluations, candidate notes, hiring decisions, and AI synthesis.
"""
import logging
from typing import Annotated, Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import require_roles
from app.models.placement import ApplicationStatus
from app.models.user import User, UserRole
from app.schemas.candidate_evaluation import (
    CandidateAISummary,
    CandidateEvaluationCreate,
    CandidateEvaluationResponse,
    CandidateListResponse,
    CandidateNoteCreate,
    CandidateNoteResponse,
    CandidateStatusTransitionRequest,
    CandidateWorkspaceDetailResponse,
)
from app.services.candidate_evaluation_service import (
    create_candidate_note,
    delete_candidate_note,
    execute_candidate_status_transition,
    generate_candidate_ai_summary,
    get_candidate_workspace_detail,
    list_candidate_evaluations,
    list_candidate_notes,
    list_candidates_for_recruiter,
    submit_candidate_evaluation,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recruiter/candidates", tags=["Recruiter Candidate Workspace"])
require_recruiter_staff = require_roles(UserRole.RECRUITER, UserRole.ADMIN)


@router.get("", response_model=CandidateListResponse, summary="List and filter candidate applications in recruiter pipeline")
async def list_candidates_endpoint(
    job_id: Annotated[Optional[int], Query(description="Filter by specific job opportunity")] = None,
    department: Annotated[Optional[str], Query(description="Filter by candidate academic department")] = None,
    graduation_year: Annotated[Optional[int], Query(description="Filter by graduation batch year")] = None,
    eligibility: Annotated[Optional[str], Query(description="Filter: all | eligible_only | ineligible_only")] = None,
    min_compatibility_score: Annotated[Optional[float], Query(ge=0.0, le=100.0, description="Minimum compatibility score cutoff")] = None,
    skill: Annotated[Optional[str], Query(description="Filter candidates possessing skill")] = None,
    min_experience_months: Annotated[Optional[int], Query(description="Minimum experience in months")] = None,
    status_filter: Annotated[Optional[ApplicationStatus], Query(alias="status", description="Filter by recruitment stage")] = None,
    search: Annotated[Optional[str], Query(description="Search by student name, roll number, or job title")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    current_user: User = Depends(require_recruiter_staff),
    session: AsyncSession = Depends(get_async_session),
) -> CandidateListResponse:
    """Retrieve filtered, paginated candidate roster for recruiter's corporate opportunities."""
    return await list_candidates_for_recruiter(
        session=session,
        current_user=current_user,
        job_id=job_id,
        department=department,
        graduation_year=graduation_year,
        eligibility=eligibility,
        min_compatibility_score=min_compatibility_score,
        skill=skill,
        min_experience_months=min_experience_months,
        status=status_filter,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/{application_id}", response_model=CandidateWorkspaceDetailResponse, summary="Get comprehensive candidate evaluation dossier")
async def get_candidate_workspace_endpoint(
    application_id: int,
    current_user: User = Depends(require_recruiter_staff),
    session: AsyncSession = Depends(get_async_session),
) -> CandidateWorkspaceDetailResponse:
    """Fetch complete candidate dossier including verified academics, skills, projects, deterministic compatibility, checklist, timeline, and evaluations."""
    return await get_candidate_workspace_detail(
        session=session,
        application_id=application_id,
        current_user=current_user,
    )


@router.post("/{application_id}/evaluations", response_model=CandidateEvaluationResponse, status_code=status.HTTP_201_CREATED, summary="Submit structured interview evaluation")
async def submit_candidate_evaluation_endpoint(
    application_id: int,
    payload: CandidateEvaluationCreate,
    current_user: User = Depends(require_recruiter_staff),
    session: AsyncSession = Depends(get_async_session),
) -> CandidateEvaluationResponse:
    """Submit a structured evaluation form with ratings, rubric, written feedback, and hiring recommendation."""
    return await submit_candidate_evaluation(
        session=session,
        application_id=application_id,
        payload=payload,
        current_user=current_user,
    )


@router.get("/{application_id}/evaluations", response_model=List[CandidateEvaluationResponse], summary="List all evaluations for candidate")
async def list_candidate_evaluations_endpoint(
    application_id: int,
    current_user: User = Depends(require_recruiter_staff),
    session: AsyncSession = Depends(get_async_session),
) -> List[CandidateEvaluationResponse]:
    """Retrieve all structured interviewer evaluation records submitted for this candidate."""
    return await list_candidate_evaluations(
        session=session,
        application_id=application_id,
        current_user=current_user,
    )


@router.post("/{application_id}/notes", response_model=CandidateNoteResponse, status_code=status.HTTP_201_CREATED, summary="Create confidential internal note")
async def create_candidate_note_endpoint(
    application_id: int,
    payload: CandidateNoteCreate,
    current_user: User = Depends(require_recruiter_staff),
    session: AsyncSession = Depends(get_async_session),
) -> CandidateNoteResponse:
    """Add an internal recruiter annotation/note confidential to corporate hiring team."""
    return await create_candidate_note(
        session=session,
        application_id=application_id,
        payload=payload,
        current_user=current_user,
    )


@router.get("/{application_id}/notes", response_model=List[CandidateNoteResponse], summary="List internal candidate notes")
async def list_candidate_notes_endpoint(
    application_id: int,
    current_user: User = Depends(require_recruiter_staff),
    session: AsyncSession = Depends(get_async_session),
) -> List[CandidateNoteResponse]:
    """Retrieve all confidential internal notes for this candidate application."""
    return await list_candidate_notes(
        session=session,
        application_id=application_id,
        current_user=current_user,
    )


@router.delete("/{application_id}/notes/{note_id}", summary="Delete internal candidate note")
async def delete_candidate_note_endpoint(
    application_id: int,
    note_id: int,
    current_user: User = Depends(require_recruiter_staff),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """Delete an internal candidate note (author or admin only)."""
    return await delete_candidate_note(
        session=session,
        application_id=application_id,
        note_id=note_id,
        current_user=current_user,
    )


@router.post("/{application_id}/status", summary="Execute documented human recruitment lifecycle transition")
async def execute_status_transition_endpoint(
    application_id: int,
    payload: CandidateStatusTransitionRequest,
    current_user: User = Depends(require_recruiter_staff),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """Shortlist, reject, schedule interview, or release offer with documented human approval and TPO screening enforcement."""
    return await execute_candidate_status_transition(
        session=session,
        application_id=application_id,
        payload=payload,
        current_user=current_user,
    )


@router.post("/{application_id}/ai-summary", response_model=CandidateAISummary, summary="Generate evidence-grounded AI evaluation summary")
async def generate_ai_summary_endpoint(
    application_id: int,
    current_user: User = Depends(require_recruiter_staff),
    session: AsyncSession = Depends(get_async_session),
) -> CandidateAISummary:
    """Generate an evidence-grounded candidate evaluation synthesis strictly separating verified facts, calculated metrics, and AI observations."""
    return await generate_candidate_ai_summary(
        session=session,
        application_id=application_id,
        current_user=current_user,
    )

