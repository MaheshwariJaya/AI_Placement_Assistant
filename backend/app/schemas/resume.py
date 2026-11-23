import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator


def _parse_year_int(val: Any) -> Optional[int]:
    if val is None or val == "":
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, str):
        match = re.search(r"\b(19\d\d|20\d\d)\b", val)
        if match:
            return int(match.group(1))
    return None


class PersonalInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    full_name: Optional[str] = Field(None, description="Candidate full name")
    email: Optional[str] = Field(None, description="Candidate contact email")
    phone: Optional[str] = Field(None, description="Candidate phone number")
    location: Optional[str] = Field(None, description="City / Region")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    github_url: Optional[str] = Field(None, description="GitHub profile URL")
    portfolio_url: Optional[str] = Field(None, description="Portfolio or personal website URL")
    evidence: Optional[str] = Field(None, description="Verbatim text quote from resume verifying personal info")
    confidence: str = Field("high", description="Confidence level: high, medium, low")

    @model_validator(mode="before")
    @classmethod
    def normalize_personal_info(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("full_name") and data.get("name"):
                data["full_name"] = str(data["name"])
            if not data.get("full_name") and data.get("candidate_name"):
                data["full_name"] = str(data["candidate_name"])
            if data.get("phone") is not None and not isinstance(data.get("phone"), str):
                data["phone"] = str(data["phone"])
            if not data.get("linkedin_url") and data.get("linkedin"):
                data["linkedin_url"] = str(data["linkedin"])
            if not data.get("github_url") and data.get("github"):
                data["github_url"] = str(data["github"])
            if not data.get("portfolio_url") and (data.get("portfolio") or data.get("website")):
                data["portfolio_url"] = str(data.get("portfolio") or data.get("website"))
        return data


class EducationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    institution: str = Field(..., description="College or university name")
    degree: str = Field(..., description="Degree e.g. B.Tech, B.E., M.Tech, BCA, MCA, Class XII, Class X")
    field_of_study: Optional[str] = Field(None, description="Specialization / branch e.g. Computer Science")
    start_year: Optional[int] = Field(None, description="Year started")
    end_year: Optional[int] = Field(None, description="Graduation year")
    cgpa_or_percentage: Optional[str] = Field(None, description="Stated CGPA or percentage")
    evidence: Optional[str] = Field(None, description="Verbatim text quote from resume verifying education record")
    confidence: str = Field("high", description="Confidence level: high, medium, low")

    @model_validator(mode="before")
    @classmethod
    def normalize_education(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("institution"):
                data["institution"] = (
                    data.get("institution_name")
                    or data.get("school")
                    or data.get("college")
                    or data.get("university")
                    or "Collegiate Institution"
                )
            if not data.get("degree"):
                data["degree"] = data.get("degree_name") or data.get("qualification") or "Degree"
            if not data.get("field_of_study"):
                data["field_of_study"] = data.get("major") or data.get("branch") or data.get("department")
            if "start_year" in data:
                data["start_year"] = _parse_year_int(data["start_year"])
            if "end_year" in data:
                data["end_year"] = _parse_year_int(data["end_year"])
            if data.get("cgpa_or_percentage") is not None and not isinstance(data.get("cgpa_or_percentage"), str):
                data["cgpa_or_percentage"] = str(data["cgpa_or_percentage"])
        return data


class SkillItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    skill_name: str = Field(..., description="Name of the skill, e.g. Python, React, PostgreSQL")
    category: str = Field("technical", description="technical, soft, tool, framework, database, language")
    proficiency_level: str = Field("intermediate", description="beginner, intermediate, advanced, expert")
    evidence: Optional[str] = Field(None, description="Verbatim text quote from resume verifying skill mention")
    confidence: str = Field("high", description="Confidence level: high, medium, low")

    @model_validator(mode="before")
    @classmethod
    def normalize_skill(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("skill_name"):
                data["skill_name"] = data.get("name") or data.get("skill") or data.get("title") or ""
            if not data.get("category"):
                data["category"] = data.get("type") or "technical"
            if not data.get("proficiency_level"):
                data["proficiency_level"] = data.get("level") or data.get("proficiency") or "intermediate"
        return data


class ProjectItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    title: str = Field(..., description="Project title")
    description: Optional[str] = Field(None, description="Overview and key contributions")
    technologies: Optional[str] = Field(None, description="Key technologies used")
    project_url: Optional[str] = Field(None, description="Repository or live URL")
    start_date: Optional[str] = Field(None, description="e.g. Jan 2024")
    end_date: Optional[str] = Field(None, description="e.g. May 2024")
    evidence: Optional[str] = Field(None, description="Verbatim text quote from resume verifying project")
    confidence: str = Field("high", description="Confidence level: high, medium, low")

    @model_validator(mode="before")
    @classmethod
    def normalize_project(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("title"):
                data["title"] = data.get("project_name") or data.get("name") or "Project"
            techs = data.get("technologies")
            if isinstance(techs, list):
                data["technologies"] = ", ".join(str(t).strip() for t in techs if t)
            elif techs is not None and not isinstance(techs, str):
                data["technologies"] = str(techs)
            if not data.get("project_url") and (data.get("url") or data.get("link") or data.get("repo_url")):
                data["project_url"] = str(data.get("url") or data.get("link") or data.get("repo_url"))
            if data.get("start_date") is not None and not isinstance(data.get("start_date"), str):
                data["start_date"] = str(data["start_date"])
            if data.get("end_date") is not None and not isinstance(data.get("end_date"), str):
                data["end_date"] = str(data["end_date"])
        return data


class ExperienceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    company_name: str = Field(..., description="Company or organization name")
    role_title: str = Field(..., description="Job or internship role title")
    description: Optional[str] = Field(None, description="Responsibilities and impact")
    start_date: Optional[str] = Field(None, description="Start date")
    end_date: Optional[str] = Field(None, description="End date or Present")
    is_current: bool = Field(False, description="Whether this is the current position")
    evidence: Optional[str] = Field(None, description="Verbatim text quote from resume verifying experience")
    confidence: str = Field("high", description="Confidence level: high, medium, low")

    @model_validator(mode="before")
    @classmethod
    def normalize_experience(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("company_name"):
                data["company_name"] = data.get("company") or data.get("organization") or data.get("employer") or "Company"
            if not data.get("role_title"):
                data["role_title"] = data.get("role") or data.get("title") or data.get("position") or data.get("job_title") or "Role"
            if data.get("start_date") is not None and not isinstance(data.get("start_date"), str):
                data["start_date"] = str(data["start_date"])
            if data.get("end_date") is not None and not isinstance(data.get("end_date"), str):
                data["end_date"] = str(data["end_date"])
            if isinstance(data.get("is_current"), str):
                data["is_current"] = data["is_current"].lower() in ("true", "yes", "current", "1")
        return data


class CertificationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    certificate_name: str = Field(..., description="Certification title")
    issuing_organization: str = Field(..., description="Issuer e.g. AWS, Coursera, Google")
    issue_date: Optional[str] = Field(None, description="Date issued")
    credential_url: Optional[str] = Field(None, description="Verification or credential URL")
    evidence: Optional[str] = Field(None, description="Verbatim text quote from resume verifying certification")
    confidence: str = Field("high", description="Confidence level: high, medium, low")

    @model_validator(mode="before")
    @classmethod
    def normalize_certification(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("certificate_name"):
                data["certificate_name"] = data.get("name") or data.get("title") or data.get("certification") or data.get("certification_name") or "Certificate"
            if not data.get("issuing_organization"):
                data["issuing_organization"] = data.get("issuer") or data.get("organization") or data.get("issued_by") or "Issuer"
            if data.get("issue_date") is not None and not isinstance(data.get("issue_date"), str):
                data["issue_date"] = str(data["issue_date"])
            if not data.get("credential_url") and (data.get("url") or data.get("link")):
                data["credential_url"] = str(data.get("url") or data.get("link"))
        return data


class ResumeStructuredData(BaseModel):
    """Normalized structured data schema extracted from resumes."""
    model_config = ConfigDict(from_attributes=True)

    personal_info: Optional[PersonalInfo] = Field(default_factory=PersonalInfo)
    education: List[EducationItem] = Field(default_factory=list)
    skills: List[SkillItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    experiences: List[ExperienceItem] = Field(default_factory=list)
    certifications: List[CertificationItem] = Field(default_factory=list)
    extraction_method: str = Field("mock_rule_based", description="mock_rule_based, gemini_ai, or openai_ai")
    overall_confidence: str = Field("high", description="high, medium, low")
    hallucinations_purged: int = Field(0, description="Count of unsupported/hallucinated items removed during validation")
    rejected_entities: List[str] = Field(default_factory=list, description="Internal diagnostic list of unsupported/purged entities")


class ResumeUploadResponse(BaseModel):
    resume_id: int
    file_name: str
    file_size_bytes: int
    parsing_status: str
    message: str


class ResumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    file_name: str
    file_type: str
    file_size_bytes: int
    file_hash: str
    parsing_status: str
    is_active: bool
    parsed_entities: Optional[ResumeStructuredData] = None
    raw_text_preview: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ResumeReviewUpdateRequest(BaseModel):
    """Payload sent by student when editing extracted entities before approval."""
    structured_data: ResumeStructuredData


class ResumeSyncRequest(BaseModel):
    """
    Payload to approve and synchronize extracted entities into student profile.
    Each domain section can be toggled by the student during verification.
    """
    verified_data: Optional[ResumeStructuredData] = None
    sync_education: bool = True
    sync_skills: bool = True
    sync_projects: bool = True
    sync_experiences: bool = True
    sync_certifications: bool = True
    sync_links: bool = True
    update_existing_links: bool = True
    update_phone: bool = False


class ResumeSyncResponse(BaseModel):
    message: str
    synced_counts: Dict[str, int]
    verified_metrics_protected: bool = True
    protected_academic_fields: List[str] = [
        "cgpa",
        "roll_number",
        "graduation_year",
        "active_backlogs",
        "total_backlogs",
        "user_email",
    ]
