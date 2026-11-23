"""FastAPI routes for TASK 05: TPO Placement Intelligence, Skill Demand & Forecasting."""
import io
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import require_institutional_staff
from app.models.user import User
from app.schemas.tpo_intelligence import TpoPlacementIntelligenceResponse
from app.services.placement_analytics_service import compute_tpo_placement_intelligence
from app.services.placement_report_exporter import (
    generate_intelligence_excel,
    generate_intelligence_pdf,
)

router = APIRouter(
    prefix="/tpo/intelligence",
    tags=["TPO Placement Intelligence & Forecasting"],
)


async def _load_intelligence_report(
    academic_year: Optional[str],
    graduation_year: Optional[int],
    department_id: Optional[int],
    company_id: Optional[int],
    job_category: Optional[str],
    employment_type: Optional[str],
    institution_id: Optional[int],
    refresh: bool,
    current_user: User,
    db: AsyncSession,
) -> TpoPlacementIntelligenceResponse:
    return await compute_tpo_placement_intelligence(
        current_user=current_user,
        db=db,
        academic_year=academic_year,
        graduation_year=graduation_year,
        department_id=department_id,
        company_id=company_id,
        job_category=job_category,
        employment_type=employment_type,
        institution_id=institution_id,
        bypass_cache=refresh,
    )


@router.get("", response_model=TpoPlacementIntelligenceResponse)
@router.get("/dashboard", response_model=TpoPlacementIntelligenceResponse)
async def get_tpo_intelligence_dashboard(
    academic_year: Annotated[Optional[str], Query(description="Filter by academic year e.g. 2025-2026")] = None,
    graduation_year: Annotated[Optional[int], Query(description="Filter by graduation batch year e.g. 2026")] = None,
    department_id: Annotated[Optional[int], Query(description="Filter by department ID")] = None,
    company_id: Annotated[Optional[int], Query(description="Filter by company ID")] = None,
    job_category: Annotated[Optional[str], Query(description="Filter by derived job category")] = None,
    employment_type: Annotated[Optional[str], Query(description="Filter by employment type")] = None,
    institution_id: Annotated[Optional[int], Query(description="Admin override for target institution")] = None,
    refresh: Annotated[bool, Query(description="Bypass analytics micro-cache")] = False,
    current_user: User = Depends(require_institutional_staff),
    db: AsyncSession = Depends(get_async_session),
) -> TpoPlacementIntelligenceResponse:
    """Return full TPO placement overview, department analytics, historical trends, forecasts, and skill intelligence."""
    return await _load_intelligence_report(
        academic_year=academic_year,
        graduation_year=graduation_year,
        department_id=department_id,
        company_id=company_id,
        job_category=job_category,
        employment_type=employment_type,
        institution_id=institution_id,
        refresh=refresh,
        current_user=current_user,
        db=db,
    )


@router.get("/export/pdf")
async def export_tpo_intelligence_pdf(
    academic_year: Annotated[Optional[str], Query()] = None,
    graduation_year: Annotated[Optional[int], Query()] = None,
    department_id: Annotated[Optional[int], Query()] = None,
    company_id: Annotated[Optional[int], Query()] = None,
    job_category: Annotated[Optional[str], Query()] = None,
    employment_type: Annotated[Optional[str], Query()] = None,
    institution_id: Annotated[Optional[int], Query()] = None,
    refresh: Annotated[bool, Query()] = False,
    current_user: User = Depends(require_institutional_staff),
    db: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    """Export filtered placement intelligence & statistical forecasts as a formatted PDF report."""
    report = await _load_intelligence_report(
        academic_year=academic_year,
        graduation_year=graduation_year,
        department_id=department_id,
        company_id=company_id,
        job_category=job_category,
        employment_type=employment_type,
        institution_id=institution_id,
        refresh=refresh,
        current_user=current_user,
        db=db,
    )
    pdf_bytes = generate_intelligence_pdf(report)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="placement_intelligence_report.pdf"'
        },
    )


@router.get("/export/excel")
async def export_tpo_intelligence_excel(
    academic_year: Annotated[Optional[str], Query()] = None,
    graduation_year: Annotated[Optional[int], Query()] = None,
    department_id: Annotated[Optional[int], Query()] = None,
    company_id: Annotated[Optional[int], Query()] = None,
    job_category: Annotated[Optional[str], Query()] = None,
    employment_type: Annotated[Optional[str], Query()] = None,
    institution_id: Annotated[Optional[int], Query()] = None,
    refresh: Annotated[bool, Query()] = False,
    current_user: User = Depends(require_institutional_staff),
    db: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    """Export filtered placement intelligence & statistical forecasts as a multi-sheet .xlsx workbook."""
    report = await _load_intelligence_report(
        academic_year=academic_year,
        graduation_year=graduation_year,
        department_id=department_id,
        company_id=company_id,
        job_category=job_category,
        employment_type=employment_type,
        institution_id=institution_id,
        refresh=refresh,
        current_user=current_user,
        db=db,
    )
    xlsx_bytes = generate_intelligence_excel(report)
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="placement_intelligence_report.xlsx"'
        },
    )
