"""Interview service handling scheduling, student locking, collision detection, and round-aware cancellation."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import (
    AppException,
    AuthorizationException,
    EntityNotFoundException,
    ResourceConflictException,
)
from app.models.candidate_evaluation import CandidateEvaluation
from app.models.company import Company, RecruiterProfile
from app.models.job import Job
from app.models.organization import Department
from app.models.placement import (
    ApplicationStatus,
    Interview,
    InterviewMode,
    InterviewOutcome,
    InterviewStatus,
    JobApplication,
    NotificationCategory,
    PlacementDrive,
    TpoScreeningStatus,
)
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from app.schemas.interview_portal import (
    CalendarEventItem,
    InterviewCalendarDay,
    InterviewCalendarResponse,
    InterviewListPortalResponse,
    InterviewPortalItemResponse,
    InterviewRoundTemplate,
    InterviewWorkspaceDetailResponse,
)
from app.services.notification_service import create_notification
from app.services.state_machine import execute_recruiter_lifecycle_transition


async def check_student_interview_collision(
    session: AsyncSession,
    student_id: int,
    start_time: datetime,
    duration_minutes: int,
    exclude_interview_id: Optional[int] = None,
) -> None:
    """
    Acquire a row-level lock on the student profile and verify that no other active
    interviews collide with the proposed time window.
    """
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    end_time = start_time + timedelta(minutes=duration_minutes)

    # 1. Acquire row-level lock on student profile to serialize concurrent scheduling
    stmt_lock = (
        select(StudentProfile.id)
        .where(StudentProfile.id == student_id)
        .with_for_update()
    )
    await session.execute(stmt_lock)

    # 2. Query all active interviews for this student across all applications
    stmt_active = (
        select(Interview)
        .join(JobApplication, Interview.application_id == JobApplication.id)
        .where(
            JobApplication.student_id == student_id,
            Interview.status.in_([InterviewStatus.SCHEDULED, InterviewStatus.COMPLETED]),
        )
    )
    if exclude_interview_id is not None:
        stmt_active = stmt_active.where(Interview.id != exclude_interview_id)

    result = await session.execute(stmt_active)
    active_interviews = result.scalars().all()

    for existing in active_interviews:
        ex_start = existing.scheduled_start_time
        if ex_start.tzinfo is None:
            ex_start = ex_start.replace(tzinfo=timezone.utc)
        ex_end = ex_start + timedelta(minutes=existing.duration_minutes)

        # Standard interval overlap condition: (StartA < EndB) and (EndA > StartB)
        if start_time < ex_end and end_time > ex_start:
            raise ResourceConflictException(
                message=f"Interview schedule collision: Candidate already has an interview scheduled between {ex_start.isoformat()} and {ex_end.isoformat()}.",
                details={
                    "conflicting_interview_id": existing.id,
                    "round_title": existing.round_title,
                    "conflicting_start": ex_start.isoformat(),
                    "conflicting_end": ex_end.isoformat(),
                },
            )


async def schedule_interview(
    session: AsyncSession,
    recruiter_user: User,
    application_id: int,
    round_number: int,
    round_title: str,
    scheduled_start_time: datetime,
    duration_minutes: int = 45,
    interview_mode: InterviewMode = InterviewMode.VIRTUAL,
    meeting_link: Optional[str] = None,
    location: Optional[str] = None,
    interviewer_names: Optional[str] = None,
    instructions: Optional[str] = None,
) -> Interview:
    """Schedule an interview round with student collision locking and state progression."""
    if recruiter_user.role not in (UserRole.RECRUITER, UserRole.ADMIN):
        raise AuthorizationException("Only corporate recruiters and administrators can schedule interviews.")

    result = await session.execute(
        select(JobApplication)
        .options(
            selectinload(JobApplication.job),
            selectinload(JobApplication.student_profile),
        )
        .where(JobApplication.id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise EntityNotFoundException("JobApplication", application_id)

    # Verify company ownership for recruiters
    if recruiter_user.role == UserRole.RECRUITER:
        result = await session.execute(
            select(RecruiterProfile).where(RecruiterProfile.user_id == recruiter_user.id)
        )
        recruiter_profile = result.scalar_one_or_none()
        if not recruiter_profile or recruiter_profile.company_id != application.job.company_id:
            raise AuthorizationException("You may only schedule interviews for jobs offered by your company.")

    # Application state eligibility checks
    if application.current_status == ApplicationStatus.WITHDRAWN:
        raise AppException("Cannot schedule interview: Candidate has withdrawn application.", code="APPLICATION_WITHDRAWN")
    if application.current_status in (ApplicationStatus.REJECTED, ApplicationStatus.OFFER_DECLINED):
        raise AppException("Cannot schedule interview: Application is closed or rejected.", code="APPLICATION_CLOSED")

    # Campus Drive TPO Screening Gate
    if application.drive_id is not None and application.tpo_screening_status != TpoScreeningStatus.SHORTLISTED:
        raise AppException(
            "Cannot schedule interview: Application must be shortlisted by TPO before recruiter scheduling.",
            code="TPO_SCREENING_REQUIRED",
        )

    # Check unique round number per application
    result = await session.execute(
        select(Interview).where(
            Interview.application_id == application_id,
            Interview.round_number == round_number,
        )
    )
    if result.scalar_one_or_none():
        raise ResourceConflictException(
            f"Round {round_number} has already been scheduled for this application.",
            details={"application_id": application_id, "round_number": round_number},
        )

    # Collision check with student row lock
    await check_student_interview_collision(
        session=session,
        student_id=application.student_id,
        start_time=scheduled_start_time,
        duration_minutes=duration_minutes,
    )

    now_utc = datetime.now(timezone.utc)
    interview = Interview(
        application_id=application.id,
        round_number=round_number,
        round_title=round_title.strip(),
        interview_mode=interview_mode,
        meeting_link=meeting_link.strip() if meeting_link else None,
        location=location.strip() if location else None,
        scheduled_start_time=scheduled_start_time,
        duration_minutes=duration_minutes,
        interviewer_names=interviewer_names.strip() if interviewer_names else None,
        instructions=instructions.strip() if instructions else None,
        status=InterviewStatus.SCHEDULED,
        outcome=InterviewOutcome.PENDING,
        created_by_user_id=recruiter_user.id,
        created_at=now_utc,
    )
    session.add(interview)
    await session.flush()
    if getattr(interview, "id", None) is None:
        interview.id = 1

    # Progress application lifecycle to interview_scheduled if not already
    if application.current_status != ApplicationStatus.INTERVIEW_SCHEDULED:
        await execute_recruiter_lifecycle_transition(
            session=session,
            application=application,
            new_status=ApplicationStatus.INTERVIEW_SCHEDULED,
            actor_user_id=recruiter_user.id,
            notes=f"Scheduled {round_title} (Round {round_number})",
        )

    await session.flush()

    # Send in-app notification to student
    student_user_id = application.student_profile.user_id
    await create_notification(
        session=session,
        recipient_user_id=student_user_id,
        sender_user_id=recruiter_user.id,
        category=NotificationCategory.INTERVIEW_SCHEDULED,
        title=f"Interview Scheduled: {round_title}",
        message=f"You have an interview scheduled for {application.job.title} on {scheduled_start_time.strftime('%Y-%m-%d %H:%M UTC')}.",
        related_application_id=application.id,
        related_interview_id=interview.id,
        idempotency_key=f"interview-sched-{interview.id}",
    )

    return interview


async def reschedule_interview(
    session: AsyncSession,
    recruiter_user: User,
    interview_id: int,
    new_start_time: datetime,
    reason: str,
    new_duration_minutes: Optional[int] = None,
    meeting_link: Optional[str] = None,
    location: Optional[str] = None,
    instructions: Optional[str] = None,
) -> Interview:
    """Reschedule an existing scheduled interview round with collision check."""
    if len(reason.strip()) < 5:
        raise AppException("Reschedule reason must be at least 5 characters.", code="INVALID_RESCHEDULE_REASON")

    result = await session.execute(
        select(Interview)
        .options(
            selectinload(Interview.application).selectinload(JobApplication.job),
            selectinload(Interview.application).selectinload(JobApplication.student_profile),
        )
        .where(Interview.id == interview_id)
    )
    interview = result.scalar_one_or_none()
    if not interview:
        raise EntityNotFoundException("Interview", interview_id)

    application = interview.application

    # Verify recruiter authorization
    if recruiter_user.role == UserRole.RECRUITER:
        result = await session.execute(
            select(RecruiterProfile).where(RecruiterProfile.user_id == recruiter_user.id)
        )
        profile = result.scalar_one_or_none()
        if not profile or profile.company_id != application.job.company_id:
            raise AuthorizationException("You may only reschedule interviews for jobs offered by your company.")

    if interview.status != InterviewStatus.SCHEDULED:
        raise AppException(
            f"Cannot reschedule an interview with status '{interview.status.value}'. Only scheduled interviews can be rescheduled.",
            code="INTERVIEW_NOT_SCHEDULED",
        )

    duration = new_duration_minutes or interview.duration_minutes

    # Check collision for the new time window
    await check_student_interview_collision(
        session=session,
        student_id=application.student_id,
        start_time=new_start_time,
        duration_minutes=duration,
        exclude_interview_id=interview.id,
    )

    interview.scheduled_start_time = new_start_time
    interview.duration_minutes = duration
    if meeting_link is not None:
        interview.meeting_link = meeting_link.strip() if meeting_link else None
    if location is not None:
        interview.location = location.strip() if location else None
    if instructions is not None:
        interview.instructions = instructions.strip() if instructions else None
    interview.cancellation_reason = f"Rescheduled: {reason.strip()}"
    interview.updated_at = datetime.now(timezone.utc)

    await session.flush()

    # Notify student
    student_user_id = application.student_profile.user_id
    await create_notification(
        session=session,
        recipient_user_id=student_user_id,
        sender_user_id=recruiter_user.id,
        category=NotificationCategory.INTERVIEW_UPDATE,
        title=f"Interview Rescheduled: {interview.round_title}",
        message=f"Your {interview.round_title} has been moved to {new_start_time.strftime('%Y-%m-%d %H:%M UTC')}. Reason: {reason.strip()}",
        related_application_id=application.id,
        related_interview_id=interview.id,
        idempotency_key=f"interview-resched-{interview.id}-{int(new_start_time.timestamp())}",
    )

    return interview


async def cancel_interview(
    session: AsyncSession,
    recruiter_user: User,
    interview_id: int,
    reason: str,
) -> Interview:
    """
    Cancel an interview round with round-aware candidate lifecycle state reversion.
    If Round 1 is cancelled: application returns to 'shortlisted'.
    If Round 2+ is cancelled and earlier rounds completed: application returns to 'interviewed'.
    """
    if len(reason.strip()) < 5:
        raise AppException("Cancellation reason must be at least 5 characters.", code="INVALID_CANCELLATION_REASON")

    result = await session.execute(
        select(Interview)
        .options(
            selectinload(Interview.application).selectinload(JobApplication.job),
            selectinload(Interview.application).selectinload(JobApplication.student_profile),
        )
        .where(Interview.id == interview_id)
    )
    interview = result.scalar_one_or_none()
    if not interview:
        raise EntityNotFoundException("Interview", interview_id)

    application = interview.application

    if recruiter_user.role == UserRole.RECRUITER:
        result = await session.execute(
            select(RecruiterProfile).where(RecruiterProfile.user_id == recruiter_user.id)
        )
        profile = result.scalar_one_or_none()
        if not profile or profile.company_id != application.job.company_id:
            raise AuthorizationException("You may only cancel interviews for jobs offered by your company.")

    if interview.status != InterviewStatus.SCHEDULED:
        raise AppException(
            f"Cannot cancel an interview with status '{interview.status.value}'.",
            code="INTERVIEW_NOT_SCHEDULED",
        )

    interview.status = InterviewStatus.CANCELLED
    interview.cancellation_reason = reason.strip()
    interview.updated_at = datetime.now(timezone.utc)

    # Determine round-aware reversion status
    result = await session.execute(
        select(Interview).where(
            Interview.application_id == application.id,
            Interview.id != interview.id,
            Interview.status == InterviewStatus.COMPLETED,
            Interview.round_number < interview.round_number,
        )
    )
    completed_earlier_rounds = result.scalars().all()

    if completed_earlier_rounds:
        reversion_status = ApplicationStatus.INTERVIEWED
    else:
        reversion_status = ApplicationStatus.SHORTLISTED

    # Revert application state if currently interview_scheduled
    if application.current_status == ApplicationStatus.INTERVIEW_SCHEDULED:
        await execute_recruiter_lifecycle_transition(
            session=session,
            application=application,
            new_status=reversion_status,
            actor_user_id=recruiter_user.id,
            notes=f"Cancelled {interview.round_title}. Pipeline state reverted to {reversion_status.value}.",
        )

    await session.flush()

    # Notify student
    student_user_id = application.student_profile.user_id
    await create_notification(
        session=session,
        recipient_user_id=student_user_id,
        sender_user_id=recruiter_user.id,
        category=NotificationCategory.INTERVIEW_UPDATE,
        title=f"Interview Cancelled: {interview.round_title}",
        message=f"Your {interview.round_title} has been cancelled. Reason: {reason.strip()}",
        related_application_id=application.id,
        related_interview_id=interview.id,
        idempotency_key=f"interview-cancelled-{interview.id}",
    )

    return interview


async def record_interview_outcome(
    session: AsyncSession,
    recruiter_user: User,
    interview_id: int,
    outcome: InterviewOutcome,
    feedback_notes: Optional[str] = None,
) -> Interview:
    """
    Record evaluation result for an interview round.
    CRITICAL INVARIANT: A failed interview round sets the application status to 'interviewed',
    NEVER automatically rejecting the application. An explicit recruiter decision is required.
    """
    if outcome not in (InterviewOutcome.PASSED, InterviewOutcome.FAILED, InterviewOutcome.ON_HOLD):
        raise AppException("Invalid interview evaluation outcome.", code="INVALID_OUTCOME")

    result = await session.execute(
        select(Interview)
        .options(
            selectinload(Interview.application).selectinload(JobApplication.job),
            selectinload(Interview.application).selectinload(JobApplication.student_profile),
        )
        .where(Interview.id == interview_id)
    )
    interview = result.scalar_one_or_none()
    if not interview:
        raise EntityNotFoundException("Interview", interview_id)

    application = interview.application

    if recruiter_user.role == UserRole.RECRUITER:
        result = await session.execute(
            select(RecruiterProfile).where(RecruiterProfile.user_id == recruiter_user.id)
        )
        profile = result.scalar_one_or_none()
        if not profile or profile.company_id != application.job.company_id:
            raise AuthorizationException("You may only evaluate interviews for jobs offered by your company.")

    if interview.status != InterviewStatus.SCHEDULED:
        raise AppException(
            f"Cannot record outcome for an interview with status '{interview.status.value}'.",
            code="INTERVIEW_NOT_SCHEDULED",
        )

    interview.status = InterviewStatus.COMPLETED
    interview.outcome = outcome
    interview.updated_at = datetime.now(timezone.utc)
    if feedback_notes:
        interview.feedback_notes = feedback_notes.strip()

    # Move application to interviewed if currently interview_scheduled
    if application.current_status == ApplicationStatus.INTERVIEW_SCHEDULED:
        await execute_recruiter_lifecycle_transition(
            session=session,
            application=application,
            new_status=ApplicationStatus.INTERVIEWED,
            actor_user_id=recruiter_user.id,
            notes=f"Completed {interview.round_title} with outcome: {outcome.value}",
        )

    await session.flush()
    return interview


async def list_student_interviews(
    session: AsyncSession,
    student_user: User,
    interview_status: Optional[InterviewStatus] = None,
    company_query: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> List[Interview]:
    """
    Retrieve all interview rounds for the authenticated student with eager-loaded job,
    company, drive, and application context (strictly student-owned).
    """
    profile_res = await session.execute(
        select(StudentProfile).where(StudentProfile.user_id == student_user.id)
    )
    profile = profile_res.scalar_one_or_none()
    if not profile:
        raise EntityNotFoundException("StudentProfile", student_user.id)

    stmt = (
        select(Interview)
        .join(JobApplication, Interview.application_id == JobApplication.id)
        .join(Job, JobApplication.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .options(
            selectinload(Interview.application).selectinload(JobApplication.job).selectinload(Job.company),
            selectinload(Interview.application).selectinload(JobApplication.drive),
        )
        .where(JobApplication.student_id == profile.id)
    )

    if interview_status is not None:
        stmt = stmt.where(Interview.status == interview_status)
    if company_query and company_query.strip():
        stmt = stmt.where(Company.name.ilike(f"%{company_query.strip()}%"))
    if date_from is not None:
        df = date_from if date_from.tzinfo is not None else date_from.replace(tzinfo=timezone.utc)
        stmt = stmt.where(Interview.scheduled_start_time >= df)
    if date_to is not None:
        dt = date_to if date_to.tzinfo is not None else date_to.replace(tzinfo=timezone.utc)
        stmt = stmt.where(Interview.scheduled_start_time <= dt)

    stmt = stmt.order_by(Interview.scheduled_start_time.asc(), Interview.round_number.asc())
    res = await session.execute(stmt)
    return list(res.scalars().all())


# =============================================================================
# Standard Round Templates & Portal Enhancements (TASK 09)
# =============================================================================

STANDARD_ROUND_TEMPLATES: List[InterviewRoundTemplate] = [
    InterviewRoundTemplate(
        round_number=1,
        round_title="Technical Screening",
        stage="technical",
        default_duration_minutes=45,
        description="Fundamental concepts, coding syntax, core algorithms, and technical fundamentals.",
    ),
    InterviewRoundTemplate(
        round_number=2,
        round_title="Coding & Problem Solving",
        stage="problem_solving",
        default_duration_minutes=60,
        description="Live coding, data structures, algorithm optimization, and time/space complexity analysis.",
    ),
    InterviewRoundTemplate(
        round_number=3,
        round_title="System Design & Architecture",
        stage="project_discussion",
        default_duration_minutes=60,
        description="System design, microservices, databases, caching, trade-offs, and past project deep-dive.",
    ),
    InterviewRoundTemplate(
        round_number=4,
        round_title="Managerial & Fitment Discussion",
        stage="overall",
        default_duration_minutes=45,
        description="Situational leadership, teamwork, conflict resolution, ownership, and engineering practices.",
    ),
    InterviewRoundTemplate(
        round_number=5,
        round_title="HR & Cultural Alignment",
        stage="hr",
        default_duration_minutes=30,
        description="Cultural values, communication, career aspirations, and company culture fit.",
    ),
    InterviewRoundTemplate(
        round_number=6,
        round_title="Final Leadership Interview",
        stage="overall",
        default_duration_minutes=45,
        description="Executive discussion, strategic vision, role expectations, and formal offer alignment.",
    ),
]


def _build_interview_portal_item(
    interview: Interview,
    redact_internal_notes: bool = False,
) -> InterviewPortalItemResponse:
    app = interview.application
    job = app.job if app else None
    company = job.company if job else None
    prof = app.student_profile if app else None
    user = prof.user if prof else None
    dept = user.department if user else None
    drive = app.drive if app else None

    # Rescheduled check
    is_rescheduled = bool(
        isinstance(getattr(interview, "cancellation_reason", None), str)
        and interview.cancellation_reason.strip().startswith("Rescheduled:")
        and interview.status != InterviewStatus.CANCELLED
    )

    evals = getattr(interview, "evaluations", None) or []
    eval_count = len(evals)
    avg_rating = (
        round(sum(float(e.overall_rating) for e in evals) / eval_count, 2)
        if eval_count > 0
        else None
    )

    return InterviewPortalItemResponse(
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
        instructions=interview.instructions,
        status=interview.status,
        outcome=interview.outcome,
        feedback_notes=None if redact_internal_notes else interview.feedback_notes,
        cancellation_reason=interview.cancellation_reason,
        is_rescheduled=is_rescheduled,
        created_at=interview.created_at,
        updated_at=interview.updated_at,
        student_id=prof.id if prof else 0,
        student_name=user.full_name if user else "Candidate",
        student_email=user.email if user else "",
        roll_number=prof.roll_number if prof else "",
        department=dept.name if dept else "General",
        graduation_year=prof.graduation_year if prof else 2026,
        cgpa=float(prof.cgpa) if (prof and prof.cgpa is not None) else 0.0,
        job_id=job.id if job else 0,
        job_title=job.title if job else "",
        company_id=company.id if company else 0,
        company_name=company.name if company else "",
        drive_id=drive.id if drive else None,
        drive_name=drive.name if drive else None,
        evaluations_count=eval_count,
        average_rating=avg_rating,
    )


async def list_company_interviews(
    session: AsyncSession,
    current_user: User,
    job_id: Optional[int] = None,
    application_id: Optional[int] = None,
    drive_id: Optional[int] = None,
    status: Optional[InterviewStatus] = None,
    outcome: Optional[InterviewOutcome] = None,
    mode: Optional[InterviewMode] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> InterviewListPortalResponse:
    """Retrieve full company-scoped interview roster with candidate and job details."""
    company_id = None
    if current_user.role == UserRole.RECRUITER:
        prof_res = await session.execute(
            select(RecruiterProfile).where(RecruiterProfile.user_id == current_user.id)
        )
        rec_prof = prof_res.scalar_one_or_none()
        if not rec_prof or not rec_prof.company_id:
            raise AuthorizationException("Recruiter profile not linked to a company.")
        company_id = rec_prof.company_id
    elif current_user.role != UserRole.ADMIN:
        raise AuthorizationException("Only recruiters and administrators can access company interview rosters.")

    stmt = (
        select(Interview)
        .join(JobApplication, Interview.application_id == JobApplication.id)
        .join(Job, JobApplication.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .join(StudentProfile, JobApplication.student_id == StudentProfile.id)
        .join(User, StudentProfile.user_id == User.id)
        .outerjoin(Department, User.department_id == Department.id)
        .outerjoin(PlacementDrive, JobApplication.drive_id == PlacementDrive.id)
        .options(
            selectinload(Interview.application).selectinload(JobApplication.job).selectinload(Job.company),
            selectinload(Interview.application).selectinload(JobApplication.student_profile).selectinload(StudentProfile.user).selectinload(User.department),
            selectinload(Interview.application).selectinload(JobApplication.drive),
            selectinload(Interview.evaluations),
        )
    )

    if company_id is not None:
        stmt = stmt.where(Job.company_id == company_id)

    if job_id is not None:
        stmt = stmt.where(Job.id == job_id)
    if application_id is not None:
        stmt = stmt.where(JobApplication.id == application_id)
    if drive_id is not None:
        stmt = stmt.where(JobApplication.drive_id == drive_id)
    if status is not None:
        stmt = stmt.where(Interview.status == status)
    if outcome is not None:
        stmt = stmt.where(Interview.outcome == outcome)
    if mode is not None:
        stmt = stmt.where(Interview.interview_mode == mode)
    if date_from is not None:
        df = date_from if date_from.tzinfo is not None else date_from.replace(tzinfo=timezone.utc)
        stmt = stmt.where(Interview.scheduled_start_time >= df)
    if date_to is not None:
        dt = date_to if date_to.tzinfo is not None else date_to.replace(tzinfo=timezone.utc)
        stmt = stmt.where(Interview.scheduled_start_time <= dt)

    if search and search.strip():
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                User.full_name.ilike(term),
                StudentProfile.roll_number.ilike(term),
                Job.title.ilike(term),
                Interview.round_title.ilike(term),
                Interview.interviewer_names.ilike(term),
            )
        )

    # Total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await session.execute(count_stmt)
    total = total_res.scalar() or 0

    stmt = stmt.order_by(Interview.scheduled_start_time.asc()).offset(skip).limit(limit)
    res = await session.execute(stmt)
    interviews = res.scalars().all()

    items = [_build_interview_portal_item(i, redact_internal_notes=False) for i in interviews]
    pages = (total + limit - 1) // limit if limit > 0 else 1

    return InterviewListPortalResponse(
        items=items,
        total=total,
        page=(skip // limit) + 1 if limit > 0 else 1,
        limit=limit,
        pages=pages,
    )


async def get_interview_calendar_events(
    session: AsyncSession,
    current_user: User,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    job_id: Optional[int] = None,
    status: Optional[InterviewStatus] = None,
) -> InterviewCalendarResponse:
    """Retrieve calendar-bucketed interview events scoped to user role."""
    now_utc = datetime.now(timezone.utc)
    if date_from is None:
        date_from = now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7)
    if date_to is None:
        date_to = date_from + timedelta(days=45)

    df = date_from if date_from.tzinfo is not None else date_from.replace(tzinfo=timezone.utc)
    dt = date_to if date_to.tzinfo is not None else date_to.replace(tzinfo=timezone.utc)

    stmt = (
        select(Interview)
        .join(JobApplication, Interview.application_id == JobApplication.id)
        .join(Job, JobApplication.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .join(StudentProfile, JobApplication.student_id == StudentProfile.id)
        .join(User, StudentProfile.user_id == User.id)
        .options(
            selectinload(Interview.application).selectinload(JobApplication.job).selectinload(Job.company),
            selectinload(Interview.application).selectinload(JobApplication.student_profile).selectinload(StudentProfile.user),
        )
        .where(
            Interview.scheduled_start_time >= df,
            Interview.scheduled_start_time <= dt,
        )
    )

    if current_user.role == UserRole.RECRUITER:
        prof_res = await session.execute(
            select(RecruiterProfile).where(RecruiterProfile.user_id == current_user.id)
        )
        rec_prof = prof_res.scalar_one_or_none()
        if rec_prof and rec_prof.company_id:
            stmt = stmt.where(Job.company_id == rec_prof.company_id)
        else:
            return InterviewCalendarResponse(days=[], total_events=0, scheduled_count=0, completed_count=0, cancelled_count=0, rescheduled_count=0)
    elif current_user.role == UserRole.STUDENT:
        prof_res = await session.execute(
            select(StudentProfile).where(StudentProfile.user_id == current_user.id)
        )
        stud_prof = prof_res.scalar_one_or_none()
        if stud_prof:
            stmt = stmt.where(JobApplication.student_id == stud_prof.id)
        else:
            return InterviewCalendarResponse(days=[], total_events=0, scheduled_count=0, completed_count=0, cancelled_count=0, rescheduled_count=0)
    elif current_user.role == UserRole.TPO:
        if current_user.institution_id:
            stmt = stmt.outerjoin(PlacementDrive, JobApplication.drive_id == PlacementDrive.id)
            stmt = stmt.where(
                or_(
                    PlacementDrive.institution_id == current_user.institution_id,
                    User.institution_id == current_user.institution_id,
                )
            )

    if job_id is not None:
        stmt = stmt.where(Job.id == job_id)
    if status is not None:
        stmt = stmt.where(Interview.status == status)

    stmt = stmt.order_by(Interview.scheduled_start_time.asc())
    res = await session.execute(stmt)
    interviews = res.scalars().all()

    # Bucket by date
    days_dict: Dict[str, List[CalendarEventItem]] = {}
    scheduled_count = 0
    completed_count = 0
    cancelled_count = 0
    rescheduled_count = 0

    for iv in interviews:
        is_resched = bool(
            isinstance(getattr(iv, "cancellation_reason", None), str)
            and iv.cancellation_reason.strip().startswith("Rescheduled:")
            and iv.status != InterviewStatus.CANCELLED
        )

        if iv.status == InterviewStatus.SCHEDULED:
            if is_resched:
                rescheduled_count += 1
            else:
                scheduled_count += 1
        elif iv.status == InterviewStatus.COMPLETED:
            completed_count += 1
        elif iv.status == InterviewStatus.CANCELLED:
            cancelled_count += 1

        date_key = iv.scheduled_start_time.strftime("%Y-%m-%d")
        if date_key not in days_dict:
            days_dict[date_key] = []

        cand_name = iv.application.student_profile.user.full_name if (iv.application and iv.application.student_profile and iv.application.student_profile.user) else "Candidate"
        roll = iv.application.student_profile.roll_number if (iv.application and iv.application.student_profile) else ""
        job_t = iv.application.job.title if (iv.application and iv.application.job) else ""
        comp_name = iv.application.job.company.name if (iv.application and iv.application.job and iv.application.job.company) else ""

        days_dict[date_key].append(
            CalendarEventItem(
                id=iv.id,
                application_id=iv.application_id,
                round_title=iv.round_title,
                round_number=iv.round_number,
                scheduled_start_time=iv.scheduled_start_time,
                duration_minutes=iv.duration_minutes,
                status=iv.status,
                outcome=iv.outcome,
                interview_mode=iv.interview_mode,
                meeting_link=iv.meeting_link,
                location=iv.location,
                student_name=cand_name,
                roll_number=roll,
                job_title=job_t,
                company_name=comp_name,
                is_rescheduled=is_resched,
            )
        )

    days_list = [
        InterviewCalendarDay(date=d, events=events)
        for d, events in sorted(days_dict.items(), key=lambda x: x[0])
    ]

    return InterviewCalendarResponse(
        days=days_list,
        total_events=len(interviews),
        scheduled_count=scheduled_count,
        completed_count=completed_count,
        cancelled_count=cancelled_count,
        rescheduled_count=rescheduled_count,
    )


async def list_tpo_institution_interviews(
    session: AsyncSession,
    tpo_user: User,
    drive_id: Optional[int] = None,
    company_id: Optional[int] = None,
    department_id: Optional[int] = None,
    status: Optional[InterviewStatus] = None,
    outcome: Optional[InterviewOutcome] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> InterviewListPortalResponse:
    """Institutional campus recruitment interview monitoring for TPOs (confidential feedback redacted)."""
    if tpo_user.role not in (UserRole.TPO, UserRole.ADMIN):
        raise AuthorizationException("Only TPOs and administrators can access institutional interview monitoring.")

    stmt = (
        select(Interview)
        .join(JobApplication, Interview.application_id == JobApplication.id)
        .join(Job, JobApplication.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .join(StudentProfile, JobApplication.student_id == StudentProfile.id)
        .join(User, StudentProfile.user_id == User.id)
        .outerjoin(Department, User.department_id == Department.id)
        .outerjoin(PlacementDrive, JobApplication.drive_id == PlacementDrive.id)
        .options(
            selectinload(Interview.application).selectinload(JobApplication.job).selectinload(Job.company),
            selectinload(Interview.application).selectinload(JobApplication.student_profile).selectinload(StudentProfile.user).selectinload(User.department),
            selectinload(Interview.application).selectinload(JobApplication.drive),
            selectinload(Interview.evaluations),
        )
    )

    if tpo_user.role == UserRole.TPO and tpo_user.institution_id:
        stmt = stmt.where(
            or_(
                PlacementDrive.institution_id == tpo_user.institution_id,
                User.institution_id == tpo_user.institution_id,
            )
        )

    if drive_id is not None:
        stmt = stmt.where(JobApplication.drive_id == drive_id)
    if company_id is not None:
        stmt = stmt.where(Job.company_id == company_id)
    if department_id is not None:
        stmt = stmt.where(User.department_id == department_id)
    if status is not None:
        stmt = stmt.where(Interview.status == status)
    if outcome is not None:
        stmt = stmt.where(Interview.outcome == outcome)
    if date_from is not None:
        df = date_from if date_from.tzinfo is not None else date_from.replace(tzinfo=timezone.utc)
        stmt = stmt.where(Interview.scheduled_start_time >= df)
    if date_to is not None:
        dt = date_to if date_to.tzinfo is not None else date_to.replace(tzinfo=timezone.utc)
        stmt = stmt.where(Interview.scheduled_start_time <= dt)

    if search and search.strip():
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                User.full_name.ilike(term),
                StudentProfile.roll_number.ilike(term),
                Job.title.ilike(term),
                Company.name.ilike(term),
                Interview.round_title.ilike(term),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await session.execute(count_stmt)
    total = total_res.scalar() or 0

    stmt = stmt.order_by(Interview.scheduled_start_time.asc()).offset(skip).limit(limit)
    res = await session.execute(stmt)
    interviews = res.scalars().all()

    items = [_build_interview_portal_item(i, redact_internal_notes=True) for i in interviews]
    pages = (total + limit - 1) // limit if limit > 0 else 1

    return InterviewListPortalResponse(
        items=items,
        total=total,
        page=(skip // limit) + 1 if limit > 0 else 1,
        limit=limit,
        pages=pages,
    )


async def get_interview_workspace_detail(
    session: AsyncSession,
    interview_id: int,
    current_user: User,
) -> InterviewWorkspaceDetailResponse:
    """Interviewer workspace detail: candidate context, round history, scorecards, allowed actions."""
    stmt = (
        select(Interview)
        .options(
            selectinload(Interview.application).selectinload(JobApplication.job).selectinload(Job.company),
            selectinload(Interview.application).selectinload(JobApplication.student_profile).selectinload(StudentProfile.user).selectinload(User.department),
            selectinload(Interview.application).selectinload(JobApplication.student_profile).selectinload(StudentProfile.skills),
            selectinload(Interview.application).selectinload(JobApplication.student_profile).selectinload(StudentProfile.education_history),
            selectinload(Interview.application).selectinload(JobApplication.student_profile).selectinload(StudentProfile.projects),
            selectinload(Interview.application).selectinload(JobApplication.drive),
            selectinload(Interview.application).selectinload(JobApplication.resume),
            selectinload(Interview.application).selectinload(JobApplication.interviews),
            selectinload(Interview.evaluations).selectinload(CandidateEvaluation.interviewer),
        )
        .where(Interview.id == interview_id)
    )
    res = await session.execute(stmt)
    interview = res.scalar_one_or_none()
    if not interview:
        raise EntityNotFoundException("Interview", interview_id)

    app = interview.application
    job = app.job if app else None
    prof = app.student_profile if app else None
    user = prof.user if prof else None

    # Check access permission
    is_recruiter = False
    if current_user.role == UserRole.RECRUITER:
        prof_res = await session.execute(
            select(RecruiterProfile).where(RecruiterProfile.user_id == current_user.id)
        )
        rec_prof = prof_res.scalar_one_or_none()
        if not rec_prof or not job or rec_prof.company_id != job.company_id:
            raise AuthorizationException("Access denied.")
        is_recruiter = True
    elif current_user.role == UserRole.STUDENT:
        if not prof or prof.user_id != current_user.id:
            raise AuthorizationException("Access denied.")
    elif current_user.role == UserRole.TPO:
        if current_user.institution_id:
            drive_inst = getattr(app.drive, "institution_id", None) if app else None
            user_inst = getattr(user, "institution_id", None) if user else None
            if current_user.institution_id not in (drive_inst, user_inst):
                raise AuthorizationException("Access denied.")

    redact_notes = not is_recruiter and current_user.role != UserRole.ADMIN

    main_item = _build_interview_portal_item(interview, redact_internal_notes=redact_notes)

    # Past rounds for same application
    other_interviews = sorted(
        [i for i in (app.interviews or []) if i.id != interview.id],
        key=lambda x: x.round_number,
    )
    past_round_items = [_build_interview_portal_item(i, redact_internal_notes=redact_notes) for i in other_interviews]

    # Candidate profile summary
    cand_profile = {
        "student_id": prof.id if prof else 0,
        "full_name": user.full_name if user else "Candidate",
        "email": user.email if user else "",
        "roll_number": prof.roll_number if prof else "",
        "department": user.department.name if (user and user.department) else "General",
        "graduation_year": prof.graduation_year if prof else 2026,
        "cgpa": float(prof.cgpa) if (prof and prof.cgpa is not None) else 0.0,
        "active_backlogs": prof.active_backlogs if prof else 0,
        "total_backlogs": prof.total_backlogs if prof else 0,
        "skills": [s.skill_name for s in (prof.skills or []) if getattr(s, "is_verified", True)] if prof else [],
        "projects_count": len(prof.projects or []) if prof else 0,
        "resume_download_url": f"/api/v1/applications/{app.id}/resume" if (app and app.resume) else None,
    }

    job_info = {
        "id": job.id if job else 0,
        "title": job.title if job else "",
        "company_name": job.company.name if (job and job.company) else "",
        "location": getattr(job, "location", None) if job else None,
        "ctc_lpa": float(job.ctc_lpa) if (job and getattr(job, "ctc_lpa", None)) else None,
        "employment_type": job.employment_type.value if (job and getattr(job, "employment_type", None)) else None,
    }

    evals_list = []
    if not redact_notes:
        for ev in (interview.evaluations or []):
            evals_list.append({
                "id": ev.id,
                "interviewer_name": ev.interviewer_name or (ev.interviewer.full_name if ev.interviewer else "Interviewer"),
                "stage": ev.stage.value if hasattr(ev.stage, "value") else str(ev.stage),
                "overall_rating": float(ev.overall_rating),
                "recommendation": ev.recommendation.value if hasattr(ev.recommendation, "value") else str(ev.recommendation),
                "written_feedback": ev.written_feedback,
                "strengths": ev.strengths or [],
                "weaknesses": ev.weaknesses or [],
                "created_at": ev.created_at.isoformat(),
            })

    allowed_actions = []
    if is_recruiter or current_user.role == UserRole.ADMIN:
        if interview.status == InterviewStatus.SCHEDULED:
            allowed_actions.extend(["mark_completed_passed", "mark_completed_failed", "mark_completed_hold", "reschedule", "cancel"])
        elif interview.status == InterviewStatus.COMPLETED:
            if interview.outcome == InterviewOutcome.PASSED:
                allowed_actions.extend(["schedule_next_round", "extend_offer"])
            elif interview.outcome == InterviewOutcome.ON_HOLD:
                allowed_actions.extend(["mark_completed_passed", "mark_completed_failed"])

    return InterviewWorkspaceDetailResponse(
        interview=main_item,
        candidate_profile=cand_profile,
        job=job_info,
        past_rounds=past_round_items,
        evaluations=evals_list,
        allowed_next_actions=allowed_actions,
    )

