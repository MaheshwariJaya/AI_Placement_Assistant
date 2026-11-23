"""Pydantic schemas for TASK 06: Complete Placement Drive Management Workspace."""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.placement import (
    DriveActivityStatus,
    DriveActivityType,
    DriveAttendanceStatus,
    DriveLifecyclePhase,
    DriveMode,
    DriveRegistrationStatus,
)


class DriveTransitionRequest(BaseModel):
    target_phase: DriveLifecyclePhase = Field(..., description="Target 7-stage lifecycle phase")
    reason: Optional[str] = Field(None, max_length=500, description="Optional transition notes")


class DriveFormCompanyOption(BaseModel):
    id: int
    name: str
    industry: str
    is_verified: bool
    institution_id: Optional[int] = None


class DriveFormJobOption(BaseModel):
    id: int
    company_id: int
    company_name: str
    title: str
    employment_type: str
    status: str
    location: str
    min_cgpa: float
    target_graduation_year: Optional[int] = None
    application_deadline: datetime
    eligible_department_ids: List[int] = Field(default_factory=list)


class DriveFormDepartmentOption(BaseModel):
    id: int
    code: str
    name: str


class DriveFormCoordinatorOption(BaseModel):
    id: int
    full_name: str
    email: str
    role: str


class DriveFormOptionsResponse(BaseModel):
    institution_id: int
    companies: List[DriveFormCompanyOption] = Field(default_factory=list)
    jobs: List[DriveFormJobOption] = Field(default_factory=list)
    departments: List[DriveFormDepartmentOption] = Field(default_factory=list)
    coordinators: List[DriveFormCoordinatorOption] = Field(default_factory=list)
    graduation_batches: List[int] = Field(default_factory=list)


class DriveDashboardJobBreakdown(BaseModel):
    job_id: int
    title: str
    company_name: str
    applications_count: int = 0
    shortlisted_count: int = 0
    interview_count: int = 0
    offered_count: int = 0
    accepted_count: int = 0


class DriveDashboardResponse(BaseModel):
    drive_id: int
    drive_name: str
    institution_id: int
    academic_year: str
    lifecycle_phase: DriveLifecyclePhase
    allowed_next_phases: List[DriveLifecyclePhase] = Field(default_factory=list)
    total_registered_students: int = 0
    eligible_students: int = 0
    ineligible_students: int = 0
    applications_received: int = 0
    shortlisted_candidates: int = 0
    interview_scheduled_count: int = 0
    interview_completed_count: int = 0
    offers_released: int = 0
    final_placements: int = 0
    activities_total: int = 0
    activities_completed: int = 0
    announcements_count: int = 0
    job_breakdown: List[DriveDashboardJobBreakdown] = Field(default_factory=list)


class DriveRegisterRequest(BaseModel):
    student_ids: Optional[List[int]] = Field(
        None,
        description="StudentProfile IDs for TPO enrollment; omitted for student self-registration",
    )
    notes: Optional[str] = Field(None, max_length=500)


class DriveRegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    drive_id: int
    student_id: int
    user_id: Optional[int] = None
    student_name: str
    roll_number: str
    department_code: Optional[str] = None
    department_name: Optional[str] = None
    graduation_year: int
    cgpa: float
    active_backlogs: int
    registered_by_user_id: int
    registration_source: str
    status: DriveRegistrationStatus
    eligibility_passed: bool
    eligibility_snapshot: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None
    registered_at: datetime


class DriveCandidateItem(BaseModel):
    student_id: int
    user_id: int
    full_name: str
    email: str
    roll_number: str
    department_code: Optional[str] = None
    department_name: Optional[str] = None
    graduation_year: int
    cgpa: float
    active_backlogs: int
    is_eligible: bool
    ineligible_reasons: List[str] = Field(default_factory=list)
    eligible_job_ids: List[int] = Field(default_factory=list)
    eligible_job_titles: List[str] = Field(default_factory=list)
    is_registered: bool = False
    registration_status: Optional[DriveRegistrationStatus] = None
    application_count: int = 0
    tpo_screening_statuses: List[str] = Field(default_factory=list)
    latest_application_status: Optional[str] = None
    final_outcome: Optional[str] = None


class DriveCandidatesResponse(BaseModel):
    drive_id: int
    eligible_candidates: List[DriveCandidateItem] = Field(default_factory=list)
    ineligible_audit_records: List[DriveCandidateItem] = Field(default_factory=list)


class DriveActivityCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    activity_type: DriveActivityType
    mode: DriveMode = DriveMode.ON_CAMPUS
    scheduled_start: datetime
    scheduled_end: datetime
    venue: Optional[str] = Field(None, max_length=255)
    meeting_link: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=3000)
    job_id: Optional[int] = None
    company_id: Optional[int] = None
    coordinator_user_id: Optional[int] = None
    coordinator_name: str = Field(..., min_length=2, max_length=150)
    coordinator_contact: Optional[str] = Field(None, max_length=150)

    @model_validator(mode="after")
    def validate_times(self) -> "DriveActivityCreate":
        if self.scheduled_start >= self.scheduled_end:
            raise ValueError("scheduled_start must be strictly earlier than scheduled_end")
        return self


class DriveActivityUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    activity_type: Optional[DriveActivityType] = None
    mode: Optional[DriveMode] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    venue: Optional[str] = Field(None, max_length=255)
    meeting_link: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=3000)
    job_id: Optional[int] = None
    company_id: Optional[int] = None
    coordinator_user_id: Optional[int] = None
    coordinator_name: Optional[str] = Field(None, min_length=2, max_length=150)
    coordinator_contact: Optional[str] = Field(None, max_length=150)
    status: Optional[DriveActivityStatus] = None

    @model_validator(mode="after")
    def validate_times(self) -> "DriveActivityUpdate":
        if (
            self.scheduled_start is not None
            and self.scheduled_end is not None
            and self.scheduled_start >= self.scheduled_end
        ):
            raise ValueError("scheduled_start must be strictly earlier than scheduled_end")
        return self


class DriveActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    drive_id: int
    job_id: Optional[int] = None
    job_title: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    coordinator_user_id: Optional[int] = None
    coordinator_name: str
    coordinator_contact: Optional[str] = None
    title: str
    activity_type: DriveActivityType
    mode: DriveMode
    venue: Optional[str] = None
    meeting_link: Optional[str] = None
    scheduled_start: datetime
    scheduled_end: datetime
    description: Optional[str] = None
    status: DriveActivityStatus
    present_count: int = 0
    absent_count: int = 0
    late_count: int = 0
    excused_count: int = 0
    created_at: datetime


class DriveAttendanceMarkItem(BaseModel):
    student_id: int
    attendance_status: DriveAttendanceStatus
    remarks: Optional[str] = Field(None, max_length=500)


class DriveAttendanceBatchRequest(BaseModel):
    records: List[DriveAttendanceMarkItem] = Field(..., min_length=1)


class DriveAttendanceRecordResponse(BaseModel):
    id: int
    activity_id: int
    drive_id: int
    student_id: int
    student_name: str
    roll_number: str
    department_code: Optional[str] = None
    attendance_status: DriveAttendanceStatus
    marked_by_user_id: int
    marked_by_name: str
    marked_at: datetime
    remarks: Optional[str] = None


class DriveAttendanceAuditResponse(BaseModel):
    id: int
    attendance_id: int
    activity_id: int
    student_id: int
    student_name: str
    roll_number: str
    changed_by_user_id: int
    changed_by_name: str
    previous_status: Optional[str] = None
    new_status: str
    remarks: Optional[str] = None
    changed_at: datetime


class DriveAnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    message: str = Field(..., min_length=5, max_length=3000)
    target_audience: Literal[
        "all_registered",
        "eligible_students",
        "shortlisted_candidates",
        "specific_job_applicants",
    ] = "all_registered"
    job_id: Optional[int] = None


class DriveAnnouncementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    drive_id: int
    sender_user_id: int
    sender_name: str
    job_id: Optional[int] = None
    title: str
    message: str
    target_audience: str
    recipients_count: int
    created_at: datetime


class DriveActivityAttendanceSummary(BaseModel):
    activity_id: int
    title: str
    activity_type: str
    scheduled_start: datetime
    status: str
    coordinator_name: str
    total_marked: int = 0
    present_count: int = 0
    absent_count: int = 0
    late_count: int = 0
    excused_count: int = 0
    attendance_rate_pct: float = 0.0


class DriveReportResponse(BaseModel):
    generated_at: datetime
    drive: Dict[str, Any]
    dashboard: DriveDashboardResponse
    attendance_summary: List[DriveActivityAttendanceSummary] = Field(default_factory=list)
    registrations_sample_count: int = 0
    eligible_sample_count: int = 0
    ineligible_sample_count: int = 0
    placed_outcomes: List[Dict[str, Any]] = Field(default_factory=list)

