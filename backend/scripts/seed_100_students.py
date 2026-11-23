"""
[ISOLATED DEVELOPMENT SEEDER - NOT FOR PRODUCTION STARTUP]
Seed script to create 100 multi-disciplinary test student accounts across all engineering branches.
Idempotent and populates full StudentProfile, StudentSkills, StudentProjects, StudentExperiences,
StudentCertifications, and approved Resumes.
Usage: python backend/scripts/seed_100_students.py
"""
import asyncio
import hashlib
import random
import sys
from datetime import datetime, timezone
from typing import Dict, List, Any

sys.path.insert(0, "backend")

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.organization import Department, Institution
from app.models.resume import Resume
from app.models.student import (
    StudentCertification,
    StudentEducation,
    StudentExperience,
    StudentProfile,
    StudentProject,
    StudentSkill,
)
from app.models.user import User, UserRole

DEFAULT_PASSWORD = "CollegeDemo2026!"

# Pool of first and last names for generating 100 realistic Indian engineering student names
FIRST_NAMES = [
    "Aarav", "Aditi", "Aditya", "Akash", "Ananya", "Ankit", "Anushka", "Arjun", "Ayush", "Bhavya",
    "Chaitanya", "Deepak", "Divya", "Gaurav", "Harsh", "Ishaan", "Jaya", "Karan", "Kavya", "Khushi",
    "Kunal", "Manish", "Mayank", "Meera", "Mohit", "Naveen", "Neha", "Nikhil", "Nisha", "Pooja",
    "Pranav", "Pratik", "Priya", "Rahul", "Rakesh", "Riya", "Rohan", "Rohit", "Sakshi", "Sameer",
    "Sanjay", "Saurabh", "Shikha", "Shivam", "Shreya", "Siddharth", "Simran", "Sneha", "Suraj", "Swati",
    "Tanmay", "Tarun", "Utkarsh", "Vaibhav", "Varun", "Vedant", "Vikas", "Vikram", "Vinay", "Vishal",
    "Yash", "Yuvraj", "Aayush", "Abhishek", "Aman", "Amita", "Aniket", "Archana", "Ashish", "Avani",
    "Barkha", "Bharat", "Chirag", "Darshan", "Devendra", "Disha", "Girish", "Himanshu", "Inder", "Jitendra",
    "Kamal", "Keshav", "Lalit", "Madhav", "Manas", "Mukul", "Nandini", "Omkar", "Pankaj", "Parth",
    "Payal", "Pradeep", "Praveen", "Rachit", "Rajesh", "Ritu", "Sanchit", "Satish", "Shubham", "Tejas"
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Malhotra", "Mehta", "Singh", "Patel", "Joshi", "Bhatia", "Reddy",
    "Chauhan", "Agarwal", "Bansal", "Mishra", "Pandey", "Saxena", "Trivedi", "Deshmukh", "Kulkarni", "Iyer",
    "Nair", "Rao", "Choudhary", "Rathore", "Bishnoi", "Gehlot", "Solanki", "Shekhawat", "Purohit", "Dave"
]

BRANCH_SPECS: Dict[str, Dict[str, Any]] = {
    "CIVIL": {
        "dept_code": "CIVIL",
        "roll_prefix": "22BCIV",
        "degree": "B.Tech in Civil Engineering",
        "skills": [
            ("AutoCAD", "tool", "advanced"),
            ("STAAD.Pro", "tool", "advanced"),
            ("Concrete Technology", "technical", "advanced"),
            ("Structural Analysis", "technical", "intermediate"),
            ("Geotechnical Engineering", "technical", "intermediate"),
            ("Surveying & Geomatics", "technical", "advanced"),
            ("Transportation Engineering", "technical", "intermediate"),
            ("Fluid Mechanics & Hydraulics", "technical", "intermediate"),
        ],
        "projects": [
            (
                "Design and Seismic Analysis of G+5 RCC Commercial Complex",
                "Executed comprehensive 3D finite-element frame analysis in STAAD.Pro conforming to IS 456:2000 and IS 1893:2016 seismic load parameters, optimizing steel consumption by 14%.",
                "STAAD.Pro, AutoCAD, MS Excel",
            ),
            (
                "Geotechnical Soil Stabilization using Fly-Ash and Lime Slurry",
                "Conducted California Bearing Ratio (CBR), Atterberg limits, and Standard Proctor compaction tests to enhance subgrade stability for low-volume rural highways.",
                "Soil Mechanics Lab, CBR Apparatus, GeoStudio",
            ),
        ],
        "experiences": [
            ("L&T Construction", "Civil Engineering Intern", "Supervised raft foundation casting, slump test quality checks, and BBS rebar detailing for urban infrastructure project."),
        ],
        "certifications": [
            ("Bentley Certified STAAD.Pro Structural Designer", "Bentley Systems"),
        ],
    },
    "MECH": {
        "dept_code": "MECH",
        "roll_prefix": "22BMECH",
        "degree": "B.Tech in Mechanical Engineering",
        "skills": [
            ("SolidWorks", "tool", "advanced"),
            ("ANSYS Mechanical", "tool", "advanced"),
            ("Thermodynamics", "technical", "advanced"),
            ("Heat & Mass Transfer", "technical", "intermediate"),
            ("Finite Element Analysis (FEA)", "technical", "advanced"),
            ("Fluid Machinery", "technical", "intermediate"),
            ("Manufacturing Processes & GD&T", "technical", "advanced"),
            ("MATLAB", "tool", "intermediate"),
        ],
        "projects": [
            (
                "CFD Thermal Optimization of Shell-and-Tube Heat Exchanger",
                "Simulated turbulent boundary layer heat dissipation using ANSYS Fluent (k-epsilon model), improving overall heat transfer coefficient by 18.5%.",
                "ANSYS Fluent, SolidWorks, MATLAB",
            ),
            (
                "Design and Kinematic Simulation of Automated Pneumatic Pick-and-Place Gripper",
                "Modeled 4-bar linkage mechanism in SolidWorks, performed static stress FEA to prevent deflection, and fabricated prototype using 3D printing and pneumatic actuators.",
                "SolidWorks, ANSYS Static Structural, Arduino",
            ),
        ],
        "experiences": [
            ("Tata Motors Ltd.", "Mechanical Production Intern", "Assisted transmission assembly line workflow, conducted cycle-time motion studies, and implemented Poka-Yoke fixtures."),
        ],
        "certifications": [
            ("CSWA - Certified SOLIDWORKS Associate", "Dassault Systèmes"),
        ],
    },
    "EEE": {
        "dept_code": "EEE",
        "roll_prefix": "22BEEE",
        "degree": "B.Tech in Electrical Engineering",
        "skills": [
            ("MATLAB & Simulink", "tool", "advanced"),
            ("Power Systems Analysis", "technical", "advanced"),
            ("Power Electronics & Drives", "technical", "advanced"),
            ("Electrical Machines", "technical", "intermediate"),
            ("Control Systems", "technical", "intermediate"),
            ("PLC & SCADA Programming", "tool", "intermediate"),
            ("ETAP", "tool", "advanced"),
            ("Microcontrollers (STM32 / Arduino)", "technical", "intermediate"),
        ],
        "projects": [
            (
                "Grid-Tied Solar Photovoltaic Inverter with P&O MPPT Algorithm",
                "Simulated 5kW single-phase grid-tied inverter topology in MATLAB/Simulink featuring perturb-and-observe maximum power point tracking and THD below 3%.",
                "MATLAB, Simulink, Power Electronics Toolbox",
            ),
            (
                "Substation Fault Analysis and Overcurrent Relay Coordination using ETAP",
                "Constructed 33/11 kV distribution substation one-line model in ETAP, evaluating short-circuit symmetrical/asymmetrical fault currents and curve grading.",
                "ETAP 20.0, Protective Relaying Standards (IEEE 242)",
            ),
        ],
        "experiences": [
            ("ABB India Ltd.", "Power Systems Engineering Intern", "Conducted relay parameter verification, primary injection testing on vacuum circuit breakers (VCB), and single-line diagram auditing."),
        ],
        "certifications": [
            ("Industrial Automation & PLC Specialist", "Siemens SITRAIN"),
        ],
    },
    "ECE": {
        "dept_code": "ECE",
        "roll_prefix": "22BECE",
        "degree": "B.Tech in Electronics and Communication Engineering",
        "skills": [
            ("Verilog HDL", "language", "advanced"),
            ("VLSI Architecture & CMOS Design", "technical", "advanced"),
            ("Embedded C / C++", "language", "advanced"),
            ("Digital Signal Processing (DSP)", "technical", "intermediate"),
            ("FPGA Prototyping (Xilinx)", "tool", "advanced"),
            ("Cadence Virtuoso", "tool", "intermediate"),
            ("Wireless Telecommunication & 5G", "technical", "intermediate"),
            ("Computer Networks", "technical", "intermediate"),
        ],
        "projects": [
            (
                "32-Bit Pipelined RISC-V Processor Core on Artix-7 FPGA",
                "Authored 5-stage hazard-handling RISC-V (RV32I) core in Verilog HDL, synthesized in Vivado, and benchmarked on Digilent Basys3 FPGA board with UART debugging.",
                "Verilog HDL, Xilinx Vivado, ModelSim, Artix-7",
            ),
            (
                "Low-Power IoT Telemetry Node with LoRa Modulation",
                "Engineered battery-efficient telemetry transmitter based on STM32 microcontroller and SX1276 LoRa module achieving 8km line-of-sight communication.",
                "Embedded C, STM32CubeIDE, KiCAD, LoRaWAN",
            ),
        ],
        "experiences": [
            ("STMicroelectronics", "Embedded Hardware Intern", "Developed board support package (BSP) device drivers for SPI memory and I2C power monitoring chips."),
        ],
        "certifications": [
            ("Cadence Certified Associate: Digital IC Design", "Cadence Design Systems"),
        ],
    },
    "CHEM": {
        "dept_code": "CHEM",
        "roll_prefix": "22BCHEM",
        "degree": "B.Tech in Chemical Engineering",
        "skills": [
            ("Aspen Plus", "tool", "advanced"),
            ("Chemical Reaction Engineering", "technical", "advanced"),
            ("Mass Transfer Operations", "technical", "advanced"),
            ("Heat Transfer & Pinch Analysis", "technical", "intermediate"),
            ("Process Dynamics & Process Control", "technical", "intermediate"),
            ("P&ID and Equipment Sizing", "technical", "intermediate"),
            ("Fluid Flow Operations", "technical", "intermediate"),
            ("Industrial Safety & HAZOP", "technical", "advanced"),
        ],
        "projects": [
            (
                "Process Simulation and Energy Pinch Optimization of Bioethanol Distillation",
                "Modeled a two-column azeotropic extractive distillation unit in Aspen Plus, achieving 99.6 wt% bioethanol recovery with 22% reduction in reboiler heat duty.",
                "Aspen Plus V12, Aspen Energy Analyzer",
            ),
            (
                "Fluidized Bed Catalytic Reactor Modeling for Hydrocarbon Cracking",
                "Formulated transient mass and heat balance PDE system in MATLAB, evaluating catalyst deactivation and optimal temperature trajectory.",
                "MATLAB, ODE15s, Chemical Kinetics",
            ),
        ],
        "experiences": [
            ("Reliance Industries Ltd. (Hazira)", "Process Engineering Trainee", "Monitored distillation tray hydraulics, column delta-P anomalies, and participated in HAZOP review for aromatics plant."),
        ],
        "certifications": [
            ("Certified Aspen Plus Simulation Professional", "AspenTech"),
        ],
    },
    "MINE": {
        "dept_code": "MINE",
        "roll_prefix": "22BMINE",
        "degree": "B.Tech in Mining Engineering",
        "skills": [
            ("GEOVIA Surpac", "tool", "advanced"),
            ("Mine Planning & Design", "technical", "advanced"),
            ("Rock Mechanics", "technical", "advanced"),
            ("Surface Mining Operations", "technical", "intermediate"),
            ("Underground Mine Ventilation", "technical", "advanced"),
            ("Drilling & Blasting Engineering", "technical", "intermediate"),
            ("Slope Stability Analysis", "technical", "intermediate"),
            ("Mines Act & Safety Regulations", "technical", "advanced"),
        ],
        "projects": [
            (
                "Open-Pit Mine Production Scheduling & Ultimate Pit Shell Optimization",
                "Imported drillhole assay database into GEOVIA Surpac, generated block model, and formulated Lerchs-Grossmann optimal pit shells for open-cast limestone deposit.",
                "GEOVIA Surpac, Whittle, AutoCAD",
            ),
            (
                "Underground Mine Ventilation Network Simulation and Gas Dispersion",
                "Modeled multi-level coal mine airway network in Ventsim, calculating airway resistance, booster fan pressure requirements, and methane dilution rates.",
                "Ventsim Visual, Rock Mechanics Testing",
            ),
        ],
        "experiences": [
            ("Coal India Limited (SECL)", "Mining Vocational Trainee", "Studied heavy earth moving machinery (HEMM) cycle efficiency, blast vibration monitoring using seismographs, and statutory safety audits."),
        ],
        "certifications": [
            ("DGMS Statutory Gas Testing Certificate", "Directorate General of Mines Safety"),
        ],
    },
    "PETRO": {
        "dept_code": "PETRO",
        "roll_prefix": "22BPETRO",
        "degree": "B.Tech in Petroleum Engineering",
        "skills": [
            ("Reservoir Simulation (Eclipse/CMG)", "tool", "advanced"),
            ("Petrophysics & Well Logging", "technical", "advanced"),
            ("Drilling Engineering & Hydraulics", "technical", "advanced"),
            ("Production Technology & Artificial Lift", "technical", "intermediate"),
            ("Formation Evaluation", "technical", "advanced"),
            ("Well Completion & Workover", "technical", "intermediate"),
            ("PVT & Reservoir Fluid Analysis", "technical", "intermediate"),
            ("Enhanced Oil Recovery (EOR)", "technical", "intermediate"),
        ],
        "projects": [
            (
                "Waterflooding Sweep Efficiency Optimization in Heterogeneous Sandstone Reservoir",
                "Constructed 3D compositional reservoir model in Eclipse to evaluate inverted 5-spot injection pattern, boosting cumulative oil recovery factor by 11.2%.",
                "Schlumberger ECLIPSE, Petrel RE",
            ),
            (
                "Hydraulic Fracturing Design and Proppant Transport Simulation",
                "Formulated PKN fracture propagation model in MATLAB, assessing gel viscosity, closure stress, and conductivity in tight gas formations.",
                "MATLAB, WellCat, Petrophysics Suite",
            ),
        ],
        "experiences": [
            ("ONGC (Western Onshore Asset)", "Petroleum Engineering Trainee", "Observed mud logging operations, casing cementing calculations, and wireline gamma-ray/resistivity interpretation."),
        ],
        "certifications": [
            ("IWCF / IADC Well Control Fundamentals", "International Well Control Forum"),
        ],
    },
    "STRUCT": {
        "dept_code": "STRUCT",
        "roll_prefix": "22BSTR",
        "degree": "B.Tech / M.Tech in Structural Engineering",
        "skills": [
            ("CSI ETABS", "tool", "advanced"),
            ("CSI SAFE", "tool", "advanced"),
            ("Structural Dynamics & Earthquake Engineering", "technical", "advanced"),
            ("IS 13920 Ductile Detailing", "technical", "advanced"),
            ("Pre-Stressed Concrete Design", "technical", "intermediate"),
            ("Design of Steel Structures (IS 800:2007)", "technical", "advanced"),
            ("Non-Linear Pushover Analysis", "technical", "intermediate"),
            ("Finite Element Modeling (FEM)", "technical", "intermediate"),
        ],
        "projects": [
            (
                "Non-Linear Static Pushover Analysis of 20-Storey Dual Lateral Load Resisting System",
                "Modeled moment frames with shear core walls in ETABS, assigned plastic hinge properties (FEMA 356), and computed seismic capacity spectrum.",
                "CSI ETABS Ultimate, SAFE, SAP2000",
            ),
            (
                "Design and Analysis of Post-Tensioned Flat Plate Slab for High-Rise Parking",
                "Modeled unbonded tendon profiles in CSI SAFE, verified punching shear capacity with shear studs, and ensured immediate/long-term deflection control.",
                "CSI SAFE, AutoCAD, IS 1343:2012",
            ),
        ],
        "experiences": [
            ("Tata Consulting Engineers (TCE)", "Structural Design Intern", "Prepared structural framing plans, column load take-down schedules, and shear wall ductile reinforcement detailing."),
        ],
        "certifications": [
            ("CSI Certified ETABS Professional", "Computers and Structures Inc."),
        ],
    },
    "PIE": {
        "dept_code": "PIE",
        "roll_prefix": "22BPIE",
        "degree": "B.Tech in Production and Industrial Engineering",
        "skills": [
            ("Operations Research & Optimization", "technical", "advanced"),
            ("Supply Chain & Logistics Management", "technical", "advanced"),
            ("Lean Manufacturing & Six Sigma", "technical", "advanced"),
            ("Statistical Quality Control (SPC)", "technical", "intermediate"),
            ("CNC Programming & CAM", "tool", "intermediate"),
            ("Facilities Planning & Ergonomics", "technical", "intermediate"),
            ("Arena / Simio Discrete Event Simulation", "tool", "advanced"),
            ("Python for Industrial Data Analytics", "language", "intermediate"),
        ],
        "projects": [
            (
                "Value Stream Mapping & Assembly Line Balancing in Precision Machine Shop",
                "Conducted time studies across 12 workstations, rebalanced cycle times to eliminate bottlenecks, and reduced manufacturing lead time by 28%.",
                "Simio Simulation, Minitab, MS Visio",
            ),
            (
                "Stochastic Multi-Echelon Inventory Optimization under Lead-Time Uncertainty",
                "Programmed Monte Carlo inventory simulation in Python, optimizing safety stock levels while sustaining 98% service fill rates.",
                "Python (NumPy, SciPy), PuLP, Minitab",
            ),
        ],
        "experiences": [
            ("Hero MotoCorp Ltd.", "Industrial Engineering Intern", "Led 5S and Kaizen shopfloor blitzes, identified idle machine time, and drafted standard operating procedures (SOPs)."),
        ],
        "certifications": [
            ("Lean Six Sigma Green Belt (ICGB)", "Six Sigma Council / ASQ"),
        ],
    },
    "ARCH_PLAN": {
        "dept_code": "ARCH_PLAN",
        "roll_prefix": "22BARCH",
        "degree": "Bachelor of Architecture & Planning",
        "skills": [
            ("Autodesk Revit (BIM)", "tool", "advanced"),
            ("AutoCAD Architecture", "tool", "advanced"),
            ("QGIS / ArcGIS Spatial Analytics", "tool", "advanced"),
            ("Urban Planning & Zoning Regulations", "technical", "advanced"),
            ("Sustainable Architecture & Passive Design", "technical", "intermediate"),
            ("Rhino 3D & Grasshopper", "tool", "intermediate"),
            ("Environmental Impact Assessment (EIA)", "technical", "intermediate"),
            ("Lumion 3D Architectural Rendering", "tool", "advanced"),
        ],
        "projects": [
            (
                "Transit-Oriented Urban Master Plan for 50-Hectare Metro Station Precinct",
                "Created comprehensive land use zoning, street hierarchy, pedestrian-first plazas, and density redistribution models using QGIS and AutoCAD.",
                "QGIS, AutoCAD, SketchUp, Adobe Illustrator",
            ),
            (
                "Net-Zero Energy Climate-Responsive Civic Cultural Center",
                "Designed bioclimatic envelope with daylighting optimization, rainwater harvesting, and solar PV integration modeled in Autodesk Revit.",
                "Autodesk Revit, Ladybug Tools, Lumion",
            ),
        ],
        "experiences": [
            ("CP Kukreja Architects", "Architectural Planning Intern", "Drafted detailed working drawings, urban contour grading diagrams, and municipal sanction presentation dossiers."),
        ],
        "certifications": [
            ("Autodesk Certified Professional: Revit for Architecture", "Autodesk"),
        ],
    },
    "CSE": {
        "dept_code": "CSE",
        "roll_prefix": "22BCSE",
        "degree": "B.Tech in Computer Science and Engineering",
        "skills": [
            ("Python", "language", "advanced"),
            ("Data Structures & Algorithms", "technical", "advanced"),
            ("FastAPI & REST Architecture", "framework", "advanced"),
            ("PostgreSQL & Database Indexing", "tool", "advanced"),
            ("Docker & Containerization", "tool", "intermediate"),
            ("Redis In-Memory Caching", "tool", "intermediate"),
            ("Distributed Systems Principles", "technical", "intermediate"),
            ("Git & CI/CD Pipelines", "tool", "advanced"),
        ],
        "projects": [
            (
                "High-Throughput Distributed Placement Telemetry & Matching Engine",
                "Engineered async FastAPI platform handling 10k requests/min with Redis token caching and PostgreSQL query optimization, achieving p95 latency under 45ms.",
                "Python, FastAPI, PostgreSQL, Docker, Redis",
            ),
            (
                "Multi-Tenant Role-Based Access Control and Resilient Audit Logger",
                "Designed tamper-evident audit logging service with SQLAlchemy transaction hooks, automated JWT revocation, and tenant data segregation.",
                "Python, SQLAlchemy 2.0, Alembic, Pytest",
            ),
        ],
        "experiences": [
            ("CloudScale Systems", "Software Engineering Intern", "Refactored microservice endpoints, tuned composite B-tree database indices, and authored unit tests with 92% code coverage."),
        ],
        "certifications": [
            ("AWS Certified Cloud Practitioner", "Amazon Web Services"),
        ],
    },
}

# 11 branches: 10 branches with 9 students + 1 branch (CSE) with 10 students = 100 students total
BRANCH_DISTRIBUTION = [
    ("CIVIL", 9),
    ("MECH", 9),
    ("EEE", 9),
    ("ECE", 9),
    ("CHEM", 9),
    ("MINE", 9),
    ("PETRO", 9),
    ("STRUCT", 9),
    ("PIE", 9),
    ("ARCH_PLAN", 9),
    ("CSE", 10),
]


async def seed_100_students():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting creation of 100 multi-disciplinary dummy student accounts...")
    hashed_pwd = hash_password(DEFAULT_PASSWORD)
    now_utc = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        # 1. Fetch departments
        dept_stmt = select(Department)
        dept_rows = (await session.execute(dept_stmt)).scalars().all()
        depts_by_code: Dict[str, Department] = {d.code: d for d in dept_rows}

        # Verify all branches exist
        missing_codes = [code for code, _ in BRANCH_DISTRIBUTION if code not in depts_by_code]
        if missing_codes:
            raise RuntimeError(f"Missing departments in database for codes: {missing_codes}")

        created_count = 0
        skipped_count = 0
        sample_accounts: List[Dict[str, Any]] = []

        name_idx = 0
        random.seed(42)  # Deterministic generation

        for branch_code, count in BRANCH_DISTRIBUTION:
            spec = BRANCH_SPECS[branch_code]
            dept = depts_by_code[branch_code]

            for i in range(1, count + 1):
                first_name = FIRST_NAMES[name_idx % len(FIRST_NAMES)]
                last_name = LAST_NAMES[(name_idx * 3 + i) % len(LAST_NAMES)]
                full_name = f"{first_name} {last_name}"
                email = f"{first_name.lower()}.{branch_code.lower()}{i:02d}@mbm.edu"
                roll_number = f"{spec['roll_prefix']}{i:02d}"
                name_idx += 1

                # Check if user already exists
                existing_user = (
                    await session.execute(select(User).where(User.email == email))
                ).scalar_one_or_none()

                if existing_user:
                    skipped_count += 1
                    if len(sample_accounts) < 15 and (i == 1 or i == 2):
                        sample_accounts.append({
                            "email": email,
                            "name": full_name,
                            "branch": dept.name,
                            "branch_code": branch_code,
                            "roll_number": roll_number,
                            "cgpa": 8.5,
                        })
                    continue

                # CGPA between 7.00 and 9.60
                cgpa_val = round(random.uniform(7.20, 9.50), 2)
                active_backlogs = 1 if (i == count and branch_code in ("CIVIL", "MECH")) else 0
                total_backlogs = active_backlogs

                # Create User
                user = User(
                    email=email,
                    hashed_password=hashed_pwd,
                    full_name=full_name,
                    role=UserRole.STUDENT,
                    institution_id=dept.institution_id or 1,
                    department_id=dept.id,
                    is_active=True,
                    is_verified=True,
                    phone=f"+91 9829{random.randint(100000, 999999)}",
                )
                session.add(user)
                await session.flush()

                # Create StudentProfile
                profile = StudentProfile(
                    user_id=user.id,
                    roll_number=roll_number,
                    graduation_year=2026,
                    cgpa=cgpa_val,
                    active_backlogs=active_backlogs,
                    total_backlogs=total_backlogs,
                    linkedin_url=f"https://linkedin.com/in/{first_name.lower()}-{last_name.lower()}-{roll_number.lower()}",
                    github_url=f"https://github.com/{first_name.lower()}{roll_number.lower()}",
                    portfolio_url=f"https://{first_name.lower()}-portfolio.me",
                    is_placement_ready=True,
                )
                session.add(profile)
                await session.flush()

                # Education History
                edu = StudentEducation(
                    student_id=profile.id,
                    institution_name="MBM University, Jodhpur",
                    degree=spec["degree"],
                    field_of_study=dept.name,
                    start_year=2022,
                    end_year=2026,
                    cgpa_or_percentage=f"{cgpa_val} CGPA",
                )
                session.add(edu)

                # Skills
                for skill_name, cat, prof in spec["skills"]:
                    sk = StudentSkill(
                        student_id=profile.id,
                        skill_name=skill_name,
                        category=cat,
                        proficiency_level=prof,
                        is_verified=True,
                    )
                    session.add(sk)

                # Projects
                for p_title, p_desc, p_tech in spec["projects"]:
                    proj = StudentProject(
                        student_id=profile.id,
                        title=p_title,
                        description=p_desc,
                        technologies=p_tech,
                        start_date="2024-01",
                        end_date="2024-06",
                    )
                    session.add(proj)

                # Experiences
                for exp_company, exp_role, exp_desc in spec["experiences"]:
                    exp = StudentExperience(
                        student_id=profile.id,
                        company_name=exp_company,
                        role_title=exp_role,
                        description=exp_desc,
                        start_date="2024-06",
                        end_date="2024-08",
                        is_current=False,
                    )
                    session.add(exp)

                # Certifications
                for cert_name, cert_org in spec["certifications"]:
                    cert = StudentCertification(
                        student_id=profile.id,
                        certificate_name=cert_name,
                        issuing_organization=cert_org,
                        issue_date="2024-07",
                    )
                    session.add(cert)

                # Create Active Approved Resume with rich extracted text
                resume_text = (
                    f"CURRICULUM VITAE\n\n"
                    f"Name: {full_name}\n"
                    f"Email: {email}\n"
                    f"Roll Number: {roll_number}\n"
                    f"Degree: {spec['degree']} (Batch 2022 - 2026)\n"
                    f"College: MBM University, Jodhpur\n"
                    f"CGPA: {cgpa_val} / 10.00\n\n"
                    f"CORE TECHNICAL SKILLS:\n"
                    f"{', '.join([s[0] for s in spec['skills']])}\n\n"
                    f"KEY PROJECTS:\n"
                    + "\n".join([f"• {p[0]}: {p[1]} (Tools: {p[2]})" for p in spec["projects"]])
                    + f"\n\nINTERNSHIP EXPERIENCE:\n"
                    + "\n".join([f"• {e[1]} at {e[0]}: {e[2]}" for e in spec["experiences"]])
                    + f"\n\nCERTIFICATIONS:\n"
                    + "\n".join([f"• {c[0]} issued by {c[1]}" for c in spec["certifications"]])
                )

                file_hash_val = hashlib.sha256(f"{email}-{roll_number}".encode()).hexdigest()
                resume = Resume(
                    student_id=profile.id,
                    file_name=f"{roll_number.lower()}_{first_name.lower()}_resume.pdf",
                    file_path=f"backend/uploads/resumes/{roll_number.lower()}_resume.pdf",
                    file_type="pdf",
                    file_size_bytes=102400 + random.randint(1000, 50000),
                    file_hash=file_hash_val,
                    raw_extracted_text=resume_text,
                    parsed_entities_json={
                        "contact_info": {"name": full_name, "email": email, "phone": user.phone},
                        "education": [{"degree": spec["degree"], "college": "MBM University", "cgpa": str(cgpa_val)}],
                        "skills": [s[0] for s in spec["skills"]],
                        "projects": [{"title": p[0], "description": p[1], "technologies": p[2]} for p in spec["projects"]],
                        "experiences": [{"company": e[0], "role": e[1], "description": e[2]} for e in spec["experiences"]],
                    },
                    parsing_status="approved",
                    is_active=True,
                )
                session.add(resume)
                created_count += 1

                if len(sample_accounts) < 15 and (i == 1 or i == 2):
                    sample_accounts.append({
                        "email": email,
                        "name": full_name,
                        "branch": dept.name,
                        "branch_code": branch_code,
                        "roll_number": roll_number,
                        "cgpa": cgpa_val,
                    })

        await session.commit()
        print(f"[{datetime.now(timezone.utc).isoformat()}] Completed: {created_count} students created, {skipped_count} skipped.")
        print(f"Total Student Accounts Processed: {created_count + skipped_count}")


if __name__ == "__main__":
    asyncio.run(seed_100_students())
