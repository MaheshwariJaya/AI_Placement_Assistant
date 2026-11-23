from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.user import UserRole
from app.schemas.auth import EmailStr


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    institution_id: Optional[int] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    institution_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=20)
