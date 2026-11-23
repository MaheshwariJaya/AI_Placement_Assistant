from datetime import datetime, timedelta, timezone
from typing import Tuple
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import HTTPException

from app.models.company import Company
from app.models.job import (
    EmploymentType,
    Job,
    JobEligibleDepartment,
    JobSkill,
    JobStatus,
    WorkMode,
)
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
from app.routes.intelligence import (
    evaluate_job_match,
    get_candidate_intelligence_for_job,
    get_recommended_jobs,
)
from app.services.eligibility_service import evaluate_student_job_eligibility
from app.services.matching_engine import (
    CANONICAL_SKILL_ALIASES,
    calculate_compatibility_score,
    calculate_experience_months,
    normalize_skill,
    parse_date_to_month_year,
)


def _run_sync(coro):
    """Utility to run a coroutine synchronously in tests without external loop fixtures."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


# =============================================================================
# Helper Fixtures & Builders
# =============================================================================

def build_job(
    id: int = 1,
    title: str = "Software Engineer",
    min_cgpa: float = 7.0,
    target_graduation_year: int = 2026,
    max_active_backlogs: int = 0,
    max_total_backlogs: int = 1,
    status: JobStatus = JobStatus.PUBLISHED,
    is_active: bool = True,
    institution_id: int = None,
    skills=None,
    eligible_departments=None,
    days_to_deadline: int = 14,
) -> Job:
    job = Job(
        id=id,
        company_id=1,
        title=title,
        description="Core software engineering position working with cloud services.",
        employment_type=EmploymentType.FULL_TIME,
        work_mode=WorkMode.ON_SITE,
        location="Bengaluru",
        min_cgpa=min_cgpa,
        target_graduation_year=target_graduation_year,
        max_active_backlogs=max_active_backlogs,
        max_total_backlogs=max_total_backlogs,
        application_deadline=datetime.now(timezone.utc) + timedelta(days=days_to_deadline),
        status=status,
        is_active=is_active,
        institution_id=institution_id,
        created_by_user_id=10,
    )
    job.company = Company(id=1, name="Acme Tech", is_verified=True)
    job.skills = skills or []
    job.eligible_departments = eligible_departments or []
    return job


def build_student(
    user_id: int = 101,
    full_name: str = "Kavya Patel",
    institution_id: int = 1,
    department_id: int = 1,
    cgpa: float = 8.5,
    graduation_year: int = 2026,
    active_backlogs: int = 0,
    total_backlogs: int = 0,
    skills=None,
    projects=None,
    experiences=None,
    certifications=None,
) -> Tuple[User, StudentProfile]:
    dept = Department(id=department_id, institution_id=institution_id, name="Computer Science & Engineering", code="CSE")
    user = User(
        id=user_id,
        email=f"student_{user_id}@example.com",
        full_name=full_name,
        role=UserRole.STUDENT,
        institution_id=institution_id,
        department_id=department_id,
        is_active=True,
    )
    user.department = dept

    profile = StudentProfile(
        id=user_id + 500,
        user_id=user_id,
        roll_number=f"2022CSE{user_id:03d}",
        graduation_year=graduation_year,
        cgpa=cgpa,
        active_backlogs=active_backlogs,
        total_backlogs=total_backlogs,
        is_placement_ready=True,
    )
    profile.user = user
    profile.skills = skills or []
    profile.projects = projects or []
    profile.experiences = experiences or []
    profile.certifications = certifications or []
    user.student_profile = profile
    return user, profile


# =============================================================================
# 1. Eligibility Engine Unit Tests
# =============================================================================

class TestEligibilityEngine:
    def test_eligibility_all_criteria_met(self):
        job = build_job(
            min_cgpa=7.5,
            target_graduation_year=2026,
            max_active_backlogs=0,
            skills=[
                JobSkill(id=1, job_id=1, skill_name="Python", is_mandatory=True),
                JobSkill(id=2, job_id=1, skill_name="PostgreSQL", is_mandatory=True),
            ],
            eligible_departments=[
                JobEligibleDepartment(id=1, job_id=1, department_id=1),
            ],
        )
        user, profile = build_student(
            cgpa=8.2,
            graduation_year=2026,
            active_backlogs=0,
            total_backlogs=0,
            department_id=1,
        )
        res = evaluate_student_job_eligibility(
            job=job,
            student_user=user,
            student_profile=profile,
            student_skill_names=["Python", "PostgreSQL", "Docker"],
        )
        assert res.is_eligible is True
        assert len(res.failed_criteria) == 0
        assert len(res.reasons) == 0
        assert "cgpa" in res.passed_criteria
        assert "graduation_year" in res.passed_criteria
        assert "required_skills" in res.passed_criteria
        assert "job_status" in res.passed_criteria

    def test_eligibility_cgpa_cutoff_failure(self):
        job = build_job(min_cgpa=8.0)
        user, profile = build_student(cgpa=7.8)
        res = evaluate_student_job_eligibility(job, user, profile, [])
        assert res.is_eligible is False
        assert "cgpa" in res.failed_criteria
        assert any("Minimum CGPA cutoff not met" in r for r in res.reasons)

    def test_eligibility_cgpa_missing_data_safeguard(self):
        job = build_job(min_cgpa=6.0)
        user, profile = build_student()
        profile.cgpa = None
        res = evaluate_student_job_eligibility(job, user, profile, [])
        assert res.is_eligible is False
        assert "cgpa" in res.failed_criteria
        assert "Academic CGPA is unrecorded / unverified" in res.reasons

    def test_eligibility_cgpa_invalid_safeguard(self):
        job = build_job(min_cgpa=6.0)
        user, profile = build_student(cgpa=12.5)  # Invalid score
        res = evaluate_student_job_eligibility(job, user, profile, [])
        assert res.is_eligible is False
        assert "cgpa" in res.failed_criteria
        assert any("invalid" in r for r in res.reasons)

        profile.cgpa = -1.0  # Invalid negative
        res2 = evaluate_student_job_eligibility(job, user, profile, [])
        assert res2.is_eligible is False
        assert "cgpa" in res2.failed_criteria

    def test_eligibility_department_branch_matching(self):
        job = build_job(
            eligible_departments=[
                JobEligibleDepartment(id=1, job_id=1, department_id=1),  # CSE only
            ]
        )
        user, profile = build_student(department_id=2)  # Mechanical
        user.department = Department(id=2, institution_id=1, name="Mechanical Engineering", code="MECH")

        res = evaluate_student_job_eligibility(job, user, profile, [])
        assert res.is_eligible is False
        assert "department" in res.failed_criteria
        assert any("Mechanical Engineering" in r for r in res.reasons)

    def test_eligibility_department_missing_safeguard(self):
        job = build_job(
            eligible_departments=[
                JobEligibleDepartment(id=1, job_id=1, department_id=1),
            ]
        )
        user, profile = build_student(department_id=None)
        user.department = None
        user.department_id = None

        res = evaluate_student_job_eligibility(job, user, profile, [])
        assert res.is_eligible is False
        assert "department" in res.failed_criteria
        assert "Academic department is unassigned / undeclared" in res.reasons

    def test_eligibility_department_open_all(self):
        job = build_job(eligible_departments=[])  # Open to all
        user, profile = build_student(department_id=3)
        res = evaluate_student_job_eligibility(job, user, profile, [])
        assert "department" in res.passed_criteria

    def test_eligibility_graduation_year_mandatory_vs_optional(self):
        # Mandatory year set
        job = build_job(target_graduation_year=2026)
        user, profile = build_student(graduation_year=2025)
        res = evaluate_student_job_eligibility(job, user, profile, [])
        assert res.is_eligible is False
        assert "graduation_year" in res.failed_criteria

        # Student year missing when job requires batch
        profile.graduation_year = None
        res_missing = evaluate_student_job_eligibility(job, user, profile, [])
        assert res_missing.is_eligible is False
        assert any("unrecorded" in r for r in res_missing.reasons)

        # Optional graduation year on job (target_graduation_year = None)
        job_open = build_job(target_graduation_year=None)
        res_open = evaluate_student_job_eligibility(job_open, user, profile, [])
        assert "graduation_year" in res_open.passed_criteria

    def test_eligibility_backlogs_safeguards(self):
        job = build_job(max_active_backlogs=0, max_total_backlogs=1)
        user, profile = build_student(active_backlogs=1, total_backlogs=2)
        res = evaluate_student_job_eligibility(job, user, profile, [])
        assert res.is_eligible is False
        assert "active_backlogs" in res.failed_criteria
        assert "total_backlogs" in res.failed_criteria

        # Missing backlog values
        profile.active_backlogs = None
        profile.total_backlogs = None
        res2 = evaluate_student_job_eligibility(job, user, profile, [])
        assert res2.is_eligible is False
        assert "active_backlogs" in res2.failed_criteria
        assert "total_backlogs" in res2.failed_criteria
        assert any("Active backlog status is unverified" in r for r in res2.reasons)

    def test_eligibility_deadline_expired(self):
        job = build_job(days_to_deadline=-1)
        user, profile = build_student()
        res = evaluate_student_job_eligibility(job, user, profile, [])
        assert res.is_eligible is False
        assert "deadline" in res.failed_criteria
        assert "Application deadline for this posting has expired" in res.reasons

    def test_eligibility_mandatory_skills_canonical_matching(self):
        job = build_job(
            skills=[
                JobSkill(id=1, job_id=1, skill_name="React.js", is_mandatory=True),
                JobSkill(id=2, job_id=1, skill_name="PostgreSQL", is_mandatory=True),
                JobSkill(id=3, job_id=1, skill_name="Docker", is_mandatory=True),
            ]
        )
        user, profile = build_student()
        # Student has alias 'react' and 'postgres', but lacks 'docker'
        res = evaluate_student_job_eligibility(
            job, user, profile, student_skill_names=["react", "postgres", "python"]
        )
        assert res.is_eligible is False
        assert "required_skills" in res.failed_criteria
        assert any("Docker" in r for r in res.reasons)

        # Now student adds docker
        res2 = evaluate_student_job_eligibility(
            job, user, profile, student_skill_names=["react", "postgres", "docker"]
        )
        assert "required_skills" in res2.passed_criteria

    def test_eligibility_institutional_scoping_global_vs_campus(self):
        # Global job
        global_job = build_job(institution_id=None)
        user_inst1, prof1 = build_student(institution_id=1)
        user_no_inst, prof2 = build_student(institution_id=None)

        res_g1 = evaluate_student_job_eligibility(global_job, user_inst1, prof1, [])
        assert "institution" in res_g1.passed_criteria

        res_g2 = evaluate_student_job_eligibility(global_job, user_no_inst, prof2, [])
        assert "institution" in res_g2.passed_criteria

        # Campus Exclusive Job
        campus_job = build_job(institution_id=1)
        user_other, prof3 = build_student(institution_id=2)

        res_c1 = evaluate_student_job_eligibility(campus_job, user_inst1, prof1, [])
        assert "institution" in res_c1.passed_criteria

        res_c2 = evaluate_student_job_eligibility(campus_job, user_other, prof3, [])
        assert res_c2.is_eligible is False
        assert "institution" in res_c2.failed_criteria
        assert "This recruitment drive is exclusive to candidates from another institution" in res_c2.reasons

    def test_eligibility_job_status_and_active(self):
        user, prof = build_student()

        # 1. PUBLISHED + active = passes
        job_pub_active = build_job(status=JobStatus.PUBLISHED, is_active=True)
        res_pub_active = evaluate_student_job_eligibility(job_pub_active, user, prof, [])
        assert "job_status" in res_pub_active.passed_criteria

        # 2. DRAFT + active = fails
        job_draft_active = build_job(status=JobStatus.DRAFT, is_active=True)
        res_draft_active = evaluate_student_job_eligibility(job_draft_active, user, prof, [])
        assert "job_status" in res_draft_active.failed_criteria
        assert res_draft_active.is_eligible is False

        # 3. CLOSED + active = fails
        job_closed_active = build_job(status=JobStatus.CLOSED, is_active=True)
        res_closed_active = evaluate_student_job_eligibility(job_closed_active, user, prof, [])
        assert "job_status" in res_closed_active.failed_criteria
        assert res_closed_active.is_eligible is False

        # 4. CANCELLED + active = fails
        job_cancelled_active = build_job(status=JobStatus.CANCELLED, is_active=True)
        res_cancelled_active = evaluate_student_job_eligibility(job_cancelled_active, user, prof, [])
        assert "job_status" in res_cancelled_active.failed_criteria
        assert res_cancelled_active.is_eligible is False

        # 5. None (status unassigned) + active = fails
        job_none_active = build_job(status=None, is_active=True)
        job_none_active.status = None
        res_none_active = evaluate_student_job_eligibility(job_none_active, user, prof, [])
        assert "job_status" in res_none_active.failed_criteria
        assert res_none_active.is_eligible is False

        # 6. PUBLISHED + inactive = fails
        job_pub_inactive = build_job(status=JobStatus.PUBLISHED, is_active=False)
        res_pub_inactive = evaluate_student_job_eligibility(job_pub_inactive, user, prof, [])
        assert "job_status" in res_pub_inactive.failed_criteria
        assert res_pub_inactive.is_eligible is False


# =============================================================================
# 2. Compatibility Scoring Engine Unit Tests
# =============================================================================

class TestCompatibilityScoringEngine:
    def test_scoring_weights_sum_to_100(self):
        job = build_job(
            min_cgpa=8.0,
            skills=[
                JobSkill(id=1, job_id=1, skill_name="Python", is_mandatory=True, weight_factor=2.0),
                JobSkill(id=2, job_id=1, skill_name="FastAPI", is_mandatory=True, weight_factor=1.5),
                JobSkill(id=3, job_id=1, skill_name="Docker", is_mandatory=False, weight_factor=1.0),
            ],
        )
        user, profile = build_student(cgpa=10.0, active_backlogs=0, total_backlogs=0)
        skills = [
            StudentSkill(id=1, student_id=profile.id, skill_name="Python", proficiency_level="expert"),
            StudentSkill(id=2, student_id=profile.id, skill_name="FastAPI", proficiency_level="advanced"),
            StudentSkill(id=3, student_id=profile.id, skill_name="Docker", proficiency_level="intermediate"),
        ]
        projects = [
            StudentProject(
                id=1,
                student_id=profile.id,
                title="Microservices Cloud API",
                technologies="Python, FastAPI, Docker, PostgreSQL",
                project_url="https://github.com/example/api",
                description="Comprehensive microservices backend running high concurrency workloads with Docker orchestration.",
            )
        ]
        experiences = [
            StudentExperience(
                id=1,
                student_id=profile.id,
                company_name="Innovate Labs",
                role_title="Backend Engineer Intern",
                start_date="2024-01-01",
                end_date="2024-06-30",
                description="Engineered asynchronous endpoints in FastAPI and deployed dockerized production services.",
            )
        ]
        certifications = [
            StudentCertification(
                id=1,
                student_id=profile.id,
                certificate_name="AWS Certified Developer Associate",
                issuing_organization="Amazon Web Services",
            ),
            StudentCertification(
                id=2,
                student_id=profile.id,
                certificate_name="Certified Kubernetes Administrator",
                issuing_organization="Linux Foundation",
            ),
        ]

        score, breakdown, matched, missing, rec, no_req, rationale = calculate_compatibility_score(
            job=job,
            student_user=user,
            student_profile=profile,
            approved_skills=skills,
            approved_projects=projects,
            approved_experiences=experiences,
            approved_certifications=certifications,
        )

        assert score == 100.0
        assert breakdown.skills == 50.0
        assert breakdown.academics == 20.0
        assert breakdown.projects == 15.0
        assert breakdown.experience == 7.0
        assert breakdown.experience <= 7.0
        assert breakdown.certifications == 5.0
        assert 0.0 <= score <= 100.0
        assert not no_req
        assert len(missing) == 0

    def test_scoring_zero_division_safety(self):
        # Case A: Cutoff = 10.0
        job_ten = build_job(min_cgpa=10.0)
        user, profile = build_student(cgpa=9.5)
        score_ten, breakdown_ten, *_ = calculate_compatibility_score(
            job_ten, user, profile, [], [], [], []
        )
        assert breakdown_ten.academics >= 0.0

        # Case B: Cutoff = 0.0
        job_zero = build_job(min_cgpa=0.0)
        score_zero, breakdown_zero, *_ = calculate_compatibility_score(
            job_zero, user, profile, [], [], [], []
        )
        assert breakdown_zero.academics >= 0.0

        # Case C: Zero skills on job (User Safeguard 3: Neutral handling)
        job_no_skills = build_job(skills=[])
        _, breakdown_no_skills, _, _, _, no_req, _ = calculate_compatibility_score(
            job_no_skills, user, profile, [], [], [], []
        )
        assert no_req is True
        assert breakdown_no_skills.skills == 25.0  # Neutral 50% allocation

        # Case D: Only mandatory skills (safe reallocation)
        job_only_mand = build_job(
            skills=[JobSkill(id=1, job_id=1, skill_name="Python", is_mandatory=True)]
        )
        user, profile = build_student()
        skills = [StudentSkill(id=1, student_id=profile.id, skill_name="Python")]
        _, breakdown_only_mand, *_ = calculate_compatibility_score(
            job_only_mand, user, profile, skills, [], [], []
        )
        assert breakdown_only_mand.skills == 50.0  # Full 50 points reallocated to mandatory

        # Case E: Only preferred skills (safe reallocation)
        job_only_pref = build_job(
            skills=[JobSkill(id=1, job_id=1, skill_name="Python", is_mandatory=False)]
        )
        _, breakdown_only_pref, *_ = calculate_compatibility_score(
            job_only_pref, user, profile, skills, [], [], []
        )
        assert breakdown_only_pref.skills == 50.0  # Full 50 points reallocated to preferred

    def test_scoring_alias_normalization_safety(self):
        assert normalize_skill("ReactJS") == "react"
        assert normalize_skill("react.js") == "react"
        assert normalize_skill("Node.js") == "node.js"
        assert normalize_skill("nodejs") == "node.js"
        assert normalize_skill("Postgres") == "postgresql"
        assert normalize_skill("postgresql") == "postgresql"
        assert normalize_skill("K8s") == "kubernetes"
        assert normalize_skill("AWS") == "amazon web services"

        # Distinct technologies must NEVER be merged!
        assert normalize_skill("Java") != normalize_skill("JavaScript")
        assert normalize_skill("C") != normalize_skill("C++")
        assert normalize_skill("C++") != normalize_skill("C#")

    def test_scoring_project_technology_deduplication(self):
        job = build_job(
            skills=[
                JobSkill(id=1, job_id=1, skill_name="Python", is_mandatory=True),
                JobSkill(id=2, job_id=1, skill_name="Docker", is_mandatory=True),
            ]
        )
        user, profile = build_student()
        # Student lists Python and Docker redundantly across two projects
        projects = [
            StudentProject(
                id=1,
                student_id=profile.id,
                title="Project A",
                technologies="Python, Docker",
                project_url="https://github.com/ex/a",
                description="Short desc",
            ),
            StudentProject(
                id=2,
                student_id=profile.id,
                title="Project B",
                technologies="python, docker, react",
                project_url=None,
                description="Short desc",
            ),
        ]
        _, breakdown, *_ = calculate_compatibility_score(
            job, user, profile, [], projects, [], []
        )
        # Tech match max is 12 points, plus 1.5 points for project_url
        assert breakdown.projects == 12.0 + 1.5

    def test_scoring_experience_safeguards(self):
        job = build_job()
        user, profile = build_student()

        # Case A: Standalone "Summer Intern" title without technical keywords (General role)
        exp_non_tech = [
            StudentExperience(
                id=1,
                student_id=profile.id,
                company_name="General Corp",
                role_title="Summer Intern",
                start_date="2024-05",
                end_date="2024-07",
                description="General administrative assistance and attending client presentations.",
            )
        ]
        _, b_non_tech, *_ = calculate_compatibility_score(
            job, user, profile, [], [], exp_non_tech, []
        )
        # General role awards 2.0 base + 2.0 duration bonus (>= 2 months) = 4.0 points (0 description points)
        assert b_non_tech.experience == 4.0
        assert b_non_tech.experience <= 7.0

        # Case B: Technical role "Software Engineer Intern"
        exp_tech = [
            StudentExperience(
                id=2,
                student_id=profile.id,
                company_name="Acme Corp",
                role_title="Software Engineer Intern",
                start_date="2024-05",
                end_date="2024-07",
                description="Assisted with backend testing and refactoring database query interfaces.",
            )
        ]
        _, b_tech, *_ = calculate_compatibility_score(
            job, user, profile, [], [], exp_tech, []
        )
        # Technical role awards 5.0 base + 2.0 duration (>= 2 months) = 7.0 points max
        assert b_tech.experience == 7.0
        assert b_tech.experience <= 7.0

        # Case C: Missing dates safeguard (Safeguard 4: incomplete/missing dates award 0 duration points)
        exp_no_dates = [
            StudentExperience(
                id=3,
                student_id=profile.id,
                company_name="Acme Corp",
                role_title="Frontend Developer",
                start_date=None,
                end_date=None,
                description="Built React dashboard components.",
            )
        ]
        _, b_no_dates, *_ = calculate_compatibility_score(
            job, user, profile, [], [], exp_no_dates, []
        )
        # Base technical 5.0 + duration 0.0 + description 0.0 = 5.0
        assert b_no_dates.experience == 5.0
        assert b_no_dates.experience <= 7.0

        # Case D: Description length invariance (descriptions of different lengths produce IDENTICAL scores)
        descriptions_to_test = [
            "A" * 250,                                      # Long description (> 200 chars)
            "A" * 50,                                       # Exactly 50 chars (former threshold)
            "Short text",                                   # Short description (10 chars)
            "",                                             # Empty string
            None,                                           # None description
        ]
        scores_by_desc = []
        for idx, desc in enumerate(descriptions_to_test):
            exp_item = [
                StudentExperience(
                    id=10 + idx,
                    student_id=profile.id,
                    company_name="Tech Corp",
                    role_title="Cloud Engineer Intern",
                    start_date="2024-01-01",
                    end_date="2024-04-30",
                    description=desc,
                )
            ]
            _, b_desc, *_ = calculate_compatibility_score(
                job, user, profile, [], [], exp_item, []
            )
            scores_by_desc.append(b_desc.experience)

        # All descriptions MUST produce the exact same objective score: 5.0 base + 2.0 duration = 7.0
        assert all(s == 7.0 for s in scores_by_desc), f"Expected all 7.0, got {scores_by_desc}"
        assert len(set(scores_by_desc)) == 1

        # Case E: Valid duration between 1 and 2 months (+1.0 duration point)
        exp_one_month = [
            StudentExperience(
                id=20,
                student_id=profile.id,
                company_name="Startup Ltd",
                role_title="Backend Developer Intern",
                start_date="2024-06-01",
                end_date="2024-06-25",
                description="Worked on APIs.",
            )
        ]
        _, b_one_mo, *_ = calculate_compatibility_score(
            job, user, profile, [], [], exp_one_month, []
        )
        # 5.0 tech role + 1.0 (1-month duration) = 6.0 points
        assert b_one_mo.experience == 6.0
        assert b_one_mo.experience <= 7.0

        # Case F: General role with 1-month duration
        exp_gen_one_mo = [
            StudentExperience(
                id=21,
                student_id=profile.id,
                company_name="Retail Inc",
                role_title="Store Assistant",
                start_date="2024-06-01",
                end_date="2024-06-25",
                description="Assisted in retail operations.",
            )
        ]
        _, b_gen_one_mo, *_ = calculate_compatibility_score(
            job, user, profile, [], [], exp_gen_one_mo, []
        )
        # 2.0 general role + 1.0 (1-month duration) = 3.0 points
        assert b_gen_one_mo.experience == 3.0
        assert b_gen_one_mo.experience <= 7.0

    def test_scoring_certification_relevance(self):
        job = build_job(
            skills=[JobSkill(id=1, job_id=1, skill_name="Python", is_mandatory=True)]
        )
        user, profile = build_student()

        # Case A: 1 relevant cloud certification
        cert_rel = [
            StudentCertification(
                id=1,
                student_id=profile.id,
                certificate_name="AWS Certified Cloud Practitioner",
                issuing_organization="Amazon Web Services",
            )
        ]
        _, b_rel, *_ = calculate_compatibility_score(
            job, user, profile, [], [], [], cert_rel
        )
        assert b_rel.certifications == 3.5

        # Case B: General non-tech certification
        cert_general = [
            StudentCertification(
                id=2,
                student_id=profile.id,
                certificate_name="Basic Workshop Attendance",
                issuing_organization="Campus Club",
            )
        ]
        _, b_gen, *_ = calculate_compatibility_score(
            job, user, profile, [], [], [], cert_general
        )
        assert b_gen.certifications == 1.5

    def test_scoring_determinism(self):
        job = build_job(
            skills=[
                JobSkill(id=1, job_id=1, skill_name="Python", is_mandatory=True),
                JobSkill(id=2, job_id=1, skill_name="PostgreSQL", is_mandatory=False),
            ]
        )
        user, profile = build_student(cgpa=8.4)
        skills = [StudentSkill(id=1, student_id=profile.id, skill_name="Python")]
        projects = [
            StudentProject(
                id=1,
                student_id=profile.id,
                title="App",
                technologies="Python",
                project_url="https://github.com",
            )
        ]

        scores = [
            calculate_compatibility_score(job, user, profile, skills, projects, [], [])[0]
            for _ in range(100)
        ]
        assert all(s == scores[0] for s in scores)

    def test_ineligible_student_retains_compatibility_score(self):
        # A student failing CGPA cutoff should still have their compatibility score computed
        job = build_job(
            min_cgpa=8.5,
            skills=[JobSkill(id=1, job_id=1, skill_name="Python", is_mandatory=True)],
        )
        user, profile = build_student(cgpa=6.5)
        skills = [StudentSkill(id=1, student_id=profile.id, skill_name="Python")]

        score, breakdown, *_ = calculate_compatibility_score(
            job, user, profile, skills, [], [], []
        )
        # Score is positive and explainable (not zeroed out)
        assert score > 50.0
        assert breakdown.skills == 50.0
        assert breakdown.academics > 0.0

    def test_scoring_normalization_formula_and_bounds(self):
        """
        Verify the exact normalization formula: compatibility_score = (raw_score / 97.0) * 100.0.
        - Zero raw score = 0.0%
        - Maximum raw score of 97 = 100.0%
        - Intermediate scores are normalized accurately
        - Scores strictly stay within [0.0, 100.0]
        """
        job = build_job(
            skills=[
                JobSkill(id=1, job_id=1, skill_name="Python", is_mandatory=True),
                JobSkill(id=2, job_id=1, skill_name="PostgreSQL", is_mandatory=True),
            ]
        )
        user, profile = build_student(cgpa=0.0, active_backlogs=5, total_backlogs=5)

        # 1. Zero raw score: no skills, 0 cgpa with excessive backlogs, no projects/exp/certs
        score_zero, b_zero, *_ = calculate_compatibility_score(
            job=job,
            student_user=user,
            student_profile=profile,
            approved_skills=[],
            approved_projects=[],
            approved_experiences=[],
            approved_certifications=[],
        )
        raw_zero = b_zero.skills + b_zero.academics + b_zero.projects + b_zero.experience + b_zero.certifications
        assert raw_zero == 0.0
        assert score_zero == 0.0

        # 2. Maximum raw score: 50 + 20 + 15 + 7 + 5 = 97.0 raw -> 100.0% normalized
        user_max, prof_max = build_student(cgpa=10.0, active_backlogs=0, total_backlogs=0)
        skills_max = [
            StudentSkill(id=1, student_id=prof_max.id, skill_name="Python", proficiency_level="expert"),
            StudentSkill(id=2, student_id=prof_max.id, skill_name="PostgreSQL", proficiency_level="expert"),
        ]
        proj_max = [
            StudentProject(
                id=1, student_id=prof_max.id, title="P1", technologies="Python, PostgreSQL",
                project_url="https://github.com/test", description="A" * 60
            )
        ]
        exp_max = [
            StudentExperience(
                id=1, student_id=prof_max.id, role_title="Python Developer",
                start_date="2024-01-01", end_date="2024-06-30", description="Tech work"
            )
        ]
        cert_max = [
            StudentCertification(id=1, student_id=prof_max.id, certificate_name="AWS Certified Developer", issuing_organization="AWS"),
            StudentCertification(id=2, student_id=prof_max.id, certificate_name="CKA", issuing_organization="Linux Foundation"),
        ]
        score_max, b_max, *_ = calculate_compatibility_score(
            job=job,
            student_user=user_max,
            student_profile=prof_max,
            approved_skills=skills_max,
            approved_projects=proj_max,
            approved_experiences=exp_max,
            approved_certifications=cert_max,
        )
        raw_max = b_max.skills + b_max.academics + b_max.projects + b_max.experience + b_max.certifications
        assert raw_max == 97.0
        assert score_max == 100.0

        # 3. Intermediate score: only skills (50.0 raw) -> (50.0 / 97.0) * 100 = 51.55%
        score_inter, b_inter, *_ = calculate_compatibility_score(
            job=job,
            student_user=user,
            student_profile=profile,
            approved_skills=skills_max,
            approved_projects=[],
            approved_experiences=[],
            approved_certifications=[],
        )
        raw_inter = b_inter.skills + b_inter.academics + b_inter.projects + b_inter.experience + b_inter.certifications
        assert raw_inter == 50.0
        expected_normalized = round((50.0 / 97.0) * 100.0, 2)
        assert expected_normalized == 51.55
        assert score_inter == 51.55

        # 4. Range and bounds verification
        assert 0.0 <= score_zero <= 100.0
        assert 0.0 <= score_inter <= 100.0
        assert 0.0 <= score_max <= 100.0


# =============================================================================
# 3. API Route Integration & Security Tests
# =============================================================================

class TestPlacementIntelligenceRoutes:
    def test_route_evaluate_student_own_profile(self):
        job = build_job()
        user, profile = build_student()

        mock_db = AsyncMock()
        mock_job_result = MagicMock()
        mock_job_result.scalar_one_or_none.return_value = job

        mock_prof_result = MagicMock()
        mock_prof_result.scalar_one_or_none.return_value = profile

        mock_db.execute.side_effect = [mock_job_result, mock_prof_result]

        res = _run_sync(
            evaluate_job_match(
                job_id=1,
                student_id=None,
                current_user=user,
                db=mock_db,
            )
        )
        assert res.job_id == 1
        assert res.student_name == user.full_name
        assert 0.0 <= res.compatibility_score <= 100.0

    def test_route_evaluate_recruiter_blocked(self):
        recruiter = User(id=201, role=UserRole.RECRUITER, email="recruiter@acme.com", full_name="Recruiter One")
        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            _run_sync(
                evaluate_job_match(
                    job_id=1,
                    student_id=10,
                    current_user=recruiter,
                    db=mock_db,
                )
            )
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "RECRUITER_EVALUATION_RESTRICTED"

    def test_route_evaluate_tpo_cross_institution_blocked(self):
        tpo = User(id=301, role=UserRole.TPO, institution_id=1, email="tpo@inst1.edu", full_name="TPO Inst1")
        target_student_user, target_profile = build_student(user_id=102, institution_id=2)  # Different institution
        job = build_job()

        mock_db = AsyncMock()
        mock_job_result = MagicMock()
        mock_job_result.scalar_one_or_none.return_value = job

        mock_prof_result = MagicMock()
        mock_prof_result.scalar_one_or_none.return_value = target_profile

        mock_db.execute.side_effect = [mock_job_result, mock_prof_result]

        with pytest.raises(HTTPException) as exc_info:
            _run_sync(
                evaluate_job_match(
                    job_id=1,
                    student_id=target_profile.id,
                    current_user=tpo,
                    db=mock_db,
                )
            )
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "CROSS_INSTITUTION_ACCESS_DENIED"

    def test_route_recommended_jobs_partitioning(self):
        user, profile = build_student(cgpa=8.0)
        # Job 1: Eligible
        job_eligible = build_job(id=1, min_cgpa=7.0, title="Job Eligible")
        # Job 2: Ineligible (due to high CGPA cutoff)
        job_ineligible = build_job(id=2, min_cgpa=9.5, title="Job Ineligible")

        mock_db = AsyncMock()
        mock_prof_res = MagicMock()
        mock_prof_res.scalar_one_or_none.return_value = profile

        mock_jobs_res = MagicMock()
        mock_jobs_res.scalars.return_value.all.return_value = [job_eligible, job_ineligible]

        mock_db.execute.side_effect = [mock_prof_res, mock_jobs_res]

        res = _run_sync(
            get_recommended_jobs(
                current_user=user,
                db=mock_db,
            )
        )
        assert res.total_eligible == 1
        assert res.total_ineligible == 1
        assert res.eligible_jobs[0].job_id == 1
        assert res.ineligible_jobs[0].job_id == 2
        assert len(res.ineligible_jobs[0].reasons) > 0

    def test_route_candidate_intelligence_tpo_ranking(self):
        tpo = User(id=301, role=UserRole.TPO, institution_id=1, email="tpo@inst1.edu", full_name="TPO Inst1")
        job = build_job(institution_id=1)

        # 3 candidates:
        # Candidate 1: Eligible, high score
        u1, p1 = build_student(user_id=101, full_name="Rohan Mehta", cgpa=9.2)
        # Candidate 2: Eligible, lower score
        u2, p2 = build_student(user_id=102, full_name="Simran Kaur", cgpa=7.8)
        # Candidate 3: Ineligible (CGPA 6.0 vs min 7.0)
        u3, p3 = build_student(user_id=103, full_name="Amit Sharma", cgpa=6.0)

        mock_db = AsyncMock()
        mock_job_res = MagicMock()
        mock_job_res.scalar_one_or_none.return_value = job

        mock_students_res = MagicMock()
        mock_students_res.scalars.return_value.all.return_value = [p1, p2, p3]

        mock_db.execute.side_effect = [mock_job_res, mock_students_res]

        res = _run_sync(
            get_candidate_intelligence_for_job(
                job_id=1,
                current_user=tpo,
                db=mock_db,
            )
        )
        assert res.total_candidates == 3
        assert res.eligible_count == 2
        assert res.ineligible_count == 1
        assert res.ranked_eligible_candidates[0].student_name == "Rohan Mehta"
        assert res.ranked_eligible_candidates[0].rank == 1
        assert res.ranked_eligible_candidates[1].student_name == "Simran Kaur"
        assert res.ranked_eligible_candidates[1].rank == 2
        assert res.ineligible_candidates[0].student_name == "Amit Sharma"

    def test_route_candidate_intelligence_cross_campus_blocked(self):
        tpo = User(id=301, role=UserRole.TPO, institution_id=1, email="tpo@inst1.edu", full_name="TPO Inst1")
        # Job exclusive to campus 2
        job_campus2 = build_job(institution_id=2)

        mock_db = AsyncMock()
        mock_job_res = MagicMock()
        mock_job_res.scalar_one_or_none.return_value = job_campus2
        mock_db.execute.return_value = mock_job_res

        with pytest.raises(HTTPException) as exc_info:
            _run_sync(
                get_candidate_intelligence_for_job(
                    job_id=1,
                    current_user=tpo,
                    db=mock_db,
                )
            )
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "CROSS_INSTITUTION_ACCESS_DENIED"
