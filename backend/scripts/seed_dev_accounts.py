"""
Optional Development Seeder: Local Development Accounts

USAGE (MANUAL/LOCAL DEV ONLY):
    python backend/scripts/seed_dev_accounts.py

PURPOSE:
    This script is strictly isolated from production and application startup.
    It provisions base development accounts for offline testing across all 4 system roles:
    - Student:   student.demo@apex.edu
    - TPO:       tpo.officer@apex.edu
    - Recruiter: recruiter.demo@techhire.io
    - Admin:     admin@placement.local

DO NOT execute or import this script in production environments.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.company import Company, RecruiterProfile
from app.models.organization import Department, Institution
from app.models.student import StudentProfile
from app.models.user import User, UserRole

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_dev_accounts")

DEV_PASSWORD = "CollegeDemo2026!"


async def seed_dev_accounts():
    async with AsyncSessionLocal() as session:
        pwd_hash = hash_password(DEV_PASSWORD)

        inst_stmt = select(Institution).where(Institution.id == 1)
        inst = (await session.execute(inst_stmt)).scalar_one_or_none()
        if not inst:
            logger.error("Base institution missing. Run ensure_system_reference_metadata first.")
            return

        cse_dept = (await session.execute(
            select(Department).where(Department.institution_id == inst.id, Department.code == "CSE")
        )).scalar_one_or_none()

        # 1. TPO Officer
        tpo_stmt = select(User).where(User.email == "tpo.officer@apex.edu")
        if not (await session.execute(tpo_stmt)).scalar_one_or_none():
            session.add(User(
                email="tpo.officer@apex.edu",
                hashed_password=pwd_hash,
                full_name="Dr. Rajesh Sharma (TPO)",
                role=UserRole.TPO,
                institution_id=inst.id,
                department_id=None,
                is_active=True,
                is_verified=True,
            ))
            logger.info("Created dev TPO user: tpo.officer@apex.edu")

        # 2. Platform Admin
        admin_stmt = select(User).where(User.email == "admin@placement.local")
        if not (await session.execute(admin_stmt)).scalar_one_or_none():
            session.add(User(
                email="admin@placement.local",
                hashed_password=pwd_hash,
                full_name="Platform Administrator",
                role=UserRole.ADMIN,
                institution_id=None,
                department_id=None,
                is_active=True,
                is_verified=True,
            ))
            logger.info("Created dev Admin user: admin@placement.local")

        # 3. Recruiter
        rec_stmt = select(User).where(User.email == "recruiter.demo@techhire.io")
        if not (await session.execute(rec_stmt)).scalar_one_or_none():
            comp_stmt = select(Company).where(Company.name == "TechHire Global Solutions")
            comp = (await session.execute(comp_stmt)).scalar_one_or_none()
            if not comp:
                comp = Company(
                    name="TechHire Global Solutions",
                    industry="Technology & Recruiting",
                    description="Recruiting partner workspace.",
                    website="https://techhire.io",
                    location="Bengaluru, India",
                    company_size="501-1000",
                    contact_email="recruiter.demo@techhire.io",
                    is_verified=True,
                    is_active=True,
                )
                session.add(comp)
                await session.flush()

            rec_user = User(
                email="recruiter.demo@techhire.io",
                hashed_password=pwd_hash,
                full_name="Sarah Jenkins (TechHire Recruiter)",
                role=UserRole.RECRUITER,
                institution_id=None,
                department_id=None,
                is_active=True,
                is_verified=True,
            )
            session.add(rec_user)
            await session.flush()

            session.add(RecruiterProfile(
                user_id=rec_user.id,
                company_id=comp.id,
                designation="Campus Talent Acquisition Partner",
                corporate_phone="+91-9876543210",
            ))
            logger.info("Created dev Recruiter user: recruiter.demo@techhire.io")

        # 4. Student
        stu_stmt = select(User).where(User.email == "student.demo@apex.edu")
        if not (await session.execute(stu_stmt)).scalar_one_or_none():
            stu_user = User(
                email="student.demo@apex.edu",
                hashed_password=pwd_hash,
                full_name="Aarav Mehta (Student Demo)",
                role=UserRole.STUDENT,
                institution_id=inst.id,
                department_id=cse_dept.id if cse_dept else None,
                is_active=True,
                is_verified=True,
            )
            session.add(stu_user)
            await session.flush()

            session.add(StudentProfile(
                user_id=stu_user.id,
                roll_number="24UCSE4001",
                graduation_year=2026,
                cgpa=8.75,
                active_backlogs=0,
                total_backlogs=0,
                is_placement_ready=True,
            ))
            logger.info("Created dev Student user: student.demo@apex.edu")

        await session.commit()
        logger.info("Development test accounts seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed_dev_accounts())
