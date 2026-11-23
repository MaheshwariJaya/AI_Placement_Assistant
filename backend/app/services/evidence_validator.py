import logging
import re
from typing import Optional, List, Tuple
from app.schemas.resume import (
    ResumeStructuredData,
    PersonalInfo,
    EducationItem,
    SkillItem,
    ProjectItem,
    ExperienceItem,
    CertificationItem,
)

logger = logging.getLogger(__name__)

DEGREE_SYNONYMS = {
    "bachelor of technology": ["b.tech", "btech", "b tech"],
    "b.tech": ["bachelor of technology", "btech", "b tech"],
    "bachelor of engineering": ["b.e.", "b.e", "be", "b eng"],
    "b.e.": ["bachelor of engineering", "b.e", "be"],
    "b.e": ["bachelor of engineering", "b.e.", "be"],
    "master of technology": ["m.tech", "mtech", "m tech"],
    "m.tech": ["master of technology", "mtech"],
    "bachelor of computer applications": ["bca", "b.c.a"],
    "bca": ["bachelor of computer applications", "b.c.a"],
    "master of computer applications": ["mca", "m.c.a"],
    "mca": ["master of computer applications", "m.c.a"],
    "senior secondary (class xii)": ["class xii", "class 12", "12th", "senior secondary", "cbse"],
    "secondary school (class x)": ["class x", "class 10", "10th", "secondary school", "cbse"],
}


def normalize_text_for_search(text: str) -> str:
    """Normalize whitespace and lowercase for reliable fuzzy/substring search."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip().lower()


def find_supporting_line(needle: str, raw_text: str, max_length: int = 150) -> Optional[str]:
    """Find a verbatim snippet or line in raw_text containing needle or its synonyms."""
    if not needle or not raw_text:
        return None
    needle_clean = needle.strip()
    if not needle_clean:
        return None

    needles_to_try = [needle_clean]
    syns = DEGREE_SYNONYMS.get(needle_clean.lower(), [])
    needles_to_try.extend(syns)

    for n in needles_to_try:
        # Search line by line first for concise evidence
        for line in raw_text.splitlines():
            line_clean = line.strip()
            if n.lower() in line_clean.lower():
                if len(line_clean) > max_length:
                    return line_clean[:max_length] + "..."
                return line_clean

        # Fallback to substring in raw_text
        lower_raw = raw_text.lower()
        idx = lower_raw.find(n.lower())
        if idx != -1:
            start = max(0, idx - 20)
            end = min(len(raw_text), idx + len(n) + 40)
            snippet = raw_text[start:end].replace("\n", " ").strip()
            return snippet
    return None


def verify_text_presence(value: str, raw_text: str, min_word_match: float = 0.6) -> bool:
    """
    Verify whether a string value is grounded in the raw text.
    Handles exact match, case-insensitive match, degree synonyms, and multi-word token overlap.
    """
    if not value or not raw_text:
        return False
    val_clean = normalize_text_for_search(value)
    text_clean = normalize_text_for_search(raw_text)

    # 1. Direct substring match
    if val_clean in text_clean:
        return True

    # 1b. Check degree synonyms
    synonyms = DEGREE_SYNONYMS.get(val_clean, [])
    for syn in synonyms:
        if syn in text_clean:
            return True

    # 2. Token overlap for longer names/titles
    tokens = [t for t in re.split(r"[^\w+#.]", val_clean) if len(t) >= 2]
    if not tokens:
        return False
    matched = sum(1 for t in tokens if t in text_clean)
    return (matched / len(tokens)) >= min_word_match


def validate_and_sanitize_resume_data(
    raw_text: str,
    data: ResumeStructuredData,
) -> ResumeStructuredData:
    """
    Core Grounding & Evidence Validation Layer.
    Audits every extracted entity against the raw extracted resume text:
    1. Verifies that claimed evidence or value actually exists in raw_text.
    2. Purges hallucinated entities (skills, education, projects, experiences, certifications).
    3. Nullifies hallucinated scalar fields (e.g., invented CGPA, invented dates, invented URLs).
    4. Attaches verbatim evidence quotes and sets appropriate confidence levels.
    """
    if not raw_text:
        # If no text extractable, return empty/nullified structure
        return ResumeStructuredData(
            personal_info=PersonalInfo(),
            education=[],
            skills=[],
            projects=[],
            experiences=[],
            certifications=[],
            extraction_method=data.extraction_method,
            overall_confidence="low",
            hallucinations_purged=0,
        )

    purged_count = 0
    rejected_entities: List[str] = []
    clean_text = normalize_text_for_search(raw_text)

    # -------------------------------------------------------------------------
    # 1. Personal Information Validation
    # -------------------------------------------------------------------------
    p = data.personal_info or PersonalInfo()
    
    # Full Name: verify presence
    if p.full_name:
        if not verify_text_presence(p.full_name, raw_text, min_word_match=0.7):
            logger.info(f"Purging hallucinated full_name: '{p.full_name}' not in resume text.")
            rejected_entities.append(f"personal_info.full_name: '{p.full_name}'")
            p.full_name = None
            purged_count += 1
        else:
            if not p.evidence:
                p.evidence = find_supporting_line(p.full_name, raw_text)

    # Email: verify presence
    if p.email:
        if p.email.lower() not in clean_text:
            logger.info(f"Purging hallucinated email: '{p.email}' not in resume text.")
            rejected_entities.append(f"personal_info.email: '{p.email}'")
            p.email = None
            purged_count += 1
        elif not p.evidence:
            p.evidence = find_supporting_line(p.email, raw_text)

    # Phone: verify digits presence
    if p.phone:
        digits_only = re.sub(r"\D", "", p.phone)
        raw_digits = re.sub(r"\D", "", raw_text)
        if len(digits_only) >= 7 and digits_only not in raw_digits:
            logger.info(f"Purging hallucinated phone: '{p.phone}' not in resume text.")
            rejected_entities.append(f"personal_info.phone: '{p.phone}'")
            p.phone = None
            purged_count += 1
        elif not p.evidence:
            p.evidence = find_supporting_line(p.phone, raw_text)

    # LinkedIn / GitHub / Portfolio URLs
    if p.linkedin_url:
        if "linkedin" not in clean_text:
            rejected_entities.append(f"personal_info.linkedin_url: '{p.linkedin_url}'")
            p.linkedin_url = None
            purged_count += 1
    if p.github_url:
        if "github" not in clean_text:
            rejected_entities.append(f"personal_info.github_url: '{p.github_url}'")
            p.github_url = None
            purged_count += 1
    if p.portfolio_url:
        portfolio_clean = p.portfolio_url.replace("https://", "").replace("http://", "").split("/")[0].lower()
        if portfolio_clean not in clean_text and not verify_text_presence(p.portfolio_url, raw_text):
            rejected_entities.append(f"personal_info.portfolio_url: '{p.portfolio_url}'")
            p.portfolio_url = None
            purged_count += 1

    # Location
    if p.location and not verify_text_presence(p.location, raw_text, min_word_match=0.5):
        rejected_entities.append(f"personal_info.location: '{p.location}'")
        p.location = None
        purged_count += 1

    # -------------------------------------------------------------------------
    # 2. Skills Validation
    # -------------------------------------------------------------------------
    validated_skills: List[SkillItem] = []
    for skill in (data.skills or []):
        s_name = skill.skill_name.strip()
        if not s_name:
            continue

        # Check exact word boundary or symbol match
        is_present = False
        s_lower = s_name.lower()

        # Handle programming language symbols like C++, C#, .NET
        if s_lower in ("c++", "c#", ".net"):
            is_present = s_lower in clean_text
        elif len(s_lower) <= 2:
            # Short names like "c", "r", "go" require strict word boundaries
            pattern = rf"(?:\b|_){re.escape(s_lower)}(?:\b|_)"
            is_present = bool(re.search(pattern, clean_text))
        else:
            pattern = rf"\b{re.escape(s_lower)}\b"
            is_present = bool(re.search(pattern, clean_text))

        if is_present:
            evidence = skill.evidence or find_supporting_line(s_name, raw_text)
            validated_skills.append(
                SkillItem(
                    skill_name=s_name,
                    category=skill.category or "technical",
                    proficiency_level=skill.proficiency_level or "intermediate",
                    evidence=evidence,
                    confidence=skill.confidence or "high",
                )
            )
        else:
            logger.info(f"Purging hallucinated skill: '{s_name}' not found in resume text.")
            rejected_entities.append(f"skill: '{s_name}'")
            purged_count += 1

    # -------------------------------------------------------------------------
    # 3. Education Validation
    # -------------------------------------------------------------------------
    validated_education: List[EducationItem] = []
    for edu in (data.education or []):
        inst_present = verify_text_presence(edu.institution, raw_text, min_word_match=0.5)
        degree_present = verify_text_presence(edu.degree, raw_text, min_word_match=0.4)

        # Require at least institution or degree to exist in text
        if not inst_present and not degree_present:
            logger.info(f"Purging hallucinated education: '{edu.institution}' / '{edu.degree}' not found in resume text.")
            rejected_entities.append(f"education: '{edu.institution}' / '{edu.degree}'")
            purged_count += 1
            continue

        # CGPA / Percentage grounding check
        validated_score = edu.cgpa_or_percentage
        if validated_score:
            # Extract numeric parts of score (e.g. "8.45" or "91.4")
            score_num_match = re.search(r"(\d+(?:\.\d+)?)", str(validated_score))
            if score_num_match:
                score_num = score_num_match.group(1)
                if score_num not in clean_text:
                    logger.info(f"Purging hallucinated academic score: '{validated_score}' not in resume text.")
                    rejected_entities.append(f"education.cgpa_or_percentage: '{validated_score}'")
                    validated_score = None
                    purged_count += 1

        # Year checks
        start_yr = edu.start_year
        if start_yr and str(start_yr) not in clean_text:
            start_yr = None
        end_yr = edu.end_year
        if end_yr and str(end_yr) not in clean_text:
            end_yr = None

        evidence = edu.evidence or find_supporting_line(edu.institution, raw_text) or find_supporting_line(edu.degree, raw_text)
        validated_education.append(
            EducationItem(
                institution=edu.institution if inst_present else "Collegiate Institution",
                degree=edu.degree,
                field_of_study=edu.field_of_study if (edu.field_of_study and verify_text_presence(edu.field_of_study, raw_text, 0.5)) else None,
                start_year=start_yr,
                end_year=end_yr,
                cgpa_or_percentage=validated_score,
                evidence=evidence,
                confidence="high" if (inst_present and degree_present) else "medium",
            )
        )

    # -------------------------------------------------------------------------
    # 4. Projects Validation
    # -------------------------------------------------------------------------
    validated_projects: List[ProjectItem] = []
    for proj in (data.projects or []):
        title_present = verify_text_presence(proj.title, raw_text, min_word_match=0.5)
        if not title_present:
            logger.info(f"Purging hallucinated project: '{proj.title}' not found in resume text.")
            rejected_entities.append(f"project: '{proj.title}'")
            purged_count += 1
            continue

        # Validate project URL if present
        proj_url = proj.project_url
        if proj_url and not verify_text_presence(proj_url, raw_text):
            proj_url = None

        evidence = proj.evidence or find_supporting_line(proj.title, raw_text)
        validated_projects.append(
            ProjectItem(
                title=proj.title,
                description=proj.description,
                technologies=proj.technologies,
                project_url=proj_url,
                start_date=proj.start_date,
                end_date=proj.end_date,
                evidence=evidence,
                confidence=proj.confidence or "high",
            )
        )

    # -------------------------------------------------------------------------
    # 5. Experience Validation
    # -------------------------------------------------------------------------
    validated_experiences: List[ExperienceItem] = []
    for exp in (data.experiences or []):
        company_present = verify_text_presence(exp.company_name, raw_text, min_word_match=0.5)
        role_present = verify_text_presence(exp.role_title, raw_text, min_word_match=0.4)

        if not company_present and not role_present:
            logger.info(f"Purging hallucinated experience: '{exp.company_name}' / '{exp.role_title}' not found in resume text.")
            rejected_entities.append(f"experience: '{exp.company_name}' / '{exp.role_title}'")
            purged_count += 1
            continue

        evidence = exp.evidence or find_supporting_line(exp.company_name, raw_text) or find_supporting_line(exp.role_title, raw_text)
        validated_experiences.append(
            ExperienceItem(
                company_name=exp.company_name,
                role_title=exp.role_title,
                description=exp.description,
                start_date=exp.start_date,
                end_date=exp.end_date,
                is_current=exp.is_current,
                evidence=evidence,
                confidence="high" if company_present else "medium",
            )
        )

    # -------------------------------------------------------------------------
    # 6. Certifications Validation
    # -------------------------------------------------------------------------
    validated_certifications: List[CertificationItem] = []
    for cert in (data.certifications or []):
        cert_present = verify_text_presence(cert.certificate_name, raw_text, min_word_match=0.5)
        issuer_present = verify_text_presence(cert.issuing_organization, raw_text, min_word_match=0.5)

        if not cert_present and not issuer_present:
            logger.info(f"Purging hallucinated certification: '{cert.certificate_name}' not found in resume text.")
            rejected_entities.append(f"certification: '{cert.certificate_name}'")
            purged_count += 1
            continue

        evidence = cert.evidence or find_supporting_line(cert.certificate_name, raw_text) or find_supporting_line(cert.issuing_organization, raw_text)
        validated_certifications.append(
            CertificationItem(
                certificate_name=cert.certificate_name,
                issuing_organization=cert.issuing_organization,
                issue_date=cert.issue_date,
                credential_url=cert.credential_url,
                evidence=evidence,
                confidence="high" if cert_present else "medium",
            )
        )

    # -------------------------------------------------------------------------
    # Overall Assessment
    # -------------------------------------------------------------------------
    overall_conf = "high"
    if purged_count > 0 or not validated_skills or not validated_education:
        overall_conf = "medium"
    if not p.full_name and not p.email:
        overall_conf = "low"

    return ResumeStructuredData(
        personal_info=p,
        education=validated_education,
        skills=validated_skills,
        projects=validated_projects,
        experiences=validated_experiences,
        certifications=validated_certifications,
        extraction_method=data.extraction_method,
        overall_confidence=overall_conf,
        hallucinations_purged=purged_count,
        rejected_entities=rejected_entities,
    )
