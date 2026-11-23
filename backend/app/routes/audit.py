"""FastAPI Routes for TASK 11: Centralized Audit Logging & Activity Monitoring.

Provides endpoints for querying append-only audit trails, viewing change diffs,
retrieving summary statistics, and verifying cryptographic chain integrity.
"""
from datetime import datetime
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.audit import (
    AuditCategoriesResponse,
    AuditIntegrityVerificationResponse,
    AuditLogItemResponse,
    AuditLogListResponse,
    AuditSummaryStats,
)
from app.services.audit_service import (
    get_audit_categories_taxonomy,
    get_audit_log_by_id,
    get_audit_summary_stats,
    list_audit_logs,
    verify_audit_log_integrity,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["Centralized Audit Logging"])
require_auditor_access = require_roles(UserRole.ADMIN, UserRole.TPO)
require_admin_only = require_roles(UserRole.ADMIN)


@router.get(
    "/logs",
    response_model=AuditLogListResponse,
    summary="List and filter audit log records",
)
async def get_audit_logs(
    category: Optional[str] = Query(None, description="Audit domain category"),
    action: Optional[str] = Query(None, description="Specific operation action"),
    entity_type: Optional[str] = Query(None, description="Target entity type name"),
    entity_id: Optional[str] = Query(None, description="Target entity primary identifier"),
    status: Optional[str] = Query(None, description="Result status: SUCCESS, FAILURE, WARNING"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    institution_id: Optional[int] = Query(None, description="Filter by institution ID (Admin only)"),
    date_from: Optional[datetime] = Query(None, description="Filter records on or after UTC datetime"),
    date_to: Optional[datetime] = Query(None, description="Filter records on or before UTC datetime"),
    search: Optional[str] = Query(None, description="Keyword search across action, user, entity"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_auditor_access),
    session: AsyncSession = Depends(get_async_session),
) -> AuditLogListResponse:
    """Retrieve paginated audit trail logs.
    
    - Admin: platform-wide access across all institutions and categories.
    - TPO: strictly scoped to own institution; administrative platform logs excluded.
    """
    return await list_audit_logs(
        session=session,
        current_user=current_user,
        category=category,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        status_filter=status,
        user_id=user_id,
        institution_id=institution_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        limit=limit,
    )


@router.get(
    "/stats",
    response_model=AuditSummaryStats,
    summary="Get audit dashboard KPI summary statistics",
)
async def get_audit_stats(
    current_user: User = Depends(require_auditor_access),
    session: AsyncSession = Depends(get_async_session),
) -> AuditSummaryStats:
    """Retrieve audit statistics (total events, security events, critical changes, failure rate)."""
    return await get_audit_summary_stats(session=session, current_user=current_user)


@router.get(
    "/categories",
    response_model=AuditCategoriesResponse,
    summary="Get available categories, actions, and entities taxonomy",
)
async def get_categories_taxonomy(
    current_user: User = Depends(require_auditor_access),
    session: AsyncSession = Depends(get_async_session),
) -> AuditCategoriesResponse:
    """Retrieve taxonomy of recorded categories, actions, and entities for UI filters."""
    return await get_audit_categories_taxonomy(session=session)


@router.get(
    "/verify-integrity",
    response_model=AuditIntegrityVerificationResponse,
    summary="Verify cryptographic SHA-256 hash chaining of audit records",
)
async def verify_integrity(
    limit: int = Query(1000, ge=1, le=5000, description="Number of sequential records to verify"),
    current_user: User = Depends(require_admin_only),
    session: AsyncSession = Depends(get_async_session),
) -> AuditIntegrityVerificationResponse:
    """Validate SHA-256 hash chain links. Restricted to platform Administrators."""
    return await verify_audit_log_integrity(session=session, limit=limit)


@router.get(
    "/logs/{log_id}",
    response_model=AuditLogItemResponse,
    summary="Get detailed audit record by ID including diffs and metadata",
)
async def get_audit_log_detail(
    log_id: int,
    current_user: User = Depends(require_auditor_access),
    session: AsyncSession = Depends(get_async_session),
) -> AuditLogItemResponse:
    """Fetch a single audit log entry with diff details."""
    return await get_audit_log_by_id(
        session=session,
        log_id=log_id,
        current_user=current_user,
    )

