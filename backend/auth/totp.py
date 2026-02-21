"""TOTP (Time-based One-Time Password) support for 2FA."""

import base64
import io
from typing import Optional

import pyotp
import qrcode


def generate_totp_secret() -> str:
    """Generate a random TOTP secret.

    Returns:
        Base32-encoded secret suitable for authenticator apps.
    """
    return pyotp.random_base32()


def generate_totp_qr_uri(
    secret: str,
    email: str,
    issuer: str = "Infographix",
) -> str:
    """Generate a TOTP provisioning URI for QR codes.

    Args:
        secret: TOTP secret.
        email: User's email address.
        issuer: Application name shown in authenticator.

    Returns:
        otpauth:// URI for QR code generation.
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def get_totp_qr_code(
    secret: str,
    email: str,
    issuer: str = "Infographix",
) -> str:
    """Generate a QR code image as base64 data URI.

    Args:
        secret: TOTP secret.
        email: User's email address.
        issuer: Application name.

    Returns:
        Data URI string (data:image/png;base64,...).
    """
    uri = generate_totp_qr_uri(secret, email, issuer)

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)

    # Create image
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return f"data:image/png;base64,{img_base64}"


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    """Verify a TOTP code.

    Args:
        secret: TOTP secret.
        code: 6-digit code from authenticator app.
        window: Number of time steps to allow (1 = 30s before/after).

    Returns:
        True if code is valid, False otherwise.
    """
    if not code or not secret:
        return False

    # Normalize code (remove spaces, dashes)
    code = code.replace(" ", "").replace("-", "")

    # Must be 6 digits
    if not code.isdigit() or len(code) != 6:
        return False

    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=window)
    except Exception:
        return False


def generate_backup_codes(count: int = 10) -> list[str]:
    """Generate backup codes for account recovery.

    Args:
        count: Number of codes to generate.

    Returns:
        List of 8-character alphanumeric codes.
    """
    import secrets
    import string

    alphabet = string.ascii_lowercase + string.digits
    # Remove confusing characters
    alphabet = alphabet.replace("0", "").replace("o", "").replace("l", "").replace("1", "")

    codes = []
    for _ in range(count):
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        # Format as xxxx-xxxx for readability
        codes.append(f"{code[:4]}-{code[4:]}")

    return codes


def hash_backup_code(code: str) -> str:
    """Hash a backup code for storage.

    Args:
        code: Backup code (with or without dash).

    Returns:
        SHA-256 hash.
    """
    import hashlib
    # Normalize: lowercase, no dashes
    normalized = code.lower().replace("-", "")
    return hashlib.sha256(normalized.encode()).hexdigest()
