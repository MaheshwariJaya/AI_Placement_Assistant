from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.schemas.user import UserResponse


class StudentProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    roll_number: str
    graduation_year: int
    cgpa: float
    active_backlogs: int
    total_backlogs: int
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    is_placement_ready: bool
    created_at: datetime
    updated_at: datetime
    department_name: Optional[str] = None
    institution_name: Optional[str] = None
    user: Optional[UserResponse] = None


class StudentPortfolioUpdate(BaseModel):
    """Fields modifiable by student for personal portfolio links."""
    linkedin_url: Optional[str] = Field(default=None, max_length=255)
    github_url: Optional[str] = Field(default=None, max_length=255)
    portfolio_url: Optional[str] = Field(default=None, max_length=255)


class StudentAcademicUpdate(BaseModel):
    """Official academic fields modifiable only by TPO / Institutional authority."""
    cgpa: Optional[float] = Field(default=None, ge=0.0, le=10.0)
    active_backlogs: Optional[int] = Field(default=None, ge=0)
    total_backlogs: Optional[int] = Field(default=None, ge=0)
    is_placement_ready: Optional[bool] = None
