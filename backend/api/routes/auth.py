"""Authentication routes with enhanced security features."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from backend.db.base import get_db
from backend.db.models import User, Session as UserSession, APIKey
from backend.auth import (
    hash_password,
    verify_password,
    check_password_strength,
    generate_token,
    hash_token,
    generate_verification_token,
    generate_reset_token,
    generate_totp_secret,
    generate_totp_qr_uri,
    verify_totp,
    get_totp_qr_code,
    check_login_attempts,
    record_failed_attempt,
    clear_failed_attempts,
)
from backend.auth.totp import generate_backup_codes, hash_backup_code
from backend.auth.tokens import generate_session_tokens, generate_api_key
from backend.api.dependencies import get_current_user, CurrentUser

router = APIRouter()


# Request/Response Models
class RegisterRequest(BaseModel):
    """Registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str | None = None


class LoginRequest(BaseModel):
    """Login request."""
    email: EmailStr
    password: str
    totp_code: str | None = None


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    requires_2fa: bool = False


class UserResponse(BaseModel):
    """User response."""
    id: str
    email: str
    name: str | None
    plan: str
    credits_remaining: int
    is_verified: bool
    totp_enabled: bool
    created_at: str


class RefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    """Email verification request."""
    token: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request."""
    token: str
    new_password: str = Field(..., min_length=8)


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class Enable2FAResponse(BaseModel):
    """2FA setup response."""
    secret: str
    qr_code: str
    backup_codes: list[str]


class Verify2FARequest(BaseModel):
    """2FA verification request."""
    code: str


class APIKeyCreate(BaseModel):
    """API key creation request."""
    name: str = Field(..., min_length=1, max_length=100)
    scopes: list[str] = ["generate", "templates", "download"]


class APIKeyResponse(BaseModel):
    """API key response."""
    id: str
    name: str
    key: str | None = None
    scopes: list[str]
    created_at: str
    last_used_at: str | None


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    """Register a new user with email and password."""
    # Check password strength
    strength = check_password_strength(request.password)
    if not strength["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password too weak", "errors": strength["errors"]},
        )

    # Check if email exists
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create user with bcrypt hashed password
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        name=request.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate verification token
    verification = generate_verification_token()
    user.verification_token_hash = verification.token_hash
    user.verification_token_expires_at = verification.expires_at
    db.commit()

    # TODO: Send verification email with verification.token
    # For now, we'll just log it (in production, use email service)
    print(f"[DEV] Verification token for {user.email}: {verification.token}")

    # Create session
    access_data, refresh_data = generate_session_tokens()

    session = UserSession(
        user_id=user.id,
        token_hash=access_data.token_hash,
        refresh_token_hash=refresh_data.token_hash,
        expires_at=access_data.expires_at,
        refresh_expires_at=refresh_data.expires_at,
    )
    db.add(session)
    db.commit()

    return TokenResponse(
        access_token=access_data.token,
        refresh_token=refresh_data.token,
        expires_in=900,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    """Login with email and password."""
    client_ip = get_client_ip(http_request)

    # Check brute force protection
    attempt_status = check_login_attempts(request.email, client_ip)
    if not attempt_status["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=attempt_status["message"],
            headers={"Retry-After": "900"},
        )

    user = db.query(User).filter(User.email == request.email).first()

    if not user or not user.password_hash:
        record_failed_attempt(request.email, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not verify_password(request.password, user.password_hash):
        status_info = record_failed_attempt(request.email, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid credentials. {status_info.get('attempts_remaining', 0)} attempts remaining.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Check 2FA if enabled
    if user.totp_enabled:
        if not request.totp_code:
            # Return a response indicating 2FA is required
            return TokenResponse(
                access_token="",
                refresh_token="",
                expires_in=0,
                requires_2fa=True,
            )

        # Verify TOTP code
        if not verify_totp(user.totp_secret, request.totp_code):
            # Check backup codes
            if not _verify_backup_code(user, request.totp_code, db):
                record_failed_attempt(request.email, client_ip)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid 2FA code",
                )

    # Clear failed attempts on successful login
    clear_failed_attempts(request.email, client_ip)

    # Update last login
    user.last_login_at = datetime.utcnow()

    # Create session
    access_data, refresh_data = generate_session_tokens()

    session = UserSession(
        user_id=user.id,
        token_hash=access_data.token_hash,
        refresh_token_hash=refresh_data.token_hash,
        expires_at=access_data.expires_at,
        refresh_expires_at=refresh_data.expires_at,
        ip_address=client_ip,
        user_agent=http_request.headers.get("User-Agent"),
    )
    db.add(session)
    db.commit()

    return TokenResponse(
        access_token=access_data.token,
        refresh_token=refresh_data.token,
        expires_in=900,
    )


def _verify_backup_code(user: User, code: str, db: Session) -> bool:
    """Verify and consume a backup code."""
    if not user.totp_backup_codes:
        return False

    code_hash = hash_backup_code(code)
    backup_codes = list(user.totp_backup_codes)

    if code_hash in backup_codes:
        backup_codes.remove(code_hash)
        user.totp_backup_codes = backup_codes
        db.commit()
        return True

    return False


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    db: Session = Depends(get_db),
):
    """Refresh access token using refresh token."""
    session = db.query(UserSession).filter(
        UserSession.refresh_token_hash == hash_token(request.refresh_token),
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if session.refresh_expires_at and session.refresh_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )

    # Generate new tokens
    access_data, refresh_data = generate_session_tokens()

    # Update session
    session.token_hash = access_data.token_hash
    session.refresh_token_hash = refresh_data.token_hash
    session.expires_at = access_data.expires_at
    session.refresh_expires_at = refresh_data.expires_at
    session.last_used_at = datetime.utcnow()

    db.commit()

    return TokenResponse(
        access_token=access_data.token,
        refresh_token=refresh_data.token,
        expires_in=900,
    )


@router.post("/logout")
async def logout(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    authorization: str | None = None,
):
    """Logout and invalidate current session."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        session = db.query(UserSession).filter(
            UserSession.token_hash == hash_token(token),
        ).first()

        if session:
            db.delete(session)
            db.commit()

    return {"status": "logged_out"}


@router.post("/logout-all")
async def logout_all_sessions(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Logout from all sessions (except current)."""
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
    ).delete()
    db.commit()

    return {"status": "all_sessions_logged_out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser,
):
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        plan=current_user.plan.value,
        credits_remaining=current_user.credits_remaining,
        is_verified=current_user.is_verified,
        totp_enabled=current_user.totp_enabled,
        created_at=current_user.created_at.isoformat(),
    )


# Email Verification
@router.post("/verify-email")
async def verify_email(
    request: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    """Verify email address with token."""
    token_hash = hash_token(request.token)

    user = db.query(User).filter(
        User.verification_token_hash == token_hash,
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    if user.verification_token_expires_at and \
       user.verification_token_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token expired",
        )

    # Verify user
    user.is_verified = True
    user.verified_at = datetime.utcnow()
    user.verification_token_hash = None
    user.verification_token_expires_at = None
    db.commit()

    return {"status": "email_verified"}


@router.post("/resend-verification")
async def resend_verification_email(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Resend verification email."""
    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified",
        )

    verification = generate_verification_token()
    current_user.verification_token_hash = verification.token_hash
    current_user.verification_token_expires_at = verification.expires_at
    db.commit()

    # TODO: Send verification email
    print(f"[DEV] Verification token for {current_user.email}: {verification.token}")

    return {"status": "verification_email_sent"}


# Password Reset
@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """Request password reset email."""
    user = db.query(User).filter(User.email == request.email).first()

    # Always return success to prevent email enumeration
    if user and user.password_hash:  # Only for password users, not OAuth
        reset = generate_reset_token()
        user.reset_token_hash = reset.token_hash
        user.reset_token_expires_at = reset.expires_at
        db.commit()

        # TODO: Send reset email
        print(f"[DEV] Reset token for {user.email}: {reset.token}")

    return {"status": "reset_email_sent_if_account_exists"}


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Reset password with token."""
    # Check password strength
    strength = check_password_strength(request.new_password)
    if not strength["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password too weak", "errors": strength["errors"]},
        )

    token_hash = hash_token(request.token)

    user = db.query(User).filter(
        User.reset_token_hash == token_hash,
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )

    if user.reset_token_expires_at and \
       user.reset_token_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token expired",
        )

    # Update password
    user.password_hash = hash_password(request.new_password)
    user.reset_token_hash = None
    user.reset_token_expires_at = None

    # Invalidate all sessions (security measure)
    db.query(UserSession).filter(UserSession.user_id == user.id).delete()

    db.commit()

    return {"status": "password_reset_successful"}


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Change password for authenticated user."""
    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change password for OAuth account",
        )

    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Check password strength
    strength = check_password_strength(request.new_password)
    if not strength["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password too weak", "errors": strength["errors"]},
        )

    # Update password
    current_user.password_hash = hash_password(request.new_password)

    # Invalidate all other sessions
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
    ).delete()

    # Create new session for current user
    access_data, refresh_data = generate_session_tokens()
    session = UserSession(
        user_id=current_user.id,
        token_hash=access_data.token_hash,
        refresh_token_hash=refresh_data.token_hash,
        expires_at=access_data.expires_at,
        refresh_expires_at=refresh_data.expires_at,
    )
    db.add(session)
    db.commit()

    return {
        "status": "password_changed",
        "access_token": access_data.token,
        "refresh_token": refresh_data.token,
    }


# 2FA (TOTP)
@router.post("/2fa/setup", response_model=Enable2FAResponse)
async def setup_2fa(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Begin 2FA setup process."""
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled",
        )

    # Generate TOTP secret
    secret = generate_totp_secret()
    current_user.totp_secret = secret

    # Generate backup codes
    backup_codes = generate_backup_codes(10)
    current_user.totp_backup_codes = [hash_backup_code(code) for code in backup_codes]

    db.commit()

    # Generate QR code
    qr_code = get_totp_qr_code(secret, current_user.email)

    return Enable2FAResponse(
        secret=secret,
        qr_code=qr_code,
        backup_codes=backup_codes,
    )


@router.post("/2fa/enable")
async def enable_2fa(
    request: Verify2FARequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Enable 2FA after verifying setup code."""
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled",
        )

    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup not started. Call /2fa/setup first.",
        )

    if not verify_totp(current_user.totp_secret, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    current_user.totp_enabled = True
    db.commit()

    return {"status": "2fa_enabled"}


@router.post("/2fa/disable")
async def disable_2fa(
    request: Verify2FARequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Disable 2FA."""
    if not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled",
        )

    if not verify_totp(current_user.totp_secret, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    current_user.totp_enabled = False
    current_user.totp_secret = None
    current_user.totp_backup_codes = None
    db.commit()

    return {"status": "2fa_disabled"}


@router.post("/2fa/backup-codes")
async def regenerate_backup_codes(
    request: Verify2FARequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Regenerate backup codes (requires 2FA verification)."""
    if not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled",
        )

    if not verify_totp(current_user.totp_secret, request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    backup_codes = generate_backup_codes(10)
    current_user.totp_backup_codes = [hash_backup_code(code) for code in backup_codes]
    db.commit()

    return {"backup_codes": backup_codes}


# API Keys
@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """List user's API keys."""
    keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
        APIKey.is_active == True,
    ).all()

    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            scopes=key.scopes or [],
            created_at=key.created_at.isoformat(),
            last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
        )
        for key in keys
    ]


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Create a new API key."""
    key, key_hash = generate_api_key()

    api_key = APIKey(
        user_id=current_user.id,
        name=request.name,
        key_hash=key_hash,
        scopes=request.scopes,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=key,  # Only shown once
        scopes=api_key.scopes or [],
        created_at=api_key.created_at.isoformat(),
        last_used_at=None,
    )


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Delete an API key."""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id,
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    db.delete(api_key)
    db.commit()

    return {"status": "api_key_deleted"}
