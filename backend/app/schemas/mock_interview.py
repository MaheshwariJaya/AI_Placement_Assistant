"""Pydantic schemas for AI Mock Interview & Assessment Studio."""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.mock_interview import (
    MockInterviewCategory,
    MockInterviewDifficulty,
    MockInterviewStatus,
)
from app.schemas.ai import AIUsageMetadata


ADVISORY_MOCK_INTERVIEW_DISCLAIMER = (
    "Advisory AI Practice Feedback Only: Mock interview scores, follow-up questions, and study "
    "recommendations are strictly for self-paced preparation and do not alter your verified academic "
    "records, campus eligibility cutoffs, or official recruiter hiring decisions."
)


# =============================================================================
# 1. Request Schemas
# =============================================================================

class MockInterviewCreateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: MockInterviewCategory = Field(
        ...,
        description="Interview type: technical, hr, behavioral, aptitude, or project_based",
    )
    difficulty: MockInterviewDifficulty = Field(
        default=MockInterviewDifficulty.INTERMEDIATE,
        description="Difficulty level: beginner, intermediate, or advanced",
    )
    question_format: Literal["conversational", "mcq"] = Field(
        default="conversational",
        description="Format: 'conversational' (interactive AI interview) or 'mcq' (timed objective screening test)",
    )
    question_count: int = Field(
        default=5,
        ge=3,
        le=50,
        description="Number of initial base questions (3 to 50)",
    )
    job_id: Optional[int] = Field(
        default=None,
        description="Optional published job posting ID to tailor questions against",
    )
    target_role: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional target role title (used if job_id is omitted or to supplement focus)",
    )
    subject_focus: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional academic core subject focus (e.g., any of the 40 CSE subjects, or branch-specific core subject)",
    )
    time_limit_minutes: Optional[int] = Field(
        default=20,
        ge=5,
        le=180,
        description="Optional countdown timer target in minutes (e.g. 30, 45, 60)",
    )
    include_followups: bool = Field(
        default=True,
        description="Whether the AI interviewer may inject targeted follow-up questions",
    )

    @field_validator("target_role")
    @classmethod
    def clean_target_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = v.strip()
        return cleaned if cleaned else None


class MockInterviewAnswerSubmitRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: int = Field(..., ge=1)
    answer_text: Optional[str] = Field(default=None, max_length=6000)
    selected_option_key: Optional[str] = Field(default=None, max_length=10)
    input_mode: Literal["text", "voice"] = Field(default="text")
    response_time_seconds: int = Field(default=0, ge=0, le=7200)
    elapsed_seconds: Optional[int] = Field(default=None, ge=0, le=18000)

    @model_validator(mode="after")
    def validate_answer(self) -> "MockInterviewAnswerSubmitRequest":
        if self.selected_option_key:
            self.selected_option_key = self.selected_option_key.strip().upper()
            if not self.answer_text or not self.answer_text.strip():
                self.answer_text = f"Option {self.selected_option_key}"
        elif not self.answer_text or not self.answer_text.strip():
            raise ValueError("Answer text or selected option key cannot be blank.")
        else:
            self.answer_text = self.answer_text.strip()
        return self


class MockInterviewTimerSyncRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    elapsed_seconds: int = Field(..., ge=0, le=18000)


# =============================================================================
# 2. AI Provider Structured Output Schemas
# =============================================================================

class GeneratedMockQuestion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic: str = Field(default="Technical", min_length=2, max_length=150)
    question_text: str = Field(..., min_length=5, max_length=1500)
    expected_key_points: List[str] = Field(default_factory=list, max_length=12)
    model_answer: str = Field(default="Evaluate reasoning, foundational principles, and technical accuracy.", min_length=5, max_length=4000)
    difficulty_hint: str = Field(default="intermediate", max_length=30)

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        import re
        if isinstance(data, str):
            q_text = data.strip() or "Explain this core concept."
            if len(q_text) < 5:
                q_text = f"Explain the fundamental principles of {q_text}."
            return {
                "topic": "Core Fundamentals",
                "question_text": q_text[:1500],
                "expected_key_points": [],
                "model_answer": "Evaluate reasoning, foundational principles, and technical accuracy.",
                "difficulty_hint": "intermediate",
            }
        if isinstance(data, dict):
            d = dict(data)
            q_text = str(d.get("question_text") or d.get("question") or d.get("text") or d.get("prompt") or d.get("title") or "Explain this core concept.").strip()
            if len(q_text) < 5:
                q_text = f"Explain the fundamental principles and practical applications of {q_text}."
            d["question_text"] = q_text[:1500]

            m_ans = str(d.get("model_answer") or d.get("answer") or d.get("solution") or d.get("explanation") or "Evaluate reasoning, foundational principles, and technical accuracy.").strip()
            if len(m_ans) < 5:
                m_ans = "Evaluate candidate reasoning, foundational principles, and domain accuracy."
            d["model_answer"] = m_ans[:4000]

            topic = str(d.get("topic") or d.get("category") or d.get("subject") or "Core Fundamentals").strip()
            if len(topic) < 2:
                topic = "Technical Fundamentals"
            d["topic"] = topic[:150]

            raw_pts = d.get("expected_key_points") or d.get("key_points") or d.get("points") or []
            if isinstance(raw_pts, str):
                pts = [p.strip() for p in re.split(r"[\n,;]+", raw_pts) if p.strip()]
            elif isinstance(raw_pts, (list, tuple)):
                pts = [str(p).strip() for p in raw_pts if str(p).strip()]
            else:
                pts = []
            d["expected_key_points"] = pts[:12]

            d["difficulty_hint"] = str(d.get("difficulty_hint") or d.get("difficulty") or "intermediate")[:30]
            return d
        return data


class GeneratedInterviewPlan(BaseModel):
    """Structured AI response for initial interview question set."""
    model_config = ConfigDict(from_attributes=True)

    questions: List[GeneratedMockQuestion] = Field(..., min_length=1, max_length=100)

    @model_validator(mode="before")
    @classmethod
    def handle_raw_list_or_wrappers(cls, data: Any) -> Any:
        if isinstance(data, list):
            return {"questions": data}
        if isinstance(data, dict):
            # If questions key is missing or not a list, search for common alternatives
            if "questions" not in data or not isinstance(data.get("questions"), list):
                for alt_key in ("items", "results", "data", "records", "interview_questions", "question_list"):
                    if alt_key in data and isinstance(data[alt_key], list):
                        data["questions"] = data[alt_key]
                        break
        return data

    @model_validator(mode="after")
    def validate_non_empty(self) -> "GeneratedInterviewPlan":
        if not self.questions:
            raise ValueError("AI provider must generate at least one interview question.")
        return self


class FollowUpDecisionAIOutput(BaseModel):
    """Structured AI decision on whether to ask a follow-up after a candidate answer."""
    model_config = ConfigDict(from_attributes=True)

    should_ask_followup: bool = False
    followup_question: Optional[GeneratedMockQuestion] = None
    rationale: Optional[str] = None

    @model_validator(mode="after")
    def validate_consistency(self) -> "FollowUpDecisionAIOutput":
        if self.should_ask_followup and self.followup_question is None:
            self.should_ask_followup = False
        return self


class CriteriaBreakdownScores(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    technical_correctness: float = Field(..., ge=0.0, le=100.0)
    conceptual_understanding: float = Field(..., ge=0.0, le=100.0)
    problem_solving_approach: float = Field(..., ge=0.0, le=100.0)
    communication_clarity: float = Field(..., ge=0.0, le=100.0)
    answer_structure: float = Field(..., ge=0.0, le=100.0)
    relevance: float = Field(..., ge=0.0, le=100.0)
    project_knowledge: Optional[float] = Field(default=None, ge=0.0, le=100.0)


class QuestionEvaluationAIItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_order: int = Field(..., ge=1)
    score: float = Field(..., ge=0.0, le=100.0)
    criteria_scores: CriteriaBreakdownScores
    feedback: str = Field(..., min_length=5)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    improvement_tip: str = Field(..., min_length=3)
    model_answer: str = Field(..., min_length=5)


class MockInterviewEvaluationAIOutput(BaseModel):
    """Structured AI assessment for a completed mock interview."""
    model_config = ConfigDict(from_attributes=True)

    overall_score: float = Field(..., ge=0.0, le=100.0)
    criteria_scores: CriteriaBreakdownScores
    question_evaluations: List[QuestionEvaluationAIItem] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    suggested_improvements: List[str] = Field(default_factory=list)
    recommended_topics: List[str] = Field(default_factory=list)
    executive_summary: str = Field(..., min_length=10)
    advisory_disclaimer: str = Field(default=ADVISORY_MOCK_INTERVIEW_DISCLAIMER)


# =============================================================================
# 3. API Response Schemas
# =============================================================================

class MockInterviewAnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    answer_text: str
    selected_option_key: Optional[str] = None
    input_mode: str
    response_time_seconds: int
    submitted_at: datetime


class MockInterviewQuestionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_order: int
    is_followup: bool
    parent_question_id: Optional[int] = None
    category: MockInterviewCategory
    topic: str
    question_text: str
    difficulty_hint: str
    question_type: str = "open_ended"
    options: Optional[List[Dict[str, Any]]] = None
    selected_option_key: Optional[str] = None
    # Spoiler-protected during active sessions; populated on completed/reviewed questions
    expected_key_points: Optional[List[str]] = None
    model_answer: Optional[str] = None
    correct_option_key: Optional[str] = None
    answer: Optional[MockInterviewAnswerResponse] = None


class MockInterviewQuestionEvaluationDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: Optional[int] = None
    question_order: int
    question_text: Optional[str] = None
    topic: Optional[str] = None
    is_followup: bool = False
    student_answer: Optional[str] = None
    selected_option_key: Optional[str] = None
    correct_option_key: Optional[str] = None
    is_correct: Optional[bool] = None
    score: float
    criteria_scores: CriteriaBreakdownScores
    feedback: str
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    improvement_tip: str
    model_answer: str


class MockInterviewEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    overall_score: float
    criteria_scores: CriteriaBreakdownScores
    question_evaluations: List[MockInterviewQuestionEvaluationDetail] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    suggested_improvements: List[str] = Field(default_factory=list)
    recommended_topics: List[str] = Field(default_factory=list)
    executive_summary: str
    advisory_disclaimer: str
    evaluated_at: datetime


class MockInterviewSessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    job_id: Optional[int] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    target_role: Optional[str] = None
    category: MockInterviewCategory
    difficulty: MockInterviewDifficulty
    question_format: str = "conversational"
    status: MockInterviewStatus
    question_count: int
    total_questions_generated: int = 0
    answered_count: int = 0
    include_followups: bool
    time_limit_minutes: Optional[int] = None
    elapsed_seconds: int
    current_question_order: int
    overall_score: Optional[float] = None
    score_delta_from_previous: Optional[float] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    started_at: datetime
    paused_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class MockInterviewSessionDetail(MockInterviewSessionSummary):
    model_config = ConfigDict(from_attributes=True)

    context_snapshot: Optional[Dict[str, Any]] = None
    questions: List[MockInterviewQuestionView] = Field(default_factory=list)
    current_question: Optional[MockInterviewQuestionView] = None
    evaluation: Optional[MockInterviewEvaluationResponse] = None
    usage: Optional[AIUsageMetadata] = None


class SubmitMockAnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session: MockInterviewSessionDetail
    submitted_answer: MockInterviewAnswerResponse
    followup_generated: bool = False
    followup_rationale: Optional[str] = None
    next_question: Optional[MockInterviewQuestionView] = None
    ready_to_complete: bool = False


class MockInterviewTrendPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: int
    attempt_number: int
    category: MockInterviewCategory
    difficulty: MockInterviewDifficulty
    overall_score: float
    completed_at: datetime
    target_label: str


class MockInterviewCategoryStat(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: MockInterviewCategory
    attempts: int
    average_score: float
    best_score: float
    latest_score: float


class MockInterviewAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_sessions: int = 0
    completed_sessions: int = 0
    in_progress_or_paused_sessions: int = 0
    average_score: Optional[float] = None
    best_score: Optional[float] = None
    latest_score: Optional[float] = None
    improvement_delta: Optional[float] = None
    average_criteria: Optional[CriteriaBreakdownScores] = None
    category_breakdown: List[MockInterviewCategoryStat] = Field(default_factory=list)
    score_trend: List[MockInterviewTrendPoint] = Field(default_factory=list)
    areas_requiring_improvement: List[str] = Field(default_factory=list)
    top_recommended_topics: List[str] = Field(default_factory=list)
    advisory_disclaimer: str = ADVISORY_MOCK_INTERVIEW_DISCLAIMER


class MockInterviewTargetJob(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company_name: str
    employment_type: str
    work_mode: str
    location: str
    compatibility_score: Optional[float] = None
    is_eligible: Optional[bool] = None

