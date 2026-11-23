from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import get_current_user, require_admin, require_roles
from app.models.organization import Department, Institution
from app.models.user import User, UserRole
from app.schemas.organization import (
    DepartmentCreate,
    DepartmentResponse,
    InstitutionCreate,
    InstitutionResponse,
)

router = APIRouter(prefix="/institutions", tags=["Organizations & Departments"])


@router.get("", response_model=List[InstitutionResponse])
async def list_institutions(
    session: AsyncSession = Depends(get_async_session),
) -> List[Institution]:
    """Retrieve all active academic institutions."""
    stmt = select(Institution).where(Institution.is_active.is_(True)).order_by(Institution.name)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=InstitutionResponse, status_code=status.HTTP_201_CREATED)
async def create_institution(
    payload: InstitutionCreate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session),
) -> Institution:
    """Create a new academic institution (Administrator permission required)."""
    code_clean = payload.code.upper().strip()
    existing_stmt = select(Institution).where(Institution.code == code_clean)
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "INSTITUTION_EXISTS", "message": f"Institution code '{code_clean}' already exists."},
        )

    inst = Institution(
        name=payload.name.strip(),
        code=code_clean,
        city=payload.city.strip(),
        is_active=True,
    )
    session.add(inst)
    await session.commit()
    await session.refresh(inst)
    return inst


@router.get("/{institution_id}/departments", response_model=List[DepartmentResponse])
async def list_institution_departments(
    institution_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> List[Department]:
    """List all active departments for an institution."""
    inst = await session.get(Institution, institution_id)
    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INSTITUTION_NOT_FOUND", "message": "Institution not found."},
        )

    stmt = (
        select(Department)
        .where(Department.institution_id == institution_id, Department.is_active.is_(True))
        .order_by(Department.name)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("/{institution_id}/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    institution_id: int,
    payload: DepartmentCreate,
    current_user: User = Depends(require_roles(UserRole.TPO, UserRole.ADMIN)),
    session: AsyncSession = Depends(get_async_session),
) -> Department:
    """Add an academic department to an institution (TPO or Admin).
    
    TPO users are strictly bounded to their authorized institution.
    """
    if current_user.role == UserRole.TPO and current_user.institution_id != institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "INSTITUTION_SCOPING_VIOLATION",
                "message": "TPOs can manage departments only within their authorized institution.",
            },
        )

    inst = await session.get(Institution, institution_id)
    if not inst or not inst.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INSTITUTION_NOT_FOUND", "message": "Target institution not found or inactive."},
        )

    code_clean = payload.code.upper().strip()
    existing_stmt = select(Department).where(
        Department.institution_id == institution_id,
        Department.code == code_clean,
    )
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "DEPARTMENT_EXISTS", "message": f"Department with code '{code_clean}' already exists in this institution."},
        )

    dept = Department(
        institution_id=institution_id,
        name=payload.name.strip(),
        code=code_clean,
        is_active=True,
    )
    session.add(dept)
    await session.commit()
    await session.refresh(dept)
    return dept

