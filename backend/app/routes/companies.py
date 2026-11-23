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
)
from app.models.company import Company, RecruiterProfile
from app.models.job import Job, JobStatus
from app.models.organization import Institution
from app.models.user import User, UserRole
from app.schemas.company import (
    CompanyAffiliateRequest,
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate,
    CompanyVerifyRequest,
    RecruiterProfileResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies", tags=["Company Management"])


@router.get("", response_model=List[CompanyResponse])
async def list_companies(
    search: Optional[str] = Query(None, description="Search by company name, industry, or location"),
    industry: Optional[str] = Query(None, description="Filter by industry sector"),
    verified_only: Optional[bool] = Query(None, description="Filter by verification status (Admin/TPO only)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    List registered corporate hiring partners.
    - Students: Strictly restricted to active, verified corporate partners.
    - Recruiters: See all verified companies plus their own linked organization.
    - TPOs: See verified partners plus unverified companies affiliated with their own institution.
    - Admins: Platform-wide visibility with optional verification filtering.
    """
    stmt = (
        select(Company)
        .where(Company.is_active == True)
        .options(selectinload(Company.jobs), selectinload(Company.institution))
    )

    # 1. Role-based verification scoping
    if current_user.role == UserRole.STUDENT:
        # Students NEVER see unverified companies as corporate partners
        stmt = stmt.where(Company.is_verified == True)
    elif current_user.role == UserRole.RECRUITER:
        # Recruiter sees verified companies + their own company (even if unverified)
        prof_res = await db.execute(select(RecruiterProfile.company_id).where(RecruiterProfile.user_id == current_user.id))
        recruiter_comp_id = prof_res.scalar_one_or_none()
        if recruiter_comp_id:
            stmt = stmt.where((Company.is_verified == True) | (Company.id == recruiter_comp_id))
        else:
            stmt = stmt.where(Company.is_verified == True)
    elif current_user.role == UserRole.TPO:
        # TPO sees verified companies + unverified companies of their own institution
        tpo_inst_id = current_user.institution_id
        if verified_only is True:
            stmt = stmt.where(Company.is_verified == True)
        elif verified_only is False:
            # Unverified audit view: strictly scoped to TPO's institution
            stmt = stmt.where(Company.is_verified == False, Company.institution_id == tpo_inst_id)
        else:
            stmt = stmt.where(
                (Company.is_verified == True) | (Company.institution_id == tpo_inst_id)
            )
    else:
        # Platform Admin: can filter explicitly by verified_only if requested
        if verified_only is not None:
            stmt = stmt.where(Company.is_verified == verified_only)

    if search:
        search_filter = f"%{search.strip()}%"
        stmt = stmt.where(
            (Company.name.ilike(search_filter))
            | (Company.industry.ilike(search_filter))
            | (Company.location.ilike(search_filter))
        )

    if industry:
        stmt = stmt.where(Company.industry.ilike(f"%{industry.strip()}%"))

    stmt = stmt.order_by(Company.name.asc())
    result = await db.execute(stmt)
    companies = result.scalars().all()

    response: List[CompanyResponse] = []
    for c in companies:
        active_count = sum(1 for j in c.jobs if j.status == JobStatus.PUBLISHED and getattr(j, "is_active", True))
        c_res = CompanyResponse.model_validate(c)
        c_res.active_jobs_count = active_count
        c_res.institution_name = c.institution.name if getattr(c, "institution", None) else None
        response.append(c_res)

    return response


@router.get("/me", response_model=RecruiterProfileResponse)
async def get_my_company_profile(
    current_user: User = Depends(require_recruiter),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Retrieve the authenticated recruiter's associated company profile and designation.
    """
    stmt = (
        select(RecruiterProfile)
        .where(RecruiterProfile.user_id == current_user.id)
        .options(
            selectinload(RecruiterProfile.company).selectinload(Company.jobs)
        )
    )
    result = await db.execute(stmt)
    recruiter_prof = result.scalar_one_or_none()

    if not recruiter_prof:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RECRUITER_COMPANY_NOT_LINKED",
                "message": "You are not currently associated with a registered company. Create or join a company first.",
            },
        )

    company_res = CompanyResponse.model_validate(recruiter_prof.company)
    company_res.active_jobs_count = sum(1 for j in recruiter_prof.company.jobs if j.status == JobStatus.PUBLISHED)

    return RecruiterProfileResponse(
        id=recruiter_prof.id,
        user_id=recruiter_prof.user_id,
        company_id=recruiter_prof.company_id,
        designation=recruiter_prof.designation,
        corporate_phone=recruiter_prof.corporate_phone,
        company=company_res,
        created_at=recruiter_prof.created_at,
        updated_at=recruiter_prof.updated_at,
    )


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company_details(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Fetch comprehensive details for a specific hiring partner organization.
    """
    stmt = (
        select(Company)
        .where(Company.id == company_id)
        .options(selectinload(Company.jobs), selectinload(Company.institution))
    )
    result = await db.execute(stmt)
    company = result.scalar_one_or_none()

    if not company or not getattr(company, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "COMPANY_NOT_FOUND", "message": f"Company with ID {company_id} does not exist."},
        )

    # Students cannot view unverified companies
    if current_user.role == UserRole.STUDENT and not company.is_verified:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "COMPANY_NOT_FOUND", "message": f"Company with ID {company_id} does not exist."},
        )

    # TPO can only view unverified companies affiliated with their own institution
    if current_user.role == UserRole.TPO and not company.is_verified:
        if company.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "CROSS_INSTITUTION_ACCESS_DENIED", "message": "You cannot view unverified companies belonging to another institution."},
            )

    active_count = sum(1 for j in company.jobs if j.status == JobStatus.PUBLISHED and getattr(j, "is_active", True))
    res = CompanyResponse.model_validate(company)
    res.active_jobs_count = active_count
    res.institution_name = company.institution.name if getattr(company, "institution", None) else None
    return res


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CompanyCreate,
    current_user: User = Depends(require_roles(UserRole.RECRUITER, UserRole.TPO, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Register a new corporate hiring partner.
    - Recruiter: Created companies are ALWAYS unverified initially. Recruiter is automatically linked.
    - TPO: Registers a company partner for institutional placement drives (scoped to TPO's institution).
    - Admin: Platform administrative registration (may create verified partner).
    """
    # Check duplicate name
    existing = await db.execute(select(Company).where(func.lower(Company.name) == payload.name.strip().lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "COMPANY_NAME_TAKEN", "message": f"Company '{payload.name}' is already registered."},
        )

    # If recruiter: check if already linked to a company
    if current_user.role == UserRole.RECRUITER:
        prof_res = await db.execute(select(RecruiterProfile).where(RecruiterProfile.user_id == current_user.id))
        if prof_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "ALREADY_ASSOCIATED_WITH_COMPANY",
                    "message": "You are already linked to a company. Each recruiter may manage only their own company.",
                },
            )

    # Scoping resolution
    target_institution_id: Optional[int] = None
    if current_user.role == UserRole.TPO:
        target_institution_id = current_user.institution_id
    elif current_user.role == UserRole.ADMIN:
        target_institution_id = payload.institution_id
    # Recruiter-created companies are platform/unaffiliated (institution_id = None)

    # Recruiter-created companies MUST remain unverified initially
    is_initially_verified = (current_user.role == UserRole.ADMIN)

    company = Company(
        institution_id=target_institution_id,
        name=payload.name.strip(),
        industry=payload.industry.strip(),
        description=payload.description.strip() if payload.description else None,
        website=payload.website.strip() if payload.website else None,
        location=payload.location.strip() if payload.location else None,
        company_size=payload.company_size,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        is_verified=is_initially_verified,
        is_active=True,
    )
    db.add(company)
    await db.flush()

    # Link recruiter if created by recruiter
    if current_user.role == UserRole.RECRUITER:
        recruiter_profile = RecruiterProfile(
            user_id=current_user.id,
            company_id=company.id,
            designation="Talent Acquisition Lead",
            corporate_phone=current_user.phone,
        )
        db.add(recruiter_profile)

    await db.commit()
    await db.refresh(company)

    res = CompanyResponse.model_validate(company)
    res.active_jobs_count = 0
    return res


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    payload: CompanyUpdate,
    current_user: User = Depends(require_roles(UserRole.RECRUITER, UserRole.TPO, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Update company information.
    - Recruiter: Strictly restricted to their OWN company (HTTP 403 otherwise).
    - TPO & Admin: Governed by institutional/platform permissions.
    """
    stmt = (
        select(Company)
        .where(Company.id == company_id)
        .options(selectinload(Company.jobs), selectinload(Company.institution))
    )
    result = await db.execute(stmt)
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "COMPANY_NOT_FOUND", "message": f"Company with ID {company_id} does not exist."},
        )

    # Recruiter Isolation Boundary Check
    if current_user.role == UserRole.RECRUITER:
        prof_res = await db.execute(select(RecruiterProfile).where(RecruiterProfile.user_id == current_user.id))
        recruiter_profile = prof_res.scalar_one_or_none()
        if not recruiter_profile or recruiter_profile.company_id != company.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "CROSS_COMPANY_ACCESS_DENIED",
                    "message": "You are only authorized to manage your own corporate company profile.",
                },
            )

    # TPO Isolation Boundary Check
    if current_user.role == UserRole.TPO:
        if company.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "CROSS_INSTITUTION_ACCESS_DENIED",
                    "message": "You are only authorized to manage corporate partner profiles affiliated with your institution.",
                },
            )

    update_dict = payload.model_dump(exclude_unset=True)

    # Only Admin can toggle is_verified
    if "is_verified" in update_dict and current_user.role != UserRole.ADMIN:
        update_dict.pop("is_verified")

    # Name uniqueness check if name is modified
    if "name" in update_dict and update_dict["name"]:
        new_name = update_dict["name"].strip()
        existing = await db.execute(
            select(Company).where(func.lower(Company.name) == new_name.lower(), Company.id != company.id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "COMPANY_NAME_TAKEN", "message": f"Company '{new_name}' is already taken."},
            )
        company.name = new_name

    for field, val in update_dict.items():
        if field != "name":
            setattr(company, field, val)

    await db.commit()
    await db.refresh(company)

    active_count = sum(1 for j in company.jobs if j.status == JobStatus.PUBLISHED and getattr(j, "is_active", True))
    res = CompanyResponse.model_validate(company)
    res.active_jobs_count = active_count
    res.institution_name = company.institution.name if getattr(company, "institution", None) else None
    return res


@router.patch("/{company_id}/verify", response_model=CompanyResponse)
async def verify_company(
    company_id: int,
    payload: CompanyVerifyRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TPO)),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Verify or unverify a corporate hiring partner.
    - Restricted to Platform Administrators and Institutional TPOs.
    - Recruiters and Students are strictly blocked (HTTP 403 Forbidden).
    """
    stmt = (
        select(Company)
        .where(Company.id == company_id)
        .options(selectinload(Company.jobs), selectinload(Company.institution))
    )
    result = await db.execute(stmt)
    company = result.scalar_one_or_none()

    if not company or not getattr(company, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "COMPANY_NOT_FOUND", "message": f"Company with ID {company_id} does not exist."},
        )

    # TPO can ONLY verify companies affiliated with their own institution
    if current_user.role == UserRole.TPO:
        if company.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "CROSS_INSTITUTION_ACCESS_DENIED",
                    "message": "TPO is only authorized to verify corporate partners affiliated with their own institution. Platform-wide company verification requires Administrator authority.",
                },
            )

    company.is_verified = payload.is_verified
    await db.commit()
    await db.refresh(company)

    active_count = sum(1 for j in company.jobs if j.status == JobStatus.PUBLISHED and getattr(j, "is_active", True))
    res = CompanyResponse.model_validate(company)
    res.active_jobs_count = active_count
    res.institution_name = company.institution.name if getattr(company, "institution", None) else None
    return res


@router.patch("/{company_id}/affiliate", response_model=CompanyResponse)
async def affiliate_company(
    company_id: int,
    payload: CompanyAffiliateRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TPO)),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Associate an existing company with a collegiate institution for campus recruitment.
    - Admin: Can associate any company with any valid institution, or disaffiliate with null.
    - TPO: Can associate an unaffiliated company (institution_id IS NULL) with their own institution.
           TPO cannot associate with other institutions or reassign an already-affiliated company.
    - Recruiters & Students: Blocked with HTTP 403 Forbidden.
    - Recruiter ownership (RecruiterProfile) is fully preserved.
    """
    stmt = (
        select(Company)
        .where(Company.id == company_id)
        .options(selectinload(Company.jobs), selectinload(Company.institution))
    )
    result = await db.execute(stmt)
    company = result.scalar_one_or_none()

    if not company or not getattr(company, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "COMPANY_NOT_FOUND", "message": f"Company with ID {company_id} does not exist."},
        )

    target_institution_id: Optional[int] = None

    if current_user.role == UserRole.TPO:
        # TPOs are strictly bound to their own institution
        if payload.institution_id is not None and payload.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "CROSS_INSTITUTION_ACCESS_DENIED",
                    "message": "TPOs are strictly prohibited from associating companies with other institutions.",
                },
            )
        # If the company is already affiliated with another institution, TPO cannot reassign it
        if company.institution_id is not None and company.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "CROSS_INSTITUTION_ACCESS_DENIED",
                    "message": "Company is already affiliated with a different collegiate institution.",
                },
            )
        target_institution_id = current_user.institution_id
    else:
        # Platform Admin can associate to any institution or disaffiliate
        target_institution_id = payload.institution_id

    # Verify target institution exists and is active if not None
    if target_institution_id is not None:
        inst_res = await db.execute(select(Institution).where(Institution.id == target_institution_id))
        institution = inst_res.scalar_one_or_none()
        if not institution or not getattr(institution, "is_active", True):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "INSTITUTION_NOT_FOUND",
                    "message": f"Institution with ID {target_institution_id} does not exist or is inactive.",
                },
            )

    company.institution_id = target_institution_id
    await db.commit()
    await db.refresh(company)

    # Ensure institution relation is reloaded for response if institution_id is set
    if company.institution_id:
        inst_res = await db.execute(select(Institution).where(Institution.id == company.institution_id))
        company.institution = inst_res.scalar_one_or_none()

    active_count = sum(1 for j in company.jobs if j.status == JobStatus.PUBLISHED and getattr(j, "is_active", True))
    res = CompanyResponse.model_validate(company)
    res.active_jobs_count = active_count
    res.institution_name = company.institution.name if getattr(company, "institution", None) else None
    return res

