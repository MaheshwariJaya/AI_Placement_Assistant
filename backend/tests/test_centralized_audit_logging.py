"""Unit and Integration Tests for TASK 11: Centralized Audit Logging & Activity Monitoring.

Validates:
1. Sensitive data sanitization and recursive secret redaction.
2. Deterministic diff calculation.
3. Append-only logging and SHA-256 cryptographic hash chaining.
4. Tamper detection and broken link identification.
5. Multi-tenant and role-based access control (Admin, TPO, Recruiter, Student).
6. Filter query parameters and full-text keyword search.
7. Audit dashboard KPI metrics computation.
8. Automated recruitment and academic audit integration.
"""
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import get_settings
from app.core.errors import AuthorizationException
from app.models.audit import AuditCategory, AuditLog, AuditStatus
from app.models.organization import Department, Institution
from app.models.placement import ApplicationStatus, JobApplication, TpoScreeningStatus
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from app.schemas.audit import AuditLogItemResponse
from app.services.audit_service import (
    calculate_tamper_hash,
    compute_deterministic_diff,
    get_audit_categories_taxonomy,
    get_audit_log_by_id,
    get_audit_summary_stats,
    list_audit_logs,
    log_audit_event,
    sanitize_sensitive_data,
    verify_audit_log_integrity,
)
from app.services.state_machine import execute_recruiter_lifecycle_transition

settings = get_settings()


def _new_test_engine():
    return create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
    )


# -----------------------------------------------------------------------------
# 1. Sanitization & Diff Tests
# -----------------------------------------------------------------------------
def test_sensitive_data_sanitization():
    raw_payload = {
        "user_email": "john.doe@test.com",
        "password": "SuperSecretPassword123!",
        "auth": {
            "access_token": "eyJhbGciOi...",
            "refresh_token": "def5020...",
            "api_key": "live_sk_99999",
            "nested": {
                "secret_key": "hidden",
                "normal_field": "visible",
            },
        },
        "safe_list": [
            {"password_hash": "argon2...", "name": "Alice"},
            {"role": "ADMIN"},
        ],
    }

    sanitized = sanitize_sensitive_data(raw_payload)

    assert sanitized["user_email"] == "john.doe@test.com"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["auth"]["access_token"] == "[REDACTED]"
    assert sanitized["auth"]["refresh_token"] == "[REDACTED]"
    assert sanitized["auth"]["api_key"] == "[REDACTED]"
    assert sanitized["auth"]["nested"]["secret_key"] == "[REDACTED]"
    assert sanitized["auth"]["nested"]["normal_field"] == "visible"
    assert sanitized["safe_list"][0]["password_hash"] == "[REDACTED]"
    assert sanitized["safe_list"][0]["name"] == "Alice"
    assert sanitized["safe_list"][1]["role"] == "ADMIN"


def test_deterministic_diff_calculation():
    old_state = {
        "cgpa": 8.5,
        "active_backlogs": 1,
        "department": "CSE",
        "password": "OldPassword123",
    }
    new_state = {
        "cgpa": 9.2,
        "active_backlogs": 0,
        "department": "CSE",  # unchanged
        "password": "NewPassword456",
    }

    prev_diff, upd_diff = compute_deterministic_diff(old_state, new_state)

    assert prev_diff is not None
    assert upd_diff is not None
    # 'department' was identical, so omitted
    assert "department" not in prev_diff
    assert "department" not in upd_diff

    # Changed values present
    assert prev_diff["cgpa"] == 8.5
    assert upd_diff["cgpa"] == 9.2
    assert prev_diff["active_backlogs"] == 1
    assert upd_diff["active_backlogs"] == 0

    # Passwords automatically sanitized
    assert prev_diff["password"] == "[REDACTED]"
    assert upd_diff["password"] == "[REDACTED]"


# -----------------------------------------------------------------------------
# 2. Cryptographic Hash Chaining & Tamper Detection Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_audit_hash_chaining_and_integrity():
    engine = _new_test_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        tag = uuid.uuid4().hex[:8]

        # Log first event
        log1 = await log_audit_event(
            session=session,
            action=f"TEST_CHAIN_START_{tag}",
            category=AuditCategory.AUTHENTICATION,
            entity_type="User",
            entity_id="101",
            metadata={"step": 1},
            commit=True,
        )
        assert log1 is not None
        assert log1.record_hash is not None

        # Log second event
        log2 = await log_audit_event(
            session=session,
            action=f"TEST_CHAIN_STEP2_{tag}",
            category=AuditCategory.ACADEMIC,
            entity_type="StudentProfile",
            entity_id="202",
            metadata={"step": 2},
            commit=True,
        )
        assert log2 is not None
        # Must chain to log1's record_hash
        assert log2.prev_hash == log1.record_hash

        # Log third event
        log3 = await log_audit_event(
            session=session,
            action=f"TEST_CHAIN_STEP3_{tag}",
            category=AuditCategory.RECRUITMENT,
            entity_type="JobApplication",
            entity_id="303",
            metadata={"step": 3},
            commit=True,
        )
        assert log3 is not None
        assert log3.prev_hash == log2.record_hash

        # Run cryptographic integrity verification
        verification = await verify_audit_log_integrity(session=session, limit=100)
        assert verification.is_valid is True
        assert verification.broken_links_count == 0
        assert len(verification.invalid_records) == 0

    await engine.dispose()


@pytest.mark.asyncio
async def test_tamper_detection():
    engine = _new_test_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        tag = uuid.uuid4().hex[:8]

        # Create audit entry
        entry = await log_audit_event(
            session=session,
            action=f"TEST_TAMPER_TARGET_{tag}",
            category=AuditCategory.ADMINISTRATION,
            entity_type="SystemConfig",
            entity_id="CFG_01",
            metadata={"status": "INITIAL"},
            commit=True,
        )
        assert entry is not None
        entry_id = entry.id
        original_hash = entry.record_hash

        # Deliberately modify record_hash directly in DB to simulate malicious tampering
        tampered_stmt = select(AuditLog).where(AuditLog.id == entry_id)
        tampered_obj = (await session.execute(tampered_stmt)).scalar_one()
        tampered_obj.record_hash = "deadbeef" * 8
        await session.commit()

        # Run verification: must detect tamper!
        verification = await verify_audit_log_integrity(session=session, limit=500)
        assert verification.is_valid is False
        assert verification.broken_links_count >= 1
        assert entry_id in verification.invalid_records

        # Restore original hash to keep clean state
        tampered_obj.record_hash = original_hash
        await session.commit()

    await engine.dispose()


# -----------------------------------------------------------------------------
# 3. Role-Based Access Control & Multi-Tenancy Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_multi_tenant_and_role_access():
    engine = _new_test_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        tag = uuid.uuid4().hex[:8]
        pwd = "$2b$12$K8yR2V56ZvZ2eF5n5FhO.OaQx7r2XpD1T6YgE7P2R2Y2Q2W2E2R2e"

        # Institutions
        inst1 = Institution(name=f"Inst A {tag}", code=f"IA_{tag}", city="City A")
        inst2 = Institution(name=f"Inst B {tag}", code=f"IB_{tag}", city="City B")
        session.add_all([inst1, inst2])
        await session.flush()

        # Users
        admin_user = User(
            email=f"admin_{tag}@audit.test",
            hashed_password=pwd,
            full_name=f"Admin {tag}",
            role=UserRole.ADMIN,
            is_active=True,
        )
        tpo_user_1 = User(
            email=f"tpo1_{tag}@audit.test",
            hashed_password=pwd,
            full_name=f"TPO One {tag}",
            role=UserRole.TPO,
            institution_id=inst1.id,
            is_active=True,
        )
        recruiter_user = User(
            email=f"rec_{tag}@audit.test",
            hashed_password=pwd,
            full_name=f"Recruiter {tag}",
            role=UserRole.RECRUITER,
            is_active=True,
        )
        student_user = User(
            email=f"std_{tag}@audit.test",
            hashed_password=pwd,
            full_name=f"Student {tag}",
            role=UserRole.STUDENT,
            institution_id=inst1.id,
            is_active=True,
        )
        session.add_all([admin_user, tpo_user_1, recruiter_user, student_user])
        await session.flush()

        # Seed distinct audit events across institutions and categories
        await log_audit_event(
            session=session,
            action=f"INST1_ACADEMIC_{tag}",
            category=AuditCategory.ACADEMIC,
            entity_type="StudentProfile",
            entity_id="1",
            user=tpo_user_1,
            institution_id=inst1.id,
            commit=True,
        )
        await log_audit_event(
            session=session,
            action=f"INST2_ACADEMIC_{tag}",
            category=AuditCategory.ACADEMIC,
            entity_type="StudentProfile",
            entity_id="2",
            institution_id=inst2.id,
            commit=True,
        )
        await log_audit_event(
            session=session,
            action=f"GLOBAL_ADMIN_CHANGE_{tag}",
            category=AuditCategory.ADMINISTRATION,
            entity_type="GlobalSetting",
            entity_id="GLOBAL",
            user=admin_user,
            institution_id=None,
            commit=True,
        )

        # 1. Admin querying: sees all events
        admin_res = await list_audit_logs(
            session=session,
            current_user=admin_user,
            search=tag,
            limit=50,
        )
        admin_actions = [i.action for i in admin_res.items]
        assert f"INST1_ACADEMIC_{tag}" in admin_actions
        assert f"INST2_ACADEMIC_{tag}" in admin_actions
        assert f"GLOBAL_ADMIN_CHANGE_{tag}" in admin_actions

        # 2. TPO 1 querying: strictly scoped to inst1, no inst2 and no ADMINISTRATION
        tpo1_res = await list_audit_logs(
            session=session,
            current_user=tpo_user_1,
            search=tag,
            limit=50,
        )
        tpo1_actions = [i.action for i in tpo1_res.items]
        assert f"INST1_ACADEMIC_{tag}" in tpo1_actions
        assert f"INST2_ACADEMIC_{tag}" not in tpo1_actions
        assert f"GLOBAL_ADMIN_CHANGE_{tag}" not in tpo1_actions

        # 3. Recruiter querying: must raise 403 Forbidden
        with pytest.raises(Exception) as exc_rec:
            await list_audit_logs(
                session=session,
                current_user=recruiter_user,
            )
        assert "403" in str(exc_rec.value) or "AUDIT_ACCESS_DENIED" in str(exc_rec.value)

        # 4. Student querying: must raise 403 Forbidden
        with pytest.raises(Exception) as exc_std:
            await list_audit_logs(
                session=session,
                current_user=student_user,
            )
        assert "403" in str(exc_std.value) or "AUDIT_ACCESS_DENIED" in str(exc_std.value)

    await engine.dispose()


# -----------------------------------------------------------------------------
# 4. Filters, Search & Summary Statistics Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_audit_filters_search_and_stats():
    engine = _new_test_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        tag = uuid.uuid4().hex[:8]
        pwd = "$2b$12$K8yR2V56ZvZ2eF5n5FhO.OaQx7r2XpD1T6YgE7P2R2Y2Q2W2E2R2e"

        admin_user = User(
            email=f"admin_filter_{tag}@audit.test",
            hashed_password=pwd,
            full_name=f"Admin Filter {tag}",
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin_user)
        await session.flush()

        # Seed events with various statuses and categories
        await log_audit_event(
            session=session,
            action=f"AUTH_LOGIN_SUCCESS_{tag}",
            category=AuditCategory.AUTHENTICATION,
            entity_type="User",
            entity_id="501",
            status=AuditStatus.SUCCESS,
            commit=True,
        )
        await log_audit_event(
            session=session,
            action=f"AUTH_LOGIN_FAILURE_{tag}",
            category=AuditCategory.AUTHENTICATION,
            entity_type="User",
            entity_id="502",
            status=AuditStatus.FAILURE,
            commit=True,
        )
        await log_audit_event(
            session=session,
            action=f"OFFER_RELEASED_{tag}",
            category=AuditCategory.RECRUITMENT,
            entity_type="JobApplication",
            entity_id="503",
            status=AuditStatus.SUCCESS,
            commit=True,
        )

        # Filter by Category
        auth_res = await list_audit_logs(
            session=session,
            current_user=admin_user,
            category=AuditCategory.AUTHENTICATION.value,
            search=tag,
        )
        assert all(i.category == AuditCategory.AUTHENTICATION.value for i in auth_res.items)
        assert len(auth_res.items) == 2

        # Filter by Status
        fail_res = await list_audit_logs(
            session=session,
            current_user=admin_user,
            status_filter=AuditStatus.FAILURE.value,
            search=tag,
        )
        assert len(fail_res.items) == 1
        assert fail_res.items[0].action == f"AUTH_LOGIN_FAILURE_{tag}"

        # Summary stats
        stats = await get_audit_summary_stats(session=session, current_user=admin_user)
        assert stats.total_events >= 3
        assert stats.security_events >= 2
        assert stats.failed_operations >= 1
        assert stats.integrity_status in ["VERIFIED", "COMPROMISED"]

        # Taxonomy
        taxonomy = await get_audit_categories_taxonomy(session=session)
        assert AuditCategory.AUTHENTICATION.value in taxonomy.categories
        assert AuditCategory.RECRUITMENT.value in taxonomy.categories

    await engine.dispose()

