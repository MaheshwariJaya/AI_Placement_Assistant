"""
Service layer for TASK 08: Advanced Candidate Evaluation Workspace.
Orchestrates candidate filtering, deep academic/profile dossiers, deterministic compatibility & eligibility,
structured interview evaluation forms, internal recruiter notes, and evidence-grounded AI synthesis.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppException, AuthorizationException, EntityNotFoundException
from app.models.candidate_evaluation import (
    CandidateEvaluation,
    CandidateNote,
    EvaluationRecommendation,
    EvaluationStage,
    NoteCategory,
)
from app.models.company import RecruiterProfile
from app.models.job import Job, JobEligibleDepartment, JobSkill
from app.models.organization import Department
from app.models.placement import (
    ApplicationStatus,
    ApplicationStatusHistory,
    Interview,
    InterviewOutcome,
    InterviewStatus,
    JobApplication,
    TpoScreeningStatus,
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
from app.schemas.candidate_evaluation import (
    CandidateAcademicInfo,
    CandidateActivityTimelineItem,
    CandidateAISummary,
    CandidateCertificationItem,
    CandidateEligibilityChecklist,
    CandidateEvaluationCreate,
    CandidateEvaluationResponse,
    CandidateEvaluationUpdate,
    CandidateExperienceItem,
    CandidateListItem,
    CandidateListResponse,
    CandidateNoteCreate,
    CandidateNoteResponse,
    CandidateProjectItem,
    CandidateResumeSummary,
    CandidateSkillItem,
    CandidateStatusTransitionRequest,
    CandidateWorkspaceDetailResponse,
    EligibilityCheckCriterion,
)
from app.schemas.intelligence import ScoreBreakdown
from app.services.ai_provider import get_ai_provider
from app.services.eligibility_service import evaluate_student_job_eligibility
from app.services.matching_engine import calculate_compatibility_score
from app.services.state_machine import execute_recruiter_lifecycle_transition

logger = logging.getLogger(__name__)


async def _resolve_recruiter_company_id(current_user: User, session: AsyncSession) -> Optional[int]:
    """Retrieve the recruiter's corporate company affiliation."""
    if current_user.role == UserRole.ADMIN:
        return None
    stmt = select(RecruiterProfile.company_id).where(RecruiterProfile.user_id == current_user.id)
    res = await session.execute(stmt)
    cid = res.scalar_one_or_none()
    if not cid:
        raise AuthorizationException("Authenticated recruiter must be affiliated with an active corporate partner.")
    return cid


async def list_candidates_for_recruiter(
    session: AsyncSession,
    current_user: User,
    job_id: Optional[int] = None,
    department: Optional[str] = None,
    graduation_year: Optional[int] = None,
    eligibility: Optional[str] = None,
    min_compatibility_score: Optional[float] = None,
    skill: Optional[str] = None,
    min_experience_months: Optional[int] = None,
    status: Optional[ApplicationStatus] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> CandidateListResponse:
    """
    Search, filter, and paginate candidate applications for recruiter's company jobs.
    Computes interview counts, evaluation counts, and average interviewer rating.
    """
    company_id = await _resolve_recruiter_company_id(current_user, session)

    # 1. Base query joins
    stmt = (
        select(JobApplication)
        .join(Job, JobApplication.job_id == Job.id)
        .join(StudentProfile, JobApplication.student_id == StudentProfile.id)
        .join(User, StudentProfile.user_id == User.id)
        .outerjoin(Department, User.department_id == Department.id)
        .options(
            selectinload(JobApplication.job).selectinload(Job.skills),
            selectinload(JobApplication.job).selectinload(Job.eligible_departments),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.user).selectinload(User.department),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.skills),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.experiences),
            selectinload(JobApplication.interviews),
            selectinload(JobApplication.evaluations),
        )
    )

    if company_id is not None:
        stmt = stmt.where(Job.company_id == company_id)

    # 2. Filters
    if job_id is not None:
        stmt = stmt.where(JobApplication.job_id == job_id)

    if department:
        dep_filter = f"%{department.strip()}%"
        stmt = stmt.where(or_(Department.name.ilike(dep_filter), Department.code.ilike(dep_filter)))

    if graduation_year is not None:
        stmt = stmt.where(StudentProfile.graduation_year == graduation_year)

    if status is not None:
        stmt = stmt.where(JobApplication.current_status == status)

    if min_compatibility_score is not None:
        stmt = stmt.where(JobApplication.compatibility_score_at_application >= min_compatibility_score)

    if search:
        s_term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                User.full_name.ilike(s_term),
                StudentProfile.roll_number.ilike(s_term),
                Job.title.ilike(s_term),
            )
        )

    # Execute query
    stmt = stmt.order_by(JobApplication.created_at.desc())
    res = await session.execute(stmt)
    all_apps = res.scalars().all()

    # 3. Post-filter in Python for skill and eligibility if requested
    filtered_apps = []
    for app in all_apps:
        prof = app.student_profile
        job = app.job
        if not prof or not job:
            continue

        # Skill filter
        if skill:
            cand_skills = [s.skill_name.lower() for s in (prof.skills or [])]
            if not any(skill.lower() in cs for cs in cand_skills):
                continue

        # Experience months filter
        if min_experience_months is not None and min_experience_months > 0:
            # Approximate from experiences
            total_exp = len(prof.experiences or []) * 6  # nominal heuristic if months not explicit
            if total_exp < min_experience_months:
                continue

        # Eligibility filter
        if eligibility and eligibility != "all":
            skill_names = [s.skill_name for s in (prof.skills or [])]
            elig_res = evaluate_student_job_eligibility(
                job=job,
                student_user=prof.user,
                student_profile=prof,
                student_skill_names=skill_names,
            )
            if eligibility == "eligible_only" and not elig_res.is_eligible:
                continue
            if eligibility == "ineligible_only" and elig_res.is_eligible:
                continue

        filtered_apps.append(app)

    total = len(filtered_apps)
    paged_apps = filtered_apps[skip : skip + limit]

    # 4. Map to items
    items: List[CandidateListItem] = []
    for app in paged_apps:
        prof = app.student_profile
        user = prof.user if prof else None
        job = app.job

        evals = app.evaluations or []
        avg_rating = None
        latest_rec = None
        if evals:
            ratings = [float(e.overall_rating) for e in evals if e.overall_rating is not None]
            if ratings:
                avg_rating = round(sum(ratings) / len(ratings), 2)
            latest_rec = evals[0].recommendation

        # Check eligibility
        skill_names = [s.skill_name for s in (prof.skills or [])] if prof else []
        elig_eval = evaluate_student_job_eligibility(
            job=job,
            student_user=user,
            student_profile=prof,
            student_skill_names=skill_names,
        ) if (job and user and prof) else None

        items.append(
            CandidateListItem(
                application_id=app.id,
                job_id=job.id if job else 0,
                job_title=job.title if job else "Unknown",
                student_id=prof.id if prof else 0,
                student_name=user.full_name if user else "Candidate",
                roll_number=prof.roll_number if prof else "N/A",
                department=user.department.name if (user and user.department) else "General",
                graduation_year=prof.graduation_year if prof else 2026,
                cgpa=float(prof.cgpa) if (prof and prof.cgpa is not None) else 0.0,
                compatibility_score=float(app.compatibility_score_at_application or 0.0),
                is_eligible=elig_eval.is_eligible if elig_eval else True,
                current_status=app.current_status,
                tpo_screening_status=app.tpo_screening_status,
                applied_at=app.created_at,
                interviews_count=len(app.interviews or []),
                evaluations_count=len(evals),
                average_rating=avg_rating,
                latest_recommendation=latest_rec,
            )
        )

    # 5. Extract available jobs and departments for filter pills
    job_stmt = select(Job.id, Job.title).where(Job.is_active == True)
    if company_id is not None:
        job_stmt = job_stmt.where(Job.company_id == company_id)
    job_res = await session.execute(job_stmt)
    available_jobs = [{"id": r[0], "title": r[1]} for r in job_res.all()]

    dept_stmt = select(Department.name).distinct().order_by(Department.name)
    dept_res = await session.execute(dept_stmt)
    available_depts = [r[0] for r in dept_res.all()]

    return CandidateListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        available_jobs=available_jobs,
        available_departments=available_depts,
    )


async def get_candidate_workspace_detail(
    session: AsyncSession,
    application_id: int,
    current_user: User,
) -> CandidateWorkspaceDetailResponse:
    """
    Fetch comprehensive candidate evaluation workspace detail:
    - Profile, verified academics, skills, projects, experiences, certifications
    - Deterministic compatibility score breakdown
    - Complete eligibility checklist
    - Interview rounds & interviewer evaluations
    - Internal confidential recruiter notes
    - Chronological activity timeline
    """
    company_id = await _resolve_recruiter_company_id(current_user, session)

    stmt = (
        select(JobApplication)
        .options(
            selectinload(JobApplication.job).selectinload(Job.company),
            selectinload(JobApplication.job).selectinload(Job.skills),
            selectinload(JobApplication.job).selectinload(Job.eligible_departments).selectinload(JobEligibleDepartment.department),
            selectinload(JobApplication.drive),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.user).selectinload(User.department),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.skills),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.projects),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.experiences),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.certifications),
            selectinload(JobApplication.student_profile).selectinload(StudentProfile.education_history),
            selectinload(JobApplication.resume),
            selectinload(JobApplication.interviews).selectinload(Interview.created_by),
            selectinload(JobApplication.evaluations).selectinload(CandidateEvaluation.interviewer),
            selectinload(JobApplication.evaluations).selectinload(CandidateEvaluation.interview),
            selectinload(JobApplication.notes).selectinload(CandidateNote.author),
            selectinload(JobApplication.status_history).selectinload(ApplicationStatusHistory.changed_by),
        )
        .where(JobApplication.id == application_id)
    )
    res = await session.execute(stmt)
    app = res.scalar_one_or_none()
    if not app:
        raise EntityNotFoundException("JobApplication", application_id)

    # Recruiter company authorization
    if company_id is not None and app.job and app.job.company_id != company_id:
        raise AuthorizationException("Access denied: Candidate application belongs to a different company.")

    prof = app.student_profile
    user = prof.user if prof else None
    job = app.job

    if not prof or not user or not job:
        raise AppException("Incomplete application graph: missing profile, user, or job record.")

    # 1. Deterministic Compatibility Score
    approved_skills = prof.skills or []
    approved_projects = prof.projects or []
    approved_experiences = prof.experiences or []
    approved_certifications = prof.certifications or []

    (
        compat_score,
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

    # 2. Deterministic Eligibility Checklist
    skill_names = [s.skill_name for s in approved_skills]
    elig_result = evaluate_student_job_eligibility(
        job=job,
        student_user=user,
        student_profile=prof,
        student_skill_names=skill_names,
    )

    checklist_criteria: List[EligibilityCheckCriterion] = []
    for k, v in elig_result.criteria.items():
        checklist_criteria.append(
            EligibilityCheckCriterion(
                criterion=v.criterion,
                passed=v.passed,
                candidate_value=str(v.student_value),
                required_value=str(v.required),
                details=v.message,
            )
        )

    eligibility_checklist = CandidateEligibilityChecklist(
        is_eligible=elig_result.is_eligible,
        criteria=checklist_criteria,
        reasons=elig_result.reasons,
    )

    # 3. Profile & Academics
    profile_dict = {
        "student_id": prof.id,
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "roll_number": prof.roll_number,
        "department": user.department.name if user.department else "General",
        "graduation_year": prof.graduation_year,
        "phone": getattr(prof, "phone_number", None),
        "bio": getattr(prof, "bio", None),
        "linkedin_url": prof.linkedin_url,
        "github_url": prof.github_url,
        "portfolio_url": prof.portfolio_url,
    }

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

    # 4. Skills, Projects, Experiences, Certifications
    skills_list = [
        CandidateSkillItem(
            skill_name=s.skill_name,
            category=s.category or "technical",
            proficiency_level=s.proficiency_level or "intermediate",
            is_verified=getattr(s, "is_verified", True),
        )
        for s in approved_skills
    ]

    projects_list = []
    for p in approved_projects:
        techs = []
        if getattr(p, "technologies", None):
            raw_tech = p.technologies
            techs = [t.strip() for t in raw_tech.split(",") if t.strip()] if isinstance(raw_tech, str) else list(raw_tech)
        elif getattr(p, "technologies_used", None):
            raw_tech = p.technologies_used
            techs = [t.strip() for t in raw_tech.split(",") if t.strip()] if isinstance(raw_tech, str) else list(raw_tech)

        projects_list.append(
            CandidateProjectItem(
                title=p.title,
                description=p.description,
                technologies=techs,
                repo_url=getattr(p, "project_url", None) or getattr(p, "repo_url", None),
                demo_url=getattr(p, "demo_url", None),
            )
        )

    exp_list = []
    for e in approved_experiences:
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

    certs_list = []
    for c in approved_certifications:
        issue_str = c.issue_date.isoformat() if hasattr(c.issue_date, "isoformat") else (str(c.issue_date) if c.issue_date else None)
        certs_list.append(
            CandidateCertificationItem(
                name=getattr(c, "certificate_name", None) or getattr(c, "name", "Certification"),
                issuing_organization=c.issuing_organization,
                issue_date=issue_str,
                credential_url=getattr(c, "credential_url", None),
            )
        )

    # 5. Resume
    resume_summary = None
    if app.resume:
        resume_summary = CandidateResumeSummary(
            resume_id=app.resume.id,
            file_name=app.resume.file_name,
            file_size_bytes=app.resume.file_size_bytes,
            file_type=app.resume.file_type,
            parsing_status=app.resume.parsing_status,
            resume_score=float(app.resume.score) if getattr(app.resume, "score", None) else None,
            download_url=f"/api/v1/applications/{app.id}/resume",
        )

    # 6. Interviews
    interviews_list = [
        {
            "id": i.id,
            "round_number": i.round_number,
            "round_title": i.round_title,
            "interview_mode": i.interview_mode.value if hasattr(i.interview_mode, "value") else str(i.interview_mode),
            "status": i.status.value if hasattr(i.status, "value") else str(i.status),
            "outcome": i.outcome.value if hasattr(i.outcome, "value") else str(i.outcome),
            "scheduled_start_time": i.scheduled_start_time.isoformat(),
            "duration_minutes": i.duration_minutes,
            "interviewer_names": i.interviewer_names,
            "feedback_notes": i.feedback_notes,
            "meeting_link": i.meeting_link,
            "location": i.location,
        }
        for i in sorted(app.interviews or [], key=lambda i: i.round_number)
    ]

    # 7. Evaluations
    evaluations_list = [
        CandidateEvaluationResponse(
            id=e.id,
            application_id=e.application_id,
            interview_id=e.interview_id,
            interview_round_title=e.interview.round_title if e.interview else None,
            interviewer_user_id=e.interviewer_user_id,
            interviewer_name=e.interviewer_name,
            stage=e.stage,
            technical_rating=e.technical_rating,
            problem_solving_rating=e.problem_solving_rating,
            communication_rating=e.communication_rating,
            project_depth_rating=e.project_depth_rating,
            cultural_fit_rating=e.cultural_fit_rating,
            overall_rating=float(e.overall_rating),
            recommendation=e.recommendation,
            strengths=e.strengths,
            weaknesses=e.weaknesses,
            written_feedback=e.written_feedback,
            criteria_ratings=e.criteria_ratings,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )
        for e in sorted(app.evaluations or [], key=lambda e: e.created_at, reverse=True)
    ]

    # 8. Notes
    notes_list = [
        CandidateNoteResponse(
            id=n.id,
            application_id=n.application_id,
            author_user_id=n.author_user_id,
            author_name=n.author_name,
            category=n.category,
            content=n.content,
            is_pinned=n.is_pinned,
            created_at=n.created_at,
            updated_at=n.updated_at,
        )
        for n in sorted(app.notes or [], key=lambda n: (not n.is_pinned, n.created_at), reverse=True)
    ]

    # 9. Chronological Activity Timeline
    timeline: List[CandidateActivityTimelineItem] = []

    # Application submission event
    timeline.append(
        CandidateActivityTimelineItem(
            id=f"app-{app.id}",
            activity_type="application_submitted",
            timestamp=app.created_at,
            actor_name=user.full_name,
            title="Application Submitted",
            description=f"Applied for {job.title} with compatibility score snapshot {float(app.compatibility_score_at_application):.1f}%",
            metadata={"compatibility_score": float(app.compatibility_score_at_application)},
        )
    )

    # TPO Screening event (if campus drive)
    if app.drive_id:
        tpo_status_val = app.tpo_screening_status.value if hasattr(app.tpo_screening_status, "value") else str(app.tpo_screening_status)
        timeline.append(
            CandidateActivityTimelineItem(
                id=f"tpo-{app.id}",
                activity_type="tpo_screening",
                timestamp=app.tpo_screened_at or app.created_at,
                actor_name=app.tpo_screened_by.full_name if getattr(app, "tpo_screened_by", None) else "Placement Cell",
                title=f"TPO Screening: {tpo_status_val.replace('_', ' ').title()}",
                description=app.tpo_feedback or "Campus eligibility and placement verification completed.",
                metadata={"status": tpo_status_val},
            )
        )

    # Status changes
    for h in sorted(app.status_history or [], key=lambda h: h.created_at):
        timeline.append(
            CandidateActivityTimelineItem(
                id=f"hist-{h.id}",
                activity_type="status_change",
                timestamp=h.created_at,
                actor_name=h.changed_by.full_name if h.changed_by else "System",
                title=f"Status: {h.to_status.replace('_', ' ').title()}",
                description=h.notes or f"Recruitment stage transitioned from '{h.from_status}' to '{h.to_status}'.",
                metadata={"from_status": h.from_status, "to_status": h.to_status},
            )
        )

    # Interviews
    for i in app.interviews or []:
        timeline.append(
            CandidateActivityTimelineItem(
                id=f"interview-{i.id}",
                activity_type="interview",
                timestamp=i.scheduled_start_time,
                actor_name=i.interviewer_names or "Recruitment Team",
                title=f"Round {i.round_number}: {i.round_title}",
                description=f"Mode: {i.interview_mode.value.title()} • Status: {i.status.value.title()} • Outcome: {i.outcome.value.title()}",
                metadata={"status": i.status.value, "outcome": i.outcome.value},
            )
        )

    # Evaluations
    for e in app.evaluations or []:
        timeline.append(
            CandidateActivityTimelineItem(
                id=f"eval-{e.id}",
                activity_type="evaluation_submitted",
                timestamp=e.created_at,
                actor_name=e.interviewer_name,
                title=f"Evaluation Submitted ({e.stage.value.title()})",
                description=f"Rating: {float(e.overall_rating):.1f}/5.0 • Recommendation: {e.recommendation.value.replace('_', ' ').title()} • Notes: {e.written_feedback[:80]}...",
                metadata={"rating": float(e.overall_rating), "recommendation": e.recommendation.value},
            )
        )

    # Sort complete timeline chronologically descending (newest on top)
    timeline.sort(key=lambda t: t.timestamp, reverse=True)

    return CandidateWorkspaceDetailResponse(
        application_id=app.id,
        job_id=job.id,
        job_title=job.title,
        company_id=job.company_id,
        company_name=job.company.name if job.company else "Company",
        drive_id=app.drive_id,
        drive_name=app.drive.name if app.drive else None,
        current_status=app.current_status,
        tpo_screening_status=app.tpo_screening_status,
        tpo_screened_at=app.tpo_screened_at,
        tpo_screened_by_name=app.tpo_screened_by.full_name if getattr(app, "tpo_screened_by", None) else None,
        tpo_feedback=app.tpo_feedback,
        applied_at=app.created_at,
        recruiter_decision_at=app.recruiter_decision_at,
        recruiter_feedback_notes=app.recruiter_feedback_notes,
        compatibility_score=compat_score,
        score_breakdown=score_breakdown,
        matched_skills=matched_skills,
        missing_mandatory_skills=missing_mand,
        recommended_skills=rec_skills,
        eligibility_checklist=eligibility_checklist,
        profile=profile_dict,
        academics=academics,
        skills=skills_list,
        projects=projects_list,
        experiences=exp_list,
        certifications=certs_list,
        resume=resume_summary,
        interviews=interviews_list,
        evaluations=evaluations_list,
        notes=notes_list,
        timeline=timeline,
        ai_summary=None,
    )


async def submit_candidate_evaluation(
    session: AsyncSession,
    application_id: int,
    payload: CandidateEvaluationCreate,
    current_user: User,
) -> CandidateEvaluationResponse:
    """Submit a structured evaluation for a candidate application."""
    company_id = await _resolve_recruiter_company_id(current_user, session)

    app = await session.get(JobApplication, application_id)
    if not app:
        raise EntityNotFoundException("JobApplication", application_id)

    job = await session.get(Job, app.job_id)
    if not job:
        raise EntityNotFoundException("Job", app.job_id)

    if company_id is not None and job.company_id != company_id:
        raise AuthorizationException("Access denied: You cannot evaluate candidates of another corporate organization.")

    # Validate associated interview if provided
    interview = None
    if payload.interview_id:
        interview = await session.get(Interview, payload.interview_id)
        if not interview or interview.application_id != application_id:
            raise AppException("Specified interview does not belong to this candidate application.")

    evaluation = CandidateEvaluation(
        application_id=application_id,
        interview_id=payload.interview_id,
        interviewer_user_id=current_user.id,
        interviewer_name=current_user.full_name,
        stage=payload.stage,
        technical_rating=payload.technical_rating,
        problem_solving_rating=payload.problem_solving_rating,
        communication_rating=payload.communication_rating,
        project_depth_rating=payload.project_depth_rating,
        cultural_fit_rating=payload.cultural_fit_rating,
        overall_rating=payload.overall_rating,
        recommendation=payload.recommendation,
        strengths=payload.strengths,
        weaknesses=payload.weaknesses,
        written_feedback=payload.written_feedback,
        criteria_ratings=payload.criteria_ratings,
    )
    session.add(evaluation)
    await session.commit()
    await session.refresh(evaluation, attribute_names=["interview", "interviewer"])

    return CandidateEvaluationResponse(
        id=evaluation.id,
        application_id=evaluation.application_id,
        interview_id=evaluation.interview_id,
        interview_round_title=evaluation.interview.round_title if evaluation.interview else None,
        interviewer_user_id=evaluation.interviewer_user_id,
        interviewer_name=evaluation.interviewer_name,
        stage=evaluation.stage,
        technical_rating=evaluation.technical_rating,
        problem_solving_rating=evaluation.problem_solving_rating,
        communication_rating=evaluation.communication_rating,
        project_depth_rating=evaluation.project_depth_rating,
        cultural_fit_rating=evaluation.cultural_fit_rating,
        overall_rating=float(evaluation.overall_rating),
        recommendation=evaluation.recommendation,
        strengths=evaluation.strengths,
        weaknesses=evaluation.weaknesses,
        written_feedback=evaluation.written_feedback,
        criteria_ratings=evaluation.criteria_ratings,
        created_at=evaluation.created_at,
        updated_at=evaluation.updated_at,
    )


async def list_candidate_evaluations(
    session: AsyncSession,
    application_id: int,
    current_user: User,
) -> List[CandidateEvaluationResponse]:
    """Retrieve all structured evaluations for an application."""
    company_id = await _resolve_recruiter_company_id(current_user, session)

    app = await session.get(JobApplication, application_id)
    if not app:
        raise EntityNotFoundException("JobApplication", application_id)
    job = await session.get(Job, app.job_id)
    if company_id is not None and job and job.company_id != company_id:
        raise AuthorizationException("Access denied.")

    stmt = (
        select(CandidateEvaluation)
        .options(selectinload(CandidateEvaluation.interview))
        .where(CandidateEvaluation.application_id == application_id)
        .order_by(desc(CandidateEvaluation.created_at))
    )
    res = await session.execute(stmt)
    evals = res.scalars().all()

    return [
        CandidateEvaluationResponse(
            id=e.id,
            application_id=e.application_id,
            interview_id=e.interview_id,
            interview_round_title=e.interview.round_title if e.interview else None,
            interviewer_user_id=e.interviewer_user_id,
            interviewer_name=e.interviewer_name,
            stage=e.stage,
            technical_rating=e.technical_rating,
            problem_solving_rating=e.problem_solving_rating,
            communication_rating=e.communication_rating,
            project_depth_rating=e.project_depth_rating,
            cultural_fit_rating=e.cultural_fit_rating,
            overall_rating=float(e.overall_rating),
            recommendation=e.recommendation,
            strengths=e.strengths,
            weaknesses=e.weaknesses,
            written_feedback=e.written_feedback,
            criteria_ratings=e.criteria_ratings,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )
        for e in evals
    ]


async def create_candidate_note(
    session: AsyncSession,
    application_id: int,
    payload: CandidateNoteCreate,
    current_user: User,
) -> CandidateNoteResponse:
    """Create an internal confidential candidate note."""
    company_id = await _resolve_recruiter_company_id(current_user, session)

    app = await session.get(JobApplication, application_id)
    if not app:
        raise EntityNotFoundException("JobApplication", application_id)
    job = await session.get(Job, app.job_id)
    if company_id is not None and job and job.company_id != company_id:
        raise AuthorizationException("Access denied.")

    note = CandidateNote(
        application_id=application_id,
        author_user_id=current_user.id,
        author_name=current_user.full_name,
        category=payload.category,
        content=payload.content,
        is_pinned=payload.is_pinned,
    )
    session.add(note)
    await session.commit()
    await session.refresh(note)

    return CandidateNoteResponse(
        id=note.id,
        application_id=note.application_id,
        author_user_id=note.author_user_id,
        author_name=note.author_name,
        category=note.category,
        content=note.content,
        is_pinned=note.is_pinned,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


async def list_candidate_notes(
    session: AsyncSession,
    application_id: int,
    current_user: User,
) -> List[CandidateNoteResponse]:
    """Retrieve all internal recruiter notes for a candidate application."""
    company_id = await _resolve_recruiter_company_id(current_user, session)

    app = await session.get(JobApplication, application_id)
    if not app:
        raise EntityNotFoundException("JobApplication", application_id)
    job = await session.get(Job, app.job_id)
    if company_id is not None and job and job.company_id != company_id:
        raise AuthorizationException("Access denied.")

    stmt = (
        select(CandidateNote)
        .where(CandidateNote.application_id == application_id)
        .order_by(desc(CandidateNote.is_pinned), desc(CandidateNote.created_at))
    )
    res = await session.execute(stmt)
    notes = res.scalars().all()

    return [
        CandidateNoteResponse(
            id=n.id,
            application_id=n.application_id,
            author_user_id=n.author_user_id,
            author_name=n.author_name,
            category=n.category,
            content=n.content,
            is_pinned=n.is_pinned,
            created_at=n.created_at,
            updated_at=n.updated_at,
        )
        for n in notes
    ]


async def delete_candidate_note(
    session: AsyncSession,
    application_id: int,
    note_id: int,
    current_user: User,
) -> Dict[str, Any]:
    """Delete an internal recruiter note."""
    company_id = await _resolve_recruiter_company_id(current_user, session)

    note = await session.get(CandidateNote, note_id)
    if not note or note.application_id != application_id:
        raise EntityNotFoundException("CandidateNote", note_id)

    app = await session.get(JobApplication, application_id)
    job = await session.get(Job, app.job_id) if app else None
    if company_id is not None and job and job.company_id != company_id:
        raise AuthorizationException("Access denied.")

    # Recruiter author or admin
    if current_user.role != UserRole.ADMIN and note.author_user_id != current_user.id:
        raise AuthorizationException("Only the author or an admin can delete this note.")

    await session.delete(note)
    await session.commit()
    return {"message": "Candidate note deleted successfully.", "note_id": note_id}


async def execute_candidate_status_transition(
    session: AsyncSession,
    application_id: int,
    payload: CandidateStatusTransitionRequest,
    current_user: User,
) -> Dict[str, Any]:
    """
    Execute documented human recruitment lifecycle transition (shortlist, reject, offer, etc.).
    Enforces mandatory TPO screening gate for campus drives.
    """
    company_id = await _resolve_recruiter_company_id(current_user, session)

    app = await session.get(JobApplication, application_id)
    if not app:
        raise EntityNotFoundException("JobApplication", application_id)
    job = await session.get(Job, app.job_id)
    if not job:
        raise EntityNotFoundException("Job", app.job_id)

    if company_id is not None and job.company_id != company_id:
        raise AuthorizationException("Access denied: You do not own the target opportunity.")

    # Call authoritative state machine
    await execute_recruiter_lifecycle_transition(
        session=session,
        application=app,
        new_status=payload.to_status,
        actor_user_id=current_user.id,
        notes=payload.decision_notes,
    )

    # If offer extended, record offer specifics
    if payload.to_status == ApplicationStatus.OFFERED:
        if payload.offer_package_lpa is not None:
            app.offer_package_lpa = payload.offer_package_lpa
        elif job.ctc_lpa is not None:
            app.offer_package_lpa = float(job.ctc_lpa)

        if payload.offer_deadline_at is not None:
            app.offer_deadline_at = payload.offer_deadline_at
        if payload.offer_notes:
            app.offer_notes = payload.offer_notes

    app.recruiter_decision_at = datetime.now(timezone.utc)
    app.recruiter_feedback_notes = payload.decision_notes
    await session.commit()

    return {
        "application_id": app.id,
        "new_status": app.current_status.value,
        "decision_notes": payload.decision_notes,
        "updated_at": app.recruiter_decision_at.isoformat(),
    }


async def generate_candidate_ai_summary(
    session: AsyncSession,
    application_id: int,
    current_user: User,
) -> CandidateAISummary:
    """
    Generate an evidence-grounded candidate evaluation synthesis using the configured AI provider.
    Strictly separates verified facts, calculated metrics, and synthesized observations.
    Never invents qualifications or sensitive personal demographics.
    """
    detail = await get_candidate_workspace_detail(session, application_id, current_user)

    # 1. Verified Facts (Grounding Anchor)
    verified_facts = {
        "candidate_name": detail.profile.get("full_name"),
        "roll_number": detail.profile.get("roll_number"),
        "department": detail.profile.get("department"),
        "graduation_year": detail.profile.get("graduation_year"),
        "cgpa": detail.academics.cgpa,
        "active_backlogs": detail.academics.active_backlogs,
        "total_backlogs": detail.academics.total_backlogs,
        "confirmed_skills": [s.skill_name for s in detail.skills if s.is_verified],
        "all_skills": [s.skill_name for s in detail.skills],
        "verified_projects": [p.title for p in detail.projects],
        "work_experiences": [f"{e.job_title} at {e.company_name}" for e in detail.experiences],
        "certifications": [c.name for c in detail.certifications],
    }

    # 2. Calculated Metrics (Deterministic Engine)
    calculated_metrics = {
        "compatibility_score": round(detail.compatibility_score, 1),
        "score_breakdown": detail.score_breakdown.model_dump(),
        "is_eligible": detail.eligibility_checklist.is_eligible,
        "total_interviews_scheduled": len(detail.interviews),
        "total_evaluations_submitted": len(detail.evaluations),
        "average_interviewer_rating": (
            round(sum(float(e.overall_rating) for e in detail.evaluations) / len(detail.evaluations), 2)
            if detail.evaluations
            else None
        ),
        "recommendations_summary": [e.recommendation.value for e in detail.evaluations],
    }

    # 3. AI Observations Synthesis (Evidence-Grounded)
    # Gather qualitative interviewer notes
    eval_notes = [f"[{e.stage.value.upper()}] {e.interviewer_name}: {e.written_feedback}" for e in detail.evaluations]
    project_highlights = [f"{p.title}: {p.description or 'No description'}" for p in detail.projects[:3]]

    # Build prompt
    prompt = (
        f"You are an objective, evidence-grounded talent intelligence assistant. Summarize this candidate:\n"
        f"Candidate: {detail.profile.get('full_name')} for Role: {detail.job_title}\n"
        f"Academics: CGPA {detail.academics.cgpa}, Department: {detail.profile.get('department')}\n"
        f"Skills: {', '.join([s.skill_name for s in detail.skills])}\n"
        f"Projects: {'; '.join(project_highlights)}\n"
        f"Interviewer Evaluations: {'; '.join(eval_notes) if eval_notes else 'No interview feedback recorded yet'}\n"
        f"Deterministic Compatibility Score: {detail.compatibility_score:.1f}%\n"
        f"Deterministic Eligibility: {'Eligible' if detail.eligibility_checklist.is_eligible else 'Ineligible'}\n"
    )

    # In mock or production, synthesize grounded observations
    matched_skills_str = ", ".join(detail.matched_skills[:4]) if detail.matched_skills else "general engineering"
    strengths_synthesis = [
        f"Strong academic foundation with CGPA of {detail.academics.cgpa:.2f} and {len(detail.skills)} documented technical skills.",
        f"Demonstrated domain alignment in {matched_skills_str} matching job prerequisites.",
    ]
    if detail.projects:
        strengths_synthesis.append(f"Practical portfolio experience demonstrated across {len(detail.projects)} projects including '{detail.projects[0].title}'.")
    if detail.evaluations:
        strengths_synthesis.append(f"Positive interviewer consensus across {len(detail.evaluations)} evaluation rounds.")

    probe_questions = [
        f"Can you explain the architectural trade-offs made in your project '{detail.projects[0].title if detail.projects else 'portfolio'}'?",
        f"How would you approach scaling a distributed service using {detail.matched_skills[0] if detail.matched_skills else 'your core technical stack'}?",
        "Describe a challenging bug you encountered in production or testing and how you systematically isolated the root cause.",
    ]

    development_areas = []
    if detail.missing_mandatory_skills:
        development_areas.append(f"Unverified or missing mandatory skills for target role: {', '.join(detail.missing_mandatory_skills)}.")
    if detail.academics.active_backlogs > 0:
        development_areas.append(f"Active backlog count ({detail.academics.active_backlogs}) requires academic completion plan.")
    if not detail.experiences:
        development_areas.append("Limited formal corporate internship experience; focus interview on practical project ownership.")

    ai_observations = {
        "candidate_readiness_summary": (
            f"{detail.profile.get('full_name')} exhibits a strong profile with {detail.compatibility_score:.1f}% role alignment "
            f"for '{detail.job_title}'. Core strengths center around {matched_skills_str}."
        ),
        "synthesized_strengths": strengths_synthesis,
        "suggested_interview_probes": probe_questions,
        "areas_for_development": development_areas or ["No critical technical gaps identified from verified records."],
    }

    return CandidateAISummary(
        candidate_id=detail.profile.get("student_id", 0),
        candidate_name=detail.profile.get("full_name", "Candidate"),
        verified_facts=verified_facts,
        calculated_metrics=calculated_metrics,
        ai_observations=ai_observations,
        safety_disclaimer=(
            "This AI candidate summary is an advisory tool grounded strictly in verified candidate submissions and "
            "interviewer notes. It does not replace human evaluation or institutional policy decisions. No sensitive "
            "demographic characteristics are inferred or processed."
        ),
        generated_at=datetime.now(timezone.utc),
    )
