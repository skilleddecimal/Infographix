"""Token generation and management."""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import NamedTuple


class TokenData(NamedTuple):
    """Token with metadata."""
    token: str
    token_hash: str
    expires_at: datetime


def generate_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token.

    Args:
        length: Number of bytes (actual string will be longer due to base64).

    Returns:
        URL-safe base64 encoded token.
    """
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    """Hash a token for secure storage.

    Uses SHA-256 which is sufficient for high-entropy tokens.

    Args:
        token: Token to hash.

    Returns:
        Hex-encoded SHA-256 hash.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def generate_verification_token(expires_hours: int = 24) -> TokenData:
    """Generate an email verification token.

    Args:
        expires_hours: Hours until token expires.

    Returns:
        TokenData with token, hash, and expiration.
    """
    token = generate_token(32)
    return TokenData(
        token=token,
        token_hash=hash_token(token),
        expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
    )


def generate_reset_token(expires_hours: int = 1) -> TokenData:
    """Generate a password reset token.

    Args:
        expires_hours: Hours until token expires (default 1 hour for security).

    Returns:
        TokenData with token, hash, and expiration.
    """
    token = generate_token(32)
    return TokenData(
        token=token,
        token_hash=hash_token(token),
        expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
    )


def generate_session_tokens(
    access_expires_minutes: int = 15,
    refresh_expires_days: int = 7,
) -> tuple[TokenData, TokenData]:
    """Generate access and refresh tokens for a session.

    Args:
        access_expires_minutes: Minutes until access token expires.
        refresh_expires_days: Days until refresh token expires.

    Returns:
        Tuple of (access_token_data, refresh_token_data).
    """
    access_token = generate_token(32)
    refresh_token = generate_token(32)

    access_data = TokenData(
        token=access_token,
        token_hash=hash_token(access_token),
        expires_at=datetime.utcnow() + timedelta(minutes=access_expires_minutes),
    )

    refresh_data = TokenData(
        token=refresh_token,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.utcnow() + timedelta(days=refresh_expires_days),
    )

    return access_data, refresh_data


def generate_api_key() -> tuple[str, str]:
    """Generate an API key.

    Returns:
        Tuple of (key, key_hash). Key is shown once, hash is stored.
    """
    # Use a prefix for easier identification
    prefix = "ig_"
    key_body = secrets.token_urlsafe(32)
    key = f"{prefix}{key_body}"

    return key, hash_token(key)
