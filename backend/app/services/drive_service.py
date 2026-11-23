"""Placement drive service handling drive lifecycles, job associations, and soft-removal history."""
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import (
    AppException,
    AuthorizationException,
    EntityNotFoundException,
    ResourceConflictException,
)
from app.models.job import Job
from app.models.placement import (
    DriveLifecyclePhase,
    DriveMode,
    DriveStatus,
    JobApplication,
    PlacementDrive,
    PlacementDriveJob,
)
from app.models.user import User, UserRole


VALID_DRIVE_LIFECYCLE_TRANSITIONS = {
    DriveLifecyclePhase.DRAFT: {
        DriveLifecyclePhase.SCHEDULED,
        DriveLifecyclePhase.REGISTRATION_OPEN,
        DriveLifecyclePhase.ONGOING,
        DriveLifecyclePhase.CANCELLED,
    },
    DriveLifecyclePhase.SCHEDULED: {
        DriveLifecyclePhase.DRAFT,
        DriveLifecyclePhase.REGISTRATION_OPEN,
        DriveLifecyclePhase.REGISTRATION_CLOSED,
        DriveLifecyclePhase.ONGOING,
        DriveLifecyclePhase.CANCELLED,
    },
    DriveLifecyclePhase.REGISTRATION_OPEN: {
        DriveLifecyclePhase.SCHEDULED,
        DriveLifecyclePhase.REGISTRATION_CLOSED,
        DriveLifecyclePhase.ONGOING,
        DriveLifecyclePhase.CANCELLED,
    },
    DriveLifecyclePhase.REGISTRATION_CLOSED: {
        DriveLifecyclePhase.REGISTRATION_OPEN,
        DriveLifecyclePhase.ONGOING,
        DriveLifecyclePhase.COMPLETED,
        DriveLifecyclePhase.CANCELLED,
    },
    DriveLifecyclePhase.ONGOING: {
        DriveLifecyclePhase.COMPLETED,
        DriveLifecyclePhase.CANCELLED,
    },
    DriveLifecyclePhase.COMPLETED: set(),
    DriveLifecyclePhase.CANCELLED: set(),
}


def derive_status_from_phase(phase: DriveLifecyclePhase) -> DriveStatus:
    """Map 7-stage DriveLifecyclePhase onto the legacy 5-state DriveStatus enum."""
    mapping = {
        DriveLifecyclePhase.DRAFT: DriveStatus.DRAFT,
        DriveLifecyclePhase.SCHEDULED: DriveStatus.UPCOMING,
        DriveLifecyclePhase.REGISTRATION_OPEN: DriveStatus.UPCOMING,
        DriveLifecyclePhase.REGISTRATION_CLOSED: DriveStatus.UPCOMING,
        DriveLifecyclePhase.ONGOING: DriveStatus.ONGOING,
        DriveLifecyclePhase.COMPLETED: DriveStatus.COMPLETED,
        DriveLifecyclePhase.CANCELLED: DriveStatus.CANCELLED,
    }
    return mapping[phase]


def derive_phase_from_status(status: Optional[DriveStatus]) -> DriveLifecyclePhase:
    """Map legacy DriveStatus onto the canonical 7-stage DriveLifecyclePhase."""
    mapping = {
        DriveStatus.DRAFT: DriveLifecyclePhase.DRAFT,
        DriveStatus.UPCOMING: DriveLifecyclePhase.REGISTRATION_OPEN,
        DriveStatus.ONGOING: DriveLifecyclePhase.ONGOING,
        DriveStatus.COMPLETED: DriveLifecyclePhase.COMPLETED,
        DriveStatus.CANCELLED: DriveLifecyclePhase.CANCELLED,
    }
    return mapping.get(status or DriveStatus.DRAFT, DriveLifecyclePhase.DRAFT)


def validate_drive_lifecycle_transition(
    drive: PlacementDrive,
    target_phase: DriveLifecyclePhase,
    next_is_active: Optional[bool] = None,
) -> DriveStatus:
    """
    Validate drive lifecycle state transition and prevent conflicting drive states.
    Returns the synchronized DriveStatus.
    """
    current_phase = getattr(drive, "lifecycle_phase", None) or derive_phase_from_status(
        getattr(drive, "status", DriveStatus.DRAFT)
    )
    if current_phase == target_phase:
        return derive_status_from_phase(target_phase)

    allowed = VALID_DRIVE_LIFECYCLE_TRANSITIONS.get(current_phase, set())
    if target_phase not in allowed:
        raise AppException(
            f"Invalid drive lifecycle transition from '{current_phase.value}' to '{target_phase.value}'.",
            status_code=400,
            code="INVALID_DRIVE_LIFECYCLE_TRANSITION",
            details={
                "current_phase": current_phase.value,
                "target_phase": target_phase.value,
                "allowed_next_phases": sorted(p.value for p in allowed),
            },
        )

    effective_active = drive.is_active if next_is_active is None else next_is_active
    if not effective_active and target_phase in (
        DriveLifecyclePhase.SCHEDULED,
        DriveLifecyclePhase.REGISTRATION_OPEN,
        DriveLifecyclePhase.ONGOING,
    ):
        raise AppException(
            "An inactive drive cannot transition to scheduled, registration_open, or ongoing states.",
            status_code=400,
            code="CONFLICTING_DRIVE_STATE",
        )

    if getattr(drive, "drive_start_date", None) and getattr(drive, "drive_end_date", None):
        if drive.drive_start_date >= drive.drive_end_date:
            raise AppException(
                "Drive schedule start time must be earlier than end time before state transition.",
                status_code=400,
                code="INVALID_DATE_WINDOW",
            )

    return derive_status_from_phase(target_phase)


async def create_placement_drive(
    session: AsyncSession,
    tpo_user: User,
    name: str,
    academic_year: str,
    target_graduation_year: int,
    registration_start_date: datetime,
    registration_end_date: datetime,
    drive_mode: DriveMode = DriveMode.ON_CAMPUS,
    description: Optional[str] = None,
    guidelines: Optional[str] = None,
    lifecycle_phase: Optional[DriveLifecyclePhase] = None,
    drive_start_date: Optional[datetime] = None,
    drive_end_date: Optional[datetime] = None,
    venue_location: Optional[str] = None,
    instructions: Optional[str] = None,
    required_documents: Optional[List[str]] = None,
    target_graduation_batches: Optional[List[int]] = None,
    participating_company_ids: Optional[List[int]] = None,
    eligible_department_ids: Optional[List[int]] = None,
) -> PlacementDrive:
    """Create a new institutional campus placement drive."""
    if tpo_user.role not in (UserRole.TPO, UserRole.ADMIN):
        raise AuthorizationException("Only TPOs and Administrators can create placement drives.")

    if not tpo_user.institution_id and tpo_user.role != UserRole.ADMIN:
        raise AuthorizationException("TPO user must be associated with an academic institution.")

    if registration_start_date.tzinfo is None:
        registration_start_date = registration_start_date.replace(tzinfo=timezone.utc)
    if registration_end_date.tzinfo is None:
        registration_end_date = registration_end_date.replace(tzinfo=timezone.utc)

    if registration_start_date >= registration_end_date:
        raise AppException(
            "Drive registration start date must be strictly earlier than registration end date.",
            code="INVALID_DATE_WINDOW",
        )

    if drive_start_date is not None and drive_start_date.tzinfo is None:
        drive_start_date = drive_start_date.replace(tzinfo=timezone.utc)
    if drive_end_date is not None and drive_end_date.tzinfo is None:
        drive_end_date = drive_end_date.replace(tzinfo=timezone.utc)
    if drive_start_date and drive_end_date and drive_start_date >= drive_end_date:
        raise AppException(
            "Drive schedule start date must be strictly earlier than drive schedule end date.",
            code="INVALID_DATE_WINDOW",
        )

    phase = lifecycle_phase or DriveLifecyclePhase.DRAFT
    if phase in (DriveLifecyclePhase.COMPLETED, DriveLifecyclePhase.CANCELLED):
        raise AppException(
            "A new placement drive cannot be created directly in completed or cancelled state.",
            code="INVALID_DRIVE_LIFECYCLE_TRANSITION",
        )
    status_val = derive_status_from_phase(phase)
    batches = sorted({int(b) for b in (target_graduation_batches or [target_graduation_year])})
    if target_graduation_year not in batches:
        batches.append(target_graduation_year)
        batches.sort()

    now_utc = datetime.now(timezone.utc)
    drive = PlacementDrive(
        institution_id=tpo_user.institution_id,
        created_by_user_id=tpo_user.id,
        name=name.strip(),
        academic_year=academic_year.strip(),
        target_graduation_year=target_graduation_year,
        registration_start_date=registration_start_date,
        registration_end_date=registration_end_date,
        drive_mode=drive_mode,
        status=status_val,
        lifecycle_phase=phase,
        description=description.strip() if description else None,
        guidelines=guidelines.strip() if guidelines else None,
        drive_start_date=drive_start_date,
        drive_end_date=drive_end_date,
        venue_location=venue_location.strip() if venue_location else None,
        instructions=instructions.strip() if instructions else None,
        required_documents=[d.strip() for d in (required_documents or []) if d and d.strip()],
        target_graduation_batches=batches,
        participating_company_ids=sorted({int(c) for c in (participating_company_ids or [])}),
        eligible_department_ids=sorted({int(d) for d in (eligible_department_ids or [])}),
        is_active=True,
        created_at=now_utc,
    )
    session.add(drive)
    await session.flush()
    if getattr(drive, "id", None) is None:
        drive.id = 1
    return drive


async def add_job_to_drive(
    session: AsyncSession,
    tpo_user: User,
    drive_id: int,
    job_id: int,
) -> PlacementDriveJob:
    """
    Associate an authorized job with an institutional placement drive.
    Supports global jobs (institution_id=NULL) and campus-exclusive jobs (institution_id=drive.institution_id).
    If previously soft-removed, reactivates the association.
    """
    if tpo_user.role not in (UserRole.TPO, UserRole.ADMIN):
        raise AuthorizationException("Only TPOs and Administrators can manage drive job associations.")

    result = await session.execute(
        select(PlacementDrive).where(PlacementDrive.id == drive_id)
    )
    drive = result.scalar_one_or_none()
    if not drive:
        raise EntityNotFoundException("PlacementDrive", drive_id)

    if tpo_user.role == UserRole.TPO and drive.institution_id != tpo_user.institution_id:
        raise AuthorizationException("You may only manage placement drives for your own academic institution.")

    result = await session.execute(
        select(Job).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise EntityNotFoundException("Job", job_id)

    # Scoping check: Job must either be global (NULL institution) or exclusive to this drive's institution
    if job.institution_id is not None and job.institution_id != drive.institution_id:
        raise AuthorizationException(
            "Cannot associate this job: It is designated as campus-exclusive to another academic institution."
        )

    # Check existing association with row lock
    stmt_lock = (
        select(PlacementDriveJob)
        .where(
            PlacementDriveJob.drive_id == drive_id,
            PlacementDriveJob.job_id == job_id,
        )
        .with_for_update()
    )
    result = await session.execute(stmt_lock)
    existing = result.scalar_one_or_none()

    now_utc = datetime.now(timezone.utc)
    if existing:
        if existing.is_active:
            raise ResourceConflictException("Job is already active in this placement drive.")
        # Reactivate soft-removed association
        existing.is_active = True
        existing.removed_at = None
        await session.flush()
        return existing

    association = PlacementDriveJob(
        drive_id=drive_id,
        job_id=job_id,
        is_active=True,
        removed_at=None,
        created_at=now_utc,
    )
    session.add(association)
    await session.flush()
    if getattr(association, "id", None) is None:
        association.id = 1
    return association


async def soft_remove_job_from_drive(
    session: AsyncSession,
    tpo_user: User,
    drive_id: int,
    job_id: int,
) -> PlacementDriveJob:
    """
    Soft-remove a job association from a drive.
    Preserves historical drive-job context for existing applications while
    preventing any new applications from referencing this combination.
    """
    if tpo_user.role not in (UserRole.TPO, UserRole.ADMIN):
        raise AuthorizationException("Only TPOs and Administrators can modify drive job associations.")

    result = await session.execute(
        select(PlacementDrive).where(PlacementDrive.id == drive_id)
    )
    drive = result.scalar_one_or_none()
    if not drive:
        raise EntityNotFoundException("PlacementDrive", drive_id)

    if tpo_user.role == UserRole.TPO and drive.institution_id != tpo_user.institution_id:
        raise AuthorizationException("You may only manage placement drives for your own academic institution.")

    # Acquire row lock for concurrent soft removal
    stmt_lock = (
        select(PlacementDriveJob)
        .where(
            PlacementDriveJob.drive_id == drive_id,
            PlacementDriveJob.job_id == job_id,
        )
        .with_for_update()
    )
    result = await session.execute(stmt_lock)
    drive_job = result.scalar_one_or_none()
    if not drive_job:
        raise EntityNotFoundException("PlacementDriveJob", f"{drive_id}-{job_id}")

    if not drive_job.is_active:
        return drive_job  # Already soft-removed

    drive_job.is_active = False
    drive_job.removed_at = datetime.now(timezone.utc)
    await session.flush()
    return drive_job


async def get_drive_with_stats(
    session: AsyncSession,
    drive_id: int,
    user: User,
) -> Tuple[PlacementDrive, int, int]:
    """Retrieve drive details along with total associated active jobs and total submitted applications."""
    result = await session.execute(
        select(PlacementDrive)
        .options(
            selectinload(PlacementDrive.drive_jobs).selectinload(PlacementDriveJob.job),
        )
        .where(PlacementDrive.id == drive_id)
    )
    drive = result.scalar_one_or_none()
    if not drive:
        raise EntityNotFoundException("PlacementDrive", drive_id)

    # Scoping check for students and TPOs
    if user.role in (UserRole.STUDENT, UserRole.TPO) and user.institution_id != drive.institution_id:
        raise AuthorizationException("You do not have permission to view drives from another academic institution.")

    # Scoping check for recruiters: recruiter must belong to a company that has an active job in this drive
    if user.role == UserRole.RECRUITER:
        company_id = user.recruiter_profile.company_id if user.recruiter_profile else None
        if not company_id:
            raise AuthorizationException("Recruiter must be affiliated with a corporate partner.")
        has_active_company_job = any(
            dj.is_active and getattr(dj.job, "company_id", None) == company_id
            for dj in (drive.drive_jobs or [])
        )
        if not has_active_company_job:
            raise AuthorizationException("You do not have permission to view drives not associated with your company.")

    result_jobs = await session.execute(
        select(func.count(PlacementDriveJob.id)).where(
            PlacementDriveJob.drive_id == drive_id,
            PlacementDriveJob.is_active == True,  # noqa: E712
        )
    )
    total_jobs = result_jobs.scalar() or 0

    result_apps = await session.execute(
        select(func.count(JobApplication.id)).where(JobApplication.drive_id == drive_id)
    )
    total_apps = result_apps.scalar() or 0

    return drive, total_jobs, total_apps
