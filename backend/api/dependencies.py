"""FastAPI dependencies for authentication, authorization, and more."""

import hashlib
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.base import get_db
from backend.db.models import User, Session as UserSession, APIKey, PlanType


def hash_token(token: str) -> str:
    """Hash a token for lookup."""
    return hashlib.sha256(token.encode()).hexdigest()


async def get_token_from_header(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> tuple[str | None, str]:
    """Extract token from Authorization header or X-API-Key.

    Returns:
        Tuple of (token, type) where type is "bearer" or "api_key".
    """
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:], "bearer"
    if x_api_key:
        return x_api_key, "api_key"
    return None, ""


async def get_current_user(
    db: Session = Depends(get_db),
    token_info: tuple[str | None, str] = Depends(get_token_from_header),
) -> User:
    """Get the current authenticated user.

    Supports both Bearer tokens (sessions) and API keys.

    Raises:
        HTTPException: If not authenticated or token is invalid.
    """
    token, token_type = token_info

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_hash = hash_token(token)

    if token_type == "bearer":
        # Session-based authentication
        session = db.query(UserSession).filter(
            UserSession.token_hash == token_hash,
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        # Check expiration
        if session.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            )

        # Update last used
        session.last_used_at = datetime.utcnow()
        db.commit()

        user = session.user

    elif token_type == "api_key":
        # API key authentication
        api_key = db.query(APIKey).filter(
            APIKey.key_hash == token_hash,
            APIKey.is_active == True,
        ).first()

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key expired",
            )

        # Update usage
        api_key.last_used_at = datetime.utcnow()
        api_key.request_count += 1
        db.commit()

        user = api_key.user

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication method",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    return user


async def get_optional_user(
    db: Session = Depends(get_db),
    token_info: tuple[str | None, str] = Depends(get_token_from_header),
) -> User | None:
    """Get the current user if authenticated, None otherwise."""
    try:
        return await get_current_user(db, token_info)
    except HTTPException:
        return None


async def check_credits(
    current_user: User = Depends(get_current_user),
) -> None:
    """Check if user has available credits.

    Raises:
        HTTPException: If user has no credits remaining.
    """
    if current_user.credits_remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="No credits remaining. Please upgrade your plan.",
        )


async def require_pro(
    current_user: User = Depends(get_current_user),
) -> None:
    """Require Pro or Enterprise plan.

    Raises:
        HTTPException: If user is on Free plan.
    """
    if not current_user.is_pro:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires a Pro plan",
        )


async def require_enterprise(
    current_user: User = Depends(get_current_user),
) -> None:
    """Require Enterprise plan.

    Raises:
        HTTPException: If user is not on Enterprise plan.
    """
    if not current_user.is_enterprise:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires an Enterprise plan",
        )


def require_scope(scope: str):
    """Create a dependency that requires a specific API key scope.

    Args:
        scope: Required scope (e.g., "generate", "templates").

    Returns:
        Dependency function.
    """
    async def check_scope(
        db: Session = Depends(get_db),
        token_info: tuple[str | None, str] = Depends(get_token_from_header),
    ) -> None:
        token, token_type = token_info

        if token_type != "api_key":
            # Bearer tokens have all scopes
            return

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )

        api_key = db.query(APIKey).filter(
            APIKey.key_hash == hash_token(token),
        ).first()

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

        if scope not in (api_key.scopes or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"API key does not have '{scope}' scope",
            )

    return check_scope


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
CreditCheck = Annotated[None, Depends(check_credits)]
ProRequired = Annotated[None, Depends(require_pro)]
EnterpriseRequired = Annotated[None, Depends(require_enterprise)]
