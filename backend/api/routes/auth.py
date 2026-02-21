"""Authentication routes."""

import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from backend.db.base import get_db
from backend.db.models import User, Session as UserSession, APIKey

router = APIRouter()

# Password hashing (use bcrypt in production)
def hash_password(password: str) -> str:
    """Hash a password."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against hash."""
    return hash_password(password) == password_hash


def generate_token() -> str:
    """Generate a secure token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


class RegisterRequest(BaseModel):
    """Registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str | None = None


class LoginRequest(BaseModel):
    """Login request."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """User response."""
    id: str
    email: str
    name: str | None
    plan: str
    credits_remaining: int
    is_verified: bool
    created_at: str


class RefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class APIKeyCreate(BaseModel):
    """API key creation request."""
    name: str = Field(..., min_length=1, max_length=100)
    scopes: list[str] = ["generate", "templates", "download"]


class APIKeyResponse(BaseModel):
    """API key response."""
    id: str
    name: str
    key: str | None = None  # Only returned on creation
    scopes: list[str]
    created_at: str
    last_used_at: str | None


@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    """Register a new user."""
    # Check if email exists
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create user
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        name=request.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create session
    access_token = generate_token()
    refresh_token = generate_token()

    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(access_token),
        refresh_token_hash=hash_token(refresh_token),
        expires_at=datetime.utcnow() + timedelta(minutes=15),
        refresh_expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(session)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=900,  # 15 minutes
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    """Login with email and password."""
    user = db.query(User).filter(User.email == request.email).first()

    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Update last login
    user.last_login_at = datetime.utcnow()

    # Create session
    access_token = generate_token()
    refresh_token = generate_token()

    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(access_token),
        refresh_token_hash=hash_token(refresh_token),
        expires_at=datetime.utcnow() + timedelta(minutes=15),
        refresh_expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(session)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=900,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    db: Session = Depends(get_db),
):
    """Refresh access token."""
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
    access_token = generate_token()
    new_refresh_token = generate_token()

    # Update session
    session.token_hash = hash_token(access_token)
    session.refresh_token_hash = hash_token(new_refresh_token)
    session.expires_at = datetime.utcnow() + timedelta(minutes=15)
    session.refresh_expires_at = datetime.utcnow() + timedelta(days=7)
    session.last_used_at = datetime.utcnow()

    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=900,
    )


@router.post("/logout")
async def logout(
    db: Session = Depends(get_db),
    authorization: str | None = None,
):
    """Logout and invalidate session."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"status": "logged_out"}

    token = authorization[7:]
    session = db.query(UserSession).filter(
        UserSession.token_hash == hash_token(token),
    ).first()

    if session:
        db.delete(session)
        db.commit()

    return {"status": "logged_out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    db: Session = Depends(get_db),
):
    """Get current user info."""
    from backend.api.dependencies import get_current_user_from_token

    # This would normally use the dependency
    # For now, return a placeholder
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    db: Session = Depends(get_db),
):
    """List user's API keys."""
    from backend.api.dependencies import get_current_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyCreate,
    db: Session = Depends(get_db),
):
    """Create a new API key."""
    from backend.api.dependencies import get_current_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    db: Session = Depends(get_db),
):
    """Delete an API key."""
    from backend.api.dependencies import get_current_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )
