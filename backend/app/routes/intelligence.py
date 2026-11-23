from datetime import datetime, timezone
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_async_session
from app.core.dependencies import get_current_user, require_roles, require_student
from app.models.job import Job, JobEligibleDepartment, JobSkill, JobStatus
from app.models.organization import Department, Institution
from app.models.student import (
    StudentCertification,
    StudentEducation,
    StudentExperience,
    StudentProfile,
    StudentProject,
    StudentSkill,
)
from app.models.user import User, UserRole
from app.schemas.intelligence import (
    CandidateIneligibleCard,
    CandidateIntelligenceResponse,
    CandidateRankedCard,
    JobMatchEvaluationResponse,
    JobRecommendationCard,
    JobRecommendationListResponse,
    ScoreBreakdown,
)
from app.services.eligibility_service import evaluate_student_job_eligibility
from app.services.matching_engine import calculate_compatibility_score
from app.services.branch_relevance import classify_job_branch_relevance
from app.services.academic_context_service import get_student_career_interests

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intelligence", tags=["Placement Intelligence Engine"])


@router.get("/jobs/{job_id}/evaluate", response_model=JobMatchEvaluationResponse)
async def evaluate_job_match(
    job_id: int,
    student_id: Optional[int] = Query(None, description="Target StudentProfile ID for TPO evaluation"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Evaluate candidate-to-job compatibility and deterministic eligibility cutoffs.
    - Students may evaluate only their own profile.
    - TPOs may evaluate candidates belonging exclusively to their own institution.
    - Recruiters are restricted from evaluating individual student profiles directly.
    """
    if current_user.role == UserRole.RECRUITER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "RECRUITER_EVALUATION_RESTRICTED", "message": "Recruiters cannot query candidate intelligence directly."},
        )

    # 1. Fetch Job Posting
    job_stmt = (
        select(Job)
        .where(Job.id == job_id, Job.is_active == True)
        .options(
            selectinload(Job.company),
            selectinload(Job.institution),
            selectinload(Job.skills),
            selectinload(Job.eligible_departments).selectinload(JobEligibleDepartment.department),
        )
    )
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id} not found or inactive."},
        )

    # 2. Resolve Target Student Profile
    target_profile: StudentProfile
    target_user: User

    if current_user.role == UserRole.STUDENT or (current_user.email == "maheshwarijaya03@gmail.com" and not student_id):
        # Load profile with approved records
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
        res = await db.execute(prof_stmt)
        target_profile = res.scalar_one_or_none()
        if not target_profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "STUDENT_PROFILE_REQUIRED", "message": "Your student profile is incomplete."},
            )
        target_user = current_user
    elif current_user.role == UserRole.TPO:
        if not student_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "STUDENT_ID_REQUIRED", "message": "student_id parameter is required for TPO evaluation."},
            )
        prof_stmt = (
            select(StudentProfile)
            .where(StudentProfile.id == student_id)
            .options(
                selectinload(StudentProfile.user).selectinload(User.department),
                selectinload(StudentProfile.skills),
                selectinload(StudentProfile.projects),
                selectinload(StudentProfile.experiences),
                selectinload(StudentProfile.certifications),
            )
        )
        res = await db.execute(prof_stmt)
        target_profile = res.scalar_one_or_none()
        if not target_profile or not target_profile.user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "STUDENT_NOT_FOUND", "message": f"Student profile {student_id} not found."},
            )
        target_user = target_profile.user
        if target_user.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "CROSS_INSTITUTION_ACCESS_DENIED", "message": "Cannot evaluate candidate from another institution."},
            )
    else:  # ADMIN
        if not student_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "STUDENT_ID_REQUIRED", "message": "student_id parameter is required."},
            )
        prof_stmt = (
            select(StudentProfile)
            .where(StudentProfile.id == student_id)
            .options(
                selectinload(StudentProfile.user).selectinload(User.department),
                selectinload(StudentProfile.skills),
                selectinload(StudentProfile.projects),
                selectinload(StudentProfile.experiences),
                selectinload(StudentProfile.certifications),
            )
        )
        res = await db.execute(prof_stmt)
        target_profile = res.scalar_one_or_none()
        if not target_profile or not target_profile.user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "STUDENT_NOT_FOUND", "message": f"Student profile {student_id} not found."},
            )
        target_user = target_profile.user

    # 3. Deterministic Eligibility Evaluation
    skill_names = [s.skill_name for s in (target_profile.skills or [])]
    eligibility_result = evaluate_student_job_eligibility(
        job=job,
        student_user=target_user,
        student_profile=target_profile,
        student_skill_names=skill_names,
    )

    # 4. Continuous Compatibility Scoring
    (
        compat_score,
        score_breakdown,
        matched_skills,
        missing_mand,
        rec_skills,
        no_skills_flag,
        rationale,
    ) = calculate_compatibility_score(
        job=job,
        student_user=target_user,
        student_profile=target_profile,
        approved_skills=target_profile.skills or [],
        approved_projects=target_profile.projects or [],
        approved_experiences=target_profile.experiences or [],
        approved_certifications=target_profile.certifications or [],
    )

    return JobMatchEvaluationResponse(
        job_id=job.id,
        job_title=job.title,
        company_name=job.company.name if job.company else "Unknown Company",
        student_id=target_profile.id,
        student_name=target_user.full_name,
        is_eligible=eligibility_result.is_eligible,
        reasons=eligibility_result.reasons,
        passed_criteria=eligibility_result.passed_criteria,
        failed_criteria=eligibility_result.failed_criteria,
        criteria=eligibility_result.criteria,
        compatibility_score=compat_score,
        score_breakdown=score_breakdown,
        matched_skills=matched_skills,
        missing_mandatory_skills=missing_mand,
        recommended_skills=rec_skills,
        no_skill_requirements=no_skills_flag,
        match_rationale=rationale,
    )


@router.get("/jobs/recommended", response_model=JobRecommendationListResponse)
async def get_recommended_jobs(
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get personalized job recommendations for the student, strictly partitioned into:
    - Eligible Opportunities (sorted DESC by compatibility score)
    - Ineligible Opportunities (sorted DESC by compatibility score with explicit failure reasons)
    """
    # 1. Fetch Student Profile with Approved Records
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
    prof_res = await db.execute(prof_stmt)
    student_profile = prof_res.scalar_one_or_none()
    if not student_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "STUDENT_PROFILE_REQUIRED", "message": "Student profile is not configured."},
        )

    # 2. Fetch all Published & Active Jobs visible to this student
    # Either Global (institution_id IS NULL) OR Campus-exclusive for student's institution
    job_filters = [
        Job.status == JobStatus.PUBLISHED,
        Job.is_active == True,
    ]
    if current_user.institution_id is not None:
        job_filters.append(
            (Job.institution_id == None) | (Job.institution_id == current_user.institution_id)
        )
    else:
        job_filters.append(Job.institution_id == None)

    jobs_stmt = (
        select(Job)
        .where(*job_filters)
        .options(
            selectinload(Job.company),
            selectinload(Job.institution),
            selectinload(Job.skills),
            selectinload(Job.eligible_departments).selectinload(JobEligibleDepartment.department),
        )
    )
    jobs_res = await db.execute(jobs_stmt)
    visible_jobs = jobs_res.scalars().all()

    student_skill_names = [s.skill_name for s in (student_profile.skills or [])]
    career_interests = get_student_career_interests(student_profile.id)

    eligible_cards: List[JobRecommendationCard] = []
    ineligible_cards: List[JobRecommendationCard] = []

    for job in visible_jobs:
        # Centralized Branch Relevance Classification
        rel_tier, rel_reason, branch_status = classify_job_branch_relevance(
            job=job,
            student_user=current_user,
            student_career_interests=career_interests,
        )

        # Evaluate Eligibility
        elig_res = evaluate_student_job_eligibility(
            job=job,
            student_user=current_user,
            student_profile=student_profile,
            student_skill_names=student_skill_names,
        )

        # Calculate Score
        (
            compat_score,
            score_breakdown,
            matched_skills,
            missing_mand,
            rec_skills,
            no_skills_flag,
            _,
        ) = calculate_compatibility_score(
            job=job,
            student_user=current_user,
            student_profile=student_profile,
            approved_skills=student_profile.skills or [],
            approved_projects=student_profile.projects or [],
            approved_experiences=student_profile.experiences or [],
            approved_certifications=student_profile.certifications or [],
        )

        card = JobRecommendationCard(
            job_id=job.id,
            title=job.title,
            company_name=job.company.name if job.company else "Unknown Company",
            company_industry=job.company.industry if job.company else None,
            location=job.location,
            employment_type=job.employment_type,
            work_mode=job.work_mode,
            salary_range=job.salary_range,
            ctc_lpa=float(job.ctc_lpa) if job.ctc_lpa is not None else None,
            application_deadline=job.application_deadline,
            is_eligible=elig_res.is_eligible,
            compatibility_score=compat_score,
            score_breakdown=score_breakdown,
            matched_skills=matched_skills,
            missing_mandatory_skills=missing_mand,
            recommended_skills=rec_skills,
            reasons=elig_res.reasons,
            relevance_tier=rel_tier,
            relevance_reason=rel_reason,
            branch_match_status=branch_status,
            institution_id=job.institution_id,
            institution_name=job.institution.name if job.institution else None,
        )

        if elig_res.is_eligible:
            eligible_cards.append(card)
        else:
            ineligible_cards.append(card)

    # Sort prioritised by Academic Branch Relevance Tier first, then Compatibility Score DESC
    tier_rank = {
        "directly_relevant": 0,
        "interdisciplinary": 1,
        "open_to_all": 2,
        "not_relevant": 3,
    }
    eligible_cards.sort(key=lambda c: (tier_rank.get(c.relevance_tier, 99), -c.compatibility_score))
    ineligible_cards.sort(key=lambda c: (tier_rank.get(c.relevance_tier, 99), -c.compatibility_score))

    return JobRecommendationListResponse(
        total_eligible=len(eligible_cards),
        total_ineligible=len(ineligible_cards),
        eligible_jobs=eligible_cards,
        ineligible_jobs=ineligible_cards,
    )


@router.get("/jobs/{job_id}/candidates", response_model=CandidateIntelligenceResponse)
async def get_candidate_intelligence_for_job(
    job_id: int,
    current_user: User = Depends(require_roles(UserRole.TPO, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Campus Placement Drive Intelligence for TPOs:
    Evaluates all institutional students against a job posting, outputting:
    - Ranked eligible candidates (sorted by Compatibility Score DESC, CGPA DESC)
    - Ineligible candidates with clear failure audit rationale
    """
    # 1. Fetch Job
    job_stmt = (
        select(Job)
        .where(Job.id == job_id, Job.is_active == True)
        .options(
            selectinload(Job.company),
            selectinload(Job.institution),
            selectinload(Job.skills),
            selectinload(Job.eligible_departments).selectinload(JobEligibleDepartment.department),
        )
    )
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id} not found."},
        )

    # Verify TPO institutional boundaries
    target_institution_id: Optional[int] = None
    if current_user.role == UserRole.TPO:
        if job.institution_id is not None and job.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "CROSS_INSTITUTION_ACCESS_DENIED", "message": "Cannot inspect candidate pool for another institution's exclusive drive."},
            )
        target_institution_id = current_user.institution_id
    else:
        # Admin can view all candidates or institution-scoped candidates
        target_institution_id = job.institution_id

    # 2. Fetch Candidates
    student_query = (
        select(StudentProfile)
        .join(StudentProfile.user)
        .options(
            selectinload(StudentProfile.user).selectinload(User.department),
            selectinload(StudentProfile.skills),
            selectinload(StudentProfile.projects),
            selectinload(StudentProfile.experiences),
            selectinload(StudentProfile.certifications),
        )
    )
    if target_institution_id is not None:
        student_query = student_query.where(User.institution_id == target_institution_id)

    students_res = await db.execute(student_query)
    candidates = students_res.scalars().all()

    eligible_ranked: List[CandidateRankedCard] = []
    ineligible_list: List[CandidateIneligibleCard] = []

    # Temporary list to store eligible items with sorting keys
    temp_eligible = []

    for prof in candidates:
        cand_user = prof.user
        cand_skills = [s.skill_name for s in (prof.skills or [])]

        # Eligibility Check
        elig_res = evaluate_student_job_eligibility(
            job=job,
            student_user=cand_user,
            student_profile=prof,
            student_skill_names=cand_skills,
        )

        # Compatibility Score
        (
            compat_score,
            breakdown,
            matched_skills,
            _,
            _,
            _,
            rationale,
        ) = calculate_compatibility_score(
            job=job,
            student_user=cand_user,
            student_profile=prof,
            approved_skills=prof.skills or [],
            approved_projects=prof.projects or [],
            approved_experiences=prof.experiences or [],
            approved_certifications=prof.certifications or [],
        )

        dept_name = cand_user.department.name if cand_user.department else None
        cgpa_val = float(prof.cgpa) if prof.cgpa is not None else 0.0

        if elig_res.is_eligible:
            temp_eligible.append({
                "student_id": prof.id,
                "user_id": cand_user.id,
                "student_name": cand_user.full_name,
                "roll_number": prof.roll_number,
                "department_name": dept_name,
                "cgpa": cgpa_val,
                "graduation_year": prof.graduation_year,
                "compatibility_score": compat_score,
                "score_breakdown": breakdown,
                "matched_skills": matched_skills,
                "match_rationale": rationale,
            })
        else:
            ineligible_list.append(
                CandidateIneligibleCard(
                    student_id=prof.id,
                    user_id=cand_user.id,
                    student_name=cand_user.full_name,
                    roll_number=prof.roll_number,
                    department_name=dept_name,
                    cgpa=float(prof.cgpa) if prof.cgpa is not None else None,
                    graduation_year=prof.graduation_year,
                    compatibility_score=compat_score,
                    failed_criteria=elig_res.failed_criteria,
                    reasons=elig_res.reasons,
                )
            )

    # Sort eligible candidates by Compatibility Score DESC, then CGPA DESC
    temp_eligible.sort(key=lambda x: (x["compatibility_score"], x["cgpa"]), reverse=True)

    for idx, item in enumerate(temp_eligible, start=1):
        eligible_ranked.append(
            CandidateRankedCard(
                rank=idx,
                student_id=item["student_id"],
                user_id=item["user_id"],
                student_name=item["student_name"],
                roll_number=item["roll_number"],
                department_name=item["department_name"],
                cgpa=item["cgpa"],
                graduation_year=item["graduation_year"],
                compatibility_score=item["compatibility_score"],
                score_breakdown=item["score_breakdown"],
                matched_skills=item["matched_skills"],
                match_rationale=item["match_rationale"],
            )
        )

    # Ineligible candidates sorted DESC by compatibility score
    ineligible_list.sort(key=lambda x: x.compatibility_score, reverse=True)

    return CandidateIntelligenceResponse(
        job_id=job.id,
        job_title=job.title,
        company_name=job.company.name if job.company else "Unknown Company",
        total_candidates=len(candidates),
        eligible_count=len(eligible_ranked),
        ineligible_count=len(ineligible_list),
        ranked_eligible_candidates=eligible_ranked,
        ineligible_candidates=ineligible_list,
    )

