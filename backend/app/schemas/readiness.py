"""Pydantic schemas for Placement Readiness Prediction & Historical Analytics."""
from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.readiness import ReadinessCategory
from app.schemas.ai import AIUsageMetadata


READINESS_FORMULA_VERSION = "v1.0"

READINESS_TRANSPARENCY_NOTICE = (
    "Advisory Preparation Indicator Only: The Placement Readiness Index summarizes portfolio, resume, "
    "and practice indicators on a 0-100 scale. It is NOT a hiring probability or prediction, is never used "
    "to rank or automatically reject candidates, uses no sensitive personal characteristics, and remains "
    "strictly separate from official academic eligibility decisions (CGPA, backlogs, and branch rules). "
    "Missing data reflects unrecorded profile information rather than lack of ability."
)


class ReadinessCategoryDefinition(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: ReadinessCategory
    label: str
    min_score: float
    max_score: float
    summary: str
    criteria_notes: str


DEFAULT_CATEGORY_DEFINITIONS: List[ReadinessCategoryDefinition] = [
    ReadinessCategoryDefinition(
        category=ReadinessCategory.EXCELLENT_PREPARATION,
        label="Excellent Preparation",
        min_score=85.0,
        max_score=100.0,
        summary="Strong across verified skills, projects, resume completeness, and mock practice.",
        criteria_notes="Readiness Index >= 85.0 out of 100 across configured preparation indicators.",
    ),
    ReadinessCategoryDefinition(
        category=ReadinessCategory.PLACEMENT_READY,
        label="Placement Ready",
        min_score=70.0,
        max_score=84.99,
        summary="Solid preparation foundation with minor polish opportunities in interviews or credentials.",
        criteria_notes="Readiness Index between 70.0 and 84.99 out of 100.",
    ),
    ReadinessCategoryDefinition(
        category=ReadinessCategory.NEEDS_IMPROVEMENT,
        label="Needs Improvement",
        min_score=50.0,
        max_score=69.99,
        summary="Core foundation present, with focused skill, project, resume, or interview practice gaps.",
        criteria_notes="Readiness Index between 50.0 and 69.99 out of 100.",
    ),
    ReadinessCategoryDefinition(
        category=ReadinessCategory.REQUIRES_SIGNIFICANT_PREPARATION,
        label="Requires Significant Preparation",
        min_score=0.0,
        max_score=49.99,
        summary="Early preparation stage or incomplete portfolio records; build core projects, resume, and practice.",
        criteria_notes="Readiness Index below 50.0 out of 100 (or sparse recorded portfolio data).",
    ),
]


class ReadinessIndicatorWeights(BaseModel):
    """Configurable indicator weights summing to 100.0 points."""
    model_config = ConfigDict(from_attributes=True)

    verified_skills: float = Field(default=20.0, ge=0.0, le=50.0)
    project_portfolio: float = Field(default=15.0, ge=0.0, le=50.0)
    internship_experience: float = Field(default=10.0, ge=0.0, le=50.0)
    certifications: float = Field(default=8.0, ge=0.0, le=50.0)
    resume_quality: float = Field(default=15.0, ge=0.0, le=50.0)
    mock_interview_performance: float = Field(default=12.0, ge=0.0, le=50.0)
    aptitude_technical_assessment: float = Field(default=10.0, ge=0.0, le=50.0)
    profile_completeness: float = Field(default=10.0, ge=0.0, le=50.0)

    @model_validator(mode="after")
    def validate_positive_sum(self) -> "ReadinessIndicatorWeights":
        total = (
            self.verified_skills
            + self.project_portfolio
            + self.internship_experience
            + self.certifications
            + self.resume_quality
            + self.mock_interview_performance
            + self.aptitude_technical_assessment
            + self.profile_completeness
        )
        if total <= 0.0:
            raise ValueError("Indicator weights must sum to a positive value.")
        return self

    def normalized_dict(self) -> Dict[str, float]:
        raw = {
            "verified_skills": float(self.verified_skills),
            "project_portfolio": float(self.project_portfolio),
            "internship_experience": float(self.internship_experience),
            "certifications": float(self.certifications),
            "resume_quality": float(self.resume_quality),
            "mock_interview_performance": float(self.mock_interview_performance),
            "aptitude_technical_assessment": float(self.aptitude_technical_assessment),
            "profile_completeness": float(self.profile_completeness),
        }
        total = sum(raw.values())
        if abs(total - 100.0) < 0.01:
            return {k: round(v, 2) for k, v in raw.items()}
        factor = 100.0 / total
        return {k: round(v * factor, 2) for k, v in raw.items()}


class ReadinessIndicatorScore(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    label: str
    weight: float = Field(..., ge=0.0, le=100.0)
    raw_score_pct: float = Field(..., ge=0.0, le=100.0)
    weighted_points: float = Field(..., ge=0.0, le=100.0)
    status: Literal["strong", "moderate", "developing", "missing_data"]
    data_present: bool
    evidence_summary: str
    limitation_note: Optional[str] = None


class ReadOnlyAcademicSummary(BaseModel):
    """Official institutional academic metrics displayed separately and read-only for students."""
    model_config = ConfigDict(from_attributes=True)

    cgpa: Optional[float] = None
    active_backlogs: int = 0
    total_backlogs: int = 0
    graduation_year: Optional[int] = None
    department_name: Optional[str] = None
    is_placement_ready_flag: bool = True
    read_only_notice: str = (
        "Official academic records (CGPA, backlogs, branch) are verified by institutional staff, "
        "read-only for students, and evaluated independently from preparation readiness."
    )


class ReadinessRecommendationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str
    category: Literal["skills", "projects", "resume", "interview", "aptitude", "profile", "certifications"]
    priority: Literal["high", "medium", "low"]
    estimated_impact: str
    completed: bool = False
    completed_at: Optional[datetime] = None


class AIRecommendationSuggestion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(..., min_length=4, max_length=120)
    description: str = Field(..., min_length=10, max_length=500)
    category: Literal["skills", "projects", "resume", "interview", "aptitude", "profile", "certifications"]
    priority: Literal["high", "medium", "low"] = "medium"
    estimated_impact: str = Field(default="Improves overall preparation depth", max_length=140)


class ReadinessRecommendationsAIOutput(BaseModel):
    """Structured AI response for personalized advisory preparation recommendations."""
    model_config = ConfigDict(from_attributes=True)

    recommendations: List[AIRecommendationSuggestion] = Field(..., min_length=1, max_length=8)


class ReadinessCalculateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: Optional[int] = None
    target_role: Optional[str] = Field(default=None, max_length=200)
    custom_weights: Optional[ReadinessIndicatorWeights] = None
    include_ai_recommendations: bool = True


class RecommendationToggleRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    completed: bool


class ReadinessSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    job_id: Optional[int] = None
    job_title: Optional[str] = None
    target_role: Optional[str] = None
    formula_version: str
    overall_score: float = Field(..., ge=0.0, le=100.0)
    category: ReadinessCategory
    category_label: str
    score_delta_from_previous: Optional[float] = None
    weights: Dict[str, float]
    indicators: List[ReadinessIndicatorScore]
    academic_summary: ReadOnlyAcademicSummary
    missing_data_fields: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    remaining_skill_gaps: List[str] = Field(default_factory=list)
    recommendations: List[ReadinessRecommendationItem] = Field(default_factory=list)
    completed_recommendations_count: int = 0
    total_recommendations_count: int = 0
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    transparency_notice: str = READINESS_TRANSPARENCY_NOTICE
    category_definitions: List[ReadinessCategoryDefinition] = Field(default_factory=lambda: list(DEFAULT_CATEGORY_DEFINITIONS))
    usage: Optional[AIUsageMetadata] = None
    calculated_at: datetime


class ReadinessHistoryPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: int
    formula_version: str
    overall_score: float
    category: ReadinessCategory
    category_label: str
    score_delta: Optional[float] = None
    completed_recommendations_count: int = 0
    total_recommendations_count: int = 0
    remaining_skill_gaps_count: int = 0
    target_label: str
    calculated_at: datetime


class ReadinessHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_snapshots: int = 0
    latest_score: Optional[float] = None
    best_score: Optional[float] = None
    net_change: Optional[float] = None
    total_completed_recommendations: int = 0
    remaining_skill_gaps: List[str] = Field(default_factory=list)
    snapshots: List[ReadinessSnapshotResponse] = Field(default_factory=list)
    trend: List[ReadinessHistoryPoint] = Field(default_factory=list)
    transparency_notice: str = READINESS_TRANSPARENCY_NOTICE


class JobReadinessCheckRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: Optional[int] = None
    target_role: Optional[str] = Field(default=None, max_length=200)
    custom_weights: Optional[ReadinessIndicatorWeights] = None

    @model_validator(mode="after")
    def require_job_or_role(self) -> "JobReadinessCheckRequest":
        if self.job_id is None and (not self.target_role or not self.target_role.strip()):
            raise ValueError("Either job_id or target_role must be provided.")
        return self


class JobReadinessCheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: Optional[int] = None
    target_label: str
    company_name: Optional[str] = None
    # Academic Eligibility strictly separated from Preparation Readiness
    academic_eligibility_checked: bool = False
    is_academically_eligible: Optional[bool] = None
    eligibility_reasons: List[str] = Field(default_factory=list)
    eligibility_passed_criteria: List[str] = Field(default_factory=list)
    eligibility_failed_criteria: List[str] = Field(default_factory=list)
    # Skill & compatibility alignment
    skill_alignment_pct: float = Field(..., ge=0.0, le=100.0)
    deterministic_compatibility_score: Optional[float] = None
    matched_skills: List[str] = Field(default_factory=list)
    missing_mandatory_skills: List[str] = Field(default_factory=list)
    missing_preferred_skills: List[str] = Field(default_factory=list)
    # Preparation gaps
    portfolio_gaps: List[str] = Field(default_factory=list)
    interview_preparation_gaps: List[str] = Field(default_factory=list)
    readiness_score: float = Field(..., ge=0.0, le=100.0)
    readiness_category: ReadinessCategory
    readiness_category_label: str
    recommendations: List[ReadinessRecommendationItem] = Field(default_factory=list)
    missing_data_fields: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    transparency_notice: str = READINESS_TRANSPARENCY_NOTICE


# =============================================================================
# TPO Institutional Analytics Schemas
# =============================================================================


class TpoCategoryDistributionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: ReadinessCategory
    label: str
    student_count: int
    percentage: float


class TpoDepartmentReadinessStat(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    department_id: Optional[int] = None
    department_code: str
    department_name: str
    student_count: int
    average_readiness_score: float
    placement_ready_count: int
    needs_attention_count: int


class TpoBatchReadinessStat(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    graduation_year: int
    student_count: int
    average_readiness_score: float
    excellent_or_ready_pct: float


class TpoSkillCategoryStat(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_category: str
    students_with_skill_count: int
    verified_skills_count: int
    cohort_coverage_pct: float


class TpoStudentReadinessRow(BaseModel):
    """Advisory student readiness view for authorized institutional TPOs (never ordered as a hiring rank)."""
    model_config = ConfigDict(from_attributes=True)

    student_id: int
    full_name: str
    roll_number: str
    department_code: str
    department_name: str
    graduation_year: int
    cgpa: Optional[float] = None
    active_backlogs: int = 0
    readiness_score: float
    category: ReadinessCategory
    category_label: str
    verified_skills_count: int
    projects_count: int
    completed_mock_interviews: int
    has_approved_resume: bool
    missing_data_count: int
    data_completeness_note: str


class TpoReadinessAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    institution_id: int
    formula_version: str = READINESS_FORMULA_VERSION
    total_students_evaluated: int = 0
    cohort_average_readiness: float = 0.0
    placement_ready_or_above_count: int = 0
    placement_ready_or_above_pct: float = 0.0
    profiles_with_missing_data_count: int = 0
    category_distribution: List[TpoCategoryDistributionItem] = Field(default_factory=list)
    department_stats: List[TpoDepartmentReadinessStat] = Field(default_factory=list)
    batch_stats: List[TpoBatchReadinessStat] = Field(default_factory=list)
    skill_category_stats: List[TpoSkillCategoryStat] = Field(default_factory=list)
    available_departments: List[Dict[str, str]] = Field(default_factory=list)
    available_batches: List[int] = Field(default_factory=list)
    available_skill_categories: List[str] = Field(default_factory=list)
    students: List[TpoStudentReadinessRow] = Field(default_factory=list)
    transparency_notice: str = READINESS_TRANSPARENCY_NOTICE
    category_definitions: List[ReadinessCategoryDefinition] = Field(default_factory=lambda: list(DEFAULT_CATEGORY_DEFINITIONS))

