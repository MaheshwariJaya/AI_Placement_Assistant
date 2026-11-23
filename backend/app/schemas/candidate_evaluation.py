"""
Pydantic schemas for TASK 08: Advanced Candidate Evaluation Workspace.
Provides schemas for recruiter candidate filtering, detailed candidate dossiers,
structured multi-interviewer evaluations, candidate notes, and evidence-grounded AI summaries.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.candidate_evaluation import (
    EvaluationRecommendation,
    EvaluationStage,
    NoteCategory,
)
from app.models.placement import ApplicationStatus, InterviewMode, InterviewOutcome, InterviewStatus, TpoScreeningStatus
from app.schemas.intelligence import ScoreBreakdown


# =============================================================================
# 1. EVALUATION FORMS & INTERVIEWER FEEDBACK SCHEMAS
# =============================================================================

class CandidateEvaluationCreate(BaseModel):
    """Payload to submit a structured interview evaluation."""
    interview_id: Optional[int] = Field(None, description="Optional associated interview round ID")
    stage: EvaluationStage = Field(default=EvaluationStage.TECHNICAL, description="Interview evaluation stage")
    technical_rating: Optional[int] = Field(None, ge=1, le=5, description="1-5 rating on technical fundamentals")
    problem_solving_rating: Optional[int] = Field(None, ge=1, le=5, description="1-5 rating on problem solving capability")
    communication_rating: Optional[int] = Field(None, ge=1, le=5, description="1-5 rating on communication clarity")
    project_depth_rating: Optional[int] = Field(None, ge=1, le=5, description="1-5 rating on project ownership and depth")
    cultural_fit_rating: Optional[int] = Field(None, ge=1, le=5, description="1-5 rating on culture and teamwork")
    overall_rating: float = Field(..., ge=1.0, le=5.0, description="1.00 to 5.00 overall synthesized score")
    recommendation: EvaluationRecommendation = Field(default=EvaluationRecommendation.HOLD, description="Interviewer hiring recommendation")
    strengths: Optional[str] = Field(None, description="Observed strengths")
    weaknesses: Optional[str] = Field(None, description="Identified areas for improvement")
    written_feedback: str = Field(..., min_length=5, description="Comprehensive qualitative feedback and notes")
    criteria_ratings: Optional[Dict[str, Any]] = Field(default=None, description="Configurable key-value rating rubric")


class CandidateEvaluationUpdate(BaseModel):
    """Payload to update an existing evaluation."""
    stage: Optional[EvaluationStage] = None
    technical_rating: Optional[int] = Field(None, ge=1, le=5)
    problem_solving_rating: Optional[int] = Field(None, ge=1, le=5)
    communication_rating: Optional[int] = Field(None, ge=1, le=5)
    project_depth_rating: Optional[int] = Field(None, ge=1, le=5)
    cultural_fit_rating: Optional[int] = Field(None, ge=1, le=5)
    overall_rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    recommendation: Optional[EvaluationRecommendation] = None
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    written_feedback: Optional[str] = Field(None, min_length=5)
    criteria_ratings: Optional[Dict[str, Any]] = None


class CandidateEvaluationResponse(BaseModel):
    """Structured evaluation record returned to recruiters."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    interview_id: Optional[int] = None
    interview_round_title: Optional[str] = None
    interviewer_user_id: int
    interviewer_name: str
    stage: EvaluationStage
    technical_rating: Optional[int] = None
    problem_solving_rating: Optional[int] = None
    communication_rating: Optional[int] = None
    project_depth_rating: Optional[int] = None
    cultural_fit_rating: Optional[int] = None
    overall_rating: float
    recommendation: EvaluationRecommendation
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    written_feedback: str
    criteria_ratings: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# 2. INTERNAL CANDIDATE NOTES SCHEMAS
# =============================================================================

class CandidateNoteCreate(BaseModel):
    """Payload to create an internal recruiter note."""
    category: NoteCategory = Field(default=NoteCategory.GENERAL, description="Note classification")
    content: str = Field(..., min_length=1, description="Internal confidential note content")
    is_pinned: bool = Field(default=False, description="Pin note to top of candidate workspace")


class CandidateNoteResponse(BaseModel):
    """Confidential internal candidate note record."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    author_user_id: int
    author_name: str
    category: NoteCategory
    content: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime


# =============================================================================
# 3. ELIGIBILITY & ACADEMIC DOSSIER SCHEMAS
# =============================================================================

class EligibilityCheckCriterion(BaseModel):
    """Individual deterministic eligibility check item."""
    criterion: str
    passed: bool
    candidate_value: str
    required_value: str
    details: Optional[str] = None


class CandidateEligibilityChecklist(BaseModel):
    """Complete deterministic eligibility audit checklist."""
    is_eligible: bool
    criteria: List[EligibilityCheckCriterion]
    reasons: List[str]


class CandidateAcademicInfo(BaseModel):
    """Official verified institutional academic records."""
    cgpa: float
    tenth_percentage: Optional[float] = None
    twelfth_percentage: Optional[float] = None
    active_backlogs: int
    total_backlogs: int
    is_placement_ready: bool


class CandidateSkillItem(BaseModel):
    """Student skill entry."""
    skill_name: str
    category: str
    proficiency_level: str
    is_verified: bool


class CandidateProjectItem(BaseModel):
    """Student project record."""
    title: str
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    repo_url: Optional[str] = None
    demo_url: Optional[str] = None


class CandidateExperienceItem(BaseModel):
    """Student internship / work experience entry."""
    job_title: str
    company_name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    description: Optional[str] = None


class CandidateCertificationItem(BaseModel):
    """Student certification record."""
    name: str
    issuing_organization: str
    issue_date: Optional[str] = None
    credential_url: Optional[str] = None


class CandidateResumeSummary(BaseModel):
    """Student resume metadata and parsed details."""
    resume_id: int
    file_name: str
    file_size_bytes: int
    file_type: str
    parsing_status: str
    resume_score: Optional[float] = None
    download_url: str


class CandidateActivityTimelineItem(BaseModel):
    """Chronological event in the candidate's recruitment journey."""
    id: str
    activity_type: str
    timestamp: datetime
    actor_name: str
    title: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# =============================================================================
# 4. AI-ASSISTED CANDIDATE SUMMARY SCHEMAS (EVIDENCE-GROUNDED)
# =============================================================================

class CandidateAISummary(BaseModel):
    """
    Evidence-grounded candidate evaluation synthesis generated by AI.
    Strictly separates verified facts, deterministic calculated metrics, and synthesized observations.
    """
    candidate_id: int
    candidate_name: str
    verified_facts: Dict[str, Any]
    calculated_metrics: Dict[str, Any]
    ai_observations: Dict[str, Any]
    safety_disclaimer: str
    generated_at: datetime


# =============================================================================
# 5. CANDIDATE WORKSPACE DETAIL & PIPELINE LIST SCHEMAS
# =============================================================================

class CandidateWorkspaceDetailResponse(BaseModel):
    """Complete candidate dossier for the recruiter evaluation workspace."""
    application_id: int
    job_id: int
    job_title: str
    company_id: int
    company_name: str
    drive_id: Optional[int] = None
    drive_name: Optional[str] = None
    current_status: ApplicationStatus
    tpo_screening_status: TpoScreeningStatus
    tpo_screened_at: Optional[datetime] = None
    tpo_screened_by_name: Optional[str] = None
    tpo_feedback: Optional[str] = None
    applied_at: datetime
    recruiter_decision_at: Optional[datetime] = None
    recruiter_feedback_notes: Optional[str] = None
    compatibility_score: float
    score_breakdown: ScoreBreakdown
    matched_skills: List[str]
    missing_mandatory_skills: List[str]
    recommended_skills: List[str]
    eligibility_checklist: CandidateEligibilityChecklist
    profile: Dict[str, Any]
    academics: CandidateAcademicInfo
    skills: List[CandidateSkillItem]
    projects: List[CandidateProjectItem]
    experiences: List[CandidateExperienceItem]
    certifications: List[CandidateCertificationItem]
    resume: Optional[CandidateResumeSummary] = None
    interviews: List[Dict[str, Any]] = Field(default_factory=list)
    evaluations: List[CandidateEvaluationResponse] = Field(default_factory=list)
    notes: List[CandidateNoteResponse] = Field(default_factory=list)
    timeline: List[CandidateActivityTimelineItem] = Field(default_factory=list)
    ai_summary: Optional[CandidateAISummary] = None


class CandidateFilterParams(BaseModel):
    """Recruiter candidate filtering query parameters."""
    job_id: Optional[int] = None
    department: Optional[str] = None
    graduation_year: Optional[int] = None
    eligibility: Optional[str] = Field(None, description="all | eligible_only | ineligible_only")
    min_compatibility_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    skill: Optional[str] = None
    min_experience_months: Optional[int] = None
    status: Optional[ApplicationStatus] = None
    search: Optional[str] = None
    skip: int = 0
    limit: int = 50


class CandidateListItem(BaseModel):
    """High-level summary card for candidates in recruiter pipeline."""
    application_id: int
    job_id: int
    job_title: str
    student_id: int
    student_name: str
    roll_number: str
    department: str
    graduation_year: int
    cgpa: float
    compatibility_score: float
    is_eligible: bool
    current_status: ApplicationStatus
    tpo_screening_status: TpoScreeningStatus
    applied_at: datetime
    interviews_count: int
    evaluations_count: int
    average_rating: Optional[float] = None
    latest_recommendation: Optional[EvaluationRecommendation] = None


class CandidateListResponse(BaseModel):
    """Paginated recruiter candidate pipeline list."""
    items: List[CandidateListItem]
    total: int
    skip: int
    limit: int
    available_jobs: List[Dict[str, Any]] = Field(default_factory=list)
    available_departments: List[str] = Field(default_factory=list)


class CandidateStatusTransitionRequest(BaseModel):
    """Human-documented recruitment stage decisioning."""
    to_status: ApplicationStatus = Field(..., description="Target lifecycle state")
    decision_notes: str = Field(..., min_length=3, description="Documented human approval / decision notes")
    offer_package_lpa: Optional[float] = Field(None, ge=0.0, description="Offered CTC package in LPA")
    offer_deadline_at: Optional[datetime] = Field(None, description="Official response deadline for extended offer")
    offer_notes: Optional[str] = Field(None, description="Student-visible offer summary terms")

