"""
[ISOLATED DEVELOPMENT SEEDER - NOT FOR PRODUCTION STARTUP]
Seed core engineering branch companies and jobs for local matching simulation.
Usage: python backend/scripts/seed_multi_branch_jobs.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.company import Company
from app.models.organization import Department
from app.models.job import Job, JobSkill, JobEligibleDepartment, JobStatus, EmploymentType, WorkMode
from app.models.user import User, UserRole

CORE_COMPANIES = [
    {"name": "Larsen & Toubro", "industry": "Infrastructure & Engineering", "website": "https://larsentoubro.com"},
    {"name": "Tata Projects Ltd", "industry": "Construction & Infrastructure", "website": "https://tataprojects.com"},
    {"name": "Tata Motors", "industry": "Automotive & Mechanical", "website": "https://tatamotors.com"},
    {"name": "Schneider Electric", "industry": "Energy Management & Automation", "website": "https://se.com"},
    {"name": "Texas Instruments", "industry": "Semiconductors & Electronics", "website": "https://ti.com"},
    {"name": "Qualcomm India", "industry": "Semiconductors & Telecommunications", "website": "https://qualcomm.com"},
    {"name": "Reliance Industries Ltd", "industry": "Chemicals & Petrochemicals", "website": "https://ril.com"},
    {"name": "Vedanta Resources Ltd", "industry": "Mining & Metals", "website": "https://vedantaresources.com"},
    {"name": "Schlumberger (SLB)", "industry": "Oilfield & Petroleum Services", "website": "https://slb.com"},
    {"name": "Thornton Tomasetti", "industry": "Structural Engineering & Advisory", "website": "https://thorntontomasetti.com"},
    {"name": "Maruti Suzuki India", "industry": "Manufacturing & Industrial Engineering", "website": "https://marutisuzuki.com"},
    {"name": "AtkinsRéalis India", "industry": "Architecture & Urban Planning", "website": "https://atkinsrealis.com"},
    {"name": "Deloitte India", "industry": "Management & Technology Consulting", "website": "https://deloitte.com"},
]

JOBS_SPEC = [
    # 1. CIVIL
    {
        "dept_code": "CIVIL",
        "company_name": "Larsen & Toubro",
        "title": "Graduate Civil Engineer - Infrastructure Projects",
        "desc": "Lead on-site highway and structural engineering execution, concrete quality assurance, surveying alignment, and STAAD modeling.",
        "location": "Jaipur / Delhi NCR",
        "work_mode": WorkMode.ON_SITE,
        "ctc_lpa": 8.5,
        "salary_range": "₹8.0 - ₹9.0 LPA",
        "min_cgpa": 7.0,
        "max_backlogs": 0,
        "skills": [
            ("AutoCAD", True),
            ("STAAD.Pro", True),
            ("Concrete Technology", True),
            ("Structural Analysis", True),
            ("Surveying & Geomatics", False),
            ("Transportation Engineering", False),
        ],
    },
    {
        "dept_code": "CIVIL",
        "company_name": "Tata Projects Ltd",
        "title": "Structural Design Engineer",
        "desc": "Perform computational RCC structural analysis, design calculation reports, and BIM modeling for high-rise infrastructure.",
        "location": "Mumbai / Remote",
        "work_mode": WorkMode.HYBRID,
        "ctc_lpa": 10.0,
        "salary_range": "₹9.5 - ₹10.5 LPA",
        "min_cgpa": 7.5,
        "max_backlogs": 0,
        "skills": [
            ("Structural Analysis", True),
            ("STAAD.Pro", True),
            ("AutoCAD", True),
            ("Concrete Technology", True),
            ("Geotechnical Engineering", False),
        ],
    },
    # 2. MECHANICAL
    {
        "dept_code": "MECH",
        "company_name": "Tata Motors",
        "title": "Mechanical Design & CAE Engineer",
        "desc": "Perform 3D CAD modeling, thermal-fluid dynamics simulations, FEA stress analyses, and automotive powertrain validation.",
        "location": "Pune",
        "work_mode": WorkMode.ON_SITE,
        "ctc_lpa": 9.5,
        "salary_range": "₹9.0 - ₹10.0 LPA",
        "min_cgpa": 7.0,
        "max_backlogs": 0,
        "skills": [
            ("SolidWorks", True),
            ("ANSYS", True),
            ("Thermodynamics", True),
            ("Fluid Mechanics", True),
            ("Machine Design", False),
        ],
    },
    # 3. ELECTRICAL
    {
        "dept_code": "EEE",
        "company_name": "Schneider Electric",
        "title": "Power Systems & Grid Automation Engineer",
        "desc": "Commission high-voltage switchgear, SCADA distribution automation, PLC ladder logic, and electrical machine protections.",
        "location": "Bengaluru",
        "work_mode": WorkMode.HYBRID,
        "ctc_lpa": 10.5,
        "salary_range": "₹10.0 - ₹11.0 LPA",
        "min_cgpa": 7.2,
        "max_backlogs": 0,
        "skills": [
            ("Power Systems", True),
            ("Electrical Machines", True),
            ("Control Systems", True),
            ("MATLAB & Simulink", False),
            ("SCADA", False),
        ],
    },
    # 4. ECE
    {
        "dept_code": "ECE",
        "company_name": "Texas Instruments",
        "title": "Embedded Systems & IoT Hardware Engineer",
        "desc": "Architect low-power firmware in Embedded C, design multi-layer PCBs, and interface microcontrollers with wireless transceivers.",
        "location": "Bengaluru",
        "work_mode": WorkMode.ON_SITE,
        "ctc_lpa": 14.0,
        "salary_range": "₹13.0 - ₹15.0 LPA",
        "min_cgpa": 7.5,
        "max_backlogs": 0,
        "skills": [
            ("Embedded C", True),
            ("Microcontrollers & ARM", True),
            ("Digital Electronics", True),
            ("PCB Design", False),
            ("VLSI Design", False),
        ],
    },
    # 5. CHEMICAL
    {
        "dept_code": "CHEM",
        "company_name": "Reliance Industries Ltd",
        "title": "Process Design & Safety Engineer",
        "desc": "Optimize distillation columns, simulate continuous reactors in Aspen Plus, and ensure HazOp compliance across continuous plants.",
        "location": "Jamnagar / Vadodara",
        "work_mode": WorkMode.ON_SITE,
        "ctc_lpa": 11.0,
        "salary_range": "₹10.5 - ₹12.0 LPA",
        "min_cgpa": 7.0,
        "max_backlogs": 0,
        "skills": [
            ("Chemical Reaction Engineering", True),
            ("Heat Transfer", True),
            ("Mass Transfer", True),
            ("Aspen Plus", True),
            ("Process Dynamics & Control", False),
        ],
    },
    # 6. MINING
    {
        "dept_code": "MINE",
        "company_name": "Vedanta Resources Ltd",
        "title": "Mine Planning & Operations Trainee",
        "desc": "Manage opencast pit stability, computer-aided 3D block modeling in Surpac, controlled blasting, and underground strata ventilation.",
        "location": "Udaipur / Goa",
        "work_mode": WorkMode.ON_SITE,
        "ctc_lpa": 12.0,
        "salary_range": "₹11.0 - ₹13.0 LPA",
        "min_cgpa": 6.8,
        "max_backlogs": 0,
        "skills": [
            ("Mine Planning & Design", True),
            ("Rock Mechanics", True),
            ("Drilling & Blasting", True),
            ("Mine Ventilation", False),
            ("Surpac", False),
        ],
    },
    # 7. PETROLEUM
    {
        "dept_code": "PETRO",
        "company_name": "Schlumberger (SLB)",
        "title": "Reservoir & Drilling Operations Engineer",
        "desc": "Perform formation evaluation, interpret wireline logs, simulate reservoir recovery, and optimize deep horizontal drilling hydraulics.",
        "location": "Mumbai / Offshore",
        "work_mode": WorkMode.ON_SITE,
        "ctc_lpa": 16.0,
        "salary_range": "₹15.0 - ₹17.0 LPA",
        "min_cgpa": 7.5,
        "max_backlogs": 0,
        "skills": [
            ("Reservoir Engineering", True),
            ("Drilling Engineering", True),
            ("Petroleum Production Operations", True),
            ("Well Logging & Formation Evaluation", False),
        ],
    },
    # 8. STRUCTURAL
    {
        "dept_code": "STRUCT",
        "company_name": "Thornton Tomasetti",
        "title": "Advanced Structural Consultant",
        "desc": "Perform non-linear seismic pushover analyses, finite element stress modeling, and structural wind tunnel mitigation for supertall towers.",
        "location": "Mumbai / Hybrid",
        "work_mode": WorkMode.HYBRID,
        "ctc_lpa": 12.5,
        "salary_range": "₹12.0 - ₹13.5 LPA",
        "min_cgpa": 7.8,
        "max_backlogs": 0,
        "skills": [
            ("Advanced Structural Dynamics", True),
            ("Finite Element Analysis (FEA)", True),
            ("Earthquake Resistant Design", True),
            ("STAAD.Pro", False),
        ],
    },
    # 9. PIE
    {
        "dept_code": "PIE",
        "company_name": "Maruti Suzuki India",
        "title": "Industrial Engineering & Supply Chain Lead",
        "desc": "Drive lean assembly optimization, value stream mapping, Six Sigma DMAIC projects, and automated inventory control.",
        "location": "Gurugram / Manesar",
        "work_mode": WorkMode.ON_SITE,
        "ctc_lpa": 9.0,
        "salary_range": "₹8.5 - ₹9.5 LPA",
        "min_cgpa": 6.8,
        "max_backlogs": 0,
        "skills": [
            ("Operations Research", True),
            ("Supply Chain & Logistics", True),
            ("Lean Manufacturing & Six Sigma", True),
            ("Statistical Quality Control", False),
        ],
    },
    # 10. ARCHITECTURE & PLANNING
    {
        "dept_code": "ARCH_PLAN",
        "company_name": "AtkinsRéalis India",
        "title": "Urban Infrastructure & Master Planner",
        "desc": "Develop GIS spatial zoning layouts, transit-oriented development frameworks, statutory master plans, and 3D architectural BIM models.",
        "location": "Bengaluru / Hybrid",
        "work_mode": WorkMode.HYBRID,
        "ctc_lpa": 8.0,
        "salary_range": "₹7.5 - ₹8.5 LPA",
        "min_cgpa": 7.0,
        "max_backlogs": 0,
        "skills": [
            ("Urban & Regional Planning", True),
            ("Geographic Information Systems (GIS)", True),
            ("Architectural Design & Detailing", True),
            ("Revit & BIM", False),
        ],
    },
    # 11. OPEN TO ALL - TECHNO-COMMERCIAL / MANAGEMENT
    {
        "dept_code": "ALL",
        "company_name": "Deloitte India",
        "title": "Technology & Management Associate",
        "desc": "Cross-functional consulting role analyzing digital operations, stakeholder communication, and analytical problem-solving across all disciplines.",
        "location": "Hyderabad / Gurugram",
        "work_mode": WorkMode.HYBRID,
        "ctc_lpa": 11.5,
        "salary_range": "₹11.0 - ₹12.0 LPA",
        "min_cgpa": 7.0,
        "max_backlogs": 0,
        "skills": [
            ("Quantitative Aptitude", True),
            ("Problem Solving", True),
            ("Business Communication", True),
            ("Data Analytics", False),
        ],
    },
]

async def seed():
    async with AsyncSessionLocal() as session:
        # 1. Fetch TPO or Admin User for created_by
        tpo_user = (await session.execute(select(User).where(User.role.in_([UserRole.TPO, UserRole.ADMIN])))).scalars().first()
        if not tpo_user:
            tpo_user = (await session.execute(select(User))).scalars().first()
        created_by_id = tpo_user.id

        # 2. Map Departments by Code
        depts = (await session.execute(select(Department))).scalars().all()
        dept_by_code = {d.code: d for d in depts if d.code}

        # 3. Ensure Companies Exist
        comp_by_name = {}
        for cdata in CORE_COMPANIES:
            stmt = select(Company).where(Company.name == cdata["name"])
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if not existing:
                existing = Company(
                    name=cdata["name"],
                    industry=cdata["industry"],
                    website=cdata["website"],
                    description=f"Premier industry hiring partner in {cdata['industry']}.",
                    is_active=True,
                )
                session.add(existing)
                await session.flush()
            comp_by_name[cdata["name"]] = existing

        # 4. Create Jobs
        created_count = 0
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(days=90)

        for jspec in JOBS_SPEC:
            comp = comp_by_name[jspec["company_name"]]
            # Check if job already exists
            stmt = select(Job).where(Job.company_id == comp.id, Job.title == jspec["title"])
            existing_job = (await session.execute(stmt)).scalar_one_or_none()
            if existing_job:
                continue

            job = Job(
                company_id=comp.id,
                institution_id=1,  # MBM University
                created_by_user_id=created_by_id,
                title=jspec["title"],
                description=jspec["desc"],
                location=jspec["location"],
                employment_type=EmploymentType.FULL_TIME,
                work_mode=jspec["work_mode"],
                salary_range=jspec["salary_range"],
                ctc_lpa=jspec["ctc_lpa"],
                min_cgpa=jspec["min_cgpa"],
                max_active_backlogs=jspec["max_backlogs"],
                max_total_backlogs=jspec["max_backlogs"],
                target_graduation_year=2026,
                application_deadline=deadline,
                status=JobStatus.PUBLISHED,
                is_active=True,
            )
            session.add(job)
            await session.flush()

            # Add Skills
            for sk_name, is_mand in jspec["skills"]:
                jsk = JobSkill(job_id=job.id, skill_name=sk_name, is_mandatory=is_mand)
                session.add(jsk)

            # Add Department Eligibility
            target_code = jspec["dept_code"]
            if target_code == "ALL":
                # Open to all: leave eligible_departments empty or add all depts
                pass
            else:
                dept_obj = dept_by_code.get(target_code)
                if dept_obj:
                    jed = JobEligibleDepartment(job_id=job.id, department_id=dept_obj.id)
                    session.add(jed)
                    # For Structural, also include Civil as eligible
                    if target_code == "STRUCT" and "CIVIL" in dept_by_code:
                        session.add(JobEligibleDepartment(job_id=job.id, department_id=dept_by_code["CIVIL"].id))

            created_count += 1

        await session.commit()
        print(f"Successfully seeded {created_count} multi-branch placement jobs!")

if __name__ == "__main__":
    asyncio.run(seed())
