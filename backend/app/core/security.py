import datetime
from datetime import timedelta, timezone
import hashlib
import re
from typing import Any, Dict, Optional
import uuid
import bcrypt
import jwt

from app.config import get_settings

settings = get_settings()

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 7          # 7 days
TOKEN_ALGORITHM = "HS256"


def validate_password_strength(password: str) -> Optional[str]:
    """Validate password strength according to SRS rules.
    
    Must be at least 8 characters, contain at least one digit and one special character.
    Returns None if valid, or an error string if invalid.
    """
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"\d", password):
        return "Password must contain at least one number."
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?/~`]", password):
        return "Password must contain at least one special character."
    if len(password.encode("utf-8")) > 72:
        return "Password cannot exceed 72 bytes."
    return None


def hash_password(password: str) -> str:
    """Hash a plaintext password using native bcrypt with auto-generated salt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a scoped JWT access token."""
    to_encode = data.copy()
    now = datetime.datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access",
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=TOKEN_ALGORITHM)
    return encoded_jwt


def hash_token(token: str) -> str:
    """Generate SHA-256 hex digest of a token string for safe server-side storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a long-lived JWT refresh token with unique jti identifier."""
    to_encode = data.copy()
    now = datetime.datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    jti = str(uuid.uuid4())
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "refresh",
        "jti": jti,
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=TOKEN_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token.
    
    Raises jwt.PyJWTError on invalid or expired token.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[TOKEN_ALGORITHM])


def create_email_verification_token(email: str) -> str:
    """Generate a time-limited email verification token (24-hour expiration)."""
    now = datetime.datetime.now(timezone.utc)
    expire = now + timedelta(hours=24)
    payload = {
        "sub": email,
        "type": "email_verification",
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=TOKEN_ALGORITHM)


def verify_email_token(token: str) -> Optional[str]:
    """Verify email token and return email if valid."""
    try:
        payload = decode_token(token)
        if payload.get("type") == "email_verification":
            return payload.get("sub")
    except Exception:
        pass
    return None


def create_password_reset_token(email: str) -> str:
    """Generate a short-lived password reset token (15-minute expiration)."""
    now = datetime.datetime.now(timezone.utc)
    expire = now + timedelta(minutes=15)
    payload = {
        "sub": email,
        "type": "password_reset",
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=TOKEN_ALGORITHM)


def verify_password_reset_token(token: str) -> Optional[str]:
    """Verify password reset token and return email if valid."""
    try:
        payload = decode_token(token)
        if payload.get("type") == "password_reset":
            return payload.get("sub")
    except Exception:
        pass
    return None

