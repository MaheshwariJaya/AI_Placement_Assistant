from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.placement import (
    ApplicationStatus,
    DecisionDomain,
    DriveActivityStatus,
    DriveActivityType,
    DriveAttendanceStatus,
    DriveLifecyclePhase,
    DriveMode,
    DriveRegistrationStatus,
    DriveStatus,
    InterviewMode,
    InterviewOutcome,
    InterviewStatus,
    NotificationCategory,
    TpoScreeningStatus,
)


# =============================================================================
# Placement Drive Schemas
# =============================================================================

class PlacementDriveCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=200, description="Drive title e.g. 'Campus Placement Drive 2026'")
    academic_year: str = Field(..., min_length=4, max_length=20, description="Academic year e.g. '2025-2026'")
    target_graduation_year: int = Field(..., ge=2020, le=2040, description="Target graduating batch e.g. 2026")
    registration_start_date: datetime = Field(..., description="Drive registration window start")
    registration_end_date: datetime = Field(..., description="Drive registration window close")
    drive_mode: DriveMode = Field(DriveMode.ON_CAMPUS, description="on_campus, virtual, hybrid")
    description: Optional[str] = Field(None, max_length=5000, description="Drive overview, instructions, and schedule")
    guidelines: Optional[str] = Field(None, max_length=5000, description="Institutional conduct rules and eligibility guidelines")
    lifecycle_phase: Optional[DriveLifecyclePhase] = Field(None, description="Initial lifecycle phase (defaults to draft)")
    drive_start_date: Optional[datetime] = Field(None, description="Scheduled start of drive activities")
    drive_end_date: Optional[datetime] = Field(None, description="Scheduled completion of drive activities")
    venue_location: Optional[str] = Field(None, max_length=255, description="Campus auditorium/venue or online platform")
    instructions: Optional[str] = Field(None, max_length=5000, description="Student participation instructions")
    required_documents: List[str] = Field(default_factory=list, description="Documents required during drive")
    target_graduation_batches: List[int] = Field(default_factory=list, description="Multiple target graduation years")
    participating_company_ids: List[int] = Field(default_factory=list, description="Pre-selected participating companies")
    eligible_department_ids: List[int] = Field(default_factory=list, description="Eligible institutional departments")
    job_ids: List[int] = Field(default_factory=list, description="Initial published/eligible jobs to associate")

    @model_validator(mode="after")
    def validate_date_window(self) -> "PlacementDriveCreate":
        if self.registration_start_date >= self.registration_end_date:
            raise ValueError("registration_start_date must be strictly earlier than registration_end_date")
        if self.drive_start_date and self.drive_end_date and self.drive_start_date >= self.drive_end_date:
            raise ValueError("drive_start_date must be strictly earlier than drive_end_date")
        return self


class PlacementDriveUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    academic_year: Optional[str] = Field(None, min_length=4, max_length=20)
    target_graduation_year: Optional[int] = Field(None, ge=2020, le=2040)
    registration_start_date: Optional[datetime] = None
    registration_end_date: Optional[datetime] = None
    drive_mode: Optional[DriveMode] = None
    status: Optional[DriveStatus] = None
    lifecycle_phase: Optional[DriveLifecyclePhase] = None
    description: Optional[str] = Field(None, max_length=5000)
    guidelines: Optional[str] = Field(None, max_length=5000)
    drive_start_date: Optional[datetime] = None
    drive_end_date: Optional[datetime] = None
    venue_location: Optional[str] = Field(None, max_length=255)
    instructions: Optional[str] = Field(None, max_length=5000)
    required_documents: Optional[List[str]] = None
    target_graduation_batches: Optional[List[int]] = None
    participating_company_ids: Optional[List[int]] = None
    eligible_department_ids: Optional[List[int]] = None
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def validate_date_window(self) -> "PlacementDriveUpdate":
        if (
            self.registration_start_date is not None
            and self.registration_end_date is not None
            and self.registration_start_date >= self.registration_end_date
        ):
            raise ValueError("registration_start_date must be strictly earlier than registration_end_date")
        if (
            self.drive_start_date is not None
            and self.drive_end_date is not None
            and self.drive_start_date >= self.drive_end_date
        ):
            raise ValueError("drive_start_date must be strictly earlier than drive_end_date")
        return self


class PlacementDriveJobAddRequest(BaseModel):
    job_id: int = Field(..., description="Authorized Job ID to associate with this placement drive")


class PlacementDriveJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    drive_id: int
    job_id: int
    is_active: bool
    removed_at: Optional[datetime] = None
    created_at: datetime

    # Denormalized job details for display
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    employment_type: Optional[str] = None
    location: Optional[str] = None


class PlacementDriveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    institution_id: int
    created_by_user_id: int
    name: str
    academic_year: str
    target_graduation_year: int
    registration_start_date: datetime
    registration_end_date: datetime
    drive_mode: DriveMode
    status: DriveStatus
    description: Optional[str] = None
    guidelines: Optional[str] = None
    lifecycle_phase: DriveLifecyclePhase = DriveLifecyclePhase.DRAFT
    drive_start_date: Optional[datetime] = None
    drive_end_date: Optional[datetime] = None
    venue_location: Optional[str] = None
    instructions: Optional[str] = None
    required_documents: List[str] = Field(default_factory=list)
    target_graduation_batches: List[int] = Field(default_factory=list)
    participating_company_ids: List[int] = Field(default_factory=list)
    eligible_department_ids: List[int] = Field(default_factory=list)
    is_active: bool
    created_at: datetime
    updated_at: datetime
    total_jobs: int = 0
    total_applications: int = 0


class PlacementDriveDetailResponse(PlacementDriveResponse):
    jobs: List[PlacementDriveJobResponse] = []


# =============================================================================
# Job Application Schemas
# =============================================================================

class JobApplicationCreate(BaseModel):
    job_id: int = Field(..., description="ID of the job posting being applied to")
    resume_id: int = Field(..., description="ID of the student's active resume to attach")
    drive_id: Optional[int] = Field(None, description="Drive ID if applying through a campus placement drive")
    cover_letter: Optional[str] = Field(None, max_length=3000, description="Optional applicant statement")


class ApplicationStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    changed_by_user_id: int
    created_at: datetime
    decision_domain: DecisionDomain
    from_status: Optional[str] = None
    to_status: str
    notes: Optional[str] = None


class TpoScreeningUpdateRequest(BaseModel):
    status: TpoScreeningStatus = Field(..., description="Must be 'shortlisted' or 'rejected'")
    feedback: Optional[str] = Field(None, max_length=1000, description="Optional reasoning for the TPO screening decision")

    @field_validator("status")
    @classmethod
    def validate_screening_decision(cls, v: TpoScreeningStatus) -> TpoScreeningStatus:
        if v not in (TpoScreeningStatus.SHORTLISTED, TpoScreeningStatus.REJECTED):
            raise ValueError("TPO screening decision must be either 'shortlisted' or 'rejected'")
        return v


class RecruiterStatusUpdateRequest(BaseModel):
    status: ApplicationStatus = Field(..., description="Target pipeline lifecycle stage")
    feedback_notes: Optional[str] = Field(None, max_length=2000, description="Internal recruiter evaluation notes")
    offer_deadline_at: Optional[datetime] = Field(None, description="Optional offer acceptance deadline when moving to offered")
    offer_package_lpa: Optional[float] = Field(None, gt=0, le=500, description="Optional offered compensation in LPA")
    offer_notes: Optional[str] = Field(None, max_length=1500, description="Optional candidate-visible offer terms or summary")


class ApplicationWithdrawRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500, description="Mandatory reason explaining candidate withdrawal")


class OfferResponseRequest(BaseModel):
    accept: bool = Field(..., description="True to accept the job offer; False to decline")
    notes: Optional[str] = Field(None, max_length=500, description="Optional remarks from student")


class JobApplicationResponse(BaseModel):
    """Standard student/public application response - redact confidential recruiter notes."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    student_id: int
    resume_id: int
    drive_id: Optional[int] = None
    tpo_screening_status: TpoScreeningStatus
    tpo_screened_by_user_id: Optional[int] = None
    tpo_screened_at: Optional[datetime] = None
    tpo_feedback: Optional[str] = None
    current_status: ApplicationStatus
    recruiter_decision_at: Optional[datetime] = None
    compatibility_score_at_application: float
    cover_letter: Optional[str] = None
    withdrawn_at: Optional[datetime] = None
    withdrawal_reason: Optional[str] = None
    offer_deadline_at: Optional[datetime] = None
    offer_package_lpa: Optional[float] = None
    offer_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Display enrichment
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    drive_name: Optional[str] = None
    application_deadline: Optional[datetime] = None
    job_location: Optional[str] = None
    work_mode: Optional[str] = None
    employment_type: Optional[str] = None
    salary_range: Optional[str] = None
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    student_roll_number: Optional[str] = None
    student_department: Optional[str] = None


class JobApplicationRecruiterResponse(JobApplicationResponse):
    """Recruiter/TPO-authorized view including confidential evaluation feedback."""
    recruiter_feedback_notes: Optional[str] = None


class JobApplicationListResponse(BaseModel):
    items: List[JobApplicationResponse]
    total: int


# =============================================================================
# Interview Schemas
# =============================================================================

class InterviewCreateRequest(BaseModel):
    round_number: int = Field(..., ge=1, le=20, description="Positive round sequence index (1, 2, 3...)")
    round_title: str = Field(..., min_length=2, max_length=100, description="e.g. 'Technical Round 1', 'Managerial Fitment'")
    interview_mode: InterviewMode = Field(InterviewMode.VIRTUAL, description="virtual or in_person")
    meeting_link: Optional[str] = Field(None, max_length=500, description="Web conference link (Zoom, Meet, Teams)")
    location: Optional[str] = Field(None, max_length=200, description="Physical room / venue for in-person interviews")
    scheduled_start_time: datetime = Field(..., description="Scheduled start timestamp")
    duration_minutes: int = Field(45, ge=15, le=240, description="Interview duration in minutes (15 to 240)")
    interviewer_names: Optional[str] = Field(None, max_length=255, description="Interviewer names or panel description")
    instructions: Optional[str] = Field(None, max_length=1500, description="Candidate preparation notes or reporting instructions")


class InterviewRescheduleRequest(BaseModel):
    scheduled_start_time: datetime = Field(..., description="New interview start timestamp")
    duration_minutes: Optional[int] = Field(None, ge=15, le=240)
    meeting_link: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=200)
    instructions: Optional[str] = Field(None, max_length=1500)
    reason: str = Field(..., min_length=5, max_length=500, description="Mandatory audit justification for rescheduling")


class InterviewCancelRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500, description="Mandatory audit justification for cancelling interview round")


class InterviewOutcomeRequest(BaseModel):
    outcome: InterviewOutcome = Field(..., description="passed, failed, or on_hold")
    feedback_notes: Optional[str] = Field(None, max_length=2000, description="Confidential evaluation feedback")
    cancellation_reason: Optional[str] = Field(None, max_length=500, description="Required when cancelling round")


class InterviewResponse(BaseModel):
    """Full interviewer / recruiter view including confidential feedback notes."""
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
    created_by_user_id: int
    cancellation_reason: Optional[str] = None
    is_rescheduled: bool = False
    created_at: datetime
    updated_at: datetime


class InterviewStudentResponse(BaseModel):
    """Redacted student view - confidential feedback notes and internal IDs omitted."""
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
    cancellation_reason: Optional[str] = None
    is_rescheduled: bool = False
    created_at: datetime
    updated_at: datetime


class JobApplicationDetailResponse(JobApplicationRecruiterResponse):
    """Complete recruiter/admin lifecycle detail including history and scheduled rounds with confidential notes."""
    status_history: List[ApplicationStatusHistoryResponse] = []
    interviews: List[InterviewResponse] = []


class JobApplicationTpoDetailResponse(JobApplicationResponse):
    """Institutional TPO view with screening details, academic profile, and interview schedule, without confidential recruiter evaluation notes."""
    status_history: List[ApplicationStatusHistoryResponse] = []
    interviews: List[InterviewStudentResponse] = []


class JobApplicationStudentDetailResponse(JobApplicationResponse):
    """Complete student view including status history and redacted interview schedule."""
    status_history: List[ApplicationStatusHistoryResponse] = []
    interviews: List[InterviewStudentResponse] = []


# =============================================================================
# Notification Schemas
# =============================================================================

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_user_id: int
    sender_user_id: Optional[int] = None
    category: NotificationCategory
    title: str
    message: str
    related_application_id: Optional[int] = None
    related_drive_id: Optional[int] = None
    related_interview_id: Optional[int] = None
    is_read: bool
    read_at: Optional[datetime] = None
    idempotency_key: Optional[str] = None
    created_at: datetime


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int


# =============================================================================
# TPO Command Center & Admin Analytics Schemas
# =============================================================================

class DepartmentPlacementStat(BaseModel):
    name: str = Field(..., description="Branch code e.g. CSE, IT")
    dept_name: str = Field(..., description="Full department name")
    total: int = Field(..., description="Total students in department")
    placed: float = Field(..., description="Placement rate percentage for Recharts")
    placed_count: int = Field(..., description="Raw count of placed students")


class TpoOverviewResponse(BaseModel):
    total_cohort: int
    target_batch: str
    available_batches: List[int] = []
    placed_students: int
    placement_rate: float
    active_drives: int
    published_jobs: int = 0
    visiting_this_week: int
    average_package_lpa: float
    highest_package_lpa: float
    top_open_ctc_lpa: float = 0.0
    department_stats: List[DepartmentPlacementStat]


class RecruiterOverviewResponse(BaseModel):
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    active_jobs_count: int
    total_applicants: int
    shortlisted_count: int
    offers_released: int
    offers_accepted: int
    recent_applications: List[JobApplicationRecruiterResponse] = []


class SimulatedStudentSummary(BaseModel):
    student_id: int
    name: str
    email: str
    roll_number: str
    department: str
    graduation_year: int
    cgpa: float
    active_backlogs: int
    skills: List[str] = []


class EligibilitySimulationRequest(BaseModel):
    target_batch: Optional[int] = Field(None, description="Graduation year e.g. 2026")
    min_cgpa: float = Field(7.5, ge=0.0, le=10.0, description="Minimum CGPA cutoff")
    max_active_backlogs: int = Field(0, ge=0, description="Maximum allowed active backlogs")
    max_total_backlogs: Optional[int] = Field(None, ge=0, description="Maximum allowed total backlogs")
    department_codes: Optional[List[str]] = Field(None, description="List of branch codes e.g. ['CSE', 'IT', 'ECE']")


class EligibilitySimulationResponse(BaseModel):
    eligible_count: int
    total_cohort_count: int
    eligible_percentage: float
    criteria_summary: Dict[str, Any]
    matching_students: List[SimulatedStudentSummary]


class UserRoleCount(BaseModel):
    role: str
    count: int
    percentage: float


class AdminOverviewResponse(BaseModel):
    total_users: int
    role_distribution: List[UserRoleCount]
    students_count: int
    recruiters_count: int
    tpos_count: int
    admins_count: int
    institutions_count: int
    departments_count: int
    companies_count: int
    jobs_count: int
    drives_count: int
    applications_count: int


class TpoStudentRosterItem(BaseModel):
    student_id: int
    user_id: int
    full_name: str
    email: str
    roll_number: str
    department_id: Optional[int] = None
    department_code: str
    department_name: str
    is_branch_verified: bool = True
    graduation_year: int
    cgpa: float
    active_backlogs: int
    total_backlogs: int
    is_placement_ready: bool
    skills: List[str] = []
    approved_resumes_count: int = 0
    applications_count: int = 0
    placement_status: str
    offer_state: str
    hired_company: Optional[str] = None
    hired_role: Optional[str] = None
    hired_ctc_lpa: Optional[float] = None
    active_pipeline_roles: List[str] = []


class TpoStudentRosterResponse(BaseModel):
    total_students: int
    hired_count: int
    offer_accepted_count: int
    offer_pending_count: int
    in_pipeline_count: int
    not_hired_count: int
    unverified_count: int = 0
    students: List[TpoStudentRosterItem] = []


# =============================================================================
# Smart Application & Recruitment Tracker Schemas (TASK 03)
# =============================================================================

class NotificationPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    interview_schedules: bool = True
    upcoming_interview_reminders: bool = True
    status_changes: bool = True
    offer_alerts: bool = True
    offer_deadline_reminders: bool = True
    placement_announcements: bool = True
    reminder_hours_before: int = 24
    updated_at: Optional[datetime] = None


class NotificationPreferenceUpdate(BaseModel):
    interview_schedules: Optional[bool] = None
    upcoming_interview_reminders: Optional[bool] = None
    status_changes: Optional[bool] = None
    offer_alerts: Optional[bool] = None
    offer_deadline_reminders: Optional[bool] = None
    placement_announcements: Optional[bool] = None
    reminder_hours_before: Optional[int] = Field(None, ge=1, le=168)


class NotificationSyncResponse(BaseModel):
    generated_count: int
    notifications: List[NotificationResponse]


class TrackerNextActivitySchema(BaseModel):
    activity_type: Literal["interview", "offer_deadline", "application_review", "tpo_screening", "completed"]
    title: str
    scheduled_at: Optional[datetime] = None
    description: Optional[str] = None
    interview_id: Optional[int] = None
    meeting_link: Optional[str] = None
    location: Optional[str] = None


class TrackerLatestUpdateSchema(BaseModel):
    title: str
    description: Optional[str] = None
    timestamp: datetime
    domain: Optional[DecisionDomain] = None
    from_status: Optional[str] = None
    to_status: Optional[str] = None


class TrackerOfferDetailSchema(BaseModel):
    company_name: str
    role_title: str
    package_lpa: Optional[float] = None
    salary_range: Optional[str] = None
    response_deadline: Optional[datetime] = None
    status: ApplicationStatus
    offer_notes: Optional[str] = None
    can_respond: bool = False


class TrackerApplicationItemSchema(JobApplicationStudentDetailResponse):
    latest_update: TrackerLatestUpdateSchema
    next_scheduled_activity: TrackerNextActivitySchema
    offer_details: Optional[TrackerOfferDetailSchema] = None
    upcoming_interviews_count: int = 0
    completed_interviews_count: int = 0


class TrackerSummaryStatsSchema(BaseModel):
    total_applications: int
    active_count: int
    upcoming_interviews_count: int
    completed_interviews_count: int
    pending_offers_count: int
    accepted_offers_count: int
    rejected_or_withdrawn_count: int


class ApplicationTrackerResponse(BaseModel):
    items: List[TrackerApplicationItemSchema]
    total: int
    skip: int
    limit: int
    summary: TrackerSummaryStatsSchema
    unread_notifications_count: int = 0


class StudentInterviewTrackingItem(InterviewStudentResponse):
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    drive_name: Optional[str] = None
    application_status: ApplicationStatus
    is_upcoming: bool = False
    reschedule_note: Optional[str] = None


class StudentInterviewListResponse(BaseModel):
    upcoming: List[StudentInterviewTrackingItem]
    completed: List[StudentInterviewTrackingItem]
    cancelled_or_other: List[StudentInterviewTrackingItem]
    total: int


class TrackerCalendarEvent(BaseModel):
    event_id: str
    event_type: Literal["interview", "application_deadline", "offer_deadline", "drive_registration"]
    title: str
    subtitle: Optional[str] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    application_id: Optional[int] = None
    interview_id: Optional[int] = None
    drive_id: Optional[int] = None
    start_at: datetime
    end_at: Optional[datetime] = None
    status: str
    meeting_link: Optional[str] = None
    location: Optional[str] = None
    instructions: Optional[str] = None
    is_rescheduled: bool = False


class TrackerCalendarResponse(BaseModel):
    events: List[TrackerCalendarEvent]
    total: int


