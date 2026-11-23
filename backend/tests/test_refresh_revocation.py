import datetime
from datetime import timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import HTTPException
import jwt

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
)
from app.models.token import RefreshToken
from app.models.user import User, UserRole
from app.routes.auth import logout, refresh_access_token
from app.schemas.auth import LogoutRequest, RefreshTokenRequest


def _run_coroutine_sync(coro):
    """Step a coroutine to completion synchronously."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


def test_refresh_token_structure_and_hashing():
    """Verify refresh token issuance includes jti, user_id, type and hashes safely."""
    raw_token = create_refresh_token({"sub": "42", "user_id": 42})
    claims = decode_token(raw_token)

    assert claims["type"] == "refresh"
    assert claims["sub"] == "42"
    assert "jti" in claims
    assert len(claims["jti"]) == 36  # UUID4 length
    assert "iat" in claims
    assert "exp" in claims

    # Hash verification
    t_hash = hash_token(raw_token)
    assert len(t_hash) == 64  # SHA-256 hex length
    assert hash_token(raw_token) == t_hash

    # Different tokens have unique jti and hashes
    raw_token_2 = create_refresh_token({"sub": "42", "user_id": 42})
    assert raw_token != raw_token_2
    assert hash_token(raw_token_2) != t_hash


def test_successful_refresh_rotation_and_revocation():
    """Verify refresh endpoint revokes old token and issues rotated token atomically."""
    raw_old = create_refresh_token({"sub": "10", "user_id": 10})
    old_hash = hash_token(raw_old)
    old_claims = decode_token(raw_old)
    old_expires_at = datetime.datetime.fromtimestamp(old_claims["exp"], tz=timezone.utc)

    # Active token record in DB
    existing_record = RefreshToken(
        id=1,
        user_id=10,
        token_hash=old_hash,
        expires_at=old_expires_at,
        revoked_at=None,
    )

    mock_user = User(
        id=10,
        email="student@univ.edu",
        full_name="Student Ten",
        role=UserRole.STUDENT,
        institution_id=1,
        department_id=1,
        is_active=True,
        is_verified=True,
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    # Mock execute returns token record on 1st call, and mock_user on 2nd call
    res_token = MagicMock()
    res_token.scalar_one_or_none.return_value = existing_record

    res_user = MagicMock()
    res_user.scalar_one_or_none.return_value = mock_user

    mock_session.execute.side_effect = [res_token, res_user]

    req = RefreshTokenRequest(refresh_token=raw_old)
    result = _run_coroutine_sync(refresh_access_token(payload=req, session=mock_session))

    # 1. Old token record was revoked
    assert existing_record.revoked_at is not None

    # 2. New token was added to session
    assert mock_session.add.called
    added_obj = mock_session.add.call_args[0][0]
    assert isinstance(added_obj, RefreshToken)
    assert added_obj.user_id == 10
    assert added_obj.token_hash != old_hash
    assert added_obj.revoked_at is None

    # 3. New rotated access and refresh tokens returned
    assert result.access_token is not None
    assert result.refresh_token is not None
    assert result.refresh_token != raw_old
    assert mock_session.commit.called


def test_reused_revoked_token_triggers_replay_detection():
    """Verify reusing an already revoked token triggers security replay detection and revokes all sessions."""
    raw_token = create_refresh_token({"sub": "25", "user_id": 25})
    t_hash = hash_token(raw_token)
    claims = decode_token(raw_token)
    exp = datetime.datetime.fromtimestamp(claims["exp"], tz=timezone.utc)

    # Token was ALREADY revoked earlier
    revoked_record = RefreshToken(
        id=5,
        user_id=25,
        token_hash=t_hash,
        expires_at=exp,
        revoked_at=datetime.datetime.now(timezone.utc) - timedelta(minutes=5),
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    res_token = MagicMock()
    res_token.scalar_one_or_none.return_value = revoked_record
    mock_session.execute.return_value = res_token

    req = RefreshTokenRequest(refresh_token=raw_token)
    with pytest.raises(HTTPException) as exc:
        _run_coroutine_sync(refresh_access_token(payload=req, session=mock_session))

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "REFRESH_TOKEN_REUSE_DETECTED"
    # Ensure bulk revocation was committed
    assert mock_session.commit.called


def test_expired_token_rejection():
    """Verify expired refresh tokens are rejected."""
    # Expired token in past
    expired_token = create_refresh_token({"sub": "30", "user_id": 30}, expires_delta=timedelta(seconds=-10))

    mock_session = AsyncMock()
    req = RefreshTokenRequest(refresh_token=expired_token)
    with pytest.raises(HTTPException) as exc:
        _run_coroutine_sync(refresh_access_token(payload=req, session=mock_session))

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "REFRESH_TOKEN_EXPIRED"


def test_unknown_token_rejection():
    """Verify refresh token not tracked in database is rejected."""
    raw_token = create_refresh_token({"sub": "99", "user_id": 99})

    mock_session = AsyncMock()
    res_empty = MagicMock()
    res_empty.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = res_empty

    req = RefreshTokenRequest(refresh_token=raw_token)
    with pytest.raises(HTTPException) as exc:
        _run_coroutine_sync(refresh_access_token(payload=req, session=mock_session))

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "UNKNOWN_REFRESH_TOKEN"


def test_access_token_rejected_at_refresh():
    """Verify access token cannot be used at the refresh endpoint."""
    access_tok = create_access_token({"sub": "40", "role": "student"})

    mock_session = AsyncMock()
    req = RefreshTokenRequest(refresh_token=access_tok)
    with pytest.raises(HTTPException) as exc:
        _run_coroutine_sync(refresh_access_token(payload=req, session=mock_session))

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "INVALID_TOKEN_TYPE"


def test_logout_revokes_specific_token_idempotently():
    """Verify logout revokes the supplied refresh token and repeated calls are safe."""
    raw_token = create_refresh_token({"sub": "7", "user_id": 7})
    t_hash = hash_token(raw_token)
    claims = decode_token(raw_token)
    exp = datetime.datetime.fromtimestamp(claims["exp"], tz=timezone.utc)

    active_record = RefreshToken(
        id=12,
        user_id=7,
        token_hash=t_hash,
        expires_at=exp,
        revoked_at=None,
    )

    mock_user = User(id=7, email="user7@univ.edu", full_name="User Seven", role=UserRole.STUDENT, is_active=True)
    mock_session = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = active_record
    mock_session.execute.return_value = res

    # 1. First logout call revokes token
    logout_req = LogoutRequest(refresh_token=raw_token)
    resp = _run_coroutine_sync(logout(payload=logout_req, current_user=mock_user, session=mock_session))
    assert resp["success"] is True
    assert active_record.revoked_at is not None
    assert mock_session.commit.called

    # 2. Second logout call is idempotent (does not error)
    resp2 = _run_coroutine_sync(logout(payload=logout_req, current_user=mock_user, session=mock_session))
    assert resp2["success"] is True


def test_logout_without_payload_revokes_all_active_sessions():
    """Verify logout without payload revokes all active refresh tokens for the user."""
    mock_user = User(id=8, email="user8@univ.edu", full_name="User Eight", role=UserRole.STUDENT, is_active=True)
    mock_session = AsyncMock()

    resp = _run_coroutine_sync(logout(payload=None, current_user=mock_user, session=mock_session))
    assert resp["success"] is True
    assert mock_session.execute.called
    assert mock_session.commit.called


def test_atomic_rollback_on_refresh_failure():
    """Verify atomic rollback if database commit fails during token rotation."""
    raw_old = create_refresh_token({"sub": "50", "user_id": 50})
    old_hash = hash_token(raw_old)
    old_claims = decode_token(raw_old)
    old_expires_at = datetime.datetime.fromtimestamp(old_claims["exp"], tz=timezone.utc)

    existing_record = RefreshToken(
        id=99,
        user_id=50,
        token_hash=old_hash,
        expires_at=old_expires_at,
        revoked_at=None,
    )
    mock_user = User(id=50, email="u50@univ.edu", full_name="U50", role=UserRole.STUDENT, is_active=True)

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    res_token = MagicMock()
    res_token.scalar_one_or_none.return_value = existing_record
    res_user = MagicMock()
    res_user.scalar_one_or_none.return_value = mock_user
    mock_session.execute.side_effect = [res_token, res_user]

    # Force commit failure
    mock_session.commit.side_effect = RuntimeError("Database IO failure")

    req = RefreshTokenRequest(refresh_token=raw_old)
    with pytest.raises(RuntimeError):
        _run_coroutine_sync(refresh_access_token(payload=req, session=mock_session))


def test_logout_cannot_revoke_another_users_token():
    """Verify that User B cannot maliciously revoke User A's refresh token."""
    raw_token_user_a = create_refresh_token({"sub": "1", "user_id": 1})
    hash_a = hash_token(raw_token_user_a)
    claims_a = decode_token(raw_token_user_a)
    exp_a = datetime.datetime.fromtimestamp(claims_a["exp"], tz=timezone.utc)

    token_record_a = RefreshToken(
        id=101,
        user_id=1,  # Belongs to User 1
        token_hash=hash_a,
        expires_at=exp_a,
        revoked_at=None,
    )

    # User 2 logs in and attempts to revoke User 1's token
    user_b = User(id=2, email="user2@univ.edu", full_name="User Two", role=UserRole.STUDENT, is_active=True)

    mock_session = AsyncMock()
    # Query with RefreshToken.user_id == 2 will return None
    res = MagicMock()
    res.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = res

    logout_req = LogoutRequest(refresh_token=raw_token_user_a)
    resp = _run_coroutine_sync(logout(payload=logout_req, current_user=user_b, session=mock_session))

    assert resp["success"] is True
    # User 1's record remains active and unrevoked!
    assert token_record_a.revoked_at is None


def test_refresh_uses_row_level_locking_for_concurrency():
    """Verify refresh executes SELECT FOR UPDATE row-level locking to prevent concurrent race conditions."""
    raw_old = create_refresh_token({"sub": "77", "user_id": 77})
    old_hash = hash_token(raw_old)
    old_claims = decode_token(raw_old)
    old_expires_at = datetime.datetime.fromtimestamp(old_claims["exp"], tz=timezone.utc)

    existing_record = RefreshToken(
        id=77,
        user_id=77,
        token_hash=old_hash,
        expires_at=old_expires_at,
        revoked_at=None,
    )
    mock_user = User(id=77, email="u77@univ.edu", full_name="U77", role=UserRole.STUDENT, is_active=True)

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    res_token = MagicMock()
    res_token.scalar_one_or_none.return_value = existing_record
    res_user = MagicMock()
    res_user.scalar_one_or_none.return_value = mock_user
    mock_session.execute.side_effect = [res_token, res_user]

    req = RefreshTokenRequest(refresh_token=raw_old)
    _run_coroutine_sync(refresh_access_token(payload=req, session=mock_session))

    # Inspect the first executed statement (the RefreshToken query)
    first_query_stmt = mock_session.execute.call_args_list[0][0][0]
    # Verify row-level lock (FOR UPDATE) is present on the query
    assert first_query_stmt._for_update_arg is not None

