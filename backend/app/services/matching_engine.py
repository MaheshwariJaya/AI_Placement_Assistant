from datetime import datetime, timezone
import re
from typing import Dict, List, Optional, Set, Tuple
import logging

from app.models.job import Job, JobSkill
from app.models.student import (
    StudentCertification,
    StudentEducation,
    StudentExperience,
    StudentProfile,
    StudentProject,
    StudentSkill,
)
from app.models.user import User
from app.schemas.intelligence import ScoreBreakdown

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Canonical Controlled Skill Alias Dictionary
# -----------------------------------------------------------------------------

CANONICAL_SKILL_ALIASES: Dict[str, str] = {
    # Web & Frontend
    "react": "react",
    "reactjs": "react",
    "react.js": "react",
    "react native": "react native",
    "reactnative": "react native",
    "vue": "vue.js",
    "vuejs": "vue.js",
    "vue.js": "vue.js",
    "angular": "angular",
    "angularjs": "angular",
    "next": "next.js",
    "nextjs": "next.js",
    "next.js": "next.js",
    "node": "node.js",
    "nodejs": "node.js",
    "node.js": "node.js",
    "express": "express.js",
    "expressjs": "express.js",
    "express.js": "express.js",
    "tailwind": "tailwindcss",
    "tailwindcss": "tailwindcss",
    "bootstrap": "bootstrap",
    "html": "html",
    "html5": "html",
    "css": "css",
    "css3": "css",
    "js": "javascript",
    "javascript": "javascript",
    "ts": "typescript",
    "typescript": "typescript",

    # Languages & Systems
    "py": "python",
    "python": "python",
    "python3": "python",
    "cpp": "c++",
    "cplusplus": "c++",
    "c++": "c++",
    "c#": "c#",
    "csharp": "c#",
    "cs": "c#",
    "golang": "go",
    "go": "go",
    "java": "java",
    "rust": "rust",
    "ruby": "ruby",
    "php": "php",
    "scala": "scala",
    "kotlin": "kotlin",
    "swift": "swift",

    # Frameworks
    "fastapi": "fastapi",
    "django": "django",
    "flask": "flask",
    "spring": "spring boot",
    "springboot": "spring boot",
    "spring boot": "spring boot",
    ".net": ".net",
    "dotnet": ".net",

    # Databases
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "psql": "postgresql",
    "mysql": "mysql",
    "mongo": "mongodb",
    "mongodb": "mongodb",
    "redis": "redis",
    "sqlite": "sqlite",
    "cassandra": "cassandra",
    "dynamodb": "dynamodb",
    "oracle": "oracle db",

    # DevOps, Cloud & Infrastructure
    "docker": "docker",
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
    "aws": "amazon web services",
    "amazon web services": "amazon web services",
    "gcp": "google cloud platform",
    "google cloud": "google cloud platform",
    "google cloud platform": "google cloud platform",
    "azure": "azure",
    "microsoft azure": "azure",
    "ci/cd": "ci/cd",
    "cicd": "ci/cd",
    "git": "git",
    "linux": "linux",
    "bash": "bash",
    "shell": "shell script",

    # Data & AI
    "ml": "machine learning",
    "machine learning": "machine learning",
    "ai": "artificial intelligence",
    "deep learning": "deep learning",
    "pytorch": "pytorch",
    "tensorflow": "tensorflow",
    "tf": "tensorflow",
    "pandas": "pandas",
    "numpy": "numpy",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "spark": "apache spark",
    "apache spark": "apache spark",
    "kafka": "apache kafka",
    "apache kafka": "apache kafka",
}


def normalize_skill(skill: str) -> str:
    """
    Clean and canonicalize a skill identifier without conflating distinct technologies.
    Preserves specialized identifiers (e.g. C vs C++ vs C#).
    """
    if not skill:
        return ""
    cleaned = skill.strip().lower()
    cleaned = " ".join(cleaned.split())
    return CANONICAL_SKILL_ALIASES.get(cleaned, cleaned)


# Technical role keywords (NOTE: 'intern' is deliberately excluded as a standalone technical role)
TECHNICAL_ROLE_KEYWORDS = {
    "developer",
    "engineer",
    "programmer",
    "architect",
    "consultant",
    "analyst",
    "scientist",
    "devops",
    "frontend",
    "backend",
    "fullstack",
    "full stack",
    "data",
    "cloud",
    "qa",
    "tester",
    "sre",
    "embedded",
    "android",
    "ios",
    "mobile",
}

# Credential validation keywords for certifications
CERTIFICATION_RECOGNITION_KEYWORDS = {
    "aws",
    "amazon web services",
    "azure",
    "gcp",
    "google cloud",
    "oracle",
    "cisco",
    "comptia",
    "kubernetes",
    "cka",
    "ckad",
    "red hat",
    "rhce",
    "rhcsa",
    "tensorflow",
    "certified",
    "developer",
    "associate",
    "professional",
    "architect",
    "specialist",
    "foundation",
}


def parse_date_to_month_year(date_str: Optional[str]) -> Optional[Tuple[int, int]]:
    """
    Extract (year, month) from dates like '2024-05', '2024-05-12', 'May 2024', '05/2024'.
    Returns None if missing, incomplete, or unparseable.
    """
    if not date_str or not date_str.strip():
        return None
    s = date_str.strip().lower()

    # Pattern: YYYY-MM or YYYY-MM-DD
    iso_match = re.match(r"^(\d{4})[-/](\d{1,2})(?:[-/]\d{1,2})?$", s)
    if iso_match:
        y, m = int(iso_match.group(1)), int(iso_match.group(2))
        if 1 <= m <= 12 and 1990 <= y <= 2040:
            return (y, m)

    # Pattern: MM/YYYY
    my_match = re.match(r"^(\d{1,2})[-/](\d{4})$", s)
    if my_match:
        m, y = int(my_match.group(1)), int(my_match.group(2))
        if 1 <= m <= 12 and 1990 <= y <= 2040:
            return (y, m)

    # Textual months
    months = {
        "jan": 1, "january": 1, "feb": 2, "february": 2,
        "mar": 3, "march": 3, "apr": 4, "april": 4,
        "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
        "aug": 8, "august": 8, "sep": 9, "september": 9,
        "oct": 10, "october": 10, "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }
    for m_name, m_val in months.items():
        if m_name in s:
            y_match = re.search(r"\b(19\d{2}|20\d{2})\b", s)
            if y_match:
                y = int(y_match.group(1))
                if 1990 <= y <= 2040:
                    return (y, m_val)

    return None


def calculate_experience_months(
    start_str: Optional[str],
    end_str: Optional[str],
    is_current: bool,
) -> Tuple[Optional[int], bool]:
    """
    Calculate duration in months.
    Returns (months, is_incomplete).
    If dates are missing, invalid, or unparseable:
      - is_incomplete = True
      - months = None
      - Do NOT award duration bonus. Do NOT invent a 1-month duration.
    """
    start_ym = parse_date_to_month_year(start_str)
    if not start_ym:
        return (None, True)

    if is_current:
        now = datetime.now(timezone.utc)
        end_ym = (now.year, now.month)
    else:
        end_ym = parse_date_to_month_year(end_str)
        if not end_ym:
            return (None, True)

    start_y, start_m = start_ym
    end_y, end_m = end_ym
    total_months = (end_y - start_y) * 12 + (end_m - start_m) + 1
    if total_months < 0:
        return (None, True)
    return (total_months, False)


def calculate_compatibility_score(
    job: Job,
    student_user: User,
    student_profile: StudentProfile,
    approved_skills: List[StudentSkill],
    approved_projects: List[StudentProject],
    approved_experiences: List[StudentExperience],
    approved_certifications: List[StudentCertification],
) -> Tuple[float, ScoreBreakdown, List[str], List[str], List[str], bool, str]:
    """
    Continuous 0-100 weighted compatibility score engine across 5 verified dimensions:
    - S_skills (max 50 points)
    - S_academics (max 20 points)
    - S_projects (max 15 points)
    - S_experience (max 7 points objective: 5 base + 2 duration)
    - S_certifications (max 5 points)

    Returns:
    (
        total_score: float,
        breakdown: ScoreBreakdown,
        matched_skills: List[str],
        missing_mandatory_skills: List[str],
        recommended_skills: List[str],
        no_skill_requirements: bool,
        match_rationale: str
    )
    """
    # -------------------------------------------------------------------------
    # 1. Skill Compatibility (S_skills, max 50 points)
    # -------------------------------------------------------------------------
    # Map student approved skills: canonical_key -> original_name & proficiency multiplier
    student_skill_map: Dict[str, Tuple[str, float]] = {}
    proficiency_multipliers = {
        "expert": 1.15,
        "advanced": 1.05,
        "intermediate": 1.0,
        "beginner": 0.85,
    }
    for sk in approved_skills:
        c_key = normalize_skill(sk.skill_name)
        if c_key:
            mult = proficiency_multipliers.get((sk.proficiency_level or "intermediate").lower(), 1.0)
            # Store highest multiplier if duplicate
            if c_key not in student_skill_map or mult > student_skill_map[c_key][1]:
                student_skill_map[c_key] = (sk.skill_name, mult)

    job_skills: List[JobSkill] = job.skills or []
    mandatory_job_skills = [s for s in job_skills if s.is_mandatory]
    preferred_job_skills = [s for s in job_skills if not s.is_mandatory]

    matched_skills_set: Set[str] = set()
    missing_mandatory_list: List[str] = []
    recommended_skills_list: List[str] = []

    s_skills: float = 0.0
    no_skill_reqs: bool = False

    if not job_skills:
        # User Safeguard 3: Neutral handling when no skills are requested
        # Do not interpret absence of requirements as 100% compatibility.
        # Neutral allocation = 25.0 points (50% of the 50-point skill dimension).
        no_skill_reqs = True
        s_skills = 25.0
    else:
        # Calculate dynamic point budget allocation
        has_mand = len(mandatory_job_skills) > 0
        has_pref = len(preferred_job_skills) > 0

        if has_mand and has_pref:
            mand_budget = 30.0
            pref_budget = 20.0
        elif has_mand and not has_pref:
            mand_budget = 50.0
            pref_budget = 0.0
        else:
            mand_budget = 0.0
            pref_budget = 50.0

        # Mandatory Scoring
        if has_mand:
            sum_mand_weights = sum(float(s.weight_factor or 1.0) for s in mandatory_job_skills)
            mand_weighted_earned = 0.0
            for ms in mandatory_job_skills:
                c_key = normalize_skill(ms.skill_name)
                w = float(ms.weight_factor or 1.0)
                if c_key in student_skill_map:
                    matched_skills_set.add(ms.skill_name)
                    earned = w * min(1.0, student_skill_map[c_key][1])
                    mand_weighted_earned += earned
                else:
                    missing_mandatory_list.append(ms.skill_name)

            if sum_mand_weights > 0:
                s_skills += mand_budget * min(1.0, mand_weighted_earned / sum_mand_weights)

        # Preferred Scoring
        if has_pref:
            sum_pref_weights = sum(float(s.weight_factor or 1.0) for s in preferred_job_skills)
            pref_weighted_earned = 0.0
            for ps in preferred_job_skills:
                c_key = normalize_skill(ps.skill_name)
                w = float(ps.weight_factor or 1.0)
                if c_key in student_skill_map:
                    matched_skills_set.add(ps.skill_name)
                    earned = w * min(1.0, student_skill_map[c_key][1])
                    pref_weighted_earned += earned
                else:
                    recommended_skills_list.append(ps.skill_name)

            if sum_pref_weights > 0:
                s_skills += pref_budget * min(1.0, pref_weighted_earned / sum_pref_weights)

    s_skills = max(0.0, min(50.0, s_skills))

    # -------------------------------------------------------------------------
    # 2. Academic Performance (S_academics, max 20 points)
    # -------------------------------------------------------------------------
    s_academics: float = 0.0
    cgpa_raw = student_profile.cgpa
    min_cgpa_raw = job.min_cgpa

    # CGPA Component (15 points max)
    # Safeguard 1 & 2: Invalid CGPA outside 0-10 receives 0 academic points. Missing receives 0.
    if cgpa_raw is not None:
        try:
            cgpa_val = float(cgpa_raw)
            min_cgpa_val = float(min_cgpa_raw) if min_cgpa_raw is not None else 0.0

            if 0.0 <= cgpa_val <= 10.0:
                if cgpa_val >= min_cgpa_val:
                    if min_cgpa_val >= 10.0:
                        s_cgpa = 15.0 if cgpa_val >= 10.0 else 0.0
                    elif min_cgpa_val <= 0.0:
                        s_cgpa = 10.0 + 5.0 * (cgpa_val / 10.0)
                    else:
                        s_cgpa = 10.0 + 5.0 * ((cgpa_val - min_cgpa_val) / (10.0 - min_cgpa_val))
                else:
                    # Partial credit below cutoff
                    if min_cgpa_val > 0:
                        s_cgpa = 7.5 * max(0.0, cgpa_val / min_cgpa_val)
                    else:
                        s_cgpa = 0.0
                s_academics += max(0.0, min(15.0, s_cgpa))
            else:
                # Invalid CGPA (>10 or <0)
                s_academics += 0.0
        except (ValueError, TypeError):
            s_academics += 0.0

    # Backlog Component (5 points max)
    active_b = student_profile.active_backlogs
    total_b = student_profile.total_backlogs
    if active_b is not None and total_b is not None:
        if active_b == 0 and total_b == 0:
            s_academics += 5.0
        elif active_b == 0 and total_b > 0:
            s_academics += 3.0
        elif active_b > 0:
            max_act = job.max_active_backlogs if job.max_active_backlogs is not None else 0
            if active_b <= max_act:
                s_academics += 1.0
            else:
                s_academics += 0.0
    else:
        # Unrecorded backlogs receive 0
        s_academics += 0.0

    s_academics = max(0.0, min(20.0, s_academics))

    # -------------------------------------------------------------------------
    # 3. Hands-On Project Relevance (S_projects, max 15 points)
    # -------------------------------------------------------------------------
    s_projects: float = 0.0
    job_target_skill_keys: Set[str] = {
        normalize_skill(s.skill_name) for s in job_skills if normalize_skill(s.skill_name)
    }

    # Extract all project technologies deduplicated
    unique_proj_techs: Set[str] = set()
    has_project_url = False
    has_substantive_desc = False

    for proj in approved_projects:
        if proj.project_url and proj.project_url.strip():
            has_project_url = True
        if proj.description and len(proj.description.strip()) >= 50:
            has_substantive_desc = True

        raw_tech = proj.technologies or ""
        tokens = re.split(r"[,;/|•\n\r]+", raw_tech)
        for t in tokens:
            norm_t = normalize_skill(t)
            if norm_t:
                unique_proj_techs.add(norm_t)

    # Technology Match (max 12 points)
    if not job_target_skill_keys:
        if approved_projects:
            s_projects += 6.0  # Neutral project technology baseline
    else:
        matched_proj_techs = unique_proj_techs.intersection(job_target_skill_keys)
        n_matched = len(matched_proj_techs)
        n_target = min(4, len(job_target_skill_keys))
        if n_target > 0:
            tech_pts = 12.0 * min(1.0, n_matched / n_target)
            s_projects += tech_pts

    # Project Completeness / Production Readiness (max 3 points)
    if has_project_url:
        s_projects += 1.5
    if has_substantive_desc:
        s_projects += 1.5

    s_projects = max(0.0, min(15.0, s_projects))

    # -------------------------------------------------------------------------
    # 4. Industry Experience & Internships (S_experience, max 7 points objective)
    # -------------------------------------------------------------------------
    # Approved objective scoring rules:
    # - Relevant / technical role base: 5.0 points
    # - General role base: 2.0 points
    # - Valid duration >= 2 months: +2.0 points
    # - Valid duration >= 1 month and < 2 months: +1.0 point
    # - Missing, invalid, or unparseable dates: +0.0 duration points
    # - Subjective description-length bonus (+3.0 pts / +1.5 pts) is removed.
    # - Unused 3 points are not redistributed; experience score never exceeds 7.0 pts.
    s_experience: float = 0.0
    if approved_experiences:
        has_tech_role = False
        has_general_role = False
        duration_bonus = 0.0

        for exp in approved_experiences:
            role_lower = (exp.role_title or "").lower()
            desc_lower = (exp.description or "").lower()

            # Technical role check without standalone 'intern'
            is_role_tech = any(kw in role_lower for kw in TECHNICAL_ROLE_KEYWORDS)
            # Or description/role references job skills
            is_skill_mentioned = any(
                sk_key in role_lower or sk_key in desc_lower
                for sk_key in job_target_skill_keys
            ) if job_target_skill_keys else False

            if is_role_tech or is_skill_mentioned:
                has_tech_role = True
            else:
                has_general_role = True

            # Duration calculation (Safeguard 4)
            months, is_incomplete = calculate_experience_months(
                exp.start_date,
                exp.end_date,
                exp.is_current,
            )
            if not is_incomplete and months is not None:
                if months >= 2:
                    duration_bonus = max(duration_bonus, 2.0)
                elif months >= 1:
                    duration_bonus = max(duration_bonus, 1.0)
            # If incomplete or missing dates: duration_bonus remains 0.0. No invented duration.

        # Base role points: 5.0 for technical role, else 2.0 for general role
        if has_tech_role:
            s_experience += 5.0
        elif has_general_role:
            s_experience += 2.0

        # Duration bonus (max 2 points: +2.0 for >= 2 months, +1.0 for >= 1 month)
        s_experience += duration_bonus

    s_experience = max(0.0, min(7.0, s_experience))

    # -------------------------------------------------------------------------
    # 5. Professional Certifications (S_certifications, max 5 points)
    # -------------------------------------------------------------------------
    s_certifications: float = 0.0
    relevant_cert_count = 0
    general_cert_count = 0

    for cert in approved_certifications:
        c_name = (cert.certificate_name or "").lower()
        c_org = (cert.issuing_organization or "").lower()
        full_text = f"{c_name} {c_org}"

        is_relevant = False
        # Check against job target skills
        for j_skill in job_target_skill_keys:
            if j_skill in full_text:
                is_relevant = True
                break

        # Check against recognized cloud/tech credential keywords
        if not is_relevant:
            for kw in CERTIFICATION_RECOGNITION_KEYWORDS:
                if kw in full_text:
                    is_relevant = True
                    break

        if is_relevant:
            relevant_cert_count += 1
        else:
            general_cert_count += 1

    if relevant_cert_count >= 2:
        s_certifications = 5.0
    elif relevant_cert_count == 1:
        s_certifications = 3.5
    elif general_cert_count >= 1:
        s_certifications = 1.5
    else:
        s_certifications = 0.0

    s_certifications = max(0.0, min(5.0, s_certifications))

    # -------------------------------------------------------------------------
    # Total Score Compilation & Normalization to 0-100%
    # -------------------------------------------------------------------------
    # Dimension weights:
    # Skills: 50, Academics: 20, Projects: 15, Experience: 7, Certifications: 5
    # Maximum raw score = 50 + 20 + 15 + 7 + 5 = 97.0 points.
    MAX_RAW_SCORE = 97.0
    raw_score = s_skills + s_academics + s_projects + s_experience + s_certifications
    raw_score = max(0.0, min(MAX_RAW_SCORE, raw_score))

    # Normalized compatibility score scaled to 0-100%
    compatibility_score = round((raw_score / MAX_RAW_SCORE) * 100.0, 2)
    compatibility_score = max(0.0, min(100.0, compatibility_score))
    total_score = compatibility_score

    breakdown = ScoreBreakdown(
        skills=round(s_skills, 2),
        academics=round(s_academics, 2),
        projects=round(s_projects, 2),
        experience=round(s_experience, 2),
        certifications=round(s_certifications, 2),
    )

    # -------------------------------------------------------------------------
    # Natural Language Explainability Summary
    # -------------------------------------------------------------------------
    rationale_parts = []
    if total_score >= 80.0:
        fit_tier = "Exceptional compatibility"
    elif total_score >= 65.0:
        fit_tier = "Strong compatibility"
    elif total_score >= 50.0:
        fit_tier = "Moderate compatibility"
    else:
        fit_tier = "Preliminary compatibility"

    rationale_parts.append(f"{fit_tier} ({total_score:.1f}% overall match).")

    # Academics summary
    if cgpa_raw is not None:
        rationale_parts.append(
            f"Academic record shows {float(cgpa_raw):.2f} CGPA with "
            f"{student_profile.active_backlogs or 0} active backlogs."
        )

    # Skills summary
    if no_skill_reqs:
        rationale_parts.append("Posting specifies no hard skill constraints.")
    else:
        matched_cnt = len(matched_skills_set)
        total_req_cnt = len(job_skills)
        rationale_parts.append(
            f"Matched {matched_cnt}/{total_req_cnt} requested competencies"
            + (f" ({', '.join(sorted(list(matched_skills_set))[:4])})" if matched_skills_set else "")
            + "."
        )

    # Projects / Experience summary
    if approved_projects:
        rationale_parts.append(f"Demonstrated practical ability in {len(approved_projects)} approved technical project(s).")
    if approved_experiences:
        rationale_parts.append(f"Possesses {len(approved_experiences)} verified industry / internship experience record(s).")
    if relevant_cert_count > 0:
        rationale_parts.append(f"Holds {relevant_cert_count} relevant industry credential(s).")

    match_rationale = " ".join(rationale_parts)

    return (
        total_score,
        breakdown,
        sorted(list(matched_skills_set)),
        missing_mandatory_list,
        recommended_skills_list,
        no_skill_reqs,
        match_rationale,
    )

