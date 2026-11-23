from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class InstitutionCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=50)
    city: str = Field(..., min_length=2, max_length=100)


class InstitutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    city: str
    is_active: bool
    created_at: datetime


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    code: str = Field(..., min_length=2, max_length=20)


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    institution_id: int
    name: str
    code: str
    is_active: bool
