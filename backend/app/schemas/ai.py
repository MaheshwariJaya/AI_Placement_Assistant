from typing import Generic, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class AIUsageMetadata(BaseModel):
    """Normalized token usage and latency telemetry from AI providers."""

    model_config = ConfigDict(from_attributes=True)

    provider: str = Field(..., description="Provider name: 'mock', 'gemini', or 'openai'")
    model: str = Field(..., description="Configured model identifier")
    prompt_tokens: Optional[int] = Field(None, description="Input prompt tokens consumed, if reported")
    completion_tokens: Optional[int] = Field(None, description="Output candidate tokens generated, if reported")
    total_tokens: Optional[int] = Field(None, description="Total tokens consumed, if reported")
    latency_ms: int = Field(0, description="End-to-end request latency in milliseconds")


class AIStructuredOutput(BaseModel, Generic[T]):
    """Container holding validated structured data and provider telemetry."""

    model_config = ConfigDict(from_attributes=True)

    data: T
    usage: AIUsageMetadata

