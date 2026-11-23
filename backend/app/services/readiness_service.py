"""Service layer for Placement Readiness Prediction, Job-Specific Gap Analysis & Historical Analytics."""
from collections import defaultdict
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import (
    AppException,
    AuthorizationException,
    EntityNotFoundException,
)
from app.models.job import Job, JobEligibleDepartment, JobStatus
from app.models.mock_interview import (
    MockInterviewCategory,
    MockInterviewSession,
    MockInterviewStatus,
)
from app.models.readiness import ReadinessCategory, ReadinessSnapshot
from app.models.resume import Resume
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from app.schemas.ai import AIUsageMetadata
from app.schemas.readiness import (
    DEFAULT_CATEGORY_DEFINITIONS,
    READINESS_FORMULA_VERSION,
    READINESS_TRANSPARENCY_NOTICE,
    JobReadinessCheckRequest,
    JobReadinessCheckResponse,
    ReadinessCalculateRequest,
    ReadinessHistoryPoint,
    ReadinessHistoryResponse,
    ReadinessIndicatorScore,
    ReadinessIndicatorWeights,
    ReadinessRecommendationItem,
    ReadinessRecommendationsAIOutput,
    ReadinessSnapshotResponse,
    ReadOnlyAcademicSummary,
    TpoBatchReadinessStat,
    TpoCategoryDistributionItem,
    TpoDepartmentReadinessStat,
    TpoReadinessAnalyticsResponse,
    TpoSkillCategoryStat,
    TpoStudentReadinessRow,
)
from app.services.ai_provider import AIServiceError, get_ai_provider, MockAIProvider
from app.services.eligibility_service import evaluate_student_job_eligibility
from app.services.matching_engine import calculate_compatibility_score, normalize_skill
from app.services.readiness_mock_helpers import generate_mock_readiness_recommendations

logger = logging.getLogger(__name__)

RECOMMENDATION_SYSTEM_PROMPT = (
    "You are a constructive campus placement preparation advisor.\n"
    "STRICT RULES:\n"
    "1. Generate 4 to 6 concrete, practical preparation actions based strictly on <WEAK_OR_MISSING_INDICATORS>, "
    "<MISSING_MANDATORY_SKILLS>, <MISSING_PREFERRED_SKILLS>, and <STUDENT_PORTFOLIO_SUMMARY>.\n"
    "2. Never describe readiness as a hiring probability, never recommend auto-rejection, and never mention CGPA manipulation.\n"
    "3. Keep titles concise and descriptions actionable (1-2 sentences). Return valid JSON.\n"
    "4. Branch Grounding: Ground all technical projects, skill suggestions, and preparation advice in the student's verified academic branch (<STUDENT_DEPARTMENT>). Never suggest Computer Science/software-specific actions (like DSA or full-stack web projects) to students from non-CS disciplines unless the student is targeting a software role."
)

CATEGORY_LABELS: Dict[ReadinessCategory, str] = {
    ReadinessCategory.EXCELLENT_PREPARATION: "Excellent Preparation",
    ReadinessCategory.PLACEMENT_READY: "Placement Ready",
    ReadinessCategory.NEEDS_IMPROVEMENT: "Needs Improvement",
    ReadinessCategory.REQUIRES_SIGNIFICANT_PREPARATION: "Requires Significant Preparation",
}


def classify_readiness_category(score: float) -> Tuple[ReadinessCategory, str]:
    """Map numeric readiness index (0-100) to transparent preparation category."""
    if score >= 85.0:
        cat = ReadinessCategory.EXCELLENT_PREPARATION
    elif score >= 70.0:
        cat = ReadinessCategory.PLACEMENT_READY
    elif score >= 50.0:
        cat = ReadinessCategory.NEEDS_IMPROVEMENT
    else:
        cat = ReadinessCategory.REQUIRES_SIGNIFICANT_PREPARATION
    return cat, CATEGORY_LABELS[cat]


def _indicator_status(pct: float, data_present: bool) -> str:
    if not data_present:
        return "missing_data"
    if pct >= 75.0:
        return "strong"
    if pct >= 50.0:
        return "moderate"
    return "developing"


def _compute_readiness_indicators(
    user: User,
    profile: StudentProfile,
    resumes: List[Resume],
    mock_sessions: List[MockInterviewSession],
    weights: Dict[str, float],
    job: Optional[Job] = None,
) -> Tuple[
    float,
    List[ReadinessIndicatorScore],
    List[str],
    List[str],
    List[str],
    Dict[str, Any],
]:
    """
    Deterministic, versioned (v1.0) 8-indicator calculation kept strictly separate from academic eligibility.
    Returns (overall_score, indicators, missing_data_fields, limitations, remaining_skill_gaps, diagnostics).
    """
    skills = list(profile.skills or [])
    projects = list(profile.projects or [])
    experiences = list(profile.experiences or [])
    certifications = list(profile.certifications or [])
    active_resumes = [r for r in resumes if getattr(r, "is_active", True)]
    completed_mocks = [
        s for s in mock_sessions
        if s.status == MockInterviewStatus.COMPLETED and s.evaluation is not None
    ]

    missing_data_fields: List[str] = []
    limitations: List[str] = [
        "Preparation readiness summarizes recorded portfolio, resume, and practice evidence — it is not a hiring probability."
    ]
    remaining_skill_gaps: List[str] = []

    # 1. Verified Skill Coverage (default 20)
    w_skills = weights["verified_skills"]
    student_skill_norms = {normalize_skill(s.skill_name) for s in skills if s.skill_name}
    verified_count = sum(1 for s in skills if s.is_verified)
    skill_categories = {s.category.lower() for s in skills if s.category}
    skill_data_present = len(skills) > 0

    matched_job_skills: List[str] = []
    missing_mand_skills: List[str] = []
    missing_pref_skills: List[str] = []

    if job is not None and (job.skills or []):
        job_mand = [s.skill_name for s in job.skills if s.is_mandatory]
        job_pref = [s.skill_name for s in job.skills if not s.is_mandatory]
        matched_mand = [s for s in job_mand if normalize_skill(s) in student_skill_norms]
        missing_mand_skills = [s for s in job_mand if normalize_skill(s) not in student_skill_norms]
        matched_pref = [s for s in job_pref if normalize_skill(s) in student_skill_norms]
        missing_pref_skills = [s for s in job_pref if normalize_skill(s) not in student_skill_norms]
        matched_job_skills = matched_mand + matched_pref
        remaining_skill_gaps.extend(missing_mand_skills[:6])

        mand_ratio = len(matched_mand) / max(1, len(job_mand)) if job_mand else 1.0
        pref_ratio = len(matched_pref) / max(1, len(job_pref)) if job_pref else 1.0
        ver_ratio = verified_count / max(1, len(skills)) if skills else 0.0
        skills_pct = round(min(100.0, (mand_ratio * 65.0) + (pref_ratio * 20.0) + (ver_ratio * 15.0)), 1)
        skills_evidence = (
            f"{len(matched_mand)}/{len(job_mand)} mandatory job skills & "
            f"{len(matched_pref)}/{len(job_pref)} preferred skills matched ({verified_count} verified)."
        )
    else:
        count_score = min(len(skills) / 6.0, 1.0) * 55.0
        verified_score = min(verified_count / 4.0, 1.0) * 25.0
        breadth_score = min(len(skill_categories) / 3.0, 1.0) * 20.0
        skills_pct = round(count_score + verified_score + breadth_score, 1)
        skills_evidence = f"{len(skills)} recorded skills ({verified_count} verified) across {len(skill_categories)} categories."
        if len(skills) < 4:
            remaining_skill_gaps.append("Expand verified core technical & tool skill coverage (target 6+ skills).")

    if not skill_data_present:
        missing_data_fields.append("Verified Skills Portfolio")

    # 2. Project Portfolio Quality (default 15)
    w_projects = weights["project_portfolio"]
    proj_present = len(projects) > 0
    if not proj_present:
        projects_pct = 0.0
        proj_evidence = "No technical or capstone projects recorded yet."
        missing_data_fields.append("Project Portfolio")
    else:
        proj_count_pts = min(len(projects) / 3.0, 1.0) * 45.0
        detailed_count = sum(1 for p in projects if p.description and len(p.description.strip()) >= 35)
        tech_count = sum(1 for p in projects if p.technologies and len(p.technologies.strip()) >= 3)
        url_count = sum(1 for p in projects if p.project_url and p.project_url.strip())
        detail_pts = min(detailed_count / max(1, min(len(projects), 3)), 1.0) * 25.0
        tech_pts = min(tech_count / max(1, min(len(projects), 3)), 1.0) * 20.0
        url_pts = 10.0 if url_count > 0 else 0.0
        projects_pct = round(min(100.0, proj_count_pts + detail_pts + tech_pts + url_pts), 1)
        proj_evidence = f"{len(projects)} projects ({detailed_count} with detailed descriptions, {tech_count} with tech stacks)."

    # 3. Internship & Experience Profile (default 10)
    w_exp = weights["internship_experience"]
    exp_present = len(experiences) > 0
    if not exp_present:
        exp_pct = 0.0
        exp_evidence = "No internship or work experience records entered."
        missing_data_fields.append("Internship / Work Experience (Optional for freshers)")
        limitations.append("No internship entries recorded — campus freshers without prior internships are not flagged as low ability.")
    else:
        exp_count_pts = min(len(experiences) / 2.0, 1.0) * 60.0
        exp_detail_cnt = sum(1 for e in experiences if e.description and len(e.description.strip()) >= 30)
        exp_detail_pts = min(exp_detail_cnt / max(1, min(len(experiences), 2)), 1.0) * 40.0
        exp_pct = round(min(100.0, exp_count_pts + exp_detail_pts), 1)
        exp_evidence = f"{len(experiences)} internship/experience record(s) ({exp_detail_cnt} with impact details)."

    # 4. Relevant Certifications (default 8)
    w_cert = weights["certifications"]
    cert_present = len(certifications) > 0
    if not cert_present:
        cert_pct = 0.0
        cert_evidence = "No verified certifications added."
        missing_data_fields.append("Relevant Certifications")
    else:
        cert_count_pts = min(len(certifications) / 2.0, 1.0) * 75.0
        url_bonus = 25.0 if any(c.credential_url for c in certifications) else 0.0
        cert_pct = round(min(100.0, cert_count_pts + url_bonus), 1)
        cert_evidence = f"{len(certifications)} certification(s) recorded."

    # 5. Resume Quality & Completeness (default 15)
    w_resume = weights["resume_quality"]
    res_present = len(active_resumes) > 0
    has_approved_resume = any(r.parsing_status == "approved" for r in active_resumes)
    if not res_present:
        resume_pct = 0.0
        resume_evidence = "No active resume uploaded."
        missing_data_fields.append("Uploaded & Approved Resume")
    else:
        best_res = sorted(
            active_resumes,
            key=lambda r: (1 if r.parsing_status == "approved" else 0, len(r.raw_extracted_text or "")),
            reverse=True,
        )[0]
        upload_pts = 30.0
        approved_pts = 30.0 if best_res.parsing_status == "approved" else 10.0
        text_len = len((best_res.raw_extracted_text or "").strip())
        text_pts = min(text_len / 1200.0, 1.0) * 25.0
        parsed_pts = 15.0 if best_res.parsed_entities_json else 0.0
        resume_pct = round(min(100.0, upload_pts + approved_pts + text_pts + parsed_pts), 1)
        resume_evidence = (
            f"Active resume '{best_res.file_name}' ({best_res.parsing_status}, {text_len} extracted chars)."
        )

    # 6. Mock Interview Performance (default 12)
    w_mock = weights["mock_interview_performance"]
    mock_present = len(completed_mocks) > 0
    if not mock_present:
        mock_pct = 0.0
        mock_evidence = "No completed mock interview sessions yet."
        missing_data_fields.append("Mock Interview Practice History")
        limitations.append("Mock interview score is 0 due to zero completed practice sessions, not measured performance.")
    else:
        mock_scores = [float(s.evaluation.overall_score) for s in completed_mocks]
        avg_mock = sum(mock_scores) / len(mock_scores)
        consistency_bonus = min(len(completed_mocks) * 4.0, 12.0)
        mock_pct = round(min(100.0, (avg_mock * 0.88) + consistency_bonus), 1)
        mock_evidence = f"{len(completed_mocks)} completed mock interview(s), average score {avg_mock:.1f}/100."

    # 7. Aptitude & Technical Assessment Performance (default 10)
    w_assess = weights["aptitude_technical_assessment"]
    assess_mocks = [
        s for s in completed_mocks
        if s.category in (MockInterviewCategory.APTITUDE, MockInterviewCategory.TECHNICAL)
    ]
    assess_present = len(assess_mocks) > 0
    if not assess_present:
        assess_pct = 0.0
        assess_evidence = "No Aptitude or Technical assessments completed yet."
        missing_data_fields.append("Aptitude & Technical Assessments")
        limitations.append("Aptitude and technical assessment indicator reflects unattempted practice assessments.")
    else:
        a_scores = [float(s.evaluation.overall_score) for s in assess_mocks]
        avg_assess = sum(a_scores) / len(a_scores)
        has_both = (
            any(s.category == MockInterviewCategory.APTITUDE for s in assess_mocks)
            and any(s.category == MockInterviewCategory.TECHNICAL for s in assess_mocks)
        )
        breadth_bonus = 10.0 if has_both else 0.0
        assess_pct = round(min(100.0, (avg_assess * 0.90) + breadth_bonus), 1)
        assess_evidence = f"{len(assess_mocks)} aptitude/technical assessment(s), average score {avg_assess:.1f}/100."

    # 8. Profile Completeness (default 10) — non-academic links & institutional contact fields
    w_profile = weights["profile_completeness"]
    profile_checks = [
        bool(user.full_name and user.full_name.strip()),
        bool(user.email and user.email.strip()),
        bool(user.phone and user.phone.strip()),
        bool(user.department_id or getattr(user, "department", None)),
        bool(profile.roll_number and profile.roll_number.strip()),
        bool(profile.graduation_year),
        bool(profile.linkedin_url and profile.linkedin_url.strip()),
        bool((profile.github_url and profile.github_url.strip()) or (profile.portfolio_url and profile.portfolio_url.strip())),
    ]
    passed_profile_checks = sum(1 for c in profile_checks if c)
    profile_present = passed_profile_checks >= 3
    profile_pct = round((passed_profile_checks / len(profile_checks)) * 100.0, 1)
    profile_evidence = f"{passed_profile_checks}/{len(profile_checks)} core contact & developer portfolio fields populated."
    if not profile.linkedin_url or not (profile.github_url or profile.portfolio_url):
        missing_data_fields.append("GitHub / LinkedIn / Portfolio Links")

    raw_specs = [
        ("verified_skills", "Verified Skill Coverage", w_skills, skills_pct, skill_data_present, skills_evidence, None),
        ("project_portfolio", "Project Portfolio Quality", w_projects, projects_pct, proj_present, proj_evidence, None),
        (
            "internship_experience",
            "Internship & Experience Profile",
            w_exp,
            exp_pct,
            exp_present,
            exp_evidence,
            "Optional for freshers; unrecorded experience is treated as missing data.",
        ),
        ("certifications", "Relevant Certifications", w_cert, cert_pct, cert_present, cert_evidence, None),
        ("resume_quality", "Resume Quality & Completeness", w_resume, resume_pct, res_present, resume_evidence, None),
        (
            "mock_interview_performance",
            "Mock Interview Performance",
            w_mock,
            mock_pct,
            mock_present,
            mock_evidence,
            "Based on completed AI Mock Interview Studio practice sessions." if mock_present else "No sessions attempted yet.",
        ),
        (
            "aptitude_technical_assessment",
            "Aptitude & Technical Assessment",
            w_assess,
            assess_pct,
            assess_present,
            assess_evidence,
            "Derived from completed Technical & Aptitude assessment sessions." if assess_present else "No assessments attempted yet.",
        ),
        ("profile_completeness", "Profile Completeness", w_profile, profile_pct, profile_present, profile_evidence, None),
    ]

    indicators: List[ReadinessIndicatorScore] = []
    total_weighted = 0.0
    for key, label, weight_val, raw_pct, present, evidence, note in raw_specs:
        weighted_pts = round((raw_pct / 100.0) * weight_val, 2)
        total_weighted += weighted_pts
        indicators.append(
            ReadinessIndicatorScore(
                key=key,
                label=label,
                weight=round(weight_val, 2),
                raw_score_pct=round(raw_pct, 1),
                weighted_points=weighted_pts,
                status=_indicator_status(raw_pct, present),  # type: ignore[arg-type]
                data_present=present,
                evidence_summary=evidence,
                limitation_note=note,
            )
        )

    overall_score = round(min(100.0, max(0.0, total_weighted)), 2)

    diagnostics = {
        "matched_job_skills": matched_job_skills,
        "missing_mandatory_skills": missing_mand_skills,
        "missing_preferred_skills": missing_pref_skills,
        "verified_skills_count": verified_count,
        "total_skills_count": len(skills),
        "projects_count": len(projects),
        "completed_mock_interviews": len(completed_mocks),
        "has_approved_resume": has_approved_resume,
    }
    return overall_score, indicators, missing_data_fields, limitations, remaining_skill_gaps, diagnostics


def _build_academic_summary(user: User, profile: StudentProfile) -> ReadOnlyAcademicSummary:
    dept_name = user.department.name if getattr(user, "department", None) else None
    return ReadOnlyAcademicSummary(
        cgpa=float(profile.cgpa) if profile.cgpa is not None else None,
        active_backlogs=int(profile.active_backlogs or 0),
        total_backlogs=int(profile.total_backlogs or 0),
        graduation_year=profile.graduation_year,
        department_name=dept_name,
        is_placement_ready_flag=bool(profile.is_placement_ready),
    )


async def _load_student_readiness_entities(
    current_user: User,
    db: AsyncSession,
) -> Tuple[StudentProfile, List[Resume], List[MockInterviewSession]]:
    if (
        current_user.role != UserRole.STUDENT
        and current_user.email != "maheshwarijaya03@gmail.com"
        and current_user.role != UserRole.ADMIN
    ):
        raise AuthorizationException("Only registered students can access personal readiness predictions.")

    prof_stmt = (
        select(StudentProfile)
        .where(StudentProfile.user_id == current_user.id)
        .options(
            selectinload(StudentProfile.user).selectinload(User.department),
            selectinload(StudentProfile.skills),
            selectinload(StudentProfile.projects),
            selectinload(StudentProfile.experiences),
            selectinload(StudentProfile.certifications),
        )
    )
    profile = (await db.execute(prof_stmt)).scalar_one_or_none()
    if not profile:
        raise AppException(
            "Student academic profile is not configured.",
            status_code=400,
            code="STUDENT_PROFILE_REQUIRED",
        )

    res_stmt = (
        select(Resume)
        .where(Resume.student_id == profile.id, Resume.is_active.is_(True))
        .order_by(Resume.updated_at.desc())
    )
    resumes = list((await db.execute(res_stmt)).scalars().all())

    mock_stmt = (
        select(MockInterviewSession)
        .where(MockInterviewSession.student_id == profile.id)
        .options(selectinload(MockInterviewSession.evaluation))
        .order_by(MockInterviewSession.created_at.desc())
    )
    mock_sessions = list((await db.execute(mock_stmt)).scalars().all())

    return profile, resumes, mock_sessions


async def _load_visible_job(job_id: int, current_user: User, db: AsyncSession) -> Job:
    stmt = (
        select(Job)
        .where(Job.id == job_id, Job.is_active.is_(True))
        .options(
            selectinload(Job.company),
            selectinload(Job.skills),
            selectinload(Job.eligible_departments).selectinload(JobEligibleDepartment.department),
        )
    )
    job = (await db.execute(stmt)).scalar_one_or_none()
    if not job:
        raise EntityNotFoundException("Job", job_id, code="JOB_NOT_FOUND")
    if job.status != JobStatus.PUBLISHED:
        raise AppException("Target job must be published.", status_code=400, code="JOB_NOT_PUBLISHED")
    if job.institution_id is not None and job.institution_id != current_user.institution_id:
        raise AuthorizationException("Cannot evaluate readiness against another institution's exclusive job.")
    return job


async def _generate_personalized_recommendations(
    indicators: List[ReadinessIndicatorScore],
    missing_mandatory_skills: List[str],
    missing_preferred_skills: List[str],
    target_role: Optional[str],
    use_ai: bool,
    department_name: Optional[str] = None,
    department_code: Optional[str] = None,
) -> Tuple[List[ReadinessRecommendationItem], Optional[AIUsageMetadata]]:
    weak_labels = [
        f"{ind.label} ({ind.raw_score_pct:.0f}%, status={ind.status})"
        for ind in indicators
        if ind.raw_score_pct < 75.0 or not ind.data_present
    ]
    user_prompt = (
        f"<STUDENT_DEPARTMENT>{department_name or 'General Engineering'} ({department_code or ''})</STUDENT_DEPARTMENT>\n"
        f"<TARGET_ROLE>{target_role or 'Campus Placement Roles'}</TARGET_ROLE>\n"
        f"<MISSING_MANDATORY_SKILLS>{', '.join(missing_mandatory_skills) if missing_mandatory_skills else 'None'}</MISSING_MANDATORY_SKILLS>\n"
        f"<MISSING_PREFERRED_SKILLS>{', '.join(missing_preferred_skills) if missing_preferred_skills else 'None'}</MISSING_PREFERRED_SKILLS>\n"
        f"<WEAK_OR_MISSING_INDICATORS>{'; '.join(weak_labels) if weak_labels else 'All indicators >= 75%'}</WEAK_OR_MISSING_INDICATORS>\n"
        f"Provide actionable preparation suggestions matching the schema."
    )

    ai_output: Optional[ReadinessRecommendationsAIOutput] = None
    usage: Optional[AIUsageMetadata] = None

    if use_ai:
        try:
            provider = get_ai_provider()
            ai_output, usage = await provider.generate_structured(
                schema=ReadinessRecommendationsAIOutput,
                system_instruction=RECOMMENDATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.25,
                max_output_tokens=1400,
            )
        except AIServiceError as exc:
            logger.warning("AI readiness recommendation fallback activated: %s", exc)
            ai_output = generate_mock_readiness_recommendations(user_prompt)
            usage = AIUsageMetadata(
                provider="deterministic-fallback",
                model="readiness-rule-engine-v1",
                is_mock=True,
            )
    else:
        ai_output = generate_mock_readiness_recommendations(user_prompt)
        usage = AIUsageMetadata(
            provider="deterministic-rule-engine",
            model="readiness-rule-engine-v1",
            is_mock=True,
        )

    items: List[ReadinessRecommendationItem] = []
    for idx, rec in enumerate((ai_output.recommendations if ai_output else []), start=1):
        items.append(
            ReadinessRecommendationItem(
                id=f"rec-{idx}",
                title=rec.title.strip(),
                description=rec.description.strip(),
                category=rec.category,
                priority=rec.priority,
                estimated_impact=rec.estimated_impact.strip(),
                completed=False,
                completed_at=None,
            )
        )
    return items, usage


def _map_snapshot_response(
    snap: ReadinessSnapshot,
    score_delta: Optional[float] = None,
    usage: Optional[AIUsageMetadata] = None,
) -> ReadinessSnapshotResponse:
    recs = [
        ReadinessRecommendationItem.model_validate(item)
        for item in (snap.recommendations_json or [])
    ]
    completed_cnt = sum(1 for r in recs if r.completed)
    indicators = [
        ReadinessIndicatorScore.model_validate(item)
        for item in (snap.indicators_json or [])
    ]
    academic_summary = ReadOnlyAcademicSummary.model_validate(snap.academic_summary_json or {})
    job_title = snap.job.title if getattr(snap, "job", None) else None

    return ReadinessSnapshotResponse(
        id=snap.id,
        student_id=snap.student_id,
        job_id=snap.job_id,
        job_title=job_title,
        target_role=snap.target_role,
        formula_version=snap.formula_version,
        overall_score=round(float(snap.overall_score), 2),
        category=snap.category,
        category_label=CATEGORY_LABELS[snap.category],
        score_delta_from_previous=score_delta,
        weights=dict(snap.weights_json or {}),
        indicators=indicators,
        academic_summary=academic_summary,
        missing_data_fields=list(snap.missing_data_fields_json or []),
        limitations=list(snap.limitations_json or []),
        remaining_skill_gaps=list(snap.remaining_skill_gaps_json or []),
        recommendations=recs,
        completed_recommendations_count=completed_cnt,
        total_recommendations_count=len(recs),
        ai_provider=snap.ai_provider,
        ai_model=snap.ai_model,
        transparency_notice=snap.transparency_notice or READINESS_TRANSPARENCY_NOTICE,
        category_definitions=list(DEFAULT_CATEGORY_DEFINITIONS),
        usage=usage,
        calculated_at=snap.calculated_at,
    )


async def calculate_and_save_readiness_snapshot(
    req: ReadinessCalculateRequest,
    current_user: User,
    db: AsyncSession,
) -> ReadinessSnapshotResponse:
    profile, resumes, mock_sessions = await _load_student_readiness_entities(current_user, db)

    job: Optional[Job] = None
    if req.job_id is not None:
        job = await _load_visible_job(req.job_id, current_user, db)

    weights = (req.custom_weights or ReadinessIndicatorWeights()).normalized_dict()
    (
        overall_score,
        indicators,
        missing_data_fields,
        limitations,
        remaining_skill_gaps,
        diagnostics,
    ) = _compute_readiness_indicators(
        user=current_user,
        profile=profile,
        resumes=resumes,
        mock_sessions=mock_sessions,
        weights=weights,
        job=job,
    )

    category, _ = classify_readiness_category(overall_score)
    academic_summary = _build_academic_summary(current_user, profile)

    effective_role = (
        req.target_role.strip()
        if req.target_role and req.target_role.strip()
        else (job.title if job else None)
    )
    dept_obj = getattr(current_user, "department", None)
    recommendations, usage = await _generate_personalized_recommendations(
        indicators=indicators,
        missing_mandatory_skills=diagnostics["missing_mandatory_skills"],
        missing_preferred_skills=diagnostics["missing_preferred_skills"],
        target_role=effective_role,
        use_ai=req.include_ai_recommendations,
        department_name=getattr(dept_obj, "name", None),
        department_code=getattr(dept_obj, "code", None),
    )

    # Fetch previous latest score for delta calculation
    prev_stmt = (
        select(ReadinessSnapshot)
        .where(ReadinessSnapshot.student_id == profile.id)
        .order_by(ReadinessSnapshot.calculated_at.desc(), ReadinessSnapshot.id.desc())
        .limit(1)
    )
    prev_snap = (await db.execute(prev_stmt)).scalar_one_or_none()
    score_delta = (
        round(overall_score - float(prev_snap.overall_score), 2)
        if prev_snap is not None
        else None
    )

    now_utc = datetime.now(timezone.utc)
    snap = ReadinessSnapshot(
        student_id=profile.id,
        job_id=job.id if job else None,
        target_role=effective_role,
        formula_version=READINESS_FORMULA_VERSION,
        overall_score=overall_score,
        category=category,
        weights_json=weights,
        indicators_json=[ind.model_dump() for ind in indicators],
        academic_summary_json=academic_summary.model_dump(),
        missing_data_fields_json=missing_data_fields,
        limitations_json=limitations,
        remaining_skill_gaps_json=remaining_skill_gaps,
        recommendations_json=[rec.model_dump(mode="json") for rec in recommendations],
        ai_provider=usage.provider if usage else None,
        ai_model=usage.model if usage else None,
        transparency_notice=READINESS_TRANSPARENCY_NOTICE,
        calculated_at=now_utc,
    )
    snap.job = job
    db.add(snap)
    await db.commit()

    return _map_snapshot_response(snap, score_delta=score_delta, usage=usage)


async def get_student_readiness_overview(
    current_user: User,
    db: AsyncSession,
) -> ReadinessSnapshotResponse:
    """Return latest readiness snapshot, computing an initial baseline snapshot if none exists."""
    profile, _, _ = await _load_student_readiness_entities(current_user, db)
    stmt = (
        select(ReadinessSnapshot)
        .where(ReadinessSnapshot.student_id == profile.id)
        .options(selectinload(ReadinessSnapshot.job))
        .order_by(ReadinessSnapshot.calculated_at.desc(), ReadinessSnapshot.id.desc())
        .limit(2)
    )
    rows = list((await db.execute(stmt)).scalars().all())
    if not rows:
        return await calculate_and_save_readiness_snapshot(
            req=ReadinessCalculateRequest(include_ai_recommendations=True),
            current_user=current_user,
            db=db,
        )

    latest = rows[0]
    delta = (
        round(float(latest.overall_score) - float(rows[1].overall_score), 2)
        if len(rows) >= 2
        else None
    )
    return _map_snapshot_response(latest, score_delta=delta)


async def get_student_readiness_history(
    current_user: User,
    db: AsyncSession,
) -> ReadinessHistoryResponse:
    profile, _, _ = await _load_student_readiness_entities(current_user, db)
    stmt = (
        select(ReadinessSnapshot)
        .where(ReadinessSnapshot.student_id == profile.id)
        .options(selectinload(ReadinessSnapshot.job))
        .order_by(ReadinessSnapshot.calculated_at.asc(), ReadinessSnapshot.id.asc())
    )
    chrono = list((await db.execute(stmt)).scalars().all())
    if not chrono:
        return ReadinessHistoryResponse()

    trend: List[ReadinessHistoryPoint] = []
    mapped_desc: List[ReadinessSnapshotResponse] = []
    prev_score: Optional[float] = None
    total_completed_recs = 0

    for snap in chrono:
        curr = round(float(snap.overall_score), 2)
        delta = round(curr - prev_score, 2) if prev_score is not None else None
        prev_score = curr
        mapped = _map_snapshot_response(snap, score_delta=delta)
        mapped_desc.append(mapped)
        total_completed_recs = max(total_completed_recs, mapped.completed_recommendations_count)
        target_label = mapped.job_title or mapped.target_role or "General Campus Readiness"
        trend.append(
            ReadinessHistoryPoint(
                snapshot_id=mapped.id,
                formula_version=mapped.formula_version,
                overall_score=mapped.overall_score,
                category=mapped.category,
                category_label=mapped.category_label,
                score_delta=delta,
                completed_recommendations_count=mapped.completed_recommendations_count,
                total_recommendations_count=mapped.total_recommendations_count,
                remaining_skill_gaps_count=len(mapped.remaining_skill_gaps),
                target_label=target_label,
                calculated_at=mapped.calculated_at,
            )
        )

    mapped_desc.reverse()
    scores = [p.overall_score for p in trend]
    latest_resp = mapped_desc[0]
    net_change = round(scores[-1] - scores[0], 2) if len(scores) >= 2 else None

    return ReadinessHistoryResponse(
        total_snapshots=len(trend),
        latest_score=scores[-1],
        best_score=max(scores),
        net_change=net_change,
        total_completed_recommendations=latest_resp.completed_recommendations_count,
        remaining_skill_gaps=latest_resp.remaining_skill_gaps,
        snapshots=mapped_desc,
        trend=trend,
    )


async def toggle_recommendation_completion(
    snapshot_id: int,
    recommendation_id: str,
    completed: bool,
    current_user: User,
    db: AsyncSession,
) -> ReadinessSnapshotResponse:
    profile, _, _ = await _load_student_readiness_entities(current_user, db)
    stmt = (
        select(ReadinessSnapshot)
        .where(ReadinessSnapshot.id == snapshot_id)
        .options(selectinload(ReadinessSnapshot.job))
    )
    snap = (await db.execute(stmt)).scalar_one_or_none()
    if not snap:
        raise EntityNotFoundException("ReadinessSnapshot", snapshot_id, code="READINESS_SNAPSHOT_NOT_FOUND")
    if snap.student_id != profile.id:
        raise AuthorizationException("You may only update recommendations on your own readiness snapshots.")

    updated_list: List[Dict[str, Any]] = []
    found = False
    now_iso = datetime.now(timezone.utc).isoformat()
    for item in (snap.recommendations_json or []):
        entry = dict(item)
        if entry.get("id") == recommendation_id:
            found = True
            entry["completed"] = completed
            entry["completed_at"] = now_iso if completed else None
        updated_list.append(entry)

    if not found:
        raise EntityNotFoundException("ReadinessRecommendation", recommendation_id, code="RECOMMENDATION_NOT_FOUND")

    snap.recommendations_json = updated_list
    await db.commit()
    return _map_snapshot_response(snap)


async def evaluate_job_specific_readiness(
    req: JobReadinessCheckRequest,
    current_user: User,
    db: AsyncSession,
) -> JobReadinessCheckResponse:
    """
    Job-specific readiness diagnostic reusing the existing deterministic eligibility engine
    and compatibility engine while keeping academic eligibility separate from preparation readiness.
    """
    profile, resumes, mock_sessions = await _load_student_readiness_entities(current_user, db)

    job: Optional[Job] = None
    if req.job_id is not None:
        job = await _load_visible_job(req.job_id, current_user, db)

    weights = (req.custom_weights or ReadinessIndicatorWeights()).normalized_dict()
    (
        readiness_score,
        indicators,
        missing_data_fields,
        limitations,
        _,
        diagnostics,
    ) = _compute_readiness_indicators(
        user=current_user,
        profile=profile,
        resumes=resumes,
        mock_sessions=mock_sessions,
        weights=weights,
        job=job,
    )
    readiness_cat, readiness_cat_label = classify_readiness_category(readiness_score)

    # Academic Eligibility & Compatibility Engine Reuse
    is_eligible: Optional[bool] = None
    elig_reasons: List[str] = []
    elig_passed: List[str] = []
    elig_failed: List[str] = []
    compat_score: Optional[float] = None
    matched_skills: List[str] = diagnostics["matched_job_skills"]
    missing_mand: List[str] = diagnostics["missing_mandatory_skills"]
    missing_pref: List[str] = diagnostics["missing_preferred_skills"]

    if job is not None:
        skill_names = [s.skill_name for s in (profile.skills or [])]
        elig_res = evaluate_student_job_eligibility(
            job=job,
            student_user=current_user,
            student_profile=profile,
            student_skill_names=skill_names,
        )
        is_eligible = elig_res.is_eligible
        elig_reasons = elig_res.reasons
        elig_passed = elig_res.passed_criteria
        elig_failed = elig_res.failed_criteria

        (
            compat_score,
            _,
            engine_matched,
            engine_missing_mand,
            engine_rec_pref,
            _,
            _,
        ) = calculate_compatibility_score(
            job=job,
            student_user=current_user,
            student_profile=profile,
            approved_skills=profile.skills or [],
            approved_projects=profile.projects or [],
            approved_experiences=profile.experiences or [],
            approved_certifications=profile.certifications or [],
        )
        matched_skills = engine_matched
        missing_mand = engine_missing_mand
        missing_pref = engine_rec_pref

    # Compute skill alignment percentage cleanly
    if job is not None and (job.skills or []):
        total_job_skills = len(job.skills)
        skill_alignment_pct = round((len(matched_skills) / max(1, total_job_skills)) * 100.0, 1)
    else:
        skill_ind = next((i for i in indicators if i.key == "verified_skills"), None)
        skill_alignment_pct = skill_ind.raw_score_pct if skill_ind else 0.0

    # Portfolio gaps
    portfolio_gaps: List[str] = []
    if diagnostics["projects_count"] == 0:
        portfolio_gaps.append("No hands-on projects recorded to demonstrate applied skills.")
    elif diagnostics["projects_count"] < 2:
        portfolio_gaps.append("Add at least 1 more documented project with clear tech stack and outcome.")
    if not diagnostics["has_approved_resume"]:
        portfolio_gaps.append("No approved active resume linked yet.")
    if not (profile.github_url or profile.portfolio_url):
        portfolio_gaps.append("Add GitHub or portfolio URL so project code/architecture can be reviewed.")

    # Interview prep gaps
    interview_gaps: List[str] = []
    completed_mocks = [
        s for s in mock_sessions
        if s.status == MockInterviewStatus.COMPLETED and s.evaluation is not None
    ]
    if not completed_mocks:
        interview_gaps.append("Zero completed mock interviews — run a Technical or Project-Based session first.")
    else:
        cats_done = {s.category for s in completed_mocks}
        if MockInterviewCategory.TECHNICAL not in cats_done:
            interview_gaps.append("No Technical mock interview completed yet.")
        if MockInterviewCategory.BEHAVIORAL not in cats_done and MockInterviewCategory.HR not in cats_done:
            interview_gaps.append("No Behavioral or HR practice round completed yet.")
        avg_mock = sum(float(s.evaluation.overall_score) for s in completed_mocks) / len(completed_mocks)
        if avg_mock < 70.0:
            interview_gaps.append(f"Average mock interview score is {avg_mock:.1f}/100 — target >= 75/100 before interviews.")

    target_label = (
        f"{job.title} ({job.company.name if job.company else 'Employer'})"
        if job is not None
        else (req.target_role or "Target Role")
    )
    recommendations, _ = await _generate_personalized_recommendations(
        indicators=indicators,
        missing_mandatory_skills=missing_mand,
        missing_preferred_skills=missing_pref,
        target_role=target_label,
        use_ai=True,
    )

    return JobReadinessCheckResponse(
        job_id=job.id if job else None,
        target_label=target_label,
        company_name=job.company.name if (job and job.company) else None,
        academic_eligibility_checked=job is not None,
        is_academically_eligible=is_eligible,
        eligibility_reasons=elig_reasons,
        eligibility_passed_criteria=elig_passed,
        eligibility_failed_criteria=elig_failed,
        skill_alignment_pct=skill_alignment_pct,
        deterministic_compatibility_score=compat_score,
        matched_skills=matched_skills,
        missing_mandatory_skills=missing_mand,
        missing_preferred_skills=missing_pref,
        portfolio_gaps=portfolio_gaps,
        interview_preparation_gaps=interview_gaps,
        readiness_score=readiness_score,
        readiness_category=readiness_cat,
        readiness_category_label=readiness_cat_label,
        recommendations=recommendations,
        missing_data_fields=missing_data_fields,
        limitations=limitations,
    )


async def get_tpo_readiness_analytics(
    current_user: User,
    db: AsyncSession,
    department_id: Optional[int] = None,
    graduation_year: Optional[int] = None,
    category: Optional[ReadinessCategory] = None,
    skill_category: Optional[str] = None,
) -> TpoReadinessAnalyticsResponse:
    """
    Aggregated institutional readiness analytics for TPOs / institutional staff.
    Enforces strict institution-level isolation, never ranks or auto-rejects students,
    and leaves official academic eligibility untouched.
    """
    if current_user.role not in (UserRole.TPO, UserRole.ADMIN):
        raise AuthorizationException("Only authorized TPO or Administrator staff may access cohort readiness analytics.")

    institution_id = current_user.institution_id or 1

    stmt = (
        select(StudentProfile)
        .join(User, StudentProfile.user_id == User.id)
        .where(
            User.institution_id == institution_id,
            User.role == UserRole.STUDENT,
            User.is_active.is_(True),
        )
        .options(
            selectinload(StudentProfile.user).selectinload(User.department),
            selectinload(StudentProfile.skills),
            selectinload(StudentProfile.projects),
            selectinload(StudentProfile.experiences),
            selectinload(StudentProfile.certifications),
            selectinload(StudentProfile.resumes),
            selectinload(StudentProfile.mock_interview_sessions).selectinload(MockInterviewSession.evaluation),
        )
        .order_by(User.full_name.asc(), StudentProfile.roll_number.asc())
    )
    all_profiles = list((await db.execute(stmt)).scalars().all())

    # Collect available filter metadata across entire institution cohort
    dept_map: Dict[str, str] = {}
    batch_set = set()
    skill_cat_set = set()
    for prof in all_profiles:
        dept = prof.user.department if prof.user else None
        if dept:
            dept_map[str(dept.id)] = f"{dept.code} - {dept.name}"
        if prof.graduation_year:
            batch_set.add(int(prof.graduation_year))
        for sk in (prof.skills or []):
            if sk.category:
                skill_cat_set.add(sk.category.lower())

    default_weights = ReadinessIndicatorWeights().normalized_dict()

    # Evaluate each student deterministically & apply permitted filters
    evaluated_rows: List[Tuple[StudentProfile, float, ReadinessCategory, List[str], Dict[str, Any]]] = []
    for prof in all_profiles:
        u = prof.user
        if not u:
            continue
        if department_id is not None and u.department_id != department_id:
            continue
        if graduation_year is not None and prof.graduation_year != graduation_year:
            continue
        if skill_category:
            target_sc = skill_category.strip().lower()
            if not any((s.category or "").lower() == target_sc for s in (prof.skills or [])):
                continue

        overall, _, missing_fields, _, _, diag = _compute_readiness_indicators(
            user=u,
            profile=prof,
            resumes=list(prof.resumes or []),
            mock_sessions=list(prof.mock_interview_sessions or []),
            weights=default_weights,
        )
        cat, _ = classify_readiness_category(overall)
        if category is not None and cat != category:
            continue

        evaluated_rows.append((prof, overall, cat, missing_fields, diag))

    total_evaluated = len(evaluated_rows)
    if total_evaluated == 0:
        return TpoReadinessAnalyticsResponse(
            institution_id=institution_id,
            available_departments=[{"id": k, "label": v} for k, v in sorted(dept_map.items(), key=lambda x: x[1])],
            available_batches=sorted(batch_set),
            available_skill_categories=sorted(skill_cat_set),
        )

    avg_readiness = round(sum(row[1] for row in evaluated_rows) / total_evaluated, 1)
    ready_count = sum(
        1 for row in evaluated_rows
        if row[2] in (ReadinessCategory.EXCELLENT_PREPARATION, ReadinessCategory.PLACEMENT_READY)
    )
    ready_pct = round((ready_count / total_evaluated) * 100.0, 1)
    missing_data_profiles = sum(1 for row in evaluated_rows if len(row[3]) > 0)

    # Category Distribution
    cat_counts = {c: 0 for c in ReadinessCategory}
    for _, _, cat, _, _ in evaluated_rows:
        cat_counts[cat] += 1
    category_distribution = [
        TpoCategoryDistributionItem(
            category=c,
            label=CATEGORY_LABELS[c],
            student_count=cat_counts[c],
            percentage=round((cat_counts[c] / total_evaluated) * 100.0, 1),
        )
        for c in ReadinessCategory
    ]

    # Department Aggregation
    dept_buckets: Dict[Optional[int], List[Tuple[StudentProfile, float, ReadinessCategory]]] = defaultdict(list)
    for prof, score, cat, _, _ in evaluated_rows:
        dept_buckets[prof.user.department_id if prof.user else None].append((prof, score, cat))

    department_stats: List[TpoDepartmentReadinessStat] = []
    for d_id, items in dept_buckets.items():
        first_dept = items[0][0].user.department if items[0][0].user else None
        d_code = first_dept.code if first_dept else "GEN"
        d_name = first_dept.name if first_dept else "General / Unassigned"
        d_avg = round(sum(x[1] for x in items) / len(items), 1)
        d_ready = sum(1 for x in items if x[2] in (ReadinessCategory.EXCELLENT_PREPARATION, ReadinessCategory.PLACEMENT_READY))
        department_stats.append(
            TpoDepartmentReadinessStat(
                department_id=d_id,
                department_code=d_code,
                department_name=d_name,
                student_count=len(items),
                average_readiness_score=d_avg,
                placement_ready_count=d_ready,
                needs_attention_count=len(items) - d_ready,
            )
        )
    department_stats.sort(key=lambda d: d.department_code)

    # Batch Aggregation
    batch_buckets: Dict[int, List[Tuple[float, ReadinessCategory]]] = defaultdict(list)
    for prof, score, cat, _, _ in evaluated_rows:
        batch_buckets[int(prof.graduation_year or 2026)].append((score, cat))

    batch_stats: List[TpoBatchReadinessStat] = []
    for yr in sorted(batch_buckets.keys()):
        b_items = batch_buckets[yr]
        b_avg = round(sum(x[0] for x in b_items) / len(b_items), 1)
        b_ready = sum(1 for x in b_items if x[1] in (ReadinessCategory.EXCELLENT_PREPARATION, ReadinessCategory.PLACEMENT_READY))
        batch_stats.append(
            TpoBatchReadinessStat(
                graduation_year=yr,
                student_count=len(b_items),
                average_readiness_score=b_avg,
                excellent_or_ready_pct=round((b_ready / len(b_items)) * 100.0, 1),
            )
        )

    # Skill Category Aggregation across evaluated cohort
    sc_students: Dict[str, set] = defaultdict(set)
    sc_verified_cnt: Dict[str, int] = defaultdict(int)
    for prof, _, _, _, _ in evaluated_rows:
        for sk in (prof.skills or []):
            sc_key = (sk.category or "technical").lower()
            sc_students[sc_key].add(prof.id)
            if sk.is_verified:
                sc_verified_cnt[sc_key] += 1

    skill_category_stats = [
        TpoSkillCategoryStat(
            skill_category=sc,
            students_with_skill_count=len(student_ids),
            verified_skills_count=sc_verified_cnt[sc],
            cohort_coverage_pct=round((len(student_ids) / total_evaluated) * 100.0, 1),
        )
        for sc, student_ids in sorted(sc_students.items(), key=lambda x: len(x[1]), reverse=True)
    ]

    # Alphabetical (strictly non-ranking) permitted student overview rows
    student_rows: List[TpoStudentReadinessRow] = []
    for prof, score, cat, missing_fields, diag in evaluated_rows:
        u = prof.user
        dept = u.department if u else None
        completeness_note = (
            "All tracked preparation sections have data."
            if not missing_fields
            else f"Incomplete sections ({len(missing_fields)}): {', '.join(missing_fields[:2])}"
        )
        student_rows.append(
            TpoStudentReadinessRow(
                student_id=prof.id,
                full_name=u.full_name if u else prof.roll_number,
                roll_number=prof.roll_number,
                department_code=dept.code if dept else "GEN",
                department_name=dept.name if dept else "General",
                graduation_year=int(prof.graduation_year),
                cgpa=float(prof.cgpa) if prof.cgpa is not None else None,
                active_backlogs=int(prof.active_backlogs or 0),
                readiness_score=score,
                category=cat,
                category_label=CATEGORY_LABELS[cat],
                verified_skills_count=diag["verified_skills_count"],
                projects_count=diag["projects_count"],
                completed_mock_interviews=diag["completed_mock_interviews"],
                has_approved_resume=diag["has_approved_resume"],
                missing_data_count=len(missing_fields),
                data_completeness_note=completeness_note,
            )
        )

    return TpoReadinessAnalyticsResponse(
        institution_id=institution_id,
        total_students_evaluated=total_evaluated,
        cohort_average_readiness=avg_readiness,
        placement_ready_or_above_count=ready_count,
        placement_ready_or_above_pct=ready_pct,
        profiles_with_missing_data_count=missing_data_profiles,
        category_distribution=category_distribution,
        department_stats=department_stats,
        batch_stats=batch_stats,
        skill_category_stats=skill_category_stats,
        available_departments=[{"id": k, "label": v} for k, v in sorted(dept_map.items(), key=lambda x: x[1])],
        available_batches=sorted(batch_set),
        available_skill_categories=sorted(skill_cat_set),
        students=student_rows,
    )

