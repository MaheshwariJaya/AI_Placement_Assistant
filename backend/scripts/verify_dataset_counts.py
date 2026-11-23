"""Verification script for synthetic dataset audit."""
import asyncio
import sys

sys.path.insert(0, "backend")

from sqlalchemy import func, select
from app.core.database import AsyncSessionLocal
from app.models.company import Company
from app.models.job import Job
from app.models.organization import Department
from app.models.placement import ApplicationStatus, JobApplication, PlacementDrive
from app.models.student import StudentProfile
from app.models.user import User


async def verify():
    async with AsyncSessionLocal() as session:
        print("\n" + "=" * 80)
        print("DATABASE INTEGRITY & DATASET COUNT VERIFICATION")
        print("=" * 80)

        # Real Student
        real_user = (
            await session.execute(
                select(User).where(User.email == "maheshwarijaya03@gmail.com")
            )
        ).scalar_one_or_none()
        print(f"1. Real Student Account (Jaya Maheshwari): {'PRESERVED ✓' if real_user else 'MISSING ✗'}")

        # Real TPO
        tpo_user = (
            await session.execute(
                select(User).where(User.email == "tpo.officer@apex.edu")
            )
        ).scalar_one_or_none()
        print(f"2. Real TPO Account (Prof. Rajesh Sharma): {'PRESERVED ✓' if tpo_user else 'MISSING ✗'}")

        # Synthetic Students
        synth_students = (
            await session.execute(
                select(func.count(User.id)).where(User.email.like("%@campus.example.test"))
            )
        ).scalar()
        print(f"3. Synthetic Students Count: {synth_students} (Expected: 100)")

        # Branch breakdown of synthetic students
        depts = (
            await session.execute(
                select(Department.code, func.count(User.id))
                .join(User, User.department_id == Department.id)
                .where(User.email.like("%@campus.example.test"))
                .group_by(Department.code)
                .order_by(func.count(User.id).desc())
            )
        ).all()
        print("   - Branch Breakdown:")
        for code, count in depts:
            print(f"     * {code:6s}: {count:2d}")

        # Synthetic Recruiters
        synth_recruiters = (
            await session.execute(
                select(func.count(User.id)).where(User.email.like("%@partner.example.test"))
            )
        ).scalar()
        print(f"4. Synthetic Recruiters Count: {synth_recruiters} (Expected: 100)")

        # Synthetic Companies
        synth_companies = (
            await session.execute(
                select(func.count(Company.id)).where(Company.name.like("%[Synthetic]%"))
            )
        ).scalar()
        print(f"5. Synthetic Companies Count: {synth_companies} (Expected: 100)")

        # Published Jobs
        synth_jobs = (
            await session.execute(
                select(func.count(Job.id)).where(
                    Job.created_by_user_id.in_(
                        select(User.id).where(User.email.like("%@partner.example.test"))
                    )
                )
            )
        ).scalar()
        print(f"6. Synthetic Published Jobs Count: {synth_jobs} (Expected: 150-170)")

        # Application Status Distribution
        app_dist = (
            await session.execute(
                select(JobApplication.current_status, func.count(JobApplication.id))
                .join(StudentProfile, JobApplication.student_id == StudentProfile.id)
                .join(User, StudentProfile.user_id == User.id)
                .where(User.email.like("%@campus.example.test"))
                .group_by(JobApplication.current_status)
            )
        ).all()
        total_apps = sum(c for _, c in app_dist)
        print(f"7. Synthetic Applications Total: {total_apps} (Expected: 305)")
        print("   - Status Distribution:")
        for status, count in sorted(app_dist, key=lambda x: str(x[0])):
            print(f"     * {str(status.value if hasattr(status, 'value') else status):20s}: {count:2d}")

        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(verify())
