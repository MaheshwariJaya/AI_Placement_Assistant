from typing import Any, List, Optional, Tuple
from app.models.job import Job
from app.models.organization import Department
from app.models.user import User

# Keyword dictionaries mapped to canonical department codes
DEPARTMENT_KEYWORDS = {
    "CIVIL": [
        "civil", "structural", "concrete", "staad", "autocad", "revit", "bim",
        "surveying", "geotechnical", "transportation", "construction", "hydraulics",
        "estimation", "site engineer", "highway", "infrastructure"
    ],
    "MECH": [
        "mechanical", "thermodynamics", "fluid mechanics", "cad", "cam", "solidworks",
        "ansys", "catia", "manufacturing", "machine design", "hvac", "automotive",
        "thermal", "robotics", "cnc"
    ],
    "EEE": [
        "electrical", "power systems", "electrical machines", "control systems",
        "power electronics", "matlab", "simulink", "scada", "plc", "switchgear",
        "substation", "high voltage", "grid"
    ],
    "ECE": [
        "electronics", "communication", "embedded", "vlsi", "verilog", "fpga",
        "signal processing", "microcontroller", "pcb", "iot", "telecom", "rf", "analog"
    ],
    "CHEM": [
        "chemical", "process engineering", "mass transfer", "heat transfer",
        "chemical reaction", "aspen", "distillation", "petrochemical", "refinery",
        "process safety", "hysys", "reactor"
    ],
    "MINE": [
        "mining", "mine planning", "rock mechanics", "blasting", "mine ventilation",
        "surpac", "mineral processing", "quarry", "opencast", "underground mining",
        "strata control"
    ],
    "PETRO": [
        "petroleum", "reservoir", "drilling", "well logging", "petrophysics",
        "eor", "upstream", "oil & gas", "well completion", "offshore"
    ],
    "STRUCT": [
        "structural", "staad", "etabs", "earthquake", "seismic", "prestressed concrete",
        "steel structures", "matrix analysis", "foundation design", "tall buildings"
    ],
    "PIE": [
        "production", "industrial engineering", "operations research", "supply chain",
        "lean manufacturing", "six sigma", "quality control", "plant layout",
        "ergonomics", "inventory management", "logistics"
    ],
    "ARCH_PLAN": [
        "architecture", "urban planning", "gis", "land use", "zoning", "revit",
        "sketchup", "spatial planning", "landscape", "building codes", "master planning"
    ],
    "CSE": [
        "software", "computer science", "developer", "backend", "frontend", "full stack",
        "data structure", "algorithm", "python", "java", "c++", "database", "cloud",
        "devops", "machine learning", "ai", "sre", "web"
    ],
    "IT": [
        "information technology", "software", "network", "system administrator",
        "cloud", "cybersecurity", "web development", "database"
    ],
}

CAREER_TRACK_KEYWORDS = {
    "software": ["software", "developer", "backend", "frontend", "full stack", "python", "java", "coding", "sre"],
    "data": ["data", "analytics", "data analyst", "data science", "bi", "sql", "tableau", "machine learning"],
    "core": ["core", "trainee", "engineer", "plant", "site", "design", "maintenance", "operations"],
    "management": ["analyst", "consultant", "management trainee", "operations", "associate", "product", "business"],
}


def classify_job_branch_relevance(
    job: Job,
    student_user: User,
    student_career_interests: Optional[List[str]] = None,
) -> Tuple[str, str, str]:
    """
    Classifies a job into one of 4 centralized relevance tiers:
    1. 'directly_relevant' - Aligned directly with the student's verified academic branch.
    2. 'interdisciplinary' - Open to student and aligned with declared career interest or interdisciplinary domain.
    3. 'open_to_all' - Open campus hiring without branch restrictions, but general domain.
    4. 'not_relevant' - Department restriction excludes student, or domain mismatch.

    Returns: (relevance_tier, relevance_reason, branch_match_status)
    """
    interests = [str(i).lower().strip() for i in (student_career_interests or [])]
    dept: Optional[Department] = getattr(student_user, "department", None)

    # 1. Inspect Job Department Restrictions
    eligible_depts = [ed.department for ed in (job.eligible_departments or []) if ed.department]
    has_dept_restrictions = len(eligible_depts) > 0

    if dept is None:
        if has_dept_restrictions:
            return (
                "not_relevant",
                "Official academic branch unverified; job requires specific verified department.",
                "branch_mismatch",
            )
        return (
            "open_to_all",
            "Campus drive open to all branches. Please verify your official branch with TPO.",
            "open_to_all",
        )

    student_dept_id = dept.id
    student_dept_code = (dept.code or "").upper().strip()
    student_dept_name = dept.name.strip()

    job_title_lower = (job.title or "").lower()
    job_desc_lower = (job.description or "").lower()
    job_skills_lower = [str(s.skill_name).lower() for s in (job.skills or [])]

    # Check if student's department is in eligible list
    is_dept_eligible = not has_dept_restrictions or any(d.id == student_dept_id for d in eligible_depts)

    if not is_dept_eligible:
        allowed_names = ", ".join(d.name for d in eligible_depts[:3])
        return (
            "not_relevant",
            f"Department cutoff: Limited to {allowed_names}.",
            "branch_mismatch",
        )

    # Check if job title/skills match student's academic branch keywords
    branch_kw = DEPARTMENT_KEYWORDS.get(student_dept_code, [student_dept_name.lower()])
    has_branch_term = any(
        kw in job_title_lower or any(kw in s for s in job_skills_lower)
        for kw in branch_kw
    )

    # Check if job is tailored to student's department specifically
    is_dedicated_to_branch = (
        has_dept_restrictions and len(eligible_depts) <= 3 and any(d.id == student_dept_id for d in eligible_depts)
    )

    if has_branch_term or is_dedicated_to_branch:
        return (
            "directly_relevant",
            f"Directly relevant to your official academic branch ({student_dept_name}).",
            "matched",
        )

    # Check if student has explicit career interests matching this job
    career_match = False
    matching_interest_name = ""
    for interest in interests:
        for track_name, kws in CAREER_TRACK_KEYWORDS.items():
            if track_name in interest or interest in track_name:
                if any(kw in job_title_lower or any(kw in s for s in job_skills_lower) for kw in kws):
                    career_match = True
                    matching_interest_name = interest.title()
                    break
        if career_match:
            break

    if career_match:
        return (
            "interdisciplinary",
            f"Interdisciplinary opportunity aligned with your declared career interest ({matching_interest_name}). Additional cross-discipline skills may be evaluated.",
            "interdisciplinary",
        )

    # Check if job is open to all
    if not has_dept_restrictions:
        return (
            "open_to_all",
            "Campus opportunity open to all academic branches without department restriction.",
            "open_to_all",
        )

    # If department is allowed along with others (e.g. multidisciplinary drive)
    return (
        "interdisciplinary",
        f"Multi-disciplinary campus drive including {student_dept_name}.",
        "matched",
    )
