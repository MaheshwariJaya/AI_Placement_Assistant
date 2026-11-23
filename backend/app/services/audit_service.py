"""Centralized Audit Logging & Activity Monitoring Service (TASK 11).

Provides tamper-evident, append-only cryptographic logging, sensitive data
redaction, multi-tenant RBAC filtering, and audit trail verification.
"""
from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import uuid

from fastapi import HTTPException, status
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditCategory, AuditLog, AuditStatus
from app.models.user import User, UserRole
from app.schemas.audit import (
    AuditCategoriesResponse,
    AuditIntegrityVerificationResponse,
    AuditLogItemResponse,
    AuditLogListResponse,
    AuditSummaryStats,
)

logger = logging.getLogger(__name__)

GENESIS_HASH = "0" * 64
SENSITIVE_KEYS: Set[str] = {
    "password",
    "password_hash",
    "hashed_password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "jwt",
    "api_key",
    "apikey",
    "authorization",
    "auth_token",
    "credit_card",
    "cvv",
}


def sanitize_sensitive_data(obj: Any) -> Any:
    """Recursively redact passwords, tokens, API keys and secrets from audit payloads."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        sanitized: Dict[str, Any] = {}
        for k, v in obj.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in SENSITIVE_KEYS):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_sensitive_data(v)
        return sanitized
    if isinstance(obj, list):
        return [sanitize_sensitive_data(item) for item in obj]
    return obj


def compute_deterministic_diff(
    previous: Optional[Dict[str, Any]],
    updated: Optional[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Extract only changed keys between previous and updated dictionaries."""
    if not previous or not updated:
        return (
            sanitize_sensitive_data(previous),
            sanitize_sensitive_data(updated),
        )

    all_keys = set(previous.keys()).union(set(updated.keys()))
    diff_prev: Dict[str, Any] = {}
    diff_upd: Dict[str, Any] = {}

    for k in all_keys:
        val_prev = previous.get(k)
        val_upd = updated.get(k)
        if val_prev != val_upd:
            diff_prev[k] = val_prev
            diff_upd[k] = val_upd

    return (
        sanitize_sensitive_data(diff_prev) if diff_prev else None,
        sanitize_sensitive_data(diff_upd) if diff_upd else None,
    )


def calculate_tamper_hash(
    prev_hash: Optional[str],
    timestamp: datetime,
    user_id: Optional[int],
    action: str,
    entity_type: str,
    entity_id: Optional[str],
    previous_values: Optional[Dict[str, Any]],
    updated_values: Optional[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]],
) -> str:
    """Compute SHA-256 tamper-evident hash for audit chain continuity."""
    effective_prev_hash = prev_hash or GENESIS_HASH
    
    # Ensure UTC ISO format string for timestamp consistency
    if timestamp.tzinfo is None:
        ts_str = timestamp.replace(tzinfo=timezone.utc).isoformat()
    else:
        ts_str = timestamp.astimezone(timezone.utc).isoformat()

    diff_payload = {
        "prev": previous_values,
        "upd": updated_values,
        "meta": metadata,
    }
    payload_json = json.dumps(diff_payload, sort_keys=True, default=str)

    hash_source = (
        f"{effective_prev_hash}|{ts_str}|{user_id or 'SYSTEM'}|"
        f"{action}|{entity_type}|{entity_id or 'NONE'}|{payload_json}"
    )
    return hashlib.sha256(hash_source.encode("utf-8")).hexdigest()


async def get_latest_audit_hash(session: AsyncSession) -> Optional[str]:
    """Retrieve the record_hash of the most recently inserted audit log entry."""
    stmt = (
        select(AuditLog.record_hash)
        .order_by(AuditLog.id.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def log_audit_event(
    session: AsyncSession,
    action: str,
    category: Union[AuditCategory, str],
    entity_type: str,
    entity_id: Optional[Union[str, int]] = None,
    user: Optional[User] = None,
    user_id: Optional[int] = None,
    user_role: Optional[str] = None,
    user_email: Optional[str] = None,
    user_name: Optional[str] = None,
    institution_id: Optional[int] = None,
    status: Union[AuditStatus, str] = AuditStatus.SUCCESS,
    previous_values: Optional[Dict[str, Any]] = None,
    updated_values: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    commit: bool = False,
) -> Optional[AuditLog]:
    """Append a cryptographically hashed, sanitized audit log event.
    
    Resilient: logs any internal error and does not crash primary business
    operations unless explicitly rethrown.
    """
    try:
        # Resolve user context if User object provided
        eff_user_id = user_id
        eff_user_role = user_role
        eff_user_email = user_email
        eff_user_name = user_name
        eff_institution_id = institution_id

        if user:
            eff_user_id = user.id
            eff_user_role = user.role.value if hasattr(user.role, "value") else str(user.role)
            eff_user_email = user.email
            eff_user_name = getattr(user, "full_name", None)
            if eff_institution_id is None and user.institution_id is not None:
                eff_institution_id = user.institution_id

        # Sanitize sensitive fields
        clean_prev = sanitize_sensitive_data(previous_values)
        clean_upd = sanitize_sensitive_data(updated_values)
        clean_meta = sanitize_sensitive_data(metadata)

        now_utc = datetime.now(timezone.utc)
        prev_hash = await get_latest_audit_hash(session)
        
        str_entity_id = str(entity_id) if entity_id is not None else None
        cat_str = category.value if hasattr(category, "value") else str(category)
        status_str = status.value if hasattr(status, "value") else str(status)

        record_hash = calculate_tamper_hash(
            prev_hash=prev_hash,
            timestamp=now_utc,
            user_id=eff_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str_entity_id,
            previous_values=clean_prev,
            updated_values=clean_upd,
            metadata=clean_meta,
        )

        audit_entry = AuditLog(
            event_id=str(uuid.uuid4()),
            user_id=eff_user_id,
            user_role=eff_user_role,
            user_email=eff_user_email,
            user_name=eff_user_name,
            institution_id=eff_institution_id,
            category=cat_str,
            action=action,
            entity_type=entity_type,
            entity_id=str_entity_id,
            status=status_str,
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
            previous_values=clean_prev,
            updated_values=clean_upd,
            metadata_=clean_meta,
            prev_hash=prev_hash,
            record_hash=record_hash,
            timestamp=now_utc,
        )

        session.add(audit_entry)
        if commit:
            await session.commit()
            await session.refresh(audit_entry)
        else:
            await session.flush()

        return audit_entry

    except Exception as exc:
        logger.error(
            f"Failed to record audit log for action '{action}' on entity '{entity_type}:{entity_id}': {str(exc)}",
            exc_info=True,
        )
        return None


async def list_audit_logs(
    session: AsyncSession,
    current_user: User,
    category: Optional[str] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    user_id: Optional[int] = None,
    institution_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
) -> AuditLogListResponse:
    """Retrieve filtered, paginated audit logs with multi-tenant RBAC enforcement."""
    # RBAC Enforcement
    if current_user.role not in [UserRole.ADMIN, UserRole.TPO]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "AUDIT_ACCESS_DENIED",
                "message": "Only Administrators and TPO officials are permitted to view audit logs.",
            },
        )

    conditions = []

    # Tenancy scoping: TPOs can strictly view only their own institution's events
    if current_user.role == UserRole.TPO:
        if not current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="TPO account is not associated with an institution.",
            )
        conditions.append(AuditLog.institution_id == current_user.institution_id)
        # Exclude administrative platform modifications from TPO view
        conditions.append(AuditLog.category != AuditCategory.ADMINISTRATION.value)
    elif institution_id:
        # Admin filtering by specific institution
        conditions.append(AuditLog.institution_id == institution_id)

    # Specific query filters
    if category:
        conditions.append(AuditLog.category == category)
    if action:
        conditions.append(AuditLog.action == action)
    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)
    if entity_id:
        conditions.append(AuditLog.entity_id == entity_id)
    if status_filter:
        conditions.append(AuditLog.status == status_filter)
    if user_id:
        conditions.append(AuditLog.user_id == user_id)
    if date_from:
        conditions.append(AuditLog.timestamp >= date_from)
    if date_to:
        conditions.append(AuditLog.timestamp <= date_to)

    # General Search filter
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(
            or_(
                AuditLog.action.ilike(term),
                AuditLog.user_email.ilike(term),
                AuditLog.user_name.ilike(term),
                AuditLog.entity_type.ilike(term),
                AuditLog.entity_id.ilike(term),
                AuditLog.correlation_id.ilike(term),
            )
        )

    where_clause = and_(*conditions) if conditions else True

    # Count total
    count_stmt = select(func.count(AuditLog.id)).where(where_clause)
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one() or 0

    # Pagination calculation
    page = max(1, page)
    limit = max(1, min(100, limit))
    offset = (page - 1) * limit
    total_pages = (total + limit - 1) // limit if total > 0 else 0

    # Fetch items
    items_stmt = (
        select(AuditLog)
        .where(where_clause)
        .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
        .offset(offset)
        .limit(limit)
    )
    items_result = await session.execute(items_stmt)
    logs = items_result.scalars().all()

    items = [
        AuditLogItemResponse(
            id=log.id,
            event_id=log.event_id,
            user_id=log.user_id,
            user_role=log.user_role,
            user_email=log.user_email,
            user_name=log.user_name,
            institution_id=log.institution_id,
            category=log.category,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            status=log.status,
            correlation_id=log.correlation_id,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            previous_values=log.previous_values,
            updated_values=log.updated_values,
            metadata_=log.metadata_,
            prev_hash=log.prev_hash,
            record_hash=log.record_hash,
            timestamp=log.timestamp,
        )
        for log in logs
    ]

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


async def get_audit_log_by_id(
    session: AsyncSession,
    log_id: int,
    current_user: User,
) -> AuditLogItemResponse:
    """Fetch single audit log record with strict institutional access validation."""
    stmt = select(AuditLog).where(AuditLog.id == log_id)
    result = await session.execute(stmt)
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log record not found.",
        )

    # Multi-tenant check
    if current_user.role == UserRole.TPO:
        if log.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to audit records from other institutions is forbidden.",
            )
        if log.category == AuditCategory.ADMINISTRATION.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="TPOs cannot access platform administration audit records.",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden.",
        )

    return AuditLogItemResponse(
        id=log.id,
        event_id=log.event_id,
        user_id=log.user_id,
        user_role=log.user_role,
        user_email=log.user_email,
        user_name=log.user_name,
        institution_id=log.institution_id,
        category=log.category,
        action=log.action,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        status=log.status,
        correlation_id=log.correlation_id,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        previous_values=log.previous_values,
        updated_values=log.updated_values,
        metadata_=log.metadata_,
        prev_hash=log.prev_hash,
        record_hash=log.record_hash,
        timestamp=log.timestamp,
    )


async def get_audit_summary_stats(
    session: AsyncSession,
    current_user: User,
) -> AuditSummaryStats:
    """Compute audit dashboard summary metrics and cryptographic integrity status."""
    conditions = []
    if current_user.role == UserRole.TPO:
        conditions.append(AuditLog.institution_id == current_user.institution_id)
        conditions.append(AuditLog.category != AuditCategory.ADMINISTRATION.value)

    where_clause = and_(*conditions) if conditions else True

    # Total events
    total_q = select(func.count(AuditLog.id)).where(where_clause)
    total_events = (await session.execute(total_q)).scalar_one() or 0

    # Security events (AUTHENTICATION)
    sec_q = select(func.count(AuditLog.id)).where(
        and_(where_clause, AuditLog.category == AuditCategory.AUTHENTICATION.value)
    )
    security_events = (await session.execute(sec_q)).scalar_one() or 0

    # Critical changes (ACADEMIC, RECRUITMENT offers/status)
    crit_q = select(func.count(AuditLog.id)).where(
        and_(
            where_clause,
            or_(
                AuditLog.category == AuditCategory.ACADEMIC.value,
                and_(
                    AuditLog.category == AuditCategory.RECRUITMENT.value,
                    AuditLog.action.in_([
                        "OFFER_RELEASED",
                        "OFFER_ACCEPTED",
                        "OFFER_DECLINED",
                        "APPLICATION_STATUS_TRANSITION",
                    ]),
                ),
            ),
        )
    )
    critical_changes = (await session.execute(crit_q)).scalar_one() or 0

    # Failed operations
    fail_q = select(func.count(AuditLog.id)).where(
        and_(where_clause, AuditLog.status != AuditStatus.SUCCESS.value)
    )
    failed_operations = (await session.execute(fail_q)).scalar_one() or 0

    # Quick verify recent 50 records for integrity status
    verification = await verify_audit_log_integrity(session, limit=50)
    integrity_status = "VERIFIED" if verification.is_valid else "COMPROMISED"

    return AuditSummaryStats(
        total_events=total_events,
        security_events=security_events,
        critical_changes=critical_changes,
        failed_operations=failed_operations,
        integrity_status=integrity_status,
    )


async def verify_audit_log_integrity(
    session: AsyncSession,
    limit: int = 1000,
) -> AuditIntegrityVerificationResponse:
    """Verify cryptographic SHA-256 hash chaining across consecutive audit logs."""
    stmt = (
        select(AuditLog)
        .order_by(AuditLog.id.asc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    records = result.scalars().all()

    if not records:
        return AuditIntegrityVerificationResponse(
            is_valid=True,
            total_checked=0,
            broken_links_count=0,
            invalid_records=[],
            details="Audit log is empty; zero records to verify.",
        )

    expected_prev_hash: Optional[str] = None
    broken_links = 0
    invalid_record_ids: List[int] = []

    for idx, rec in enumerate(records):
        # 1. Verify prev_hash matches prior record's record_hash
        if idx > 0 and rec.prev_hash != expected_prev_hash:
            broken_links += 1
            invalid_record_ids.append(rec.id)
            logger.warning(
                f"Audit hash chain link broken at record id={rec.id}. "
                f"Expected prev_hash='{expected_prev_hash}', got '{rec.prev_hash}'"
            )

        # 2. Recalculate record_hash
        recalculated_hash = calculate_tamper_hash(
            prev_hash=rec.prev_hash,
            timestamp=rec.timestamp,
            user_id=rec.user_id,
            action=rec.action,
            entity_type=rec.entity_type,
            entity_id=rec.entity_id,
            previous_values=rec.previous_values,
            updated_values=rec.updated_values,
            metadata=rec.metadata_,
        )

        if recalculated_hash != rec.record_hash:
            broken_links += 1
            if rec.id not in invalid_record_ids:
                invalid_record_ids.append(rec.id)
            logger.warning(
                f"Audit record content hash mismatch at record id={rec.id}. "
                f"Stored hash='{rec.record_hash}', recalculated='{recalculated_hash}'"
            )

        expected_prev_hash = rec.record_hash

    is_valid = (broken_links == 0)
    details = (
        f"Cryptographic chain verified for {len(records)} audit records: "
        f"{'All hashes match securely.' if is_valid else f'Detected {broken_links} tampered/broken links.'}"
    )

    return AuditIntegrityVerificationResponse(
        is_valid=is_valid,
        total_checked=len(records),
        broken_links_count=broken_links,
        invalid_records=invalid_record_ids,
        details=details,
    )


async def get_audit_categories_taxonomy(
    session: AsyncSession,
) -> AuditCategoriesResponse:
    """Return distinct categories, actions, and entity types currently present in audit logs."""
    cat_stmt = select(AuditLog.category).distinct()
    act_stmt = select(AuditLog.action).distinct()
    ent_stmt = select(AuditLog.entity_type).distinct()

    cats = (await session.execute(cat_stmt)).scalars().all()
    acts = (await session.execute(act_stmt)).scalars().all()
    ents = (await session.execute(ent_stmt)).scalars().all()

    # Prepopulate standard categories if empty
    all_categories = sorted(list(set(list(cats) + [c.value for c in AuditCategory])))
    all_actions = sorted(list(set(acts)))
    all_entities = sorted(list(set(ents)))

    return AuditCategoriesResponse(
        categories=all_categories,
        actions=all_actions,
        entity_types=all_entities,
    )
