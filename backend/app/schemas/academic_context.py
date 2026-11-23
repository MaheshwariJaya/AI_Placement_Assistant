from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StudentAcademicContext(BaseModel):
    """Authoritative, centralized student academic context.
    
    Guarantees official academic branch is derived strictly from verified institutional
    records and never inferred from skills, resumes, or client input.
    """
    model_config = ConfigDict(from_attributes=True)

    student_id: int
    user_id: int
    full_name: str
    email: str
    roll_number: Optional[str] = None
    institution_id: int
    institution_name: str

    # Authoritative Academic Branch
    official_department_id: Optional[int] = None
    official_department_name: Optional[str] = None
    official_department_code: Optional[str] = None
    is_branch_verified: bool = False
    branch_verification_message: Optional[str] = None

    # Academic Performance & Cutoff Data
    graduation_year: Optional[int] = None
    current_semester: Optional[int] = None
    verified_cgpa: float = Field(default=0.0, ge=0.0, le=10.0)
    active_backlogs: int = Field(default=0, ge=0)
    total_backlogs: int = Field(default=0, ge=0)
    academic_status: str = "verified"

    # Portfolio & Career Context
    career_interests: List[str] = Field(default_factory=list)
    approved_skills: List[str] = Field(default_factory=list)
    approved_projects: List[str] = Field(default_factory=list)


class UpdateCareerInterestsRequest(BaseModel):
    """Allows students to declare elective career goals without altering official academic branch."""
    career_interests: List[str] = Field(..., max_length=10)


class TPOUpdateBranchRequest(BaseModel):
    """Authorized TPO/Admin workflow to update a student's official academic branch."""
    department_id: int
    reason: str = Field(..., min_length=3, max_length=500)
    cgpa: Optional[float] = Field(default=None, ge=0.0, le=10.0)
    active_backlogs: Optional[int] = Field(default=None, ge=0)
    total_backlogs: Optional[int] = Field(default=None, ge=0)
