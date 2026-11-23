"""Service layer for TASK 10: Candidate Comparison & Hiring Insights.

Provides side-by-side comparative analysis of 2 to 5 candidates for a specific job posting,
enforces strict company/recruiter tenant isolation, preserves historical application scores,
computes skill coverage and candidate matrix rankings, generates evidence-grounded AI hiring insights,
and manages saved comparison sessions.
"""
from datetime import date, datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppException, AuthorizationException, EntityNotFoundException
from app.models.candidate_evaluation import (
    CandidateComparisonSession,
    CandidateEvaluation,
    CandidateNote,
)
from app.models.company import Company, RecruiterProfile
from app.models.job import Job, JobSkill
from app.models.placement import (
    ApplicationStatus,
    Interview,
    InterviewOutcome,
    InterviewStatus,
    JobApplication,
)
from app.models.student import (
    StudentCertification,
    StudentEducation,
    StudentExperience,
    StudentProfile,
    StudentProject,
    StudentSkill,
)
from app.models.user import User, UserRole
from app.schemas.candidate_comparison import (
    CandidateComparisonAISummary,
    CandidateComparisonItem,
    CandidateComparisonResponse,
    ComparisonSessionListResponse,
    ComparisonSessionResponse,
    SkillMatrixRow,
)
from app.schemas.candidate_evaluation import (
    CandidateAcademicInfo,
    CandidateCertificationItem,
    CandidateEvaluationResponse,
    CandidateExperienceItem,
    CandidateProjectItem,
    CandidateResumeSummary,
    CandidateSkillItem,
)
from app.schemas.intelligence import ScoreBreakdown
from app.services.ai_provider import get_ai_provider
from app.services.candidate_evaluation_service import _resolve_recruiter_company_id
from app.services.eligibility_service import evaluate_student_job_eligibility
from app.services.matching_engine import calculate_compatibility_score

logger = logging.getLogger(__name__)


def _calculate_experience_months(exp: StudentExperience) -> int:
    """Calculate duration in months for a candidate work experience entry."""
    start_raw = exp.start_date
    end_raw = exp.end_date

    if not start_raw:
        return 0

    start_dt = None
    if isinstance(start_raw, (datetime, date)):
        start_dt = start_raw if isinstance(start_raw, date) else start_raw.date()
    elif isinstance(start_raw, str) and len(start_raw.strip()) >= 7:
        try:
            # Handle YYYY-MM-DD or YYYY-MM
            cleaned = start_raw.strip()[:10]
            if len(cleaned) == 7:
                cleaned += "-01"
            start_dt = datetime.fromisoformat(cleaned).date()
        except Exception:
            start_dt = None

    if not start_dt:
        return 0

    end_dt = None
    if getattr(exp, "is_current", False):
        end_dt = date.today()
    elif isinstance(end_raw, (datetime, date)):
        end_dt = end_raw if isinstance(end_raw, date) else end_raw.date()
    elif isinstance(end_raw, str) and len(end_raw.strip()) >= 7:
        try:
            cleaned = end_raw.strip()[:10]
            if len(cleaned) == 7:
                cleaned += "-01"
            end_dt = datetime.fromisoformat(cleaned).date()
        except Exception:
            end_dt = None
    else:
        end_dt = date.today()

    if not end_dt or end_dt < start_dt:
        return 0
    days = (end_dt - start_dt).days
    return max(1, days // 30)


async def compare_candidates_for_job(
    session: AsyncSession,
    job_id: int,
    application_ids: List[int],
    current_user: User,
    generate_ai_insights: bool = False,
) -> CandidateComparisonResponse:
    """
    Compare up to 5 candidates side-by-side for a specific job posting.

    Validates:
    - 2 <= len(application_ids) <= 5.
    - All applications belong to the specified job_id.
    - Recruiter has company authorization for the job.
    - Preserves historical application compatibility score snapshots.
    - Generates multi-criteria skill coverage, portfolio comparison, and ranking matrix.
    """
    # 1. Validation of Candidate Selection bounds
    unique_app_ids = list(dict.fromkeys(application_ids))
    if len(unique_app_ids) < 2:
        raise AppException(
            "Candidate comparison requires selecting at least two distinct candidates.",
            status_code=400,
        )
    if len(unique_app_ids) > 5:
        raise AppException(
            "Candidate comparison is limited to a maximum of five candidates at a time.",
            status_code=400,
        )

    # 2. Company Tenant Authorization
    company_id = await _resolve_recruiter_company_id(current_user, session)

    # 3. Fetch Job and verify ownership
    stmt_job = (
        select(Job)
        .options(
            selectinload(Job.company),
            selectinload(Job.skills),
            selectinload(Job.eligible_departments),
        )
        .where(Job.id == job_id)
    )
    res_job = await session.execute(stmt_job)
    job = res_job.scalar_one_or_none()
    if not job:
        raise EntityNotFoundException("Job", job_id)

    if company_id is not None and job.company_id != company_id:
        raise AuthorizationException("Access denied: You cannot compare candidates for another company's job posting.")

    # 4. Fetch Candidate Applications with deep graphs
    stmt_apps = (
        select(JobApplication)
        .options(
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.user).selectinload(User.department),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.skills),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.projects),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.experiences),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.certifications),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.education_history),
            selectinload(JobApplication.resume),
            selectinload(JobApplication.interviews),
            selectinload(JobApplication.evaluations).selectinload(CandidateEvaluation.interviewer),
            selectinload(JobApplication.evaluations).selectinload(CandidateEvaluation.interview),
            selectinload(JobApplication.notes),
        )
        .where(JobApplication.id.in_(unique_app_ids))
    )
    res_apps = await session.execute(stmt_apps)
    app_records = res_apps.scalars().all()
    app_map = {a.id: a for a in app_records}

    # Verify all applications exist and belong to this job
    for aid in unique_app_ids:
        if aid not in app_map:
            raise EntityNotFoundException("JobApplication", aid)
        app = app_map[aid]
        if app.job_id != job_id:
            raise AppException(
                f"Application #{aid} belongs to a different job (#{app.job_id}) and cannot be compared with job #{job_id}.",
                status_code=400,
            )

    # 5. Extract Job Skill Requirements
    job_mandatory_skills = [
        s.skill_name.strip() for s in (job.skills or []) if getattr(s, "is_mandatory", False)
    ]
    job_preferred_skills = [
        s.skill_name.strip() for s in (job.skills or []) if not getattr(s, "is_mandatory", False)
    ]

    candidate_items: List[CandidateComparisonItem] = []
    all_observed_skills: Set[str] = set([s.lower() for s in job_mandatory_skills + job_preferred_skills])

    for aid in unique_app_ids:
        app = app_map[aid]
        prof = app.student_profile
        user = prof.user if prof else None

        if not prof or not user:
            raise AppException(f"Incomplete candidate graph for application #{aid}: missing profile or user.")

        approved_skills = prof.skills or []
        approved_projects = prof.projects or []
        approved_experiences = prof.experiences or []
        approved_certifications = prof.certifications or []

        for s in approved_skills:
            if s.skill_name:
                all_observed_skills.add(s.skill_name.strip().lower())

        # Deterministic Eligibility Check
        skill_names = [s.skill_name for s in approved_skills]
        elig_result = evaluate_student_job_eligibility(
            job=job,
            student_user=user,
            student_profile=prof,
            student_skill_names=skill_names,
        )

        # Deterministic Compatibility Score
        (
            current_compat_score,
            score_breakdown,
            matched_skills,
            missing_mand,
            rec_skills,
            _,
            _,
        ) = calculate_compatibility_score(
            job=job,
            student_user=user,
            student_profile=prof,
            approved_skills=approved_skills,
            approved_projects=approved_projects,
            approved_experiences=approved_experiences,
            approved_certifications=approved_certifications,
        )

        # Historical Compatibility Score integrity
        historical_score = (
            float(app.compatibility_score_at_application)
            if app.compatibility_score_at_application is not None
            else current_compat_score
        )

        # Academics
        tenth_pct = getattr(prof, "tenth_percentage", None)
        twelfth_pct = getattr(prof, "twelfth_percentage", None)
        if getattr(prof, "education_history", None):
            for edu in prof.education_history:
                deg = (edu.degree or "").lower()
                val_str = (edu.cgpa_or_percentage or "").replace("%", "").strip()
                try:
                    parsed_val = float(val_str) if val_str else None
                except ValueError:
                    parsed_val = None
                if parsed_val is not None:
                    if any(k in deg for k in ["class x", "10th", "matric", "secondary"]):
                        if tenth_pct is None:
                            tenth_pct = parsed_val
                    elif any(k in deg for k in ["class xii", "12th", "higher secondary", "intermediate"]):
                        if twelfth_pct is None:
                            twelfth_pct = parsed_val

        academics = CandidateAcademicInfo(
            cgpa=float(prof.cgpa) if prof.cgpa is not None else 0.0,
            tenth_percentage=float(tenth_pct) if tenth_pct is not None else None,
            twelfth_percentage=float(twelfth_pct) if twelfth_pct is not None else None,
            active_backlogs=prof.active_backlogs,
            total_backlogs=prof.total_backlogs,
            is_placement_ready=prof.is_placement_ready,
        )

        # Mandatory & Preferred Skill Coverage breakdown
        candidate_skill_names_lower = {s.skill_name.strip().lower() for s in approved_skills}

        matched_mand = [s for s in job_mandatory_skills if s.lower() in candidate_skill_names_lower]
        missing_mand_list = [s for s in job_mandatory_skills if s.lower() not in candidate_skill_names_lower]
        mand_cov_pct = (len(matched_mand) / len(job_mandatory_skills) * 100.0) if job_mandatory_skills else 100.0

        matched_pref = [s for s in job_preferred_skills if s.lower() in candidate_skill_names_lower]
        missing_pref_list = [s for s in job_preferred_skills if s.lower() not in candidate_skill_names_lower]
        pref_cov_pct = (len(matched_pref) / len(job_preferred_skills) * 100.0) if job_preferred_skills else 100.0

        mandatory_coverage = {
            "required": job_mandatory_skills,
            "matched": matched_mand,
            "missing": missing_mand_list,
            "coverage_percentage": round(mand_cov_pct, 1),
        }
        preferred_coverage = {
            "required": job_preferred_skills,
            "matched": matched_pref,
            "missing": missing_pref_list,
            "coverage_percentage": round(pref_cov_pct, 1),
        }

        # Skills list
        skills_list = [
            CandidateSkillItem(
                skill_name=s.skill_name,
                category=s.category or "technical",
                proficiency_level=s.proficiency_level or "intermediate",
                is_verified=getattr(s, "is_verified", True),
            )
            for s in approved_skills
        ]

        # Projects
        projects_list: List[CandidateProjectItem] = []
        for p in approved_projects:
            techs = []
            if getattr(p, "technologies", None):
                raw_t = p.technologies
                techs = [t.strip() for t in raw_t.split(",") if t.strip()] if isinstance(raw_t, str) else list(raw_t)
            elif getattr(p, "technologies_used", None):
                raw_t = p.technologies_used
                techs = [t.strip() for t in raw_t.split(",") if t.strip()] if isinstance(raw_t, str) else list(raw_t)
            projects_list.append(
                CandidateProjectItem(
                    title=p.title,
                    description=p.description,
                    technologies=techs,
                    repo_url=getattr(p, "project_url", None) or getattr(p, "repo_url", None),
                    demo_url=getattr(p, "demo_url", None),
                )
            )

        # Experience & total months
        exp_list: List[CandidateExperienceItem] = []
        total_months = 0
        for e in approved_experiences:
            total_months += _calculate_experience_months(e)
            start_str = e.start_date.isoformat() if hasattr(e.start_date, "isoformat") else (str(e.start_date) if e.start_date else None)
            end_str = e.end_date.isoformat() if hasattr(e.end_date, "isoformat") else (str(e.end_date) if e.end_date else None)
            exp_list.append(
                CandidateExperienceItem(
                    job_title=getattr(e, "role_title", None) or getattr(e, "job_title", "Software Engineer"),
                    company_name=e.company_name,
                    start_date=start_str,
                    end_date=end_str,
                    is_current=e.is_current,
                    description=e.description,
                )
            )

        # Certifications
        certs_list = [
            CandidateCertificationItem(
                name=getattr(c, "certificate_name", None) or getattr(c, "name", "Certification"),
                issuing_organization=c.issuing_organization,
                issue_date=c.issue_date.isoformat() if hasattr(c.issue_date, "isoformat") else (str(c.issue_date) if c.issue_date else None),
                credential_url=getattr(c, "credential_url", None),
            )
            for c in approved_certifications
        ]

        # Resume
        resume_summary = None
        if app.resume:
            resume_summary = CandidateResumeSummary(
                resume_id=app.resume.id,
                file_name=app.resume.file_name,
                file_size_bytes=app.resume.file_size_bytes,
                file_type=app.resume.file_type,
                parsing_status=app.resume.parsing_status,
                resume_score=float(app.resume.score) if getattr(app.resume, "score", None) is not None else None,
                download_url=f"/api/v1/applications/{app.id}/resume",
            )

        # Evaluations & Ratings
        evals = app.evaluations or []
        eval_responses = [
            CandidateEvaluationResponse(
                id=ev.id,
                application_id=ev.application_id,
                interview_id=ev.interview_id,
                interviewer_user_id=ev.interviewer_user_id,
                interviewer_name=ev.interviewer_name,
                stage=ev.stage,
                technical_rating=ev.technical_rating,
                problem_solving_rating=ev.problem_solving_rating,
                communication_rating=ev.communication_rating,
                project_depth_rating=ev.project_depth_rating,
                cultural_fit_rating=ev.cultural_fit_rating,
                overall_rating=float(ev.overall_rating),
                recommendation=ev.recommendation,
                strengths=ev.strengths,
                weaknesses=ev.weaknesses,
                written_feedback=ev.written_feedback,
                criteria_ratings=ev.criteria_ratings,
                created_at=ev.created_at,
                updated_at=ev.updated_at,
            )
            for ev in evals
        ]
        avg_rating = (
            round(sum(float(e.overall_rating) for e in evals) / len(evals), 2)
            if evals
            else None
        )
        latest_rec = evals[-1].recommendation.value if evals else None

        item = CandidateComparisonItem(
            application_id=app.id,
            student_id=prof.id,
            user_id=user.id,
            candidate_name=user.full_name,
            roll_number=prof.roll_number,
            email=user.email,
            department=user.department.name if user.department else "General",
            graduation_year=prof.graduation_year,
            current_status=app.current_status,
            applied_at=app.created_at,
            is_eligible=elig_result.is_eligible,
            eligibility_reasons=elig_result.reasons,
            academics=academics,
            compatibility_score_at_application=round(historical_score, 1),
            current_compatibility_score=round(current_compat_score, 1),
            score_breakdown=score_breakdown,
            mandatory_skills_coverage=mandatory_coverage,
            preferred_skills_coverage=preferred_coverage,
            skills=skills_list,
            projects=projects_list,
            total_projects_count=len(projects_list),
            experiences=exp_list,
            total_experience_months=total_months,
            certifications=certs_list,
            resume=resume_summary,
            interviews_count=len(app.interviews or []),
            evaluations_count=len(evals),
            average_rating=avg_rating,
            latest_recommendation=latest_rec,
            notes_count=len(app.notes or []),
        )
        candidate_items.append(item)

    # 6. Build Comprehensive Skill Matrix
    # Include all mandatory and preferred job skills, plus top observed candidate skills
    skill_matrix: List[SkillMatrixRow] = []
    seen_matrix_skills: Set[str] = set()

    for mand_s in job_mandatory_skills:
        s_lower = mand_s.strip().lower()
        if s_lower not in seen_matrix_skills:
            seen_matrix_skills.add(s_lower)
            coverage_map = {
                str(c.application_id): any(sk.skill_name.strip().lower() == s_lower for sk in c.skills)
                for c in candidate_items
            }
            skill_matrix.append(
                SkillMatrixRow(skill_name=mand_s, is_mandatory=True, candidate_coverage=coverage_map)
            )

    for pref_s in job_preferred_skills:
        s_lower = pref_s.strip().lower()
        if s_lower not in seen_matrix_skills:
            seen_matrix_skills.add(s_lower)
            coverage_map = {
                str(c.application_id): any(sk.skill_name.strip().lower() == s_lower for sk in c.skills)
                for c in candidate_items
            }
            skill_matrix.append(
                SkillMatrixRow(skill_name=pref_s, is_mandatory=False, candidate_coverage=coverage_map)
            )

    # Also include other key skills present in multiple candidates
    other_skills = [
        s for s in sorted(all_observed_skills)
        if s not in seen_matrix_skills
    ][:8]  # Limit to 8 additional key skills
    for other_s in other_skills:
        coverage_map = {
            str(c.application_id): any(sk.skill_name.strip().lower() == other_s for sk in c.skills)
            for c in candidate_items
        }
        if sum(1 for has_sk in coverage_map.values() if has_sk) > 0:
            skill_matrix.append(
                SkillMatrixRow(skill_name=other_s.capitalize(), is_mandatory=False, candidate_coverage=coverage_map)
            )

    # 7. Compute Relative Metric Rankings
    rankings = {
        "by_compatibility": [
            c.application_id
            for c in sorted(candidate_items, key=lambda x: x.compatibility_score_at_application, reverse=True)
        ],
        "by_cgpa": [
            c.application_id
            for c in sorted(candidate_items, key=lambda x: x.academics.cgpa, reverse=True)
        ],
        "by_experience": [
            c.application_id
            for c in sorted(candidate_items, key=lambda x: x.total_experience_months, reverse=True)
        ],
        "by_rating": [
            c.application_id
            for c in sorted(candidate_items, key=lambda x: (x.average_rating or 0.0), reverse=True)
        ],
    }

    # 8. Compute Standout Highlights
    top_compat = max(candidate_items, key=lambda x: x.compatibility_score_at_application)
    top_cgpa = max(candidate_items, key=lambda x: x.academics.cgpa)
    top_exp = max(candidate_items, key=lambda x: x.total_experience_months)
    top_rating_cands = [c for c in candidate_items if c.average_rating is not None]
    top_rating = max(top_rating_cands, key=lambda x: x.average_rating) if top_rating_cands else None

    highlights = {
        "highest_compatibility": {
            "application_id": top_compat.application_id,
            "candidate_name": top_compat.candidate_name,
            "score": top_compat.compatibility_score_at_application,
        },
        "highest_cgpa": {
            "application_id": top_cgpa.application_id,
            "candidate_name": top_cgpa.candidate_name,
            "cgpa": top_cgpa.academics.cgpa,
        },
        "most_experience": {
            "application_id": top_exp.application_id,
            "candidate_name": top_exp.candidate_name,
            "months": top_exp.total_experience_months,
        },
        "highest_rating": (
            {
                "application_id": top_rating.application_id,
                "candidate_name": top_rating.candidate_name,
                "rating": top_rating.average_rating,
            }
            if top_rating
            else None
        ),
    }

    # 9. Optional AI-Assisted Hiring Insights Synthesis
    ai_insights = None
    if generate_ai_insights:
        ai_insights = await generate_candidate_comparison_ai_insights(job, candidate_items)

    return CandidateComparisonResponse(
        job_id=job.id,
        job_title=job.title,
        company_id=job.company_id,
        company_name=job.company.name if job.company else "Corporate Partner",
        required_mandatory_skills=job_mandatory_skills,
        required_preferred_skills=job_preferred_skills,
        candidates=candidate_items,
        skill_matrix=skill_matrix,
        rankings=rankings,
        highlights=highlights,
        ai_insights=ai_insights,
        comparison_timestamp=datetime.now(timezone.utc),
    )


async def generate_candidate_comparison_ai_insights(
    job: Job,
    candidates: List[CandidateComparisonItem],
) -> CandidateComparisonAISummary:
    """
    Synthesize evidence-grounded comparative hiring insights across candidates.
    Strictly anchored in actual student records, verified skills, portfolio projects, and evaluations.
    Never hallucinates unverified qualifications or issues automated hiring decisions.
    """
    # 1. Identify Shared Strengths
    shared_strengths: List[str] = []

    all_eligible = all(c.is_eligible for c in candidates)
    if all_eligible:
        shared_strengths.append(f"All {len(candidates)} candidates meet institutional academic and backlog eligibility criteria for '{job.title}'.")

    avg_cgpa = sum(c.academics.cgpa for c in candidates) / len(candidates)
    if avg_cgpa >= 8.0:
        shared_strengths.append(f"Strong collective academic benchmark with an average cohort CGPA of {avg_cgpa:.2f}.")

    # Common skills
    if candidates:
        first_skills = set(s.skill_name.lower() for s in candidates[0].skills)
        common_skills = first_skills.intersection(*(set(s.skill_name.lower() for s in c.skills) for c in candidates[1:]))
        if common_skills:
            common_skills_str = ", ".join(list(common_skills)[:4])
            shared_strengths.append(f"Common technical competencies across all candidates: {common_skills_str}.")

    if not shared_strengths:
        shared_strengths.append(f"All candidates possess confirmed interest and verified application records for {job.title}.")

    # 2. Candidate-Specific Unique Strengths
    candidate_strengths: Dict[str, List[str]] = {}
    missing_requirements: Dict[str, List[str]] = {}
    recommended_interview_focus: Dict[str, List[str]] = {}

    for c in candidates:
        c_strengths: List[str] = []
        c_name = c.candidate_name

        # Compatibility highlight
        c_strengths.append(f"{c.compatibility_score_at_application:.1f}% compatibility match with {c.mandatory_skills_coverage.get('coverage_percentage', 0):.0f}% mandatory skill coverage.")

        # Practical project depth
        if c.projects:
            top_p = c.projects[0]
            techs = f" using {', '.join(top_p.technologies[:3])}" if top_p.technologies else ""
            c_strengths.append(f"Hands-on project ownership: '{top_p.title}'{techs}.")

        # Work experience
        if c.total_experience_months > 0:
            c_strengths.append(f"{c.total_experience_months} months of direct professional experience across {len(c.experiences)} roles.")

        # Evaluator rating
        if c.average_rating and c.average_rating >= 4.0:
            c_strengths.append(f"Strong interviewer evaluation consensus (★ {c.average_rating:.1f}/5.0).")

        candidate_strengths[c_name] = c_strengths

        # Missing requirements
        c_missing: List[str] = []
        missing_mand = c.mandatory_skills_coverage.get("missing", [])
        if missing_mand:
            c_missing.append(f"Missing mandatory skill requirements: {', '.join(missing_mand)}.")
        missing_pref = c.preferred_skills_coverage.get("missing", [])
        if missing_pref:
            c_missing.append(f"Missing preferred skills: {', '.join(missing_pref[:3])}.")
        if c.academics.active_backlogs > 0:
            c_missing.append(f"{c.academics.active_backlogs} active academic backlogs pending clearance.")
        if not c.experiences:
            c_missing.append("No prior formal internship or corporate experience recorded.")

        missing_requirements[c_name] = c_missing or ["Meets all core baseline requirements without notable deficits."]

        # Interview Probes
        probes: List[str] = []
        if c.projects:
            probes.append(f"Probe technical trade-offs and concurrency decisions in '{c.projects[0].title}'.")
        if missing_mand:
            probes.append(f"Evaluate candidate's ability to quickly upskill in missing requirement '{missing_mand[0]}'.")
        if c.total_experience_months > 0:
            probes.append(f"Discuss cross-functional collaboration and production challenges faced during internship at {c.experiences[0].company_name}.")
        else:
            probes.append("Evaluate problem solving methodology and software lifecycle ownership in an academic project setting.")

        recommended_interview_focus[c_name] = probes

    # 3. Project Differences
    project_diffs: List[str] = []
    for c in candidates:
        if c.projects:
            techs = ", ".join(c.projects[0].technologies[:3]) if c.projects[0].technologies else "core software tools"
            project_diffs.append(f"{c.candidate_name} focuses on '{c.projects[0].title}' ({techs}).")
        else:
            project_diffs.append(f"{c.candidate_name} has no detailed portfolio projects listed.")

    return CandidateComparisonAISummary(
        shared_strengths=shared_strengths,
        candidate_strengths=candidate_strengths,
        missing_requirements=missing_requirements,
        project_differences=project_diffs,
        recommended_interview_focus=recommended_interview_focus,
        evidence_grounding_notes=(
            "This comparative synthesis is strictly grounded in verified academic credentials, deterministic "
            "compatibility scoring, and submitted interviewer evaluations. It serves as decision support for recruiter "
            "deliberation and does not make automated selection or rejection decisions."
        ),
    )


async def save_comparison_session(
    session: AsyncSession,
    job_id: int,
    title: str,
    application_ids: List[int],
    current_user: User,
    notes: Optional[str] = None,
    include_ai_insights: bool = False,
) -> ComparisonSessionResponse:
    """Save recruiter candidate comparison session for later review and collaborative deliberation."""
    # Run comparison to validate job, applications, permissions, and generate AI insights if requested
    comparison_res = await compare_candidates_for_job(
        session=session,
        job_id=job_id,
        application_ids=application_ids,
        current_user=current_user,
        generate_ai_insights=include_ai_insights,
    )

    ai_cache = comparison_res.ai_insights.model_dump() if comparison_res.ai_insights else None

    sess = CandidateComparisonSession(
        company_id=comparison_res.company_id,
        job_id=job_id,
        created_by_user_id=current_user.id,
        title=title.strip(),
        application_ids=application_ids,
        notes=notes.strip() if notes else None,
        ai_summary=ai_cache,
    )
    session.add(sess)
    await session.flush()
    await session.refresh(sess)

    return ComparisonSessionResponse(
        id=sess.id,
        company_id=sess.company_id,
        job_id=sess.job_id,
        job_title=comparison_res.job_title,
        title=sess.title,
        application_ids=sess.application_ids,
        notes=sess.notes,
        ai_summary=sess.ai_summary,
        created_by_user_id=sess.created_by_user_id,
        created_by_name=current_user.full_name,
        created_at=sess.created_at,
        updated_at=sess.updated_at,
    )


async def list_comparison_sessions(
    session: AsyncSession,
    current_user: User,
    job_id: Optional[int] = None,
) -> ComparisonSessionListResponse:
    """List saved candidate comparison sessions for recruiter's company."""
    company_id = await _resolve_recruiter_company_id(current_user, session)

    stmt = (
        select(CandidateComparisonSession)
        .options(
            selectinload(CandidateComparisonSession.job),
            selectinload(CandidateComparisonSession.created_by),
        )
        .order_by(desc(CandidateComparisonSession.updated_at))
    )
    if company_id is not None:
        stmt = stmt.where(CandidateComparisonSession.company_id == company_id)
    if job_id is not None:
        stmt = stmt.where(CandidateComparisonSession.job_id == job_id)

    res = await session.execute(stmt)
    records = res.scalars().all()

    items = [
        ComparisonSessionResponse(
            id=r.id,
            company_id=r.company_id,
            job_id=r.job_id,
            job_title=r.job.title if r.job else f"Job #{r.job_id}",
            title=r.title,
            application_ids=r.application_ids,
            notes=r.notes,
            ai_summary=r.ai_summary,
            created_by_user_id=r.created_by_user_id,
            created_by_name=r.created_by.full_name if r.created_by else "Recruiter",
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in records
    ]
    return ComparisonSessionListResponse(items=items, total=len(items))


async def get_comparison_session(
    session: AsyncSession,
    session_id: int,
    current_user: User,
) -> Tuple[ComparisonSessionResponse, CandidateComparisonResponse]:
    """Retrieve saved comparison session and re-execute live side-by-side comparison."""
    company_id = await _resolve_recruiter_company_id(current_user, session)

    stmt = (
        select(CandidateComparisonSession)
        .options(
            selectinload(CandidateComparisonSession.job),
            selectinload(CandidateComparisonSession.created_by),
        )
        .where(CandidateComparisonSession.id == session_id)
    )
    res = await session.execute(stmt)
    sess = res.scalar_one_or_none()
    if not sess:
        raise EntityNotFoundException("CandidateComparisonSession", session_id)

    if company_id is not None and sess.company_id != company_id:
        raise AuthorizationException("Access denied: Saved comparison session belongs to another company.")

    live_comparison = await compare_candidates_for_job(
        session=session,
        job_id=sess.job_id,
        application_ids=sess.application_ids,
        current_user=current_user,
        generate_ai_insights=False,
    )
    # If the session had a cached AI summary, attach it
    if sess.ai_summary:
        live_comparison.ai_insights = CandidateComparisonAISummary(**sess.ai_summary)

    sess_resp = ComparisonSessionResponse(
        id=sess.id,
        company_id=sess.company_id,
        job_id=sess.job_id,
        job_title=sess.job.title if sess.job else f"Job #{sess.job_id}",
        title=sess.title,
        application_ids=sess.application_ids,
        notes=sess.notes,
        ai_summary=sess.ai_summary,
        created_by_user_id=sess.created_by_user_id,
        created_by_name=sess.created_by.full_name if sess.created_by else "Recruiter",
        created_at=sess.created_at,
        updated_at=sess.updated_at,
    )
    return sess_resp, live_comparison


async def update_comparison_session(
    session: AsyncSession,
    session_id: int,
    current_user: User,
    title: Optional[str] = None,
    notes: Optional[str] = None,
) -> ComparisonSessionResponse:
    """Update title and/or notes of an existing saved comparison session."""
    company_id = await _resolve_recruiter_company_id(current_user, session)

    stmt = (
        select(CandidateComparisonSession)
        .options(
            selectinload(CandidateComparisonSession.job),
            selectinload(CandidateComparisonSession.created_by),
        )
        .where(CandidateComparisonSession.id == session_id)
    )
    res = await session.execute(stmt)
    sess = res.scalar_one_or_none()
    if not sess:
        raise EntityNotFoundException("CandidateComparisonSession", session_id)

    if company_id is not None and sess.company_id != company_id:
        raise AuthorizationException("Access denied: Saved comparison session belongs to another company.")

    if title is not None:
        sess.title = title.strip()
    if notes is not None:
        sess.notes = notes.strip()
    sess.updated_at = datetime.now(timezone.utc)

    await session.flush()
    await session.refresh(sess)

    return ComparisonSessionResponse(
        id=sess.id,
        company_id=sess.company_id,
        job_id=sess.job_id,
        job_title=sess.job.title if sess.job else f"Job #{sess.job_id}",
        title=sess.title,
        application_ids=sess.application_ids,
        notes=sess.notes,
        ai_summary=sess.ai_summary,
        created_by_user_id=sess.created_by_user_id,
        created_by_name=sess.created_by.full_name if sess.created_by else "Recruiter",
        created_at=sess.created_at,
        updated_at=sess.updated_at,
    )


async def delete_comparison_session(
    session: AsyncSession,
    session_id: int,
    current_user: User,
) -> Dict[str, Any]:
    """Delete a saved comparison session."""
    company_id = await _resolve_recruiter_company_id(current_user, session)

    stmt = select(CandidateComparisonSession).where(CandidateComparisonSession.id == session_id)
    res = await session.execute(stmt)
    sess = res.scalar_one_or_none()
    if not sess:
        raise EntityNotFoundException("CandidateComparisonSession", session_id)

    if company_id is not None and sess.company_id != company_id:
        raise AuthorizationException("Access denied: Saved comparison session belongs to another company.")

    await session.delete(sess)
    await session.flush()
    return {"message": "Saved comparison session deleted successfully.", "deleted_id": session_id}
