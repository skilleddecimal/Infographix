"""Brute force protection for login attempts."""

import hashlib
from datetime import datetime, timedelta
from typing import Optional

# In-memory store for failed attempts (use Redis in production)
_failed_attempts: dict[str, list[datetime]] = {}

# Configuration
MAX_ATTEMPTS = 5  # Maximum failed attempts before lockout
LOCKOUT_MINUTES = 15  # Lockout duration
ATTEMPT_WINDOW_MINUTES = 15  # Window for counting attempts


def _get_key(identifier: str) -> str:
    """Get cache key for an identifier (email or IP)."""
    return hashlib.sha256(identifier.lower().encode()).hexdigest()[:16]


def _cleanup_old_attempts(key: str) -> None:
    """Remove attempts older than the window."""
    if key not in _failed_attempts:
        return

    cutoff = datetime.utcnow() - timedelta(minutes=ATTEMPT_WINDOW_MINUTES)
    _failed_attempts[key] = [
        attempt for attempt in _failed_attempts[key]
        if attempt > cutoff
    ]

    if not _failed_attempts[key]:
        del _failed_attempts[key]


def check_login_attempts(
    email: str,
    ip_address: Optional[str] = None,
) -> dict:
    """Check if login attempts are allowed.

    Args:
        email: User email being attempted.
        ip_address: Client IP address.

    Returns:
        Dict with 'allowed' bool, 'attempts_remaining', and optional 'locked_until'.
    """
    email_key = _get_key(email)
    _cleanup_old_attempts(email_key)

    attempts = _failed_attempts.get(email_key, [])

    if len(attempts) >= MAX_ATTEMPTS:
        # Check if still in lockout period
        last_attempt = max(attempts)
        locked_until = last_attempt + timedelta(minutes=LOCKOUT_MINUTES)

        if datetime.utcnow() < locked_until:
            return {
                "allowed": False,
                "attempts_remaining": 0,
                "locked_until": locked_until.isoformat(),
                "message": f"Account locked. Try again in {LOCKOUT_MINUTES} minutes.",
            }
        else:
            # Lockout expired, clear attempts
            _failed_attempts.pop(email_key, None)
            attempts = []

    # Also check IP-based rate limiting
    if ip_address:
        ip_key = _get_key(ip_address)
        _cleanup_old_attempts(ip_key)
        ip_attempts = _failed_attempts.get(ip_key, [])

        # IP limit is higher (20 attempts) to avoid blocking shared IPs
        if len(ip_attempts) >= 20:
            last_ip_attempt = max(ip_attempts)
            ip_locked_until = last_ip_attempt + timedelta(minutes=LOCKOUT_MINUTES)

            if datetime.utcnow() < ip_locked_until:
                return {
                    "allowed": False,
                    "attempts_remaining": 0,
                    "locked_until": ip_locked_until.isoformat(),
                    "message": "Too many login attempts from this location.",
                }

    return {
        "allowed": True,
        "attempts_remaining": MAX_ATTEMPTS - len(attempts),
    }


def record_failed_attempt(
    email: str,
    ip_address: Optional[str] = None,
) -> dict:
    """Record a failed login attempt.

    Args:
        email: Email that failed login.
        ip_address: Client IP address.

    Returns:
        Updated attempt status.
    """
    now = datetime.utcnow()

    email_key = _get_key(email)
    if email_key not in _failed_attempts:
        _failed_attempts[email_key] = []
    _failed_attempts[email_key].append(now)

    if ip_address:
        ip_key = _get_key(ip_address)
        if ip_key not in _failed_attempts:
            _failed_attempts[ip_key] = []
        _failed_attempts[ip_key].append(now)

    return check_login_attempts(email, ip_address)


def clear_failed_attempts(
    email: str,
    ip_address: Optional[str] = None,
) -> None:
    """Clear failed attempts after successful login.

    Args:
        email: Email to clear.
        ip_address: IP address to clear.
    """
    email_key = _get_key(email)
    _failed_attempts.pop(email_key, None)

    # Don't clear IP attempts to maintain some protection


def get_lockout_status(email: str) -> Optional[dict]:
    """Get current lockout status for an email.

    Args:
        email: Email to check.

    Returns:
        Dict with lockout info or None if not locked.
    """
    result = check_login_attempts(email)
    if not result["allowed"]:
        return result
    return None


# For testing: reset all state
def _reset_for_testing() -> None:
    """Clear all stored attempts. Only for testing."""
    global _failed_attempts
    _failed_attempts = {}
