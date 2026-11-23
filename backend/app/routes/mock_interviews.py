"""FastAPI routes for AI Mock Interview & Assessment Studio (Student Practice Portal)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import require_student
from app.models.mock_interview import MockInterviewCategory, MockInterviewStatus
from app.models.user import User
from app.schemas.mock_interview import (
    MockInterviewAnalyticsResponse,
    MockInterviewAnswerSubmitRequest,
    MockInterviewCreateRequest,
    MockInterviewSessionDetail,
    MockInterviewSessionSummary,
    MockInterviewTargetJob,
    MockInterviewTimerSyncRequest,
    SubmitMockAnswerResponse,
)
from app.services.mock_interview_service import (
    complete_mock_interview_session,
    create_mock_interview_session,
    get_mock_interview_analytics,
    get_mock_interview_session_detail,
    list_mock_interview_sessions,
    list_mock_interview_target_jobs,
    pause_mock_interview_session,
    resume_mock_interview_session,
    submit_mock_interview_answer,
)

router = APIRouter(prefix="/mock-interviews", tags=["AI Mock Interview Studio"])


@router.get(
    "/target-jobs",
    response_model=List[MockInterviewTargetJob],
    status_code=status.HTTP_200_OK,
)
async def get_target_jobs_for_mock_interview(
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """List active, published job postings visible to the student for tailored mock interviews."""
    return await list_mock_interview_target_jobs(current_user=current_user, db=db)


@router.get(
    "/analytics",
    response_model=MockInterviewAnalyticsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_student_mock_interview_analytics(
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Retrieve practice history KPIs, score improvement trends, and 7-criteria analytics."""
    return await get_mock_interview_analytics(current_user=current_user, db=db)


@router.get(
    "",
    response_model=List[MockInterviewSessionSummary],
    status_code=status.HTTP_200_OK,
)
async def list_my_mock_interviews(
    category: Optional[MockInterviewCategory] = Query(None),
    status_filter: Optional[MockInterviewStatus] = Query(None, alias="status"),
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """List the authenticated student's mock interview sessions with attempt score deltas."""
    return await list_mock_interview_sessions(
        current_user=current_user,
        db=db,
        category=category,
        status_filter=status_filter,
    )


@router.post(
    "",
    response_model=MockInterviewSessionDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_mock_interview(
    req: MockInterviewCreateRequest,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a tailored AI mock interview grounded in verified student portfolio and optional job posting."""
    return await create_mock_interview_session(req=req, current_user=current_user, db=db)


@router.get(
    "/{session_id}",
    response_model=MockInterviewSessionDetail,
    status_code=status.HTTP_200_OK,
)
async def get_mock_interview_session(
    session_id: int,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Fetch a single mock interview session with Q&A history and evaluation report."""
    return await get_mock_interview_session_detail(session_id=session_id, current_user=current_user, db=db)


@router.post(
    "/{session_id}/answers",
    response_model=SubmitMockAnswerResponse,
    status_code=status.HTTP_200_OK,
)
async def submit_mock_answer(
    session_id: int,
    req: MockInterviewAnswerSubmitRequest,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Submit an answer for a question and optionally generate a targeted follow-up question."""
    return await submit_mock_interview_answer(
        session_id=session_id,
        question_id=req.question_id,
        answer_text=req.answer_text or "",
        selected_option_key=req.selected_option_key,
        input_mode=req.input_mode,
        response_time_seconds=req.response_time_seconds,
        elapsed_seconds=req.elapsed_seconds,
        current_user=current_user,
        db=db,
    )


@router.post(
    "/{session_id}/pause",
    response_model=MockInterviewSessionDetail,
    status_code=status.HTTP_200_OK,
)
async def pause_mock_interview(
    session_id: int,
    req: MockInterviewTimerSyncRequest,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Pause an active mock interview session and save elapsed timer progress."""
    return await pause_mock_interview_session(
        session_id=session_id,
        elapsed_seconds=req.elapsed_seconds,
        current_user=current_user,
        db=db,
    )


@router.post(
    "/{session_id}/resume",
    response_model=MockInterviewSessionDetail,
    status_code=status.HTTP_200_OK,
)
async def resume_mock_interview(
    session_id: int,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Resume a previously paused mock interview session."""
    return await resume_mock_interview_session(session_id=session_id, current_user=current_user, db=db)


@router.post(
    "/{session_id}/complete",
    response_model=MockInterviewSessionDetail,
    status_code=status.HTTP_200_OK,
)
async def complete_mock_interview(
    session_id: int,
    req: Optional[MockInterviewTimerSyncRequest] = None,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Finish a mock interview (all answered or ended early) and generate structured 7-criteria evaluation."""
    elapsed = req.elapsed_seconds if req is not None else None
    return await complete_mock_interview_session(
        session_id=session_id,
        elapsed_seconds=elapsed,
        current_user=current_user,
        db=db,
    )
