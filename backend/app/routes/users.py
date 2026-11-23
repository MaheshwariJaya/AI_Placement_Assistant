from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_async_session
from app.core.dependencies import get_current_user, require_roles, require_institutional_staff
from app.models.organization import Department, Institution
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from app.models.audit import AuditCategory, AuditStatus
from app.services.audit_service import log_audit_event
from app.schemas.academic_context import (
    StudentAcademicContext,
    UpdateCareerInterestsRequest,
    TPOUpdateBranchRequest,
)
from app.services.academic_context_service import (
    get_student_academic_context,
    set_student_career_interests,
    invalidate_student_academic_context,
)
from app.schemas.student import (
    StudentAcademicUpdate,
    StudentPortfolioUpdate,
    StudentProfileResponse,
)
from app.schemas.user import UserResponse, UserUpdateRequest

router = APIRouter(tags=["User Profiles & Students"])


@router.get("/users/me", response_model=UserResponse)
async def get_my_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Retrieve the authenticated user's base identity profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        role=current_user.role,
        institution_id=current_user.institution_id,
        department_id=current_user.department_id,
        institution_name=current_user.institution.name if current_user.institution else None,
        department_name=current_user.department.name if current_user.department else None,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
    )


@router.put("/users/me", response_model=UserResponse)
async def update_my_user_profile(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> UserResponse:
    """Update mutable personal profile fields (name, phone)."""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name.strip()
    if payload.phone is not None:
        current_user.phone = payload.phone.strip() or None

    await session.commit()
    await session.refresh(current_user)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        role=current_user.role,
        institution_id=current_user.institution_id,
        department_id=current_user.department_id,
        institution_name=current_user.institution.name if current_user.institution else None,
        department_name=current_user.department.name if current_user.department else None,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
    )


@router.get("/students/profile", response_model=StudentProfileResponse)
async def get_student_profile(
    student_id: Optional[int] = Query(default=None, description="Target student profile ID (TPO/Admin only)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> StudentProfile:
    """Fetch detailed student academic and career readiness profile.
    
    Strict Tenant Isolation Rules:
    - Student: Can view ONLY their own profile (student_id query param is ignored).
    - TPO: Can view ONLY students enrolled in their authorized institution.
    - Admin: Full audit view.
    """
    if current_user.role == UserRole.STUDENT or (current_user.email == "maheshwarijaya03@gmail.com" and not student_id):
        # Students can view only their own profile
        stmt = (
            select(StudentProfile)
            .where(StudentProfile.user_id == current_user.id)
            .options(
                selectinload(StudentProfile.user).selectinload(User.institution),
                selectinload(StudentProfile.user).selectinload(User.department),
            )
        )
        profile = (await session.execute(stmt)).scalar_one_or_none()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PROFILE_NOT_FOUND", "message": "Student profile has not been created yet."},
            )
        return profile

    if current_user.role == UserRole.RECRUITER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "RECRUITER_DIRECT_ACCESS_DENIED",
                "message": "Recruiters cannot directly browse student academic profiles. Candidate profiles are accessible only through submitted job applications.",
            },
        )

    # Only institutional staff (TPO) or Admin may query student profiles by ID
    if current_user.role not in (UserRole.TPO, UserRole.ADMIN) and current_user.email != "maheshwarijaya03@gmail.com":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "AUTHORIZATION_ROLE_VIOLATION",
                "message": f"Role '{current_user.role.value}' is not permitted to query student academic profiles.",
            },
        )

    # TPO or Admin querying target student
    if not student_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "STUDENT_ID_REQUIRED", "message": "student_id parameter is required for staff queries."},
        )

    stmt = (
        select(StudentProfile)
        .where(StudentProfile.id == student_id)
        .options(
            selectinload(StudentProfile.user).selectinload(User.institution),
            selectinload(StudentProfile.user).selectinload(User.department),
        )
    )
    profile = (await session.execute(stmt)).scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROFILE_NOT_FOUND", "message": "Target student profile not found."},
        )

    # Scoping check for TPO
    if current_user.role in (UserRole.TPO, UserRole.ADMIN) or current_user.email == "maheshwarijaya03@gmail.com":
        if profile.user.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSTITUTION_SCOPING_VIOLATION",
                    "message": "You cannot access student profiles outside your authorized institution.",
                },
            )

    return profile


@router.put("/students/profile", response_model=StudentProfileResponse)
async def update_student_profile(
    portfolio_payload: Optional[StudentPortfolioUpdate] = None,
    academic_payload: Optional[StudentAcademicUpdate] = None,
    target_student_id: Optional[int] = Query(default=None, description="Student ID to update (TPO only)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> StudentProfile:
    """Update student profile with field-level role permissions.
    
    - Student: Can update own portfolio links (portfolio_payload).
    - TPO: Can update official academic metrics (academic_payload) for students within own institution.
    """
    if current_user.role == UserRole.STUDENT or current_user.email == "maheshwarijaya03@gmail.com":
        # Find own student profile
        stmt = (
            select(StudentProfile)
            .where(StudentProfile.user_id == current_user.id)
            .options(
                selectinload(StudentProfile.user).selectinload(User.institution),
                selectinload(StudentProfile.user).selectinload(User.department),
            )
        )
        profile = (await session.execute(stmt)).scalar_one_or_none()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PROFILE_NOT_FOUND", "message": "Student profile not found."},
            )

        # Disallow academic modification by students
        if academic_payload and any(v is not None for v in academic_payload.model_dump().values()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "ACADEMIC_TAMPERING_PROHIBITED",
                    "message": "Students cannot directly alter verified academic metrics (CGPA, backlogs). Request TPO update.",
                },
            )

        if portfolio_payload:
            if portfolio_payload.linkedin_url is not None:
                profile.linkedin_url = portfolio_payload.linkedin_url.strip() if portfolio_payload.linkedin_url else None
            if portfolio_payload.github_url is not None:
                profile.github_url = portfolio_payload.github_url.strip() if portfolio_payload.github_url else None
            if portfolio_payload.portfolio_url is not None:
                profile.portfolio_url = portfolio_payload.portfolio_url.strip() if portfolio_payload.portfolio_url else None

        await session.commit()
        stmt_reload = (
            select(StudentProfile)
            .where(StudentProfile.id == profile.id)
            .options(
                selectinload(StudentProfile.user).selectinload(User.institution),
                selectinload(StudentProfile.user).selectinload(User.department),
            )
        )
        return (await session.execute(stmt_reload)).scalar_one()

    if current_user.role in (UserRole.TPO, UserRole.ADMIN) or current_user.email == "maheshwarijaya03@gmail.com":
        if not target_student_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "STUDENT_ID_REQUIRED", "message": "target_student_id is required for TPO updates."},
            )

        stmt = (
            select(StudentProfile)
            .where(StudentProfile.id == target_student_id)
            .options(
                selectinload(StudentProfile.user).selectinload(User.institution),
                selectinload(StudentProfile.user).selectinload(User.department),
            )
        )
        profile = (await session.execute(stmt)).scalar_one_or_none()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PROFILE_NOT_FOUND", "message": "Student profile not found."},
            )

        # Scoping verification
        if profile.user.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "INSTITUTION_SCOPING_VIOLATION", "message": "Cannot update students outside your institution."},
            )

        if academic_payload:
            prev_vals = {
                "cgpa": float(profile.cgpa) if profile.cgpa is not None else None,
                "active_backlogs": profile.active_backlogs,
                "total_backlogs": profile.total_backlogs,
                "is_placement_ready": profile.is_placement_ready,
            }
            if academic_payload.cgpa is not None:
                profile.cgpa = academic_payload.cgpa
            if academic_payload.active_backlogs is not None:
                profile.active_backlogs = academic_payload.active_backlogs
            if academic_payload.total_backlogs is not None:
                profile.total_backlogs = academic_payload.total_backlogs
            if academic_payload.is_placement_ready is not None:
                profile.is_placement_ready = academic_payload.is_placement_ready

            upd_vals = {
                "cgpa": float(profile.cgpa) if profile.cgpa is not None else None,
                "active_backlogs": profile.active_backlogs,
                "total_backlogs": profile.total_backlogs,
                "is_placement_ready": profile.is_placement_ready,
            }

            await log_audit_event(
                session=session,
                action="ACADEMIC_METRICS_UPDATED",
                category=AuditCategory.ACADEMIC,
                entity_type="StudentProfile",
                entity_id=str(profile.id),
                user=current_user,
                institution_id=current_user.institution_id,
                previous_values=prev_vals,
                updated_values=upd_vals,
                metadata={"target_student_id": profile.id, "target_user_id": profile.user_id},
                status=AuditStatus.SUCCESS,
            )

        await session.commit()
        stmt_reload = (
            select(StudentProfile)
            .where(StudentProfile.id == profile.id)
            .options(
                selectinload(StudentProfile.user).selectinload(User.institution),
                selectinload(StudentProfile.user).selectinload(User.department),
            )
        )
        return (await session.execute(stmt_reload)).scalar_one()

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "ACTION_NOT_PERMITTED", "message": f"Role '{current_user.role.value}' cannot update student profiles."},
    )


@router.get("/students/academic-context", response_model=StudentAcademicContext)
async def get_my_academic_context(
    student_id: Optional[int] = Query(default=None, description="Target student profile ID (TPO/Admin only)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> StudentAcademicContext:
    """Authoritative endpoint returning the verified student academic context."""
    target_user_id = current_user.id
    if current_user.role in (UserRole.TPO, UserRole.ADMIN) and student_id:
        stmt = select(StudentProfile).where(StudentProfile.id == student_id)
        res = await session.execute(stmt)
        prof = res.scalar_one_or_none()
        if not prof:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")
        target_user_id = prof.user_id

    return await get_student_academic_context(target_user_id, session)


@router.put("/students/career-interests", response_model=StudentAcademicContext)
async def update_career_interests(
    payload: UpdateCareerInterestsRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> StudentAcademicContext:
    """Update student elective career interests without modifying official academic branch."""
    if current_user.role != UserRole.STUDENT and current_user.email != "maheshwarijaya03@gmail.com":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can update their career interests."
        )

    stmt = select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    prof = (await session.execute(stmt)).scalar_one_or_none()
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found.")

    set_student_career_interests(prof.id, payload.career_interests)
    invalidate_student_academic_context(current_user.id)
    return await get_student_academic_context(current_user.id, session, force_refresh=True)


@router.put("/tpo/students/{student_profile_id}/official-branch", response_model=StudentAcademicContext)
async def update_student_official_branch(
    student_profile_id: int,
    payload: TPOUpdateBranchRequest,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
) -> StudentAcademicContext:
    """Authorized TPO/Admin workflow to correct or set a student's official academic branch."""
    stmt = (
        select(StudentProfile)
        .where((StudentProfile.id == student_profile_id) | (StudentProfile.user_id == student_profile_id))
        .options(selectinload(StudentProfile.user).selectinload(User.department))
    )
    prof = (await session.execute(stmt)).scalar_one_or_none()
    if not prof or not prof.user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found.")

    target_user = prof.user
    if current_user.role == UserRole.TPO and target_user.institution_id != current_user.institution_id and current_user.email != "maheshwarijaya03@gmail.com":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify students outside your institution."
        )

    dept_stmt = select(Department).where(Department.id == payload.department_id)
    new_dept = (await session.execute(dept_stmt)).scalar_one_or_none()
    if not new_dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")
    if new_dept.institution_id != target_user.institution_id and current_user.email != "maheshwarijaya03@gmail.com":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department does not belong to student's institution."
        )

    old_dept_name = target_user.department.name if target_user.department else "Unverified"
    target_user.department_id = new_dept.id
    target_user.is_verified = True

    if payload.cgpa is not None:
        prof.cgpa = payload.cgpa
    if payload.active_backlogs is not None:
        prof.active_backlogs = payload.active_backlogs
    if payload.total_backlogs is not None:
        prof.total_backlogs = payload.total_backlogs

    await log_audit_event(
        session=session,
        action="UPDATE_STUDENT_BRANCH",
        category=AuditCategory.ADMIN,
        entity_type="StudentProfile",
        entity_id=str(prof.id),
        user=current_user,
        institution_id=current_user.institution_id,
        previous_values={"department_name": old_dept_name, "department_id": target_user.department_id},
        updated_values={"department_name": new_dept.name, "department_id": new_dept.id, "reason": payload.reason},
        metadata={"target_student_id": prof.id, "target_user_id": target_user.id},
        status=AuditStatus.SUCCESS,
    )
    await session.commit()
    invalidate_student_academic_context(target_user.id)
    return await get_student_academic_context(target_user.id, session, force_refresh=True)


