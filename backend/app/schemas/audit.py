"""Pydantic schemas for TASK 11: Centralized Audit Logging & Activity Monitoring.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AuditLogItemResponse(BaseModel):
    """Detailed audit log item response schema."""
    id: int
    event_id: str
    user_id: Optional[int] = None
    user_role: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    institution_id: Optional[int] = None
    category: str
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    status: str
    correlation_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    previous_values: Optional[Dict[str, Any]] = None
    updated_values: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="metadata_")
    prev_hash: Optional[str] = None
    record_hash: str
    timestamp: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class AuditLogListResponse(BaseModel):
    """Paginated audit records response."""
    items: List[AuditLogItemResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class AuditSummaryStats(BaseModel):
    """High-level KPI metrics for audit dashboard."""
    total_events: int
    security_events: int
    critical_changes: int
    failed_operations: int
    integrity_status: str


class AuditIntegrityVerificationResponse(BaseModel):
    """Cryptographic SHA-256 hash chain verification result."""
    is_valid: bool
    total_checked: int
    broken_links_count: int
    invalid_records: List[int] = Field(default_factory=list)
    details: str


class AuditCategoriesResponse(BaseModel):
    """Taxonomy of categories, actions, and entities for UI filters."""
    categories: List[str]
    actions: List[str]
    entity_types: List[str]

