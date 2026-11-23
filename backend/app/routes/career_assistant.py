import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import require_student
from app.models.user import User
from app.schemas.career_assistant import (
    CareerAssistantChatRequest,
    CareerAssistantResponse,
    CareerContextSummary,
    CareerPromptSuggestion,
)
from app.services.career_assistant_service import (
    assemble_career_context,
    get_default_prompt_suggestions,
    process_career_assistant_chat,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/career-assistant", tags=["AI Career Assistant"])


@router.post("/chat", response_model=CareerAssistantResponse, status_code=status.HTTP_200_OK)
async def chat_with_career_assistant(
    req: CareerAssistantChatRequest,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Interactive AI Career Assistant chat endpoint for enrolled students.
    Grounds guidance strictly in the authenticated student's verified profile,
    skills, projects, experiences, and deterministic placement intelligence scores.
    """
    return await process_career_assistant_chat(
        req=req,
        current_user=current_user,
        db=db,
    )


@router.get("/prompts", response_model=List[CareerPromptSuggestion])
async def get_career_prompt_suggestions(
    job_id: Optional[int] = Query(None, description="Optional target job ID"),
    current_user: User = Depends(require_student),
):
    """Returns curated starter prompts for placement students."""
    return get_default_prompt_suggestions(has_job_context=job_id is not None)


@router.get("/context", response_model=CareerContextSummary)
async def get_student_career_context(
    job_id: Optional[int] = Query(None, description="Optional target job ID"),
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Retrieves a sanitized snapshot of student portfolio data and job context."""
    summary, _ = await assemble_career_context(
        current_user=current_user,
        job_id=job_id,
        db=db,
    )
    return summary

