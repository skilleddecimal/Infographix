"""Password hashing and validation using bcrypt."""

import re
import bcrypt


# Bcrypt cost factor (12 is recommended for production)
BCRYPT_COST = 12


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password.

    Returns:
        Bcrypt hash string.
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=BCRYPT_COST)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash.

    Args:
        password: Plain text password to verify.
        password_hash: Bcrypt hash to check against.

    Returns:
        True if password matches, False otherwise.
    """
    try:
        password_bytes = password.encode("utf-8")
        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception:
        return False


def check_password_strength(password: str) -> dict:
    """Check password strength and return validation results.

    Args:
        password: Password to check.

    Returns:
        Dict with 'valid' bool and list of 'errors'.
    """
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    if len(password) > 128:
        errors.append("Password must be less than 128 characters")

    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    if not re.search(r"\d", password):
        errors.append("Password must contain at least one number")

    # Check for common passwords
    common_passwords = {
        "password", "12345678", "qwerty123", "admin123",
        "letmein", "welcome", "password1", "Password1",
    }
    if password.lower() in common_passwords:
        errors.append("Password is too common")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "strength": _calculate_strength(password, errors),
    }


def _calculate_strength(password: str, errors: list) -> str:
    """Calculate password strength level.

    Returns:
        'weak', 'fair', 'good', or 'strong'.
    """
    if errors:
        return "weak"

    score = 0

    # Length bonus
    if len(password) >= 12:
        score += 2
    elif len(password) >= 10:
        score += 1

    # Complexity
    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        score += 2

    # Mixed case and numbers
    if re.search(r"[a-z]", password) and re.search(r"[A-Z]", password):
        score += 1
    if re.search(r"\d", password):
        score += 1

    if score >= 5:
        return "strong"
    elif score >= 3:
        return "good"
    elif score >= 1:
        return "fair"
    return "weak"


def needs_rehash(password_hash: str) -> bool:
    """Check if a password hash needs to be rehashed.

    This is useful for upgrading from SHA256 to bcrypt or
    increasing the cost factor.

    Args:
        password_hash: Existing hash to check.

    Returns:
        True if hash should be regenerated.
    """
    # SHA256 hashes are 64 hex chars
    if len(password_hash) == 64 and all(c in "0123456789abcdef" for c in password_hash):
        return True

    # Check if bcrypt cost is outdated
    if password_hash.startswith("$2"):
        try:
            # Extract cost factor from bcrypt hash
            parts = password_hash.split("$")
            if len(parts) >= 3:
                cost = int(parts[2])
                if cost < BCRYPT_COST:
                    return True
        except (ValueError, IndexError):
            pass

    return False
