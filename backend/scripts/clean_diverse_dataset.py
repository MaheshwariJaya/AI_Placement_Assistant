"""
[ISOLATED DEVELOPMENT CLEANER - NOT FOR PRODUCTION STARTUP]
Dedicated, safe, and idempotent cleanup script for the synthetic placement testing dataset.
Safely removes ONLY synthetic testing data identified by reserved testing identifiers:
  - Users with domain '@campus.example.test' and '@partner.example.test'
  - Companies with '[Synthetic]' in the name or '.example.test' domains
  - Placement Drives with '[Synthetic]' in name
  - Roll numbers starting with '22SYNTH'
  - Associated applications, status histories, interviews, evaluations, resumes,
    skills, projects, experiences, certifications, education, arena attempts,
    and readiness snapshots.

EXPLICITLY PRESERVES:
  - System reference data (Institutions, Departments, System Roles)
  - Real administrative and TPO accounts (e.g. tpo.officer@apex.edu, admin@mbm.ac.in)
  - Real student accounts (e.g. maheshwarijaya03@gmail.com, roll 24UCSE4058)
  - Real recruiter and company accounts
  - System configuration and core database schema

Usage:
  python backend/scripts/clean_diverse_dataset.py [--dry-run] [--force-prod]
"""
import argparse
import asyncio
import os
import sys
from typing import Any, Dict, List, Set

sys.path.insert(0, "backend")

from sqlalchemy import delete, func, select, text
from app.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.arena import ArenaAttempt
from app.models.candidate_evaluation import CandidateEvaluation
from app.models.company import Company, RecruiterProfile
from app.models.job import Job, JobEligibleDepartment, JobSkill
from app.models.organization import Department, Institution
from app.models.placement import (
    ApplicationStatusHistory,
    Interview,
    JobApplication,
    PlacementDrive,
    PlacementDriveJob,
)
from app.models.readiness import ReadinessSnapshot
from app.models.resume import Resume
from app.models.student import (
    StudentCertification,
    StudentEducation,
    StudentExperience,
    StudentProfile,
    StudentProject,
    StudentSkill,
)
from app.models.user import User


async def clean_synthetic_dataset(dry_run: bool = False, force_prod: bool = False):
    settings = get_settings()
    app_env = getattr(settings, "APP_ENV", os.getenv("APP_ENV", "development")).lower()

    if app_env == "production" and not force_prod:
        print("=" * 80)
        print("FATAL ERROR: Cleaner script refused to execute in PRODUCTION environment.")
        print("To override in production, you must pass the --force-prod flag explicitly.")
        print("=" * 80)
        sys.exit(1)

    print("\n" + "=" * 80)
    print(f"🧹 SYNTHETIC PLACEMENT DATASET CLEANER [{'DRY RUN - NO CHANGES' if dry_run else 'LIVE EXECUTION'}]")
    print("=" * 80)

    stats: Dict[str, int] = {
        "candidate_evaluations": 0,
        "interviews": 0,
        "application_status_histories": 0,
        "job_applications": 0,
        "placement_drive_jobs": 0,
        "placement_drives": 0,
        "job_skills": 0,
        "job_eligible_departments": 0,
        "jobs": 0,
        "recruiter_profiles": 0,
        "companies": 0,
        "student_certifications": 0,
        "student_experiences": 0,
        "student_projects": 0,
        "student_skills": 0,
        "student_educations": 0,
        "resumes": 0,
        "arena_attempts": 0,
        "readiness_snapshots": 0,
        "student_profiles": 0,
        "synthetic_users": 0,
    }

    async with AsyncSessionLocal() as session:
        # 1. Identify Synthetic Student Users
        synth_student_users = (
            await session.execute(
                select(User).where(User.email.like("%@campus.example.test"))
            )
        ).scalars().all()
        synth_student_user_ids = [u.id for u in synth_student_users]

        # 2. Identify Synthetic Student Profiles
        synth_profiles = (
            await session.execute(
                select(StudentProfile).where(
                    (StudentProfile.user_id.in_(synth_student_user_ids))
                    | (StudentProfile.roll_number.like("22SYNTH%"))
                )
            )
        ).scalars().all()
        synth_profile_ids = [p.id for p in synth_profiles]

        # 3. Identify Synthetic Recruiter Users
        synth_recruiter_users = (
            await session.execute(
                select(User).where(User.email.like("%@partner.example.test"))
            )
        ).scalars().all()
        synth_recruiter_user_ids = [u.id for u in synth_recruiter_users]

        # 4. Identify Synthetic Companies
        synth_companies = (
            await session.execute(
                select(Company).where(
                    (Company.name.like("%[Synthetic]%"))
                    | (Company.website.like("%.example.test%"))
                    | (Company.contact_email.like("%.example.test%"))
                )
            )
        ).scalars().all()
        synth_company_ids = [c.id for c in synth_companies]

        # 5. Identify Synthetic Jobs
        synth_jobs = (
            await session.execute(
                select(Job).where(
                    (Job.company_id.in_(synth_company_ids))
                    | (Job.created_by_user_id.in_(synth_recruiter_user_ids))
                )
            )
        ).scalars().all()
        synth_job_ids = [j.id for j in synth_jobs]

        # 6. Identify Synthetic Placement Drives
        synth_drives = (
            await session.execute(
                select(PlacementDrive).where(
                    (PlacementDrive.name.like("%[Synthetic]%"))
                )
            )
        ).scalars().all()
        synth_drive_ids = [d.id for d in synth_drives]

        # 7. Identify Applications linked to synthetic students or synthetic jobs
        synth_applications = (
            await session.execute(
                select(JobApplication).where(
                    (JobApplication.student_id.in_(synth_profile_ids))
                    | (JobApplication.job_id.in_(synth_job_ids))
                )
            )
        ).scalars().all()
        synth_app_ids = [a.id for a in synth_applications]

        # 8. Identify Interviews & Evaluations
        synth_interviews = (
            await session.execute(
                select(Interview).where(
                    (Interview.application_id.in_(synth_app_ids))
                    | (Interview.created_by_user_id.in_(synth_recruiter_user_ids))
                )
            )
        ).scalars().all()
        synth_interview_ids = [i.id for i in synth_interviews]

        synth_evaluations = (
            await session.execute(
                select(CandidateEvaluation).where(
                    (CandidateEvaluation.application_id.in_(synth_app_ids))
                    | (CandidateEvaluation.interview_id.in_(synth_interview_ids))
                    | (CandidateEvaluation.interviewer_user_id.in_(synth_recruiter_user_ids))
                )
            )
        ).scalars().all()
        synth_evaluation_ids = [e.id for e in synth_evaluations]

        # Count records
        stats["candidate_evaluations"] = len(synth_evaluation_ids)
        stats["interviews"] = len(synth_interview_ids)
        stats["job_applications"] = len(synth_app_ids)

        if synth_app_ids:
            hist_res = await session.execute(
                select(func.count(ApplicationStatusHistory.id)).where(
                    ApplicationStatusHistory.application_id.in_(synth_app_ids)
                )
            )
            stats["application_status_histories"] = hist_res.scalar() or 0

        # Placement drive jobs
        if synth_drive_ids or synth_job_ids:
            pdj_res = await session.execute(
                select(func.count(PlacementDriveJob.id)).where(
                    (PlacementDriveJob.drive_id.in_(synth_drive_ids))
                    | (PlacementDriveJob.job_id.in_(synth_job_ids))
                )
            )
            stats["placement_drive_jobs"] = pdj_res.scalar() or 0
        stats["placement_drives"] = len(synth_drive_ids)

        # Job children
        if synth_job_ids:
            js_res = await session.execute(
                select(func.count(JobSkill.id)).where(JobSkill.job_id.in_(synth_job_ids))
            )
            stats["job_skills"] = js_res.scalar() or 0

            jed_res = await session.execute(
                select(func.count(JobEligibleDepartment.id)).where(
                    JobEligibleDepartment.job_id.in_(synth_job_ids)
                )
            )
            stats["job_eligible_departments"] = jed_res.scalar() or 0
        stats["jobs"] = len(synth_job_ids)

        # Companies & Recruiters
        if synth_company_ids or synth_recruiter_user_ids:
            rp_res = await session.execute(
                select(func.count(RecruiterProfile.id)).where(
                    (RecruiterProfile.company_id.in_(synth_company_ids))
                    | (RecruiterProfile.user_id.in_(synth_recruiter_user_ids))
                )
            )
            stats["recruiter_profiles"] = rp_res.scalar() or 0
        stats["companies"] = len(synth_company_ids)

        # Student Profile Children
        if synth_profile_ids:
            sc_res = await session.execute(
                select(func.count(StudentCertification.id)).where(
                    StudentCertification.student_id.in_(synth_profile_ids)
                )
            )
            stats["student_certifications"] = sc_res.scalar() or 0

            se_res = await session.execute(
                select(func.count(StudentExperience.id)).where(
                    StudentExperience.student_id.in_(synth_profile_ids)
                )
            )
            stats["student_experiences"] = se_res.scalar() or 0

            sp_res = await session.execute(
                select(func.count(StudentProject.id)).where(
                    StudentProject.student_id.in_(synth_profile_ids)
                )
            )
            stats["student_projects"] = sp_res.scalar() or 0

            ss_res = await session.execute(
                select(func.count(StudentSkill.id)).where(
                    StudentSkill.student_id.in_(synth_profile_ids)
                )
            )
            stats["student_skills"] = ss_res.scalar() or 0

            s_edu_res = await session.execute(
                select(func.count(StudentEducation.id)).where(
                    StudentEducation.student_id.in_(synth_profile_ids)
                )
            )
            stats["student_educations"] = s_edu_res.scalar() or 0

            res_res = await session.execute(
                select(func.count(Resume.id)).where(Resume.student_id.in_(synth_profile_ids))
            )
            stats["resumes"] = res_res.scalar() or 0

            aa_res = await session.execute(
                select(func.count(ArenaAttempt.id)).where(
                    ArenaAttempt.student_id.in_(synth_profile_ids)
                )
            )
            stats["arena_attempts"] = aa_res.scalar() or 0

            rs_res = await session.execute(
                select(func.count(ReadinessSnapshot.id)).where(
                    ReadinessSnapshot.student_id.in_(synth_profile_ids)
                )
            )
            stats["readiness_snapshots"] = rs_res.scalar() or 0

        stats["student_profiles"] = len(synth_profile_ids)
        all_synth_user_ids = list(set(synth_student_user_ids + synth_recruiter_user_ids))
        stats["synthetic_users"] = len(all_synth_user_ids)

        # Report Audit
        print("Identified Synthetic Records for Removal:")
        for entity, count in stats.items():
            print(f"  • {entity.replace('_', ' ').title():32s}: {count:4d}")

        if dry_run:
            print("\n[DRY RUN COMPLETE] No records were modified or deleted.")
            return stats

        # Perform Cascade Deletions in strict referential order
        print("\n--- Performing Referential Cascade Deletions ---")

        # 1. Candidate Evaluations
        if synth_evaluation_ids:
            await session.execute(
                delete(CandidateEvaluation).where(CandidateEvaluation.id.in_(synth_evaluation_ids))
            )
            await session.flush()
            print("✓ Deleted CandidateEvaluations.")

        # 2. Interviews
        if synth_interview_ids:
            await session.execute(delete(Interview).where(Interview.id.in_(synth_interview_ids)))
            await session.flush()
            print("✓ Deleted Interviews.")

        # 3. Application Status Histories & Job Applications
        if synth_app_ids:
            await session.execute(
                text(f"ALTER TABLE {settings.DB_SCHEMA}.application_status_history DISABLE TRIGGER trg_application_status_history_immutable;")
            )
            try:
                await session.execute(
                    delete(ApplicationStatusHistory).where(
                        ApplicationStatusHistory.application_id.in_(synth_app_ids)
                    )
                )
                await session.flush()
                print("✓ Deleted ApplicationStatusHistories.")
            finally:
                await session.execute(
                    text(f"ALTER TABLE {settings.DB_SCHEMA}.application_status_history ENABLE TRIGGER trg_application_status_history_immutable;")
                )

        # 4. Job Applications
        if synth_app_ids:
            await session.execute(
                delete(JobApplication).where(JobApplication.id.in_(synth_app_ids))
            )
            await session.flush()
            print("✓ Deleted JobApplications.")

        # 5. Placement Drive Jobs
        if synth_drive_ids or synth_job_ids:
            await session.execute(
                delete(PlacementDriveJob).where(
                    (PlacementDriveJob.drive_id.in_(synth_drive_ids))
                    | (PlacementDriveJob.job_id.in_(synth_job_ids))
                )
            )
            await session.flush()
            print("✓ Deleted PlacementDriveJobs.")

        # 6. Placement Drives
        if synth_drive_ids:
            await session.execute(
                delete(PlacementDrive).where(PlacementDrive.id.in_(synth_drive_ids))
            )
            await session.flush()
            print("✓ Deleted PlacementDrives.")

        # 7. Job Skills & Eligible Departments
        if synth_job_ids:
            await session.execute(delete(JobSkill).where(JobSkill.job_id.in_(synth_job_ids)))
            await session.execute(
                delete(JobEligibleDepartment).where(JobEligibleDepartment.job_id.in_(synth_job_ids))
            )
            await session.flush()
            print("✓ Deleted JobSkills and JobEligibleDepartments.")

        # 8. Jobs
        if synth_job_ids:
            await session.execute(delete(Job).where(Job.id.in_(synth_job_ids)))
            await session.flush()
            print("✓ Deleted Jobs.")

        # 9. Recruiter Profiles
        if synth_company_ids or synth_recruiter_user_ids:
            await session.execute(
                delete(RecruiterProfile).where(
                    (RecruiterProfile.company_id.in_(synth_company_ids))
                    | (RecruiterProfile.user_id.in_(synth_recruiter_user_ids))
                )
            )
            await session.flush()
            print("✓ Deleted RecruiterProfiles.")

        # 10. Companies
        if synth_company_ids:
            await session.execute(delete(Company).where(Company.id.in_(synth_company_ids)))
            await session.flush()
            print("✓ Deleted Companies.")

        # 11. Student Profile Sub-tables
        if synth_profile_ids:
            await session.execute(
                delete(StudentCertification).where(
                    StudentCertification.student_id.in_(synth_profile_ids)
                )
            )
            await session.execute(
                delete(StudentExperience).where(
                    StudentExperience.student_id.in_(synth_profile_ids)
                )
            )
            await session.execute(
                delete(StudentProject).where(StudentProject.student_id.in_(synth_profile_ids))
            )
            await session.execute(
                delete(StudentSkill).where(StudentSkill.student_id.in_(synth_profile_ids))
            )
            await session.execute(
                delete(StudentEducation).where(StudentEducation.student_id.in_(synth_profile_ids))
            )
            await session.execute(
                delete(Resume).where(Resume.student_id.in_(synth_profile_ids))
            )
            await session.execute(
                delete(ArenaAttempt).where(ArenaAttempt.student_id.in_(synth_profile_ids))
            )
            await session.execute(
                delete(ReadinessSnapshot).where(
                    ReadinessSnapshot.student_id.in_(synth_profile_ids)
                )
            )
            await session.flush()
            print("✓ Deleted Student skills, projects, experiences, certifications, resumes, arena attempts, and readiness records.")

        # 12. Student Profiles
        if synth_profile_ids:
            await session.execute(
                delete(StudentProfile).where(StudentProfile.id.in_(synth_profile_ids))
            )
            await session.flush()
            print("✓ Deleted StudentProfiles.")

        # 13. Users
        if all_synth_user_ids:
            await session.execute(delete(User).where(User.id.in_(all_synth_user_ids)))
            await session.flush()
            print(f"✓ Deleted {len(all_synth_user_ids)} synthetic Users.")

        await session.commit()
        print("\n" + "=" * 80)
        print("✨ CLEANUP SUCCESSFUL: All synthetic testing records have been safely purged.")
        print("All real institutional users, reference metadata, and live accounts remain fully intact.")
        print("=" * 80)
        return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Safely clean synthetic testing dataset.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be deleted without making database changes.",
    )
    parser.add_argument(
        "--force-prod",
        action="store_true",
        help="Force execution even if ENVIRONMENT is set to production.",
    )
    args = parser.parse_args()

    asyncio.run(clean_synthetic_dataset(dry_run=args.dry_run, force_prod=args.force_prod))
