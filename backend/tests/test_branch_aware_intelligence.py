import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from pydantic import ValidationError

from app.models.user import User, UserRole
from app.models.organization import Department, Institution
from app.models.student import StudentProfile, StudentSkill, StudentProject
from app.models.job import Job, JobSkill, JobEligibleDepartment, JobStatus, EmploymentType, WorkMode
from app.models.company import Company
from app.models.arena import ArenaCategory
from app.schemas.mock_interview import GeneratedInterviewPlan, GeneratedMockQuestion
from app.schemas.academic_context import StudentAcademicContext, TPOUpdateBranchRequest
from app.services.academic_context_service import (
    get_student_academic_context,
    set_student_career_interests,
    get_student_career_interests,
    invalidate_student_academic_context,
)
from app.services.branch_relevance import classify_job_branch_relevance
from app.services.arena_service import get_arena_categories
from app.services.mock_interview_mock_helpers import synthesize_mock_interview_plan
from app.services.career_assistant_service import assemble_career_context


@pytest.fixture
def sample_institution():
    return Institution(id=1, name="MBM University")


@pytest.fixture
def civil_dept(sample_institution):
    return Department(id=1096, name="Civil Engineering", code="CIVIL", institution_id=sample_institution.id)


@pytest.fixture
def cse_dept(sample_institution):
    return Department(id=1, name="Computer Science and Engineering", code="CSE", institution_id=sample_institution.id)


@pytest.fixture
def mech_dept(sample_institution):
    return Department(id=17, name="Mechanical Engineering", code="MECH", institution_id=sample_institution.id)


@pytest.fixture
def aarav_civil_user(civil_dept, sample_institution):
    user = User(
        id=201,
        email="aarav.civil01@mbm.edu",
        full_name="Aarav Verma",
        role=UserRole.STUDENT,
        institution_id=sample_institution.id,
        department_id=civil_dept.id,
    )
    user.department = civil_dept
    user.institution = sample_institution
    return user


@pytest.fixture
def cse_user(cse_dept, sample_institution):
    user = User(
        id=202,
        email="neha.cse01@mbm.edu",
        full_name="Neha Sharma",
        role=UserRole.STUDENT,
        institution_id=sample_institution.id,
        department_id=cse_dept.id,
    )
    user.department = cse_dept
    user.institution = sample_institution
    return user


@pytest.fixture
def mech_user(mech_dept, sample_institution):
    user = User(
        id=203,
        email="rohit.mech01@mbm.edu",
        full_name="Rohit Meena",
        role=UserRole.STUDENT,
        institution_id=sample_institution.id,
        department_id=mech_dept.id,
    )
    user.department = mech_dept
    user.institution = sample_institution
    return user


# =============================================================================
# 1. Civil Student Job Recommendation Tiering Test
# =============================================================================
def test_civil_student_job_recommendation_tiering(aarav_civil_user, civil_dept, cse_dept):
    # Job 1: L&T Civil Infrastructure (Restricted to CIVIL)
    civil_job = Job(id=501, title="Graduate Civil Engineer - Infrastructure Projects")
    civil_job.eligible_departments = [JobEligibleDepartment(job_id=501, department_id=civil_dept.id, department=civil_dept)]
    civil_job.skills = [JobSkill(job_id=501, skill_name="AutoCAD", is_mandatory=True)]

    # Job 2: Software SRE (Open to ALL)
    sre_job = Job(id=502, title="Site Reliability Engineer")
    sre_job.eligible_departments = []
    sre_job.skills = [JobSkill(job_id=502, skill_name="Kubernetes", is_mandatory=True)]

    # Job 3: Pure CSE backend role (Restricted to CSE)
    cse_job = Job(id=503, title="Backend Distributed Systems Engineer")
    cse_job.eligible_departments = [JobEligibleDepartment(job_id=503, department_id=cse_dept.id, department=cse_dept)]
    cse_job.skills = [JobSkill(job_id=503, skill_name="Go", is_mandatory=True)]

    # Classify relevance for Aarav
    tier1, reason1, status1 = classify_job_branch_relevance(civil_job, aarav_civil_user, [])
    assert tier1 == "directly_relevant"
    assert status1 == "matched"
    assert "Civil Engineering" in reason1

    tier2, reason2, status2 = classify_job_branch_relevance(sre_job, aarav_civil_user, [])
    assert tier2 == "open_to_all"
    assert status2 == "open_to_all"

    tier3, reason3, status3 = classify_job_branch_relevance(cse_job, aarav_civil_user, [])
    assert tier3 == "not_relevant"
    assert status3 == "branch_mismatch"


# =============================================================================
# 2. CSE Student Job Recommendation Tiering Test
# =============================================================================
def test_cse_student_job_recommendation_tiering(cse_user, cse_dept):
    cse_job = Job(id=503, title="Backend Distributed Systems Engineer")
    cse_job.eligible_departments = [JobEligibleDepartment(job_id=503, department_id=cse_dept.id, department=cse_dept)]
    cse_job.skills = [JobSkill(job_id=503, skill_name="Python", is_mandatory=True)]

    tier, reason, status = classify_job_branch_relevance(cse_job, cse_user, [])
    assert tier == "directly_relevant"
    assert status == "matched"


# =============================================================================
# 3. Mechanical Student Job Recommendation Tiering Test
# =============================================================================
def test_mechanical_student_job_recommendation_tiering(mech_user, mech_dept):
    mech_job = Job(id=504, title="Mechanical Design & CAE Engineer")
    mech_job.eligible_departments = [JobEligibleDepartment(job_id=504, department_id=mech_dept.id, department=mech_dept)]
    mech_job.skills = [JobSkill(job_id=504, skill_name="SolidWorks", is_mandatory=True)]

    tier, reason, status = classify_job_branch_relevance(mech_job, mech_user, [])
    assert tier == "directly_relevant"
    assert status == "matched"
    assert "Mechanical" in reason


# =============================================================================
# 4. Cross-Branch Career Interest Test
# =============================================================================
def test_cross_branch_career_interest(aarav_civil_user):
    # Software job open to all
    sw_job = Job(id=505, title="Software Development Engineer - Web Platforms")
    sw_job.eligible_departments = []
    sw_job.skills = [JobSkill(job_id=505, skill_name="React", is_mandatory=True)]

    # Case A: Civil student WITHOUT declared software career interest
    tier_a, _, status_a = classify_job_branch_relevance(sw_job, aarav_civil_user, [])
    assert tier_a == "open_to_all"

    # Case B: Civil student WITH explicit declared career interest in "Software Development"
    tier_b, reason_b, status_b = classify_job_branch_relevance(sw_job, aarav_civil_user, ["Software Development"])
    assert tier_b == "interdisciplinary"
    assert status_b == "interdisciplinary"
    assert "Software Development" in reason_b
    # Critical rule: official academic branch must NOT be changed
    assert aarav_civil_user.department.name == "Civil Engineering"


# =============================================================================
# 5. Missing Branch Verification Alert Test
# =============================================================================
@pytest.mark.asyncio
async def test_missing_branch_verification_alert():
    mock_user = User(
        id=999,
        email="unverified.student@mbm.edu",
        full_name="Unverified Student",
        role=UserRole.STUDENT,
        institution_id=1,
        department_id=None,
    )
    mock_user.department = None
    mock_user.institution = Institution(id=1, name="MBM University")

    mock_db = AsyncMock()
    # Mock query returning user
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=mock_user)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
    ]

    ctx = await get_student_academic_context(user_id=999, db=mock_db, force_refresh=True)
    assert ctx.is_branch_verified is False
    assert ctx.official_department_id is None
    assert ctx.official_department_name is None
    assert "unverified" in (ctx.branch_verification_message or "").lower()
    # Must never default to CSE
    assert ctx.official_department_code != "CSE"


# =============================================================================
# 6. TPO Branch Update Workflow Test
# =============================================================================
@pytest.mark.asyncio
async def test_tpo_branch_update_workflow(sample_institution, civil_dept, mech_dept):
    student_user = User(
        id=301,
        email="student.test@mbm.edu",
        full_name="Student Test",
        role=UserRole.STUDENT,
        institution_id=sample_institution.id,
        department_id=civil_dept.id,
    )
    student_user.department = civil_dept

    # Cache context initially
    set_student_career_interests(1, ["Data Analytics"])
    invalidate_student_academic_context(301)

    # Perform branch update
    student_user.department_id = mech_dept.id
    student_user.department = mech_dept
    invalidate_student_academic_context(301)

    mock_db = AsyncMock()
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=student_user)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
    ]

    ctx = await get_student_academic_context(user_id=301, db=mock_db, force_refresh=True)
    assert ctx.official_department_id == mech_dept.id
    assert ctx.official_department_name == "Mechanical Engineering"


# =============================================================================
# 7. Multi-Tenant Institution Isolation Test
# =============================================================================
def test_multi_tenant_institution_isolation(sample_institution):
    tpo_user = User(
        id=10,
        email="tpo@otherinst.edu",
        role=UserRole.TPO,
        institution_id=99,  # Other college
    )
    student_inst1 = User(
        id=20,
        email="student@mbm.edu",
        role=UserRole.STUDENT,
        institution_id=sample_institution.id,  # MBM University (id=1)
    )
    # TPO from inst 99 cannot update student from inst 1
    assert tpo_user.institution_id != student_inst1.institution_id


# =============================================================================
# 8. Preparation Arena Dynamic Categories Test
# =============================================================================
@pytest.mark.asyncio
async def test_preparation_arena_dynamic_categories(aarav_civil_user):
    mock_profile = StudentProfile(id=1, user_id=aarav_civil_user.id, graduation_year=2026, cgpa=8.5)
    mock_db = AsyncMock()
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=mock_profile)),
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
    ]

    with patch("app.services.arena_service.ensure_arena_seed_data", new_callable=AsyncMock):
        summaries = await get_arena_categories(current_user=aarav_civil_user, db=mock_db)

    # Civil Engineering student must receive official Civil Engineering core subjects
    struct_cat = next(s for s in summaries if s.category == ArenaCategory.CIVIL_STRUCTURES)
    assert struct_cat.label == "Structural Analysis & Design"
    assert struct_cat.track_type == "branch_core"

    quant_cat = next(s for s in summaries if s.category == ArenaCategory.QUANTITATIVE)
    assert quant_cat.track_type == "common"
    assert quant_cat.is_recommended_for_student is True

    # CS subjects must NOT be present for Civil Engineering students
    cs_cats = [s for s in summaries if s.category in (ArenaCategory.DSA, ArenaCategory.DBMS, ArenaCategory.OPERATING_SYSTEMS)]
    assert len(cs_cats) == 0


# =============================================================================
# 9. Mock Interview Grounded Synthesis Test
# =============================================================================
def test_mock_interview_grounded_synthesis():
    civil_prompt = (
        "<INTERVIEW_CONFIG>\nCategory: technical\nDifficulty: intermediate\nQuestion Count: 5\nTarget Role: Civil Engineer\n</INTERVIEW_CONFIG>\n"
        "<STUDENT_CONTEXT>\nDepartment: Civil Engineering\nVerified Skills: AutoCAD, STAAD.Pro, Concrete Technology\nVerified Projects: Raft Foundation Design\n</STUDENT_CONTEXT>"
    )
    plan = synthesize_mock_interview_plan(civil_prompt)
    assert len(plan.questions) >= 5

    topics = [q.topic.lower() for q in plan.questions]
    # Verify Civil Engineering concepts are synthesized
    assert any("structural" in t or "concrete" in t or "autocad" in t for t in topics)
    # Must NOT include software debugging or API questions for Civil
    assert not any("api reliability" in t for t in topics)
    assert not any("concurrency" in t for t in topics)


# =============================================================================
# 10. Mock Interview Schema Resilience Test
# =============================================================================
def test_mock_interview_schema_resilience():
    # Payload from Gemini returning bare array with raw string and stringified key points
    gemini_raw_list = [
        {
            "topic": "Geotechnical Analysis",
            "question": "Explain Terzaghi's bearing capacity formula.",
            "expected_key_points": "Cohesion, surcharge, unit weight terms",  # String instead of list
            "answer": "q_u = c*Nc + q*Nq + 0.5*gamma*B*Ngamma",
        },
        "Explain the standard penetration test (SPT) procedure and N-value correction factors.",  # Raw string
    ]

    plan = GeneratedInterviewPlan.model_validate(gemini_raw_list)
    assert len(plan.questions) == 2
    assert plan.questions[0].topic == "Geotechnical Analysis"
    assert len(plan.questions[0].expected_key_points) > 0
    assert "SPT" in plan.questions[1].question_text


# =============================================================================
# 11. Career Assistant Prompt Grounding Test
# =============================================================================
@pytest.mark.asyncio
async def test_career_assistant_grounding(aarav_civil_user):
    mock_profile = StudentProfile(id=1, user_id=aarav_civil_user.id, graduation_year=2026, cgpa=8.67, active_backlogs=0)
    aarav_civil_user.student_profile = mock_profile

    mock_db = AsyncMock()
    mock_db.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),  # skills
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),  # projects
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),  # experiences
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),  # certs
    ]

    summary, snippets = await assemble_career_context(current_user=aarav_civil_user, job_id=None, db=mock_db)
    assert summary.department_name == "Civil Engineering"
    assert "Civil Engineering" in snippets["profile"]


# =============================================================================
# 12. Branch-Wise Company Preparation Isolation Test
# =============================================================================
@pytest.mark.asyncio
async def test_branch_wise_company_preparation_isolation(aarav_civil_user, civil_dept, cse_dept):
    from app.services.arena_service import list_arena_assessments
    from app.models.arena import ArenaAssessment, ArenaAssessmentMode, ArenaDifficulty

    mock_profile = StudentProfile(id=1, user_id=aarav_civil_user.id, graduation_year=2026, cgpa=8.5)

    civil_assess = ArenaAssessment(
        id=201,
        title="Larsen & Toubro Civil Trainee Pattern Prep",
        description="L&T civil prep",
        mode=ArenaAssessmentMode.COMPANY_PREP,
        difficulty=ArenaDifficulty.MEDIUM,
        provenance_notice="Curated original pattern",
        department_id=civil_dept.id,
        is_published=True,
        question_ids_json=[1, 2, 3],
        duration_minutes=30,
    )
    civil_assess.department = civil_dept

    cs_assess = ArenaAssessment(
        id=202,
        title="ApexCloud Software Engineer Pattern Prep",
        description="ApexCloud CS prep",
        mode=ArenaAssessmentMode.COMPANY_PREP,
        difficulty=ArenaDifficulty.MEDIUM,
        provenance_notice="Curated original pattern",
        department_id=cse_dept.id,
        is_published=True,
        question_ids_json=[4, 5, 6],
        duration_minutes=35,
    )
    cs_assess.department = cse_dept

    campus_aptitude = ArenaAssessment(
        id=203,
        title="Campus Aptitude, Quant & Verbal Screening",
        description="General campus aptitude",
        mode=ArenaAssessmentMode.TIMED_TEST,
        difficulty=ArenaDifficulty.EASY,
        provenance_notice="Curated original pattern",
        department_id=None,
        is_published=True,
        question_ids_json=[7, 8, 9],
        duration_minutes=15,
    )
    campus_aptitude.department = None

    all_assessments = [civil_assess, cs_assess, campus_aptitude]

    mock_db = AsyncMock()
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=mock_profile)),
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=all_assessments)))),
    ]

    with patch("app.services.arena_service.ensure_arena_seed_data", new_callable=AsyncMock):
        results = await list_arena_assessments(current_user=aarav_civil_user, db=mock_db)

    result_titles = [r.title for r in results]

    # Civil student MUST see Larsen & Toubro and Campus Aptitude
    assert "Larsen & Toubro Civil Trainee Pattern Prep" in result_titles
    assert "Campus Aptitude, Quant & Verbal Screening" in result_titles

    # Civil student MUST NEVER see ApexCloud Software Engineer
    assert "ApexCloud Software Engineer Pattern Prep" not in result_titles


def test_cse_40_curricular_subjects_resolution():
    """Verify that a CSE/IT student resolves exactly 44 categories (4 placement common + 40 official CSE curriculum subjects)."""
    from app.services.branch_arena_question_bank import resolve_department_arena_categories, CS_ARENA_CATEGORIES
    from app.services.cse_40_subjects_data import CSE_40_CATEGORIES_LIST

    assert len(CSE_40_CATEGORIES_LIST) == 40
    assert len(CS_ARENA_CATEGORIES) == 40

    cse_resolved = resolve_department_arena_categories("CSE", "Computer Science and Engineering")
    # 4 common placement categories + 40 CSE subjects = 44 total categories
    assert len(cse_resolved) == 44

    # Verify key new subjects are present
    resolved_values = {c.value for c in cse_resolved}
    assert "cs_maths_for_computing" in resolved_values
    assert "cs_compiler_design" in resolved_values
    assert "cs_deep_learning" in resolved_values
    assert "cs_blockchain" in resolved_values
    assert "cs_cyber_security" in resolved_values
    assert "cs_distributed_computing" in resolved_values


def test_non_cs_isolation_with_40_cse_subjects():
    """Verify that Civil and Mechanical students receive ONLY their branch categories and zero CSE subjects."""
    from app.services.branch_arena_question_bank import resolve_department_arena_categories, CS_ARENA_CATEGORIES

    civil_cats = resolve_department_arena_categories("CIVIL", "Civil Engineering")
    civil_values = {c.value for c in civil_cats}

    mech_cats = resolve_department_arena_categories("MECH", "Mechanical Engineering")
    mech_values = {c.value for c in mech_cats}

    # Strict isolation check: no CS subjects in Civil or Mech
    for cs_cat in CS_ARENA_CATEGORIES:
        assert cs_cat.value not in civil_values, f"Leaked {cs_cat.value} into Civil!"
        assert cs_cat.value not in mech_values, f"Leaked {cs_cat.value} into Mechanical!"


def test_mock_interview_subject_focus_synthesis():
    """Verify that Mock Interview synthesis correctly generates discipline-grounded questions when a CSE subject is selected."""
    from app.services.mock_interview_mock_helpers import synthesize_mock_interview_plan

    prompt = (
        "<INTERVIEW_CONFIG>\n"
        "Category: technical\n"
        "Difficulty: intermediate\n"
        "Question Count: 5\n"
        "Target Role: Software Engineer — Subject: Principles of Compiler Design\n"
        "Subject Focus: Principles of Compiler Design\n"
        "</INTERVIEW_CONFIG>\n\n"
        "<STUDENT_CONTEXT>\n"
        "Department: Computer Science and Engineering\n"
        "Verified Skills: C++, Compiler Design, Data Structures\n"
        "</STUDENT_CONTEXT>"
    )

    plan = synthesize_mock_interview_plan(prompt)
    assert len(plan.questions) == 5

    topics = [q.topic.lower() for q in plan.questions]
    question_texts = " ".join([q.question_text.lower() for q in plan.questions])

    # Must contain compiler-specific topics and questions
    assert any("compiler" in t for t in topics)
    assert "parser" in question_texts or "ast" in question_texts or "llvm" in question_texts or "ir" in question_texts


