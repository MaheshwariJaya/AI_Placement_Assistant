from typing import Annotated, Any, Dict, Optional
from pydantic import BaseModel, Field

from app.models.user import UserRole

# Standard RFC-compliant email string pattern
EmailStr = Annotated[
    str,
    Field(
        min_length=5,
        max_length=255,
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
    ),
]


class LoginRequest(BaseModel):
    """User login credential payload."""
    email: EmailStr
    password: str = Field(..., min_length=1)


class StudentRegistrationData(BaseModel):
    """Specific academic attributes required when role is Student."""
    roll_number: str = Field(..., min_length=1, max_length=50)
    graduation_year: int = Field(..., ge=2000, le=2100)
    cgpa: float = Field(..., ge=0.0, le=10.0)
    active_backlogs: int = Field(default=0, ge=0)
    total_backlogs: int = Field(default=0, ge=0)


class RegisterRequest(BaseModel):
    """Unified user registration payload adhering to M1 specifications."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=150)
    phone: Optional[str] = Field(default=None, max_length=20)
    role: UserRole
    institution_id: Optional[int] = None
    department_id: Optional[int] = None
    student_data: Optional[StudentRegistrationData] = None


class TokenResponse(BaseModel):
    """Standard JWT authentication response envelope."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_hours: int = 24
    user: Dict[str, Any]


class RefreshTokenRequest(BaseModel):
    """Refresh token payload to request a new access token."""
    refresh_token: str


class LogoutRequest(BaseModel):
    """Payload for secure server-side session termination."""
    refresh_token: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    """Request password reset link."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password payload using verified token."""
    token: str
    new_password: str = Field(..., min_length=8)


class EmailVerifyRequest(BaseModel):
    """Email activation verification payload."""
    token: str


class ChangePasswordRequest(BaseModel):
    """Authenticated password update payload."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)
