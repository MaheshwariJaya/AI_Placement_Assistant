import logging
from pathlib import Path
from typing import Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError, PermissionDeniedError
from app.models.resume import Resume
from app.models.student import (
    StudentProfile,
    StudentEducation,
    StudentSkill,
    StudentProject,
    StudentExperience,
    StudentCertification,
)
from app.models.user import User
from app.schemas.resume import (
    ResumeStructuredData,
    ResumeSyncRequest,
    ResumeSyncResponse,
)
from app.services.ai_provider import (
    get_ai_provider,
    AIServiceError,
    MockAIProvider,
    GeminiAIProvider,
    OpenAIProvider,
)
from app.services.evidence_validator import validate_and_sanitize_resume_data
from app.services.document_parser import (
    extract_document_text,
    ScannedPdfError,
    DocumentParsingError,
)
from app.services.resume_cache import (
    extraction_cache,
    compute_extraction_cache_key,
    EXTRACTION_SCHEMA_VERSION,
    EXTRACTION_PROMPT_VERSION,
)

logger = logging.getLogger(__name__)


async def run_resume_extraction_pipeline(
    resume_id: int,
    db: AsyncSession,
) -> Resume:
    """
    Executes end-to-end local text extraction and AI entity extraction on a resume.
    Updates resume state machine: uploaded -> processing -> review_required (or failed).
    """
    stmt = select(Resume).where(Resume.id == resume_id)
    result = await db.execute(stmt)
    resume = result.scalar_one_or_none()
    if not resume:
        raise NotFoundError("Resume record not found.", code="RESUME_NOT_FOUND")

    # Guard against duplicate concurrent extraction requests
    if resume.parsing_status == "processing":
        raise AppError(
            "Resume extraction is already in progress for this document.",
            code="EXTRACTION_IN_PROGRESS",
            status_code=409,
        )

    # Set status to processing
    resume.parsing_status = "processing"
    await db.commit()
    await db.refresh(resume)

    try:
        # Step 1: Local text extraction
        file_path = Path(resume.file_path)
        raw_text = extract_document_text(file_path=file_path, file_type=resume.file_type)
        resume.raw_extracted_text = raw_text

        # Determine active provider and model
        ai_provider = get_ai_provider()
        if isinstance(ai_provider, MockAIProvider):
            provider_name = "mock"
            model_name = "mock-rule-engine"
        elif isinstance(ai_provider, GeminiAIProvider):
            provider_name = "gemini"
            model_name = ai_provider.model_name
        elif isinstance(ai_provider, OpenAIProvider):
            provider_name = "openai"
            model_name = ai_provider.model_name
        else:
            provider_name = getattr(ai_provider, "provider_name", "unknown")
            model_name = getattr(ai_provider, "model_name", "default")

        # Step 2: Check service-level extraction cache
        cache_key = compute_extraction_cache_key(
            file_hash=resume.file_hash,
            provider=provider_name,
            model=model_name,
        )

        cached_dict = extraction_cache.get(cache_key)
        if not cached_dict:
            # Check DB fallback across previous completed parses of same file hash
            existing_stmt = (
                select(Resume)
                .where(
                    Resume.file_hash == resume.file_hash,
                    Resume.parsing_status.in_(["review_required", "approved"]),
                    Resume.parsed_entities_json.isnot(None),
                    Resume.id != resume.id,
                )
                .order_by(Resume.created_at.desc())
                .limit(1)
            )
            existing_res = await db.execute(existing_stmt)
            prior_resume = existing_res.scalar_one_or_none()
            if prior_resume and prior_resume.parsed_entities_json:
                prior_meta = prior_resume.parsed_entities_json.get("_cache_meta", {})
                if (
                    prior_meta.get("schema_version") == EXTRACTION_SCHEMA_VERSION
                    and prior_meta.get("prompt_version") == EXTRACTION_PROMPT_VERSION
                    and prior_meta.get("provider") == provider_name
                    and prior_meta.get("model") == model_name
                ):
                    cached_dict = prior_resume.parsed_entities_json
                    extraction_cache.put(cache_key, cached_dict)

        if cached_dict:
            logger.info(
                "Extraction cache hit for resume %s (hash: %s, provider: %s, model: %s)",
                resume.id, resume.file_hash, provider_name, model_name,
            )
            resume.parsed_entities_json = cached_dict
            resume.parsing_status = "review_required"
            await db.commit()
            await db.refresh(resume)
            return resume

        # Step 3: AI structured entity extraction with usage telemetry
        structured_data, usage = await ai_provider.extract_resume_entities_with_usage(raw_text)

        # Step 4: Defense-in-depth source evidence verification and hallucination purge
        sanitized_data = validate_and_sanitize_resume_data(raw_text, structured_data)

        # Step 5: Persist extracted entities, cache metadata, and transition state
        payload = sanitized_data.model_dump()
        payload["_cache_meta"] = {
            "cache_key": cache_key,
            "file_hash": resume.file_hash,
            "schema_version": EXTRACTION_SCHEMA_VERSION,
            "prompt_version": EXTRACTION_PROMPT_VERSION,
            "provider": provider_name,
            "model": model_name,
            "usage": usage.model_dump() if usage else None,
        }
        extraction_cache.put(cache_key, payload)

        logger.info(
            "Resume %s extracted via %s (%s): tokens(prompt=%s, completion=%s, total=%s), latency=%sms",
            resume.id,
            usage.provider if usage else provider_name,
            usage.model if usage else model_name,
            usage.prompt_tokens if usage else None,
            usage.completion_tokens if usage else None,
            usage.total_tokens if usage else None,
            usage.latency_ms if usage else None,
        )

        resume.parsed_entities_json = payload
        resume.parsing_status = "review_required"
        await db.commit()
        await db.refresh(resume)
        return resume

    except ScannedPdfError as e:
        logger.warning(f"Resume {resume_id} failed: Scanned PDF detected without selectable text.")
        resume.parsing_status = "failed"
        resume.raw_extracted_text = f"[FAILED] {e.message}"
        await db.commit()
        await db.refresh(resume)
        raise e

    except (DocumentParsingError, AIServiceError) as e:
        logger.error(f"Resume {resume_id} extraction failed: {e.message}")
        resume.parsing_status = "failed"
        resume.raw_extracted_text = f"[FAILED] {e.message}"
        await db.commit()
        await db.refresh(resume)
        raise e

    except Exception as e:
        logger.exception(f"Unexpected error parsing resume {resume_id}: {str(e)}")
        resume.parsing_status = "failed"
        resume.raw_extracted_text = f"[FAILED] Internal processing error: {str(e)}"
        await db.commit()
        await db.refresh(resume)
        raise AppError(f"Resume processing failed: {str(e)}", code="EXTRACTION_PIPELINE_ERROR", status_code=500)


async def sync_approved_resume_entities(
    resume: Resume,
    student_profile: StudentProfile,
    sync_req: ResumeSyncRequest,
    db: AsyncSession,
) -> ResumeSyncResponse:
    """
    Commits approved structured entities into the student's normalized database profile.
    STRICT GUARDRAIL: Never overwrites verified academic metrics (CGPA, roll_number, backlogs, user email).
    """
    # 1. Determine entity payload (from request or stored parsed_entities_json)
    if sync_req.verified_data:
        data = sync_req.verified_data
    elif resume.parsed_entities_json:
        data = ResumeStructuredData.model_validate(resume.parsed_entities_json)
    else:
        raise AppError("No extracted or verified entities available to sync.", code="NO_ENTITIES_TO_SYNC", status_code=400)

    synced_counts = {
        "education": 0,
        "skills": 0,
        "projects": 0,
        "experiences": 0,
        "certifications": 0,
        "profile_links_updated": 0,
        "phone_updated": 0,
    }

    # 2. Synchronize Education History (into normalized student_education table)
    if sync_req.sync_education and data.education:
        try:
            edu_stmt = select(StudentEducation).where(StudentEducation.student_id == student_profile.id)
            existing_edu_res = await db.execute(edu_stmt)
            existing_edu = {
                (e.institution_name.lower().strip(), e.degree.lower().strip()): e
                for e in existing_edu_res.scalars().all()
            }
        except Exception:
            existing_edu = {}

        for edu in data.education:
            key = (edu.institution.lower().strip(), edu.degree.lower().strip())
            if key in existing_edu:
                curr_edu = existing_edu[key]
                if edu.field_of_study:
                    curr_edu.field_of_study = edu.field_of_study.strip()
                if edu.start_year is not None:
                    curr_edu.start_year = edu.start_year
                if edu.end_year is not None:
                    curr_edu.end_year = edu.end_year
                if edu.cgpa_or_percentage:
                    curr_edu.cgpa_or_percentage = edu.cgpa_or_percentage.strip()
            else:
                new_edu = StudentEducation(
                    student_id=student_profile.id,
                    institution_name=edu.institution.strip(),
                    degree=edu.degree.strip(),
                    field_of_study=edu.field_of_study.strip() if edu.field_of_study else None,
                    start_year=edu.start_year,
                    end_year=edu.end_year,
                    cgpa_or_percentage=edu.cgpa_or_percentage.strip() if edu.cgpa_or_percentage else None,
                )
                db.add(new_edu)
                existing_edu[key] = new_edu
                synced_counts["education"] += 1

    # 3. Synchronize Skills
    if sync_req.sync_skills and data.skills:
        # Load existing skills to prevent duplicate key violations
        try:
            skills_stmt = select(StudentSkill).where(StudentSkill.student_id == student_profile.id)
            existing_skills_res = await db.execute(skills_stmt)
            existing_skills = {s.skill_name.lower().strip(): s for s in existing_skills_res.scalars().all()}
        except Exception:
            existing_skills = {}

        for skill_item in data.skills:
            normalized_name = skill_item.skill_name.strip()
            key = normalized_name.lower()
            if key in existing_skills:
                # Update existing proficiency / category if not already verified
                existing = existing_skills[key]
                if not existing.is_verified:
                    existing.proficiency_level = skill_item.proficiency_level
                    existing.category = skill_item.category
            else:
                new_skill = StudentSkill(
                    student_id=student_profile.id,
                    skill_name=normalized_name,
                    category=skill_item.category,
                    proficiency_level=skill_item.proficiency_level,
                    is_verified=False,
                )
                db.add(new_skill)
                existing_skills[key] = new_skill
                synced_counts["skills"] += 1

    # 4. Synchronize Projects
    if sync_req.sync_projects and data.projects:
        try:
            proj_stmt = select(StudentProject).where(StudentProject.student_id == student_profile.id)
            existing_proj_res = await db.execute(proj_stmt)
            existing_projs = {
                p.title.lower().strip(): p
                for p in existing_proj_res.scalars().all()
            }
        except Exception:
            existing_projs = {}

        for p in data.projects:
            key = p.title.lower().strip()
            if key in existing_projs:
                curr_proj = existing_projs[key]
                if p.description:
                    curr_proj.description = p.description
                if p.technologies:
                    curr_proj.technologies = p.technologies
                if p.project_url:
                    curr_proj.project_url = p.project_url
                if p.start_date:
                    curr_proj.start_date = p.start_date
                if p.end_date:
                    curr_proj.end_date = p.end_date
            else:
                new_project = StudentProject(
                    student_id=student_profile.id,
                    title=p.title.strip(),
                    description=p.description,
                    technologies=p.technologies,
                    project_url=p.project_url,
                    start_date=p.start_date,
                    end_date=p.end_date,
                )
                db.add(new_project)
                existing_projs[key] = new_project
                synced_counts["projects"] += 1

    # 5. Synchronize Experiences
    if sync_req.sync_experiences and data.experiences:
        try:
            exp_stmt = select(StudentExperience).where(StudentExperience.student_id == student_profile.id)
            existing_exp_res = await db.execute(exp_stmt)
            existing_exps = {
                (e.company_name.lower().strip(), e.role_title.lower().strip()): e
                for e in existing_exp_res.scalars().all()
            }
        except Exception:
            existing_exps = {}

        for exp in data.experiences:
            key = (exp.company_name.lower().strip(), exp.role_title.lower().strip())
            if key in existing_exps:
                curr_exp = existing_exps[key]
                if exp.description:
                    curr_exp.description = exp.description
                if exp.start_date:
                    curr_exp.start_date = exp.start_date
                if exp.end_date:
                    curr_exp.end_date = exp.end_date
                curr_exp.is_current = exp.is_current
            else:
                new_exp = StudentExperience(
                    student_id=student_profile.id,
                    company_name=exp.company_name.strip(),
                    role_title=exp.role_title.strip(),
                    description=exp.description,
                    start_date=exp.start_date,
                    end_date=exp.end_date,
                    is_current=exp.is_current,
                )
                db.add(new_exp)
                existing_exps[key] = new_exp
                synced_counts["experiences"] += 1

    # 6. Synchronize Certifications
    if sync_req.sync_certifications and data.certifications:
        try:
            cert_stmt = select(StudentCertification).where(StudentCertification.student_id == student_profile.id)
            existing_cert_res = await db.execute(cert_stmt)
            existing_certs = {
                c.certificate_name.lower().strip(): c
                for c in existing_cert_res.scalars().all()
            }
        except Exception:
            existing_certs = {}
        for cert in data.certifications:
            key = cert.certificate_name.lower().strip()
            if key in existing_certs:
                curr_cert = existing_certs[key]
                if cert.issuing_organization:
                    curr_cert.issuing_organization = cert.issuing_organization.strip()
                if cert.issue_date:
                    curr_cert.issue_date = cert.issue_date
                if cert.credential_url:
                    curr_cert.credential_url = cert.credential_url
            else:
                new_cert = StudentCertification(
                    student_id=student_profile.id,
                    certificate_name=cert.certificate_name.strip(),
                    issuing_organization=cert.issuing_organization.strip(),
                    issue_date=cert.issue_date,
                    credential_url=cert.credential_url,
                )
                db.add(new_cert)
                existing_certs[key] = new_cert
                synced_counts["certifications"] += 1

    # 7. Synchronize External Profile Links (LinkedIn, GitHub, Portfolio)
    if sync_req.sync_links and data.personal_info:
        links_changed = False
        # LinkedIn
        if data.personal_info.linkedin_url:
            if not student_profile.linkedin_url or sync_req.update_existing_links or "student-profile" in (student_profile.linkedin_url or ""):
                student_profile.linkedin_url = data.personal_info.linkedin_url
                links_changed = True
        # GitHub
        if data.personal_info.github_url:
            if not student_profile.github_url or sync_req.update_existing_links or "student-dev" in (student_profile.github_url or ""):
                student_profile.github_url = data.personal_info.github_url
                links_changed = True
        # Portfolio
        if data.personal_info.portfolio_url:
            if not student_profile.portfolio_url or sync_req.update_existing_links:
                student_profile.portfolio_url = data.personal_info.portfolio_url
                links_changed = True

        if links_changed:
            synced_counts["profile_links_updated"] += 1

    # 8. Synchronize Contact Phone (if requested and user.phone is currently empty)
    if sync_req.update_phone and data.personal_info and data.personal_info.phone:
        user_stmt = select(User).where(User.id == student_profile.user_id)
        u_res = await db.execute(user_stmt)
        user = u_res.scalar_one_or_none()
        if user and not user.phone:
            user.phone = data.personal_info.phone.strip()
            synced_counts["phone_updated"] += 1

    # STRICT SECURITY ASSERTION: User.email and User.full_name are NEVER modified by resume parsing.
    # Academic metrics (student_profile.cgpa, roll_number, graduation_year, backlogs) are 100% UNTOUCHED.

    # 9. Update Resume Status to Approved
    resume.parsing_status = "approved"
    resume.parsed_entities_json = data.model_dump()

    await db.commit()
    await db.refresh(resume)

    return ResumeSyncResponse(
        message="Resume extraction approved and student portfolio successfully synchronized.",
        synced_counts=synced_counts,
        verified_metrics_protected=True,
    )
