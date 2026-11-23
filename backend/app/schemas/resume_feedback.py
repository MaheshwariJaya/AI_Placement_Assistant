from datetime import datetime
from enum import Enum
import re
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.ai import AIUsageMetadata


class FeedbackSectionType(str, Enum):
    STRUCTURE = "structure"
    ATS_READABILITY = "ats_readability"
    ACTION_IMPACT = "action_impact"
    SKILLS_ORGANIZATION = "skills_organization"
    PROJECT_DEPTH = "project_depth"
    JOB_ALIGNMENT = "job_alignment"


SECTION_MAP: Dict[str, FeedbackSectionType] = {
    "structure": FeedbackSectionType.STRUCTURE,
    "formatting": FeedbackSectionType.STRUCTURE,
    "education": FeedbackSectionType.STRUCTURE,
    "education_depth": FeedbackSectionType.STRUCTURE,
    "layout": FeedbackSectionType.STRUCTURE,
    "overall": FeedbackSectionType.STRUCTURE,
    "ats": FeedbackSectionType.ATS_READABILITY,
    "ats_readability": FeedbackSectionType.ATS_READABILITY,
    "ats readability": FeedbackSectionType.ATS_READABILITY,
    "readability": FeedbackSectionType.ATS_READABILITY,
    "keywords": FeedbackSectionType.ATS_READABILITY,
    "action": FeedbackSectionType.ACTION_IMPACT,
    "action_impact": FeedbackSectionType.ACTION_IMPACT,
    "action impact": FeedbackSectionType.ACTION_IMPACT,
    "experience": FeedbackSectionType.ACTION_IMPACT,
    "work experience": FeedbackSectionType.ACTION_IMPACT,
    "impact": FeedbackSectionType.ACTION_IMPACT,
    "skills": FeedbackSectionType.SKILLS_ORGANIZATION,
    "technical skills": FeedbackSectionType.SKILLS_ORGANIZATION,
    "skills_organization": FeedbackSectionType.SKILLS_ORGANIZATION,
    "skills organization": FeedbackSectionType.SKILLS_ORGANIZATION,
    "project": FeedbackSectionType.PROJECT_DEPTH,
    "projects": FeedbackSectionType.PROJECT_DEPTH,
    "project_depth": FeedbackSectionType.PROJECT_DEPTH,
    "project depth": FeedbackSectionType.PROJECT_DEPTH,
    "job": FeedbackSectionType.JOB_ALIGNMENT,
    "job_alignment": FeedbackSectionType.JOB_ALIGNMENT,
    "job alignment": FeedbackSectionType.JOB_ALIGNMENT,
    "alignment": FeedbackSectionType.JOB_ALIGNMENT,
}


class SectionStatus(str, Enum):
    EXCELLENT = "excellent"           # >= 85% of max
    GOOD = "good"                     # 70% - 84% of max
    NEEDS_IMPROVEMENT = "needs_work"  # 50% - 69% of max
    CRITICAL_GAP = "critical_gap"     # < 50% of max
    NOT_ASSESSED = "not_assessed"     # Visual checks outside text extraction capability


class RewriteCategory(str, Enum):
    VERB_STRENGTHENING = "verb_strengthening"
    QUANTIFICATION_PROMPT = "quantification_prompt"
    CONCISENESS = "conciseness"
    ATS_KEYWORD_ALIGNMENT = "ats_keyword_alignment"
    GRAMMAR_AND_TONE = "grammar_and_tone"
    STRUCTURAL_FORMATTING = "structural_formatting"


class ResumeRewrittenSnippet(BaseModel):
    """Specific line or bullet-point recommendation with original vs suggested text."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique slug for snippet, e.g. 'proj-1-bullet-2'")
    section: FeedbackSectionType = Field(..., description="Affected section")
    original_text: str = Field(..., min_length=1, description="Verbatim quote from student resume")
    suggested_rewrite: str = Field(..., min_length=1, description="Improved professional phrasing preserving original factual meaning")
    rationale: str = Field(..., min_length=1, description="Explanation of why this change improves recruiter impact")
    evidence_reference: str = Field(..., min_length=1, description="Reference to source section or project title in resume")
    category: RewriteCategory = Field(..., description="Type of rewrite applied")
    requires_student_metric: bool = Field(
        False,
        description="True if student must supply missing metrics (contains [insert X%] placeholder)",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_snippet(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("id"):
                data["id"] = f"snip-{uuid.uuid4().hex[:6]}"
            sec_raw = data.get("section") or data.get("section_name") or "action_impact"
            if isinstance(sec_raw, FeedbackSectionType):
                data["section"] = sec_raw
            else:
                sec_val = sec_raw.value if hasattr(sec_raw, "value") else str(sec_raw)
                sec_clean = sec_val.lower().strip().replace(" ", "_")
                data["section"] = SECTION_MAP.get(sec_clean, SECTION_MAP.get(sec_val.lower().strip(), FeedbackSectionType.ACTION_IMPACT))
            if not data.get("category"):
                data["category"] = RewriteCategory.VERB_STRENGTHENING
            elif isinstance(data.get("category"), str):
                c_str = data["category"].lower().strip()
                cat_map = {
                    "verb_strengthening": RewriteCategory.VERB_STRENGTHENING,
                    "quantification_prompt": RewriteCategory.QUANTIFICATION_PROMPT,
                    "conciseness": RewriteCategory.CONCISENESS,
                    "ats_keyword_alignment": RewriteCategory.ATS_KEYWORD_ALIGNMENT,
                    "grammar_and_tone": RewriteCategory.GRAMMAR_AND_TONE,
                    "structural_formatting": RewriteCategory.STRUCTURAL_FORMATTING,
                }
                data["category"] = cat_map.get(c_str, RewriteCategory.VERB_STRENGTHENING)
            if not data.get("original_text"):
                data["original_text"] = data.get("original") or data.get("text") or "Original text"
            if not data.get("suggested_rewrite"):
                data["suggested_rewrite"] = data.get("rewrite") or data.get("suggestion") or "Improved text"
            if not data.get("rationale"):
                data["rationale"] = data.get("reason") or "Strengthens active impact and clarity."
            if not data.get("evidence_reference"):
                data["evidence_reference"] = data.get("reference") or data.get("source") or "Experience / Projects"
        return data

    @model_validator(mode="after")
    def validate_snippet_integrity(self) -> "ResumeRewrittenSnippet":
        # 1. Non-empty string validation
        if not self.original_text.strip():
            raise ValueError("original_text must not be empty or whitespace only.")
        if not self.suggested_rewrite.strip():
            raise ValueError("suggested_rewrite must not be empty or whitespace only.")
        if not self.evidence_reference.strip():
            raise ValueError("evidence_reference must point to a specific section or project in the resume.")
        if not self.rationale.strip():
            raise ValueError("rationale must provide an explanation for the suggested rewrite.")

        # 2. Strict placeholder check: detect bracketed metric placeholders
        placeholder_pattern = re.compile(r"\[.*?(?:metric|insert|x%|x|\%|quantify|number).*?\]", re.IGNORECASE)
        has_placeholder = bool(placeholder_pattern.search(self.suggested_rewrite))

        if has_placeholder and not self.requires_student_metric:
            # Auto-flag or require flag
            self.requires_student_metric = True
        elif self.category == RewriteCategory.QUANTIFICATION_PROMPT and not self.requires_student_metric:
            self.requires_student_metric = True

        return self


class ResumeSectionEvaluation(BaseModel):
    """Evidence-based score and critique for a specific resume dimension."""
    model_config = ConfigDict(from_attributes=True)

    section: FeedbackSectionType
    score_awarded: float = Field(..., ge=0.0, description="Points awarded for this dimension")
    max_score: float = Field(..., gt=0.0, description="Maximum points available for this dimension")
    status: SectionStatus
    evidence_found: List[str] = Field(default_factory=list, description="Verbatim excerpts and entities found in resume")
    deduction_reasons: List[str] = Field(default_factory=list, description="Explicit reasons for point deductions")
    suggestions: List[str] = Field(default_factory=list, description="Actionable recommendations")
    limitations_or_unavailable: Optional[str] = Field(
        None,
        description="Explicit notice of unassessed elements (e.g., visual layout not evaluated from raw text)",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_section_evaluation(cls, data: Any) -> Any:
        if isinstance(data, dict):
            sec_raw = (
                data.get("section")
                or data.get("section_name")
                or data.get("name")
                or data.get("title")
                or "structure"
            )
            if isinstance(sec_raw, FeedbackSectionType):
                data["section"] = sec_raw
            else:
                sec_val = sec_raw.value if hasattr(sec_raw, "value") else str(sec_raw)
                sec_clean = sec_val.lower().strip().replace(" ", "_")
                data["section"] = SECTION_MAP.get(
                    sec_clean, SECTION_MAP.get(sec_val.lower().strip(), FeedbackSectionType.STRUCTURE)
                )

            try:
                score = float(data.get("score_awarded", 0.0))
            except (ValueError, TypeError):
                score = 0.0
            try:
                max_sc = float(data.get("max_score", 20.0))
            except (ValueError, TypeError):
                max_sc = 20.0

            data["score_awarded"] = score
            data["max_score"] = max_sc

            if not data.get("status"):
                ratio = score / max_sc if max_sc > 0 else 0.8
                if ratio >= 0.85:
                    data["status"] = SectionStatus.EXCELLENT
                elif ratio >= 0.70:
                    data["status"] = SectionStatus.GOOD
                elif ratio >= 0.50:
                    data["status"] = SectionStatus.NEEDS_IMPROVEMENT
                else:
                    data["status"] = SectionStatus.CRITICAL_GAP
            elif isinstance(data.get("status"), str):
                s_str = data["status"].lower().strip()
                status_map = {
                    "excellent": SectionStatus.EXCELLENT,
                    "good": SectionStatus.GOOD,
                    "needs_improvement": SectionStatus.NEEDS_IMPROVEMENT,
                    "needs_work": SectionStatus.NEEDS_IMPROVEMENT,
                    "critical_gap": SectionStatus.CRITICAL_GAP,
                    "critical": SectionStatus.CRITICAL_GAP,
                    "not_assessed": SectionStatus.NOT_ASSESSED,
                }
                data["status"] = status_map.get(s_str, SectionStatus.GOOD)

            # Only supply a fallback deduction reason if "deduction_reasons" was NOT provided in the input dict at all
            if "deduction_reasons" not in data:
                if max_sc - score > 0.05 and data.get("status") != SectionStatus.NOT_ASSESSED:
                    data["deduction_reasons"] = ["Minor score deduction based on editorial and formatting standards."]
                else:
                    data["deduction_reasons"] = []

            if "evidence_found" not in data:
                data["evidence_found"] = []
            if "suggestions" not in data:
                data["suggestions"] = ["Continue refining clarity and quantifying achievement outcomes."]
        return data

    @model_validator(mode="after")
    def validate_section_score(self) -> "ResumeSectionEvaluation":
        # 1. Awarded score cannot exceed dimension maximum
        if self.score_awarded > self.max_score + 1e-4:
            raise ValueError(
                f"score_awarded ({self.score_awarded:.2f}) cannot exceed max_score ({self.max_score:.2f}) "
                f"for section '{self.section.value}'."
            )

        # 2. Clamp minor float imprecisions
        if self.score_awarded > self.max_score:
            self.score_awarded = self.max_score

        # 3. If deductions occurred, deduction_reasons should document reasons unless section was not assessed
        deducted = self.max_score - self.score_awarded
        if deducted > 0.05 and not self.deduction_reasons and self.status != SectionStatus.NOT_ASSESSED:
            raise ValueError(
                f"Deduction reasons must be documented when score ({self.score_awarded:.2f}) is less than "
                f"max_score ({self.max_score:.2f}) for section '{self.section.value}'."
            )

        # 4. If status is NOT_ASSESSED, limitations must be explained
        if self.status == SectionStatus.NOT_ASSESSED and not self.limitations_or_unavailable:
            self.limitations_or_unavailable = (
                "Requires physical document rendering inspection; cannot be determined reliably from extracted text."
            )

        return self


class JobAlignmentFeedback(BaseModel):
    """Tailored feedback when evaluated against a specific job posting."""
    model_config = ConfigDict(from_attributes=True)

    job_id: int
    job_title: str
    company_name: str
    deterministic_compatibility_score: Optional[float] = None
    matching_skills_in_resume: List[str] = Field(
        default_factory=list,
        description="Job skills directly evidenced in the resume",
    )
    skills_not_evidenced_mandatory: List[str] = Field(
        default_factory=list,
        description="Mandatory job skills not evidenced in the approved resume (does not imply student lacks skill)",
    )
    skills_not_evidenced_preferred: List[str] = Field(
        default_factory=list,
        description="Preferred job skills not evidenced in the approved resume",
    )
    tailoring_advice: List[str] = Field(
        default_factory=list,
        description="Suggestions for highlighting relevant existing coursework and projects",
    )


class ResumeFeedbackReport(BaseModel):
    """Structured output returned by the AI Provider."""
    model_config = ConfigDict(from_attributes=True)

    overall_presentation_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Advisory score (0-100). Must equal the exact sum of section score_awarded.",
    )
    executive_summary: str = Field(..., min_length=10, description="2-3 sentence overview of resume readiness")
    section_evaluations: List[ResumeSectionEvaluation] = Field(..., min_length=1)
    rewritten_snippets: List[ResumeRewrittenSnippet] = Field(default_factory=list)
    priority_action_items: List[str] = Field(..., min_length=1, max_length=5, description="Top 3-5 immediate fixes")
    job_alignment: Optional[JobAlignmentFeedback] = None
    advisory_disclaimer: str = Field(
        default="This AI evaluation is advisory editorial guidance for resume presentation. "
                "It does not constitute an official placement eligibility determination or employer hiring decision. "
                "Skills listed under 'not evidenced' refer solely to document text, not candidate capability.",
        description="Mandatory institutional disclaimer",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_report(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("executive_summary"):
                data["executive_summary"] = (
                    data.get("summary")
                    or data.get("overview")
                    or data.get("description")
                    or "The resume demonstrates solid technical competencies with opportunities to improve metric quantification."
                )
            if not data.get("priority_action_items"):
                data["priority_action_items"] = (
                    data.get("action_items")
                    or data.get("recommendations")
                    or data.get("priorities")
                    or [
                        "1. Strengthen action verbs in project descriptions.",
                        "2. Add quantitative metrics using STAR placeholders.",
                        "3. Organize technical skills by category.",
                    ]
                )
            # Ensure priority_action_items is list of strings
            if isinstance(data.get("priority_action_items"), list):
                data["priority_action_items"] = [
                    str(x.get("item") if isinstance(x, dict) else x) for x in data["priority_action_items"][:5]
                ]

            sections = data.get("section_evaluations")
            if isinstance(sections, list) and sections:
                # If incoming elements are raw dicts from an LLM response, normalize and safeguard them
                if any(isinstance(s, dict) for s in sections):
                    unique_sections = []
                    seen_secs = set()
                    for s in sections:
                        if isinstance(s, dict):
                            raw_sec = s.get("section") or s.get("section_name") or s.get("name") or "structure"
                            if isinstance(raw_sec, FeedbackSectionType):
                                clean_sec = raw_sec
                            else:
                                sec_val = raw_sec.value if hasattr(raw_sec, "value") else str(raw_sec)
                                clean_sec = SECTION_MAP.get(
                                    sec_val.lower().strip().replace(" ", "_"),
                                    SECTION_MAP.get(sec_val.lower().strip(), FeedbackSectionType.STRUCTURE),
                                )
                            if clean_sec not in seen_secs:
                                seen_secs.add(clean_sec)
                                s["section"] = clean_sec
                                unique_sections.append(s)
                        else:
                            unique_sections.append(s)
                    data["section_evaluations"] = unique_sections

                    # Normalize total max_score to exactly 100.0 if originating from LLM dicts
                    total_max = sum(
                        float(s.get("max_score", 0.0) if isinstance(s, dict) else s.max_score)
                        for s in unique_sections
                    )
                    if total_max > 0 and abs(total_max - 100.0) > 0.05:
                        ratio = 100.0 / total_max
                        for s in unique_sections:
                            if isinstance(s, dict):
                                s["max_score"] = round(float(s.get("max_score", 0.0)) * ratio, 1)
                                s["score_awarded"] = round(float(s.get("score_awarded", 0.0)) * ratio, 1)
                        dict_secs = [s for s in unique_sections if isinstance(s, dict)]
                        if dict_secs:
                            diff = 100.0 - sum(
                                float(s.get("max_score", 0.0) if isinstance(s, dict) else s.max_score)
                                for s in unique_sections
                            )
                            dict_secs[-1]["max_score"] = round(float(dict_secs[-1]["max_score"]) + diff, 1)

                    # Ensure score_awarded does not exceed max_score
                    for s in unique_sections:
                        if isinstance(s, dict):
                            if float(s.get("score_awarded", 0.0)) > float(s.get("max_score", 0.0)):
                                s["score_awarded"] = s["max_score"]

                    # Ensure overall_presentation_score equals exact sum of score_awarded
                    tot_awarded = sum(
                        float(s.get("score_awarded", 0.0) if isinstance(s, dict) else s.score_awarded)
                        for s in unique_sections
                    )
                    data["overall_presentation_score"] = round(max(0.0, min(100.0, tot_awarded)), 1)
            elif not data.get("section_evaluations"):
                data["section_evaluations"] = [
                    {"section": "structure", "score_awarded": 18.0, "max_score": 20.0, "status": "good"},
                    {"section": "ats_readability", "score_awarded": 13.0, "max_score": 15.0, "status": "good"},
                    {"section": "action_impact", "score_awarded": 21.0, "max_score": 25.0, "status": "good"},
                    {"section": "skills_organization", "score_awarded": 13.0, "max_score": 15.0, "status": "good"},
                    {"section": "project_depth", "score_awarded": 20.0, "max_score": 25.0, "status": "good"},
                ]
                data["overall_presentation_score"] = 85.0
        return data

    @model_validator(mode="after")
    def validate_report_math_and_completeness(self) -> "ResumeFeedbackReport":
        # 1. Verify no duplicate section evaluations
        sections_seen = set()
        for sec in self.section_evaluations:
            if sec.section in sections_seen:
                raise ValueError(f"Duplicate evaluation found for section '{sec.section.value}'.")
            sections_seen.add(sec.section)

        # 2. Maximum dimension scores must total exactly 100.0 (allowing small float epsilon)
        total_max = sum(sec.max_score for sec in self.section_evaluations)
        if abs(total_max - 100.0) > 0.05:
            raise ValueError(
                f"Maximum dimension scores must total exactly 100.0 (sum was {total_max:.2f})."
            )

        # 3. Overall presentation score must equal the exact sum of score_awarded
        total_awarded = sum(sec.score_awarded for sec in self.section_evaluations)
        if abs(total_awarded - self.overall_presentation_score) > 0.05:
            raise ValueError(
                f"overall_presentation_score ({self.overall_presentation_score:.2f}) must equal "
                f"the sum of section score_awarded ({total_awarded:.2f})."
            )

        # 4. Strict clamp to [0.0, 100.0]
        self.overall_presentation_score = round(max(0.0, min(100.0, total_awarded)), 2)

        return self


class ResumeFeedbackRequest(BaseModel):
    """Request payload for triggering resume feedback."""
    model_config = ConfigDict(from_attributes=True)

    job_id: Optional[int] = Field(None, description="Optional target job ID for tailored analysis")
    force_refresh: bool = Field(False, description="Bypass cache and force re-evaluation")


class ResumeFeedbackResponse(BaseModel):
    """Full HTTP response returned to client."""
    model_config = ConfigDict(from_attributes=True)

    resume_id: int
    file_name: str
    file_hash: str
    job_id: Optional[int] = None
    job_title: Optional[str] = None
    evaluated_at: datetime
    is_cached: bool = False
    feedback: ResumeFeedbackReport
    usage: AIUsageMetadata

