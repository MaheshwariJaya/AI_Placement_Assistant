import asyncio
import hashlib
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.errors import AppError, AuthorizationException, NotFoundError
from app.models.resume import Resume
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from app.schemas.resume import (
    ResumeStructuredData,
    PersonalInfo,
    EducationItem,
    SkillItem,
    ProjectItem,
    ExperienceItem,
    CertificationItem,
    ResumeSyncRequest,
)
from app.services.ai_provider import (
    AIServiceError,
    AIConfigError,
    AIRateLimitError,
    AITimeoutError,
    GeminiAIProvider,
    OpenAIProvider,
    MockAIProvider,
    get_ai_provider,
)
from app.services.resume_cache import (
    extraction_cache,
    compute_extraction_cache_key,
    EXTRACTION_SCHEMA_VERSION,
    EXTRACTION_PROMPT_VERSION,
)
from app.services.resume_extractor import (
    run_resume_extraction_pipeline,
    sync_approved_resume_entities,
)
from app.services.evidence_validator import validate_and_sanitize_resume_data


@pytest.fixture(autouse=True)
def clear_cache_between_tests():
    """Ensure in-memory extraction cache is clean before every test."""
    extraction_cache.clear()
    yield
    extraction_cache.clear()


def _create_mock_resume_file(tmp_path: Path, content: str = "Candidate Resume") -> Path:
    """Helper to create a temporary text/pdf placeholder file."""
    fpath = tmp_path / "test_resume.pdf"
    fpath.write_text(content, encoding="utf-8")
    return fpath


# =============================================================================
# 1. END-TO-END PIPELINE WITH MOCK PROVIDER
# =============================================================================

@pytest.mark.asyncio
async def test_pipeline_mock_provider_end_to_end(tmp_path):
    """Verify default mock provider performs offline extraction with caching."""
    sample_text = (
        "Aditi Sharma\n"
        "aditi.sharma@example.com\n"
        "B.Tech in Computer Science, 2020 - 2024\n"
        "Apex Institute of Technology\n"
        "Skills: Python, FastAPI, PostgreSQL, React\n"
        "Projects\n"
        "Placement Portal: Web platform built with Python and FastAPI\n"
    )
    fpath = _create_mock_resume_file(tmp_path, sample_text)
    file_hash = hashlib.sha256(sample_text.encode("utf-8")).hexdigest()

    resume = Resume(
        id=101,
        student_id=5,
        file_name="aditi_resume.pdf",
        file_path=str(fpath),
        file_type="pdf",
        file_size_bytes=len(sample_text),
        file_hash=file_hash,
        parsing_status="uploaded",
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = resume
    mock_db.execute = AsyncMock(return_value=mock_res)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    with patch("app.services.resume_extractor.extract_document_text", return_value=sample_text), \
         patch("app.services.ai_provider.settings.AI_PROVIDER", "mock"):
        result = await run_resume_extraction_pipeline(resume_id=101, db=mock_db)

    assert result.parsing_status == "review_required"
    assert result.parsed_entities_json is not None
    assert result.parsed_entities_json["extraction_method"] == "mock_rule_based"
    assert "_cache_meta" in result.parsed_entities_json
    assert result.parsed_entities_json["_cache_meta"]["provider"] == "mock"
    assert result.parsed_entities_json["_cache_meta"]["file_hash"] == file_hash

    # Verify cache entry was stored
    cache_key = result.parsed_entities_json["_cache_meta"]["cache_key"]
    assert extraction_cache.get(cache_key) is not None


# =============================================================================
# 2. END-TO-END PIPELINE WITH GEMINI PROVIDER (MOCKED HTTP)
# =============================================================================

@pytest.mark.asyncio
async def test_pipeline_gemini_provider_end_to_end(tmp_path):
    """Verify Gemini AI provider is called, parses response, sanitizes, and caches."""
    sample_text = (
        "Rahul Verma\n"
        "rahul@example.com\n"
        "Skills: Python, Django, Docker\n"
        "Education: B.Tech Computer Science, Apex University\n"
    )
    fpath = _create_mock_resume_file(tmp_path, sample_text)
    file_hash = hashlib.sha256(sample_text.encode("utf-8")).hexdigest()

    resume = Resume(
        id=102,
        student_id=5,
        file_name="rahul_resume.pdf",
        file_path=str(fpath),
        file_type="pdf",
        file_size_bytes=len(sample_text),
        file_hash=file_hash,
        parsing_status="uploaded",
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = resume
    mock_db.execute = AsyncMock(return_value=mock_res)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    gemini_output_json = {
        "personal_info": {
            "full_name": "Rahul Verma",
            "email": "rahul@example.com",
            "evidence": "Rahul Verma\nrahul@example.com",
            "confidence": "high",
        },
        "education": [
            {
                "institution": "Apex University",
                "degree": "B.Tech Computer Science",
                "evidence": "Education: B.Tech Computer Science, Apex University",
                "confidence": "high",
            }
        ],
        "skills": [
            {"skill_name": "Python", "category": "technical", "proficiency_level": "advanced", "evidence": "Skills: Python", "confidence": "high"},
            {"skill_name": "Django", "category": "framework", "proficiency_level": "intermediate", "evidence": "Skills: Django", "confidence": "high"},
            {"skill_name": "Docker", "category": "tool", "proficiency_level": "intermediate", "evidence": "Skills: Docker", "confidence": "high"},
        ],
        "projects": [],
        "experiences": [],
        "certifications": [],
    }

    mock_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": json.dumps(gemini_output_json)}],
                    "role": "model",
                },
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {"promptTokenCount": 120, "candidatesTokenCount": 85, "totalTokenCount": 205},
    }

    recorded_headers = {}

    def handle_gemini(request: httpx.Request) -> httpx.Response:
        nonlocal recorded_headers
        recorded_headers = dict(request.headers)
        return httpx.Response(200, json=mock_gemini_response)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handle_gemini))

    with patch("app.services.resume_extractor.extract_document_text", return_value=sample_text), \
         patch("app.services.resume_extractor.get_ai_provider", return_value=GeminiAIProvider(api_key="mock_gemini_key", client=mock_client)):
        result = await run_resume_extraction_pipeline(resume_id=102, db=mock_db)

    assert result.parsing_status == "review_required"
    assert result.parsed_entities_json["extraction_method"] == "gemini_ai"
    assert recorded_headers.get("x-goog-api-key") == "mock_gemini_key"
    assert len(result.parsed_entities_json["skills"]) == 3
    assert result.parsed_entities_json["_cache_meta"]["provider"] == "gemini"


# =============================================================================
# 3. END-TO-END PIPELINE WITH OPENAI PROVIDER (MOCKED HTTP)
# =============================================================================

@pytest.mark.asyncio
async def test_pipeline_openai_provider_end_to_end(tmp_path):
    """Verify OpenAI provider is called, parses response, sanitizes, and caches."""
    sample_text = (
        "Sneha Patel\n"
        "sneha@example.com\n"
        "Skills: React, TypeScript, Node.js\n"
    )
    fpath = _create_mock_resume_file(tmp_path, sample_text)
    file_hash = hashlib.sha256(sample_text.encode("utf-8")).hexdigest()

    resume = Resume(
        id=103,
        student_id=5,
        file_name="sneha_resume.pdf",
        file_path=str(fpath),
        file_type="pdf",
        file_size_bytes=len(sample_text),
        file_hash=file_hash,
        parsing_status="uploaded",
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = resume
    mock_db.execute = AsyncMock(return_value=mock_res)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    openai_output_json = {
        "personal_info": {"full_name": "Sneha Patel", "email": "sneha@example.com", "evidence": "Sneha Patel", "confidence": "high"},
        "education": [],
        "skills": [
            {"skill_name": "React", "category": "framework", "proficiency_level": "intermediate", "evidence": "React", "confidence": "high"},
            {"skill_name": "TypeScript", "category": "technical", "proficiency_level": "intermediate", "evidence": "TypeScript", "confidence": "high"},
        ],
        "projects": [],
        "experiences": [],
        "certifications": [],
    }

    mock_openai_response = {
        "choices": [
            {
                "message": {"content": json.dumps(openai_output_json), "role": "assistant"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 110, "completion_tokens": 60, "total_tokens": 170},
    }

    recorded_headers = {}

    def handle_openai(request: httpx.Request) -> httpx.Response:
        nonlocal recorded_headers
        recorded_headers = dict(request.headers)
        return httpx.Response(200, json=mock_openai_response)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handle_openai))

    with patch("app.services.resume_extractor.extract_document_text", return_value=sample_text), \
         patch("app.services.resume_extractor.get_ai_provider", return_value=OpenAIProvider(api_key="mock_openai_key", client=mock_client)):
        result = await run_resume_extraction_pipeline(resume_id=103, db=mock_db)

    assert result.parsing_status == "review_required"
    assert result.parsed_entities_json["extraction_method"] == "openai_ai"
    assert recorded_headers.get("authorization") == "Bearer mock_openai_key"
    assert result.parsed_entities_json["_cache_meta"]["provider"] == "openai"


# =============================================================================
# 4. EVIDENCE VALIDATION & HALLUCINATED ENTITY REMOVAL
# =============================================================================

def test_evidence_validator_purges_ungrounded_and_tracks_rejected():
    """Verify ungrounded entities are purged and recorded in rejected_entities."""
    raw_text = "Karan Singh\nkaran@example.com\nSkills: Python, SQL"

    # AI hallucinated Kubernetes, Amazon experience, and 9.9 CGPA
    hallucinated_data = ResumeStructuredData(
        personal_info=PersonalInfo(full_name="Karan Singh", email="karan@example.com"),
        skills=[
            SkillItem(skill_name="Python", category="technical", proficiency_level="advanced"),
            SkillItem(skill_name="Kubernetes", category="tool", proficiency_level="expert"),
        ],
        education=[
            EducationItem(institution="MIT Boston", degree="PhD", cgpa_or_percentage="9.9"),
        ],
        experiences=[
            ExperienceItem(company_name="Amazon AWS", role_title="Principal Architect"),
        ],
        extraction_method="gemini_ai",
    )

    sanitized = validate_and_sanitize_resume_data(raw_text, hallucinated_data)

    # Kubernetes, MIT Boston, and Amazon must be purged!
    assert len(sanitized.skills) == 1
    assert sanitized.skills[0].skill_name == "Python"
    assert len(sanitized.education) == 0
    assert len(sanitized.experiences) == 0
    assert sanitized.hallucinations_purged >= 3
    assert len(sanitized.rejected_entities) >= 3
    assert any("Kubernetes" in item for item in sanitized.rejected_entities)
    assert any("MIT Boston" in item for item in sanitized.rejected_entities)


def test_missing_information_returns_null_or_empty():
    """Verify that absent sections in raw text result in clean empty structures without fabrication."""
    raw_text = "Vijay Kumar\nEmail: vijay@apex.edu\nSkills: C++"
    empty_data = ResumeStructuredData(
        personal_info=PersonalInfo(full_name="Vijay Kumar", email="vijay@apex.edu"),
        skills=[SkillItem(skill_name="C++")],
        education=[],
        projects=[],
        experiences=[],
        certifications=[],
    )

    sanitized = validate_and_sanitize_resume_data(raw_text, empty_data)
    assert sanitized.projects == []
    assert sanitized.experiences == []
    assert sanitized.certifications == []
    assert sanitized.personal_info.phone is None
    assert sanitized.personal_info.linkedin_url is None


# =============================================================================
# 5. VERIFIED ACADEMIC METRIC PROTECTION
# =============================================================================

@pytest.mark.asyncio
async def test_sync_approved_protects_academic_metrics():
    """Verify institutional verified academic records are never overwritten by resume data."""
    student_profile = StudentProfile(
        id=7,
        user_id=20,
        roll_number="VERIFIED_ROLL_101",
        graduation_year=2025,
        cgpa=8.50,
        active_backlogs=0,
        total_backlogs=0,
    )

    resume = Resume(
        id=55,
        student_id=7,
        file_name="resume.pdf",
        file_path="/tmp/f.pdf",
        file_type="pdf",
        file_size_bytes=100,
        file_hash="hash55",
        parsing_status="review_required",
    )

    # Resume falsely claims CGPA 9.8
    claimed_data = ResumeStructuredData(
        personal_info=PersonalInfo(full_name="Student", email="student@example.com"),
        education=[EducationItem(institution="College", degree="B.Tech", cgpa_or_percentage="9.80")],
        skills=[SkillItem(skill_name="Python")],
    )

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    sync_req = ResumeSyncRequest(verified_data=claimed_data)
    resp = await sync_approved_resume_entities(
        resume=resume,
        student_profile=student_profile,
        sync_req=sync_req,
        db=mock_db,
    )

    assert resp.verified_metrics_protected is True
    # StudentProfile academic fields remain strictly identical
    assert student_profile.cgpa == 8.50
    assert student_profile.roll_number == "VERIFIED_ROLL_101"
    assert student_profile.graduation_year == 2025
    assert student_profile.active_backlogs == 0


# =============================================================================
# 6. FILE-HASH CACHING & VERSION INVALIDATION
# =============================================================================

@pytest.mark.asyncio
async def test_file_hash_caching_prevents_duplicate_calls(tmp_path):
    """Verify second extraction on identical file hash is served from cache."""
    sample_text = "Anita Roy\nEmail: anita@example.com\nSkills: Java, SQL"
    fpath = _create_mock_resume_file(tmp_path, sample_text)
    file_hash = hashlib.sha256(sample_text.encode("utf-8")).hexdigest()

    resume1 = Resume(id=201, student_id=1, file_name="a.pdf", file_path=str(fpath), file_type="pdf", file_size_bytes=50, file_hash=file_hash)
    resume2 = Resume(id=202, student_id=1, file_name="a_copy.pdf", file_path=str(fpath), file_type="pdf", file_size_bytes=50, file_hash=file_hash)

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = resume1
    mock_db.execute = AsyncMock(return_value=mock_res)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    call_count = 0
    mock_provider = MockAIProvider()
    original_extract = mock_provider.extract_resume_entities_with_usage

    async def counting_extract(text):
        nonlocal call_count
        call_count += 1
        return await original_extract(text)

    mock_provider.extract_resume_entities_with_usage = counting_extract  # type: ignore

    with patch("app.services.resume_extractor.extract_document_text", return_value=sample_text), \
         patch("app.services.resume_extractor.get_ai_provider", return_value=mock_provider):
        # First call: cache miss, invokes provider
        res1 = await run_resume_extraction_pipeline(resume_id=201, db=mock_db)
        assert call_count == 1

        # Second call with same hash: served from cache!
        mock_res.scalar_one_or_none.return_value = resume2
        res2 = await run_resume_extraction_pipeline(resume_id=202, db=mock_db)
        # Call count must still be 1 (zero additional provider calls)
        assert call_count == 1
        assert res2.parsed_entities_json == res1.parsed_entities_json


def test_cache_invalidation_on_prompt_and_schema_version_change():
    """Verify cache keys change when prompt version or schema version changes."""
    file_hash = "abcdef123456"
    base_key = compute_extraction_cache_key(file_hash, "gemini", "gemini-1.5-flash", schema_version="v1.0", prompt_version="v1.1")

    # Changed prompt version
    new_prompt_key = compute_extraction_cache_key(file_hash, "gemini", "gemini-1.5-flash", schema_version="v1.0", prompt_version="v1.2")
    assert base_key != new_prompt_key

    # Changed schema version
    new_schema_key = compute_extraction_cache_key(file_hash, "gemini", "gemini-1.5-flash", schema_version="v2.0", prompt_version="v1.1")
    assert base_key != new_schema_key

    # Changed provider
    openai_key = compute_extraction_cache_key(file_hash, "openai", "gpt-4o-mini", schema_version="v1.0", prompt_version="v1.1")
    assert base_key != openai_key


# =============================================================================
# 7. CONCURRENT DUPLICATE PREVENTION & PROVIDER ERROR HANDLING
# =============================================================================

@pytest.mark.asyncio
async def test_duplicate_concurrent_request_prevention():
    """Verify that attempting to re-trigger extraction while status is 'processing' raises HTTP 409."""
    resume = Resume(
        id=301,
        student_id=1,
        file_name="active.pdf",
        file_path="/tmp/act.pdf",
        file_type="pdf",
        file_size_bytes=100,
        file_hash="h1",
        parsing_status="processing",  # Already processing
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = resume
    mock_db.execute = AsyncMock(return_value=mock_res)

    with pytest.raises(AppError) as exc_info:
        await run_resume_extraction_pipeline(resume_id=301, db=mock_db)

    assert exc_info.value.code == "EXTRACTION_IN_PROGRESS"
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_provider_error_transitions_status_to_failed(tmp_path):
    """Verify that an AI provider error (e.g. rate limit, timeout) marks resume as failed."""
    sample_text = "Test Resume"
    fpath = _create_mock_resume_file(tmp_path, sample_text)
    resume = Resume(
        id=401,
        student_id=1,
        file_name="err.pdf",
        file_path=str(fpath),
        file_type="pdf",
        file_size_bytes=10,
        file_hash="hash_err",
        parsing_status="uploaded",
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = resume
    mock_db.execute = AsyncMock(return_value=mock_res)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    failing_provider = MagicMock()
    failing_provider.extract_resume_entities_with_usage = AsyncMock(
        side_effect=AIRateLimitError("Quota exhausted", retry_after=2.0)
    )

    with patch("app.services.resume_extractor.extract_document_text", return_value=sample_text), \
         patch("app.services.resume_extractor.get_ai_provider", return_value=failing_provider):
        with pytest.raises(AIRateLimitError):
            await run_resume_extraction_pipeline(resume_id=401, db=mock_db)

    assert resume.parsing_status == "failed"
    assert "[FAILED]" in resume.raw_extracted_text


# =============================================================================
# 8. AUTHORIZATION & OWNERSHIP BOUNDARIES
# =============================================================================

@pytest.mark.asyncio
async def test_student_ownership_authorization():
    """Verify Student B cannot trigger extraction or modify Student A's resume."""
    from app.routes.resumes import trigger_extraction

    student_a_user = User(id=1, role=UserRole.STUDENT)
    student_a_user.student_profile = StudentProfile(id=10, user_id=1)

    student_b_user = User(id=2, role=UserRole.STUDENT)
    student_b_user.student_profile = StudentProfile(id=20, user_id=2)

    resume_a = Resume(
        id=501,
        student_id=10,  # Belongs to Student A
        file_name="a.pdf",
        file_path="/tmp/a.pdf",
        file_type="pdf",
        file_size_bytes=50,
        file_hash="ha",
        parsing_status="uploaded",
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = resume_a
    mock_db.execute = AsyncMock(return_value=mock_res)

    # Student B attempts to trigger extraction on Student A's resume
    with pytest.raises(AuthorizationException) as exc_info:
        await trigger_extraction(resume_id=501, current_user=student_b_user, db=mock_db)

    assert "from your own resumes" in exc_info.value.message
