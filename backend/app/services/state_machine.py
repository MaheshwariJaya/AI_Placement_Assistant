"""State machine enforcing TPO screening and recruiter recruitment pipeline lifecycles."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppException
from app.models.company import RecruiterProfile
from app.models.job import Job
from app.models.placement import (
    ApplicationStatus,
    ApplicationStatusHistory,
    DecisionDomain,
    JobApplication,
    NotificationCategory,
    TpoScreeningStatus,
)
from app.services.notification_service import create_notification
from app.models.audit import AuditCategory, AuditStatus
from app.services.audit_service import log_audit_event


class InvalidStateTransitionError(AppException):
    def __init__(self, message: str, code: str = "INVALID_STATE_TRANSITION", details: Optional[dict] = None):
        super().__init__(message=message, status_code=400, code=code, details=details or {})


# =============================================================================
# Transition Tables
# =============================================================================

# Valid transitions within the TPO screening domain
VALID_TPO_SCREENING_TRANSITIONS = {
    TpoScreeningStatus.PENDING: {TpoScreeningStatus.SHORTLISTED, TpoScreeningStatus.REJECTED},
    TpoScreeningStatus.SHORTLISTED: {TpoScreeningStatus.REJECTED},  # Late TPO rejection
    TpoScreeningStatus.REJECTED: set(),  # Terminal
    TpoScreeningStatus.BYPASSED: set(),  # Direct applications are permanently bypassed
}

# Valid transitions within the Recruiter selection lifecycle domain
VALID_RECRUITER_TRANSITIONS = {
    ApplicationStatus.APPLIED: {
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.SHORTLISTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.UNDER_REVIEW: {
        ApplicationStatus.SHORTLISTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.SHORTLISTED: {
        ApplicationStatus.INTERVIEW_SCHEDULED,
        ApplicationStatus.OFFERED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.INTERVIEW_SCHEDULED: {
        ApplicationStatus.INTERVIEWED,
        ApplicationStatus.SHORTLISTED,  # Round cancelled reverting to shortlisted
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.INTERVIEWED: {
        ApplicationStatus.INTERVIEW_SCHEDULED,  # Next round
        ApplicationStatus.OFFERED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.OFFERED: {
        ApplicationStatus.OFFER_ACCEPTED,
        ApplicationStatus.OFFER_DECLINED,
        ApplicationStatus.REJECTED,  # Rescinded
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.OFFER_ACCEPTED: {
        ApplicationStatus.WITHDRAWN,  # Exceptional pre-joining withdrawal
    },
    ApplicationStatus.OFFER_DECLINED: set(),
    ApplicationStatus.REJECTED: set(),
    ApplicationStatus.WITHDRAWN: set(),
}


# =============================================================================
# Validation Functions
# =============================================================================

def validate_tpo_screening_transition(
    current_status: TpoScreeningStatus,
    target_status: TpoScreeningStatus,
    drive_id: Optional[int],
) -> None:
    """Enforce permitted state transitions for institutional TPO screening."""
    if drive_id is None:
        raise InvalidStateTransitionError(
            message="Direct applications bypass TPO screening and cannot undergo screening state changes.",
            code="TPO_SCREENING_BYPASSED",
        )

    allowed = VALID_TPO_SCREENING_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise InvalidStateTransitionError(
            message=f"Invalid TPO screening transition from '{current_status.value}' to '{target_status.value}'.",
            details={"current_status": current_status.value, "target_status": target_status.value},
        )


def validate_recruiter_lifecycle_transition(
    current_status: ApplicationStatus,
    target_status: ApplicationStatus,
    tpo_screening_status: TpoScreeningStatus,
    drive_id: Optional[int],
) -> None:
    """
    Enforce permitted recruitment lifecycle state transitions, including the mandatory
    TPO screening gate for campus drive opportunities.
    """
    # 1. Check basic graph transition
    allowed = VALID_RECRUITER_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise InvalidStateTransitionError(
            message=f"Invalid recruitment pipeline transition from '{current_status.value}' to '{target_status.value}'.",
            details={"current_status": current_status.value, "target_status": target_status.value},
        )

    # 2. Enforce TPO screening gate for campus drives:
    # If drive_id is present, recruiter CANNOT advance candidate past 'applied'
    # unless TPO has explicitly shortlisted the application!
    # (Recruiter rejection and candidate withdrawal are always permitted).
    if drive_id is not None and target_status not in (ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN):
        if tpo_screening_status == TpoScreeningStatus.PENDING:
            raise InvalidStateTransitionError(
                message="Recruiter progression blocked: application is awaiting TPO institutional screening.",
                code="TPO_SCREENING_PENDING",
            )
        elif tpo_screening_status == TpoScreeningStatus.REJECTED:
            raise InvalidStateTransitionError(
                message="Recruiter progression blocked: application was rejected by TPO institutional screening.",
                code="TPO_SCREENING_REJECTED",
            )


# =============================================================================
# Transition Execution & Audit
# =============================================================================

async def execute_tpo_screening_transition(
    session: AsyncSession,
    application: JobApplication,
    new_screening_status: TpoScreeningStatus,
    actor_user_id: int,
    notes: Optional[str] = None,
) -> ApplicationStatusHistory:
    """
    Execute and audit a TPO screening transition.

    CRITICAL ARCHITECTURAL INVARIANT:
    TPO screening and recruiter recruitment must remain strictly separate decision domains.
    A TPO screening update (including late rejection) updates ONLY the TPO screening status
    and its audit history. It NEVER automatically overwrites or mutates the recruiter's recruitment
    lifecycle status (application.current_status), preserving all recruiter states (applied,
    under_review, shortlisted, interview_scheduled, interviewed, offered, offer_accepted,
    offer_declined, rejected, withdrawn).

    When a late TPO rejection occurs, an idempotent notification is dispatched to the corporate
    recruiter(s) explaining the institutional rejection so the recruiter can explicitly make
    the recruitment lifecycle decision.
    """
    if application.current_status == ApplicationStatus.WITHDRAWN:
        raise InvalidStateTransitionError(
            message="Cannot perform TPO screening: Candidate has withdrawn this application.",
            code="APPLICATION_WITHDRAWN",
        )

    validate_tpo_screening_transition(
        current_status=application.tpo_screening_status,
        target_status=new_screening_status,
        drive_id=application.drive_id,
    )

    from_status_val = application.tpo_screening_status.value
    now_utc = datetime.now(timezone.utc)

    # 1. Update application screening state ONLY
    application.tpo_screening_status = new_screening_status
    application.tpo_screened_by_user_id = actor_user_id
    application.tpo_screened_at = now_utc
    application.updated_at = now_utc
    if notes:
        application.tpo_feedback = notes

    # 2. Record append-only history for TPO screening domain ONLY
    history = ApplicationStatusHistory(
        application_id=application.id,
        changed_by_user_id=actor_user_id,
        decision_domain=DecisionDomain.TPO_SCREENING,
        from_status=from_status_val,
        to_status=new_screening_status.value,
        notes=notes,
        created_at=now_utc,
    )
    session.add(history)

    await log_audit_event(
        session=session,
        action=f"APPLICATION_TPO_SCREEN_{new_screening_status.value.upper()}",
        category=AuditCategory.RECRUITMENT,
        entity_type="JobApplication",
        entity_id=str(application.id),
        user_id=actor_user_id,
        previous_values={"tpo_screening_status": from_status_val},
        updated_values={"tpo_screening_status": new_screening_status.value, "notes": notes},
        status=AuditStatus.SUCCESS,
    )

    # 3. If TPO rejection occurs, dispatch an idempotent alert notification to the corporate recruiter(s)
    # The recruiter must explicitly make any corresponding recruitment lifecycle decision.
    if new_screening_status == TpoScreeningStatus.REJECTED:
        job = application.job
        if not job and getattr(application, "job_id", None):
            result = await session.execute(
                select(Job).where(Job.id == application.job_id)
            )
            job = result.scalar_one_or_none()

        job_title = job.title if job else f"Job #{application.job_id}"
        company_id = job.company_id if job else None

        if company_id:
            rec_result = await session.execute(
                select(RecruiterProfile.user_id).where(RecruiterProfile.company_id == company_id)
            )
            recruiter_user_ids = rec_result.scalars().all()
            for r_user_id in recruiter_user_ids:
                await create_notification(
                    session=session,
                    recipient_user_id=r_user_id,
                    sender_user_id=actor_user_id,
                    category=NotificationCategory.APPLICATION_UPDATE,
                    title=f"TPO Screening Rejection: Application #{application.id}",
                    message=(
                        f"Candidate application #{application.id} for '{job_title}' was rejected during institutional "
                        f"TPO screening (Reason: {notes or 'No reason specified'}). Current recruitment pipeline status "
                        f"('{application.current_status.value}') remains preserved. Please review and make an explicit decision."
                    ),
                    related_application_id=application.id,
                    related_drive_id=application.drive_id,
                    idempotency_key=f"tpo-rejection-alert-{application.id}-{r_user_id}",
                )

    await session.flush()
    return history


async def execute_recruiter_lifecycle_transition(
    session: AsyncSession,
    application: JobApplication,
    new_status: ApplicationStatus,
    actor_user_id: int,
    notes: Optional[str] = None,
) -> ApplicationStatusHistory:
    """Execute and audit a recruiter lifecycle transition."""
    validate_recruiter_lifecycle_transition(
        current_status=application.current_status,
        target_status=new_status,
        tpo_screening_status=application.tpo_screening_status,
        drive_id=application.drive_id,
    )

    from_status_val = application.current_status.value
    now_utc = datetime.now(timezone.utc)

    # Update application lifecycle state
    application.current_status = new_status
    application.recruiter_decision_at = now_utc
    application.updated_at = now_utc
    if notes:
        application.recruiter_feedback_notes = notes

    history = ApplicationStatusHistory(
        application_id=application.id,
        changed_by_user_id=actor_user_id,
        decision_domain=DecisionDomain.RECRUITMENT_LIFECYCLE,
        from_status=from_status_val,
        to_status=new_status.value,
        notes=notes,
        created_at=now_utc,
    )
    session.add(history)

    await log_audit_event(
        session=session,
        action="APPLICATION_STATUS_TRANSITION",
        category=AuditCategory.RECRUITMENT,
        entity_type="JobApplication",
        entity_id=str(application.id),
        user_id=actor_user_id,
        previous_values={"current_status": from_status_val},
        updated_values={"current_status": new_status.value, "notes": notes},
        status=AuditStatus.SUCCESS,
    )
    await session.flush()
    return history

