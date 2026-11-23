import logging
from typing import Dict

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.organization import Department, Institution

logger = logging.getLogger(__name__)


async def ensure_system_reference_metadata() -> None:
    """
    Idempotently ensures baseline collegiate institutional reference metadata exists:
    - Institution (MBM University)
    - Authorized academic engineering departments (CSE, CIVIL, EEE, ECE, MECH, etc.)

    Production startup requirement:
    Zero synthetic business records, zero fake users, zero demo companies.
    """
    try:
        async with AsyncSessionLocal() as session:
            # 1. Ensure Institution & Departments Exist
            inst_stmt = select(Institution).where(Institution.id == 1)
            inst = (await session.execute(inst_stmt)).scalar_one_or_none()
            if not inst:
                inst = Institution(
                    id=1,
                    name="MBM University",
                    code="MBMU",
                    city="Jodhpur",
                    is_active=True,
                )
                session.add(inst)
                await session.flush()

            branches = [
                ("CSE", "Computer Science and Engineering"),
                ("CIVIL", "Civil Engineering"),
                ("EEE", "Electrical Engineering"),
                ("ECE", "Electronics and Communication Engineering"),
                ("MECH", "Mechanical Engineering"),
                ("PIE", "Production & Industrial Engineering"),
                ("CHEM", "Chemical Engineering"),
                ("MINE", "Mining Engineering"),
                ("PETRO", "Petroleum Engineering"),
                ("STRUCT", "Structural Engineering"),
                ("ARCH_PLAN", "Architecture / Planning (Bachelor of Planning / Architecture)"),
                ("IT", "Information Technology"),
                ("AIML", "Artificial Intelligence & Machine Learning"),
                ("AIDS", "Artificial Intelligence & Data Science"),
            ]
            for code, name in branches:
                dept_stmt = select(Department).where(
                    Department.institution_id == inst.id,
                    Department.code == code,
                )
                dept = (await session.execute(dept_stmt)).scalar_one_or_none()
                if not dept:
                    dept = Department(
                        institution_id=inst.id,
                        name=name,
                        code=code,
                        is_active=True,
                    )
                    session.add(dept)
                    await session.flush()

            await session.commit()
            logger.info("Base institutional reference metadata verified.")
    except Exception as e:
        logger.warning(f"Database bootstrap reference check encountered non-critical error: {e}")


# Backwards compatibility alias for application lifespan
seed_demo_accounts = ensure_system_reference_metadata

