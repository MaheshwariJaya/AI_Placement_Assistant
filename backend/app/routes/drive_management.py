"""FastAPI routes for TASK 06: Complete Placement Drive Management Workspace."""
import io
from typing import List

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import get_current_user, require_institutional_staff, require_student
from app.models.user import User
from app.schemas.drive_workspace import (
    DriveActivityCreate,
    DriveActivityResponse,
    DriveActivityUpdate,
    DriveAnnouncementCreate,
    DriveAnnouncementResponse,
    DriveAttendanceAuditResponse,
    DriveAttendanceBatchRequest,
    DriveAttendanceRecordResponse,
    DriveCandidatesResponse,
    DriveDashboardResponse,
    DriveFormOptionsResponse,
    DriveRegisterRequest,
    DriveRegistrationResponse,
    DriveReportResponse,
    DriveTransitionRequest,
)
from app.schemas.placement import PlacementDriveResponse
from app.routes.placement import _map_drive_to_response
from app.services.drive_report_exporter import (
    generate_drive_report_excel,
    generate_drive_report_pdf,
)
from app.services.drive_workspace_service import (
    build_drive_report,
    create_drive_activity,
    get_drive_candidates,
    get_drive_dashboard,
    get_drive_form_options,
    list_activity_attendance,
    list_activity_attendance_audit,
    list_drive_activities,
    list_drive_announcements,
    list_drive_registrations,
    record_activity_attendance,
    register_student_for_drive,
    register_students_batch_for_drive,
    send_drive_announcement,
    transition_drive_lifecycle,
    update_drive_activity,
)

router = APIRouter(prefix="/drives", tags=["Placement Drive Workspace"])


@router.get("/form-options", response_model=DriveFormOptionsResponse)
async def get_drive_form_options_endpoint(
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
) -> DriveFormOptionsResponse:
    """Return institution-scoped companies, jobs, departments, batches, and coordinators."""
    return await get_drive_form_options(session=session, current_user=current_user)


@router.post("/{drive_id}/transition", response_model=PlacementDriveResponse)
async def transition_drive_phase_endpoint(
    drive_id: int,
    payload: DriveTransitionRequest,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
) -> PlacementDriveResponse:
    """Validate and apply a 7-stage placement drive lifecycle transition."""
    drive, total_jobs, total_apps = await transition_drive_lifecycle(
        session=session,
        current_user=current_user,
        drive_id=drive_id,
        target_phase=payload.target_phase,
    )
    return _map_drive_to_response(drive, total_jobs=total_jobs, total_applications=total_apps)


@router.get("/{drive_id}/dashboard", response_model=DriveDashboardResponse)
async def get_drive_dashboard_endpoint(
    drive_id: int,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
) -> DriveDashboardResponse:
    """Return real-time KPIs, funnel breakdown, and allowed lifecycle transitions for a drive."""
    return await get_drive_dashboard(session=session, current_user=current_user, drive_id=drive_id)


@router.post("/{drive_id}/register", response_model=DriveRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def student_register_drive_endpoint(
    drive_id: int,
    payload: DriveRegisterRequest = DriveRegisterRequest(),
    current_user: User = Depends(require_student),
    session: AsyncSession = Depends(get_async_session),
) -> DriveRegistrationResponse:
    """Student self-registration with deterministic eligibility validation and duplicate prevention."""
    return await register_student_for_drive(
        session=session,
        current_user=current_user,
        drive_id=drive_id,
        notes=payload.notes,
    )


@router.post("/{drive_id}/registrations", response_model=List[DriveRegistrationResponse], status_code=status.HTTP_201_CREATED)
async def tpo_register_students_endpoint(
    drive_id: int,
    payload: DriveRegisterRequest,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
) -> List[DriveRegistrationResponse]:
    """Authorized TPO registration of verified eligible students into a drive."""
    return await register_students_batch_for_drive(
        session=session,
        current_user=current_user,
        drive_id=drive_id,
        student_ids=payload.student_ids or [],
        notes=payload.notes,
    )


@router.get("/{drive_id}/registrations", response_model=List[DriveRegistrationResponse])
async def list_drive_registrations_endpoint(
    drive_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> List[DriveRegistrationResponse]:
    """List drive registrations (institution TPO sees all; students see their own registration)."""
    return await list_drive_registrations(session=session, current_user=current_user, drive_id=drive_id)


@router.get("/{drive_id}/candidates", response_model=DriveCandidatesResponse)
async def get_drive_candidates_endpoint(
    drive_id: int,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
) -> DriveCandidatesResponse:
    """Return deterministic eligible candidates, ineligible audit records, screening & final outcomes."""
    return await get_drive_candidates(session=session, current_user=current_user, drive_id=drive_id)


@router.get("/{drive_id}/activities", response_model=List[DriveActivityResponse])
async def list_drive_activities_endpoint(
    drive_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> List[DriveActivityResponse]:
    """List scheduled PPTs, presentations, assessments, interview rounds, and coordinator details."""
    return await list_drive_activities(session=session, current_user=current_user, drive_id=drive_id)


@router.post("/{drive_id}/activities", response_model=DriveActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_drive_activity_endpoint(
    drive_id: int,
    payload: DriveActivityCreate,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
) -> DriveActivityResponse:
    """Schedule a drive activity with venue, time slot, and coordinator assignment."""
    return await create_drive_activity(
        session=session,
        current_user=current_user,
        drive_id=drive_id,
        payload=payload,
    )


@router.patch("/{drive_id}/activities/{activity_id}", response_model=DriveActivityResponse)
async def update_drive_activity_endpoint(
    drive_id: int,
    activity_id: int,
    payload: DriveActivityUpdate,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
) -> DriveActivityResponse:
    """Update schedule slot, venue, coordinator, or status for a drive activity."""
    return await update_drive_activity(
        session=session,
        current_user=current_user,
        drive_id=drive_id,
        activity_id=activity_id,
        payload=payload,
    )


@router.get("/{drive_id}/activities/{activity_id}/attendance", response_model=List[DriveAttendanceRecordResponse])
async def list_activity_attendance_endpoint(
    drive_id: int,
    activity_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> List[DriveAttendanceRecordResponse]:
    """List attendance records for a drive activity (authorized TPO or assigned coordinator only)."""
    return await list_activity_attendance(
        session=session,
        current_user=current_user,
        drive_id=drive_id,
        activity_id=activity_id,
    )


@router.post("/{drive_id}/activities/{activity_id}/attendance", response_model=List[DriveAttendanceRecordResponse])
async def mark_activity_attendance_endpoint(
    drive_id: int,
    activity_id: int,
    payload: DriveAttendanceBatchRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> List[DriveAttendanceRecordResponse]:
    """Record or update attendance with immutable audit logging (authorized TPO or assigned coordinator)."""
    return await record_activity_attendance(
        session=session,
        current_user=current_user,
        drive_id=drive_id,
        activity_id=activity_id,
        payload=payload,
    )


@router.get("/{drive_id}/activities/{activity_id}/attendance/audit", response_model=List[DriveAttendanceAuditResponse])
async def list_activity_attendance_audit_endpoint(
    drive_id: int,
    activity_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> List[DriveAttendanceAuditResponse]:
    """Retrieve immutable attendance audit history for an activity."""
    return await list_activity_attendance_audit(
        session=session,
        current_user=current_user,
        drive_id=drive_id,
        activity_id=activity_id,
    )


@router.get("/{drive_id}/announcements", response_model=List[DriveAnnouncementResponse])
async def list_drive_announcements_endpoint(
    drive_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> List[DriveAnnouncementResponse]:
    """List drive-specific announcements sent for this drive."""
    return await list_drive_announcements(session=session, current_user=current_user, drive_id=drive_id)


@router.post("/{drive_id}/announcements", response_model=DriveAnnouncementResponse, status_code=status.HTTP_201_CREATED)
async def send_drive_announcement_endpoint(
    drive_id: int,
    payload: DriveAnnouncementCreate,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
) -> DriveAnnouncementResponse:
    """Broadcast a drive-specific announcement and dispatch deduplicated in-app notifications."""
    return await send_drive_announcement(
        session=session,
        current_user=current_user,
        drive_id=drive_id,
        payload=payload,
    )


@router.get("/{drive_id}/report", response_model=DriveReportResponse)
async def get_drive_report_endpoint(
    drive_id: int,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
) -> DriveReportResponse:
    """Generate structured participation, eligibility, attendance, and placement report for a drive."""
    return await build_drive_report(session=session, current_user=current_user, drive_id=drive_id)


@router.get("/{drive_id}/report/export/pdf")
async def export_drive_report_pdf_endpoint(
    drive_id: int,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    """Export drive-specific report as PDF."""
    report = await build_drive_report(session=session, current_user=current_user, drive_id=drive_id)
    pdf_bytes = generate_drive_report_pdf(report)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="drive_{drive_id}_report.pdf"'},
    )


@router.get("/{drive_id}/report/export/excel")
async def export_drive_report_excel_endpoint(
    drive_id: int,
    current_user: User = Depends(require_institutional_staff),
    session: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    """Export drive-specific report as a multi-sheet .xlsx workbook."""
    report = await build_drive_report(session=session, current_user=current_user, drive_id=drive_id)
    xlsx_bytes = generate_drive_report_excel(report)
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="drive_{drive_id}_report.xlsx"'},
    )

