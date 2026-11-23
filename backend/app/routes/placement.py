"""Phase 6 Placement and Recruitment Management API Routes."""
from datetime import datetime, timedelta, timezone
import io
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, inspect as sa_inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_async_session
from app.core.dependencies import (
    get_current_user,
    require_admin,
    require_institutional_staff,
    require_recruiter,
    require_roles,
    require_student,
    require_tpo,
)
from app.core.errors import (
    AppException,
    AuthorizationException,
    EntityNotFoundException,
    ResourceConflictException,
)
from app.models.company import Company, RecruiterProfile
from app.models.job import Job, JobStatus
from app.models.organization import Department, Institution
from app.models.placement import (
    ApplicationStatus,
    ApplicationStatusHistory,
    DecisionDomain,
    DriveMode,
    DriveStatus,
    Interview,
    InterviewMode,
    InterviewOutcome,
    InterviewStatus,
    JobApplication,
    Notification,
    NotificationCategory,
    PlacementDrive,
    PlacementDriveJob,
    TpoScreeningStatus,
)
from app.models.resume import Resume
from app.models.student import StudentProfile, StudentSkill
from app.models.user import User, UserRole
from app.models.audit import AuditCategory, AuditStatus
from app.services.audit_service import log_audit_event
from app.schemas.placement import (
    AdminOverviewResponse,
    ApplicationStatusHistoryResponse,
    ApplicationTrackerResponse,
    ApplicationWithdrawRequest,
    DepartmentPlacementStat,
    EligibilitySimulationRequest,
    EligibilitySimulationResponse,
    InterviewCancelRequest,
    InterviewCreateRequest,
    InterviewOutcomeRequest,
    InterviewRescheduleRequest,
    InterviewResponse,
    InterviewStudentResponse,
    JobApplicationCreate,
    JobApplicationDetailResponse,
    JobApplicationListResponse,
    JobApplicationRecruiterResponse,
    JobApplicationResponse,
    JobApplicationStudentDetailResponse,
    JobApplicationTpoDetailResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationResponse,
    NotificationSyncResponse,
    NotificationUnreadCountResponse,
    OfferResponseRequest,
    PlacementDriveCreate,
    PlacementDriveDetailResponse,
    PlacementDriveJobAddRequest,
    PlacementDriveJobResponse,
    PlacementDriveResponse,
    PlacementDriveUpdate,
    RecruiterOverviewResponse,
    RecruiterStatusUpdateRequest,
    SimulatedStudentSummary,
    StudentInterviewListResponse,
    StudentInterviewTrackingItem,
    TpoOverviewResponse,
    TpoScreeningUpdateRequest,
    TpoStudentRosterItem,
    TpoStudentRosterResponse,
    TrackerCalendarResponse,
    UserRoleCount,
)
from app.services.application_service import (
    get_student_application_tracker,
    get_student_calendar_events,
    stream_recruiter_resume,
    submit_application,
    withdraw_application,
)
from app.services.drive_service import (
    add_job_to_drive,
    create_placement_drive,
    derive_phase_from_status,
    derive_status_from_phase,
    get_drive_with_stats,
    soft_remove_job_from_drive,
    validate_drive_lifecycle_transition,
)
from app.schemas.interview_portal import (
    InterviewCalendarResponse,
    InterviewListPortalResponse,
    InterviewRoundTemplate,
    InterviewWorkspaceDetailResponse,
)
from app.services.interview_service import (
    STANDARD_ROUND_TEMPLATES,
    cancel_interview,
    get_interview_calendar_events,
    get_interview_workspace_detail,
    list_company_interviews,
    list_student_interviews,
    list_tpo_institution_interviews,
    record_interview_outcome,
    reschedule_interview,
    schedule_interview,
)
from app.services.notification_service import (
    get_or_create_notification_preferences,
    get_unread_count,
    list_notifications,
    mark_all_as_read,
    mark_as_read,
    sync_smart_student_notifications,
    update_notification_preferences,
)
from app.services.state_machine import (
    InvalidStateTransitionError,
    execute_recruiter_lifecycle_transition,
    execute_tpo_screening_transition,
)

logger = logging.getLogger(__name__)

router = APIRouter()
drives_router = APIRouter(prefix="/drives", tags=["Placement Drives"])
applications_router = APIRouter(prefix="/applications", tags=["Job Applications"])
interviews_router = APIRouter(prefix="/interviews", tags=["Interviews"])
notifications_router = APIRouter(prefix="/notifications", tags=["Notifications"])
recruiter_router = APIRouter(prefix="/recruiter", tags=["Recruiter Operations"])


# =============================================================================
# Helper Serialization Functions
# =============================================================================

def _map_drive_job_to_response(dj: PlacementDriveJob) -> PlacementDriveJobResponse:
    job = getattr(dj, "job", None)
    company = getattr(job, "company", None) if job else None
    now_utc = datetime.now(timezone.utc)
    created_at = getattr(dj, "created_at", None) or now_utc
    return PlacementDriveJobResponse(
        id=dj.id,
        drive_id=dj.drive_id,
        job_id=dj.job_id,
        is_active=dj.is_active,
        removed_at=dj.removed_at,
        created_at=created_at,
        job_title=job.title if job else None,
        company_name=company.name if company else None,
        employment_type=job.employment_type.value if (job and getattr(job, "employment_type", None)) else None,
        location=job.location if job else None,
    )


def _map_drive_to_response(
    drive: PlacementDrive,
    total_jobs: int = 0,
    total_applications: int = 0,
) -> PlacementDriveResponse:
    now_utc = datetime.now(timezone.utc)
    created_at = getattr(drive, "created_at", None) or now_utc
    updated_at = getattr(drive, "updated_at", None) or created_at
    lifecycle_phase = getattr(drive, "lifecycle_phase", None) or derive_phase_from_status(drive.status)
    return PlacementDriveResponse(
        id=drive.id,
        institution_id=drive.institution_id,
        created_by_user_id=drive.created_by_user_id,
        name=drive.name,
        academic_year=drive.academic_year,
        target_graduation_year=drive.target_graduation_year,
        registration_start_date=drive.registration_start_date,
        registration_end_date=drive.registration_end_date,
        drive_mode=drive.drive_mode,
        status=drive.status,
        lifecycle_phase=lifecycle_phase,
        description=drive.description,
        guidelines=drive.guidelines,
        drive_start_date=getattr(drive, "drive_start_date", None),
        drive_end_date=getattr(drive, "drive_end_date", None),
        venue_location=getattr(drive, "venue_location", None),
        instructions=getattr(drive, "instructions", None),
        required_documents=list(getattr(drive, "required_documents", None) or []),
        target_graduation_batches=list(
            getattr(drive, "target_graduation_batches", None) or [drive.target_graduation_year]
        ),
        participating_company_ids=list(getattr(drive, "participating_company_ids", None) or []),
        eligible_department_ids=list(getattr(drive, "eligible_department_ids", None) or []),
        is_active=drive.is_active,
        created_at=created_at,
        updated_at=updated_at,
        total_jobs=total_jobs,
        total_applications=total_applications,
    )


def _safe_loaded(obj, attr: str, default=None):
    """Safely read an attribute or loaded relationship without triggering async lazy IO on expired fields."""
    if obj is None:
        return default
    try:
        state = sa_inspect(obj)
        if attr in state.unloaded:
            return obj.__dict__.get(attr, default)
    except Exception:
        pass
    return getattr(obj, attr, default)


def _map_application_to_response(
    app: JobApplication,
    is_recruiter: bool = False,
) -> JobApplicationResponse:
    job = _safe_loaded(app, "job")
    company = _safe_loaded(job, "company") if job else None
    drive = _safe_loaded(app, "drive")
    student_profile = _safe_loaded(app, "student_profile")
    student_user = _safe_loaded(student_profile, "user") if student_profile else None
    student_dept = _safe_loaded(student_user, "department") if student_user else None
    now_utc = datetime.now(timezone.utc)
    created_at = _safe_loaded(app, "created_at") or now_utc
    updated_at = _safe_loaded(app, "updated_at") or created_at

    base_kwargs = {
        "id": app.id,
        "job_id": app.job_id,
        "student_id": app.student_id,
        "resume_id": app.resume_id,
        "drive_id": app.drive_id,
        "tpo_screening_status": app.tpo_screening_status,
        "tpo_screened_by_user_id": app.tpo_screened_by_user_id,
        "tpo_screened_at": app.tpo_screened_at,
        "tpo_feedback": app.tpo_feedback,
        "current_status": app.current_status,
        "recruiter_decision_at": app.recruiter_decision_at,
        "compatibility_score_at_application": float(app.compatibility_score_at_application or 0.0),
        "cover_letter": app.cover_letter,
        "withdrawn_at": app.withdrawn_at,
        "withdrawal_reason": app.withdrawal_reason,
        "offer_deadline_at": getattr(app, "offer_deadline_at", None),
        "offer_package_lpa": (
            float(app.offer_package_lpa)
            if getattr(app, "offer_package_lpa", None) is not None
            else None
        ),
        "offer_notes": getattr(app, "offer_notes", None),
        "created_at": created_at,
        "updated_at": updated_at,
        "job_title": job.title if job else None,
        "company_name": company.name if company else None,
        "drive_name": drive.name if drive else None,
        "application_deadline": getattr(job, "application_deadline", None) if job else None,
        "job_location": getattr(job, "location", None) if job else None,
        "work_mode": job.work_mode.value if (job and getattr(job, "work_mode", None)) else None,
        "employment_type": job.employment_type.value if (job and getattr(job, "employment_type", None)) else None,
        "salary_range": getattr(job, "salary_range", None) if job else None,
        "student_name": student_user.full_name if student_user else None,
        "student_email": student_user.email if student_user else None,
        "student_roll_number": student_profile.roll_number if student_profile else None,
        "student_department": student_dept.name if student_dept else None,
    }
    if is_recruiter:
        return JobApplicationRecruiterResponse(
            **base_kwargs,
            recruiter_feedback_notes=app.recruiter_feedback_notes,
        )
    return JobApplicationResponse(**base_kwargs)


def _map_interview_to_response(
    interview: Interview,
    is_student: bool = False,
) -> InterviewResponse | InterviewStudentResponse:
    now_utc = datetime.now(timezone.utc)
    created_at = _safe_loaded(interview, "created_at") or now_utc
    updated_at = _safe_loaded(interview, "updated_at") or created_at
    created_by_user_id = _safe_loaded(interview, "created_by_user_id") or 1
    is_rescheduled = bool(
        isinstance(getattr(interview, "cancellation_reason", None), str)
        and interview.cancellation_reason.strip().startswith("Rescheduled:")
        and interview.status != InterviewStatus.CANCELLED
    )
    if is_student:
        return InterviewStudentResponse(
            id=interview.id,
            application_id=interview.application_id,
            round_number=interview.round_number,
            round_title=interview.round_title,
            interview_mode=interview.interview_mode,
            meeting_link=interview.meeting_link,
            location=interview.location,
            scheduled_start_time=interview.scheduled_start_time,
            duration_minutes=interview.duration_minutes,
            interviewer_names=interview.interviewer_names,
            instructions=getattr(interview, "instructions", None),
            status=interview.status,
            outcome=interview.outcome,
            cancellation_reason=interview.cancellation_reason,
            is_rescheduled=is_rescheduled,
            created_at=created_at,
            updated_at=updated_at,
        )
    return InterviewResponse(
        id=interview.id,
        application_id=interview.application_id,
        round_number=interview.round_number,
        round_title=interview.round_title,
        interview_mode=interview.interview_mode,
        meeting_link=interview.meeting_link,
        location=interview.location,
        scheduled_start_time=interview.scheduled_start_time,
        duration_minutes=interview.duration_minutes,
        interviewer_names=interview.interviewer_names,
        instructions=getattr(interview, "instructions", None),
        status=interview.status,
        outcome=interview.outcome,
        feedback_notes=interview.feedback_notes,
        created_by_user_id=created_by_user_id,
        cancellation_reason=interview.cancellation_reason,
        is_rescheduled=is_rescheduled,
        created_at=created_at,
        updated_at=updated_at,
    )


# =============================================================================
# 1. Placement Drive Management Routes
# =============================================================================

@drives_router.post(
    "",
    response_model=PlacementDriveResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new campus placement drive",
)
async def create_drive_endpoint(
    payload: PlacementDriveCreate,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
):
    drive = await create_placement_drive(
        session=session,
        tpo_user=current_user,
        name=payload.name,
        academic_year=payload.academic_year,
        target_graduation_year=payload.target_graduation_year,
        registration_start_date=payload.registration_start_date,
        registration_end_date=payload.registration_end_date,
        drive_mode=payload.drive_mode,
        description=payload.description,
        guidelines=payload.guidelines,
        lifecycle_phase=payload.lifecycle_phase,
        drive_start_date=payload.drive_start_date,
        drive_end_date=payload.drive_end_date,
        venue_location=payload.venue_location,
        instructions=payload.instructions,
        required_documents=payload.required_documents,
        target_graduation_batches=payload.target_graduation_batches,
        participating_company_ids=payload.participating_company_ids,
        eligible_department_ids=payload.eligible_department_ids,
    )
    added_jobs = 0
    for jid in dict.fromkeys(payload.job_ids or []):
        await add_job_to_drive(
            session=session,
            tpo_user=current_user,
            drive_id=drive.id,
            job_id=jid,
        )
        added_jobs += 1
    return _map_drive_to_response(drive, total_jobs=added_jobs, total_applications=0)


@drives_router.get(
    "",
    response_model=List[PlacementDriveResponse],
    summary="List placement drives with institution scoping",
)
async def list_drives_endpoint(
    academic_year: Optional[str] = Query(None, description="Filter by academic year"),
    target_graduation_year: Optional[int] = Query(None, description="Filter by graduation year"),
    drive_mode: Optional[DriveMode] = Query(None, description="Filter by drive mode"),
    drive_status: Optional[DriveStatus] = Query(None, alias="status", description="Filter by drive status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    stmt = select(PlacementDrive)

    # Scoping by role
    if current_user.role == UserRole.STUDENT:
        stmt = stmt.where(
            PlacementDrive.institution_id == current_user.institution_id,
            PlacementDrive.is_active == True,  # noqa: E712
            PlacementDrive.status.in_([DriveStatus.UPCOMING, DriveStatus.ONGOING]),
        )
    elif current_user.role in (UserRole.TPO, UserRole.ADMIN) or current_user.email == "maheshwarijaya03@gmail.com":
        stmt = stmt.where(PlacementDrive.institution_id == current_user.institution_id)
    elif current_user.role == UserRole.RECRUITER:
        # Recruiters can ONLY see drives that have an active job associated with their company
        recruiter_profile = current_user.recruiter_profile
        company_id = recruiter_profile.company_id if recruiter_profile else None
        if not company_id:
            return []
        stmt = (
            stmt.join(PlacementDriveJob, PlacementDrive.id == PlacementDriveJob.drive_id)
            .join(Job, PlacementDriveJob.job_id == Job.id)
            .where(
                Job.company_id == company_id,
                PlacementDriveJob.is_active == True,  # noqa: E712
            )
            .distinct()
        )
    # Admin sees all drives

    if isinstance(academic_year, str) and academic_year.strip():
        stmt = stmt.where(PlacementDrive.academic_year == academic_year.strip())
    if isinstance(target_graduation_year, int):
        stmt = stmt.where(PlacementDrive.target_graduation_year == target_graduation_year)
    if isinstance(drive_mode, DriveMode):
        stmt = stmt.where(PlacementDrive.drive_mode == drive_mode)
    if isinstance(drive_status, DriveStatus):
        stmt = stmt.where(PlacementDrive.status == drive_status)

    actual_skip = skip if isinstance(skip, int) else 0
    actual_limit = limit if isinstance(limit, int) else 50
    stmt = stmt.order_by(PlacementDrive.registration_start_date.desc()).offset(actual_skip).limit(actual_limit)
    result = await session.execute(stmt)
    drives = result.scalars().all()

    response_items = []
    for d in drives:
        res_jobs = await session.execute(
            select(func.count(PlacementDriveJob.id)).where(
                PlacementDriveJob.drive_id == d.id,
                PlacementDriveJob.is_active == True,  # noqa: E712
            )
        )
        total_jobs = res_jobs.scalar() or 0

        res_apps = await session.execute(
            select(func.count(JobApplication.id)).where(JobApplication.drive_id == d.id)
        )
        total_apps = res_apps.scalar() or 0

        response_items.append(_map_drive_to_response(d, total_jobs, total_apps))

    return response_items


@drives_router.get(
    "/{drive_id}",
    response_model=PlacementDriveDetailResponse,
    summary="Get placement drive details with associated active jobs",
)
async def get_drive_endpoint(
    drive_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    drive, total_jobs, total_apps = await get_drive_with_stats(
        session=session,
        drive_id=drive_id,
        user=current_user,
    )
    if current_user.role == UserRole.RECRUITER:
        company_id = current_user.recruiter_profile.company_id if current_user.recruiter_profile else None
        job_responses = [
            _map_drive_job_to_response(dj)
            for dj in (drive.drive_jobs or [])
            if dj.is_active and getattr(dj.job, "company_id", None) == company_id
        ]
    else:
        job_responses = [
            _map_drive_job_to_response(dj)
            for dj in (drive.drive_jobs or [])
            if dj.is_active
        ]
    base_res = _map_drive_to_response(drive, total_jobs, total_apps)
    return PlacementDriveDetailResponse(
        **base_res.model_dump(),
        jobs=job_responses,
    )


@drives_router.patch(
    "/{drive_id}",
    response_model=PlacementDriveResponse,
    summary="Update placement drive details",
)
async def update_drive_endpoint(
    drive_id: int,
    payload: PlacementDriveUpdate,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(PlacementDrive).where(PlacementDrive.id == drive_id)
    )
    drive = result.scalar_one_or_none()
    if not drive:
        raise EntityNotFoundException("PlacementDrive", drive_id)

    if current_user.role == UserRole.TPO and drive.institution_id != current_user.institution_id:
        raise AuthorizationException("You may only manage placement drives for your own academic institution.")

    update_dict = payload.model_dump(exclude_unset=True)
    start_date = update_dict.get("registration_start_date", drive.registration_start_date)
    end_date = update_dict.get("registration_end_date", drive.registration_end_date)
    if start_date and end_date and start_date >= end_date:
        raise AppException("Drive registration start date must be strictly earlier than registration end date.")

    sched_start = update_dict.get("drive_start_date", getattr(drive, "drive_start_date", None))
    sched_end = update_dict.get("drive_end_date", getattr(drive, "drive_end_date", None))
    if sched_start and sched_end and sched_start >= sched_end:
        raise AppException("Drive schedule start date must be strictly earlier than drive schedule end date.")

    next_active = update_dict.get("is_active", drive.is_active)
    target_phase = update_dict.pop("lifecycle_phase", None)
    target_status = update_dict.pop("status", None)

    if target_phase is not None:
        synced_status = validate_drive_lifecycle_transition(drive, target_phase, next_is_active=next_active)
        drive.lifecycle_phase = target_phase
        drive.status = synced_status
    elif target_status is not None:
        mapped_phase = derive_phase_from_status(target_status)
        synced_status = validate_drive_lifecycle_transition(drive, mapped_phase, next_is_active=next_active)
        drive.lifecycle_phase = mapped_phase
        drive.status = target_status

    for field, val in update_dict.items():
        setattr(drive, field, val)

    await session.flush()
    return _map_drive_to_response(drive)


# =============================================================================
# 2. Drive-Job Association Management Routes
# =============================================================================

@drives_router.post(
    "/{drive_id}/jobs",
    response_model=PlacementDriveJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Associate a job with an institutional placement drive",
)
async def add_job_to_drive_endpoint(
    drive_id: int,
    payload: PlacementDriveJobAddRequest,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
):
    drive_job = await add_job_to_drive(
        session=session,
        tpo_user=current_user,
        drive_id=drive_id,
        job_id=payload.job_id,
    )
    result = await session.execute(
        select(PlacementDriveJob)
        .options(selectinload(PlacementDriveJob.job).selectinload(Job.company))
        .where(PlacementDriveJob.id == drive_job.id)
    )
    dj_loaded = result.scalar_one_or_none() or drive_job
    return _map_drive_job_to_response(dj_loaded)


@drives_router.delete(
    "/{drive_id}/jobs/{job_id}",
    response_model=PlacementDriveJobResponse,
    summary="Soft-remove a job association from a placement drive",
)
async def remove_job_from_drive_endpoint(
    drive_id: int,
    job_id: int,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
):
    removed = await soft_remove_job_from_drive(
        session=session,
        tpo_user=current_user,
        drive_id=drive_id,
        job_id=job_id,
    )
    return _map_drive_job_to_response(removed)


@drives_router.get(
    "/{drive_id}/jobs",
    response_model=List[PlacementDriveJobResponse],
    summary="List active job postings associated with a placement drive",
)
async def list_drive_jobs_endpoint(
    drive_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(PlacementDrive).where(PlacementDrive.id == drive_id)
    )
    drive = result.scalar_one_or_none()
    if not drive:
        raise EntityNotFoundException("PlacementDrive", drive_id)

    if current_user.role in (UserRole.STUDENT, UserRole.TPO) and current_user.institution_id != drive.institution_id:
        raise AuthorizationException("You do not have permission to view drives from another academic institution.")

    stmt = (
        select(PlacementDriveJob)
        .options(selectinload(PlacementDriveJob.job).selectinload(Job.company))
        .join(Job, PlacementDriveJob.job_id == Job.id)
        .where(
            PlacementDriveJob.drive_id == drive_id,
            PlacementDriveJob.is_active == True,  # noqa: E712
        )
    )
    if current_user.role == UserRole.RECRUITER:
        company_id = current_user.recruiter_profile.company_id if current_user.recruiter_profile else None
        if not company_id:
            raise AuthorizationException("Recruiter must be affiliated with a corporate partner.")
        # Recruiter can only inspect jobs associated with their company
        stmt = stmt.where(Job.company_id == company_id)

    result_jobs = await session.execute(stmt)
    associations = result_jobs.scalars().all()
    if current_user.role == UserRole.RECRUITER and not associations:
        raise AuthorizationException("You do not have permission to view drives not associated with your company.")
    return [_map_drive_job_to_response(dj) for dj in associations]


@drives_router.get(
    "/{drive_id}/applications",
    response_model=JobApplicationListResponse,
    summary="List candidate applications for a campus placement drive (TPO view)",
)
async def list_drive_applications_endpoint(
    drive_id: int,
    screening_status: Optional[TpoScreeningStatus] = Query(None, description="Filter by TPO screening status"),
    job_id: Optional[int] = Query(None, description="Filter by job ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(PlacementDrive).where(PlacementDrive.id == drive_id)
    )
    drive = result.scalar_one_or_none()
    if not drive:
        raise EntityNotFoundException("PlacementDrive", drive_id)

    if current_user.role == UserRole.TPO and current_user.institution_id != drive.institution_id:
        raise AuthorizationException("You may only view applications for placement drives of your own institution.")

    stmt = (
        select(JobApplication)
        .options(
            selectinload(JobApplication.job).selectinload(Job.company),
            selectinload(JobApplication.drive),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.user).selectinload(User.department),
        )
        .where(JobApplication.drive_id == drive_id)
    )
    actual_skip = skip if isinstance(skip, int) else 0
    actual_limit = limit if isinstance(limit, int) else 50

    if isinstance(screening_status, TpoScreeningStatus):
        stmt = stmt.where(JobApplication.tpo_screening_status == screening_status)
    if isinstance(job_id, int):
        stmt = stmt.where(JobApplication.job_id == job_id)

    # Count total
    count_stmt = select(func.count(JobApplication.id)).where(JobApplication.drive_id == drive_id)
    if isinstance(screening_status, TpoScreeningStatus):
        count_stmt = count_stmt.where(JobApplication.tpo_screening_status == screening_status)
    if isinstance(job_id, int):
        count_stmt = count_stmt.where(JobApplication.job_id == job_id)

    total_res = await session.execute(count_stmt)
    total = total_res.scalar() or 0

    stmt = stmt.order_by(JobApplication.created_at.desc()).offset(actual_skip).limit(actual_limit)
    res = await session.execute(stmt)
    applications = res.scalars().all()

    items = [_map_application_to_response(app, is_recruiter=False) for app in applications]
    return JobApplicationListResponse(items=items, total=total)


# =============================================================================
# 3. Student Application Submission & Student Routes
# =============================================================================

@applications_router.post(
    "",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a job application with Phase 5 eligibility and matching verification",
)
async def submit_application_endpoint(
    payload: JobApplicationCreate,
    current_user: User = Depends(require_student),
    session: AsyncSession = Depends(get_async_session),
):
    application = await submit_application(
        session=session,
        student_user=current_user,
        job_id=payload.job_id,
        resume_id=payload.resume_id,
        drive_id=payload.drive_id,
        cover_letter=payload.cover_letter,
    )

    await log_audit_event(
        session=session,
        action="APPLICATION_SUBMITTED",
        category=AuditCategory.RECRUITMENT,
        entity_type="JobApplication",
        entity_id=str(application.id),
        user=current_user,
        institution_id=current_user.institution_id,
        metadata={"job_id": payload.job_id, "drive_id": payload.drive_id, "resume_id": payload.resume_id},
        status=AuditStatus.SUCCESS,
        commit=True,
    )
    # Reload with display relations
    result = await session.execute(
        select(JobApplication)
        .options(
            selectinload(JobApplication.job).selectinload(Job.company),
            selectinload(JobApplication.drive),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.user).selectinload(User.department),
        )
        .where(JobApplication.id == application.id)
    )
    app_loaded = result.scalar_one_or_none() or application
    return _map_application_to_response(app_loaded, is_recruiter=False)


@applications_router.get(
    "/my",
    response_model=JobApplicationListResponse,
    summary="List all applications submitted by the current authenticated student",
)
async def get_my_applications_endpoint(
    app_status: Optional[ApplicationStatus] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_student),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise EntityNotFoundException("StudentProfile", current_user.id)

    stmt = (
        select(JobApplication)
        .options(
            selectinload(JobApplication.job).selectinload(Job.company),
            selectinload(JobApplication.drive),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.user).selectinload(User.department),
        )
        .where(JobApplication.student_id == profile.id)
    )
    actual_skip = skip if isinstance(skip, int) else 0
    actual_limit = limit if isinstance(limit, int) else 50

    if isinstance(app_status, ApplicationStatus):
        stmt = stmt.where(JobApplication.current_status == app_status)

    count_stmt = select(func.count(JobApplication.id)).where(JobApplication.student_id == profile.id)
    if isinstance(app_status, ApplicationStatus):
        count_stmt = count_stmt.where(JobApplication.current_status == app_status)
    total_res = await session.execute(count_stmt)
    total = total_res.scalar() or 0

    stmt = stmt.order_by(JobApplication.created_at.desc()).offset(actual_skip).limit(actual_limit)
    res = await session.execute(stmt)
    applications = res.scalars().all()

    items = [_map_application_to_response(app, is_recruiter=False) for app in applications]
    return JobApplicationListResponse(items=items, total=total)


@applications_router.get(
    "/tracker",
    response_model=ApplicationTrackerResponse,
    summary="Centralized smart application tracker with filters, timeline, interviews, and offers",
)
async def get_student_application_tracker_endpoint(
    app_status: Optional[ApplicationStatus] = Query(None, alias="status", description="Filter by application stage"),
    company: Optional[str] = Query(None, description="Filter by company name (partial match)"),
    role: Optional[str] = Query(None, description="Filter by job role title (partial match)"),
    search: Optional[str] = Query(None, description="Search by company or job title"),
    date_from: Optional[datetime] = Query(None, description="Applied on or after timestamp"),
    date_to: Optional[datetime] = Query(None, description="Applied on or before timestamp"),
    interview_status: Optional[str] = Query(None, description="scheduled, upcoming, completed, cancelled, no_show, none"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sync_notifications: bool = Query(True, description="Generate deduplicated smart notifications"),
    current_user: User = Depends(require_student),
    session: AsyncSession = Depends(get_async_session),
):
    return await get_student_application_tracker(
        session=session,
        student_user=current_user,
        app_status=app_status if isinstance(app_status, ApplicationStatus) else None,
        company_query=company if isinstance(company, str) else None,
        role_query=role if isinstance(role, str) else None,
        search_query=search if isinstance(search, str) else None,
        date_from=date_from if isinstance(date_from, datetime) else None,
        date_to=date_to if isinstance(date_to, datetime) else None,
        interview_status=interview_status if isinstance(interview_status, str) else None,
        skip=skip if isinstance(skip, int) else 0,
        limit=limit if isinstance(limit, int) else 20,
        sync_notifications=sync_notifications if isinstance(sync_notifications, bool) else True,
    )


@applications_router.get(
    "/tracker/calendar",
    response_model=TrackerCalendarResponse,
    summary="Calendar events for student interviews, application deadlines, offers, and drives",
)
async def get_student_calendar_events_endpoint(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    app_status: Optional[ApplicationStatus] = Query(None, alias="status"),
    company: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    interview_status: Optional[str] = Query(None),
    current_user: User = Depends(require_student),
    session: AsyncSession = Depends(get_async_session),
):
    return await get_student_calendar_events(
        session=session,
        student_user=current_user,
        start_date=start_date if isinstance(start_date, datetime) else None,
        end_date=end_date if isinstance(end_date, datetime) else None,
        app_status=app_status if isinstance(app_status, ApplicationStatus) else None,
        company_query=company if isinstance(company, str) else None,
        role_query=role if isinstance(role, str) else None,
        interview_status=interview_status if isinstance(interview_status, str) else None,
    )


@applications_router.get(
    "/{application_id}",
    response_model=JobApplicationDetailResponse | JobApplicationTpoDetailResponse | JobApplicationStudentDetailResponse,
    summary="Get complete application details with history and interview rounds (scoped & redacted)",
)
async def get_application_detail_endpoint(
    application_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(JobApplication)
        .options(
            selectinload(JobApplication.job).selectinload(Job.company),
            selectinload(JobApplication.drive),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.user).selectinload(User.department),
            selectinload(JobApplication.status_history),
            selectinload(JobApplication.interviews),
        )
        .where(JobApplication.id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise EntityNotFoundException("JobApplication", application_id)

    # Authorization and scoping
    is_student_owner = (
        current_user.role == UserRole.STUDENT
        and application.student_profile
        and application.student_profile.user_id == current_user.id
    )
    is_recruiter_owner = False
    if current_user.role == UserRole.RECRUITER and current_user.recruiter_profile and application.job:
        is_recruiter_owner = current_user.recruiter_profile.company_id == application.job.company_id

    is_tpo_authorized = False
    if current_user.role == UserRole.TPO:
        # TPO can view if candidate belongs to TPO's institution or application is linked to TPO's drive
        student_inst = application.student_profile.user.institution_id if (application.student_profile and application.student_profile.user) else None
        drive_inst = application.drive.institution_id if application.drive else None
        is_tpo_authorized = current_user.institution_id in (student_inst, drive_inst)

    is_admin = current_user.role == UserRole.ADMIN

    if not (is_student_owner or is_recruiter_owner or is_tpo_authorized or is_admin):
        raise AuthorizationException("You do not have permission to view this application.")

    history_responses = [
        ApplicationStatusHistoryResponse.model_validate(h)
        for h in sorted(application.status_history or [], key=lambda h: h.created_at)
    ]

    # 1. Redacted student view: no recruiter notes, no confidential interview notes
    if is_student_owner and not (is_recruiter_owner or is_tpo_authorized or is_admin):
        interview_student_responses = [
            _map_interview_to_response(i, is_student=True)
            for i in sorted(application.interviews or [], key=lambda i: i.round_number)
        ]
        base_res = _map_application_to_response(application, is_recruiter=False)
        return JobApplicationStudentDetailResponse(
            **base_res.model_dump(),
            status_history=history_responses,
            interviews=interview_student_responses,
        )

    # 2. Institutional TPO view: screening info & interview schedule, without confidential recruiter evaluation notes
    if is_tpo_authorized and not (is_recruiter_owner or is_admin):
        interview_tpo_responses = [
            _map_interview_to_response(i, is_student=True)
            for i in sorted(application.interviews or [], key=lambda i: i.round_number)
        ]
        base_res = _map_application_to_response(application, is_recruiter=False)
        return JobApplicationTpoDetailResponse(
            **base_res.model_dump(),
            status_history=history_responses,
            interviews=interview_tpo_responses,
        )

    # 3. Full authorized view: Recruiter owning company / Admin
    interview_responses = [
        _map_interview_to_response(i, is_student=False)
        for i in sorted(application.interviews or [], key=lambda i: i.round_number)
    ]
    base_res = _map_application_to_response(application, is_recruiter=True)
    return JobApplicationDetailResponse(
        **base_res.model_dump(),
        status_history=history_responses,
        interviews=interview_responses,
    )


@applications_router.post(
    "/{application_id}/withdraw",
    response_model=JobApplicationResponse,
    summary="Candidate withdraws their active job application",
)
async def withdraw_application_endpoint(
    application_id: int,
    payload: ApplicationWithdrawRequest,
    current_user: User = Depends(require_student),
    session: AsyncSession = Depends(get_async_session),
):
    withdrawn = await withdraw_application(
        session=session,
        student_user=current_user,
        application_id=application_id,
        reason=payload.reason,
    )

    await log_audit_event(
        session=session,
        action="APPLICATION_WITHDRAWN",
        category=AuditCategory.RECRUITMENT,
        entity_type="JobApplication",
        entity_id=str(withdrawn.id),
        user=current_user,
        institution_id=current_user.institution_id,
        metadata={"reason": payload.reason},
        status=AuditStatus.SUCCESS,
        commit=True,
    )
    result = await session.execute(
        select(JobApplication)
        .options(
            selectinload(JobApplication.job).selectinload(Job.company),
            selectinload(JobApplication.drive),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.user).selectinload(User.department),
        )
        .where(JobApplication.id == withdrawn.id)
    )
    app_loaded = result.scalar_one_or_none() or withdrawn
    return _map_application_to_response(app_loaded, is_recruiter=False)


@applications_router.post(
    "/{application_id}/offer-response",
    response_model=JobApplicationResponse,
    summary="Student accepts or declines an official job offer",
)
async def respond_to_offer_endpoint(
    application_id: int,
    payload: OfferResponseRequest,
    current_user: User = Depends(require_student),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(JobApplication)
        .options(
            selectinload(JobApplication.student_profile),
            selectinload(JobApplication.job).selectinload(Job.company),
            selectinload(JobApplication.drive),
        )
        .where(JobApplication.id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise EntityNotFoundException("JobApplication", application_id)

    if application.student_profile.user_id != current_user.id:
        raise AuthorizationException("You may only respond to offers for your own applications.")

    if application.current_status != ApplicationStatus.OFFERED:
        raise AppException(
            f"Cannot respond to offer: Application status is '{application.current_status.value}'. Must be 'offered'.",
            code="APPLICATION_NOT_OFFERED",
        )

    target_status = ApplicationStatus.OFFER_ACCEPTED if payload.accept else ApplicationStatus.OFFER_DECLINED
    notes = f"Candidate {'accepted' if payload.accept else 'declined'} offer. {payload.notes or ''}".strip()

    await execute_recruiter_lifecycle_transition(
        session=session,
        application=application,
        new_status=target_status,
        actor_user_id=current_user.id,
        notes=notes,
    )
    return _map_application_to_response(application, is_recruiter=False)


# =============================================================================
# 4. TPO Screening and Institutional Review Routes
# =============================================================================

@applications_router.post(
    "/{application_id}/screen",
    response_model=JobApplicationResponse,
    summary="TPO institutional screening decision (shortlist or reject)",
)
async def tpo_screen_application_endpoint(
    application_id: int,
    payload: TpoScreeningUpdateRequest,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(JobApplication)
        .options(
            selectinload(JobApplication.job).selectinload(Job.company),
            selectinload(JobApplication.drive),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.user).selectinload(User.department),
        )
        .where(JobApplication.id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise EntityNotFoundException("JobApplication", application_id)

    # Reject screening for direct applications (screening bypassed)
    if application.drive_id is None:
        raise AuthorizationException("Direct applications bypass institutional TPO screening and cannot be screened by TPOs.")

    # Scoping check: TPO can only screen applications linked to a drive within their own institution
    if current_user.role == UserRole.TPO:
        if not application.drive or application.drive.institution_id != current_user.institution_id:
            raise AuthorizationException("You may only screen applications linked to a placement drive of your own institution.")

    await execute_tpo_screening_transition(
        session=session,
        application=application,
        new_screening_status=payload.status,
        actor_user_id=current_user.id,
        notes=payload.feedback,
    )
    return _map_application_to_response(application, is_recruiter=False)


# =============================================================================
# 5. Recruiter Application Review & Lifecycle Decision Routes
# =============================================================================

@recruiter_router.get(
    "/applications",
    response_model=JobApplicationListResponse,
    summary="List candidate applications for recruiter's company (Recruiter view)",
)
async def list_recruiter_applications_endpoint(
    job_id: Optional[int] = Query(None, description="Filter by job posting ID"),
    app_status: Optional[ApplicationStatus] = Query(None, alias="status", description="Filter by status"),
    drive_id: Optional[int] = Query(None, description="Filter by placement drive ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_recruiter),
    session: AsyncSession = Depends(get_async_session),
):
    company_id = current_user.recruiter_profile.company_id if current_user.recruiter_profile else None
    if not company_id and current_user.role != UserRole.ADMIN:
        raise AuthorizationException("Recruiter must be affiliated with a corporate partner.")

    stmt = (
        select(JobApplication)
        .join(Job, JobApplication.job_id == Job.id)
        .options(
            selectinload(JobApplication.job).selectinload(Job.company),
            selectinload(JobApplication.drive),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.user).selectinload(User.department),
        )
    )
    if current_user.role != UserRole.ADMIN:
        stmt = stmt.where(Job.company_id == company_id)

    if isinstance(job_id, int):
        stmt = stmt.where(JobApplication.job_id == job_id)
    if isinstance(app_status, ApplicationStatus):
        stmt = stmt.where(JobApplication.current_status == app_status)
    if isinstance(drive_id, int):
        stmt = stmt.where(JobApplication.drive_id == drive_id)

    count_stmt = select(func.count(JobApplication.id)).join(Job, JobApplication.job_id == Job.id)
    if current_user.role != UserRole.ADMIN:
        count_stmt = count_stmt.where(Job.company_id == company_id)
    if isinstance(job_id, int):
        count_stmt = count_stmt.where(JobApplication.job_id == job_id)
    if isinstance(app_status, ApplicationStatus):
        count_stmt = count_stmt.where(JobApplication.current_status == app_status)
    if isinstance(drive_id, int):
        count_stmt = count_stmt.where(JobApplication.drive_id == drive_id)

    total_res = await session.execute(count_stmt)
    total = total_res.scalar() or 0

    actual_skip = skip if isinstance(skip, int) else 0
    actual_limit = limit if isinstance(limit, int) else 50
    stmt = stmt.order_by(JobApplication.created_at.desc()).offset(actual_skip).limit(actual_limit)
    res = await session.execute(stmt)
    applications = res.scalars().all()

    items = [_map_application_to_response(app, is_recruiter=True) for app in applications]
    return JobApplicationListResponse(items=items, total=total)


@applications_router.post(
    "/{application_id}/status",
    response_model=JobApplicationRecruiterResponse,
    summary="Recruiter advances or transitions recruitment pipeline lifecycle status",
)
async def recruiter_update_status_endpoint(
    application_id: int,
    payload: RecruiterStatusUpdateRequest,
    current_user: User = Depends(require_recruiter),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(JobApplication)
        .options(
            selectinload(JobApplication.job).selectinload(Job.company),
            selectinload(JobApplication.drive),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.user).selectinload(User.department),
        )
        .where(JobApplication.id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise EntityNotFoundException("JobApplication", application_id)

    if current_user.role == UserRole.RECRUITER:
        if (
            not current_user.recruiter_profile
            or current_user.recruiter_profile.company_id != application.job.company_id
        ):
            raise AuthorizationException("You may only update applications for jobs offered by your company.")

    await execute_recruiter_lifecycle_transition(
        session=session,
        application=application,
        new_status=payload.status,
        actor_user_id=current_user.id,
        notes=payload.feedback_notes,
    )
    if payload.status == ApplicationStatus.OFFERED:
        if payload.offer_deadline_at is not None:
            application.offer_deadline_at = payload.offer_deadline_at
        if payload.offer_package_lpa is not None:
            application.offer_package_lpa = payload.offer_package_lpa
        if payload.offer_notes is not None:
            application.offer_notes = payload.offer_notes.strip() if payload.offer_notes else None
        application.updated_at = datetime.now(timezone.utc)
        await session.flush()
    return _map_application_to_response(application, is_recruiter=True)


# =============================================================================
# 6. Recruiter Resume Streaming / Download Routes
# =============================================================================

@applications_router.get(
    "/{application_id}/resume",
    summary="Recruiter-authorized verified resume download and streaming",
)
async def stream_application_resume_endpoint(
    application_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    buffer, file_name, file_size, media_type = await stream_recruiter_resume(
        session=session,
        application_id=application_id,
        recruiter_user=current_user,
    )
    headers = {
        "Content-Disposition": f'attachment; filename="{file_name}"',
        "Content-Length": str(file_size),
    }

    async def iter_buffer():
        try:
            buffer.seek(0)
            while chunk := buffer.read(65536):
                yield chunk
        finally:
            buffer.close()

    return StreamingResponse(
        content=iter_buffer(),
        media_type=media_type,
        headers=headers,
    )


# =============================================================================
# 7. Interview Scheduling, Rescheduling, Cancellation & Outcome Routes
# =============================================================================

@applications_router.post(
    "/{application_id}/interviews",
    response_model=InterviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule an interview round for an application (with student locking)",
)
async def schedule_interview_endpoint(
    application_id: int,
    payload: InterviewCreateRequest,
    current_user: User = Depends(require_recruiter),
    session: AsyncSession = Depends(get_async_session),
):
    interview = await schedule_interview(
        session=session,
        recruiter_user=current_user,
        application_id=application_id,
        round_number=payload.round_number,
        round_title=payload.round_title,
        scheduled_start_time=payload.scheduled_start_time,
        duration_minutes=payload.duration_minutes,
        interview_mode=payload.interview_mode,
        meeting_link=payload.meeting_link,
        location=payload.location,
        interviewer_names=payload.interviewer_names,
        instructions=getattr(payload, "instructions", None),
    )
    return _map_interview_to_response(interview, is_student=False)


@interviews_router.get(
    "/rounds/templates",
    response_model=List[InterviewRoundTemplate],
    summary="Get standard pre-configured interview round templates",
)
async def get_interview_round_templates_endpoint():
    return STANDARD_ROUND_TEMPLATES


@interviews_router.get(
    "",
    response_model=InterviewListPortalResponse,
    summary="List company-scoped interview roster with candidate and job details",
)
async def list_company_interviews_endpoint(
    job_id: Optional[int] = Query(None),
    application_id: Optional[int] = Query(None),
    drive_id: Optional[int] = Query(None),
    status: Optional[InterviewStatus] = Query(None),
    outcome: Optional[InterviewOutcome] = Query(None),
    mode: Optional[InterviewMode] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_recruiter),
    session: AsyncSession = Depends(get_async_session),
):
    return await list_company_interviews(
        session=session,
        current_user=current_user,
        job_id=job_id,
        application_id=application_id,
        drive_id=drive_id,
        status=status,
        outcome=outcome,
        mode=mode,
        date_from=date_from,
        date_to=date_to,
        search=search,
        skip=skip,
        limit=limit,
    )


@interviews_router.get(
    "/calendar",
    response_model=InterviewCalendarResponse,
    summary="Get interview events bucketed by calendar days",
)
async def get_interview_calendar_endpoint(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    job_id: Optional[int] = Query(None),
    status: Optional[InterviewStatus] = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await get_interview_calendar_events(
        session=session,
        current_user=current_user,
        date_from=date_from,
        date_to=date_to,
        job_id=job_id,
        status=status,
    )


@interviews_router.get(
    "/tpo/monitoring",
    response_model=InterviewListPortalResponse,
    summary="TPO institutional campus recruitment interview monitoring",
)
async def list_tpo_monitoring_interviews_endpoint(
    drive_id: Optional[int] = Query(None),
    company_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    status: Optional[InterviewStatus] = Query(None),
    outcome: Optional[InterviewOutcome] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_tpo),
    session: AsyncSession = Depends(get_async_session),
):
    return await list_tpo_institution_interviews(
        session=session,
        tpo_user=current_user,
        drive_id=drive_id,
        company_id=company_id,
        department_id=department_id,
        status=status,
        outcome=outcome,
        date_from=date_from,
        date_to=date_to,
        search=search,
        skip=skip,
        limit=limit,
    )


@interviews_router.get(
    "/me",
    response_model=StudentInterviewListResponse,
    summary="List upcoming, completed, and cancelled interviews for the authenticated student",
)
async def get_my_interviews_endpoint(
    interview_status: Optional[InterviewStatus] = Query(None, alias="status"),
    company: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    current_user: User = Depends(require_student),
    session: AsyncSession = Depends(get_async_session),
):
    interviews = await list_student_interviews(
        session=session,
        student_user=current_user,
        interview_status=interview_status if isinstance(interview_status, InterviewStatus) else None,
        company_query=company if isinstance(company, str) else None,
        date_from=date_from if isinstance(date_from, datetime) else None,
        date_to=date_to if isinstance(date_to, datetime) else None,
    )
    now_utc = datetime.now(timezone.utc)
    upcoming: List[StudentInterviewTrackingItem] = []
    completed: List[StudentInterviewTrackingItem] = []
    cancelled_or_other: List[StudentInterviewTrackingItem] = []

    for iv in interviews:
        app = getattr(iv, "application", None)
        job = getattr(app, "job", None) if app else None
        company_obj = getattr(job, "company", None) if job else None
        drive = getattr(app, "drive", None) if app else None
        redacted = _map_interview_to_response(iv, is_student=True)
        iv_start = iv.scheduled_start_time
        if iv_start.tzinfo is None:
            iv_start = iv_start.replace(tzinfo=timezone.utc)
        is_upcoming = iv.status == InterviewStatus.SCHEDULED and iv_start >= now_utc - timedelta(minutes=15)
        item = StudentInterviewTrackingItem(
            **redacted.model_dump(),
            company_name=company_obj.name if company_obj else None,
            job_title=job.title if job else None,
            drive_name=drive.name if drive else None,
            application_status=app.current_status if app else ApplicationStatus.INTERVIEW_SCHEDULED,
            is_upcoming=is_upcoming,
            reschedule_note=iv.cancellation_reason if redacted.is_rescheduled else None,
        )
        if iv.status == InterviewStatus.COMPLETED:
            completed.append(item)
        elif iv.status == InterviewStatus.SCHEDULED and is_upcoming:
            upcoming.append(item)
        else:
            cancelled_or_other.append(item)

    return StudentInterviewListResponse(
        upcoming=upcoming,
        completed=completed,
        cancelled_or_other=cancelled_or_other,
        total=len(interviews),
    )


@applications_router.get(
    "/{application_id}/interviews",
    response_model=List[InterviewResponse] | List[InterviewStudentResponse],
    summary="List all interview rounds for an application (scoped & redacted)",
)
async def list_application_interviews_endpoint(
    application_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(JobApplication)
        .options(
            selectinload(JobApplication.job),
            selectinload(JobApplication.student_profile),
            selectinload(JobApplication.interviews),
        )
        .where(JobApplication.id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise EntityNotFoundException("JobApplication", application_id)

    # Scoping check
    is_student_owner = (
        current_user.role == UserRole.STUDENT
        and application.student_profile
        and application.student_profile.user_id == current_user.id
    )
    is_recruiter_owner = False
    if current_user.role == UserRole.RECRUITER and current_user.recruiter_profile and application.job:
        is_recruiter_owner = current_user.recruiter_profile.company_id == application.job.company_id

    is_tpo = current_user.role == UserRole.TPO and current_user.institution_id == getattr(application.drive, "institution_id", None)
    is_admin = current_user.role == UserRole.ADMIN

    if not (is_student_owner or is_recruiter_owner or is_tpo or is_admin):
        raise AuthorizationException("You do not have permission to view interviews for this application.")

    interviews = sorted(application.interviews or [], key=lambda i: i.round_number)
    if is_student_owner and not (is_recruiter_owner or is_tpo or is_admin):
        return [_map_interview_to_response(i, is_student=True) for i in interviews]
    return [_map_interview_to_response(i, is_student=False) for i in interviews]


@interviews_router.post(
    "/{interview_id}/reschedule",
    response_model=InterviewResponse,
    summary="Reschedule an interview round with collision check",
)
async def reschedule_interview_endpoint(
    interview_id: int,
    payload: InterviewRescheduleRequest,
    current_user: User = Depends(require_recruiter),
    session: AsyncSession = Depends(get_async_session),
):
    updated = await reschedule_interview(
        session=session,
        recruiter_user=current_user,
        interview_id=interview_id,
        new_start_time=payload.scheduled_start_time,
        new_duration_minutes=payload.duration_minutes,
        meeting_link=payload.meeting_link,
        location=payload.location,
        instructions=getattr(payload, "instructions", None),
        reason=payload.reason,
    )
    return _map_interview_to_response(updated, is_student=False)


@interviews_router.post(
    "/{interview_id}/cancel",
    response_model=InterviewResponse,
    summary="Cancel an interview round with round-aware lifecycle reversion",
)
async def cancel_interview_endpoint(
    interview_id: int,
    payload: InterviewCancelRequest,
    current_user: User = Depends(require_recruiter),
    session: AsyncSession = Depends(get_async_session),
):
    cancelled = await cancel_interview(
        session=session,
        recruiter_user=current_user,
        interview_id=interview_id,
        reason=payload.reason,
    )
    return _map_interview_to_response(cancelled, is_student=False)


@interviews_router.post(
    "/{interview_id}/outcome",
    response_model=InterviewResponse,
    summary="Record interview outcome (completed round; does NOT auto-reject application)",
)
async def record_interview_outcome_endpoint(
    interview_id: int,
    payload: InterviewOutcomeRequest,
    current_user: User = Depends(require_recruiter),
    session: AsyncSession = Depends(get_async_session),
):
    completed = await record_interview_outcome(
        session=session,
        recruiter_user=current_user,
        interview_id=interview_id,
        outcome=payload.outcome,
        feedback_notes=payload.feedback_notes,
    )
    return _map_interview_to_response(completed, is_student=False)


@interviews_router.get(
    "/{interview_id}",
    response_model=InterviewWorkspaceDetailResponse,
    summary="Get full interviewer workspace detail for a specific interview round",
)
async def get_interview_workspace_endpoint(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    return await get_interview_workspace_detail(
        session=session,
        interview_id=interview_id,
        current_user=current_user,
    )


# =============================================================================
# 8. In-App Notifications, Unread Counts & Read Tracking
# =============================================================================

@notifications_router.get(
    "",
    response_model=List[NotificationResponse],
    summary="List authenticated user's notifications",
)
async def list_notifications_endpoint(
    unread_only: bool = Query(False, description="Filter for unread notifications only"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    actual_unread_only = unread_only if isinstance(unread_only, bool) else False
    actual_skip = skip if isinstance(skip, int) else 0
    actual_limit = limit if isinstance(limit, int) else 50
    notifications = await list_notifications(
        session=session,
        user_id=current_user.id,
        limit=actual_limit,
        offset=actual_skip,
        unread_only=actual_unread_only,
    )
    return [NotificationResponse.model_validate(n) for n in notifications]


@notifications_router.get(
    "/unread-count",
    response_model=NotificationUnreadCountResponse,
    summary="Get count of unread notifications for authenticated user",
)
async def get_unread_count_endpoint(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    count = await get_unread_count(
        session=session,
        user_id=current_user.id,
    )
    return NotificationUnreadCountResponse(unread_count=count)


@notifications_router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark a specific notification as read (recipient only)",
)
async def mark_notification_read_endpoint(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    updated = await mark_as_read(
        session=session,
        notification_id=notification_id,
        user_id=current_user.id,
    )
    return NotificationResponse.model_validate(updated)


@notifications_router.post(
    "/mark-all-read",
    summary="Mark all unread notifications as read for authenticated user",
)
async def mark_all_read_endpoint(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    count = await mark_all_as_read(
        session=session,
        user_id=current_user.id,
    )
    return {"marked_read_count": count}


@notifications_router.get(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    summary="Get authenticated user's smart notification preferences",
)
async def get_notification_preferences_endpoint(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    pref = await get_or_create_notification_preferences(session=session, user_id=current_user.id)
    return NotificationPreferenceResponse.model_validate(pref)


@notifications_router.put(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    summary="Update authenticated user's smart notification preferences",
)
async def update_notification_preferences_endpoint(
    payload: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    pref = await update_notification_preferences(
        session=session,
        user_id=current_user.id,
        interview_schedules=payload.interview_schedules,
        upcoming_interview_reminders=payload.upcoming_interview_reminders,
        status_changes=payload.status_changes,
        offer_alerts=payload.offer_alerts,
        offer_deadline_reminders=payload.offer_deadline_reminders,
        placement_announcements=payload.placement_announcements,
        reminder_hours_before=payload.reminder_hours_before,
    )
    return NotificationPreferenceResponse.model_validate(pref)


@notifications_router.post(
    "/sync",
    response_model=NotificationSyncResponse,
    summary="Evaluate and generate deduplicated smart placement notifications for student",
)
async def sync_smart_notifications_endpoint(
    current_user: User = Depends(require_student),
    session: AsyncSession = Depends(get_async_session),
):
    created = await sync_smart_student_notifications(session=session, student_user=current_user)
    return NotificationSyncResponse(
        generated_count=len(created),
        notifications=[NotificationResponse.model_validate(n) for n in created],
    )


# =============================================================================
# TPO Command Center & Admin Analytics Endpoints
# =============================================================================

@router.get(
    "/placement/tpo/overview",
    response_model=TpoOverviewResponse,
    summary="Get live placement statistics for TPO Command Center",
)
@router.get(
    "/tpo/overview",
    response_model=TpoOverviewResponse,
    summary="Get live placement statistics for TPO Command Center (alias)",
)
async def get_tpo_overview_endpoint(
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
):
    institution_id = current_user.institution_id or 1
    now_utc = datetime.now(timezone.utc)
    week_ahead = now_utc + timedelta(days=7)

    cohort_stmt = (
        select(func.count(StudentProfile.id))
        .join(User, StudentProfile.user_id == User.id)
        .where(
            User.institution_id == institution_id,
            (User.role == UserRole.STUDENT) | (User.email == "maheshwarijaya03@gmail.com"),
            User.is_active.is_(True),
        )
    )
    total_cohort = (await session.execute(cohort_stmt)).scalar() or 0

    batches_stmt = (
        select(StudentProfile.graduation_year)
        .join(User, StudentProfile.user_id == User.id)
        .where(
            User.institution_id == institution_id,
            User.role == UserRole.STUDENT,
            User.is_active.is_(True),
            StudentProfile.graduation_year.isnot(None),
        )
        .distinct()
        .order_by(StudentProfile.graduation_year)
    )
    available_batches = [
        int(y) for y in (await session.execute(batches_stmt)).scalars().all() if y is not None
    ]
    if len(available_batches) == 1:
        target_batch_label = f"Class of {available_batches[0]}"
    elif len(available_batches) > 1:
        target_batch_label = f"Batches {', '.join(map(str, available_batches))}"
    else:
        target_batch_label = "No Cohort Registered"

    placed_stmt = (
        select(func.count(func.distinct(JobApplication.student_id)))
        .join(StudentProfile, JobApplication.student_id == StudentProfile.id)
        .join(User, StudentProfile.user_id == User.id)
        .where(
            User.institution_id == institution_id,
            JobApplication.current_status.in_([
                ApplicationStatus.OFFER_ACCEPTED,
                ApplicationStatus.OFFERED,
            ]),
        )
    )
    placed_students = (await session.execute(placed_stmt)).scalar() or 0
    placement_rate = round((placed_students / max(1, total_cohort)) * 100, 1) if total_cohort > 0 else 0.0

    drives_stmt = select(func.count(PlacementDrive.id)).where(
        PlacementDrive.institution_id == institution_id,
        PlacementDrive.status == DriveStatus.ONGOING,
        PlacementDrive.is_active.is_(True),
    )
    active_drives = (await session.execute(drives_stmt)).scalar() or 0

    jobs_cnt_stmt = select(func.count(Job.id)).where(
        Job.is_active.is_(True),
        Job.status == JobStatus.PUBLISHED,
    )
    published_jobs = (await session.execute(jobs_cnt_stmt)).scalar() or 0

    visiting_stmt = select(func.count(Job.id)).where(
        Job.is_active.is_(True),
        Job.status == JobStatus.PUBLISHED,
        Job.application_deadline >= now_utc,
        Job.application_deadline <= week_ahead,
    )
    visiting_this_week = (await session.execute(visiting_stmt)).scalar() or 0

    offer_pkg_stmt = (
        select(func.avg(Job.ctc_lpa), func.max(Job.ctc_lpa))
        .join(JobApplication, JobApplication.job_id == Job.id)
        .join(StudentProfile, JobApplication.student_id == StudentProfile.id)
        .join(User, StudentProfile.user_id == User.id)
        .where(
            User.institution_id == institution_id,
            JobApplication.current_status.in_([
                ApplicationStatus.OFFER_ACCEPTED,
                ApplicationStatus.OFFERED,
            ]),
        )
    )
    avg_offer_raw, max_offer_raw = (await session.execute(offer_pkg_stmt)).one()
    avg_package = float(avg_offer_raw or 0.0)
    highest_package = float(max_offer_raw or 0.0)

    top_open_stmt = select(func.max(Job.ctc_lpa)).where(
        Job.is_active.is_(True),
        Job.status == JobStatus.PUBLISHED,
    )
    top_open_ctc = float((await session.execute(top_open_stmt)).scalar() or 0.0)

    depts_stmt = (
        select(Department)
        .where(Department.institution_id == institution_id, Department.is_active.is_(True))
        .order_by(Department.id)
    )
    departments = (await session.execute(depts_stmt)).scalars().all()
    department_stats = []
    for d in departments:
        d_tot_stmt = (
            select(func.count(StudentProfile.id))
            .join(User, StudentProfile.user_id == User.id)
            .where(User.department_id == d.id, User.is_active.is_(True))
        )
        d_total = (await session.execute(d_tot_stmt)).scalar() or 0

        d_pl_stmt = (
            select(func.count(func.distinct(JobApplication.student_id)))
            .join(StudentProfile, JobApplication.student_id == StudentProfile.id)
            .join(User, StudentProfile.user_id == User.id)
            .where(
                User.department_id == d.id,
                JobApplication.current_status.in_([
                    ApplicationStatus.OFFER_ACCEPTED,
                    ApplicationStatus.OFFERED,
                ]),
            )
        )
        d_placed = (await session.execute(d_pl_stmt)).scalar() or 0
        d_rate = round((d_placed / max(1, d_total)) * 100, 1) if d_total > 0 else 0.0
        department_stats.append(
            DepartmentPlacementStat(
                name=d.code,
                dept_name=d.name,
                total=d_total,
                placed=d_rate,
                placed_count=d_placed,
            )
        )

    return TpoOverviewResponse(
        total_cohort=total_cohort,
        target_batch=target_batch_label,
        available_batches=available_batches,
        placed_students=placed_students,
        placement_rate=placement_rate,
        active_drives=active_drives,
        published_jobs=published_jobs,
        visiting_this_week=visiting_this_week,
        average_package_lpa=round(float(avg_package), 1),
        highest_package_lpa=round(float(highest_package), 1),
        top_open_ctc_lpa=round(top_open_ctc, 1),
        department_stats=department_stats,
    )


@router.get(
    "/placement/tpo/students",
    response_model=TpoStudentRosterResponse,
    summary="List institutional students with hired, pipeline, and unplaced status",
)
@router.get(
    "/tpo/students",
    response_model=TpoStudentRosterResponse,
    summary="List institutional students with hired, pipeline, and unplaced status (alias)",
)
async def get_tpo_students_roster_endpoint(
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
):
    institution_id = current_user.institution_id or 1

    stmt = (
        select(StudentProfile)
        .join(User, StudentProfile.user_id == User.id)
        .options(
            selectinload(StudentProfile.user).selectinload(User.department),
            selectinload(StudentProfile.skills),
            selectinload(StudentProfile.resumes),
            selectinload(StudentProfile.applications)
            .selectinload(JobApplication.job)
            .selectinload(Job.company),
        )
        .where(
            User.institution_id == institution_id,
            (User.role == UserRole.STUDENT) | (User.email == "maheshwarijaya03@gmail.com"),
            User.is_active.is_(True),
        )
        .order_by(StudentProfile.cgpa.desc(), User.full_name.asc())
    )
    profiles = (await session.execute(stmt)).scalars().all()

    pipeline_states = {
        ApplicationStatus.APPLIED,
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.SHORTLISTED,
        ApplicationStatus.INTERVIEW_SCHEDULED,
        ApplicationStatus.INTERVIEWED,
    }
    hired_states = {
        ApplicationStatus.OFFER_ACCEPTED,
        ApplicationStatus.OFFERED,
    }

    roster: List[TpoStudentRosterItem] = []
    hired_count = 0
    offer_accepted_count = 0
    offer_pending_count = 0
    in_pipeline_count = 0
    not_hired_count = 0

    for prof in profiles:
        u = prof.user
        dept = u.department if u else None
        active_apps = [
            app for app in (prof.applications or [])
            if app.current_status != ApplicationStatus.WITHDRAWN
        ]
        hired_apps = [app for app in active_apps if app.current_status in hired_states]
        active_pipeline_apps = [app for app in active_apps if app.current_status in pipeline_states]

        hired_company = None
        hired_role = None
        hired_ctc_lpa = None

        if hired_apps:
            hired_apps.sort(
                key=lambda a: (
                    1 if a.current_status == ApplicationStatus.OFFER_ACCEPTED else 0,
                    float(a.job.ctc_lpa) if (a.job and a.job.ctc_lpa is not None) else 0.0,
                ),
                reverse=True,
            )
            best = hired_apps[0]
            placement_status = "hired"
            offer_state = best.current_status.value
            hired_company = best.job.company.name if (best.job and best.job.company) else None
            hired_role = best.job.title if best.job else None
            hired_ctc_lpa = float(best.job.ctc_lpa) if (best.job and best.job.ctc_lpa is not None) else None
            hired_count += 1
            if best.current_status == ApplicationStatus.OFFER_ACCEPTED:
                offer_accepted_count += 1
            else:
                offer_pending_count += 1
        elif active_pipeline_apps:
            active_pipeline_apps.sort(
                key=lambda a: a.updated_at or a.created_at,
                reverse=True,
            )
            placement_status = "in_pipeline"
            offer_state = active_pipeline_apps[0].current_status.value
            in_pipeline_count += 1
        elif active_apps:
            sorted_apps = sorted(
                active_apps,
                key=lambda a: a.updated_at or a.created_at,
                reverse=True,
            )
            placement_status = "not_hired"
            offer_state = sorted_apps[0].current_status.value
            not_hired_count += 1
        else:
            placement_status = "not_hired"
            offer_state = "unapplied"
            not_hired_count += 1

        pipeline_labels = [
            f"{app.job.company.name if (app.job and app.job.company) else 'Company'} — {app.job.title if app.job else 'Role'}"
            for app in active_pipeline_apps[:3]
        ]

        approved_resumes = sum(
            1 for r in (prof.resumes or [])
            if r.parsing_status == "approved" and r.is_active
        )

        dept_id = dept.id if dept else None
        is_branch_verified = bool(
            dept
            and dept.id
            and dept.name
            and dept.code not in ("GEN", "UNASSIGNED", "")
            and getattr(u, "is_verified", True)
        )

        roster.append(
            TpoStudentRosterItem(
                student_id=prof.id,
                user_id=u.id,
                full_name=u.full_name,
                email=u.email,
                roll_number=prof.roll_number,
                department_id=dept_id,
                department_code=dept.code if dept else "GEN",
                department_name=dept.name if dept else "General",
                is_branch_verified=is_branch_verified,
                graduation_year=prof.graduation_year,
                cgpa=round(float(prof.cgpa or 0.0), 2),
                active_backlogs=prof.active_backlogs,
                total_backlogs=prof.total_backlogs,
                is_placement_ready=prof.is_placement_ready,
                skills=[s.skill_name for s in (prof.skills or [])],
                approved_resumes_count=approved_resumes,
                applications_count=len(active_apps),
                placement_status=placement_status,
                offer_state=offer_state,
                hired_company=hired_company,
                hired_role=hired_role,
                hired_ctc_lpa=hired_ctc_lpa,
                active_pipeline_roles=pipeline_labels,
            )
        )

    status_rank = {"hired": 0, "in_pipeline": 1, "not_hired": 2}
    roster.sort(
        key=lambda item: (
            status_rank.get(item.placement_status, 3),
            -(item.hired_ctc_lpa or 0.0),
            -item.cgpa,
            item.full_name,
        )
    )

    unverified_count = sum(1 for item in roster if not item.is_branch_verified)

    return TpoStudentRosterResponse(
        total_students=len(roster),
        hired_count=hired_count,
        offer_accepted_count=offer_accepted_count,
        offer_pending_count=offer_pending_count,
        in_pipeline_count=in_pipeline_count,
        not_hired_count=not_hired_count,
        unverified_count=unverified_count,
        students=roster,
    )


@router.post(
    "/placement/tpo/simulate-eligibility",
    response_model=EligibilitySimulationResponse,
    summary="Interactive Student Eligibility Simulator query builder",
)
@router.post(
    "/tpo/simulate-eligibility",
    response_model=EligibilitySimulationResponse,
    summary="Interactive Student Eligibility Simulator query builder (alias)",
)
async def simulate_eligibility_endpoint(
    criteria: EligibilitySimulationRequest,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
):
    institution_id = current_user.institution_id or 1

    # Base query for all students in scope
    base_stmt = (
        select(StudentProfile, User, Department)
        .join(User, StudentProfile.user_id == User.id)
        .outerjoin(Department, User.department_id == Department.id)
        .where(
            User.institution_id == institution_id,
            (User.role == UserRole.STUDENT) | (User.email == "maheshwarijaya03@gmail.com"),
            User.is_active.is_(True),
        )
    )

    if criteria.target_batch:
        base_stmt = base_stmt.where(StudentProfile.graduation_year == criteria.target_batch)

    all_students_res = (await session.execute(base_stmt)).all()
    total_cohort_count = len(all_students_res)

    # Filtered query for eligible students
    filter_stmt = base_stmt.where(
        StudentProfile.cgpa >= criteria.min_cgpa,
        StudentProfile.active_backlogs <= criteria.max_active_backlogs,
    )
    if criteria.max_total_backlogs is not None:
        filter_stmt = filter_stmt.where(StudentProfile.total_backlogs <= criteria.max_total_backlogs)
    if criteria.department_codes:
        filter_stmt = filter_stmt.where(Department.code.in_(criteria.department_codes))

    filter_stmt = (
        filter_stmt.order_by(StudentProfile.cgpa.desc(), User.full_name.asc())
    )
    eligible_rows = (await session.execute(filter_stmt)).all()
    eligible_count = len(eligible_rows)
    percentage = round((eligible_count / max(1, total_cohort_count)) * 100, 1) if total_cohort_count > 0 else 0.0

    # Build student summaries
    matching_students = []
    for prof, user, dept in eligible_rows[:200]:
        skills_stmt = select(StudentSkill.skill_name).where(StudentSkill.student_id == prof.id)
        skills = (await session.execute(skills_stmt)).scalars().all()

        matching_students.append(
            SimulatedStudentSummary(
                student_id=prof.id,
                name=user.full_name,
                email=user.email,
                roll_number=prof.roll_number,
                department=dept.code if dept else "General",
                graduation_year=prof.graduation_year,
                cgpa=float(prof.cgpa or 0.0),
                active_backlogs=prof.active_backlogs,
                skills=list(skills),
            )
        )

    return EligibilitySimulationResponse(
        eligible_count=eligible_count,
        total_cohort_count=total_cohort_count,
        eligible_percentage=percentage,
        criteria_summary={
            "target_batch": criteria.target_batch or "All Batches",
            "min_cgpa": criteria.min_cgpa,
            "max_active_backlogs": criteria.max_active_backlogs,
            "max_total_backlogs": criteria.max_total_backlogs,
            "departments": criteria.department_codes or ["All"],
        },
        matching_students=matching_students,
    )


@router.get(
    "/placement/admin/overview",
    response_model=AdminOverviewResponse,
    summary="Get system overview and user directory metrics for System Administrator",
)
@router.get(
    "/admin/overview",
    response_model=AdminOverviewResponse,
    summary="Get system overview and user directory metrics for System Administrator (alias)",
)
async def get_admin_overview_endpoint(
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session),
):
    total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
    students_cnt = (await session.execute(select(func.count(User.id)).where(User.role == UserRole.STUDENT))).scalar() or 0
    recruiters_cnt = (await session.execute(select(func.count(User.id)).where(User.role == UserRole.RECRUITER))).scalar() or 0
    tpos_cnt = (await session.execute(select(func.count(User.id)).where(User.role == UserRole.TPO))).scalar() or 0
    admins_cnt = (await session.execute(select(func.count(User.id)).where(User.role == UserRole.ADMIN))).scalar() or 0

    inst_cnt = (await session.execute(select(func.count(Institution.id)).where(Institution.is_active.is_(True)))).scalar() or 0
    depts_cnt = (await session.execute(select(func.count(Department.id)).where(Department.is_active.is_(True)))).scalar() or 0
    comps_cnt = (await session.execute(select(func.count(Company.id)).where(Company.is_active.is_(True)))).scalar() or 0
    jobs_cnt = (await session.execute(select(func.count(Job.id)).where(Job.is_active.is_(True)))).scalar() or 0
    drives_cnt = (await session.execute(select(func.count(PlacementDrive.id)).where(PlacementDrive.is_active.is_(True)))).scalar() or 0
    apps_cnt = (await session.execute(select(func.count(JobApplication.id)))).scalar() or 0

    role_dist = [
        UserRoleCount(
            role="Students",
            count=students_cnt,
            percentage=round((students_cnt / max(1, total_users)) * 100, 1) if total_users > 0 else 0.0,
        ),
        UserRoleCount(
            role="Recruiters",
            count=recruiters_cnt,
            percentage=round((recruiters_cnt / max(1, total_users)) * 100, 1) if total_users > 0 else 0.0,
        ),
        UserRoleCount(
            role="TPO Coordinators",
            count=tpos_cnt,
            percentage=round((tpos_cnt / max(1, total_users)) * 100, 1) if total_users > 0 else 0.0,
        ),
        UserRoleCount(
            role="System Administrators",
            count=admins_cnt,
            percentage=round((admins_cnt / max(1, total_users)) * 100, 1) if total_users > 0 else 0.0,
        ),
    ]

    return AdminOverviewResponse(
        total_users=total_users,
        role_distribution=role_dist,
        students_count=students_cnt,
        recruiters_count=recruiters_cnt,
        tpos_count=tpos_cnt,
        admins_count=admins_cnt,
        institutions_count=inst_cnt,
        departments_count=depts_cnt,
        companies_count=comps_cnt,
        jobs_count=jobs_cnt,
        drives_count=drives_cnt,
        applications_count=apps_cnt,
    )


@recruiter_router.get(
    "/overview",
    response_model=RecruiterOverviewResponse,
    summary="Get live recruitment pipeline statistics for Recruiter Command Center",
)
@router.get(
    "/placement/recruiter/overview",
    response_model=RecruiterOverviewResponse,
    summary="Get live recruitment pipeline statistics for Recruiter Command Center (alias)",
)
async def get_recruiter_overview_endpoint(
    current_user: User = Depends(require_recruiter),
    session: AsyncSession = Depends(get_async_session),
):
    rec_prof_stmt = (
        select(RecruiterProfile)
        .options(selectinload(RecruiterProfile.company))
        .where(RecruiterProfile.user_id == current_user.id)
    )
    rec_prof = (await session.execute(rec_prof_stmt)).scalar_one_or_none()
    company_id = rec_prof.company_id if rec_prof else None
    company_name = rec_prof.company.name if (rec_prof and rec_prof.company) else None

    if not company_id and current_user.role != UserRole.ADMIN:
        return RecruiterOverviewResponse(
            company_id=None,
            company_name=None,
            active_jobs_count=0,
            total_applicants=0,
            shortlisted_count=0,
            offers_released=0,
            offers_accepted=0,
            recent_applications=[],
        )

    jobs_stmt = select(func.count(Job.id)).where(
        Job.is_active.is_(True),
        Job.status == JobStatus.PUBLISHED,
    )
    if company_id:
        jobs_stmt = jobs_stmt.where(Job.company_id == company_id)
    active_jobs_count = (await session.execute(jobs_stmt)).scalar() or 0

    base_app_filter = [JobApplication.current_status != ApplicationStatus.WITHDRAWN]
    if company_id:
        base_app_filter.append(Job.company_id == company_id)

    total_app_stmt = (
        select(func.count(JobApplication.id))
        .join(Job, JobApplication.job_id == Job.id)
        .where(*base_app_filter)
    )
    total_applicants = (await session.execute(total_app_stmt)).scalar() or 0

    shortlisted_stmt = (
        select(func.count(JobApplication.id))
        .join(Job, JobApplication.job_id == Job.id)
        .where(
            *base_app_filter,
            JobApplication.current_status.in_([
                ApplicationStatus.SHORTLISTED,
                ApplicationStatus.INTERVIEW_SCHEDULED,
            ]),
        )
    )
    shortlisted_count = (await session.execute(shortlisted_stmt)).scalar() or 0

    offers_stmt = (
        select(func.count(JobApplication.id))
        .join(Job, JobApplication.job_id == Job.id)
        .where(
            *base_app_filter,
            JobApplication.current_status.in_([
                ApplicationStatus.OFFERED,
                ApplicationStatus.OFFER_ACCEPTED,
            ]),
        )
    )
    offers_released = (await session.execute(offers_stmt)).scalar() or 0

    accepted_stmt = (
        select(func.count(JobApplication.id))
        .join(Job, JobApplication.job_id == Job.id)
        .where(
            *base_app_filter,
            JobApplication.current_status == ApplicationStatus.OFFER_ACCEPTED,
        )
    )
    offers_accepted = (await session.execute(accepted_stmt)).scalar() or 0

    recent_stmt = (
        select(JobApplication)
        .join(Job, JobApplication.job_id == Job.id)
        .options(
            selectinload(JobApplication.job).selectinload(Job.company),
            selectinload(JobApplication.drive),
            selectinload(JobApplication.student_profile)
            .selectinload(StudentProfile.user)
            .selectinload(User.department),
        )
        .where(*base_app_filter)
        .order_by(JobApplication.created_at.desc())
        .limit(20)
    )
    recent_apps = (await session.execute(recent_stmt)).scalars().all()

    return RecruiterOverviewResponse(
        company_id=company_id,
        company_name=company_name or ("All Partner Companies" if current_user.role == UserRole.ADMIN else None),
        active_jobs_count=active_jobs_count,
        total_applicants=total_applicants,
        shortlisted_count=shortlisted_count,
        offers_released=offers_released,
        offers_accepted=offers_accepted,
        recent_applications=[_map_application_to_response(app, is_recruiter=True) for app in recent_apps],
    )


# Mount all subrouters onto master placement router
router.include_router(drives_router)
router.include_router(applications_router)
router.include_router(interviews_router)
router.include_router(notifications_router)
router.include_router(recruiter_router)
