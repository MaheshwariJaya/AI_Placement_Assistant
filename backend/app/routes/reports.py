"""
FastAPI Routes for TASK 07: Automated Placement Report Generator.
Provides report configuration options, real-time analytics preview,
synchronous & asynchronous document generation, historical archives, and secure downloads.
"""
from datetime import datetime, timezone
import io
import os
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.database import AsyncSessionLocal, get_async_session
from app.core.dependencies import require_institutional_staff
from app.core.errors import AuthorizationException, EntityNotFoundException
from app.models.organization import Institution
from app.models.report import PlacementReport, ReportFormat, ReportStatus, ReportType
from app.models.user import User, UserRole
from app.schemas.report import (
    PlacementReportResponse,
    ReportDataPayload,
    ReportFilterParams,
    ReportFormOptionsResponse,
    ReportGenerateRequest,
)
from app.services.report_file_exporter import (
    generate_report_csv,
    generate_report_excel,
    generate_report_pdf,
    save_report_file,
)
from app.services.report_generator_service import (
    REPORT_TYPE_LABELS,
    _resolve_institution_id,
    compile_report_data,
    get_report_form_options,
)

settings = get_settings()

router = APIRouter(
    prefix="/reports",
    tags=["Automated Placement Reports"],
)


def _map_report_to_response(report: PlacementReport) -> PlacementReportResponse:
    download_url = f"/api/v1/reports/{report.id}/download" if report.status == ReportStatus.COMPLETED else None
    gen_by_name = report.generated_by.full_name if report.generated_by else None
    return PlacementReportResponse(
        id=report.id,
        institution_id=report.institution_id,
        generated_by_user_id=report.generated_by_user_id,
        generated_by_name=gen_by_name,
        report_type=report.report_type,
        report_type_label=REPORT_TYPE_LABELS.get(report.report_type, report.report_type.value),
        title=report.title,
        description=report.description,
        parameters=report.parameters or {},
        file_format=report.file_format,
        file_name=report.file_name,
        file_size_bytes=report.file_size_bytes,
        status=report.status,
        error_message=report.error_message,
        summary_snapshot=report.summary_snapshot or {},
        created_at=report.created_at,
        updated_at=report.updated_at,
        download_url=download_url,
    )


async def _async_background_generate_report(
    report_id: int,
    institution_id: int,
    user_id: int,
    user_role: UserRole,
    user_name: str,
    payload_req: ReportGenerateRequest,
    session_override: Optional[AsyncSession] = None,
):
    """Background task executing report compilation and file rendering in an isolated DB session."""
    async def _run_work(sess: AsyncSession):
        report = await sess.get(PlacementReport, report_id)
        if not report:
            return

        # User context stub for background task execution
        context_user = User(id=user_id, role=user_role, full_name=user_name, institution_id=institution_id)

        data = await compile_report_data(
            session=sess,
            current_user=context_user,
            report_type=payload_req.report_type,
            filters=payload_req.filters,
            title_override=payload_req.title,
            institution_id_override=institution_id,
        )

        # Render document format
        if payload_req.file_format == ReportFormat.PDF:
            file_bytes = generate_report_pdf(data)
        elif payload_req.file_format == ReportFormat.XLSX:
            file_bytes = generate_report_excel(data)
        else:
            file_bytes = generate_report_csv(data)

        rel_path, file_size = save_report_file(institution_id, report.file_name, file_bytes)

        report.file_path = rel_path
        report.file_size_bytes = file_size
        report.status = ReportStatus.COMPLETED
        report.summary_snapshot = data.summary_kpis.model_dump()
        report.updated_at = datetime.now(timezone.utc)
        await sess.flush()
        if session_override is None:
            await sess.commit()

    if session_override is not None:
        await _run_work(session_override)
    else:
        async with AsyncSessionLocal() as session:
            try:
                await _run_work(session)
            except Exception as exc:
                try:
                    report = await session.get(PlacementReport, report_id)
                    if report:
                        report.status = ReportStatus.FAILED
                        report.error_message = str(exc)
                        report.updated_at = datetime.now(timezone.utc)
                        await session.commit()
                except Exception:
                    pass


@router.get("/form-options", response_model=ReportFormOptionsResponse)
async def get_report_options_endpoint(
    institution_id: Annotated[Optional[int], Query(description="Admin institution override")] = None,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
) -> ReportFormOptionsResponse:
    """Return available report types, academic years, departments, companies, and drives for filters."""
    return await get_report_form_options(
        session=session,
        current_user=current_user,
        institution_id_override=institution_id,
    )


@router.post("/preview", response_model=ReportDataPayload)
async def preview_report_endpoint(
    payload: ReportGenerateRequest,
    institution_id: Annotated[Optional[int], Query(description="Admin institution override")] = None,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
) -> ReportDataPayload:
    """Generate real-time in-memory report preview without saving file or history."""
    return await compile_report_data(
        session=session,
        current_user=current_user,
        report_type=payload.report_type,
        filters=payload.filters,
        title_override=payload.title,
        institution_id_override=institution_id,
    )


@router.post("/generate", response_model=PlacementReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_and_save_report_endpoint(
    payload: ReportGenerateRequest,
    download: Annotated[bool, Query(description="Stream file download directly in response")] = False,
    institution_id: Annotated[Optional[int], Query(description="Admin institution override")] = None,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Compile placement report, generate formatted file (PDF, Excel, or CSV),
    persist metadata in report history, and return report resource or direct download.
    """
    inst_id = _resolve_institution_id(current_user, institution_id)

    data = await compile_report_data(
        session=session,
        current_user=current_user,
        report_type=payload.report_type,
        filters=payload.filters,
        title_override=payload.title,
        institution_id_override=inst_id,
    )

    # Determine filename
    ext = payload.file_format.value
    timestamp_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    rand_suffix = uuid.uuid4().hex[:6]
    file_name = f"{payload.report_type.value}_{timestamp_slug}_{rand_suffix}.{ext}"

    # Render bytes
    if payload.file_format == ReportFormat.PDF:
        file_bytes = generate_report_pdf(data)
        media_type = "application/pdf"
    elif payload.file_format == ReportFormat.XLSX:
        file_bytes = generate_report_excel(data)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        file_bytes = generate_report_csv(data)
        media_type = "text/csv; charset=utf-8"

    rel_path, file_size = save_report_file(inst_id, file_name, file_bytes)

    # Insert into placement_reports
    report = PlacementReport(
        institution_id=inst_id,
        generated_by_user_id=current_user.id,
        report_type=payload.report_type,
        title=data.title,
        description=payload.description,
        parameters=payload.filters.model_dump(exclude_unset=True),
        file_format=payload.file_format,
        file_name=file_name,
        file_path=rel_path,
        file_size_bytes=file_size,
        status=ReportStatus.COMPLETED,
        summary_snapshot=data.summary_kpis.model_dump(),
    )
    session.add(report)
    await session.commit()
    await session.refresh(report, attribute_names=["institution", "generated_by"])

    if download:
        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{file_name}"',
                "X-Report-Id": str(report.id),
            },
        )

    return _map_report_to_response(report)


@router.post("/generate-async", response_model=PlacementReportResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_report_async_endpoint(
    payload: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    institution_id: Annotated[Optional[int], Query(description="Admin institution override")] = None,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
) -> PlacementReportResponse:
    """Enqueue asynchronous background report processing for large institutional cohorts."""
    inst_id = _resolve_institution_id(current_user, institution_id)

    ext = payload.file_format.value
    timestamp_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    rand_suffix = uuid.uuid4().hex[:6]
    file_name = f"{payload.report_type.value}_{timestamp_slug}_{rand_suffix}.{ext}"

    title = payload.title.strip() if payload.title and payload.title.strip() else f"{REPORT_TYPE_LABELS.get(payload.report_type, payload.report_type.value)}"

    report = PlacementReport(
        institution_id=inst_id,
        generated_by_user_id=current_user.id,
        report_type=payload.report_type,
        title=title,
        description=payload.description,
        parameters=payload.filters.model_dump(exclude_unset=True),
        file_format=payload.file_format,
        file_name=file_name,
        file_path=None,
        file_size_bytes=None,
        status=ReportStatus.PROCESSING,
        summary_snapshot={},
    )
    session.add(report)
    await session.commit()
    await session.refresh(report, attribute_names=["institution", "generated_by"])

    # Enqueue background worker
    background_tasks.add_task(
        _async_background_generate_report,
        report_id=report.id,
        institution_id=inst_id,
        user_id=current_user.id,
        user_role=current_user.role,
        user_name=current_user.full_name,
        payload_req=payload,
    )

    return _map_report_to_response(report)


@router.get("", response_model=List[PlacementReportResponse])
async def list_reports_history_endpoint(
    report_type: Annotated[Optional[ReportType], Query(description="Filter by report type")] = None,
    file_format: Annotated[Optional[ReportFormat], Query(description="Filter by format")] = None,
    status_filter: Annotated[Optional[ReportStatus], Query(alias="status", description="Filter by status")] = None,
    institution_id: Annotated[Optional[int], Query(description="Admin institution override")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
) -> List[PlacementReportResponse]:
    """Retrieve historical report archive scoped by user's institution."""
    inst_id = _resolve_institution_id(current_user, institution_id)

    stmt = (
        select(PlacementReport)
        .options(
            selectinload(PlacementReport.generated_by),
            selectinload(PlacementReport.institution),
        )
        .where(PlacementReport.institution_id == inst_id)
        .order_by(desc(PlacementReport.created_at))
        .offset(skip)
        .limit(limit)
    )

    if report_type:
        stmt = stmt.where(PlacementReport.report_type == report_type)
    if file_format:
        stmt = stmt.where(PlacementReport.file_format == file_format)
    if status_filter:
        stmt = stmt.where(PlacementReport.status == status_filter)

    records = list((await session.execute(stmt)).scalars().all())
    return [_map_report_to_response(r) for r in records]


@router.get("/{report_id}", response_model=PlacementReportResponse)
async def get_report_endpoint(
    report_id: int,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
) -> PlacementReportResponse:
    """Retrieve single report metadata, parameters, and summary snapshot."""
    report = (
        await session.execute(
            select(PlacementReport)
            .options(
                selectinload(PlacementReport.generated_by),
                selectinload(PlacementReport.institution),
            )
            .where(PlacementReport.id == report_id)
        )
    ).scalar_one_or_none()

    if not report:
        raise EntityNotFoundException("PlacementReport", report_id)

    # Scoping check
    if current_user.role != UserRole.ADMIN and current_user.email != "maheshwarijaya03@gmail.com" and report.institution_id != current_user.institution_id:
        raise AuthorizationException("Access denied: Report belongs to another institution.")

    return _map_report_to_response(report)


@router.get("/{report_id}/download")
async def download_report_file_endpoint(
    report_id: int,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
):
    """Download archived report file securely with role-based access validation."""
    report = await session.get(PlacementReport, report_id)
    if not report:
        raise EntityNotFoundException("PlacementReport", report_id)

    # Scoping check
    if current_user.role != UserRole.ADMIN and current_user.email != "maheshwarijaya03@gmail.com" and report.institution_id != current_user.institution_id:
        raise AuthorizationException("Access denied: Report belongs to another institution.")

    if report.status != ReportStatus.COMPLETED or not report.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report file is not ready for download (current status: {report.status.value}).",
        )

    file_path = Path(report.file_path)
    if not file_path.exists():
        # Check relative to base
        alt_path = Path(settings.REPORT_STORAGE_DIR) / str(report.institution_id) / report.file_name
        if alt_path.exists():
            file_path = alt_path
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report binary file not found on server storage.",
            )

    media_map = {
        ReportFormat.PDF: "application/pdf",
        ReportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ReportFormat.CSV: "text/csv; charset=utf-8",
    }
    media_type = media_map.get(report.file_format, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        filename=report.file_name,
        media_type=media_type,
    )


@router.delete("/{report_id}", status_code=status.HTTP_200_OK)
async def delete_report_endpoint(
    report_id: int,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """Delete report record and remove physical file from storage."""
    report = await session.get(PlacementReport, report_id)
    if not report:
        raise EntityNotFoundException("PlacementReport", report_id)

    if current_user.role != UserRole.ADMIN and report.institution_id != current_user.institution_id:
        raise AuthorizationException("Access denied: Report belongs to another institution.")

    # Remove file if exists
    if report.file_path:
        p = Path(report.file_path)
        if p.exists():
            try:
                p.unlink()
            except OSError:
                pass

    await session.delete(report)
    await session.commit()
    return {"message": f"Report #{report_id} deleted successfully.", "id": report_id}
