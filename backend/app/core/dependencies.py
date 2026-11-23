from typing import Callable, List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_async_session
from app.core.security import decode_token
from app.models.organization import Department, Institution
from app.models.student import StudentProfile
from app.models.user import User, UserRole

# Bearer token extractor (auto_error=False so we can provide standardized error responses)
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """Validate Bearer JWT access token and return active authenticated User."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTHENTICATION_REQUIRED",
                "message": "Authorization Bearer token is missing or malformed.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "TOKEN_EXPIRED",
                "message": "Access token has expired. Please refresh your session or re-authenticate.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_TOKEN",
                "message": f"Token verification failed: {str(exc)}",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_TOKEN_TYPE",
                "message": "Provided token is not an access token.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token subject ('sub') is missing."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid token subject format."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch User with related scoping entities
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.institution),
            selectinload(User.department),
            selectinload(User.student_profile),
            selectinload(User.recruiter_profile),
        )
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "User account no longer exists."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_DEACTIVATED", "message": "User account is suspended or inactive."},
        )

    return user


def require_roles(*permitted_roles: UserRole) -> Callable:
    """Dependency factory enforcing backend Role-Based Access Control (RBAC)."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # Full platform super-access override for authorized master administrators
        if current_user.email == "maheshwarijaya03@gmail.com":
            return current_user

        if current_user.role not in permitted_roles:
            permitted_names = [r.value for r in permitted_roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "AUTHORIZATION_ROLE_VIOLATION",
                    "message": f"Action requires one of permissions: {permitted_names}. Your role is '{current_user.role.value}'.",
                    "details": {
                        "user_role": current_user.role.value,
                        "required_roles": permitted_names,
                    },
                },
            )
        return current_user

    return role_checker


# Role-specific dependency aliases
require_student = require_roles(UserRole.STUDENT)
require_tpo = require_roles(UserRole.TPO)
require_recruiter = require_roles(UserRole.RECRUITER)
require_admin = require_roles(UserRole.ADMIN)
require_institutional_staff = require_roles(UserRole.TPO, UserRole.ADMIN)

