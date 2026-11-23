from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.job import EmploymentType, JobStatus, WorkMode
from app.schemas.company import CompanyResponse


# -----------------------------------------------------------------------------
# Skill & Department Junction Schemas
# -----------------------------------------------------------------------------

class JobSkillCreate(BaseModel):
    skill_name: str = Field(..., min_length=1, max_length=100)
    is_mandatory: bool = Field(True, description="True for Required Skills; False for Preferred Skills")
    weight_factor: float = Field(1.0, ge=0.1, le=3.0, description="Relative importance weight")


class JobSkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    skill_name: str
    is_mandatory: bool
    weight_factor: float


class JobDepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    department_name: Optional[str] = None
    department_code: Optional[str] = None


# -----------------------------------------------------------------------------
# Core Job Posting Schemas
# -----------------------------------------------------------------------------

class JobCreate(BaseModel):
    company_id: Optional[int] = Field(None, description="Partner corporate company ID (required for TPO/Admin campus drives; ignored for Recruiters)")
    title: str = Field(..., min_length=3, max_length=200, description="Job role title e.g. Associate Software Engineer")
    description: str = Field(..., min_length=10, description="Complete job profile, roles, responsibilities, and team overview")
    employment_type: EmploymentType = Field(EmploymentType.FULL_TIME, description="full_time, internship, intern_to_full_time")
    work_mode: WorkMode = Field(WorkMode.ON_SITE, description="on_site, hybrid, remote")
    location: str = Field(..., min_length=2, max_length=150, description="Primary work city or 'Remote'")
    salary_range: Optional[str] = Field(None, max_length=100, description="Display compensation string e.g. '12 - 16 LPA'")
    ctc_lpa: Optional[float] = Field(None, ge=0.0, description="Annual CTC in Lakhs Per Annum")
    base_salary_lpa: Optional[float] = Field(None, ge=0.0)
    stipend_monthly: Optional[float] = Field(None, ge=0.0)
    
    # Deterministic Academic Eligibility Cutoffs
    min_cgpa: float = Field(0.0, ge=0.0, le=10.0, description="Minimum CGPA cutoff (0.0 to 10.0)")
    target_graduation_year: Optional[int] = Field(None, ge=2020, le=2040, description="Target graduating batch e.g. 2026")
    max_active_backlogs: int = Field(0, ge=0, description="Maximum pending backlogs allowed")
    max_total_backlogs: int = Field(0, ge=0, description="Maximum historical backlogs allowed")
    application_deadline: datetime = Field(..., description="Timestamp after which applications close")
    status: JobStatus = Field(JobStatus.DRAFT, description="Initial lifecycle state: draft or published")
    institution_id: Optional[int] = Field(None, description="Optional target institution ID for campus-specific drives")

    # Structured Skills & Departments
    required_skills: List[str] = Field(default_factory=list, description="Mandatory technical or domain skills")
    preferred_skills: List[str] = Field(default_factory=list, description="Bonus / preferred skills")
    eligible_department_ids: List[int] = Field(default_factory=list, description="IDs of academic departments allowed to apply")


class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=10)
    employment_type: Optional[EmploymentType] = None
    work_mode: Optional[WorkMode] = None
    location: Optional[str] = Field(None, min_length=2, max_length=150)
    salary_range: Optional[str] = Field(None, max_length=100)
    ctc_lpa: Optional[float] = Field(None, ge=0.0)
    base_salary_lpa: Optional[float] = Field(None, ge=0.0)
    stipend_monthly: Optional[float] = Field(None, ge=0.0)
    min_cgpa: Optional[float] = Field(None, ge=0.0, le=10.0)
    target_graduation_year: Optional[int] = Field(None, ge=2020, le=2040)
    max_active_backlogs: Optional[int] = Field(None, ge=0)
    max_total_backlogs: Optional[int] = Field(None, ge=0)
    application_deadline: Optional[datetime] = None
    status: Optional[JobStatus] = None
    institution_id: Optional[int] = None

    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    eligible_department_ids: Optional[List[int]] = None


class JobStatusUpdate(BaseModel):
    status: JobStatus = Field(..., description="Target lifecycle state: draft, published, closed, cancelled")


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    company_name: str
    company_industry: Optional[str] = None
    created_by_user_id: int
    institution_id: Optional[int] = None
    institution_name: Optional[str] = None
    is_active: Optional[bool] = True
    title: str
    employment_type: EmploymentType
    work_mode: WorkMode
    location: str
    salary_range: Optional[str] = None
    ctc_lpa: Optional[float] = None
    min_cgpa: float
    target_graduation_year: Optional[int] = None
    max_active_backlogs: int
    max_total_backlogs: int
    application_deadline: datetime
    status: JobStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    skills: List[str] = Field(default_factory=list)
    eligible_department_names: List[str] = Field(default_factory=list)


class JobDetailResponse(JobResponse):
    description: str
    company: CompanyResponse
    base_salary_lpa: Optional[float] = None
    stipend_monthly: Optional[float] = None
    all_skills: List[JobSkillResponse] = Field(default_factory=list)
    eligible_departments: List[JobDepartmentResponse] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# Structured Eligibility Evaluation Schemas (Deterministic)
# -----------------------------------------------------------------------------

class CriterionEvaluation(BaseModel):
    criterion: str = Field(..., description="Academic cutoff name: CGPA, Department, Graduation Year, Backlogs, Skills, Deadline")
    required: Any
    student_value: Any
    passed: bool
    message: str


class JobEligibilityResult(BaseModel):
    job_id: int
    job_title: str
    student_id: int
    student_name: str
    is_eligible: bool = Field(..., description="Overall boolean eligibility pass flag")
    reasons: List[str] = Field(default_factory=list, description="Explanations for any unmet cutoff criteria")
    passed_criteria: List[str] = Field(default_factory=list, description="Names of passed criteria")
    failed_criteria: List[str] = Field(default_factory=list, description="Names of failed criteria")
    criteria: Dict[str, CriterionEvaluation] = Field(default_factory=dict, description="Detailed breakdown per criterion")
