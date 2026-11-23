"""Tests for Phase 6 Stage 1: Domain Models and Validation Schemas."""
from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError
from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import configure_mappers

from app.config import get_settings
from app.core.base import Base
from app.models.placement import (
    ApplicationStatus,
    ApplicationStatusHistory,
    DecisionDomain,
    DriveMode,
    DriveStatus,
    Interview,
    InterviewMode,
    InterviewOutcome,
    InterviewStatus,
    JobApplication,
    Notification,
    NotificationCategory,
    PlacementDrive,
    PlacementDriveJob,
    TpoScreeningStatus,
)
from app.schemas.placement import (
    ApplicationStatusHistoryResponse,
    ApplicationWithdrawRequest,
    InterviewCreateRequest,
    InterviewOutcomeRequest,
    InterviewRescheduleRequest,
    InterviewResponse,
    InterviewStudentResponse,
    JobApplicationCreate,
    JobApplicationDetailResponse,
    JobApplicationListResponse,
    JobApplicationRecruiterResponse,
    JobApplicationResponse,
    JobApplicationStudentDetailResponse,
    NotificationResponse,
    NotificationUnreadCountResponse,
    OfferResponseRequest,
    PlacementDriveCreate,
    PlacementDriveDetailResponse,
    PlacementDriveJobAddRequest,
    PlacementDriveJobResponse,
    PlacementDriveResponse,
    PlacementDriveUpdate,
    RecruiterStatusUpdateRequest,
    TpoScreeningUpdateRequest,
)

settings = get_settings()


# =============================================================================
# 1. Enums Verification (9 Enums)
# =============================================================================

def test_phase6_enums_values():
    """Verify all 9 Phase 6 enums and their approved string values."""
    assert [e.value for e in DriveMode] == ["on_campus", "virtual", "hybrid"]
    assert [e.value for e in DriveStatus] == ["draft", "upcoming", "ongoing", "completed", "cancelled"]
    assert [e.value for e in TpoScreeningStatus] == ["bypassed", "pending", "shortlisted", "rejected"]
    assert [e.value for e in ApplicationStatus] == [
        "applied",
        "under_review",
        "shortlisted",
        "interview_scheduled",
        "interviewed",
        "offered",
        "offer_accepted",
        "offer_declined",
        "rejected",
        "withdrawn",
    ]
    assert [e.value for e in DecisionDomain] == ["tpo_screening", "recruitment_lifecycle"]
    assert [e.value for e in InterviewMode] == ["virtual", "in_person"]
    assert [e.value for e in InterviewStatus] == ["scheduled", "completed", "cancelled", "no_show"]
    assert [e.value for e in InterviewOutcome] == ["pending", "passed", "failed", "on_hold"]
    assert [e.value for e in NotificationCategory] == [
        "application_update",
        "interview_scheduled",
        "interview_update",
        "drive_announcement",
        "offer_extended",
        "action_required",
    ]


# =============================================================================
# 2. Database Models & Schema Scoping (6 Tables)
# =============================================================================

def test_models_registered_in_schema():
    """Ensure all 6 Phase 6 models are registered under settings.DB_SCHEMA."""
    schema = settings.DB_SCHEMA
    expected_tables = {
        f"{schema}.placement_drives",
        f"{schema}.placement_drive_jobs",
        f"{schema}.job_applications",
        f"{schema}.application_status_history",
        f"{schema}.interviews",
        f"{schema}.notifications",
    }
    registered_tables = set(Base.metadata.tables.keys())
    for tbl in expected_tables:
        assert tbl in registered_tables, f"Missing table {tbl} in Base.metadata"


def test_drive_model_structure():
    """Verify PlacementDrive table structure, columns, and constraints."""
    table = Base.metadata.tables[f"{settings.DB_SCHEMA}.placement_drives"]
    col_names = {c.name for c in table.columns}
    assert {
        "id",
        "institution_id",
        "created_by_user_id",
        "name",
        "academic_year",
        "target_graduation_year",
        "registration_start_date",
        "registration_end_date",
        "drive_mode",
        "status",
        "description",
        "guidelines",
        "is_active",
        "created_at",
        "updated_at",
    }.issubset(col_names)

    # Check constraint
    chk_names = {c.name for c in table.constraints if isinstance(c, CheckConstraint)}
    assert "chk_drive_registration_dates" in chk_names


def test_drive_job_model_structure():
    """Verify PlacementDriveJob table structure, columns, and constraints."""
    table = Base.metadata.tables[f"{settings.DB_SCHEMA}.placement_drive_jobs"]
    col_names = {c.name for c in table.columns}
    assert {
        "id",
        "drive_id",
        "job_id",
        "is_active",
        "removed_at",
        "created_at",
        "updated_at",
    }.issubset(col_names)

    # Ensure removed_by_user_id is NOT in placement_drive_jobs
    assert "removed_by_user_id" not in col_names

    # Unique constraint (drive_id, job_id)
    uq_names = {c.name for c in table.constraints if isinstance(c, UniqueConstraint)}
    assert "uq_drive_jobs_drive_job" in uq_names

    # Check constraint
    chk_names = {c.name for c in table.constraints if isinstance(c, CheckConstraint)}
    assert "chk_drive_job_removed_at" in chk_names


def test_job_application_composite_foreign_key_and_constraints():
    """Verify JobApplication composite foreign key, unique constraints, and check constraints."""
    table = Base.metadata.tables[f"{settings.DB_SCHEMA}.job_applications"]
    col_names = {c.name for c in table.columns}
    assert {
        "id",
        "job_id",
        "student_id",
        "resume_id",
        "drive_id",
        "tpo_screening_status",
        "tpo_screened_by_user_id",
        "tpo_screened_at",
        "tpo_feedback",
        "current_status",
        "recruiter_decision_at",
        "recruiter_feedback_notes",
        "compatibility_score_at_application",
        "cover_letter",
        "withdrawn_at",
        "withdrawal_reason",
        "created_at",
        "updated_at",
    }.issubset(col_names)

    # Composite foreign key
    composite_fks = [
        fk for fk in table.constraints
        if isinstance(fk, ForeignKeyConstraint) and len(fk.columns) == 2
    ]
    assert len(composite_fks) == 1
    comp_fk = composite_fks[0]
    assert comp_fk.name == "fk_job_applications_drive_job"
    assert [c.name for c in comp_fk.columns] == ["drive_id", "job_id"]
    assert comp_fk.ondelete == "RESTRICT"

    # Unique constraint (job_id, student_id)
    uq_names = {c.name for c in table.constraints if isinstance(c, UniqueConstraint)}
    assert "uq_job_applications_job_student" in uq_names

    # Check constraints (4 approved check constraints)
    chk_names = {c.name for c in table.constraints if isinstance(c, CheckConstraint)}
    assert "chk_app_drive_tpo_screening" in chk_names
    assert "chk_app_tpo_screening_audit" in chk_names
    assert "chk_app_compatibility_score" in chk_names
    assert "chk_app_withdrawn_state" in chk_names


def test_application_status_history_structure():
    """Verify ApplicationStatusHistory table structure, created_at timestamp, and RESTRICT deletion."""
    table = Base.metadata.tables[f"{settings.DB_SCHEMA}.application_status_history"]
    col_names = {c.name for c in table.columns}
    assert {
        "id",
        "application_id",
        "changed_by_user_id",
        "decision_domain",
        "from_status",
        "to_status",
        "notes",
        "created_at",
    }.issubset(col_names)

    # Timestamp standardization: must be created_at, NOT changed_at
    assert "created_at" in col_names
    assert "changed_at" not in col_names

    # Deletion behavior: ON DELETE RESTRICT
    fks = {fk.parent.name: fk for fk in table.foreign_keys}
    assert fks["application_id"].ondelete == "RESTRICT"
    assert fks["changed_by_user_id"].ondelete == "RESTRICT"


def test_interview_model_structure():
    """Verify Interview table structure, created_by_user_id, unique constraints, and check constraints."""
    table = Base.metadata.tables[f"{settings.DB_SCHEMA}.interviews"]
    col_names = {c.name for c in table.columns}
    assert {
        "id",
        "application_id",
        "round_number",
        "round_title",
        "interview_mode",
        "meeting_link",
        "location",
        "scheduled_start_time",
        "duration_minutes",
        "interviewer_names",
        "status",
        "outcome",
        "feedback_notes",
        "created_by_user_id",
        "cancellation_reason",
        "created_at",
        "updated_at",
    }.issubset(col_names)

    # Ensure rescheduled_from_id is NOT in interviews
    assert "rescheduled_from_id" not in col_names

    # Deletion behavior: ON DELETE RESTRICT
    fks = {fk.parent.name: fk for fk in table.foreign_keys}
    assert fks["application_id"].ondelete == "RESTRICT"
    assert fks["created_by_user_id"].ondelete == "RESTRICT"

    # Unique constraint (application_id, round_number)
    uq_names = {c.name for c in table.constraints if isinstance(c, UniqueConstraint)}
    assert "uq_interviews_app_round" in uq_names

    # Check constraints
    chk_names = {c.name for c in table.constraints if isinstance(c, CheckConstraint)}
    assert "chk_interview_round_positive" in chk_names
    assert "chk_interview_duration_range" in chk_names


def test_notification_model_structure():
    """Verify complete Notification table structure, foreign keys, and partial unique index."""
    table = Base.metadata.tables[f"{settings.DB_SCHEMA}.notifications"]
    col_names = {c.name for c in table.columns}
    assert {
        "id",
        "recipient_user_id",
        "sender_user_id",
        "category",
        "title",
        "message",
        "related_application_id",
        "related_drive_id",
        "related_interview_id",
        "is_read",
        "read_at",
        "idempotency_key",
        "created_at",
    }.issubset(col_names)
    assert "updated_at" not in col_names

    # Verify FK deletion rules for notifications:
    fks = {fk.parent.name: fk for fk in table.foreign_keys}
    assert fks["recipient_user_id"].ondelete == "CASCADE"
    assert fks["sender_user_id"].ondelete == "SET NULL"
    assert fks["related_application_id"].ondelete == "SET NULL"
    assert fks["related_drive_id"].ondelete == "SET NULL"
    assert fks["related_interview_id"].ondelete == "SET NULL"

    # Partial unique index on recipient_user_id and idempotency_key
    idx_names = {ix.name for ix in table.indexes}
    assert "uq_notifications_recipient_idempotency" in idx_names


# =============================================================================
# 3. Exact 19 Foreign Keys & Constraints Inventory Audit
# =============================================================================

def test_exact_19_foreign_keys_audit():
    """Audit the complete list of 19 foreign keys across all Phase 6 tables."""
    schema = settings.DB_SCHEMA
    phase6_tables = [
        f"{schema}.placement_drives",
        f"{schema}.placement_drive_jobs",
        f"{schema}.job_applications",
        f"{schema}.application_status_history",
        f"{schema}.interviews",
        f"{schema}.notifications",
    ]

    total_fks = 0
    fk_details = []
    for tname in phase6_tables:
        t = Base.metadata.tables[tname]
        for c in t.constraints:
            if isinstance(c, ForeignKeyConstraint):
                total_fks += 1
                fk_details.append({
                    "table": tname,
                    "columns": [col.name for col in c.columns],
                    "target": [el.target_fullname for el in c.elements],
                    "ondelete": c.ondelete,
                })

    assert total_fks == 19, f"Expected 19 foreign keys across Phase 6 tables, found {total_fks}: {fk_details}"


def test_exact_4_unique_constraints_audit():
    """Audit the 4 unique constraints/indexes across Phase 6."""
    schema = settings.DB_SCHEMA
    table_names = [
        f"{schema}.placement_drives",
        f"{schema}.placement_drive_jobs",
        f"{schema}.job_applications",
        f"{schema}.application_status_history",
        f"{schema}.interviews",
        f"{schema}.notifications",
    ]

    unique_items = []
    for tname in table_names:
        t = Base.metadata.tables[tname]
        for c in t.constraints:
            if isinstance(c, UniqueConstraint):
                unique_items.append(c.name)
        for ix in t.indexes:
            if ix.unique and ix.name.startswith("uq_"):
                unique_items.append(ix.name)

    expected_uniques = {
        "uq_drive_jobs_drive_job",
        "uq_job_applications_job_student",
        "uq_interviews_app_round",
        "uq_notifications_recipient_idempotency",
    }
    assert set(unique_items) == expected_uniques


def test_exact_8_check_constraints_audit():
    """Audit the 8 CHECK constraints across Phase 6."""
    schema = settings.DB_SCHEMA
    table_names = [
        f"{schema}.placement_drives",
        f"{schema}.placement_drive_jobs",
        f"{schema}.job_applications",
        f"{schema}.application_status_history",
        f"{schema}.interviews",
        f"{schema}.notifications",
    ]

    check_names = set()
    for tname in table_names:
        t = Base.metadata.tables[tname]
        for c in t.constraints:
            if isinstance(c, CheckConstraint):
                check_names.add(c.name)

    expected_checks = {
        "chk_drive_registration_dates",
        "chk_drive_job_removed_at",
        "chk_app_drive_tpo_screening",
        "chk_app_tpo_screening_audit",
        "chk_app_compatibility_score",
        "chk_app_withdrawn_state",
        "chk_interview_round_positive",
        "chk_interview_duration_range",
    }
    assert check_names == expected_checks


def test_orm_cascades_do_not_silently_delete_history_or_interviews():
    """
    Ensure ORM relationships on JobApplication and PlacementDrive do NOT contain
    cascade='all, delete-orphan' that could bypass ON DELETE RESTRICT database rules.
    """
    configure_mappers()

    # JobApplication relationships must not have delete-orphan cascades
    app_mapper = JobApplication.__mapper__
    status_history_rel = app_mapper.relationships["status_history"]
    interviews_rel = app_mapper.relationships["interviews"]
    assert not status_history_rel.cascade.delete_orphan, "status_history must not cascade delete-orphan"
    assert not interviews_rel.cascade.delete_orphan, "interviews must not cascade delete-orphan"

    # PlacementDrive relationships must not cascade delete drive_jobs
    drive_mapper = PlacementDrive.__mapper__
    drive_jobs_rel = drive_mapper.relationships["drive_jobs"]
    assert not drive_jobs_rel.cascade.delete_orphan, "drive_jobs must not cascade delete-orphan"


# =============================================================================
# 4. Pydantic Validation Schemas & Privacy Controls
# =============================================================================

def test_placement_drive_create_valid():
    """Valid drive creation passes validation."""
    now = datetime.now(timezone.utc)
    drive_data = {
        "name": "Annual Placement Drive 2026",
        "academic_year": "2025-2026",
        "target_graduation_year": 2026,
        "registration_start_date": now + timedelta(days=1),
        "registration_end_date": now + timedelta(days=10),
        "drive_mode": DriveMode.ON_CAMPUS,
        "description": "Premier engineering placement drive",
    }
    schema = PlacementDriveCreate(**drive_data)
    assert schema.name == "Annual Placement Drive 2026"
    assert schema.drive_mode == DriveMode.ON_CAMPUS


def test_placement_drive_create_invalid_dates():
    """Drive registration start date >= end date must fail validation."""
    now = datetime.now(timezone.utc)
    drive_data = {
        "name": "Annual Placement Drive 2026",
        "academic_year": "2025-2026",
        "target_graduation_year": 2026,
        "registration_start_date": now + timedelta(days=10),
        "registration_end_date": now + timedelta(days=2),  # invalid: start > end
    }
    with pytest.raises(ValidationError) as exc:
        PlacementDriveCreate(**drive_data)
    assert "registration_start_date must be strictly earlier than registration_end_date" in str(exc.value)


def test_placement_drive_update_date_validation():
    """Drive update validating start < end when both provided."""
    now = datetime.now(timezone.utc)
    up = PlacementDriveUpdate(
        registration_start_date=now + timedelta(days=1),
        registration_end_date=now + timedelta(days=5),
    )
    assert up.registration_start_date < up.registration_end_date

    with pytest.raises(ValidationError):
        PlacementDriveUpdate(
            registration_start_date=now + timedelta(days=5),
            registration_end_date=now + timedelta(days=1),
        )


def test_job_application_create_schema():
    """Verify JobApplicationCreate request schema."""
    req = JobApplicationCreate(
        job_id=10,
        resume_id=5,
        drive_id=2,
        cover_letter="I am excited to apply for this software engineer position.",
    )
    assert req.job_id == 10
    assert req.resume_id == 5
    assert req.drive_id == 2
    assert "excited to apply" in req.cover_letter


def test_application_status_history_response_created_at():
    """Verify history schema uses standardized created_at timestamp."""
    now = datetime.now(timezone.utc)
    resp = ApplicationStatusHistoryResponse(
        id=1,
        application_id=10,
        changed_by_user_id=2,
        created_at=now,
        decision_domain=DecisionDomain.TPO_SCREENING,
        from_status="pending",
        to_status="shortlisted",
        notes="Meets academic eligibility",
    )
    assert resp.created_at == now
    assert resp.changed_by_user_id == 2


def test_tpo_screening_update_validation():
    """TPO screening status must be shortlisted or rejected."""
    req = TpoScreeningUpdateRequest(status=TpoScreeningStatus.SHORTLISTED, feedback="Strong academic record")
    assert req.status == TpoScreeningStatus.SHORTLISTED

    req = TpoScreeningUpdateRequest(status=TpoScreeningStatus.REJECTED, feedback="Does not meet department requirements")
    assert req.status == TpoScreeningStatus.REJECTED

    with pytest.raises(ValidationError) as exc:
        TpoScreeningUpdateRequest(status=TpoScreeningStatus.PENDING)
    assert "TPO screening decision must be either 'shortlisted' or 'rejected'" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        TpoScreeningUpdateRequest(status=TpoScreeningStatus.BYPASSED)
    assert "TPO screening decision must be either 'shortlisted' or 'rejected'" in str(exc.value)


def test_recruiter_status_update_schema():
    """Verify RecruiterStatusUpdateRequest."""
    req = RecruiterStatusUpdateRequest(
        status=ApplicationStatus.SHORTLISTED,
        feedback_notes="Impressive portfolio and coding challenge score",
    )
    assert req.status == ApplicationStatus.SHORTLISTED
    assert req.feedback_notes == "Impressive portfolio and coding challenge score"


def test_application_withdraw_request():
    """Withdrawal reason must have at least 5 characters."""
    req = ApplicationWithdrawRequest(reason="Accepted offer elsewhere")
    assert req.reason == "Accepted offer elsewhere"

    with pytest.raises(ValidationError):
        ApplicationWithdrawRequest(reason="no")


def test_offer_response_request():
    """Verify OfferResponseRequest."""
    accept = OfferResponseRequest(accept=True, notes="Excited to join!")
    assert accept.accept is True

    decline = OfferResponseRequest(accept=False, notes="Pursuing higher education")
    assert decline.accept is False


def test_interview_create_request_validation():
    """Verify InterviewCreateRequest constraints."""
    now = datetime.now(timezone.utc)
    req = InterviewCreateRequest(
        round_number=1,
        round_title="Technical Round 1",
        interview_mode=InterviewMode.VIRTUAL,
        meeting_link="https://meet.google.com/abc-defg-hij",
        scheduled_start_time=now + timedelta(days=2),
        duration_minutes=60,
        interviewer_names="Jane Doe, Principal Engineer",
    )
    assert req.round_number == 1
    assert req.duration_minutes == 60

    with pytest.raises(ValidationError):
        InterviewCreateRequest(
            round_number=0,
            round_title="Round 0",
            scheduled_start_time=now + timedelta(days=2),
        )

    with pytest.raises(ValidationError):
        InterviewCreateRequest(
            round_number=1,
            round_title="Too short",
            scheduled_start_time=now + timedelta(days=2),
            duration_minutes=10,
        )


def test_interview_reschedule_request():
    """Verify InterviewRescheduleRequest constraints."""
    now = datetime.now(timezone.utc)
    req = InterviewRescheduleRequest(
        scheduled_start_time=now + timedelta(days=3),
        reason="Interviewer travel conflict",
    )
    assert req.reason == "Interviewer travel conflict"

    with pytest.raises(ValidationError):
        InterviewRescheduleRequest(
            scheduled_start_time=now + timedelta(days=3),
            reason="busy",
        )


def test_interview_outcome_request():
    """Verify InterviewOutcomeRequest."""
    req = InterviewOutcomeRequest(
        outcome=InterviewOutcome.PASSED,
        feedback_notes="Strong algorithms and system design performance",
    )
    assert req.outcome == InterviewOutcome.PASSED


def test_student_interview_response_redaction():
    """Verify InterviewStudentResponse does not expose recruiter feedback_notes or internal IDs."""
    now = datetime.now(timezone.utc)
    resp_data = {
        "id": 1,
        "application_id": 5,
        "round_number": 1,
        "round_title": "Technical Round 1",
        "interview_mode": InterviewMode.VIRTUAL,
        "meeting_link": "https://meet.google.com/abc-xyz",
        "location": None,
        "scheduled_start_time": now + timedelta(days=1),
        "duration_minutes": 45,
        "interviewer_names": "Alex Smith",
        "status": InterviewStatus.SCHEDULED,
        "outcome": InterviewOutcome.PENDING,
        "cancellation_reason": None,
        "created_at": now,
        "updated_at": now,
    }
    student_view = InterviewStudentResponse(**resp_data)
    assert not hasattr(student_view, "feedback_notes")
    assert not hasattr(student_view, "created_by_user_id")
    assert student_view.round_title == "Technical Round 1"


def test_job_application_response_recruiter_vs_base():
    """Verify JobApplicationResponse does not expose recruiter notes, while RecruiterResponse does."""
    now = datetime.now(timezone.utc)
    base_data = {
        "id": 1,
        "job_id": 10,
        "student_id": 20,
        "resume_id": 30,
        "drive_id": 5,
        "tpo_screening_status": TpoScreeningStatus.SHORTLISTED,
        "current_status": ApplicationStatus.UNDER_REVIEW,
        "compatibility_score_at_application": 87.5,
        "cover_letter": "I would love to work with you",
        "created_at": now,
        "updated_at": now,
    }
    base_resp = JobApplicationResponse(**base_data)
    assert not hasattr(base_resp, "recruiter_feedback_notes")

    recruiter_data = {
        **base_data,
        "recruiter_feedback_notes": "Internal evaluation note: candidate has high math aptitude",
    }
    recruiter_resp = JobApplicationRecruiterResponse(**recruiter_data)
    assert recruiter_resp.recruiter_feedback_notes == "Internal evaluation note: candidate has high math aptitude"


def test_notification_schemas_complete_fields():
    """Verify complete notification schema with sender and entity reference IDs."""
    now = datetime.now(timezone.utc)
    notif = NotificationResponse(
        id=1,
        recipient_user_id=12,
        sender_user_id=2,
        category=NotificationCategory.INTERVIEW_SCHEDULED,
        title="Technical Interview Scheduled",
        message="Your Round 1 interview has been scheduled for tomorrow.",
        related_application_id=5,
        related_drive_id=1,
        related_interview_id=3,
        link_url="/applications/5",
        is_read=False,
        read_at=None,
        idempotency_key="interview-sched-5-1",
        created_at=now,
    )
    assert notif.id == 1
    assert notif.recipient_user_id == 12
    assert notif.sender_user_id == 2
    assert notif.related_application_id == 5
    assert notif.related_drive_id == 1
    assert notif.related_interview_id == 3
    assert notif.idempotency_key == "interview-sched-5-1"
    assert notif.category == NotificationCategory.INTERVIEW_SCHEDULED
    assert notif.is_read is False

    unread = NotificationUnreadCountResponse(unread_count=3)
    assert unread.unread_count == 3
