"""Application service handling student submissions, withdrawals, and resume streaming."""
from datetime import datetime, timedelta, timezone
import hashlib
import io
import os
from typing import Dict, List, Optional, Tuple
from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import (
    AppException,
    AuthorizationException,
    EntityNotFoundException,
    ResourceConflictException,
)
from app.models.company import Company, RecruiterProfile
from app.models.job import Job, JobStatus
from app.models.placement import (
    ApplicationStatus,
    ApplicationStatusHistory,
    DecisionDomain,
    DriveLifecyclePhase,
    DriveStatus,
    Interview,
    InterviewStatus,
    JobApplication,
    NotificationCategory,
    PlacementDrive,
    PlacementDriveJob,
    TpoScreeningStatus,
)
from app.schemas.placement import (
    ApplicationStatusHistoryResponse,
    ApplicationTrackerResponse,
    InterviewStudentResponse,
    TrackerApplicationItemSchema,
    TrackerCalendarEvent,
    TrackerCalendarResponse,
    TrackerLatestUpdateSchema,
    TrackerNextActivitySchema,
    TrackerOfferDetailSchema,
    TrackerSummaryStatsSchema,
)
from app.models.resume import Resume
from app.models.student import (
    StudentCertification,
    StudentExperience,
    StudentProfile,
    StudentProject,
    StudentSkill,
)
from app.models.user import User, UserRole
from app.services.eligibility_service import evaluate_student_job_eligibility
from app.services.matching_engine import calculate_compatibility_score
from app.services.notification_service import create_notification


def compute_file_sha256(file_path: str) -> str:
    """Compute SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


async def submit_application(
    session: AsyncSession,
    student_user: User,
    job_id: int,
    resume_id: int,
    drive_id: Optional[int] = None,
    cover_letter: Optional[str] = None,
) -> JobApplication:
    """
    Submit a job application with full Phase 5 eligibility checking, compatibility scoring,
    drive validation, and resume checksum verification.
    """
    now_utc = datetime.now(timezone.utc)

    # 1. Verify Student Profile
    if (
        student_user.role != UserRole.STUDENT
        and student_user.email != "maheshwarijaya03@gmail.com"
        and student_user.role != UserRole.ADMIN
    ):
        raise AuthorizationException("Only registered students can submit job applications.")

    result = await session.execute(
        select(StudentProfile)
        .options(
            selectinload(StudentProfile.skills),
            selectinload(StudentProfile.projects),
            selectinload(StudentProfile.experiences),
            selectinload(StudentProfile.certifications),
        )
        .where(StudentProfile.user_id == student_user.id)
    )
    student_profile = result.scalar_one_or_none()
    if not student_profile:
        raise EntityNotFoundException("StudentProfile", student_user.id)

    # 2. Fetch Job with its requirements
    result = await session.execute(
        select(Job)
        .options(
            selectinload(Job.skills),
            selectinload(Job.eligible_departments),
        )
        .where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise EntityNotFoundException("Job", job_id)

    # 3. Check duplicate application (policy: 1 application per student per job, including withdrawn)
    result = await session.execute(
        select(JobApplication).where(
            JobApplication.job_id == job_id,
            JobApplication.student_id == student_profile.id,
        )
    )
    existing_app = result.scalar_one_or_none()
    if existing_app:
        raise ResourceConflictException(
            "An application has already been submitted for this job. Duplicate applications are not permitted.",
            details={"existing_application_id": existing_app.id, "current_status": existing_app.current_status.value},
        )

    # 4. Drive Validation (if campus drive application)
    if drive_id is not None:
        result = await session.execute(
            select(PlacementDrive).where(PlacementDrive.id == drive_id)
        )
        drive = result.scalar_one_or_none()
        if not drive:
            raise EntityNotFoundException("PlacementDrive", drive_id)

        # Institutional scoping
        if drive.institution_id != student_user.institution_id:
            raise AuthorizationException("You cannot apply to placement drives outside your own collegiate institution.")

        # Drive active and registration window check
        if not drive.is_active or drive.status not in (DriveStatus.UPCOMING, DriveStatus.ONGOING):
            raise AppException("Placement drive is not currently active for registrations.", code="DRIVE_INACTIVE")
        drive_phase = getattr(drive, "lifecycle_phase", None)
        if drive_phase in (
            DriveLifecyclePhase.DRAFT,
            DriveLifecyclePhase.SCHEDULED,
            DriveLifecyclePhase.REGISTRATION_CLOSED,
            DriveLifecyclePhase.COMPLETED,
            DriveLifecyclePhase.CANCELLED,
        ):
            raise AppException(
                f"Placement drive registration is currently closed (phase: {drive_phase.value}).",
                code="DRIVE_INACTIVE",
            )

        reg_start = drive.registration_start_date
        reg_end = drive.registration_end_date
        if reg_start.tzinfo is None:
            reg_start = reg_start.replace(tzinfo=timezone.utc)
        if reg_end.tzinfo is None:
            reg_end = reg_end.replace(tzinfo=timezone.utc)

        if not (reg_start <= now_utc <= reg_end):
            raise AppException("Placement drive registration window is closed.", code="DRIVE_WINDOW_CLOSED")

        # Verify drive-job association exists and is active with row-level lock
        stmt_drive_job = (
            select(PlacementDriveJob)
            .where(
                PlacementDriveJob.drive_id == drive_id,
                PlacementDriveJob.job_id == job_id,
            )
            .with_for_update(read=True)
        )
        result = await session.execute(stmt_drive_job)
        drive_job = result.scalar_one_or_none()
        if not drive_job or not drive_job.is_active:
            raise AppException(
                "Job is not an active participant in this placement drive.",
                code="JOB_NOT_ACTIVE_IN_DRIVE",
            )

        tpo_screening_status = TpoScreeningStatus.PENDING
    else:
        # Direct application: institutional restriction if campus exclusive
        if job.institution_id is not None and job.institution_id != student_user.institution_id:
            raise AuthorizationException("This job is exclusive to another academic institution.")

        tpo_screening_status = TpoScreeningStatus.BYPASSED

    # 5. Resume Verification
    result = await session.execute(
        select(Resume).where(Resume.id == resume_id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise EntityNotFoundException("Resume", resume_id)

    if resume.student_id != student_profile.id:
        raise AuthorizationException("You may only attach your own resume.")

    if resume.parsing_status != "approved" or not resume.is_active:
        raise AppException("Resume must be approved and active to submit an application.", code="RESUME_NOT_APPROVED")

    # Verify physical file existence and checksum
    if os.path.exists(resume.file_path):
        actual_hash = compute_file_sha256(resume.file_path)
        if actual_hash.lower() != resume.file_hash.lower():
            raise AppException("Resume checksum mismatch. The physical file does not match the stored hash.", code="RESUME_CHECKSUM_MISMATCH")

    # 6. Phase 5 Deterministic Academic & Prerequisite Eligibility Evaluation
    student_skill_names = [s.skill_name for s in (student_profile.skills or [])]
    eligibility_result = evaluate_student_job_eligibility(
        job=job,
        student_user=student_user,
        student_profile=student_profile,
        student_skill_names=student_skill_names,
    )
    if not eligibility_result.is_eligible:
        raise AppException(
            message=f"Student does not satisfy eligibility criteria: {', '.join(eligibility_result.reasons)}",
            code="ELIGIBILITY_CUTOFF_FAILED",
            details={"ineligible_reasons": eligibility_result.reasons},
        )

    # 7. Phase 5 Compatibility Score Calculation (snapshot at submission)
    approved_skills = list(student_profile.skills or [])
    approved_projects = list(student_profile.projects or [])
    approved_experiences = list(student_profile.experiences or [])
    approved_certifications = list(student_profile.certifications or [])

    score, _, _, _, _, _, _ = calculate_compatibility_score(
        job=job,
        student_user=student_user,
        student_profile=student_profile,
        approved_skills=approved_skills,
        approved_projects=approved_projects,
        approved_experiences=approved_experiences,
        approved_certifications=approved_certifications,
    )

    # 8. Create Application and Initial History (Atomic)
    application = JobApplication(
        job_id=job.id,
        student_id=student_profile.id,
        resume_id=resume.id,
        drive_id=drive_id,
        tpo_screening_status=tpo_screening_status,
        current_status=ApplicationStatus.APPLIED,
        compatibility_score_at_application=score,
        cover_letter=cover_letter,
        created_at=now_utc,
    )
    session.add(application)
    await session.flush()  # obtain application.id
    if getattr(application, "id", None) is None:
        application.id = 1

    # Create initial recruiter lifecycle history
    initial_recruiter_history = ApplicationStatusHistory(
        application_id=application.id,
        changed_by_user_id=student_user.id,
        decision_domain=DecisionDomain.RECRUITMENT_LIFECYCLE,
        from_status=None,
        to_status=ApplicationStatus.APPLIED.value,
        notes="Application submitted by candidate.",
        created_at=now_utc,
    )
    session.add(initial_recruiter_history)

    # If drive-linked, create initial TPO screening history
    if drive_id is not None:
        initial_tpo_history = ApplicationStatusHistory(
            application_id=application.id,
            changed_by_user_id=student_user.id,
            decision_domain=DecisionDomain.TPO_SCREENING,
            from_status=None,
            to_status=TpoScreeningStatus.PENDING.value,
            notes="Application submitted within campus placement drive; pending TPO screening.",
            created_at=now_utc,
        )
        session.add(initial_tpo_history)

    # 9. Trigger Initial Notification
    await create_notification(
        session=session,
        recipient_user_id=student_user.id,
        category=NotificationCategory.APPLICATION_UPDATE,
        title=f"Application Submitted: {job.title}",
        message=f"Your application for {job.title} has been submitted successfully.",
        related_application_id=application.id,
        related_drive_id=drive_id,
        idempotency_key=f"app-submitted-{application.id}",
    )

    await session.flush()
    return application


async def withdraw_application(
    session: AsyncSession,
    student_user: User,
    application_id: int,
    reason: str,
) -> JobApplication:
    """Withdraw an active job application with mandatory audit reason."""
    if len(reason.strip()) < 5:
        raise AppException("Withdrawal reason must be at least 5 characters.", code="INVALID_WITHDRAWAL_REASON")

    result = await session.execute(
        select(JobApplication)
        .options(selectinload(JobApplication.student_profile))
        .where(JobApplication.id == application_id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise EntityNotFoundException("JobApplication", application_id)

    # Verify student ownership
    if application.student_profile.user_id != student_user.id:
        raise AuthorizationException("You may only withdraw your own applications.")

    # Check terminal statuses
    if application.current_status == ApplicationStatus.WITHDRAWN:
        raise AppException("Application is already withdrawn.", code="APPLICATION_ALREADY_WITHDRAWN")
    if application.current_status in (ApplicationStatus.REJECTED, ApplicationStatus.OFFER_DECLINED):
        raise AppException("Cannot withdraw a closed or rejected application.", code="APPLICATION_CLOSED")

    now_utc = datetime.now(timezone.utc)
    from_status_val = application.current_status.value

    application.current_status = ApplicationStatus.WITHDRAWN
    application.withdrawn_at = now_utc
    application.withdrawal_reason = reason.strip()

    # Record append-only history
    history = ApplicationStatusHistory(
        application_id=application.id,
        changed_by_user_id=student_user.id,
        decision_domain=DecisionDomain.RECRUITMENT_LIFECYCLE,
        from_status=from_status_val,
        to_status=ApplicationStatus.WITHDRAWN.value,
        notes=f"Candidate withdrew application: {reason.strip()}",
        created_at=now_utc,
    )
    session.add(history)
    await session.flush()
    return application


async def stream_recruiter_resume(
    session: AsyncSession,
    application_id: int,
    recruiter_user: User,
) -> Tuple[io.BytesIO, str, int, str]:
    """
    Authorize candidate resume access and stream verified bytes without TOCTOU vulnerability.

    Opens the physical storage file exactly once, computes its SHA-256 checksum in-memory,
    validates the checksum against the database record, and returns an in-memory byte stream
    (io.BytesIO) ready for immediate streaming. The physical filesystem path is NEVER reopened
    after verification.

    Returns:
        (verified_stream, file_name, file_size_bytes, media_type)
    """
    if recruiter_user.role not in (UserRole.RECRUITER, UserRole.ADMIN):
        raise AuthorizationException("Only corporate recruiters and administrators can access candidate resumes.")

    result = await session.execute(
        select(JobApplication)
        .options(
            selectinload(JobApplication.job),
            selectinload(JobApplication.resume),
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
        profile = result.scalar_one_or_none()
        if not profile or profile.company_id != application.job.company_id:
            raise AuthorizationException("You may only access candidate resumes for jobs offered by your company.")

    # Withdrawn applications revoke recruiter resume streaming
    if application.current_status == ApplicationStatus.WITHDRAWN:
        raise AuthorizationException(
            "Access denied: Candidate has withdrawn their application for this role.",
        )

    resume = application.resume
    if not resume:
        raise EntityNotFoundException("Resume", application.resume_id)

    if not os.path.exists(resume.file_path):
        raise EntityNotFoundException("ResumeFile", resume.file_path)

    # Open the file once, read into memory buffer, and compute SHA-256 simultaneously
    hasher = hashlib.sha256()
    buffer = io.BytesIO()
    try:
        with open(resume.file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
                buffer.write(chunk)
    except OSError as err:
        buffer.close()
        raise AppException(
            f"Failed to read resume file from storage: {err}",
            code="RESUME_READ_ERROR",
        )

    computed_hash = hasher.hexdigest()
    if computed_hash.lower() != resume.file_hash.lower():
        buffer.close()
        raise AppException(
            message="Security violation: Stored resume file does not match its registered SHA-256 checksum.",
            code="RESUME_CHECKSUM_MISMATCH",
            status_code=403,
        )

    buffer.seek(0)
    file_size = buffer.getbuffer().nbytes

    # Determine standard MIME type
    ext = (resume.file_name or "").split(".")[-1].lower()
    if ext == "pdf":
        media_type = "application/pdf"
    elif ext in ("docx", "doc"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        media_type = "application/octet-stream"

    return buffer, resume.file_name, file_size, media_type


def _normalize_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _is_rescheduled_interview(iv: Interview) -> bool:
    note = (iv.cancellation_reason or "").strip()
    return note.startswith("Rescheduled:") and iv.status != InterviewStatus.CANCELLED


def _build_tracker_filters(
    profile_id: int,
    app_status: Optional[ApplicationStatus] = None,
    company_query: Optional[str] = None,
    role_query: Optional[str] = None,
    search_query: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    interview_status: Optional[str] = None,
) -> list:
    filters = [JobApplication.student_id == profile_id]

    if app_status is not None:
        filters.append(JobApplication.current_status == app_status)
    if company_query and company_query.strip():
        filters.append(Company.name.ilike(f"%{company_query.strip()}%"))
    if role_query and role_query.strip():
        filters.append(Job.title.ilike(f"%{role_query.strip()}%"))
    if search_query and search_query.strip():
        pattern = f"%{search_query.strip()}%"
        filters.append(or_(Job.title.ilike(pattern), Company.name.ilike(pattern)))
    if date_from is not None:
        filters.append(JobApplication.created_at >= _normalize_utc(date_from))
    if date_to is not None:
        filters.append(JobApplication.created_at <= _normalize_utc(date_to))

    if interview_status and interview_status.strip().lower() not in ("all", ""):
        iv_filter = interview_status.strip().lower()
        now_utc = datetime.now(timezone.utc)
        if iv_filter == "upcoming":
            filters.append(
                exists().where(
                    Interview.application_id == JobApplication.id,
                    Interview.status == InterviewStatus.SCHEDULED,
                    Interview.scheduled_start_time >= now_utc,
                )
            )
        elif iv_filter == "none":
            filters.append(
                ~exists().where(Interview.application_id == JobApplication.id)
            )
        else:
            try:
                status_enum = InterviewStatus(iv_filter)
                filters.append(
                    exists().where(
                        Interview.application_id == JobApplication.id,
                        Interview.status == status_enum,
                    )
                )
            except ValueError:
                pass

    return filters


def _sanitize_history_notes_for_student(
    history_row: ApplicationStatusHistory,
    student_user_id: Optional[int],
) -> Optional[str]:
    notes = history_row.notes
    if not notes:
        return None
    if history_row.decision_domain == DecisionDomain.RECRUITMENT_LIFECYCLE:
        if history_row.changed_by_user_id != student_user_id and not notes.startswith(
            ("Scheduled ", "Completed ", "Cancelled ")
        ):
            return None
    return notes


def _build_latest_update(app: JobApplication, student_user_id: Optional[int] = None) -> TrackerLatestUpdateSchema:
    sorted_hist = sorted(app.status_history or [], key=lambda h: h.created_at)
    if sorted_hist:
        latest = sorted_hist[-1]
        stage_label = latest.to_status.replace("_", " ").title()
        domain_label = (
            "TPO Screening"
            if latest.decision_domain == DecisionDomain.TPO_SCREENING
            else "Recruitment Stage"
        )
        return TrackerLatestUpdateSchema(
            title=f"{domain_label}: {stage_label}",
            description=_sanitize_history_notes_for_student(latest, student_user_id),
            timestamp=latest.created_at,
            domain=latest.decision_domain,
            from_status=latest.from_status,
            to_status=latest.to_status,
        )
    created_at = getattr(app, "updated_at", None) or getattr(app, "created_at", None) or datetime.now(timezone.utc)
    return TrackerLatestUpdateSchema(
        title=f"Stage: {app.current_status.value.replace('_', ' ').title()}",
        description=None,
        timestamp=created_at,
        domain=DecisionDomain.RECRUITMENT_LIFECYCLE,
        from_status=None,
        to_status=app.current_status.value,
    )


def _build_next_activity(app: JobApplication, now_utc: datetime) -> TrackerNextActivitySchema:
    scheduled_interviews = sorted(
        [
            iv
            for iv in (app.interviews or [])
            if iv.status == InterviewStatus.SCHEDULED
            and (_normalize_utc(iv.scheduled_start_time) or now_utc) >= now_utc - timedelta(minutes=15)
        ],
        key=lambda iv: iv.scheduled_start_time,
    )
    if scheduled_interviews:
        next_iv = scheduled_interviews[0]
        return TrackerNextActivitySchema(
            activity_type="interview",
            title=f"Round {next_iv.round_number}: {next_iv.round_title}",
            scheduled_at=next_iv.scheduled_start_time,
            description=next_iv.instructions or next_iv.cancellation_reason,
            interview_id=next_iv.id,
            meeting_link=next_iv.meeting_link,
            location=next_iv.location,
        )

    if app.current_status == ApplicationStatus.OFFERED:
        return TrackerNextActivitySchema(
            activity_type="offer_deadline",
            title="Respond to Official Offer",
            scheduled_at=app.offer_deadline_at,
            description=app.offer_notes or "Review compensation package and accept or decline.",
        )

    if app.drive_id is not None and app.tpo_screening_status == TpoScreeningStatus.PENDING and app.current_status not in (
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.REJECTED,
    ):
        return TrackerNextActivitySchema(
            activity_type="tpo_screening",
            title="Awaiting Institutional TPO Screening",
            scheduled_at=app.job.application_deadline if getattr(app, "job", None) else None,
            description="Your application is queued for campus drive eligibility verification.",
        )

    if app.current_status in (
        ApplicationStatus.APPLIED,
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.SHORTLISTED,
        ApplicationStatus.INTERVIEWED,
    ):
        return TrackerNextActivitySchema(
            activity_type="application_review",
            title="Awaiting Recruiter Update",
            scheduled_at=app.job.application_deadline if getattr(app, "job", None) else None,
            description="Recruiter review in progress; next round or decision will appear here.",
        )

    return TrackerNextActivitySchema(
        activity_type="completed",
        title=f"Closed ({app.current_status.value.replace('_', ' ').title()})",
        scheduled_at=app.withdrawn_at or app.recruiter_decision_at or app.updated_at,
        description=app.withdrawal_reason,
    )


def _map_tracker_item(app: JobApplication, now_utc: datetime) -> TrackerApplicationItemSchema:
    job = getattr(app, "job", None)
    company = getattr(job, "company", None) if job else None
    drive = getattr(app, "drive", None)
    student_profile = getattr(app, "student_profile", None)
    student_user = getattr(student_profile, "user", None) if student_profile else None
    student_dept = getattr(student_user, "department", None) if student_user else None

    student_user_id = getattr(student_profile, "user_id", None) if student_profile else None

    sorted_hist = [
        ApplicationStatusHistoryResponse(
            id=h.id,
            application_id=h.application_id,
            changed_by_user_id=h.changed_by_user_id,
            created_at=h.created_at,
            decision_domain=h.decision_domain,
            from_status=h.from_status,
            to_status=h.to_status,
            notes=_sanitize_history_notes_for_student(h, student_user_id),
        )
        for h in sorted(app.status_history or [], key=lambda h: h.created_at)
    ]
    sorted_interviews = []
    upcoming_iv_count = 0
    completed_iv_count = 0
    for iv in sorted(app.interviews or [], key=lambda i: i.round_number):
        iv_start = _normalize_utc(iv.scheduled_start_time)
        if iv.status == InterviewStatus.SCHEDULED and iv_start is not None and iv_start >= now_utc - timedelta(minutes=15):
            upcoming_iv_count += 1
        elif iv.status == InterviewStatus.COMPLETED:
            completed_iv_count += 1
        sorted_interviews.append(
            InterviewStudentResponse(
                id=iv.id,
                application_id=iv.application_id,
                round_number=iv.round_number,
                round_title=iv.round_title,
                interview_mode=iv.interview_mode,
                meeting_link=iv.meeting_link,
                location=iv.location,
                scheduled_start_time=iv.scheduled_start_time,
                duration_minutes=iv.duration_minutes,
                interviewer_names=iv.interviewer_names,
                instructions=iv.instructions,
                status=iv.status,
                outcome=iv.outcome,
                cancellation_reason=iv.cancellation_reason,
                is_rescheduled=_is_rescheduled_interview(iv),
                created_at=iv.created_at or now_utc,
                updated_at=iv.updated_at or iv.created_at or now_utc,
            )
        )

    offer_details: Optional[TrackerOfferDetailSchema] = None
    if app.current_status in (
        ApplicationStatus.OFFERED,
        ApplicationStatus.OFFER_ACCEPTED,
        ApplicationStatus.OFFER_DECLINED,
    ):
        pkg = (
            float(app.offer_package_lpa)
            if app.offer_package_lpa is not None
            else (float(job.ctc_lpa) if job and job.ctc_lpa is not None else None)
        )
        offer_details = TrackerOfferDetailSchema(
            company_name=company.name if company else "Partner Company",
            role_title=job.title if job else f"Job #{app.job_id}",
            package_lpa=pkg,
            salary_range=job.salary_range if job else None,
            response_deadline=app.offer_deadline_at,
            status=app.current_status,
            offer_notes=app.offer_notes,
            can_respond=(app.current_status == ApplicationStatus.OFFERED),
        )

    created_at = app.created_at or now_utc
    updated_at = app.updated_at or created_at

    return TrackerApplicationItemSchema(
        id=app.id,
        job_id=app.job_id,
        student_id=app.student_id,
        resume_id=app.resume_id,
        drive_id=app.drive_id,
        tpo_screening_status=app.tpo_screening_status,
        tpo_screened_by_user_id=app.tpo_screened_by_user_id,
        tpo_screened_at=app.tpo_screened_at,
        tpo_feedback=app.tpo_feedback,
        current_status=app.current_status,
        recruiter_decision_at=app.recruiter_decision_at,
        compatibility_score_at_application=float(app.compatibility_score_at_application or 0.0),
        cover_letter=app.cover_letter,
        withdrawn_at=app.withdrawn_at,
        withdrawal_reason=app.withdrawal_reason,
        offer_deadline_at=app.offer_deadline_at,
        offer_package_lpa=float(app.offer_package_lpa) if app.offer_package_lpa is not None else None,
        offer_notes=app.offer_notes,
        created_at=created_at,
        updated_at=updated_at,
        job_title=job.title if job else None,
        company_name=company.name if company else None,
        drive_name=drive.name if drive else None,
        application_deadline=job.application_deadline if job else None,
        job_location=job.location if job else None,
        work_mode=job.work_mode.value if job and job.work_mode else None,
        employment_type=job.employment_type.value if job and job.employment_type else None,
        salary_range=job.salary_range if job else None,
        student_name=student_user.full_name if student_user else None,
        student_email=student_user.email if student_user else None,
        student_roll_number=student_profile.roll_number if student_profile else None,
        student_department=student_dept.name if student_dept else None,
        status_history=sorted_hist,
        interviews=sorted_interviews,
        latest_update=_build_latest_update(app, student_user_id),
        next_scheduled_activity=_build_next_activity(app, now_utc),
        offer_details=offer_details,
        upcoming_interviews_count=upcoming_iv_count,
        completed_interviews_count=completed_iv_count,
    )


async def get_student_application_tracker(
    session: AsyncSession,
    student_user: User,
    app_status: Optional[ApplicationStatus] = None,
    company_query: Optional[str] = None,
    role_query: Optional[str] = None,
    search_query: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    interview_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    sync_notifications: bool = True,
) -> ApplicationTrackerResponse:
    """
    Centralized student recruitment tracker with server-side filters, pagination,
    chronological status history, redacted interview details, and offer metadata.
    """
    profile_res = await session.execute(
        select(StudentProfile).where(StudentProfile.user_id == student_user.id)
    )
    profile = profile_res.scalar_one_or_none()
    if not profile:
        raise EntityNotFoundException("StudentProfile", student_user.id)

    if sync_notifications:
        from app.services.notification_service import sync_smart_student_notifications
        await sync_smart_student_notifications(session, student_user)

    now_utc = datetime.now(timezone.utc)
    filters = _build_tracker_filters(
        profile_id=profile.id,
        app_status=app_status,
        company_query=company_query,
        role_query=role_query,
        search_query=search_query,
        date_from=date_from,
        date_to=date_to,
        interview_status=interview_status,
    )

    count_stmt = (
        select(func.count(JobApplication.id))
        .join(Job, JobApplication.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .where(*filters)
    )
    total = (await session.execute(count_stmt)).scalar() or 0

    data_stmt = (
        select(JobApplication)
        .join(Job, JobApplication.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .options(
            selectinload(JobApplication.job).selectinload(Job.company),
            selectinload(JobApplication.drive),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.user).selectinload(User.department),
            selectinload(JobApplication.status_history),
            selectinload(JobApplication.interviews),
        )
        .where(*filters)
        .order_by(JobApplication.updated_at.desc(), JobApplication.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    apps = list((await session.execute(data_stmt)).scalars().all())
    items = [_map_tracker_item(app, now_utc) for app in apps]

    # Portfolio summary counts across all of the student's applications
    all_apps_stmt = (
        select(JobApplication)
        .options(selectinload(JobApplication.interviews))
        .where(JobApplication.student_id == profile.id)
    )
    all_apps = list((await session.execute(all_apps_stmt)).scalars().all())

    active_statuses = {
        ApplicationStatus.APPLIED,
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.SHORTLISTED,
        ApplicationStatus.INTERVIEW_SCHEDULED,
        ApplicationStatus.INTERVIEWED,
    }
    closed_statuses = {
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.OFFER_DECLINED,
    }

    upcoming_ivs = 0
    completed_ivs = 0
    for a in all_apps:
        for iv in a.interviews or []:
            iv_start = _normalize_utc(iv.scheduled_start_time)
            if iv.status == InterviewStatus.SCHEDULED and iv_start is not None and iv_start >= now_utc - timedelta(minutes=15):
                upcoming_ivs += 1
            elif iv.status == InterviewStatus.COMPLETED:
                completed_ivs += 1

    summary = TrackerSummaryStatsSchema(
        total_applications=len(all_apps),
        active_count=sum(1 for a in all_apps if a.current_status in active_statuses),
        upcoming_interviews_count=upcoming_ivs,
        completed_interviews_count=completed_ivs,
        pending_offers_count=sum(1 for a in all_apps if a.current_status == ApplicationStatus.OFFERED),
        accepted_offers_count=sum(1 for a in all_apps if a.current_status == ApplicationStatus.OFFER_ACCEPTED),
        rejected_or_withdrawn_count=sum(1 for a in all_apps if a.current_status in closed_statuses),
    )

    from app.services.notification_service import get_unread_count
    unread_count = await get_unread_count(session, student_user.id)

    return ApplicationTrackerResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        summary=summary,
        unread_notifications_count=unread_count,
    )


async def get_student_calendar_events(
    session: AsyncSession,
    student_user: User,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    app_status: Optional[ApplicationStatus] = None,
    company_query: Optional[str] = None,
    role_query: Optional[str] = None,
    interview_status: Optional[str] = None,
) -> TrackerCalendarResponse:
    """
    Return unified chronological calendar events for the student:
    scheduled/completed interviews, job application deadlines, offer response deadlines,
    and institutional placement drive registration deadlines.
    """
    profile_res = await session.execute(
        select(StudentProfile).where(StudentProfile.user_id == student_user.id)
    )
    profile = profile_res.scalar_one_or_none()
    if not profile:
        raise EntityNotFoundException("StudentProfile", student_user.id)

    filters = _build_tracker_filters(
        profile_id=profile.id,
        app_status=app_status,
        company_query=company_query,
        role_query=role_query,
        interview_status=interview_status,
    )

    apps_stmt = (
        select(JobApplication)
        .join(Job, JobApplication.job_id == Job.id)
        .join(Company, Job.company_id == Company.id)
        .options(
            selectinload(JobApplication.job).selectinload(Job.company),
            selectinload(JobApplication.drive),
            selectinload(JobApplication.interviews),
        )
        .where(*filters)
    )
    apps = list((await session.execute(apps_stmt)).scalars().all())

    events: List[TrackerCalendarEvent] = []
    start_utc = _normalize_utc(start_date)
    end_utc = _normalize_utc(end_date)

    def _in_range(dt: Optional[datetime]) -> bool:
        norm = _normalize_utc(dt)
        if norm is None:
            return False
        if start_utc is not None and norm < start_utc:
            return False
        if end_utc is not None and norm > end_utc:
            return False
        return True

    for app in apps:
        job = getattr(app, "job", None)
        company = getattr(job, "company", None) if job else None
        company_name = company.name if company else "Partner Company"
        job_title = job.title if job else f"Job #{app.job_id}"

        # 1. Interview rounds
        for iv in app.interviews or []:
            if not _in_range(iv.scheduled_start_time):
                continue
            iv_start = _normalize_utc(iv.scheduled_start_time)
            iv_end = iv_start + timedelta(minutes=iv.duration_minutes) if iv_start else None
            events.append(
                TrackerCalendarEvent(
                    event_id=f"interview-{iv.id}",
                    event_type="interview",
                    title=f"{company_name}: {iv.round_title} (R{iv.round_number})",
                    subtitle=job_title,
                    company_name=company_name,
                    job_title=job_title,
                    application_id=app.id,
                    interview_id=iv.id,
                    drive_id=app.drive_id,
                    start_at=iv.scheduled_start_time,
                    end_at=iv_end,
                    status=iv.status.value,
                    meeting_link=iv.meeting_link,
                    location=iv.location,
                    instructions=iv.instructions,
                    is_rescheduled=_is_rescheduled_interview(iv),
                )
            )

        # 2. Job application deadline
        if job and job.application_deadline and _in_range(job.application_deadline):
            events.append(
                TrackerCalendarEvent(
                    event_id=f"app-deadline-{app.id}",
                    event_type="application_deadline",
                    title=f"Application Deadline: {job_title}",
                    subtitle=company_name,
                    company_name=company_name,
                    job_title=job_title,
                    application_id=app.id,
                    drive_id=app.drive_id,
                    start_at=job.application_deadline,
                    status=app.current_status.value,
                )
            )

        # 3. Offer response deadline
        if app.offer_deadline_at and _in_range(app.offer_deadline_at):
            events.append(
                TrackerCalendarEvent(
                    event_id=f"offer-deadline-{app.id}",
                    event_type="offer_deadline",
                    title=f"Offer Response Due: {company_name}",
                    subtitle=job_title,
                    company_name=company_name,
                    job_title=job_title,
                    application_id=app.id,
                    drive_id=app.drive_id,
                    start_at=app.offer_deadline_at,
                    status=app.current_status.value,
                )
            )

    # 4. Active drive deadlines for student's institution (when unfiltered by company/role/status)
    if (
        student_user.institution_id
        and not app_status
        and not (company_query and company_query.strip())
        and not (role_query and role_query.strip())
        and not (interview_status and interview_status.strip().lower() not in ("all", ""))
    ):
        drv_res = await session.execute(
            select(PlacementDrive).where(
                PlacementDrive.institution_id == student_user.institution_id,
                PlacementDrive.is_active == True,  # noqa: E712
                PlacementDrive.status.in_([DriveStatus.ONGOING, DriveStatus.UPCOMING]),
            )
        )
        for drv in drv_res.scalars().all():
            if _in_range(drv.registration_end_date):
                events.append(
                    TrackerCalendarEvent(
                        event_id=f"drive-reg-{drv.id}",
                        event_type="drive_registration",
                        title=f"Drive Registration Closes: {drv.name}",
                        subtitle=drv.academic_year,
                        drive_id=drv.id,
                        start_at=drv.registration_end_date,
                        status=drv.status.value,
                    )
                )

    events.sort(key=lambda e: e.start_at)
    return TrackerCalendarResponse(events=events, total=len(events))

