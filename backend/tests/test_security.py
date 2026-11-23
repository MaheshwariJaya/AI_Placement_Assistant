import datetime
from datetime import timedelta, timezone
import pytest
import jwt

from app.core.security import (
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    validate_password_strength,
    verify_email_token,
    verify_password,
    verify_password_reset_token,
)


def test_password_strength_validation():
    # Less than 8 chars
    assert validate_password_strength("Pass1!") == "Password must be at least 8 characters long."
    # Missing digit
    assert validate_password_strength("Password!") == "Password must contain at least one number."
    # Missing special char
    assert validate_password_strength("Password123") == "Password must contain at least one special character."
    # Valid password
    assert validate_password_strength("SecurePass123!") is None
    assert validate_password_strength("My@Colle9eP1acement") is None


def test_password_hashing_and_verification():
    raw_pwd = "Antigravity@2026Password"
    hashed = hash_password(raw_pwd)

    assert hashed != raw_pwd
    assert hashed.startswith("$2b$")
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_jwt_access_and_refresh_tokens():
    payload = {"sub": "42", "role": "student", "email": "student@college.edu"}
    
    # 1. Access token
    token = create_access_token(payload, expires_delta=timedelta(minutes=5))
    decoded = decode_token(token)
    assert decoded["sub"] == "42"
    assert decoded["role"] == "student"
    assert decoded["type"] == "access"
    assert "exp" in decoded

    # 2. Refresh token
    refresh = create_refresh_token({"sub": "42"}, expires_delta=timedelta(days=1))
    decoded_refresh = decode_token(refresh)
    assert decoded_refresh["sub"] == "42"
    assert decoded_refresh["type"] == "refresh"


def test_jwt_expiration():
    # Expired token (1 second in the past)
    expired_token = create_access_token({"sub": "42"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(expired_token)


def test_email_verification_token():
    email = "new_student@college.edu"
    token = create_email_verification_token(email)
    verified = verify_email_token(token)
    assert verified == email

    # Invalid token returns None
    assert verify_email_token("invalid.jwt.token") is None


def test_password_reset_token():
    email = "reset_user@college.edu"
    token = create_password_reset_token(email)
    verified = verify_password_reset_token(token)
    assert verified == email

    # Invalid token returns None
    assert verify_password_reset_token("invalid.token") is None

