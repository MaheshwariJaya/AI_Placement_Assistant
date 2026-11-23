import logging
import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_async_session
from app.core.dependencies import get_current_user, require_student
from app.core.errors import AppError, NotFoundError, PermissionDeniedError
from app.models.resume import Resume
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from app.schemas.resume import (
    ResumeResponse,
    ResumeUploadResponse,
    ResumeStructuredData,
    ResumeReviewUpdateRequest,
    ResumeSyncRequest,
    ResumeSyncResponse,
)
from app.services.ai_provider import AIServiceError
from app.services.document_parser import (
    validate_file_content,
    save_resume_file,
    ScannedPdfError,
    DocumentParsingError,
)
from app.services.resume_extractor import (
    run_resume_extraction_pipeline,
    sync_approved_resume_entities,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["Resume Intelligence"])


def format_resume_response(resume: Resume) -> ResumeResponse:
    """Helper to convert Resume ORM instance into ResumeResponse schema."""
    parsed_entities = None
    if resume.parsed_entities_json:
        try:
            parsed_entities = ResumeStructuredData.model_validate(resume.parsed_entities_json)
        except Exception as e:
            logger.warning(f"Failed to validate parsed_entities_json for resume {resume.id}: {e}")

    # Generate truncated preview of raw text
    text_preview = None
    if resume.raw_extracted_text:
        text_preview = resume.raw_extracted_text[:500] + ("..." if len(resume.raw_extracted_text) > 500 else "")

    return ResumeResponse(
        id=resume.id,
        student_id=resume.student_id,
        file_name=resume.file_name,
        file_type=resume.file_type,
        file_size_bytes=resume.file_size_bytes,
        file_hash=resume.file_hash,
        parsing_status=resume.parsing_status,
        is_active=resume.is_active,
        parsed_entities=parsed_entities,
        raw_text_preview=text_preview,
        created_at=resume.created_at,
        updated_at=resume.updated_at,
    )


async def check_resume_access(
    resume: Resume,
    current_user: User,
    db: AsyncSession,
) -> StudentProfile:
    """Enforces multi-role authorization boundary for resume retrieval and downloading."""
    # Load associated student profile and user
    stmt = (
        select(StudentProfile)
        .where(StudentProfile.id == resume.student_id)
        .options(selectinload(StudentProfile.user))
    )
    res = await db.execute(stmt)
    student_profile = res.scalar_one_or_none()
    if not student_profile:
        raise NotFoundError("Associated student profile not found.", code="STUDENT_NOT_FOUND")

    # 1. Student Access: private to own profile
    if current_user.role == UserRole.STUDENT:
        if not current_user.student_profile or current_user.student_profile.id != resume.student_id:
            raise PermissionDeniedError("You are not authorized to access another student's resume.")
        return student_profile

    # 2. TPO Access: scoped to student of same institution
    elif current_user.role == UserRole.TPO:
        if student_profile.user.institution_id != current_user.institution_id:
            raise PermissionDeniedError("TPOs can only access resumes of students from their own institution.")
        return student_profile

    # 3. Admin Access: system platform auditing
    elif current_user.role == UserRole.ADMIN:
        return student_profile

    # 4. Recruiter Access: strictly scoped to applicants of their company's jobs
    elif current_user.role == UserRole.RECRUITER:
        # In current phase before applications module, recruiters cannot browse arbitrary student resumes
        raise PermissionDeniedError(
            "Recruiters can only access resumes of candidates who have actively applied to their company's jobs."
        )

    raise PermissionDeniedError("Unauthorized role for resume access.")


@router.post("/upload", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    auto_extract: bool = True,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Upload a PDF or DOCX resume document.
    Enforces 5MB size limit, extension, magic byte validation, and private storage.
    Automatically triggers local text extraction and AI entity extraction when auto_extract=True.
    """
    if not current_user.student_profile:
        raise AppError("User does not have an associated student profile.", code="STUDENT_PROFILE_REQUIRED", status_code=400)

    student_id = current_user.student_profile.id

    # Read uploaded file content
    content = await file.read()
    original_filename = file.filename or "resume.pdf"

    # Validate file size, extension, and magic signatures
    file_type, file_hash = validate_file_content(content=content, original_filename=original_filename)

    # Save to private uploads directory
    secure_filename, target_path = save_resume_file(
        content=content,
        student_id=student_id,
        file_type=file_type,
    )

    # Create Resume DB record
    resume = Resume(
        student_id=student_id,
        file_name=original_filename,
        file_path=str(target_path),
        file_type=file_type,
        file_size_bytes=len(content),
        file_hash=file_hash,
        parsing_status="uploaded",
        is_active=True,
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    # Trigger extraction pipeline if requested
    if auto_extract:
        try:
            resume = await run_resume_extraction_pipeline(resume_id=resume.id, db=db)
        except (ScannedPdfError, DocumentParsingError, AIServiceError) as e:
            # We preserve the uploaded resume record with 'failed' status for user feedback
            logger.warning(f"Resume {resume.id} uploaded but extraction stopped: {e.message}")

    return format_resume_response(resume)


@router.get("", response_model=List[ResumeResponse])
async def list_resumes(
    student_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    List resumes with role-based scoping:
    - Students see only their own resumes.
    - TPOs and Admins see resumes for students in their institution.
    """
    if current_user.role == UserRole.STUDENT or (current_user.email == "maheshwarijaya03@gmail.com" and current_user.student_profile):
        if not current_user.student_profile:
            return []
        stmt = (
            select(Resume)
            .where(Resume.student_id == current_user.student_profile.id)
            .order_by(Resume.created_at.desc())
        )
    elif current_user.role in [UserRole.TPO, UserRole.ADMIN]:
        stmt = (
            select(Resume)
            .join(StudentProfile, Resume.student_id == StudentProfile.id)
            .join(User, StudentProfile.user_id == User.id)
        )
        if current_user.role == UserRole.TPO:
            stmt = stmt.where(User.institution_id == current_user.institution_id)
        if student_id:
            stmt = stmt.where(Resume.student_id == student_id)
        stmt = stmt.order_by(Resume.created_at.desc())
    else:
        raise PermissionDeniedError("Recruiters cannot list bulk resumes without an active job application context.")

    result = await db.execute(stmt)
    resumes = result.scalars().all()
    return [format_resume_response(r) for r in resumes]


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume_details(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Retrieve resume metadata and structured extracted entities."""
    stmt = select(Resume).where(Resume.id == resume_id)
    res = await db.execute(stmt)
    resume = res.scalar_one_or_none()
    if not resume:
        raise NotFoundError("Resume not found.", code="RESUME_NOT_FOUND")

    await check_resume_access(resume, current_user, db)
    return format_resume_response(resume)


@router.get("/{resume_id}/download")
async def download_resume_file(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Secure authenticated streaming download of private resume document.
    Validates role scoping and streams directly from backend filesystem.
    """
    stmt = select(Resume).where(Resume.id == resume_id)
    res = await db.execute(stmt)
    resume = res.scalar_one_or_none()
    if not resume:
        raise NotFoundError("Resume not found.", code="RESUME_NOT_FOUND")

    await check_resume_access(resume, current_user, db)

    file_path = Path(resume.file_path)
    if not file_path.exists():
        raise NotFoundError("Resume file is missing from private storage.", code="FILE_NOT_FOUND")

    # Determine standard MIME type
    if resume.file_type == "pdf":
        media_type = "application/pdf"
    elif resume.file_type == "docx":
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        media_type = "application/octet-stream"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=resume.file_name,
    )


@router.delete("/{resume_id}", status_code=status.HTTP_200_OK)
async def delete_resume(
    resume_id: int,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Permanently delete a resume document and its physical file."""
    stmt = select(Resume).where(Resume.id == resume_id)
    res = await db.execute(stmt)
    resume = res.scalar_one_or_none()
    if not resume:
        raise NotFoundError("Resume not found.", code="RESUME_NOT_FOUND")

    if not current_user.student_profile or resume.student_id != current_user.student_profile.id:
        raise PermissionDeniedError("You can delete only your own resumes.")

    # Remove physical file if present
    file_path = Path(resume.file_path)
    if file_path.exists():
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Could not remove physical file {file_path}: {e}")

    await db.delete(resume)
    await db.commit()
    return {"message": "Resume document deleted successfully."}


@router.post("/{resume_id}/extract", response_model=ResumeResponse)
async def trigger_extraction(
    resume_id: int,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Re-run or trigger local text extraction and AI entity extraction on an uploaded resume."""
    stmt = select(Resume).where(Resume.id == resume_id)
    res = await db.execute(stmt)
    resume = res.scalar_one_or_none()
    if not resume:
        raise NotFoundError("Resume not found.", code="RESUME_NOT_FOUND")

    if not current_user.student_profile or resume.student_id != current_user.student_profile.id:
        raise PermissionDeniedError("You can only extract entities from your own resumes.")

    resume = await run_resume_extraction_pipeline(resume_id=resume.id, db=db)
    return format_resume_response(resume)


@router.put("/{resume_id}/review", response_model=ResumeResponse)
async def update_extracted_entities(
    resume_id: int,
    req: ResumeReviewUpdateRequest,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Allow student to edit and correct AI-extracted structured entities before approval.
    Updates the stored JSON and marks status as review_required.
    """
    stmt = select(Resume).where(Resume.id == resume_id)
    res = await db.execute(stmt)
    resume = res.scalar_one_or_none()
    if not resume:
        raise NotFoundError("Resume not found.", code="RESUME_NOT_FOUND")

    if not current_user.student_profile or resume.student_id != current_user.student_profile.id:
        raise PermissionDeniedError("You can modify only your own resumes.")

    resume.parsed_entities_json = req.structured_data.model_dump()
    resume.parsing_status = "review_required"
    await db.commit()
    await db.refresh(resume)

    return format_resume_response(resume)


@router.post("/{resume_id}/approve", response_model=ResumeSyncResponse)
async def approve_and_sync_resume(
    resume_id: int,
    sync_req: ResumeSyncRequest,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Approve extracted entities and synchronize them into normalized student portfolio tables.
    Protects verified academic metrics (CGPA, backlogs, roll_number) from being overwritten.
    """
    stmt = select(Resume).where(Resume.id == resume_id)
    res = await db.execute(stmt)
    resume = res.scalar_one_or_none()
    if not resume:
        raise NotFoundError("Resume not found.", code="RESUME_NOT_FOUND")

    if not current_user.student_profile or resume.student_id != current_user.student_profile.id:
        raise PermissionDeniedError("You can approve only your own resumes.")

    return await sync_approved_resume_entities(
        resume=resume,
        student_profile=current_user.student_profile,
        sync_req=sync_req,
        db=db,
    )


@router.post("/{resume_id}/reject")
async def reject_resume_extraction(
    resume_id: int,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """Mark resume extraction as rejected by the student."""
    stmt = select(Resume).where(Resume.id == resume_id)
    res = await db.execute(stmt)
    resume = res.scalar_one_or_none()
    if not resume:
        raise NotFoundError("Resume not found.", code="RESUME_NOT_FOUND")

    if not current_user.student_profile or resume.student_id != current_user.student_profile.id:
        raise PermissionDeniedError("You can reject only your own resumes.")

    resume.parsing_status = "rejected"
    await db.commit()
    return {"message": "Resume extraction marked as rejected."}

