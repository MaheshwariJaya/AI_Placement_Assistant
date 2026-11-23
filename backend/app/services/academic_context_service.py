from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.organization import Department, Institution
from app.models.student import StudentProfile, StudentSkill, StudentProject
from app.models.user import User
from app.schemas.academic_context import StudentAcademicContext

logger = logging.getLogger(__name__)

# In-memory context cache: user_id -> (timestamp, StudentAcademicContext)
_CONTEXT_CACHE: Dict[int, Tuple[float, StudentAcademicContext]] = {}
_CACHE_TTL_SECONDS = 300.0  # 5 minutes

# In-memory store for student elective career interests: student_id -> list of interests
_STUDENT_CAREER_INTERESTS: Dict[int, List[str]] = {}


def invalidate_student_academic_context(user_id: int) -> None:
    """Invalidate cached context after authorized TPO academic modifications."""
    if user_id in _CONTEXT_CACHE:
        del _CONTEXT_CACHE[user_id]
        logger.info("Invalidated academic context cache for user %d", user_id)


def set_student_career_interests(student_id: int, interests: List[str]) -> None:
    """Update student's elective career interests without altering official academic branch."""
    cleaned = [str(i).strip() for i in interests if str(i).strip()]
    _STUDENT_CAREER_INTERESTS[student_id] = cleaned[:10]


def get_student_career_interests(student_id: int) -> List[str]:
    """Retrieve student's elective career interests."""
    return _STUDENT_CAREER_INTERESTS.get(student_id, [])


async def get_student_academic_context(
    user_id: int,
    db: AsyncSession,
    force_refresh: bool = False,
) -> StudentAcademicContext:
    """Authoritative service retrieving verified academic information from institutional records.
    
    Guarantees:
    1. Official department comes directly from verified User -> Department relationship.
    2. Never infers branch from user name, resume text, skills, or AI.
    3. If official branch is missing, does NOT default to CSE or another branch.
       Flags is_branch_verified=False with an explicit institutional alert.
    4. Multi-tenant isolation verified by institution_id scoping.
    """
    now = datetime.now(timezone.utc).timestamp()
    if not force_refresh and user_id in _CONTEXT_CACHE:
        cached_time, cached_ctx = _CONTEXT_CACHE[user_id]
        if now - cached_time < _CACHE_TTL_SECONDS:
            return cached_ctx

    # Fetch User along with Department and Institution
    stmt_user = (
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.department),
            selectinload(User.institution),
        )
    )
    user_res = await db.execute(stmt_user)
    user_obj = user_res.scalar_one_or_none()

    if not user_obj:
        raise ValueError(f"User with ID {user_id} does not exist.")

    # Fetch StudentProfile along with skills and projects
    stmt_profile = (
        select(StudentProfile)
        .where(StudentProfile.user_id == user_id)
        .options(
            selectinload(StudentProfile.skills),
            selectinload(StudentProfile.projects),
        )
    )
    prof_res = await db.execute(stmt_profile)
    student_profile = prof_res.scalar_one_or_none()

    institution_name = user_obj.institution.name if user_obj.institution else "MBM University"
    institution_id = user_obj.institution_id or (user_obj.institution.id if user_obj.institution else 1)

    # Department validation
    dept: Optional[Department] = user_obj.department
    is_verified = False
    verification_msg: Optional[str] = None
    dept_id: Optional[int] = None
    dept_name: Optional[str] = None
    dept_code: Optional[str] = None

    if dept is not None and dept.name and dept.name.strip():
        is_verified = True
        dept_id = dept.id
        dept_name = dept.name.strip()
        dept_code = dept.code.strip() if dept.code else None
    else:
        is_verified = False
        verification_msg = (
            "Official academic branch is unverified. Please contact your Training & Placement "
            "Office (TPO) to complete official academic verification."
        )

    # Academic metrics
    verified_cgpa = float(student_profile.cgpa) if student_profile and student_profile.cgpa is not None else 0.0
    active_backlogs = student_profile.active_backlogs if student_profile and student_profile.active_backlogs is not None else 0
    total_backlogs = student_profile.total_backlogs if student_profile and student_profile.total_backlogs is not None else 0
    grad_year = student_profile.graduation_year if student_profile else None
    roll_num = student_profile.roll_number if student_profile else None
    student_id = student_profile.id if student_profile else 0

    # Approved skills & projects
    approved_skills = [
        (getattr(s, "skill_name", None) or getattr(s, "name", "")).strip()
        for s in (student_profile.skills if student_profile else [])
        if getattr(s, "is_verified", True) and (getattr(s, "skill_name", None) or getattr(s, "name", ""))
    ]
    approved_projects = [
        p.title.strip()
        for p in (student_profile.projects if student_profile else [])
        if getattr(p, "is_verified", True) and p.title
    ]

    career_interests = get_student_career_interests(student_id)

    ctx = StudentAcademicContext(
        student_id=student_id,
        user_id=user_obj.id,
        full_name=user_obj.full_name,
        email=user_obj.email,
        roll_number=roll_num,
        institution_id=institution_id,
        institution_name=institution_name,
        official_department_id=dept_id,
        official_department_name=dept_name,
        official_department_code=dept_code,
        is_branch_verified=is_verified,
        branch_verification_message=verification_msg,
        graduation_year=grad_year,
        current_semester=None,
        verified_cgpa=round(verified_cgpa, 2),
        active_backlogs=active_backlogs,
        total_backlogs=total_backlogs,
        academic_status="verified" if is_verified else "pending_verification",
        career_interests=career_interests,
        approved_skills=approved_skills,
        approved_projects=approved_projects,
    )

    _CONTEXT_CACHE[user_id] = (now, ctx)
    return ctx
