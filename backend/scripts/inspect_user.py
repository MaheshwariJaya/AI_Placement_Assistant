"""Script to inspect user details."""
import asyncio
import sys

sys.path.insert(0, "backend")

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.company import RecruiterProfile
from app.models.student import StudentProfile
from app.models.user import User


async def check():
    async with AsyncSessionLocal() as session:
        u = (
            await session.execute(
                select(User).where(User.email == "maheshwarijaya03@gmail.com")
            )
        ).scalar_one_or_none()
        if u:
            print(f"User: id={u.id}, email={u.email}, role={u.role}, institution_id={u.institution_id}, department_id={u.department_id}")
            sp = (
                await session.execute(
                    select(StudentProfile).where(StudentProfile.user_id == u.id)
                )
            ).scalar_one_or_none()
            print(f"StudentProfile: {sp.id if sp else None}, roll={sp.roll_number if sp else None}")
            rp = (
                await session.execute(
                    select(RecruiterProfile).where(RecruiterProfile.user_id == u.id)
                )
            ).scalar_one_or_none()
            print(f"RecruiterProfile: {rp.id if rp else None}")
        else:
            print("User not found!")


if __name__ == "__main__":
    asyncio.run(check())
