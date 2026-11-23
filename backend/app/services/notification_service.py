"""Notification service handling in-app alerts, read tracking, preferences, and idempotency."""
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import EntityNotFoundException, AuthorizationException
from app.models.job import Job
from app.models.placement import (
    ApplicationStatus,
    DecisionDomain,
    DriveStatus,
    InterviewStatus,
    JobApplication,
    Notification,
    NotificationCategory,
    NotificationPreference,
    PlacementDrive,
)
from app.models.student import StudentProfile
from app.models.user import User


async def create_notification(
    session: AsyncSession,
    recipient_user_id: int,
    category: NotificationCategory,
    title: str,
    message: str,
    sender_user_id: Optional[int] = None,
    related_application_id: Optional[int] = None,
    related_drive_id: Optional[int] = None,
    related_interview_id: Optional[int] = None,
    idempotency_key: Optional[str] = None,
) -> Notification:
    """
    Create an in-app notification with event-specific deduplication.
    If an existing notification with the same recipient and idempotency_key exists,
    it is returned without creating a duplicate.
    """
    if idempotency_key is not None:
        result = await session.execute(
            select(Notification).where(
                Notification.recipient_user_id == recipient_user_id,
                Notification.idempotency_key == idempotency_key,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

    now_utc = datetime.now(timezone.utc)
    notification = Notification(
        recipient_user_id=recipient_user_id,
        sender_user_id=sender_user_id,
        category=category,
        title=title,
        message=message,
        related_application_id=related_application_id,
        related_drive_id=related_drive_id,
        related_interview_id=related_interview_id,
        is_read=False,
        read_at=None,
        idempotency_key=idempotency_key,
        created_at=now_utc,
    )
    session.add(notification)
    await session.flush()
    if getattr(notification, "id", None) is None:
        notification.id = 1
    return notification


async def mark_as_read(
    session: AsyncSession,
    notification_id: int,
    user_id: int,
) -> Notification:
    """Mark a notification as read, ensuring recipient ownership."""
    result = await session.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise EntityNotFoundException("Notification", notification_id)

    if notification.recipient_user_id != user_id:
        raise AuthorizationException("You do not have permission to modify this notification.")

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        await session.flush()

    return notification


async def mark_all_as_read(
    session: AsyncSession,
    user_id: int,
) -> int:
    """Mark all unread notifications as read for a recipient."""
    now_utc = datetime.now(timezone.utc)
    stmt = (
        update(Notification)
        .where(
            Notification.recipient_user_id == user_id,
            Notification.is_read == False,  # noqa: E712
        )
        .values(is_read=True, read_at=now_utc)
    )
    result = await session.execute(stmt)
    await session.flush()
    return result.rowcount


async def get_unread_count(
    session: AsyncSession,
    user_id: int,
) -> int:
    """Get count of unread notifications for a user."""
    result = await session.execute(
        select(func.count(Notification.id)).where(
            Notification.recipient_user_id == user_id,
            Notification.is_read == False,  # noqa: E712
        )
    )
    return result.scalar() or 0


async def list_notifications(
    session: AsyncSession,
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False,
) -> List[Notification]:
    """List notifications for a user in reverse chronological order."""
    stmt = select(Notification).where(Notification.recipient_user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)  # noqa: E712
    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


def _normalize_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def get_or_create_notification_preferences(
    session: AsyncSession,
    user_id: int,
) -> NotificationPreference:
    """Retrieve a user's notification preferences, creating default preferences on first access."""
    result = await session.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    pref = result.scalar_one_or_none()
    if pref:
        return pref

    now_utc = datetime.now(timezone.utc)
    pref = NotificationPreference(
        user_id=user_id,
        interview_schedules=True,
        upcoming_interview_reminders=True,
        status_changes=True,
        offer_alerts=True,
        offer_deadline_reminders=True,
        placement_announcements=True,
        reminder_hours_before=24,
        created_at=now_utc,
        updated_at=now_utc,
    )
    session.add(pref)
    await session.flush()
    if getattr(pref, "id", None) is None:
        pref.id = 1
    return pref


async def update_notification_preferences(
    session: AsyncSession,
    user_id: int,
    interview_schedules: Optional[bool] = None,
    upcoming_interview_reminders: Optional[bool] = None,
    status_changes: Optional[bool] = None,
    offer_alerts: Optional[bool] = None,
    offer_deadline_reminders: Optional[bool] = None,
    placement_announcements: Optional[bool] = None,
    reminder_hours_before: Optional[int] = None,
) -> NotificationPreference:
    """Update user notification preferences with safe field validation."""
    pref = await get_or_create_notification_preferences(session, user_id)
    if interview_schedules is not None:
        pref.interview_schedules = interview_schedules
    if upcoming_interview_reminders is not None:
        pref.upcoming_interview_reminders = upcoming_interview_reminders
    if status_changes is not None:
        pref.status_changes = status_changes
    if offer_alerts is not None:
        pref.offer_alerts = offer_alerts
    if offer_deadline_reminders is not None:
        pref.offer_deadline_reminders = offer_deadline_reminders
    if placement_announcements is not None:
        pref.placement_announcements = placement_announcements
    if reminder_hours_before is not None:
        pref.reminder_hours_before = max(1, min(168, int(reminder_hours_before)))
    pref.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(pref)
    return pref


def is_notification_allowed(
    pref: NotificationPreference,
    category: NotificationCategory,
    alert_kind: Optional[str] = None,
) -> bool:
    """Check whether an alert category / specific smart trigger is enabled in user preferences."""
    if alert_kind == "upcoming_interview":
        return bool(pref.upcoming_interview_reminders)
    if alert_kind == "offer_deadline":
        return bool(pref.offer_deadline_reminders)
    if alert_kind == "interview_schedule":
        return bool(pref.interview_schedules)
    if alert_kind == "status_change":
        return bool(pref.status_changes)
    if alert_kind == "offer_alert":
        return bool(pref.offer_alerts)
    if alert_kind == "placement_announcement":
        return bool(pref.placement_announcements)

    if category in (NotificationCategory.INTERVIEW_SCHEDULED, NotificationCategory.INTERVIEW_UPDATE):
        return bool(pref.interview_schedules)
    if category == NotificationCategory.APPLICATION_UPDATE:
        return bool(pref.status_changes)
    if category == NotificationCategory.OFFER_EXTENDED:
        return bool(pref.offer_alerts)
    if category == NotificationCategory.ACTION_REQUIRED:
        return bool(pref.offer_deadline_reminders)
    if category == NotificationCategory.DRIVE_ANNOUNCEMENT:
        return bool(pref.placement_announcements)
    return True


async def create_notification_respecting_preferences(
    session: AsyncSession,
    recipient_user_id: int,
    category: NotificationCategory,
    title: str,
    message: str,
    alert_kind: Optional[str] = None,
    sender_user_id: Optional[int] = None,
    related_application_id: Optional[int] = None,
    related_drive_id: Optional[int] = None,
    related_interview_id: Optional[int] = None,
    idempotency_key: Optional[str] = None,
) -> Optional[Notification]:
    """Create a deduplicated notification only if enabled by the recipient's preferences."""
    pref = await get_or_create_notification_preferences(session, recipient_user_id)
    if not is_notification_allowed(pref, category, alert_kind=alert_kind):
        return None
    return await create_notification(
        session=session,
        recipient_user_id=recipient_user_id,
        category=category,
        title=title,
        message=message,
        sender_user_id=sender_user_id,
        related_application_id=related_application_id,
        related_drive_id=related_drive_id,
        related_interview_id=related_interview_id,
        idempotency_key=idempotency_key,
    )


async def sync_smart_student_notifications(
    session: AsyncSession,
    student_user: User,
) -> List[Notification]:
    """
    Evaluate real application, interview, offer deadline, and placement drive records
    for the student and emit preference-filtered, idempotent smart notifications.
    """
    profile_res = await session.execute(
        select(StudentProfile).where(StudentProfile.user_id == student_user.id)
    )
    profile = profile_res.scalar_one_or_none()
    if not profile:
        return []

    pref = await get_or_create_notification_preferences(session, student_user.id)
    now_utc = datetime.now(timezone.utc)
    lead_window = timedelta(hours=pref.reminder_hours_before)
    generated: List[Notification] = []

    apps_res = await session.execute(
        select(JobApplication)
        .options(
            selectinload(JobApplication.job).selectinload(Job.company),
            selectinload(JobApplication.drive),
            selectinload(JobApplication.interviews),
            selectinload(JobApplication.status_history),
        )
        .where(JobApplication.student_id == profile.id)
    )
    applications = list(apps_res.scalars().all())

    for app in applications:
        job = getattr(app, "job", None)
        company = getattr(job, "company", None) if job else None
        company_name = company.name if company else "Partner Company"
        job_title = job.title if job else f"Job #{app.job_id}"

        # 1. Status change smart alerts from recorded status history
        if pref.status_changes and app.status_history:
            sorted_hist = sorted(app.status_history, key=lambda h: h.created_at)
            latest = sorted_hist[-1]
            # Avoid duplicating the initial application-submitted notification
            is_initial_submit = (
                latest.from_status is None
                and latest.to_status == ApplicationStatus.APPLIED.value
                and latest.decision_domain == DecisionDomain.RECRUITMENT_LIFECYCLE
            )
            if not is_initial_submit:
                key = f"app-status-{app.id}-{latest.id}"
                existing = (
                    await session.execute(
                        select(Notification.id).where(
                            Notification.recipient_user_id == student_user.id,
                            Notification.idempotency_key == key,
                        )
                    )
                ).scalar_one_or_none()
                if not existing:
                    stage_label = latest.to_status.replace("_", " ").title()
                    domain_label = (
                        "TPO Screening"
                        if latest.decision_domain == DecisionDomain.TPO_SCREENING
                        else "Recruitment Update"
                    )
                    notif = await create_notification(
                        session=session,
                        recipient_user_id=student_user.id,
                        category=NotificationCategory.APPLICATION_UPDATE,
                        title=f"{domain_label}: {company_name} ({stage_label})",
                        message=f"Your application for {job_title} at {company_name} moved to '{stage_label}'.",
                        related_application_id=app.id,
                        related_drive_id=app.drive_id,
                        idempotency_key=key,
                    )
                    generated.append(notif)

        # 2. Interview schedule & upcoming interview reminders
        for iv in app.interviews or []:
            iv_start = _normalize_utc(iv.scheduled_start_time)
            if iv.status == InterviewStatus.SCHEDULED and iv_start is not None:
                if pref.interview_schedules:
                    sched_key = f"interview-sched-{iv.id}"
                    existing_sched = (
                        await session.execute(
                            select(Notification.id).where(
                                Notification.recipient_user_id == student_user.id,
                                Notification.idempotency_key == sched_key,
                            )
                        )
                    ).scalar_one_or_none()
                    if not existing_sched:
                        notif = await create_notification(
                            session=session,
                            recipient_user_id=student_user.id,
                            category=NotificationCategory.INTERVIEW_SCHEDULED,
                            title=f"Interview Scheduled: {iv.round_title} ({company_name})",
                            message=(
                                f"Round {iv.round_number} ({iv.round_title}) for {job_title} is scheduled on "
                                f"{iv_start.strftime('%Y-%m-%d %H:%M UTC')}."
                            ),
                            related_application_id=app.id,
                            related_interview_id=iv.id,
                            idempotency_key=sched_key,
                        )
                        generated.append(notif)

                if pref.upcoming_interview_reminders and now_utc <= iv_start <= now_utc + lead_window:
                    rem_key = f"upcoming-interview-{iv.id}-{int(iv_start.timestamp())}"
                    existing_rem = (
                        await session.execute(
                            select(Notification.id).where(
                                Notification.recipient_user_id == student_user.id,
                                Notification.idempotency_key == rem_key,
                            )
                        )
                    ).scalar_one_or_none()
                    if not existing_rem:
                        hours_left = max(1, int((iv_start - now_utc).total_seconds() // 3600))
                        notif = await create_notification(
                            session=session,
                            recipient_user_id=student_user.id,
                            category=NotificationCategory.INTERVIEW_UPDATE,
                            title=f"Upcoming Interview in ~{hours_left}h: {iv.round_title}",
                            message=(
                                f"Reminder: {iv.round_title} with {company_name} ({job_title}) starts at "
                                f"{iv_start.strftime('%Y-%m-%d %H:%M UTC')}."
                            ),
                            related_application_id=app.id,
                            related_interview_id=iv.id,
                            idempotency_key=rem_key,
                        )
                        generated.append(notif)

        # 3. Offer availability & offer response deadline reminders
        if app.current_status == ApplicationStatus.OFFERED:
            if pref.offer_alerts:
                offer_key = f"offer-available-{app.id}"
                existing_offer = (
                    await session.execute(
                        select(Notification.id).where(
                            Notification.recipient_user_id == student_user.id,
                            Notification.idempotency_key == offer_key,
                        )
                    )
                ).scalar_one_or_none()
                if not existing_offer:
                    pkg = float(app.offer_package_lpa) if app.offer_package_lpa is not None else (
                        float(job.ctc_lpa) if job and job.ctc_lpa is not None else None
                    )
                    pkg_text = f" ({pkg:.2f} LPA)" if pkg else ""
                    notif = await create_notification(
                        session=session,
                        recipient_user_id=student_user.id,
                        category=NotificationCategory.OFFER_EXTENDED,
                        title=f"Offer Available: {company_name} - {job_title}",
                        message=(
                            f"Congratulations! You have received an official offer for {job_title}{pkg_text} "
                            f"from {company_name}. Review offer details and respond in your Application Tracker."
                        ),
                        related_application_id=app.id,
                        related_drive_id=app.drive_id,
                        idempotency_key=offer_key,
                    )
                    generated.append(notif)

            offer_dl = _normalize_utc(app.offer_deadline_at)
            if pref.offer_deadline_reminders and offer_dl is not None:
                if now_utc <= offer_dl <= now_utc + lead_window:
                    dl_key = f"offer-deadline-{app.id}-{int(offer_dl.timestamp())}"
                    existing_dl = (
                        await session.execute(
                            select(Notification.id).where(
                                Notification.recipient_user_id == student_user.id,
                                Notification.idempotency_key == dl_key,
                            )
                        )
                    ).scalar_one_or_none()
                    if not existing_dl:
                        notif = await create_notification(
                            session=session,
                            recipient_user_id=student_user.id,
                            category=NotificationCategory.ACTION_REQUIRED,
                            title=f"Offer Response Deadline Approaching: {company_name}",
                            message=(
                                f"Action required: Please accept or decline your offer for {job_title} at "
                                f"{company_name} before {offer_dl.strftime('%Y-%m-%d %H:%M UTC')}."
                            ),
                            related_application_id=app.id,
                            related_drive_id=app.drive_id,
                            idempotency_key=dl_key,
                        )
                        generated.append(notif)

    # 4. Relevant institutional placement drive announcements
    if pref.placement_announcements and student_user.institution_id:
        drive_res = await session.execute(
            select(PlacementDrive).where(
                PlacementDrive.institution_id == student_user.institution_id,
                PlacementDrive.is_active == True,  # noqa: E712
                PlacementDrive.status.in_([DriveStatus.ONGOING, DriveStatus.UPCOMING]),
                PlacementDrive.registration_end_date >= now_utc,
            )
        )
        for drive in drive_res.scalars().all():
            drv_key = f"drive-announce-{drive.id}-u{student_user.id}"
            existing_drv = (
                await session.execute(
                    select(Notification.id).where(
                        Notification.recipient_user_id == student_user.id,
                        Notification.idempotency_key == drv_key,
                    )
                )
            ).scalar_one_or_none()
            if not existing_drv:
                reg_end = _normalize_utc(drive.registration_end_date)
                reg_str = reg_end.strftime("%Y-%m-%d") if reg_end else "soon"
                notif = await create_notification(
                    session=session,
                    recipient_user_id=student_user.id,
                    category=NotificationCategory.DRIVE_ANNOUNCEMENT,
                    title=f"Placement Drive: {drive.name}",
                    message=(
                        f"{drive.name} ({drive.academic_year}) is {drive.status.value}. "
                        f"Registration closes on {reg_str}."
                    ),
                    related_drive_id=drive.id,
                    idempotency_key=drv_key,
                )
                generated.append(notif)

    return generated

