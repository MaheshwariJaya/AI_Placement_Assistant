"""Pydantic schemas for the Complete Interview Management Portal."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.placement import InterviewMode, InterviewOutcome, InterviewStatus


class InterviewPortalItemResponse(BaseModel):
    """Rich interview representation for Recruiters, Interviewers, TPOs, and Admins."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    round_number: int
    round_title: str
    interview_mode: InterviewMode
    meeting_link: Optional[str] = None
    location: Optional[str] = None
    scheduled_start_time: datetime
    duration_minutes: int
    interviewer_names: Optional[str] = None
    instructions: Optional[str] = None
    status: InterviewStatus
    outcome: InterviewOutcome
    feedback_notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    is_rescheduled: bool = False
    created_at: datetime
    updated_at: datetime

    # Candidate details
    student_id: int
    student_name: str
    student_email: str
    roll_number: str
    department: str
    graduation_year: int
    cgpa: float

    # Job & Company details
    job_id: int
    job_title: str
    company_id: int
    company_name: str

    # Placement Drive details
    drive_id: Optional[int] = None
    drive_name: Optional[str] = None

    # Evaluations summary
    evaluations_count: int = 0
    average_rating: Optional[float] = None


class InterviewListPortalResponse(BaseModel):
    """Paginated list of interviews."""
    items: List[InterviewPortalItemResponse]
    total: int
    page: int
    limit: int
    pages: int


class CalendarEventItem(BaseModel):
    """Calendar-optimized interview event."""
    id: int
    application_id: int
    round_title: str
    round_number: int
    scheduled_start_time: datetime
    duration_minutes: int
    status: InterviewStatus
    outcome: InterviewOutcome
    interview_mode: InterviewMode
    meeting_link: Optional[str] = None
    location: Optional[str] = None
    student_name: str
    roll_number: str
    job_title: str
    company_name: str
    is_rescheduled: bool = False


class InterviewCalendarDay(BaseModel):
    """Single calendar day bucket with events."""
    date: str  # YYYY-MM-DD
    events: List[CalendarEventItem]


class InterviewCalendarResponse(BaseModel):
    """Aggregated calendar response across requested period."""
    days: List[InterviewCalendarDay]
    total_events: int
    scheduled_count: int
    completed_count: int
    cancelled_count: int
    rescheduled_count: int


class InterviewRoundTemplate(BaseModel):
    """Pre-configured standard interview round template."""
    round_number: int
    round_title: str
    stage: str
    default_duration_minutes: int
    description: str


class InterviewWorkspaceDetailResponse(BaseModel):
    """Full detail for an interviewer evaluating a specific interview round."""
    interview: InterviewPortalItemResponse
    candidate_profile: Dict[str, Any]
    job: Dict[str, Any]
    past_rounds: List[InterviewPortalItemResponse]
    evaluations: List[Dict[str, Any]]
    allowed_next_actions: List[str]

