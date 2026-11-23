from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.job import EmploymentType, WorkMode
from app.schemas.job import CriterionEvaluation


class ScoreBreakdown(BaseModel):
    """5-dimensional weighted score breakdown strictly summing to max 100 points."""
    skills: float = Field(..., ge=0.0, le=50.0, description="Skill compatibility score (0-50)")
    academics: float = Field(..., ge=0.0, le=20.0, description="Academic performance score (0-20)")
    projects: float = Field(..., ge=0.0, le=15.0, description="Hands-on project relevance score (0-15)")
    experience: float = Field(..., ge=0.0, le=10.0, description="Industry experience score (0-7 objective points: max 5 base + 2 duration)")
    certifications: float = Field(..., ge=0.0, le=5.0, description="Verified certification score (0-5)")


class JobMatchEvaluationResponse(BaseModel):
    """Detailed evaluation result for a student against a specific job opportunity."""
    job_id: int
    job_title: str
    company_name: str
    student_id: int
    student_name: str
    is_eligible: bool = Field(..., description="Deterministic academic & policy eligibility boolean")
    reasons: List[str] = Field(default_factory=list, description="Explanations for failed criteria")
    passed_criteria: List[str] = Field(default_factory=list, description="Names of passed criteria")
    failed_criteria: List[str] = Field(default_factory=list, description="Names of failed criteria")
    criteria: Dict[str, CriterionEvaluation] = Field(default_factory=dict, description="Detailed per-criterion evaluation")
    compatibility_score: float = Field(..., ge=0.0, le=100.0, description="Continuous weighted match score (0-100)")
    score_breakdown: ScoreBreakdown
    matched_skills: List[str] = Field(default_factory=list, description="Skills present in both student profile and job posting")
    missing_mandatory_skills: List[str] = Field(default_factory=list, description="Mandatory job skills lacking in student profile")
    recommended_skills: List[str] = Field(default_factory=list, description="Preferred job skills that would boost match")
    no_skill_requirements: bool = Field(False, description="Flag indicating job posted zero skill requirements")
    match_rationale: str = Field(..., description="Deterministic explainable summary of candidate fit")


class JobRecommendationCard(BaseModel):
    """Lightweight recommendation card for student dashboard and explore jobs feed."""
    job_id: int
    title: str
    company_name: str
    company_industry: Optional[str] = None
    location: str
    employment_type: EmploymentType
    work_mode: WorkMode
    salary_range: Optional[str] = None
    ctc_lpa: Optional[float] = None
    application_deadline: datetime
    is_eligible: bool
    compatibility_score: float = Field(..., ge=0.0, le=100.0)
    score_breakdown: ScoreBreakdown
    matched_skills: List[str] = Field(default_factory=list)
    missing_mandatory_skills: List[str] = Field(default_factory=list)
    recommended_skills: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    relevance_tier: str = Field(default="directly_relevant", description="directly_relevant | interdisciplinary | open_to_all | not_relevant")
    relevance_reason: Optional[str] = None
    branch_match_status: str = Field(default="matched", description="matched | interdisciplinary | open_to_all | branch_mismatch")
    institution_id: Optional[int] = None
    institution_name: Optional[str] = None


class JobRecommendationListResponse(BaseModel):
    """Partitioned recommendation response separating eligible and ineligible opportunities."""
    total_eligible: int
    total_ineligible: int
    eligible_jobs: List[JobRecommendationCard]
    ineligible_jobs: List[JobRecommendationCard]


class CandidateRankedCard(BaseModel):
    """Ranked eligible student profile for TPO campus drive intelligence."""
    rank: int
    student_id: int
    user_id: int
    student_name: str
    roll_number: str
    department_name: Optional[str] = None
    cgpa: float
    graduation_year: int
    compatibility_score: float = Field(..., ge=0.0, le=100.0)
    score_breakdown: ScoreBreakdown
    matched_skills: List[str] = Field(default_factory=list)
    match_rationale: str


class CandidateIneligibleCard(BaseModel):
    """Audit card for candidate failing deterministic eligibility cutoffs."""
    student_id: int
    user_id: int
    student_name: str
    roll_number: str
    department_name: Optional[str] = None
    cgpa: Optional[float] = None
    graduation_year: Optional[int] = None
    compatibility_score: float = Field(..., ge=0.0, le=100.0)
    failed_criteria: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)


class CandidateIntelligenceResponse(BaseModel):
    """Complete candidate intelligence view for TPO campus placement drive."""
    job_id: int
    job_title: str
    company_name: str
    total_candidates: int
    eligible_count: int
    ineligible_count: int
    ranked_eligible_candidates: List[CandidateRankedCard]
    ineligible_candidates: List[CandidateIneligibleCard]

