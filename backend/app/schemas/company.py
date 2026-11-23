from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CompanyBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200, description="Company registered legal or brand name")
    industry: str = Field(..., min_length=2, max_length=100, description="Industry sector e.g. Information Technology, FinTech, Automotive")
    description: Optional[str] = Field(None, max_length=5000, description="Company overview, vision, and campus recruitment summary")
    website: Optional[str] = Field(None, max_length=255, description="Official company domain or careers portal URL")
    location: Optional[str] = Field(None, max_length=150, description="Corporate headquarters or primary operational city")
    company_size: Optional[str] = Field(None, max_length=50, description="Employee count bracket e.g. '1-50', '51-200', '201-1000', '1000+'")
    contact_email: Optional[str] = Field(None, max_length=255, description="Official corporate recruiting contact email")
    contact_phone: Optional[str] = Field(None, max_length=30, description="Official HR contact telephone number")


class CompanyCreate(CompanyBase):
    institution_id: Optional[int] = Field(None, description="Optional collegiate institution partner affiliation")


class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    industry: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=5000)
    website: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=150)
    company_size: Optional[str] = Field(None, max_length=50)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=30)


class CompanyVerifyRequest(BaseModel):
    """Payload for TPO or Platform Administrator verification workflow."""
    is_verified: bool = Field(..., description="Verification status approved by institutional TPO or platform Admin")


class CompanyAffiliateRequest(BaseModel):
    """Payload for associating an existing company with a collegiate institution."""
    institution_id: Optional[int] = Field(
        None,
        description="Collegiate institution ID to associate with. For TPO, defaults to their own institution if omitted.",
    )


class CompanyResponse(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = 1
    institution_id: Optional[int] = None
    institution_name: Optional[str] = None
    is_verified: Optional[bool] = False
    is_active: Optional[bool] = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    active_jobs_count: Optional[int] = 0


class RecruiterProfileBase(BaseModel):
    designation: Optional[str] = Field(None, max_length=100, description="Corporate title e.g. Technical Hiring Lead")
    corporate_phone: Optional[str] = Field(None, max_length=30)


class RecruiterProfileCreate(RecruiterProfileBase):
    company_id: int = Field(..., description="Target corporate company ID to associate with")


class RecruiterProfileUpdate(RecruiterProfileBase):
    pass


class RecruiterProfileResponse(RecruiterProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = 1
    user_id: int
    company_id: int
    company: Optional[CompanyResponse] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
