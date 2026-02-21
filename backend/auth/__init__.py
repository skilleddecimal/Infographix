"""Authentication module with enhanced security features."""

from backend.auth.password import hash_password, verify_password, check_password_strength
from backend.auth.tokens import (
    generate_token,
    hash_token,
    generate_verification_token,
    generate_reset_token,
)
from backend.auth.totp import (
    generate_totp_secret,
    generate_totp_qr_uri,
    verify_totp,
    get_totp_qr_code,
)
from backend.auth.brute_force import check_login_attempts, record_failed_attempt, clear_failed_attempts

__all__ = [
    "hash_password",
    "verify_password",
    "check_password_strength",
    "generate_token",
    "hash_token",
    "generate_verification_token",
    "generate_reset_token",
    "generate_totp_secret",
    "generate_totp_qr_uri",
    "verify_totp",
    "get_totp_qr_code",
    "check_login_attempts",
    "record_failed_attempt",
    "clear_failed_attempts",
]
