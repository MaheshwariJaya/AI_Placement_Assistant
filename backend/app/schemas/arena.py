"""Pydantic schemas for Placement Preparation Arena."""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.arena import (
    ArenaAssessmentMode,
    ArenaAttemptStatus,
    ArenaCategory,
    ArenaContentSource,
    ArenaDifficulty,
    ArenaQuestionType,
)


class ArenaCategorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: ArenaCategory
    label: str
    description: str
    total_questions: int = 0
    mcq_count: int = 0
    coding_count: int = 0
    behavioral_count: int = 0
    easy_count: int = 0
    medium_count: int = 0
    hard_count: int = 0
    attempted_questions: int = 0
    accuracy_pct: float = 0.0
    avg_solving_seconds: float = 0.0
    proficiency_label: str = "Not Started"
    track_type: str = Field(default="common", description="common | branch_core | career_elective")
    branch_name: Optional[str] = None
    is_recommended_for_student: bool = True


class ArenaOptionItem(BaseModel):
    key: str
    text: str


class ArenaSampleTestCase(BaseModel):
    stdin: str
    expected_stdout: str


class ArenaQuestionPublicView(BaseModel):
    """Student-facing question payload BEFORE submission (never exposes correct option, hidden tests, or explanation)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    prompt_text: str
    category: ArenaCategory
    difficulty: ArenaDifficulty
    question_type: ArenaQuestionType
    content_source: ArenaContentSource
    company_tag: Optional[str] = None
    provenance_notice: str
    role_tags: List[str] = Field(default_factory=list)
    options: List[ArenaOptionItem] = Field(default_factory=list)
    starter_code: Dict[str, str] = Field(default_factory=dict)
    sample_test_cases: List[ArenaSampleTestCase] = Field(default_factory=list)
    expected_time_seconds: int
    max_marks: int
    institution_id: Optional[int] = None


class ArenaQuestionReviewView(ArenaQuestionPublicView):
    """Post-submission review payload unlocking correct answer, explanation, and sample solution."""
    correct_option_key: Optional[str] = None
    explanation_text: str
    sample_solution_text: Optional[str] = None


class ArenaAssessmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    mode: ArenaAssessmentMode
    category: Optional[ArenaCategory] = None
    difficulty: ArenaDifficulty
    company_name_style: Optional[str] = None
    provenance_notice: str
    duration_minutes: int
    question_count: int
    passing_percentage: float
    institution_id: Optional[int] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    target_graduation_year: Optional[int] = None
    is_published: bool
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class ArenaStartAttemptRequest(BaseModel):
    assessment_id: Optional[int] = None
    mode: ArenaAssessmentMode = ArenaAssessmentMode.TOPIC_PRACTICE
    category: Optional[ArenaCategory] = None
    difficulty: Optional[ArenaDifficulty] = None
    company_name_style: Optional[str] = None
    question_count: int = Field(default=5, ge=1, le=30)
    time_limit_minutes: Optional[int] = Field(default=None, ge=1, le=180)
    title: Optional[str] = Field(default=None, max_length=255)


class SandboxTestCaseResult(BaseModel):
    test_index: int
    is_sample: bool
    passed: bool
    stdin: Optional[str] = None
    expected_stdout: Optional[str] = None
    actual_stdout: str = ""
    stderr: str = ""
    runtime_ms: int = 0
    status: Literal[
        "passed",
        "wrong_answer",
        "runtime_error",
        "time_limit_exceeded",
        "memory_limit_exceeded",
        "security_violation",
        "compile_error",
        "runtime_unavailable",
    ]


class SandboxRunResponse(BaseModel):
    language: str
    sandbox_provider: str
    isolated_execution: bool = True
    all_passed: bool
    passed_count: int
    total_count: int
    compile_error: Optional[str] = None
    security_violation: Optional[str] = None
    custom_stdout: Optional[str] = None
    custom_stderr: Optional[str] = None
    runtime_ms: int = 0
    test_results: List[SandboxTestCaseResult] = Field(default_factory=list)


class ArenaRunCodeRequest(BaseModel):
    question_id: int
    language: Literal["python", "javascript", "java"]
    source_code: str = Field(..., min_length=1, max_length=25000)
    custom_stdin: Optional[str] = Field(default=None, max_length=5000)


class ArenaSubmitAnswerRequest(BaseModel):
    question_id: int
    selected_option_key: Optional[str] = Field(default=None, max_length=16)
    submitted_code: Optional[str] = Field(default=None, max_length=25000)
    code_language: Optional[Literal["python", "javascript", "java"]] = None
    behavioral_response: Optional[str] = Field(default=None, max_length=8000)
    time_spent_seconds: int = Field(default=0, ge=0, le=7200)


class ArenaAttemptAnswerView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    question_order: int
    selected_option_key: Optional[str] = None
    submitted_code: Optional[str] = None
    code_language: Optional[str] = None
    behavioral_response: Optional[str] = None
    is_correct: bool
    score_awarded: float
    time_spent_seconds: int
    execution_result: Optional[SandboxRunResponse] = None
    ai_feedback: Optional[Dict[str, Any]] = None
    answered_at: datetime


class ArenaQuestionSlot(BaseModel):
    question_order: int
    answered: bool
    question: ArenaQuestionPublicView | ArenaQuestionReviewView
    answer: Optional[ArenaAttemptAnswerView] = None


class ArenaAttemptSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assessment_id: Optional[int] = None
    title: str
    mode: ArenaAssessmentMode
    category: Optional[ArenaCategory] = None
    difficulty: Optional[ArenaDifficulty] = None
    company_name_style: Optional[str] = None
    status: ArenaAttemptStatus
    time_limit_seconds: Optional[int] = None
    started_at: datetime
    expires_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    elapsed_seconds: int
    total_questions: int
    attempted_count: int
    correct_count: int
    accuracy_pct: float
    score_pct: float


class ArenaAttemptDetail(ArenaAttemptSummary):
    provenance_notice: str
    questions: List[ArenaQuestionSlot] = Field(default_factory=list)


class ArenaSubmitAttemptRequest(BaseModel):
    elapsed_seconds: Optional[int] = Field(default=None, ge=0, le=20000)


class ArenaSubmitAnswerResponse(BaseModel):
    attempt: ArenaAttemptSummary
    answer: ArenaAttemptAnswerView
    immediate_review_unlocked: bool
    correct_option_key: Optional[str] = None
    explanation_text: Optional[str] = None
    sample_solution_text: Optional[str] = None


class ArenaTopicProficiencyItem(BaseModel):
    category: ArenaCategory
    label: str
    questions_attempted: int
    correct_count: int
    incorrect_count: int
    accuracy_pct: float
    avg_solving_seconds: float
    proficiency_band: str


class ArenaTrendPoint(BaseModel):
    attempt_id: int
    title: str
    mode: ArenaAssessmentMode
    submitted_at: datetime
    score_pct: float
    accuracy_pct: float
    questions_attempted: int


class ArenaPerformanceAnalytics(BaseModel):
    total_attempts: int
    completed_attempts: int
    total_questions_attempted: int
    total_correct: int
    total_incorrect: int
    overall_accuracy_pct: float
    avg_solving_time_seconds: float
    coding_problems_solved: int
    topic_proficiency: List[ArenaTopicProficiencyItem] = Field(default_factory=list)
    recent_attempts: List[ArenaAttemptSummary] = Field(default_factory=list)
    improvement_trend: List[ArenaTrendPoint] = Field(default_factory=list)
    advisory_note: str


class ArenaRecommendedExercise(BaseModel):
    recommendation_id: str
    title: str
    reason: str
    source_signal: Literal["skill_gap", "weak_category", "target_job", "career_roadmap"]
    category: ArenaCategory
    category_label: str
    difficulty: ArenaDifficulty
    suggested_question_ids: List[int] = Field(default_factory=list)
    target_role: Optional[str] = None


class ArenaPersonalizedPracticeResponse(BaseModel):
    target_roles_considered: List[str] = Field(default_factory=list)
    missing_skills_detected: List[str] = Field(default_factory=list)
    weak_categories: List[ArenaCategory] = Field(default_factory=list)
    recommendations: List[ArenaRecommendedExercise] = Field(default_factory=list)
    ai_study_tip: Optional[str] = None
    advisory_notice: str


class ArenaUserPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    leaderboard_opt_in: bool
    anonymize_name: bool
    preferred_language: str
    privacy_notice: str


class ArenaUserPreferenceUpdate(BaseModel):
    leaderboard_opt_in: Optional[bool] = None
    anonymize_name: Optional[bool] = None
    preferred_language: Optional[Literal["python", "javascript", "java"]] = None


class ArenaLeaderboardEntry(BaseModel):
    rank: int
    display_name: str
    is_current_user: bool = False
    is_anonymized: bool = True
    department_name: Optional[str] = None
    graduation_year: Optional[int] = None
    questions_attempted: int
    accuracy_pct: float
    avg_score_pct: float
    completed_attempts: int


class ArenaLeaderboardResponse(BaseModel):
    scope: Literal["department", "batch", "institution"]
    department_name: Optional[str] = None
    graduation_year: Optional[int] = None
    viewer_opted_in: bool
    total_opted_in_participants: int
    privacy_guarantee: str
    entries: List[ArenaLeaderboardEntry] = Field(default_factory=list)


class ArenaTpoQuestionCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    prompt_text: str = Field(..., min_length=10, max_length=8000)
    category: ArenaCategory
    difficulty: ArenaDifficulty = ArenaDifficulty.MEDIUM
    question_type: ArenaQuestionType = ArenaQuestionType.MCQ
    role_tags: List[str] = Field(default_factory=list)
    options: List[ArenaOptionItem] = Field(default_factory=list)
    correct_option_key: Optional[str] = Field(default=None, max_length=16)
    starter_code: Optional[Dict[str, str]] = None
    test_cases: Optional[List[Dict[str, Any]]] = None
    explanation_text: str = Field(..., min_length=5, max_length=6000)
    sample_solution_text: Optional[str] = Field(default=None, max_length=6000)
    expected_time_seconds: int = Field(default=90, ge=10, le=7200)
    max_marks: int = Field(default=10, ge=1, le=100)
    institution_id: Optional[int] = None


class ArenaTpoAssessmentCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=5, max_length=3000)
    category: Optional[ArenaCategory] = None
    difficulty: ArenaDifficulty = ArenaDifficulty.MEDIUM
    duration_minutes: int = Field(default=30, ge=1, le=180)
    question_ids: List[int] = Field(..., min_length=1, max_length=50)
    passing_percentage: float = Field(default=60.0, ge=0.0, le=100.0)
    department_id: Optional[int] = None
    target_graduation_year: Optional[int] = Field(default=None, ge=2020, le=2035)
    is_published: bool = True
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    institution_id: Optional[int] = None


class ArenaTpoAssessmentAnalyticsItem(BaseModel):
    assessment_id: int
    title: str
    category: Optional[ArenaCategory] = None
    difficulty: ArenaDifficulty
    is_published: bool
    department_name: Optional[str] = None
    target_graduation_year: Optional[int] = None
    total_attempts: int
    submitted_attempts: int
    avg_score_pct: float
    avg_accuracy_pct: float
    pass_rate_pct: float


class ArenaTpoAnalyticsResponse(BaseModel):
    institution_id: int
    total_published_assessments: int
    total_institutional_questions: int
    participating_students: int
    total_submitted_attempts: int
    institution_avg_score_pct: float
    institution_avg_accuracy_pct: float
    category_performance: List[ArenaTopicProficiencyItem] = Field(default_factory=list)
    assessment_breakdown: List[ArenaTpoAssessmentAnalyticsItem] = Field(default_factory=list)


class ArenaStudentPerformanceItem(BaseModel):
    student_id: int
    user_id: int
    full_name: str
    roll_number: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    graduation_year: Optional[int] = None
    cgpa: Optional[float] = None
    total_attempts: int = 0
    completed_attempts: int = 0
    questions_attempted: int = 0
    questions_correct: int = 0
    overall_accuracy_pct: float = 0.0
    avg_score_pct: float = 0.0
    top_category: Optional[str] = None
    weakest_category: Optional[str] = None
    last_active_at: Optional[datetime] = None
    latest_attempt_title: Optional[str] = None


class ArenaTpoStudentRosterResponse(BaseModel):
    institution_id: int
    total_students: int
    participating_students: int
    average_accuracy_pct: float
    students: List[ArenaStudentPerformanceItem] = Field(default_factory=list)

