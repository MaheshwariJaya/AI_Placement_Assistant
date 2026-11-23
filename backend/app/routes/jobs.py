from datetime import datetime, timezone
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_async_session
from app.core.dependencies import (
    get_current_user,
    require_recruiter,
    require_roles,
    require_student,
)
from app.models.company import Company, RecruiterProfile
from app.models.job import (
    EmploymentType,
    Job,
    JobEligibleDepartment,
    JobSkill,
    JobStatus,
    WorkMode,
)
from app.models.organization import Department
from app.models.student import StudentProfile, StudentSkill
from app.models.user import User, UserRole
from app.schemas.company import CompanyResponse
from app.schemas.job import (
    JobCreate,
    JobDepartmentResponse,
    JobDetailResponse,
    JobEligibilityResult,
    JobResponse,
    JobSkillResponse,
    JobStatusUpdate,
    JobUpdate,
)
from app.services.eligibility_service import evaluate_student_job_eligibility

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Job Management"])


def _map_job_to_response(job: Job) -> JobResponse:
    """Helper to convert Job ORM instance into JobResponse summary."""
    skill_names = [s.skill_name for s in (job.skills or [])]
    dept_names = [
        ed.department.name for ed in (job.eligible_departments or []) if ed.department
    ]
    return JobResponse(
        id=job.id,
        company_id=job.company_id,
        company_name=job.company.name if job.company else "Unknown Partner",
        company_industry=job.company.industry if job.company else None,
        created_by_user_id=job.created_by_user_id,
        institution_id=job.institution_id,
        institution_name=job.institution.name if getattr(job, "institution", None) else None,
        is_active=getattr(job, "is_active", True) if getattr(job, "is_active", None) is not None else True,
        title=job.title,
        employment_type=job.employment_type,
        work_mode=job.work_mode,
        location=job.location,
        salary_range=job.salary_range,
        ctc_lpa=float(job.ctc_lpa) if job.ctc_lpa is not None else None,
        min_cgpa=float(job.min_cgpa) if job.min_cgpa is not None else 0.0,
        target_graduation_year=job.target_graduation_year,
        max_active_backlogs=job.max_active_backlogs,
        max_total_backlogs=job.max_total_backlogs,
        application_deadline=job.application_deadline,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        skills=skill_names,
        eligible_department_names=dept_names,
    )


def _map_job_to_detail(job: Job) -> JobDetailResponse:
    """Helper to convert Job ORM instance into full JobDetailResponse."""
    summary = _map_job_to_response(job)
    company_res = CompanyResponse.model_validate(job.company)

    skills_res = [
        JobSkillResponse(
            id=s.id,
            job_id=s.job_id,
            skill_name=s.skill_name,
            is_mandatory=s.is_mandatory,
            weight_factor=float(s.weight_factor),
        )
        for s in (job.skills or [])
    ]

    dept_res = [
        JobDepartmentResponse(
            id=ed.id,
            department_id=ed.department_id,
            department_name=ed.department.name if ed.department else None,
            department_code=ed.department.code if ed.department else None,
        )
        for ed in (job.eligible_departments or [])
    ]

    return JobDetailResponse(
        **summary.model_dump(),
        description=job.description,
        company=company_res,
        base_salary_lpa=float(job.base_salary_lpa) if job.base_salary_lpa is not None else None,
        stipend_monthly=float(job.stipend_monthly) if job.stipend_monthly is not None else None,
        all_skills=skills_res,
        eligible_departments=dept_res,
    )


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    status_filter: Optional[JobStatus] = Query(None, alias="status", description="Filter by lifecycle status"),
    search: Optional[str] = Query(None, description="Search by title, location, or company name"),
    employment_type: Optional[EmploymentType] = Query(None, description="Filter by full_time, internship, etc."),
    work_mode: Optional[WorkMode] = Query(None, description="Filter by on_site, hybrid, remote"),
    department_id: Optional[int] = Query(None, description="Filter by department eligibility"),
    my_company_only: bool = Query(False, description="For recruiters: filter to own company postings"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    List campus placement job opportunities with RBAC filtering.
    - Students: Strictly restricted to 'published' jobs.
    - Recruiters: See their company's jobs (including drafts). Can toggle to explore platform-wide published jobs.
    - TPOs & Admins: Comprehensive access with institutional scoping.
    """
    stmt = (
        select(Job)
        .where(Job.is_active == True)
        .options(
            selectinload(Job.company),
            selectinload(Job.institution),
            selectinload(Job.skills),
            selectinload(Job.eligible_departments).selectinload(JobEligibleDepartment.department),
        )
    )

    # 1. Role-based scoping and visibility
    if current_user.role == UserRole.STUDENT:
        # Students: strictly published jobs, scoped to their institution or open drives
        stmt = stmt.where(Job.status == JobStatus.PUBLISHED)
        if current_user.institution_id:
            stmt = stmt.where(
                (Job.institution_id.is_(None)) | (Job.institution_id == current_user.institution_id)
            )
    elif current_user.role == UserRole.RECRUITER:
        # Recruiters: manage own company jobs (any status), browse published jobs
        prof_res = await db.execute(select(RecruiterProfile).where(RecruiterProfile.user_id == current_user.id))
        recruiter_profile = prof_res.scalar_one_or_none()
        recruiter_company_id = recruiter_profile.company_id if recruiter_profile else None

        if my_company_only or status_filter in (JobStatus.DRAFT, JobStatus.CLOSED, JobStatus.CANCELLED):
            if recruiter_company_id:
                stmt = stmt.where(Job.company_id == recruiter_company_id)
            else:
                return []
        elif not my_company_only and recruiter_company_id:
            stmt = stmt.where(
                (Job.company_id == recruiter_company_id) | (Job.status == JobStatus.PUBLISHED)
            )

        if status_filter:
            stmt = stmt.where(Job.status == status_filter)
    elif current_user.role == UserRole.TPO:
        # TPO Institutional Isolation: strictly scoped to TPO's institution
        tpo_inst_id = current_user.institution_id
        if tpo_inst_id:
            # Jobs scoped to TPO's institution, or jobs open to departments in TPO's institution, or open published jobs
            dept_ids_subq = select(Department.id).where(Department.institution_id == tpo_inst_id)
            tpo_dept_jobs_subq = select(JobEligibleDepartment.job_id).where(JobEligibleDepartment.department_id.in_(dept_ids_subq))
            
            stmt = stmt.where(
                (Job.institution_id == tpo_inst_id)
                | (Job.id.in_(tpo_dept_jobs_subq))
                | ((Job.institution_id.is_(None)) & (Job.status == JobStatus.PUBLISHED))
            )
        if status_filter:
            stmt = stmt.where(Job.status == status_filter)
    else:
        # Platform Admin: global platform-wide visibility
        if status_filter:
            stmt = stmt.where(Job.status == status_filter)

    # 2. Search query filter
    if search:
        search_term = f"%{search.strip()}%"
        stmt = stmt.join(Job.company).where(
            (Job.title.ilike(search_term))
            | (Job.location.ilike(search_term))
            | (Company.name.ilike(search_term))
        )

    # 3. Employment type & Work mode
    if employment_type:
        stmt = stmt.where(Job.employment_type == employment_type)
    if work_mode:
        stmt = stmt.where(Job.work_mode == work_mode)

    # 4. Department filter
    if department_id:
        stmt = stmt.where(
            Job.id.in_(
                select(JobEligibleDepartment.job_id).where(JobEligibleDepartment.department_id == department_id)
            )
        )

    stmt = stmt.order_by(Job.created_at.desc())
    result = await db.execute(stmt)
    jobs = result.scalars().all()

    return [_map_job_to_response(j) for j in jobs]


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job_details(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Fetch comprehensive job requirements, cutoffs, company profile, and eligible branches.
    - Recruiter can view draft/closed jobs only for their own company.
    - Students can only view published jobs.
    """
    stmt = (
        select(Job)
        .where(Job.id == job_id, Job.is_active == True)
        .options(
            selectinload(Job.company),
            selectinload(Job.institution),
            selectinload(Job.skills),
            selectinload(Job.eligible_departments).selectinload(JobEligibleDepartment.department),
        )
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job posting with ID {job_id} does not exist."},
        )

    # RBAC Visibility checks
    if current_user.role == UserRole.STUDENT:
        if job.status != JobStatus.PUBLISHED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "UNPUBLISHED_JOB_ACCESS_DENIED", "message": "Students may only view published opportunities."},
            )
        if job.institution_id is not None and current_user.institution_id and job.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "CROSS_INSTITUTION_ACCESS_DENIED", "message": "This placement drive is exclusive to candidates of another institution."},
            )

    if current_user.role == UserRole.RECRUITER and job.status != JobStatus.PUBLISHED:
        prof_res = await db.execute(select(RecruiterProfile.company_id).where(RecruiterProfile.user_id == current_user.id))
        recruiter_comp_id = prof_res.scalar_one_or_none()
        if not recruiter_comp_id or recruiter_comp_id != job.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "CROSS_COMPANY_ACCESS_DENIED",
                    "message": "You cannot view unreleased job drafts belonging to another corporate organization.",
                },
            )

    if current_user.role == UserRole.TPO and job.status != JobStatus.PUBLISHED:
        if job.institution_id is not None and job.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "CROSS_INSTITUTION_ACCESS_DENIED",
                    "message": "You cannot access private placement information belonging to another institution.",
                },
            )

    return _map_job_to_detail(job)


@router.post("", response_model=JobDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    current_user: User = Depends(require_roles(UserRole.RECRUITER, UserRole.ADMIN, UserRole.TPO)),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Create a new campus placement job posting with strict academic cutoffs and skill requirements.
    - Recruiter: Bound strictly to their associated corporate company.
    - TPO: Posts on behalf of partner companies for on-campus drives.
    """
    # 1. Resolve Company ID
    target_company_id: int
    if current_user.role == UserRole.RECRUITER:
        prof_res = await db.execute(select(RecruiterProfile).where(RecruiterProfile.user_id == current_user.id))
        recruiter_profile = prof_res.scalar_one_or_none()
        if not recruiter_profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "RECRUITER_COMPANY_REQUIRED",
                    "message": "You must register or link your company profile before publishing job opportunities.",
                },
            )
        target_company_id = recruiter_profile.company_id
    elif current_user.role == UserRole.TPO:
        # TPO: must link job to an affiliated, verified partner company for their own institution
        comp_id = payload.company_id
        if not comp_id:
            # Fallback to single affiliated verified company if exists, else require company_id
            comp_stmt = select(Company).where(
                Company.institution_id == current_user.institution_id,
                Company.is_verified == True,
                Company.is_active == True,
            )
            comp_res = await db.execute(comp_stmt)
            partner_company = comp_res.scalars().first()
            if not partner_company:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "PARTNER_COMPANY_REQUIRED",
                        "message": "A valid, verified corporate partner company affiliated with your institution is required to create a campus-exclusive placement drive.",
                    },
                )
            target_company_id = partner_company.id
        else:
            comp_stmt = select(Company).where(Company.id == comp_id, Company.is_active == True)
            comp_res = await db.execute(comp_stmt)
            partner_company = comp_res.scalar_one_or_none()
            if not partner_company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "COMPANY_NOT_FOUND", "message": f"Company with ID {comp_id} does not exist."},
                )
            if partner_company.institution_id != current_user.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "CROSS_INSTITUTION_ACCESS_DENIED",
                        "message": "TPOs can only create campus placement drives for corporate partners affiliated with their own institution.",
                    },
                )
            if not partner_company.is_verified:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "COMPANY_NOT_VERIFIED",
                        "message": "Partner company must be verified before creating campus-exclusive placement drives.",
                    },
                )
            target_company_id = partner_company.id
    else:
        # Admin: platform-wide creation
        if payload.company_id:
            comp_stmt = select(Company.id).where(Company.id == payload.company_id, Company.is_active == True)
            comp_res = await db.execute(comp_stmt)
            if not comp_res.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "COMPANY_NOT_FOUND", "message": f"Company with ID {payload.company_id} does not exist."},
                )
            target_company_id = payload.company_id
        else:
            first_comp = await db.execute(select(Company.id).where(Company.is_active == True).limit(1))
            found_id = first_comp.scalar_one_or_none()
            if not found_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": "NO_COMPANIES_EXIST", "message": "Please register at least one company partner first."},
                )
            target_company_id = found_id

    # 2. Deadline validation
    now_utc = datetime.now(timezone.utc)
    deadline = payload.application_deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if deadline <= now_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_DEADLINE", "message": "Application deadline must be a future date and time."},
        )

    # 3. Create Job - Institutional Scope Enforcement
    target_institution_id: Optional[int] = None
    if current_user.role == UserRole.TPO:
        # TPO-created exclusive jobs are automatically assigned to the authenticated TPO's institution
        if payload.institution_id is not None and payload.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "CROSS_INSTITUTION_ACCESS_DENIED",
                    "message": "TPOs can only author job opportunities for their own institution.",
                },
            )
        target_institution_id = current_user.institution_id
    elif current_user.role == UserRole.RECRUITER:
        # Recruiters cannot assign jobs to arbitrary institutions directly
        if payload.institution_id is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "RECRUITER_INSTITUTION_RESTRICTED",
                    "message": "Recruiters cannot assign jobs to specific institutions directly. Institutional drives must be coordinated through the institutional TPO or Admin.",
                },
            )
        target_institution_id = None
    elif current_user.role == UserRole.ADMIN:
        # Admin retains platform-wide assignment authority
        target_institution_id = payload.institution_id

    # 4. Department-Institution Consistency Validation
    if target_institution_id is not None and payload.eligible_department_ids:
        dept_stmt = select(Department.id).where(
            Department.id.in_(payload.eligible_department_ids),
            Department.institution_id != target_institution_id,
        )
        mismatched_res = await db.execute(dept_stmt)
        mismatched_ids = mismatched_res.scalars().all()
        if mismatched_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "DEPARTMENT_INSTITUTION_MISMATCH",
                    "message": f"Departments {list(mismatched_ids)} do not belong to target institution {target_institution_id}. Exclusive campus drives cannot include departments of other institutions.",
                },
            )

    job = Job(
        company_id=target_company_id,
        created_by_user_id=current_user.id,
        institution_id=target_institution_id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        employment_type=payload.employment_type,
        work_mode=payload.work_mode,
        location=payload.location.strip(),
        salary_range=payload.salary_range.strip() if payload.salary_range else None,
        ctc_lpa=payload.ctc_lpa,
        base_salary_lpa=payload.base_salary_lpa,
        stipend_monthly=payload.stipend_monthly,
        min_cgpa=payload.min_cgpa,
        target_graduation_year=payload.target_graduation_year,
        max_active_backlogs=payload.max_active_backlogs,
        max_total_backlogs=payload.max_total_backlogs,
        application_deadline=deadline,
        status=payload.status,
        is_active=True,
    )
    db.add(job)
    await db.flush()

    # 4. Attach Mandatory & Preferred Skills
    seen_skills = set()
    for s_name in payload.required_skills:
        clean = s_name.strip()
        if clean and clean.lower() not in seen_skills:
            seen_skills.add(clean.lower())
            db.add(JobSkill(job_id=job.id, skill_name=clean, is_mandatory=True, weight_factor=1.5))

    for s_name in payload.preferred_skills:
        clean = s_name.strip()
        if clean and clean.lower() not in seen_skills:
            seen_skills.add(clean.lower())
            db.add(JobSkill(job_id=job.id, skill_name=clean, is_mandatory=False, weight_factor=1.0))

    # 5. Attach Eligible Departments
    for dept_id in payload.eligible_department_ids:
        db.add(JobEligibleDepartment(job_id=job.id, department_id=dept_id))

    await db.commit()

    # Re-fetch with all eager loads
    refreshed_stmt = (
        select(Job)
        .where(Job.id == job.id)
        .options(
            selectinload(Job.company),
            selectinload(Job.institution),
            selectinload(Job.skills),
            selectinload(Job.eligible_departments).selectinload(JobEligibleDepartment.department),
        )
    )
    refreshed_job = (await db.execute(refreshed_stmt)).scalar_one()
    return _map_job_to_detail(refreshed_job)


@router.put("/{job_id}", response_model=JobDetailResponse)
async def update_job(
    job_id: int,
    payload: JobUpdate,
    current_user: User = Depends(require_roles(UserRole.RECRUITER, UserRole.TPO, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Update job posting attributes, cutoffs, skills, or department eligibility.
    - Recruiters are strictly confined to jobs authored by their own company.
    - TPOs are strictly confined to jobs scoped to their own institution.
    """
    stmt = (
        select(Job)
        .where(Job.id == job_id, Job.is_active == True)
        .options(
            selectinload(Job.company),
            selectinload(Job.institution),
            selectinload(Job.skills),
            selectinload(Job.eligible_departments).selectinload(JobEligibleDepartment.department),
        )
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job with ID {job_id} does not exist."},
        )

    # Recruiter Isolation Check
    if current_user.role == UserRole.RECRUITER:
        prof_res = await db.execute(select(RecruiterProfile).where(RecruiterProfile.user_id == current_user.id))
        recruiter_profile = prof_res.scalar_one_or_none()
        if not recruiter_profile or recruiter_profile.company_id != job.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "CROSS_COMPANY_ACCESS_DENIED",
                    "message": "You are not authorized to modify job postings belonging to another corporate organization.",
                },
            )

    # TPO Institutional Isolation Check
    if current_user.role == UserRole.TPO:
        if job.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "CROSS_INSTITUTION_ACCESS_DENIED",
                    "message": "You are only authorized to modify campus-exclusive job postings belonging to your own institution.",
                },
            )
        if payload.institution_id is not None and payload.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "CROSS_INSTITUTION_ACCESS_DENIED",
                    "message": "TPOs cannot reassign job opportunities to another institution.",
                },
            )

    # Recruiter Scope Immutability Check
    if current_user.role == UserRole.RECRUITER:
        if payload.institution_id is not None and payload.institution_id != job.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "RECRUITER_INSTITUTION_IMMUTABLE",
                    "message": "Recruiters are not permitted to alter the institutional scope of job postings.",
                },
            )

    # Department-Institution Consistency Validation
    effective_inst_id = (
        payload.institution_id
        if (payload.institution_id is not None and current_user.role == UserRole.ADMIN)
        else job.institution_id
    )
    if effective_inst_id is not None and payload.eligible_department_ids:
        dept_stmt = select(Department.id).where(
            Department.id.in_(payload.eligible_department_ids),
            Department.institution_id != effective_inst_id,
        )
        mismatched_res = await db.execute(dept_stmt)
        mismatched_ids = mismatched_res.scalars().all()
        if mismatched_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "DEPARTMENT_INSTITUTION_MISMATCH",
                    "message": f"Departments {list(mismatched_ids)} do not belong to target institution {effective_inst_id}. Exclusive campus drives cannot include departments of other institutions.",
                },
            )

    if current_user.role == UserRole.ADMIN and "institution_id" in payload.model_fields_set:
        job.institution_id = payload.institution_id

    update_data = payload.model_dump(exclude_unset=True)

    # Scalar attributes
    scalar_fields = [
        "title", "description", "employment_type", "work_mode", "location",
        "salary_range", "ctc_lpa", "base_salary_lpa", "stipend_monthly",
        "min_cgpa", "target_graduation_year", "max_active_backlogs",
        "max_total_backlogs", "status"
    ]
    for field in scalar_fields:
        if field in update_data and update_data[field] is not None:
            setattr(job, field, update_data[field])

    if "application_deadline" in update_data and update_data["application_deadline"]:
        dl = update_data["application_deadline"]
        if dl.tzinfo is None:
            dl = dl.replace(tzinfo=timezone.utc)
        job.application_deadline = dl

    # Update Skills if explicitly supplied
    if payload.required_skills is not None or payload.preferred_skills is not None:
        # Delete existing skills
        await db.execute(
            JobSkill.__table__.delete().where(JobSkill.job_id == job.id)
        )
        seen_skills = set()
        req_skills = payload.required_skills if payload.required_skills is not None else [s.skill_name for s in job.skills if s.is_mandatory]
        pref_skills = payload.preferred_skills if payload.preferred_skills is not None else [s.skill_name for s in job.skills if not s.is_mandatory]

        for s_name in req_skills:
            clean = s_name.strip()
            if clean and clean.lower() not in seen_skills:
                seen_skills.add(clean.lower())
                db.add(JobSkill(job_id=job.id, skill_name=clean, is_mandatory=True, weight_factor=1.5))

        for s_name in pref_skills:
            clean = s_name.strip()
            if clean and clean.lower() not in seen_skills:
                seen_skills.add(clean.lower())
                db.add(JobSkill(job_id=job.id, skill_name=clean, is_mandatory=False, weight_factor=1.0))

    # Update Eligible Departments if explicitly supplied
    if payload.eligible_department_ids is not None:
        await db.execute(
            JobEligibleDepartment.__table__.delete().where(JobEligibleDepartment.job_id == job.id)
        )
        for dept_id in payload.eligible_department_ids:
            db.add(JobEligibleDepartment(job_id=job.id, department_id=dept_id))

    await db.commit()

    # Re-fetch updated entity
    refreshed_job = (await db.execute(stmt)).scalar_one()
    return _map_job_to_detail(refreshed_job)


@router.patch("/{job_id}/status", response_model=JobDetailResponse)
async def update_job_status(
    job_id: int,
    payload: JobStatusUpdate,
    current_user: User = Depends(require_roles(UserRole.RECRUITER, UserRole.TPO, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Publish a draft job, close an active posting, or archive a cancellation.
    - Recruiters may manage lifecycle only for their own company's jobs.
    - TPOs may manage lifecycle only for jobs scoped to their own institution.
    """
    stmt = (
        select(Job)
        .where(Job.id == job_id, Job.is_active == True)
        .options(
            selectinload(Job.company),
            selectinload(Job.institution),
            selectinload(Job.skills),
            selectinload(Job.eligible_departments).selectinload(JobEligibleDepartment.department),
        )
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job with ID {job_id} does not exist."},
        )

    if current_user.role == UserRole.RECRUITER:
        prof_res = await db.execute(select(RecruiterProfile.company_id).where(RecruiterProfile.user_id == current_user.id))
        recruiter_comp_id = prof_res.scalar_one_or_none()
        if hasattr(recruiter_comp_id, "company_id"):
            recruiter_comp_id = recruiter_comp_id.company_id
        if not recruiter_comp_id or recruiter_comp_id != job.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "CROSS_COMPANY_ACCESS_DENIED", "message": "Cannot modify job status of another organization."},
            )

    if current_user.role == UserRole.TPO:
        if job.institution_id is not None and job.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "CROSS_INSTITUTION_ACCESS_DENIED", "message": "Cannot modify job status of another institution."},
            )

    job.status = payload.status
    await db.commit()
    await db.refresh(job)

    return _map_job_to_detail(job)


@router.get("/{job_id}/check-eligibility", response_model=JobEligibilityResult)
async def check_student_eligibility(
    job_id: int,
    student_id: Optional[int] = Query(None, description="Optional profile ID for TPO/Recruiter evaluation. Defaults to current student."),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Evaluate student academic and skill prerequisites against a job's
    deterministic cutoff criteria.
    - Students can evaluate only themselves.
    - TPOs and Recruiters can inspect eligibility for candidate profiles.
    - TPO is strictly bound to candidates of their own institution.
    """
    # 1. Fetch Job with cutoffs, skills, and eligible departments
    job_stmt = (
        select(Job)
        .where(Job.id == job_id, Job.is_active == True)
        .options(
            selectinload(Job.company),
            selectinload(Job.institution),
            selectinload(Job.skills),
            selectinload(Job.eligible_departments).selectinload(JobEligibleDepartment.department),
        )
    )
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id} not found."},
        )

    # 2. Resolve target student profile
    target_profile: StudentProfile
    target_user: User

    if current_user.role == UserRole.STUDENT:
        if not current_user.student_profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "STUDENT_PROFILE_REQUIRED", "message": "Your student profile is incomplete."},
            )
        target_profile = current_user.student_profile
        target_user = current_user
    else:
        # TPO / Recruiter evaluating a student
        if not student_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "STUDENT_ID_REQUIRED", "message": "Provide ?student_id to evaluate candidate eligibility."},
            )
        prof_stmt = (
            select(StudentProfile)
            .where(StudentProfile.id == student_id)
            .options(selectinload(StudentProfile.user).selectinload(User.department))
        )
        prof_res = await db.execute(prof_stmt)
        found_prof = prof_res.scalar_one_or_none()
        if not found_prof:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "STUDENT_PROFILE_NOT_FOUND", "message": f"Student profile {student_id} not found."},
            )
        target_profile = found_prof
        target_user = found_prof.user

        # TPO Institutional Isolation Boundary
        if current_user.role == UserRole.TPO:
            if target_user.institution_id != current_user.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "CROSS_INSTITUTION_ACCESS_DENIED",
                        "message": "You are only authorized to evaluate candidate profiles belonging to your institution.",
                    },
                )

    # 3. Fetch Student's confirmed skills
    skill_stmt = select(StudentSkill.skill_name).where(StudentSkill.student_id == target_profile.id)
    skills_res = await db.execute(skill_stmt)
    student_skills = [row[0] for row in skills_res.fetchall()]

    # 4. Evaluate using deterministic engine
    return evaluate_student_job_eligibility(
        job=job,
        student_user=target_user,
        student_profile=target_profile,
        student_skill_names=student_skills,
    )

