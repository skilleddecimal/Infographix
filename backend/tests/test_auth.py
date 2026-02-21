"""Tests for authentication module."""

import pytest
from datetime import datetime, timedelta

from backend.auth.password import (
    hash_password,
    verify_password,
    check_password_strength,
    needs_rehash,
)
from backend.auth.tokens import (
    generate_token,
    hash_token,
    generate_verification_token,
    generate_reset_token,
    generate_session_tokens,
    generate_api_key,
)
from backend.auth.totp import (
    generate_totp_secret,
    generate_totp_qr_uri,
    verify_totp,
    generate_backup_codes,
    hash_backup_code,
)
from backend.auth.brute_force import (
    check_login_attempts,
    record_failed_attempt,
    clear_failed_attempts,
    _reset_for_testing,
)


class TestPasswordHashing:
    """Test bcrypt password hashing."""

    def test_hash_password_returns_bcrypt_hash(self):
        """Password hash should be bcrypt format."""
        hashed = hash_password("TestPassword123")
        assert hashed.startswith("$2")  # bcrypt prefix
        assert len(hashed) == 60  # bcrypt hash length

    def test_verify_password_correct(self):
        """Correct password should verify."""
        password = "MySecurePassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Incorrect password should not verify."""
        hashed = hash_password("CorrectPassword")
        assert verify_password("WrongPassword", hashed) is False

    def test_verify_password_handles_invalid_hash(self):
        """Should handle invalid hash gracefully."""
        assert verify_password("password", "invalid_hash") is False

    def test_check_password_strength_weak(self):
        """Weak passwords should be rejected."""
        result = check_password_strength("short")
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert result["strength"] == "weak"

    def test_check_password_strength_no_uppercase(self):
        """Password without uppercase should be rejected."""
        result = check_password_strength("alllowercase123")
        assert result["valid"] is False
        assert "uppercase" in result["errors"][0].lower()

    def test_check_password_strength_no_number(self):
        """Password without number should be rejected."""
        result = check_password_strength("NoNumbersHere")
        assert result["valid"] is False
        assert "number" in result["errors"][0].lower()

    def test_check_password_strength_common_password(self):
        """Common passwords should be rejected."""
        result = check_password_strength("password")
        assert result["valid"] is False

    def test_check_password_strength_strong(self):
        """Strong password should pass."""
        result = check_password_strength("MyStr0ngP@ssword!")
        assert result["valid"] is True
        assert result["strength"] in ["good", "strong"]

    def test_needs_rehash_sha256(self):
        """SHA256 hashes should need rehash."""
        sha256_hash = "a" * 64  # 64 hex chars
        assert needs_rehash(sha256_hash) is True

    def test_needs_rehash_bcrypt(self):
        """Current bcrypt hashes should not need rehash."""
        bcrypt_hash = hash_password("test")
        assert needs_rehash(bcrypt_hash) is False


class TestTokenGeneration:
    """Test token generation utilities."""

    def test_generate_token_length(self):
        """Generated token should be URL-safe."""
        token = generate_token(32)
        assert len(token) > 32  # Base64 encoding increases length
        assert "/" not in token  # URL-safe

    def test_generate_token_unique(self):
        """Each token should be unique."""
        tokens = [generate_token() for _ in range(100)]
        assert len(set(tokens)) == 100

    def test_hash_token(self):
        """Token hash should be consistent."""
        token = "my_secret_token"
        hash1 = hash_token(token)
        hash2 = hash_token(token)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_generate_verification_token(self):
        """Verification token should have correct expiry."""
        data = generate_verification_token(24)
        assert data.token
        assert data.token_hash
        assert data.expires_at > datetime.utcnow()
        assert data.expires_at < datetime.utcnow() + timedelta(hours=25)

    def test_generate_reset_token(self):
        """Reset token should have short expiry."""
        data = generate_reset_token(1)
        assert data.token
        assert data.expires_at < datetime.utcnow() + timedelta(hours=2)

    def test_generate_session_tokens(self):
        """Session tokens should have correct expiries."""
        access, refresh = generate_session_tokens()
        assert access.token
        assert refresh.token
        assert access.expires_at < refresh.expires_at

    def test_generate_api_key(self):
        """API key should have prefix and be hashable."""
        key, key_hash = generate_api_key()
        assert key.startswith("ig_")
        assert len(key_hash) == 64
        assert hash_token(key) == key_hash


class TestTOTP:
    """Test TOTP (2FA) functionality."""

    def test_generate_totp_secret(self):
        """TOTP secret should be base32 encoded."""
        secret = generate_totp_secret()
        assert len(secret) == 32
        # Base32 characters only
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in secret)

    def test_generate_totp_qr_uri(self):
        """QR URI should be properly formatted."""
        secret = generate_totp_secret()
        uri = generate_totp_qr_uri(secret, "test@example.com")
        assert uri.startswith("otpauth://totp/")
        assert "Infographix" in uri
        # Email is URL-encoded, @ becomes %40
        assert "test%40example.com" in uri or "test@example.com" in uri

    def test_verify_totp_valid(self):
        """Valid TOTP code should verify."""
        import pyotp
        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        assert verify_totp(secret, code) is True

    def test_verify_totp_invalid(self):
        """Invalid TOTP code should not verify."""
        secret = generate_totp_secret()
        assert verify_totp(secret, "000000") is False
        assert verify_totp(secret, "invalid") is False
        assert verify_totp(secret, "") is False

    def test_generate_backup_codes(self):
        """Backup codes should be properly formatted."""
        codes = generate_backup_codes(10)
        assert len(codes) == 10
        for code in codes:
            assert "-" in code
            assert len(code) == 9  # xxxx-xxxx

    def test_backup_codes_unique(self):
        """Backup codes should be unique."""
        codes = generate_backup_codes(10)
        assert len(set(codes)) == 10

    def test_hash_backup_code_normalized(self):
        """Backup code hashing should normalize input."""
        hash1 = hash_backup_code("abcd-efgh")
        hash2 = hash_backup_code("ABCD-EFGH")
        hash3 = hash_backup_code("abcdefgh")
        assert hash1 == hash2 == hash3


class TestBruteForceProtection:
    """Test brute force protection."""

    def setup_method(self):
        """Reset state before each test."""
        _reset_for_testing()

    def test_first_attempt_allowed(self):
        """First login attempt should be allowed."""
        result = check_login_attempts("test@example.com")
        assert result["allowed"] is True
        assert result["attempts_remaining"] == 5

    def test_failed_attempts_decrease_remaining(self):
        """Failed attempts should decrease remaining count."""
        email = "test@example.com"
        record_failed_attempt(email)
        result = check_login_attempts(email)
        assert result["attempts_remaining"] == 4

    def test_lockout_after_max_attempts(self):
        """Should lock out after max failed attempts."""
        email = "locked@example.com"
        for _ in range(5):
            record_failed_attempt(email)

        result = check_login_attempts(email)
        assert result["allowed"] is False
        assert "locked_until" in result

    def test_clear_failed_attempts(self):
        """Clearing attempts should reset count."""
        email = "clear@example.com"
        record_failed_attempt(email)
        record_failed_attempt(email)
        clear_failed_attempts(email)

        result = check_login_attempts(email)
        assert result["attempts_remaining"] == 5

    def test_ip_based_limiting(self):
        """Should track attempts by IP as well."""
        ip = "192.168.1.1"
        for i in range(20):
            record_failed_attempt(f"user{i}@example.com", ip)

        # Next attempt from same IP should be blocked
        result = check_login_attempts("new@example.com", ip)
        assert result["allowed"] is False


class TestBillingPlans:
    """Test billing plans configuration."""

    def test_plan_limits_free(self):
        """Free plan should have limited resources."""
        from backend.billing.plans import get_plan_limits
        from backend.db.models import PlanType

        limits = get_plan_limits(PlanType.FREE)
        assert limits.generations_per_month == 10
        assert limits.variations_per_generation == 2
        assert limits.custom_templates is False
        assert limits.api_access is False

    def test_plan_limits_pro(self):
        """Pro plan should have more resources."""
        from backend.billing.plans import get_plan_limits
        from backend.db.models import PlanType

        limits = get_plan_limits(PlanType.PRO)
        assert limits.generations_per_month == 200
        assert limits.variations_per_generation == 10
        assert limits.custom_templates is True
        assert limits.api_access is True

    def test_can_export_format(self):
        """Should check export format permissions."""
        from backend.billing.plans import can_export_format
        from backend.db.models import PlanType

        # Free can only export PPTX
        assert can_export_format(PlanType.FREE, "pptx") is True
        assert can_export_format(PlanType.FREE, "pdf") is False

        # Pro can export all
        assert can_export_format(PlanType.PRO, "pptx") is True
        assert can_export_format(PlanType.PRO, "pdf") is True
        assert can_export_format(PlanType.PRO, "png") is True
