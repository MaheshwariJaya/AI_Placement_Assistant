from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
import jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.database import get_async_session
from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_email_token,
    verify_password,
    verify_password_reset_token,
)
from app.models.organization import Department, Institution
from app.models.student import StudentProfile
from app.models.token import RefreshToken
from app.models.user import User, UserRole
from app.models.audit import AuditCategory, AuditStatus
from app.services.audit_service import log_audit_event
from app.schemas.auth import (
    ChangePasswordRequest,
    EmailVerifyRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])
settings = get_settings()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """Register a new user account adhering to role-based scoping rules."""
    email_clean = payload.email.lower().strip()

    # 1. Validate Password Strength
    pw_error = validate_password_strength(payload.password)
    if pw_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "WEAK_PASSWORD", "message": pw_error},
        )

    # 2. Structural & Role-Based Payload Validations (before DB query)
    # Reject public self-registration for privileged administrative roles
    if payload.role in (UserRole.TPO, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "PRIVILEGED_ROLE_SELF_REGISTRATION_DENIED",
                "message": (
                    f"Account role '{payload.role.value}' cannot be self-registered publicly. "
                    "Institutional staff and administrator accounts must be provisioned by authorized administrative authorities."
                ),
            },
        )

    institution_id = payload.institution_id
    department_id = payload.department_id

    if payload.role == UserRole.STUDENT:
        if not institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INSTITUTION_REQUIRED", "message": "Students must be enrolled in an institution."},
            )
        if not department_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "DEPARTMENT_REQUIRED", "message": "Students must be assigned to an academic department."},
            )
        if not payload.student_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "STUDENT_DATA_REQUIRED", "message": "Student registration requires academic portfolio details."},
            )
    elif payload.role == UserRole.RECRUITER:
        # Enforce that recruiters cannot self-assign institutional scopes
        department_id = None
        institution_id = None

    # 3. Check for Duplicate Email
    existing_user_stmt = select(User).where(User.email == email_clean)
    existing_user = (await session.execute(existing_user_stmt)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_ALREADY_EXISTS", "message": f"An account with email '{email_clean}' already exists."},
        )

    # 4. Database Foreign Key & Institutional Integrity Validations
    if payload.role == UserRole.STUDENT:
        # Validate institution exists and is active
        inst = await session.get(Institution, institution_id)
        if not inst or not inst.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_INSTITUTION", "message": "Specified institution does not exist or is inactive."},
            )

        # Validate department exists and belongs to the specified institution
        dept = await session.get(Department, department_id)
        if not dept or not dept.is_active or dept.institution_id != institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_DEPARTMENT", "message": "Specified department does not exist in this institution."},
            )

        # Check for Duplicate Roll Number
        roll_clean = payload.student_data.roll_number.strip()
        existing_profile_stmt = select(StudentProfile).where(StudentProfile.roll_number == roll_clean)
        existing_profile = (await session.execute(existing_profile_stmt)).scalar_one_or_none()
        if existing_profile:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "ROLL_NUMBER_ALREADY_EXISTS", "message": f"Roll number '{roll_clean}' is already registered."},
            )

    # 4. Create User Record
    hashed_pwd = hash_password(payload.password)
    new_user = User(
        email=email_clean,
        hashed_password=hashed_pwd,
        full_name=payload.full_name.strip(),
        phone=payload.phone.strip() if payload.phone else None,
        role=payload.role,
        institution_id=institution_id,
        department_id=department_id,
        is_active=True,
        is_verified=False,
    )
    session.add(new_user)
    await session.flush()  # Populates new_user.id

    # 5. Create StudentProfile if Student
    if payload.role == UserRole.STUDENT and payload.student_data:
        student_profile = StudentProfile(
            user_id=new_user.id,
            roll_number=payload.student_data.roll_number.strip(),
            graduation_year=payload.student_data.graduation_year,
            cgpa=payload.student_data.cgpa,
            active_backlogs=payload.student_data.active_backlogs,
            total_backlogs=payload.student_data.total_backlogs,
            is_placement_ready=True,
        )
        session.add(student_profile)

    await session.commit()

    return {
        "success": True,
        "message": "Registration successful. Please verify your email.",
        "user_id": new_user.id,
        "email": new_user.email,
        "role": new_user.role.value,
    }


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_async_session),
) -> TokenResponse:
    """Authenticate user with email/password and issue scoped JWT access & refresh tokens."""
    email_clean = payload.email.lower().strip()

    stmt = (
        select(User)
        .where(User.email == email_clean)
        .options(
            selectinload(User.institution),
            selectinload(User.department),
            selectinload(User.student_profile),
        )
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        await log_audit_event(
            session=session,
            action="LOGIN_FAILURE",
            category=AuditCategory.AUTHENTICATION,
            entity_type="User",
            entity_id=str(user.id) if user else None,
            user_email=email_clean,
            user_name=getattr(user, "full_name", None),
            institution_id=user.institution_id if user else None,
            status=AuditStatus.FAILURE,
            metadata={"email": email_clean, "reason": "INVALID_CREDENTIALS"},
            commit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        await log_audit_event(
            session=session,
            action="LOGIN_BLOCKED_INACTIVE",
            category=AuditCategory.AUTHENTICATION,
            entity_type="User",
            entity_id=str(user.id),
            user=user,
            status=AuditStatus.FAILURE,
            metadata={"reason": "ACCOUNT_DEACTIVATED"},
            commit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_DEACTIVATED", "message": "Your account has been deactivated. Contact administration."},
        )

    # Generate JWT Tokens
    token_claims = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "institution_id": user.institution_id,
        "department_id": user.department_id,
    }
    access_token = create_access_token(token_claims)
    refresh_token = create_refresh_token({"sub": str(user.id), "user_id": user.id})

    # Track refresh token server-side for rotation & revocation (SEC-03)
    r_hash = hash_token(refresh_token)
    r_claims = decode_token(refresh_token)
    r_expires_at = datetime.fromtimestamp(r_claims["exp"], tz=timezone.utc)

    refresh_record = RefreshToken(
        user_id=user.id,
        token_hash=r_hash,
        expires_at=r_expires_at,
    )
    session.add(refresh_record)

    await log_audit_event(
        session=session,
        action="LOGIN_SUCCESS",
        category=AuditCategory.AUTHENTICATION,
        entity_type="User",
        entity_id=str(user.id),
        user=user,
        status=AuditStatus.SUCCESS,
        metadata={"auth_method": "PASSWORD"},
    )
    await session.commit()

    user_dict = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "institution_id": user.institution_id,
        "institution_name": user.institution.name if user.institution else None,
        "department_id": user.department_id,
        "department_name": user.department.name if user.department else None,
        "is_verified": user.is_verified,
    }
    if user.student_profile:
        user_dict["student_profile_id"] = user.student_profile.id
        user_dict["roll_number"] = user.student_profile.roll_number

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in_hours=24,
        user=user_dict,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    payload: RefreshTokenRequest,
    session: AsyncSession = Depends(get_async_session),
) -> TokenResponse:
    """Issue a new access token and rotated refresh token using an active refresh token."""
    raw_token = payload.refresh_token.strip()

    # 1. Verify signature, expiration and token type
    try:
        claims = decode_token(raw_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "REFRESH_TOKEN_EXPIRED", "message": "Refresh token has expired. Please log in again."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_REFRESH_TOKEN", "message": f"Malformed or invalid refresh token: {exc}"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if claims.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN_TYPE", "message": "Provided token is not a refresh token."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = int(claims.get("sub", claims.get("user_id", 0)))
    now = datetime.now(timezone.utc)
    token_hash = hash_token(raw_token)

    # 2. Query server-side token record with row-level lock (prevents concurrent race conditions)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
    token_record = (await session.execute(stmt)).scalar_one_or_none()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNKNOWN_REFRESH_TOKEN", "message": "Refresh token unrecognized or not found."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Detect Replay Attack: If token was ALREADY revoked, revoke ALL active tokens for this user!
    if token_record.revoked_at is not None:
        revoke_all_stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await session.execute(revoke_all_stmt)
        await session.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "REFRESH_TOKEN_REUSE_DETECTED",
                "message": (
                    "Security alert: Revoked refresh token reuse detected. "
                    "All active sessions for this account have been invalidated. Please log in again."
                ),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. Check database expiration
    if token_record.expires_at <= now:
        token_record.revoked_at = now
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "REFRESH_TOKEN_EXPIRED", "message": "Refresh token has expired."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 5. Fetch User to ensure active status
    user_stmt = (
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.institution),
            selectinload(User.department),
            selectinload(User.student_profile),
        )
    )
    user = (await session.execute(user_stmt)).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_INACTIVE", "message": "User account no longer active."},
        )

    # 6. ATOMIC TRANSACTION: Revoke Old Token + Issue New Rotated Token
    token_record.revoked_at = now

    new_refresh_raw = create_refresh_token({"sub": str(user.id), "user_id": user.id})
    new_hash = hash_token(new_refresh_raw)
    new_claims = decode_token(new_refresh_raw)
    new_expires_at = datetime.fromtimestamp(new_claims["exp"], tz=timezone.utc)

    new_token_record = RefreshToken(
        user_id=user.id,
        token_hash=new_hash,
        expires_at=new_expires_at,
    )
    session.add(new_token_record)

    token_claims = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "institution_id": user.institution_id,
        "department_id": user.department_id,
    }
    new_access_token = create_access_token(token_claims)

    await session.commit()

    user_dict = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "institution_id": user.institution_id,
        "institution_name": user.institution.name if user.institution else None,
        "department_id": user.department_id,
        "department_name": user.department.name if user.department else None,
        "is_verified": user.is_verified,
    }
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_raw,
        token_type="bearer",
        expires_in_hours=24,
        user=user_dict,
    )


@router.post("/logout")
async def logout(
    payload: Optional[LogoutRequest] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """Logout current user session and revoke refresh token server-side (idempotent)."""
    now = datetime.now(timezone.utc)
    if payload and payload.refresh_token:
        # 1. Targeted single-session revocation with row-level lock
        token_hash = hash_token(payload.refresh_token.strip())
        stmt = (
            select(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.user_id == current_user.id,
            )
            .with_for_update()
        )
        token_record = (await session.execute(stmt)).scalar_one_or_none()
        if token_record and token_record.revoked_at is None:
            token_record.revoked_at = now
            await session.commit()
    else:
        # 2. Universal revocation for this user across all sessions
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == current_user.id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await session.execute(stmt)
        await session.commit()

    await log_audit_event(
        session=session,
        action="LOGOUT",
        category=AuditCategory.AUTHENTICATION,
        entity_type="User",
        entity_id=str(current_user.id),
        user=current_user,
        status=AuditStatus.SUCCESS,
        metadata={"scope": "single_session" if (payload and payload.refresh_token) else "all_sessions"},
        commit=True,
    )

    return {"success": True, "message": "Successfully logged out. Refresh token has been revoked."}


@router.get("/me")
async def get_my_context(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Retrieve currently authenticated user identity and institutional bounds."""
    data = {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "role": current_user.role.value,
        "institution_id": current_user.institution_id,
        "institution_name": current_user.institution.name if current_user.institution else None,
        "department_id": current_user.department_id,
        "department_name": current_user.department.name if current_user.department else None,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }
    if current_user.student_profile:
        data["student_profile"] = {
            "id": current_user.student_profile.id,
            "roll_number": current_user.student_profile.roll_number,
            "graduation_year": current_user.student_profile.graduation_year,
            "cgpa": float(current_user.student_profile.cgpa),
            "active_backlogs": current_user.student_profile.active_backlogs,
            "total_backlogs": current_user.student_profile.total_backlogs,
            "linkedin_url": current_user.student_profile.linkedin_url,
            "github_url": current_user.student_profile.github_url,
            "portfolio_url": current_user.student_profile.portfolio_url,
            "is_placement_ready": current_user.student_profile.is_placement_ready,
        }
    return {"success": True, "user": data}


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """Initiate password reset flow foundation."""
    email_clean = payload.email.lower().strip()
    stmt = select(User).where(User.email == email_clean)
    user = (await session.execute(stmt)).scalar_one_or_none()

    reset_token = None
    if user and user.is_active:
        reset_token = create_password_reset_token(user.email)

    response = {
        "success": True,
        "message": "If this email is registered, a password reset link has been dispatched.",
    }
    # In development or debug, surface token for easy automated testing
    if settings.APP_DEBUG and reset_token:
        response["dev_reset_token"] = reset_token

    return response


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """Complete password reset using valid signed reset token."""
    email = verify_password_reset_token(payload.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_RESET_TOKEN", "message": "Password reset token is invalid or has expired."},
        )

    pw_error = validate_password_strength(payload.new_password)
    if pw_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "WEAK_PASSWORD", "message": pw_error},
        )

    stmt = select(User).where(User.email == email)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User associated with this token was not found."},
        )

    user.hashed_password = hash_password(payload.new_password)
    await session.commit()

    return {"success": True, "message": "Password has been successfully updated. You may now log in."}


@router.post("/verify-email")
async def verify_email(
    payload: EmailVerifyRequest,
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """Verify email activation token and mark user account verified."""
    email = verify_email_token(payload.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_VERIFICATION_TOKEN", "message": "Email verification token is invalid or expired."},
        )

    stmt = select(User).where(User.email == email)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found."},
        )

    user.is_verified = True
    await session.commit()

    return {"success": True, "message": "Email address successfully verified."}


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """Allow an authenticated user to change their password after verifying the current one."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_CURRENT_PASSWORD",
                "message": "Current password is incorrect.",
            },
        )

    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "SAME_PASSWORD",
                "message": "New password must be different from your current password.",
            },
        )

    pw_error = validate_password_strength(payload.new_password)
    if pw_error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "WEAK_PASSWORD", "message": pw_error},
        )

    current_user.hashed_password = hash_password(payload.new_password)
    await session.commit()

    return {"success": True, "message": "Password updated successfully."}
