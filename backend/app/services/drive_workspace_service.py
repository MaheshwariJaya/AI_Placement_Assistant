"""
Service layer for TASK 06: Complete Placement Drive Management Workspace.

Covers:
- Form metadata options (institution-scoped companies, jobs, departments, coordinators)
- 7-stage lifecycle transition validation (reusing VALID_DRIVE_LIFECYCLE_TRANSITIONS)
- Drive dashboard KPIs (registrations, deterministic eligibility, applications, shortlists, interviews, offers, final placements)
- Authorized student & TPO drive registration with duplicate prevention & deterministic eligibility audit
- Candidate management (eligible candidates, ineligible audit records, screening & final outcomes)
- Activity scheduling (PPT, presentations, assessments, interviews, venue/slots, coordinator assignment)
- Attendance tracking with coordinator RBAC & append-only audit trail
- Drive-specific announcements & notifications via notification_service
- Drive participation, eligibility, attendance & outcome reports
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import (
    AppException,
    AuthorizationException,
    EntityNotFoundException,
    ResourceConflictException,
)
from app.models.company import Company
from app.models.job import Job, JobStatus
from app.models.organization import Department
from app.models.placement import (
    ApplicationStatus,
    DriveActivityStatus,
    DriveActivityType,
    DriveLifecyclePhase,
    DriveMode,
    DriveRegistrationStatus,
    DriveStatus,
    Interview,
    InterviewStatus,
    JobApplication,
    NotificationCategory,
    NotificationPreference,
    PlacementDrive,
    PlacementDriveActivity,
    PlacementDriveAnnouncement,
    PlacementDriveAttendance,
    PlacementDriveAttendanceAudit,
    PlacementDriveJob,
    PlacementDriveRegistration,
    TpoScreeningStatus,
)
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from app.schemas.drive_workspace import (
    DriveActivityAttendanceSummary,
    DriveActivityCreate,
    DriveActivityResponse,
    DriveActivityUpdate,
    DriveAnnouncementCreate,
    DriveAnnouncementResponse,
    DriveAttendanceAuditResponse,
    DriveAttendanceBatchRequest,
    DriveAttendanceRecordResponse,
    DriveCandidateItem,
    DriveCandidatesResponse,
    DriveDashboardJobBreakdown,
    DriveDashboardResponse,
    DriveFormCompanyOption,
    DriveFormCoordinatorOption,
    DriveFormDepartmentOption,
    DriveFormJobOption,
    DriveFormOptionsResponse,
    DriveRegistrationResponse,
    DriveReportResponse,
)
from app.services.drive_service import (
    VALID_DRIVE_LIFECYCLE_TRANSITIONS,
    derive_phase_from_status,
    validate_drive_lifecycle_transition,
)
from app.services.eligibility_service import evaluate_student_job_eligibility
from app.services.notification_service import create_notification


def _resolve_tpo_institution_id(user: User) -> int:
    if user.role == UserRole.TPO:
        if user.institution_id is None:
            raise AuthorizationException("TPO user must belong to an academic institution.")
        return user.institution_id
    if user.role == UserRole.ADMIN:
        return user.institution_id or 1
    raise AuthorizationException("Only authorized TPO or Admin staff can perform this action.")


async def _load_drive_scoped(
    session: AsyncSession,
    drive_id: int,
    user: User,
    allow_student: bool = False,
    allow_recruiter: bool = False,
) -> PlacementDrive:
    stmt = (
        select(PlacementDrive)
        .options(
            selectinload(PlacementDrive.drive_jobs)
            .selectinload(PlacementDriveJob.job)
            .selectinload(Job.company),
            selectinload(PlacementDrive.drive_jobs)
            .selectinload(PlacementDriveJob.job)
            .selectinload(Job.skills),
            selectinload(PlacementDrive.drive_jobs)
            .selectinload(PlacementDriveJob.job)
            .selectinload(Job.eligible_departments),
        )
        .where(PlacementDrive.id == drive_id)
    )
    drive = (await session.execute(stmt)).scalar_one_or_none()
    if not drive:
        raise EntityNotFoundException("PlacementDrive", drive_id)

    if user.role == UserRole.ADMIN:
        return drive
    if user.role == UserRole.TPO:
        if user.institution_id != drive.institution_id:
            raise AuthorizationException("You may only manage placement drives of your own institution.")
        return drive
    if user.role == UserRole.STUDENT:
        if not allow_student:
            raise AuthorizationException("Only authorized TPO staff may manage institutional drives.")
        if user.institution_id != drive.institution_id:
            raise AuthorizationException("You cannot access placement drives outside your institution.")
        return drive
    if user.role == UserRole.RECRUITER:
        if not allow_recruiter:
            raise AuthorizationException("Recruiters are not authorized for this institutional drive endpoint.")
        company_id = user.recruiter_profile.company_id if getattr(user, "recruiter_profile", None) else None
        if not company_id:
            raise AuthorizationException("Recruiter profile must be affiliated with a company.")
        has_job = any(
            dj.is_active and dj.job is not None and dj.job.company_id == company_id
            for dj in (drive.drive_jobs or [])
        )
        if not has_job:
            raise AuthorizationException("Recruiter cannot access drives not associated with their company.")
        return drive

    raise AuthorizationException("Unauthorized role for drive operation.")


def _evaluate_drive_eligibility_for_student(
    drive: PlacementDrive,
    student_profile: StudentProfile,
    student_user: User,
) -> Tuple[bool, List[str], List[int], List[str], Dict[str, Any]]:
    """
    Deterministically evaluate whether a student qualifies for a placement drive
    using drive batch/department scope + existing evaluate_student_job_eligibility engine.
    """
    reasons: List[str] = []
    batches = list(getattr(drive, "target_graduation_batches", None) or [])
    if drive.target_graduation_year not in batches:
        batches.append(drive.target_graduation_year)

    if batches and student_profile.graduation_year not in batches:
        reasons.append(
            f"Graduation batch {student_profile.graduation_year} is outside drive target batches ({', '.join(map(str, sorted(batches)))})"
        )

    dept_ids = list(getattr(drive, "eligible_department_ids", None) or [])
    if dept_ids:
        if student_user.department_id is None or student_user.department_id not in dept_ids:
            dept_label = student_user.department.code if student_user.department else "Undeclared"
            reasons.append(f"Department '{dept_label}' is not listed among eligible drive departments")

    if not student_user.is_active:
        reasons.append("Student account is inactive")

    active_jobs = [dj.job for dj in (drive.drive_jobs or []) if dj.is_active and dj.job is not None]
    skill_names = [s.skill_name for s in (getattr(student_profile, "skills", None) or [])]

    eligible_job_ids: List[int] = []
    eligible_job_titles: List[str] = []
    job_failure_reasons: List[str] = []

    if active_jobs:
        for job in active_jobs:
            res = evaluate_student_job_eligibility(
                job=job,
                student_user=student_user,
                student_profile=student_profile,
                student_skill_names=skill_names,
            )
            if res.is_eligible:
                eligible_job_ids.append(job.id)
                eligible_job_titles.append(job.title)
            else:
                for r in res.reasons:
                    tagged = f"{job.title}: {r}"
                    if tagged not in job_failure_reasons:
                        job_failure_reasons.append(tagged)

        if not eligible_job_ids:
            reasons.extend(job_failure_reasons[:4] or ["Did not satisfy eligibility criteria for any active drive role"])
    else:
        # Before jobs are added, ensure basic academic validity
        cgpa_val = float(student_profile.cgpa) if student_profile.cgpa is not None else -1.0
        if cgpa_val < 0.0 or cgpa_val > 10.0:
            reasons.append("Academic CGPA is missing or outside 0.0-10.0 range")

    is_eligible = len(reasons) == 0
    snapshot = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "is_eligible": is_eligible,
        "reasons": reasons,
        "eligible_job_ids": eligible_job_ids,
        "cgpa": float(student_profile.cgpa or 0.0),
        "active_backlogs": int(student_profile.active_backlogs or 0),
        "graduation_year": int(student_profile.graduation_year),
        "department_id": student_user.department_id,
    }
    return is_eligible, reasons, eligible_job_ids, eligible_job_titles, snapshot


async def get_drive_form_options(
    session: AsyncSession,
    current_user: User,
) -> DriveFormOptionsResponse:
    inst_id = _resolve_tpo_institution_id(current_user)

    companies = list(
        (
            await session.execute(
                select(Company)
                .where(
                    Company.is_active.is_(True),
                    (Company.institution_id.is_(None)) | (Company.institution_id == inst_id),
                )
                .order_by(Company.name.asc())
            )
        )
        .scalars()
        .all()
    )

    jobs = list(
        (
            await session.execute(
                select(Job)
                .options(
                    selectinload(Job.company),
                    selectinload(Job.eligible_departments),
                )
                .where(
                    Job.is_active.is_(True),
                    Job.status.in_([JobStatus.PUBLISHED, JobStatus.DRAFT]),
                    (Job.institution_id.is_(None)) | (Job.institution_id == inst_id),
                )
                .order_by(Job.created_at.desc())
            )
        )
        .scalars()
        .all()
    )

    depts = list(
        (
            await session.execute(
                select(Department)
                .where(Department.institution_id == inst_id, Department.is_active.is_(True))
                .order_by(Department.code.asc())
            )
        )
        .scalars()
        .all()
    )

    coordinators = list(
        (
            await session.execute(
                select(User)
                .where(
                    User.institution_id == inst_id,
                    User.is_active.is_(True),
                    User.role.in_([UserRole.TPO, UserRole.ADMIN]),
                )
                .order_by(User.full_name.asc())
            )
        )
        .scalars()
        .all()
    )

    batch_rows = list(
        (
            await session.execute(
                select(StudentProfile.graduation_year)
                .join(User, StudentProfile.user_id == User.id)
                .where(User.institution_id == inst_id, User.role == UserRole.STUDENT, User.is_active.is_(True))
                .distinct()
                .order_by(StudentProfile.graduation_year.asc())
            )
        )
        .scalars()
        .all()
    )

    return DriveFormOptionsResponse(
        institution_id=inst_id,
        companies=[
            DriveFormCompanyOption(
                id=c.id,
                name=c.name,
                industry=c.industry,
                is_verified=c.is_verified,
                institution_id=c.institution_id,
            )
            for c in companies
        ],
        jobs=[
            DriveFormJobOption(
                id=j.id,
                company_id=j.company_id,
                company_name=j.company.name if j.company else f"Company #{j.company_id}",
                title=j.title,
                employment_type=j.employment_type.value,
                status=j.status.value,
                location=j.location,
                min_cgpa=float(j.min_cgpa or 0.0),
                target_graduation_year=j.target_graduation_year,
                application_deadline=j.application_deadline,
                eligible_department_ids=[ed.department_id for ed in (j.eligible_departments or [])],
            )
            for j in jobs
        ],
        departments=[
            DriveFormDepartmentOption(id=d.id, code=d.code, name=d.name)
            for d in depts
        ],
        coordinators=[
            DriveFormCoordinatorOption(id=u.id, full_name=u.full_name, email=u.email, role=u.role.value)
            for u in coordinators
        ],
        graduation_batches=[int(y) for y in batch_rows if y is not None],
    )


async def transition_drive_lifecycle(
    session: AsyncSession,
    current_user: User,
    drive_id: int,
    target_phase: DriveLifecyclePhase,
) -> Tuple[PlacementDrive, int, int]:
    if current_user.role not in (UserRole.TPO, UserRole.ADMIN):
        raise AuthorizationException("Only authorized TPO or Admin staff can transition drive states.")

    drive = await _load_drive_scoped(session, drive_id, current_user)
    synced_status = validate_drive_lifecycle_transition(drive, target_phase)
    drive.lifecycle_phase = target_phase
    drive.status = synced_status
    await session.flush()
    await session.refresh(drive, attribute_names=["updated_at", "lifecycle_phase", "status"])

    total_jobs = sum(1 for dj in (drive.drive_jobs or []) if dj.is_active)
    total_apps = (
        await session.execute(select(func.count(JobApplication.id)).where(JobApplication.drive_id == drive.id))
    ).scalar() or 0
    return drive, total_jobs, total_apps


async def _load_institution_cohort(session: AsyncSession, institution_id: int) -> List[Tuple[StudentProfile, User]]:
    rows = (
        await session.execute(
            select(StudentProfile, User)
            .join(User, StudentProfile.user_id == User.id)
            .options(
                selectinload(StudentProfile.skills),
                selectinload(User.department),
            )
            .where(
                User.institution_id == institution_id,
                User.role == UserRole.STUDENT,
                User.is_active.is_(True),
            )
            .order_by(StudentProfile.roll_number.asc())
        )
    ).all()
    return [(sp, usr) for sp, usr in rows]


async def get_drive_dashboard(
    session: AsyncSession,
    current_user: User,
    drive_id: int,
) -> DriveDashboardResponse:
    drive = await _load_drive_scoped(session, drive_id, current_user, allow_recruiter=False)
    cohort = await _load_institution_cohort(session, drive.institution_id)

    eligible_cnt = 0
    ineligible_cnt = 0
    for sp, usr in cohort:
        ok, *_ = _evaluate_drive_eligibility_for_student(drive, sp, usr)
        if ok:
            eligible_cnt += 1
        else:
            ineligible_cnt += 1

    regs = list(
        (
            await session.execute(
                select(PlacementDriveRegistration).where(
                    PlacementDriveRegistration.drive_id == drive.id,
                    PlacementDriveRegistration.status == DriveRegistrationStatus.REGISTERED,
                )
            )
        )
        .scalars()
        .all()
    )
    apps = list(
        (
            await session.execute(
                select(JobApplication)
                .options(selectinload(JobApplication.job).selectinload(Job.company))
                .where(JobApplication.drive_id == drive.id)
            )
        )
        .scalars()
        .all()
    )
    app_ids = [a.id for a in apps]
    interviews: List[Interview] = []
    if app_ids:
        interviews = list(
            (
                await session.execute(
                    select(Interview).where(Interview.application_id.in_(app_ids))
                )
            )
            .scalars()
            .all()
        )

    activities = list(
        (
            await session.execute(
                select(PlacementDriveActivity).where(PlacementDriveActivity.drive_id == drive.id)
            )
        )
        .scalars()
        .all()
    )
    ann_count = (
        await session.execute(
            select(func.count(PlacementDriveAnnouncement.id)).where(PlacementDriveAnnouncement.drive_id == drive.id)
        )
    ).scalar() or 0

    reg_student_ids = {r.student_id for r in regs} | {
        a.student_id for a in apps if a.current_status != ApplicationStatus.WITHDRAWN
    }

    shortlisted_apps = [
        a
        for a in apps
        if a.tpo_screening_status == TpoScreeningStatus.SHORTLISTED
        or a.current_status
        in {
            ApplicationStatus.SHORTLISTED,
            ApplicationStatus.INTERVIEW_SCHEDULED,
            ApplicationStatus.INTERVIEWED,
            ApplicationStatus.OFFERED,
            ApplicationStatus.OFFER_ACCEPTED,
        }
    ]
    offers_released = sum(
        1
        for a in apps
        if a.current_status
        in {ApplicationStatus.OFFERED, ApplicationStatus.OFFER_ACCEPTED, ApplicationStatus.OFFER_DECLINED}
    )
    placed_student_ids = {
        a.student_id for a in apps if a.current_status == ApplicationStatus.OFFER_ACCEPTED
    }

    int_sched = sum(1 for iv in interviews if iv.status == InterviewStatus.SCHEDULED)
    int_comp = sum(1 for iv in interviews if iv.status == InterviewStatus.COMPLETED)

    by_job: Dict[int, DriveDashboardJobBreakdown] = {}
    for dj in (drive.drive_jobs or []):
        if dj.is_active and dj.job is not None:
            by_job[dj.job.id] = DriveDashboardJobBreakdown(
                job_id=dj.job.id,
                title=dj.job.title,
                company_name=dj.job.company.name if dj.job.company else f"Company #{dj.job.company_id}",
            )
    for a in apps:
        if a.job_id not in by_job and a.job is not None:
            by_job[a.job_id] = DriveDashboardJobBreakdown(
                job_id=a.job.id,
                title=a.job.title,
                company_name=a.job.company.name if a.job.company else f"Company #{a.job.company_id}",
            )
        jb = by_job.get(a.job_id)
        if not jb:
            continue
        jb.applications_count += 1
        if a.tpo_screening_status == TpoScreeningStatus.SHORTLISTED or a.current_status in {
            ApplicationStatus.SHORTLISTED,
            ApplicationStatus.INTERVIEW_SCHEDULED,
            ApplicationStatus.INTERVIEWED,
            ApplicationStatus.OFFERED,
            ApplicationStatus.OFFER_ACCEPTED,
        }:
            jb.shortlisted_count += 1
        if a.current_status in {ApplicationStatus.INTERVIEW_SCHEDULED, ApplicationStatus.INTERVIEWED}:
            jb.interview_count += 1
        if a.current_status in {ApplicationStatus.OFFERED, ApplicationStatus.OFFER_ACCEPTED, ApplicationStatus.OFFER_DECLINED}:
            jb.offered_count += 1
        if a.current_status == ApplicationStatus.OFFER_ACCEPTED:
            jb.accepted_count += 1

    phase = getattr(drive, "lifecycle_phase", None) or derive_phase_from_status(drive.status)
    allowed_next = sorted(
        list(VALID_DRIVE_LIFECYCLE_TRANSITIONS.get(phase, set())),
        key=lambda p: p.value,
    )

    return DriveDashboardResponse(
        drive_id=drive.id,
        drive_name=drive.name,
        institution_id=drive.institution_id,
        academic_year=drive.academic_year,
        lifecycle_phase=phase,
        allowed_next_phases=allowed_next,
        total_registered_students=len(reg_student_ids),
        eligible_students=eligible_cnt,
        ineligible_students=ineligible_cnt,
        applications_received=len(apps),
        shortlisted_candidates=len({a.student_id for a in shortlisted_apps}),
        interview_scheduled_count=int_sched,
        interview_completed_count=int_comp,
        offers_released=offers_released,
        final_placements=len(placed_student_ids),
        activities_total=len(activities),
        activities_completed=sum(1 for ac in activities if ac.status == DriveActivityStatus.COMPLETED),
        announcements_count=int(ann_count),
        job_breakdown=list(by_job.values()),
    )


def _map_registration_row(
    reg: PlacementDriveRegistration,
    sp: StudentProfile,
    usr: User,
) -> DriveRegistrationResponse:
    return DriveRegistrationResponse(
        id=reg.id,
        drive_id=reg.drive_id,
        student_id=sp.id,
        user_id=usr.id,
        student_name=usr.full_name,
        roll_number=sp.roll_number,
        department_code=usr.department.code if usr.department else None,
        department_name=usr.department.name if usr.department else None,
        graduation_year=sp.graduation_year,
        cgpa=float(sp.cgpa or 0.0),
        active_backlogs=int(sp.active_backlogs or 0),
        registered_by_user_id=reg.registered_by_user_id,
        registration_source=reg.registration_source,
        status=reg.status,
        eligibility_passed=reg.eligibility_passed,
        eligibility_snapshot=reg.eligibility_snapshot or {},
        notes=reg.notes,
        registered_at=reg.registered_at,
    )


async def register_student_for_drive(
    session: AsyncSession,
    current_user: User,
    drive_id: int,
    target_student_id: Optional[int] = None,
    notes: Optional[str] = None,
) -> DriveRegistrationResponse:
    """
    Authorized registration workflow for a placement drive.
    - Students self-register (when drive registration window & phase are open).
    - Authorized TPO/Admin can enroll an eligible student in their institution.
    Validates eligibility deterministically and prevents duplicate registrations.
    """
    now_utc = datetime.now(timezone.utc)
    if current_user.role == UserRole.STUDENT:
        drive = await _load_drive_scoped(session, drive_id, current_user, allow_student=True)
        phase = getattr(drive, "lifecycle_phase", None) or derive_phase_from_status(drive.status)
        if not drive.is_active or phase not in (
            DriveLifecyclePhase.REGISTRATION_OPEN,
            DriveLifecyclePhase.ONGOING,
        ):
            raise AppException(
                f"Drive registration is not open (current phase: {phase.value}).",
                status_code=400,
                code="DRIVE_REGISTRATION_CLOSED",
            )
        reg_start = drive.registration_start_date
        reg_end = drive.registration_end_date
        if reg_start.tzinfo is None:
            reg_start = reg_start.replace(tzinfo=timezone.utc)
        if reg_end.tzinfo is None:
            reg_end = reg_end.replace(tzinfo=timezone.utc)
        if not (reg_start <= now_utc <= reg_end):
            raise AppException(
                "Current timestamp is outside the drive's official registration window.",
                status_code=400,
                code="REGISTRATION_WINDOW_CLOSED",
            )
        sp = (
            await session.execute(
                select(StudentProfile)
                .options(selectinload(StudentProfile.skills))
                .where(StudentProfile.user_id == current_user.id)
            )
        ).scalar_one_or_none()
        if not sp:
            raise EntityNotFoundException("StudentProfile", current_user.id)
        stu_user = (
            await session.execute(
                select(User).options(selectinload(User.department)).where(User.id == current_user.id)
            )
        ).scalar_one()
        source = "student_self"
    elif current_user.role in (UserRole.TPO, UserRole.ADMIN):
        drive = await _load_drive_scoped(session, drive_id, current_user)
        phase = getattr(drive, "lifecycle_phase", None) or derive_phase_from_status(drive.status)
        if not drive.is_active or phase in (DriveLifecyclePhase.COMPLETED, DriveLifecyclePhase.CANCELLED):
            raise AppException(
                f"Cannot register students for a {phase.value} placement drive.",
                status_code=400,
                code="DRIVE_INACTIVE",
            )
        if target_student_id is None:
            raise AppException("student_ids is required when enrolling via TPO.", status_code=400)
        row = (
            await session.execute(
                select(StudentProfile, User)
                .join(User, StudentProfile.user_id == User.id)
                .options(selectinload(StudentProfile.skills), selectinload(User.department))
                .where(StudentProfile.id == target_student_id)
            )
        ).first()
        if not row:
            raise EntityNotFoundException("StudentProfile", target_student_id)
        sp, stu_user = row
        if stu_user.institution_id != drive.institution_id:
            raise AuthorizationException("Cannot register a student from another academic institution.")
        source = "tpo_enrolled"
    else:
        raise AuthorizationException("Only students or authorized institutional TPO staff can register for drives.")

    # Duplicate check
    existing = (
        await session.execute(
            select(PlacementDriveRegistration)
            .where(
                PlacementDriveRegistration.drive_id == drive.id,
                PlacementDriveRegistration.student_id == sp.id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()

    if existing and existing.status == DriveRegistrationStatus.REGISTERED:
        raise ResourceConflictException(
            "Student is already registered for this placement drive.",
            details={"registration_id": existing.id, "drive_id": drive.id, "student_id": sp.id},
        )

    is_elig, reasons, _job_ids, _titles, snapshot = _evaluate_drive_eligibility_for_student(
        drive, sp, stu_user
    )
    if not is_elig:
        raise AppException(
            "Student does not meet deterministic eligibility requirements for this drive.",
            status_code=403,
            code="NOT_ELIGIBLE",
            details={"reasons": reasons},
        )

    if existing:
        existing.status = DriveRegistrationStatus.REGISTERED
        existing.registered_by_user_id = current_user.id
        existing.registration_source = source
        existing.eligibility_passed = True
        existing.eligibility_snapshot = snapshot
        existing.notes = notes
        existing.registered_at = now_utc
        await session.flush()
        return _map_registration_row(existing, sp, stu_user)

    reg = PlacementDriveRegistration(
        drive_id=drive.id,
        student_id=sp.id,
        registered_by_user_id=current_user.id,
        registration_source=source,
        status=DriveRegistrationStatus.REGISTERED,
        eligibility_passed=True,
        eligibility_snapshot=snapshot,
        notes=notes,
        registered_at=now_utc,
    )
    session.add(reg)
    await session.flush()
    return _map_registration_row(reg, sp, stu_user)


async def register_students_batch_for_drive(
    session: AsyncSession,
    current_user: User,
    drive_id: int,
    student_ids: List[int],
    notes: Optional[str] = None,
) -> List[DriveRegistrationResponse]:
    if current_user.role not in (UserRole.TPO, UserRole.ADMIN):
        raise AuthorizationException("Batch drive registration is restricted to authorized TPO staff.")
    results: List[DriveRegistrationResponse] = []
    for sid in dict.fromkeys(student_ids):
        results.append(
            await register_student_for_drive(
                session=session,
                current_user=current_user,
                drive_id=drive_id,
                target_student_id=sid,
                notes=notes,
            )
        )
    return results


async def list_drive_registrations(
    session: AsyncSession,
    current_user: User,
    drive_id: int,
) -> List[DriveRegistrationResponse]:
    drive = await _load_drive_scoped(session, drive_id, current_user, allow_student=True)
    stmt = (
        select(PlacementDriveRegistration, StudentProfile, User)
        .join(StudentProfile, PlacementDriveRegistration.student_id == StudentProfile.id)
        .join(User, StudentProfile.user_id == User.id)
        .options(selectinload(User.department))
        .where(PlacementDriveRegistration.drive_id == drive.id)
        .order_by(PlacementDriveRegistration.registered_at.desc())
    )
    if current_user.role == UserRole.STUDENT:
        stmt = stmt.where(User.id == current_user.id)

    rows = (await session.execute(stmt)).all()
    return [_map_registration_row(reg, sp, usr) for reg, sp, usr in rows]


async def get_drive_candidates(
    session: AsyncSession,
    current_user: User,
    drive_id: int,
) -> DriveCandidatesResponse:
    drive = await _load_drive_scoped(session, drive_id, current_user)
    cohort = await _load_institution_cohort(session, drive.institution_id)

    regs = {
        r.student_id: r
        for r in (
            await session.execute(
                select(PlacementDriveRegistration).where(PlacementDriveRegistration.drive_id == drive.id)
            )
        )
        .scalars()
        .all()
    }
    apps_by_student: Dict[int, List[JobApplication]] = {}
    all_apps = list(
        (
            await session.execute(
                select(JobApplication).where(JobApplication.drive_id == drive.id)
            )
        )
        .scalars()
        .all()
    )
    for a in all_apps:
        apps_by_student.setdefault(a.student_id, []).append(a)

    eligible: List[DriveCandidateItem] = []
    ineligible: List[DriveCandidateItem] = []

    for sp, usr in cohort:
        ok, reasons, job_ids, job_titles, _snap = _evaluate_drive_eligibility_for_student(drive, sp, usr)
        reg = regs.get(sp.id)
        s_apps = apps_by_student.get(sp.id, [])
        screenings = [a.tpo_screening_status.value for a in s_apps]
        statuses = [a.current_status.value for a in s_apps]
        latest_st = statuses[0] if statuses else None
        final_out: Optional[str] = None
        if any(a.current_status == ApplicationStatus.OFFER_ACCEPTED for a in s_apps):
            final_out = "Placed (Offer Accepted)"
        elif any(a.current_status == ApplicationStatus.OFFERED for a in s_apps):
            final_out = "Offer Extended"
        elif any(a.current_status == ApplicationStatus.OFFER_DECLINED for a in s_apps):
            final_out = "Offer Declined"

        item = DriveCandidateItem(
            student_id=sp.id,
            user_id=usr.id,
            full_name=usr.full_name,
            email=usr.email,
            roll_number=sp.roll_number,
            department_code=usr.department.code if usr.department else None,
            department_name=usr.department.name if usr.department else None,
            graduation_year=sp.graduation_year,
            cgpa=float(sp.cgpa or 0.0),
            active_backlogs=int(sp.active_backlogs or 0),
            is_eligible=ok,
            ineligible_reasons=reasons,
            eligible_job_ids=job_ids,
            eligible_job_titles=job_titles,
            is_registered=(reg is not None and reg.status == DriveRegistrationStatus.REGISTERED),
            registration_status=reg.status if reg else None,
            application_count=len(s_apps),
            tpo_screening_statuses=screenings,
            latest_application_status=latest_st,
            final_outcome=final_out,
        )
        if ok:
            eligible.append(item)
        else:
            ineligible.append(item)

    return DriveCandidatesResponse(
        drive_id=drive.id,
        eligible_candidates=eligible,
        ineligible_audit_records=ineligible,
    )


def _map_activity_to_response(
    act: PlacementDriveActivity,
    attendance_rows: Optional[List[PlacementDriveAttendance]] = None,
) -> DriveActivityResponse:
    att = attendance_rows if attendance_rows is not None else (getattr(act, "attendance_records", None) or [])
    p_cnt = sum(1 for r in att if r.attendance_status.value == "present")
    a_cnt = sum(1 for r in att if r.attendance_status.value == "absent")
    l_cnt = sum(1 for r in att if r.attendance_status.value == "late")
    e_cnt = sum(1 for r in att if r.attendance_status.value == "excused")
    return DriveActivityResponse(
        id=act.id,
        drive_id=act.drive_id,
        job_id=act.job_id,
        job_title=act.job.title if getattr(act, "job", None) else None,
        company_id=act.company_id,
        company_name=act.company.name if getattr(act, "company", None) else None,
        coordinator_user_id=act.coordinator_user_id,
        coordinator_name=act.coordinator_name,
        coordinator_contact=act.coordinator_contact,
        title=act.title,
        activity_type=act.activity_type,
        mode=act.mode,
        venue=act.venue,
        meeting_link=act.meeting_link,
        scheduled_start=act.scheduled_start,
        scheduled_end=act.scheduled_end,
        description=act.description,
        status=act.status,
        present_count=p_cnt,
        absent_count=a_cnt,
        late_count=l_cnt,
        excused_count=e_cnt,
        created_at=act.created_at or datetime.now(timezone.utc),
    )


async def list_drive_activities(
    session: AsyncSession,
    current_user: User,
    drive_id: int,
) -> List[DriveActivityResponse]:
    drive = await _load_drive_scoped(session, drive_id, current_user, allow_student=True, allow_recruiter=True)
    acts = list(
        (
            await session.execute(
                select(PlacementDriveActivity)
                .options(
                    selectinload(PlacementDriveActivity.company),
                    selectinload(PlacementDriveActivity.job),
                    selectinload(PlacementDriveActivity.attendance_records),
                )
                .where(PlacementDriveActivity.drive_id == drive.id)
                .order_by(PlacementDriveActivity.scheduled_start.asc())
            )
        )
        .scalars()
        .all()
    )
    if current_user.role == UserRole.RECRUITER:
        cid = current_user.recruiter_profile.company_id if current_user.recruiter_profile else None
        acts = [a for a in acts if a.company_id in (None, cid)]
    return [_map_activity_to_response(a) for a in acts]


async def create_drive_activity(
    session: AsyncSession,
    current_user: User,
    drive_id: int,
    payload: DriveActivityCreate,
) -> DriveActivityResponse:
    if current_user.role not in (UserRole.TPO, UserRole.ADMIN):
        raise AuthorizationException("Only authorized TPO or Admin staff can schedule drive activities.")
    drive = await _load_drive_scoped(session, drive_id, current_user)

    start_dt = payload.scheduled_start
    end_dt = payload.scheduled_end
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)
    if start_dt >= end_dt:
        raise AppException("Activity start time must be strictly earlier than end time.", code="INVALID_TIME_WINDOW")

    if payload.coordinator_user_id is not None:
        coord = (
            await session.execute(select(User).where(User.id == payload.coordinator_user_id))
        ).scalar_one_or_none()
        if not coord:
            raise EntityNotFoundException("User", payload.coordinator_user_id)
        if coord.institution_id != drive.institution_id:
            raise AuthorizationException("Assigned coordinator must belong to the same institution.")

    act = PlacementDriveActivity(
        drive_id=drive.id,
        job_id=payload.job_id,
        company_id=payload.company_id,
        created_by_user_id=current_user.id,
        coordinator_user_id=payload.coordinator_user_id,
        coordinator_name=payload.coordinator_name.strip(),
        coordinator_contact=payload.coordinator_contact.strip() if payload.coordinator_contact else None,
        title=payload.title.strip(),
        activity_type=payload.activity_type,
        mode=payload.mode,
        venue=payload.venue.strip() if payload.venue else None,
        meeting_link=payload.meeting_link.strip() if payload.meeting_link else None,
        scheduled_start=start_dt,
        scheduled_end=end_dt,
        description=payload.description.strip() if payload.description else None,
        status=DriveActivityStatus.SCHEDULED,
    )
    session.add(act)
    await session.flush()

    loaded = (
        await session.execute(
            select(PlacementDriveActivity)
            .options(
                selectinload(PlacementDriveActivity.company),
                selectinload(PlacementDriveActivity.job),
                selectinload(PlacementDriveActivity.attendance_records),
            )
            .where(PlacementDriveActivity.id == act.id)
        )
    ).scalar_one()
    return _map_activity_to_response(loaded)


async def update_drive_activity(
    session: AsyncSession,
    current_user: User,
    drive_id: int,
    activity_id: int,
    payload: DriveActivityUpdate,
) -> DriveActivityResponse:
    if current_user.role not in (UserRole.TPO, UserRole.ADMIN):
        raise AuthorizationException("Only authorized TPO or Admin staff can modify drive activities.")
    drive = await _load_drive_scoped(session, drive_id, current_user)
    act = (
        await session.execute(
            select(PlacementDriveActivity)
            .options(
                selectinload(PlacementDriveActivity.company),
                selectinload(PlacementDriveActivity.job),
                selectinload(PlacementDriveActivity.attendance_records),
            )
            .where(
                PlacementDriveActivity.id == activity_id,
                PlacementDriveActivity.drive_id == drive.id,
            )
        )
    ).scalar_one_or_none()
    if not act:
        raise EntityNotFoundException("PlacementDriveActivity", activity_id)

    upd = payload.model_dump(exclude_unset=True)
    next_start = upd.get("scheduled_start", act.scheduled_start)
    next_end = upd.get("scheduled_end", act.scheduled_end)
    if next_start >= next_end:
        raise AppException("Activity start time must be strictly earlier than end time.", code="INVALID_TIME_WINDOW")

    for k, v in upd.items():
        setattr(act, k, v)
    await session.flush()
    await session.refresh(act, attribute_names=["updated_at"])
    return _map_activity_to_response(act)


def _ensure_attendance_authority(user: User, drive: PlacementDrive, activity: PlacementDriveActivity) -> None:
    if user.role == UserRole.ADMIN:
        return
    if user.role == UserRole.TPO and user.institution_id == drive.institution_id:
        return
    if (
        activity.coordinator_user_id is not None
        and activity.coordinator_user_id == user.id
        and user.institution_id == drive.institution_id
    ):
        return
    raise AuthorizationException(
        "Attendance management is restricted to authorized institutional TPOs or the assigned activity coordinator."
    )


async def record_activity_attendance(
    session: AsyncSession,
    current_user: User,
    drive_id: int,
    activity_id: int,
    payload: DriveAttendanceBatchRequest,
) -> List[DriveAttendanceRecordResponse]:
    drive = (
        await session.execute(select(PlacementDrive).where(PlacementDrive.id == drive_id))
    ).scalar_one_or_none()
    if not drive:
        raise EntityNotFoundException("PlacementDrive", drive_id)

    activity = (
        await session.execute(
            select(PlacementDriveActivity).where(
                PlacementDriveActivity.id == activity_id,
                PlacementDriveActivity.drive_id == drive_id,
            )
        )
    ).scalar_one_or_none()
    if not activity:
        raise EntityNotFoundException("PlacementDriveActivity", activity_id)

    _ensure_attendance_authority(current_user, drive, activity)

    now_utc = datetime.now(timezone.utc)
    for item in payload.records:
        row = (
            await session.execute(
                select(StudentProfile, User)
                .join(User, StudentProfile.user_id == User.id)
                .where(StudentProfile.id == item.student_id)
            )
        ).first()
        if not row:
            raise EntityNotFoundException("StudentProfile", item.student_id)
        _sp, stu_usr = row
        if stu_usr.institution_id != drive.institution_id:
            raise AuthorizationException("Cannot record attendance for a student from another institution.")

        existing = (
            await session.execute(
                select(PlacementDriveAttendance)
                .where(
                    PlacementDriveAttendance.activity_id == activity_id,
                    PlacementDriveAttendance.student_id == item.student_id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()

        prev_status: Optional[str] = None
        if existing:
            prev_status = existing.attendance_status.value
            existing.attendance_status = item.attendance_status
            existing.marked_by_user_id = current_user.id
            existing.marked_at = now_utc
            existing.remarks = item.remarks
            att_obj = existing
        else:
            att_obj = PlacementDriveAttendance(
                activity_id=activity_id,
                drive_id=drive_id,
                student_id=item.student_id,
                attendance_status=item.attendance_status,
                marked_by_user_id=current_user.id,
                marked_at=now_utc,
                remarks=item.remarks,
            )
            session.add(att_obj)
            await session.flush()

        audit_row = PlacementDriveAttendanceAudit(
            attendance_id=att_obj.id,
            activity_id=activity_id,
            drive_id=drive_id,
            student_id=item.student_id,
            changed_by_user_id=current_user.id,
            previous_status=prev_status,
            new_status=item.attendance_status.value,
            remarks=item.remarks,
            changed_at=now_utc,
        )
        session.add(audit_row)

    await session.flush()
    return await list_activity_attendance(session, current_user, drive_id, activity_id)


async def list_activity_attendance(
    session: AsyncSession,
    current_user: User,
    drive_id: int,
    activity_id: int,
) -> List[DriveAttendanceRecordResponse]:
    drive = (await session.execute(select(PlacementDrive).where(PlacementDrive.id == drive_id))).scalar_one_or_none()
    if not drive:
        raise EntityNotFoundException("PlacementDrive", drive_id)
    activity = (
        await session.execute(
            select(PlacementDriveActivity).where(
                PlacementDriveActivity.id == activity_id,
                PlacementDriveActivity.drive_id == drive_id,
            )
        )
    ).scalar_one_or_none()
    if not activity:
        raise EntityNotFoundException("PlacementDriveActivity", activity_id)
    _ensure_attendance_authority(current_user, drive, activity)

    rows = (
        await session.execute(
            select(PlacementDriveAttendance, StudentProfile, User)
            .join(StudentProfile, PlacementDriveAttendance.student_id == StudentProfile.id)
            .join(User, StudentProfile.user_id == User.id)
            .options(selectinload(User.department))
            .where(PlacementDriveAttendance.activity_id == activity_id)
            .order_by(StudentProfile.roll_number.asc())
        )
    ).all()

    marker_ids = {att.marked_by_user_id for att, _, _ in rows}
    marker_names: Dict[int, str] = {}
    if marker_ids:
        m_rows = (
            await session.execute(select(User.id, User.full_name).where(User.id.in_(marker_ids)))
        ).all()
        marker_names = {uid: uname for uid, uname in m_rows}

    return [
        DriveAttendanceRecordResponse(
            id=att.id,
            activity_id=att.activity_id,
            drive_id=att.drive_id,
            student_id=sp.id,
            student_name=usr.full_name,
            roll_number=sp.roll_number,
            department_code=usr.department.code if usr.department else None,
            attendance_status=att.attendance_status,
            marked_by_user_id=att.marked_by_user_id,
            marked_by_name=marker_names.get(att.marked_by_user_id, f"User #{att.marked_by_user_id}"),
            marked_at=att.marked_at,
            remarks=att.remarks,
        )
        for att, sp, usr in rows
    ]


async def list_activity_attendance_audit(
    session: AsyncSession,
    current_user: User,
    drive_id: int,
    activity_id: int,
) -> List[DriveAttendanceAuditResponse]:
    drive = (await session.execute(select(PlacementDrive).where(PlacementDrive.id == drive_id))).scalar_one_or_none()
    if not drive:
        raise EntityNotFoundException("PlacementDrive", drive_id)
    activity = (
        await session.execute(
            select(PlacementDriveActivity).where(
                PlacementDriveActivity.id == activity_id,
                PlacementDriveActivity.drive_id == drive_id,
            )
        )
    ).scalar_one_or_none()
    if not activity:
        raise EntityNotFoundException("PlacementDriveActivity", activity_id)
    _ensure_attendance_authority(current_user, drive, activity)

    rows = (
        await session.execute(
            select(PlacementDriveAttendanceAudit, StudentProfile, User)
            .join(StudentProfile, PlacementDriveAttendanceAudit.student_id == StudentProfile.id)
            .join(User, StudentProfile.user_id == User.id)
            .where(PlacementDriveAttendanceAudit.activity_id == activity_id)
            .order_by(PlacementDriveAttendanceAudit.changed_at.desc(), PlacementDriveAttendanceAudit.id.desc())
        )
    ).all()

    changer_ids = {au.changed_by_user_id for au, _, _ in rows}
    changer_names: Dict[int, str] = {}
    if changer_ids:
        c_rows = (
            await session.execute(select(User.id, User.full_name).where(User.id.in_(changer_ids)))
        ).all()
        changer_names = {uid: uname for uid, uname in c_rows}

    return [
        DriveAttendanceAuditResponse(
            id=au.id,
            attendance_id=au.attendance_id,
            activity_id=au.activity_id,
            student_id=sp.id,
            student_name=stu_usr.full_name,
            roll_number=sp.roll_number,
            changed_by_user_id=au.changed_by_user_id,
            changed_by_name=changer_names.get(au.changed_by_user_id, f"User #{au.changed_by_user_id}"),
            previous_status=au.previous_status,
            new_status=au.new_status,
            remarks=au.remarks,
            changed_at=au.changed_at,
        )
        for au, sp, stu_usr in rows
    ]


async def send_drive_announcement(
    session: AsyncSession,
    current_user: User,
    drive_id: int,
    payload: DriveAnnouncementCreate,
) -> DriveAnnouncementResponse:
    if current_user.role not in (UserRole.TPO, UserRole.ADMIN):
        raise AuthorizationException("Only authorized TPO or Admin staff can send drive announcements.")
    drive = await _load_drive_scoped(session, drive_id, current_user)

    recipient_user_ids: Set[int] = set()
    if payload.target_audience == "all_registered":
        reg_uids = (
            await session.execute(
                select(StudentProfile.user_id)
                .join(PlacementDriveRegistration, PlacementDriveRegistration.student_id == StudentProfile.id)
                .where(
                    PlacementDriveRegistration.drive_id == drive.id,
                    PlacementDriveRegistration.status == DriveRegistrationStatus.REGISTERED,
                )
            )
        ).scalars().all()
        app_uids = (
            await session.execute(
                select(StudentProfile.user_id)
                .join(JobApplication, JobApplication.student_id == StudentProfile.id)
                .where(
                    JobApplication.drive_id == drive.id,
                    JobApplication.current_status != ApplicationStatus.WITHDRAWN,
                )
            )
        ).scalars().all()
        recipient_user_ids = set(reg_uids) | set(app_uids)
    elif payload.target_audience == "eligible_students":
        cohort = await _load_institution_cohort(session, drive.institution_id)
        for sp, usr in cohort:
            ok, *_ = _evaluate_drive_eligibility_for_student(drive, sp, usr)
            if ok:
                recipient_user_ids.add(usr.id)
    elif payload.target_audience == "shortlisted_candidates":
        s_uids = (
            await session.execute(
                select(StudentProfile.user_id)
                .join(JobApplication, JobApplication.student_id == StudentProfile.id)
                .where(
                    JobApplication.drive_id == drive.id,
                    (JobApplication.tpo_screening_status == TpoScreeningStatus.SHORTLISTED)
                    | (
                        JobApplication.current_status.in_(
                            [
                                ApplicationStatus.SHORTLISTED,
                                ApplicationStatus.INTERVIEW_SCHEDULED,
                                ApplicationStatus.INTERVIEWED,
                                ApplicationStatus.OFFERED,
                            ]
                        )
                    ),
                )
            )
        ).scalars().all()
        recipient_user_ids = set(s_uids)
    elif payload.target_audience == "specific_job_applicants":
        stmt = (
            select(StudentProfile.user_id)
            .join(JobApplication, JobApplication.student_id == StudentProfile.id)
            .where(
                JobApplication.drive_id == drive.id,
                JobApplication.current_status != ApplicationStatus.WITHDRAWN,
            )
        )
        if payload.job_id is not None:
            stmt = stmt.where(JobApplication.job_id == payload.job_id)
        recipient_user_ids = set((await session.execute(stmt)).scalars().all())

    ann = PlacementDriveAnnouncement(
        drive_id=drive.id,
        sender_user_id=current_user.id,
        job_id=payload.job_id,
        title=payload.title.strip(),
        message=payload.message.strip(),
        target_audience=payload.target_audience,
        recipients_count=0,
    )
    session.add(ann)
    await session.flush()

    delivered = 0
    if recipient_user_ids:
        prefs_rows = (
            await session.execute(
                select(NotificationPreference).where(NotificationPreference.user_id.in_(recipient_user_ids))
            )
        ).scalars().all()
        opt_out_ids = {p.user_id for p in prefs_rows if not p.placement_announcements}
        for uid in sorted(recipient_user_ids):
            if uid in opt_out_ids:
                continue
            await create_notification(
                session=session,
                recipient_user_id=uid,
                sender_user_id=current_user.id,
                category=NotificationCategory.DRIVE_ANNOUNCEMENT,
                title=f"[{drive.name}] {ann.title}",
                message=ann.message,
                related_drive_id=drive.id,
                idempotency_key=f"drive_ann:{ann.id}:u:{uid}",
            )
            delivered += 1

    ann.recipients_count = delivered
    await session.flush()
    return DriveAnnouncementResponse(
        id=ann.id,
        drive_id=ann.drive_id,
        sender_user_id=ann.sender_user_id,
        sender_name=current_user.full_name,
        job_id=ann.job_id,
        title=ann.title,
        message=ann.message,
        target_audience=ann.target_audience,
        recipients_count=ann.recipients_count,
        created_at=ann.created_at or datetime.now(timezone.utc),
    )


async def list_drive_announcements(
    session: AsyncSession,
    current_user: User,
    drive_id: int,
) -> List[DriveAnnouncementResponse]:
    drive = await _load_drive_scoped(session, drive_id, current_user, allow_student=True)
    rows = (
        await session.execute(
            select(PlacementDriveAnnouncement, User)
            .join(User, PlacementDriveAnnouncement.sender_user_id == User.id)
            .where(PlacementDriveAnnouncement.drive_id == drive.id)
            .order_by(PlacementDriveAnnouncement.created_at.desc(), PlacementDriveAnnouncement.id.desc())
        )
    ).all()
    return [
        DriveAnnouncementResponse(
            id=ann.id,
            drive_id=ann.drive_id,
            sender_user_id=ann.sender_user_id,
            sender_name=usr.full_name,
            job_id=ann.job_id,
            title=ann.title,
            message=ann.message,
            target_audience=ann.target_audience,
            recipients_count=ann.recipients_count,
            created_at=ann.created_at or datetime.now(timezone.utc),
        )
        for ann, usr in rows
    ]


async def build_drive_report(
    session: AsyncSession,
    current_user: User,
    drive_id: int,
) -> DriveReportResponse:
    drive = await _load_drive_scoped(session, drive_id, current_user)
    dashboard = await get_drive_dashboard(session, current_user, drive_id)
    candidates = await get_drive_candidates(session, current_user, drive_id)
    activities = await list_drive_activities(session, current_user, drive_id)

    attendance_summary: List[DriveActivityAttendanceSummary] = []
    for ac in activities:
        total_marked = ac.present_count + ac.absent_count + ac.late_count + ac.excused_count
        attended = ac.present_count + ac.late_count
        rate = round((attended / total_marked) * 100.0, 1) if total_marked > 0 else 0.0
        attendance_summary.append(
            DriveActivityAttendanceSummary(
                activity_id=ac.id,
                title=ac.title,
                activity_type=ac.activity_type.value,
                scheduled_start=ac.scheduled_start,
                status=ac.status.value,
                coordinator_name=ac.coordinator_name,
                total_marked=total_marked,
                present_count=ac.present_count,
                absent_count=ac.absent_count,
                late_count=ac.late_count,
                excused_count=ac.excused_count,
                attendance_rate_pct=rate,
            )
        )

    accepted_rows = (
        await session.execute(
            select(JobApplication, StudentProfile, User, Job)
            .join(StudentProfile, JobApplication.student_id == StudentProfile.id)
            .join(User, StudentProfile.user_id == User.id)
            .join(Job, JobApplication.job_id == Job.id)
            .options(selectinload(Job.company), selectinload(User.department))
            .where(
                JobApplication.drive_id == drive.id,
                JobApplication.current_status == ApplicationStatus.OFFER_ACCEPTED,
            )
        )
    ).all()

    placed_outcomes = [
        {
            "student_id": sp.id,
            "student_name": usr.full_name,
            "roll_number": sp.roll_number,
            "department": usr.department.code if usr.department else "N/A",
            "company_name": job.company.name if job.company else "N/A",
            "job_title": job.title,
            "package_lpa": float(app.offer_package_lpa)
            if app.offer_package_lpa is not None
            else (float(job.ctc_lpa) if job.ctc_lpa is not None else None),
        }
        for app, sp, usr, job in accepted_rows
    ]

    phase = getattr(drive, "lifecycle_phase", None) or derive_phase_from_status(drive.status)
    return DriveReportResponse(
        generated_at=datetime.now(timezone.utc),
        drive={
            "id": drive.id,
            "name": drive.name,
            "academic_year": drive.academic_year,
            "target_graduation_year": drive.target_graduation_year,
            "target_graduation_batches": getattr(drive, "target_graduation_batches", None)
            or [drive.target_graduation_year],
            "drive_mode": drive.drive_mode.value,
            "lifecycle_phase": phase.value,
            "venue_location": getattr(drive, "venue_location", None),
            "registration_start_date": drive.registration_start_date.isoformat(),
            "registration_end_date": drive.registration_end_date.isoformat(),
        },
        dashboard=dashboard,
        attendance_summary=attendance_summary,
        registrations_sample_count=dashboard.total_registered_students,
        eligible_sample_count=len(candidates.eligible_candidates),
        ineligible_sample_count=len(candidates.ineligible_audit_records),
        placed_outcomes=placed_outcomes,
    )
