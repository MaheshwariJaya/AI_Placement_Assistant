"""
Grant full platform access to Jaya Maheshwari (maheshwarijaya03@gmail.com):
  - Sets role to ADMIN (full platform scope, TPO, and Admin authority)
  - Scoped to MBM University (Institution ID: 1) and CSE (Department ID: 1)
  - Preserves StudentProfile (roll: 24UCSE4058, Class of 2027)
  - Attaches a RecruiterProfile for corporate workspace access
"""
import asyncio
import sys

sys.path.insert(0, "backend")

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.company import Company, RecruiterProfile
from app.models.student import StudentProfile
from app.models.user import User, UserRole


async def grant_full_access():
    async with AsyncSessionLocal() as session:
        print("=" * 80)
        print("PROVISIONING FULL PLATFORM ACCESS FOR JAYA MAHESHWARI")
        print("=" * 80)

        user = (
            await session.execute(
                select(User).where(User.email == "maheshwarijaya03@gmail.com")
            )
        ).scalar_one_or_none()

        if not user:
            print("ERROR: User maheshwarijaya03@gmail.com not found!")
            return

        # 1. Update Role to ADMIN (grants Admin & TPO staff authority system-wide)
        user.role = UserRole.ADMIN
        user.is_verified = True
        user.is_active = True
        if not user.institution_id:
            user.institution_id = 1
        if not user.department_id:
            user.department_id = 1

        print(f"✓ Updated User: id={user.id}, email={user.email}, role={user.role.value}")
        print(f"  - Institution ID: {user.institution_id} (MBM University)")
        print(f"  - Department ID:  {user.department_id} (Computer Science & Engineering)")

        # 2. Verify Student Profile
        sp = (
            await session.execute(
                select(StudentProfile).where(StudentProfile.user_id == user.id)
            )
        ).scalar_one_or_none()

        if sp:
            print(f"✓ Preserved StudentProfile: id={sp.id}, roll={sp.roll_number}, cgpa={sp.cgpa}, grad_year={sp.graduation_year}")
        else:
            print("WARNING: StudentProfile not found, preserving user record.")

        # 3. Ensure Recruiter Profile for complete corporate hiring platform access
        rp = (
            await session.execute(
                select(RecruiterProfile).where(RecruiterProfile.user_id == user.id)
            )
        ).scalar_one_or_none()

        if not rp:
            first_comp = (
                await session.execute(select(Company).order_by(Company.id.asc()).limit(1))
            ).scalar_one_or_none()
            if first_comp:
                rp = RecruiterProfile(
                    user_id=user.id,
                    company_id=first_comp.id,
                    designation="Platform Super-Administrator & Talent Partner",
                )
                session.add(rp)
                print(f"✓ Provisioned RecruiterProfile for company '{first_comp.name}' (ID: {first_comp.id})")

        await session.commit()
        print("=" * 80)
        print("✨ SUCCESS: Full multi-platform access successfully granted to Jaya Maheshwari!")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(grant_full_access())
