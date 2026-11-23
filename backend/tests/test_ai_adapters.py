import asyncio
import json
import logging
from typing import List, Optional
from unittest.mock import patch

import httpx
import pytest
from pydantic import BaseModel, Field

from app.schemas.ai import AIUsageMetadata
from app.schemas.resume import ResumeStructuredData
from app.services.ai_provider import (
    AIAuthenticationError,
    AIConfigError,
    AIInvalidResponseError,
    AIProviderError,
    AIRateLimitError,
    AIServiceError,
    AITimeoutError,
    AIValidationError,
    BaseAIProvider,
    GeminiAIProvider,
    MockAIProvider,
    OpenAIProvider,
    get_ai_provider,
    mask_secret,
    parse_retry_after,
    strip_markdown_json_delimiters,
)


# Test Pydantic Schema
class SampleAdviceSchema(BaseModel):
    advice: str = Field(..., description="Advice message")
    steps: List[str] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0)


# =============================================================================
# 1. UTILITY TESTS
# =============================================================================

def test_strip_markdown_json_delimiters():
    raw_markdown = '```json\n{"message": "hello"}\n```'
    assert strip_markdown_json_delimiters(raw_markdown) == '{"message": "hello"}'

    raw_markdown_no_lang = '```\n{"message": "world"}\n```'
    assert strip_markdown_json_delimiters(raw_markdown_no_lang) == '{"message": "world"}'

    clean_json = '{"message": "clean"}'
    assert strip_markdown_json_delimiters(clean_json) == '{"message": "clean"}'

    assert strip_markdown_json_delimiters("") == ""
    assert strip_markdown_json_delimiters(None) == ""


def test_parse_retry_after():
    assert parse_retry_after("2.5") == 2.5
    assert parse_retry_after("0.05") == 0.1  # min bound
    assert parse_retry_after("100.0", max_delay=5.0) == 5.0  # max bound
    assert parse_retry_after("invalid_header", fallback=1.0) == 1.0
    assert parse_retry_after(None, fallback=1.5) == 1.5


def test_mask_secret():
    assert mask_secret("sk-1234567890abcdef") == "sk-...cdef"
    assert mask_secret("short") == "***"
    assert mask_secret("") == "[NOT_SET]"
    assert mask_secret(None) == "[NOT_SET]"


# =============================================================================
# 2. PROVIDER FACTORY & CONFIGURATION TESTS
# =============================================================================

def test_get_ai_provider_mock():
    with patch("app.services.ai_provider.settings.AI_PROVIDER", "mock"):
        provider = get_ai_provider()
        assert isinstance(provider, MockAIProvider)


def test_get_ai_provider_gemini_missing_key():
    with patch("app.services.ai_provider.settings.AI_PROVIDER", "gemini"), \
         patch("app.services.ai_provider.settings.GEMINI_API_KEY", ""):
        with pytest.raises(AIConfigError) as exc_info:
            get_ai_provider()
        assert exc_info.value.code == "CONFIG_ERROR"
        assert "GEMINI_API_KEY" in exc_info.value.message


def test_get_ai_provider_gemini_success():
    with patch("app.services.ai_provider.settings.AI_PROVIDER", "gemini"), \
         patch("app.services.ai_provider.settings.GEMINI_API_KEY", "test_gemini_key"), \
         patch("app.services.ai_provider.settings.GEMINI_MODEL", "gemini-2.0-flash-exp"):
        provider = get_ai_provider()
        assert isinstance(provider, GeminiAIProvider)
        assert provider.api_key == "test_gemini_key"
        assert provider.model_name == "gemini-2.0-flash-exp"
        assert "gemini-2.0-flash-exp" in provider.endpoint


def test_get_ai_provider_openai_missing_key():
    with patch("app.services.ai_provider.settings.AI_PROVIDER", "openai"), \
         patch("app.services.ai_provider.settings.OPENAI_API_KEY", ""):
        with pytest.raises(AIConfigError) as exc_info:
            get_ai_provider()
        assert exc_info.value.code == "CONFIG_ERROR"
        assert "OPENAI_API_KEY" in exc_info.value.message


def test_get_ai_provider_openai_success():
    with patch("app.services.ai_provider.settings.AI_PROVIDER", "openai"), \
         patch("app.services.ai_provider.settings.OPENAI_API_KEY", "test_openai_key"), \
         patch("app.services.ai_provider.settings.OPENAI_MODEL", "gpt-4o"):
        provider = get_ai_provider()
        assert isinstance(provider, OpenAIProvider)
        assert provider.api_key == "test_openai_key"
        assert provider.model_name == "gpt-4o"


def test_get_ai_provider_unknown_fails_clearly():
    with patch("app.services.ai_provider.settings.AI_PROVIDER", "claude_anthropic"):
        with pytest.raises(AIConfigError) as exc_info:
            get_ai_provider()
        assert exc_info.value.code == "CONFIG_ERROR"
        assert "Unknown AI_PROVIDER" in exc_info.value.message


def test_provider_constructors_require_keys():
    with pytest.raises(AIConfigError) as exc_gemini:
        GeminiAIProvider(api_key="")
    assert exc_gemini.value.code == "CONFIG_ERROR"

    with pytest.raises(AIConfigError) as exc_openai:
        OpenAIProvider(api_key="")
    assert exc_openai.value.code == "CONFIG_ERROR"


def test_direct_provider_constructors_read_settings_models():
    with patch("app.services.ai_provider.settings.GEMINI_MODEL", "gemini-pro-custom"), \
         patch("app.services.ai_provider.settings.OPENAI_MODEL", "gpt-4o-custom"):
        gemini = GeminiAIProvider(api_key="gemini_key")
        assert gemini.model_name == "gemini-pro-custom"
        assert "gemini-pro-custom" in gemini.endpoint

        openai = OpenAIProvider(api_key="openai_key")
        assert openai.model_name == "gpt-4o-custom"


# =============================================================================
# 3. MOCK AI PROVIDER TESTS (OFFLINE)
# =============================================================================

@pytest.mark.asyncio
async def test_mock_provider_extract_resume_entities():
    provider = MockAIProvider()
    sample_text = """
    John Doe
    john.doe@example.com
    (555) 123-4567
    https://github.com/johndoe

    Education
    Bachelor of Technology in Computer Science, 2020 - 2024
    Apex University
    CGPA: 8.9 / 10

    Technical Skills
    Python, FastAPI, React, Docker, PostgreSQL, Git

    Projects
    Placement Intelligence: Built automated ATS matching system using Python and FastAPI
    """
    res = await provider.extract_resume_entities(sample_text)
    assert isinstance(res, ResumeStructuredData)
    assert res.personal_info.full_name == "John Doe"
    assert res.personal_info.email == "john.doe@example.com"
    assert any(s.skill_name == "Python" for s in res.skills)
    assert any(s.skill_name == "FastAPI" for s in res.skills)
    assert any(e.degree == "Bachelor of Technology" for e in res.education)
    assert res.extraction_method == "mock_rule_based"


@pytest.mark.asyncio
async def test_mock_provider_extract_with_usage():
    provider = MockAIProvider()
    data, usage = await provider.extract_resume_entities_with_usage("Python Developer")
    assert isinstance(data, ResumeStructuredData)
    assert isinstance(usage, AIUsageMetadata)
    assert usage.provider == "mock"
    assert usage.model == "mock-rule-engine"
    assert usage.prompt_tokens is not None
    assert usage.completion_tokens == 150


@pytest.mark.asyncio
async def test_mock_provider_generate_structured():
    provider = MockAIProvider()
    data, usage = await provider.generate_structured(
        schema=SampleAdviceSchema,
        system_instruction="Provide guidance",
        user_prompt="How do I prepare for Python?",
    )
    assert isinstance(data, SampleAdviceSchema)
    assert isinstance(usage, AIUsageMetadata)
    assert usage.provider == "mock"


# =============================================================================
# 4. GEMINI ADAPTER TESTS (MOCKED HTTP TRANSPORT)
# =============================================================================

@pytest.mark.asyncio
async def test_gemini_generate_structured_success():
    sample_response_json = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "advice": "Practice LeetCode mediums and system design basics.",
                                "steps": ["Learn hash maps", "Solve two pointers", "Review trees"],
                                "confidence": 0.95,
                            })
                        }
                    ],
                    "role": "model",
                },
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 85,
            "candidatesTokenCount": 42,
            "totalTokenCount": 127,
        },
    }

    recorded_requests = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        recorded_requests.append(request)
        assert request.method == "POST"
        assert "generativelanguage.googleapis.com" in str(request.url)
        assert request.headers.get("x-goog-api-key") == "fake_gemini_key"
        assert "key=" not in str(request.url)  # No secret in URL!
        req_body = json.loads(request.content)
        assert "systemInstruction" in req_body
        assert req_body["generationConfig"]["responseMimeType"] == "application/json"
        return httpx.Response(200, json=sample_response_json)

    transport = httpx.MockTransport(handle_request)
    client = httpx.AsyncClient(transport=transport)

    provider = GeminiAIProvider(
        api_key="fake_gemini_key",
        model_name="gemini-1.5-flash",
        client=client,
    )

    data, usage = await provider.generate_structured(
        schema=SampleAdviceSchema,
        system_instruction="You are a career mentor.",
        user_prompt="Give me steps for Python prep.",
    )

    assert isinstance(data, SampleAdviceSchema)
    assert data.advice == "Practice LeetCode mediums and system design basics."
    assert len(data.steps) == 3
    assert data.confidence == 0.95

    assert isinstance(usage, AIUsageMetadata)
    assert usage.provider == "gemini"
    assert usage.model == "gemini-1.5-flash"
    assert usage.prompt_tokens == 85
    assert usage.completion_tokens == 42
    assert usage.total_tokens == 127
    assert len(recorded_requests) == 1


@pytest.mark.asyncio
async def test_gemini_markdown_code_fence_cleaning():
    markdown_wrapped_json = '```json\n{"advice": "Master SQL queries", "steps": ["Joins", "Indexes"], "confidence": 0.9}\n```'
    sample_response = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": markdown_wrapped_json}]
                }
            }
        ],
        "usageMetadata": {"promptTokenCount": 50, "candidatesTokenCount": 30, "totalTokenCount": 80},
    }

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=sample_response))
    client = httpx.AsyncClient(transport=transport)
    provider = GeminiAIProvider(api_key="fake_key", client=client)

    data, usage = await provider.generate_structured(
        schema=SampleAdviceSchema,
        system_instruction="Help",
        user_prompt="SQL advice",
    )
    assert data.advice == "Master SQL queries"
    assert data.steps == ["Joins", "Indexes"]


@pytest.mark.asyncio
async def test_gemini_auth_error_no_retry():
    call_count = 0

    def handle_auth_fail(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(401, json={"error": {"message": "API key not valid."}})

    transport = httpx.MockTransport(handle_auth_fail)
    client = httpx.AsyncClient(transport=transport)
    provider = GeminiAIProvider(api_key="invalid_key", client=client)

    with pytest.raises(AIAuthenticationError) as exc_info:
        await provider.generate_structured(
            schema=SampleAdviceSchema,
            system_instruction="Help",
            user_prompt="Hello",
        )
    assert exc_info.value.code == "AUTHENTICATION_ERROR"
    # Crucial: Must NOT retry 401
    assert call_count == 1


@pytest.mark.asyncio
async def test_gemini_rate_limit_with_retry_after():
    call_count = 0

    def handle_rate_limit(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            return httpx.Response(
                429,
                headers={"Retry-After": "0.1"},
                json={"error": {"message": "Resource exhausted"}},
            )
        # Succeed on 2nd attempt
        return httpx.Response(200, json={
            "candidates": [{"content": {"parts": [{"text": '{"advice": "Recovered", "steps": [], "confidence": 1.0}'}]}}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 10, "totalTokenCount": 20},
        })

    transport = httpx.MockTransport(handle_rate_limit)
    client = httpx.AsyncClient(transport=transport)
    provider = GeminiAIProvider(api_key="fake_key", client=client)

    data, usage = await provider.generate_structured(
        schema=SampleAdviceSchema,
        system_instruction="System",
        user_prompt="Prompt",
    )
    assert data.advice == "Recovered"
    assert call_count == 2


@pytest.mark.asyncio
async def test_gemini_malformed_json_raises_invalid_response():
    sample_response = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "{malformed_json: true,,"}]
                }
            }
        ]
    }
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=sample_response))
    client = httpx.AsyncClient(transport=transport)
    provider = GeminiAIProvider(api_key="fake_key", client=client)

    with pytest.raises(AIInvalidResponseError) as exc_info:
        await provider.generate_structured(
            schema=SampleAdviceSchema,
            system_instruction="System",
            user_prompt="Prompt",
        )
    assert exc_info.value.code == "INVALID_RESPONSE"


@pytest.mark.asyncio
async def test_gemini_schema_validation_error():
    # Valid JSON but missing required field 'advice'
    sample_response = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": '{"steps": ["Step 1"], "confidence": 0.5}'}]
                }
            }
        ]
    }
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=sample_response))
    client = httpx.AsyncClient(transport=transport)
    provider = GeminiAIProvider(api_key="fake_key", client=client)

    with pytest.raises(AIValidationError) as exc_info:
        await provider.generate_structured(
            schema=SampleAdviceSchema,
            system_instruction="System",
            user_prompt="Prompt",
        )
    assert exc_info.value.code == "VALIDATION_ERROR"


# =============================================================================
# 5. OPENAI ADAPTER TESTS (MOCKED HTTP TRANSPORT)
# =============================================================================

@pytest.mark.asyncio
async def test_openai_generate_structured_success():
    sample_openai_json = {
        "id": "chatcmpl-test-123",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps({
                        "advice": "Focus on data structures and concurrency.",
                        "steps": ["Learn async/await", "Practice lock contention"],
                        "confidence": 0.92,
                    }),
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 110,
            "completion_tokens": 35,
            "total_tokens": 145,
        },
    }

    recorded_requests = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        recorded_requests.append(request)
        assert request.method == "POST"
        assert str(request.url) == "https://api.openai.com/v1/chat/completions"
        assert request.headers.get("Authorization") == "Bearer fake_openai_key"
        body = json.loads(request.content)
        assert body["model"] == "gpt-4o-mini"
        assert body["response_format"] == {"type": "json_object"}
        assert len(body["messages"]) == 2
        return httpx.Response(200, json=sample_openai_json)

    transport = httpx.MockTransport(handle_request)
    client = httpx.AsyncClient(transport=transport)
    provider = OpenAIProvider(api_key="fake_openai_key", client=client)

    data, usage = await provider.generate_structured(
        schema=SampleAdviceSchema,
        system_instruction="You are an expert engineer.",
        user_prompt="Concurrency questions.",
    )

    assert isinstance(data, SampleAdviceSchema)
    assert data.advice == "Focus on data structures and concurrency."
    assert len(data.steps) == 2

    assert isinstance(usage, AIUsageMetadata)
    assert usage.provider == "openai"
    assert usage.model == "gpt-4o-mini"
    assert usage.prompt_tokens == 110
    assert usage.completion_tokens == 35
    assert usage.total_tokens == 145


@pytest.mark.asyncio
async def test_openai_auth_error_no_retry():
    call_count = 0

    def handle_auth_fail(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(401, json={"error": {"message": "Incorrect API key provided"}})

    transport = httpx.MockTransport(handle_auth_fail)
    client = httpx.AsyncClient(transport=transport)
    provider = OpenAIProvider(api_key="bad_openai_key", client=client)

    with pytest.raises(AIAuthenticationError) as exc_info:
        await provider.generate_structured(
            schema=SampleAdviceSchema,
            system_instruction="Help",
            user_prompt="Hello",
        )
    assert exc_info.value.code == "AUTHENTICATION_ERROR"
    assert call_count == 1


@pytest.mark.asyncio
async def test_openai_timeout_handling():
    def handle_timeout(request: httpx.Request):
        raise httpx.ReadTimeout("Read timed out")

    transport = httpx.MockTransport(handle_timeout)
    client = httpx.AsyncClient(transport=transport)
    provider = OpenAIProvider(api_key="fake_key", client=client)

    with pytest.raises(AITimeoutError) as exc_info:
        await provider.generate_structured(
            schema=SampleAdviceSchema,
            system_instruction="Help",
            user_prompt="Hello",
        )
    assert exc_info.value.code == "TIMEOUT_ERROR"


@pytest.mark.asyncio
async def test_openai_usage_none_when_omitted():
    # Verify that if provider does not return usage, it is safely None (not invented)
    sample_response_no_usage = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"advice": "Keep going", "steps": [], "confidence": 1.0})
                }
            }
        ]
    }
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=sample_response_no_usage))
    client = httpx.AsyncClient(transport=transport)
    provider = OpenAIProvider(api_key="fake_key", client=client)

    data, usage = await provider.generate_structured(
        schema=SampleAdviceSchema,
        system_instruction="Help",
        user_prompt="Hello",
    )
    assert usage.prompt_tokens is None
    assert usage.completion_tokens is None
    assert usage.total_tokens is None


# =============================================================================
# 6. RESUME EXTRACTION PIPELINE INTEGRATION (WITH EVIDENCE VALIDATION)
# =============================================================================

@pytest.mark.asyncio
async def test_gemini_extract_resume_entities_with_evidence_sanitization():
    raw_resume = """
    Alice Smith
    alice.smith@university.edu
    +1-555-0199
    
    Education
    Bachelor of Technology in Electrical Engineering, 2021 - 2025
    State Engineering College
    CGPA: 8.4
    
    Skills
    Python, C++, Machine Learning, Docker
    """

    mock_llm_json = {
        "personal_info": {
            "full_name": "Alice Smith",
            "email": "alice.smith@university.edu",
            "phone": "+1-555-0199",
            "evidence": "Alice Smith alice.smith@university.edu",
            "confidence": "high",
        },
        "education": [
            {
                "institution": "State Engineering College",
                "degree": "Bachelor of Technology",
                "field_of_study": "Electrical Engineering",
                "start_year": 2021,
                "end_year": 2025,
                "cgpa_or_percentage": "8.4",
                "evidence": "Bachelor of Technology in Electrical Engineering, 2021 - 2025 State Engineering College CGPA: 8.4",
                "confidence": "high",
            }
        ],
        "skills": [
            {"skill_name": "Python", "category": "technical", "evidence": "Python", "confidence": "high"},
            {"skill_name": "C++", "category": "technical", "evidence": "C++", "confidence": "high"},
            {"skill_name": "Docker", "category": "tool", "evidence": "Docker", "confidence": "high"},
            # Hallucinated skill not present in text:
            {"skill_name": "Quantum Computing", "category": "technical", "evidence": "Quantum Computing", "confidence": "high"},
        ],
        "projects": [],
        "experiences": [],
        "certifications": [],
    }

    gemini_response = {
        "candidates": [
            {
                "content": {"parts": [{"text": json.dumps(mock_llm_json)}]}
            }
        ],
        "usageMetadata": {"promptTokenCount": 200, "candidatesTokenCount": 150, "totalTokenCount": 350},
    }

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=gemini_response))
    client = httpx.AsyncClient(transport=transport)
    provider = GeminiAIProvider(api_key="fake_key", client=client)

    result = await provider.extract_resume_entities(raw_resume)
    assert isinstance(result, ResumeStructuredData)
    assert result.extraction_method == "gemini_ai"
    assert result.personal_info.full_name == "Alice Smith"
    
    skill_names = [s.skill_name for s in result.skills]
    assert "Python" in skill_names
    assert "C++" in skill_names
    assert "Docker" in skill_names
    # Grounding defense: Hallucinated skill must have been purged by evidence_validator!
    assert "Quantum Computing" not in skill_names
    assert result.hallucinations_purged >= 1


@pytest.mark.asyncio
async def test_openai_extract_resume_entities_with_usage():
    raw_resume = "Jane Doe\njane@test.com\nSkills: Python, React"
    mock_llm_json = {
        "personal_info": {"full_name": "Jane Doe", "email": "jane@test.com", "confidence": "high"},
        "education": [],
        "skills": [{"skill_name": "Python", "evidence": "Python", "confidence": "high"}],
        "projects": [],
        "experiences": [],
        "certifications": [],
    }
    openai_response = {
        "choices": [{"message": {"content": json.dumps(mock_llm_json)}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    }

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=openai_response))
    client = httpx.AsyncClient(transport=transport)
    provider = OpenAIProvider(api_key="fake_key", client=client)

    data, usage = await provider.extract_resume_entities_with_usage(raw_resume)
    assert data.extraction_method == "openai_ai"
    assert usage.provider == "openai"
    assert usage.prompt_tokens == 100
    assert usage.total_tokens == 150


# =============================================================================
# 7. LOGGING & SENSITIVITY AUDIT
# =============================================================================

@pytest.mark.asyncio
async def test_sensitive_credentials_never_logged(caplog):
    secret_key = "super_secret_ai_key_9999"
    sample_response = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": '{"advice": "OK", "steps": [], "confidence": 1.0}'}]
                }
            }
        ]
    }
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=sample_response))
    client = httpx.AsyncClient(transport=transport)
    provider = GeminiAIProvider(api_key=secret_key, client=client)

    with caplog.at_level(logging.DEBUG):
        await provider.generate_structured(
            schema=SampleAdviceSchema,
            system_instruction="Private system prompt with sensitive context",
            user_prompt="Confidential resume text with phone: 555-0199",
        )

    full_log_text = caplog.text
    # Assert API key is NEVER logged
    assert secret_key not in full_log_text
    assert "KEY_REDACTED" in full_log_text or secret_key not in full_log_text
