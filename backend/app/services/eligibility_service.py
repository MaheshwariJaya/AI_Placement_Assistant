from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging

from app.models.job import Job, JobStatus
from app.models.student import StudentProfile
from app.models.user import User
from app.schemas.job import CriterionEvaluation, JobEligibilityResult
from app.services.matching_engine import normalize_skill

logger = logging.getLogger(__name__)


def evaluate_student_job_eligibility(
    job: Job,
    student_user: User,
    student_profile: StudentProfile,
    student_skill_names: Optional[List[str]] = None,
) -> JobEligibilityResult:
    """
    Evaluate student academic metrics and skill prerequisites against a job's
    deterministic cutoff criteria.

    Strictly deterministic rule engine evaluating 9 criteria:
    1. Job Active & Published Status
    2. Application Deadline
    3. Institutional Scope (Global vs Campus Exclusive)
    4. Academic CGPA Cutoff (with invalid data & missing data safeguards)
    5. Department / Branch Eligibility
    6. Target Graduation Year (batch requirement)
    7. Active Backlogs Limit
    8. Historical Total Backlogs Limit
    9. Mandatory Skill Prerequisites (with canonical alias matching)
    """
    criteria: Dict[str, CriterionEvaluation] = {}
    reasons: List[str] = []

    # 1. Job Active & Published Status
    is_active = getattr(job, "is_active", None)
    job_status = getattr(job, "status", None)

    # Strict rule: A job must have status PUBLISHED and is_active must be True
    job_status_passed = (job_status == JobStatus.PUBLISHED) and (is_active is True)
    status_str = job_status.value if hasattr(job_status, "value") else (str(job_status) if job_status is not None else "None")

    criteria["job_status"] = CriterionEvaluation(
        criterion="Job Lifecycle Status",
        required="published (active)",
        student_value=f"{status_str} (active={is_active})",
        passed=job_status_passed,
        message="Job opportunity is open and accepting applications" if job_status_passed else f"Job opportunity is not active or published (status: {status_str}, active={is_active})",
    )
    if not job_status_passed:
        reasons.append(f"Job posting is not active (Status: {status_str})")

    # 2. Application Deadline
    now_utc = datetime.now(timezone.utc)
    deadline = job.application_deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    deadline_passed = now_utc <= deadline
    criteria["deadline"] = CriterionEvaluation(
        criterion="Application Deadline",
        required=deadline.isoformat(),
        student_value=now_utc.isoformat(),
        passed=deadline_passed,
        message="Application window is currently active" if deadline_passed else "Application deadline has closed",
    )
    if not deadline_passed:
        reasons.append("Application deadline for this posting has expired")

    # 3. Institutional Scoping
    if getattr(job, "institution_id", None) is not None:
        inst_passed = (
            student_user.institution_id is not None
            and student_user.institution_id == job.institution_id
        )
        criteria["institution"] = CriterionEvaluation(
            criterion="Institution Eligibility",
            required=job.institution_id,
            student_value=student_user.institution_id,
            passed=inst_passed,
            message="Student enrolled in host institution" if inst_passed else "Drive restricted to host institution candidates",
        )
        if not inst_passed:
            reasons.append("This recruitment drive is exclusive to candidates from another institution")
    else:
        criteria["institution"] = CriterionEvaluation(
            criterion="Institution Eligibility",
            required="Global / All Institutions",
            student_value=student_user.institution_id or "Any",
            passed=True,
            message="Open globally to candidates across institutions",
        )

    # 4. Academic CGPA Cutoff
    cgpa_req = float(job.min_cgpa or 0.0)
    student_cgpa_raw = student_profile.cgpa
    if student_cgpa_raw is None:
        cgpa_passed = False
        criteria["cgpa"] = CriterionEvaluation(
            criterion="CGPA Cutoff",
            required=f"{cgpa_req:.2f}",
            student_value="Unrecorded",
            passed=False,
            message="Academic CGPA is unrecorded / unverified",
        )
        reasons.append("Academic CGPA is unrecorded / unverified")
    else:
        student_cgpa = float(student_cgpa_raw)
        if student_cgpa < 0.0 or student_cgpa > 10.0:
            # Safeguard 1: Invalid CGPA values outside 0-10 must be flagged as invalid data
            cgpa_passed = False
            criteria["cgpa"] = CriterionEvaluation(
                criterion="CGPA Cutoff",
                required=f"{cgpa_req:.2f}",
                student_value=f"{student_cgpa:.2f}",
                passed=False,
                message=f"Academic CGPA value ({student_cgpa:.2f}) is invalid (must be between 0.0 and 10.0)",
            )
            reasons.append(f"Academic CGPA value ({student_cgpa:.2f}) is invalid")
        else:
            cgpa_passed = student_cgpa >= cgpa_req
            criteria["cgpa"] = CriterionEvaluation(
                criterion="CGPA Cutoff",
                required=f"{cgpa_req:.2f}",
                student_value=f"{student_cgpa:.2f}",
                passed=cgpa_passed,
                message="CGPA meets or exceeds cutoff" if cgpa_passed else f"Requires minimum {cgpa_req:.2f} CGPA (Candidate: {student_cgpa:.2f})",
            )
            if not cgpa_passed:
                reasons.append(f"Minimum CGPA cutoff not met (Requires: {cgpa_req:.2f}, Candidate: {student_cgpa:.2f})")

    # 5. Department Verification
    eligible_dept_ids = [ed.department_id for ed in (job.eligible_departments or [])]
    dept_id = student_user.department_id
    dept_name = student_user.department.name if student_user.department else "Undeclared"

    if eligible_dept_ids:
        if dept_id is None:
            dept_passed = False
            criteria["department"] = CriterionEvaluation(
                criterion="Eligible Departments",
                required=eligible_dept_ids,
                student_value="None",
                passed=False,
                message="Academic department is unassigned / undeclared",
            )
            reasons.append("Academic department is unassigned / undeclared")
        else:
            dept_passed = dept_id in eligible_dept_ids
            criteria["department"] = CriterionEvaluation(
                criterion="Eligible Departments",
                required=eligible_dept_ids,
                student_value=dept_id,
                passed=dept_passed,
                message="Department is eligible" if dept_passed else f"Department '{dept_name}' is not in the eligible list",
            )
            if not dept_passed:
                reasons.append(f"Department '{dept_name}' is not eligible for this role")
    else:
        criteria["department"] = CriterionEvaluation(
            criterion="Eligible Departments",
            required="All Departments",
            student_value=dept_name,
            passed=True,
            message="Open to all academic departments",
        )

    # 6. Graduation Year
    if job.target_graduation_year:
        if student_profile.graduation_year is None:
            grad_year_passed = False
            criteria["graduation_year"] = CriterionEvaluation(
                criterion="Graduation Year",
                required=job.target_graduation_year,
                student_value="Unrecorded",
                passed=False,
                message=f"Target graduation batch is required ({job.target_graduation_year}) but student graduation year is unrecorded",
            )
            reasons.append(f"Target graduation batch is {job.target_graduation_year} but student graduation year is unrecorded")
        else:
            grad_year_passed = student_profile.graduation_year == job.target_graduation_year
            criteria["graduation_year"] = CriterionEvaluation(
                criterion="Graduation Year",
                required=job.target_graduation_year,
                student_value=student_profile.graduation_year,
                passed=grad_year_passed,
                message="Batch year matches" if grad_year_passed else f"Role is strictly for batch of {job.target_graduation_year}",
            )
            if not grad_year_passed:
                reasons.append(f"Target graduation batch is {job.target_graduation_year} (Candidate: {student_profile.graduation_year})")
    else:
        criteria["graduation_year"] = CriterionEvaluation(
            criterion="Graduation Year",
            required="Any Batch",
            student_value=student_profile.graduation_year if student_profile.graduation_year is not None else "Any",
            passed=True,
            message="Open to all graduating batches",
        )

    # 7. Active Backlogs
    if student_profile.active_backlogs is None:
        active_passed = False
        criteria["active_backlogs"] = CriterionEvaluation(
            criterion="Active Backlogs Limit",
            required=f"Max {job.max_active_backlogs or 0}",
            student_value="Unrecorded",
            passed=False,
            message="Active backlog status is unverified / unrecorded",
        )
        reasons.append("Active backlog status is unverified / unrecorded")
    else:
        max_active = job.max_active_backlogs if job.max_active_backlogs is not None else 0
        active_backlogs = student_profile.active_backlogs
        active_passed = active_backlogs <= max_active
        criteria["active_backlogs"] = CriterionEvaluation(
            criterion="Active Backlogs Limit",
            required=f"Max {max_active}",
            student_value=active_backlogs,
            passed=active_passed,
            message="Active backlogs within permissible threshold" if active_passed else f"Maximum {max_active} active backlogs allowed (Candidate: {active_backlogs})",
        )
        if not active_passed:
            reasons.append(f"Exceeds active backlogs limit (Max: {max_active}, Candidate: {active_backlogs})")

    # 8. Total Backlogs
    if student_profile.total_backlogs is None:
        total_passed = False
        criteria["total_backlogs"] = CriterionEvaluation(
            criterion="Historical Total Backlogs Limit",
            required=f"Max {job.max_total_backlogs or 0}",
            student_value="Unrecorded",
            passed=False,
            message="Historical total backlog status is unverified / unrecorded",
        )
        reasons.append("Historical total backlog status is unverified / unrecorded")
    else:
        max_total = job.max_total_backlogs if job.max_total_backlogs is not None else 0
        total_backlogs = student_profile.total_backlogs
        total_passed = total_backlogs <= max_total
        criteria["total_backlogs"] = CriterionEvaluation(
            criterion="Historical Total Backlogs Limit",
            required=f"Max {max_total}",
            student_value=total_backlogs,
            passed=total_passed,
            message="Total historical backlogs within permissible threshold" if total_passed else f"Maximum {max_total} historical backlogs allowed (Candidate: {total_backlogs})",
        )
        if not total_passed:
            reasons.append(f"Exceeds historical total backlogs limit (Max: {max_total}, Candidate: {total_backlogs})")

    # 9. Mandatory Required Skills (canonical matching)
    mandatory_skills = [
        s.skill_name for s in (job.skills or []) if s.is_mandatory
    ]
    student_canonical_skills = {
        normalize_skill(s) for s in (student_skill_names or []) if normalize_skill(s)
    }
    missing_skills = [
        s for s in mandatory_skills if normalize_skill(s) not in student_canonical_skills
    ]
    skills_passed = len(missing_skills) == 0
    criteria["required_skills"] = CriterionEvaluation(
        criterion="Mandatory Skill Prerequisites",
        required=mandatory_skills,
        student_value=student_skill_names or [],
        passed=skills_passed,
        message="All mandatory skills detected" if skills_passed else f"Missing required skills: {', '.join(missing_skills)}",
    )
    if not skills_passed:
        reasons.append(f"Missing mandatory required skills: {', '.join(missing_skills)}")

    # Compile Passed & Failed Lists
    passed_criteria = [k for k, v in criteria.items() if v.passed]
    failed_criteria = [k for k, v in criteria.items() if not v.passed]
    overall_eligible = len(failed_criteria) == 0

    return JobEligibilityResult(
        job_id=job.id,
        job_title=job.title,
        student_id=student_profile.id,
        student_name=student_user.full_name,
        is_eligible=overall_eligible,
        reasons=reasons,
        passed_criteria=passed_criteria,
        failed_criteria=failed_criteria,
        criteria=criteria,
    )
