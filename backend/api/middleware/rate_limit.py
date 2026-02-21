"""Rate limiting middleware."""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    # Requests per window
    requests_per_minute: int = 60
    requests_per_hour: int = 1000

    # Burst allowance
    burst_size: int = 10

    # Sliding window size
    window_size: int = 60  # seconds

    # Exempted paths (no rate limiting)
    exempt_paths: list[str] = field(default_factory=lambda: ["/health", "/ready"])


class InMemoryRateLimiter:
    """Simple in-memory rate limiter using sliding window.

    For production, use Redis-based rate limiting.
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.time()

    def is_allowed(self, key: str) -> tuple[bool, dict]:
        """Check if request is allowed.

        Args:
            key: Rate limit key (e.g., IP address or user ID).

        Returns:
            Tuple of (allowed, info dict with limits).
        """
        now = time.time()

        # Cleanup old entries periodically
        if now - self._last_cleanup > 60:
            self._cleanup()
            self._last_cleanup = now

        # Get request timestamps for this key
        timestamps = self._requests[key]

        # Remove old timestamps outside window
        window_start = now - self.config.window_size
        timestamps = [t for t in timestamps if t > window_start]
        self._requests[key] = timestamps

        # Check rate limit
        request_count = len(timestamps)
        limit = self.config.requests_per_minute

        if request_count >= limit:
            retry_after = int(timestamps[0] + self.config.window_size - now) + 1
            return False, {
                "limit": limit,
                "remaining": 0,
                "reset": int(timestamps[0] + self.config.window_size),
                "retry_after": retry_after,
            }

        # Add current request
        timestamps.append(now)
        self._requests[key] = timestamps

        return True, {
            "limit": limit,
            "remaining": limit - request_count - 1,
            "reset": int(now + self.config.window_size),
        }

    def _cleanup(self):
        """Remove expired entries."""
        now = time.time()
        window_start = now - self.config.window_size

        keys_to_remove = []
        for key, timestamps in self._requests.items():
            # Remove old timestamps
            timestamps = [t for t in timestamps if t > window_start]
            if not timestamps:
                keys_to_remove.append(key)
            else:
                self._requests[key] = timestamps

        for key in keys_to_remove:
            del self._requests[key]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware.

    Applies rate limits based on client IP or authenticated user.
    """

    def __init__(
        self,
        app,
        config: RateLimitConfig | None = None,
        get_key: Callable[[Request], str] | None = None,
    ):
        super().__init__(app)
        self.config = config or RateLimitConfig()
        self.limiter = InMemoryRateLimiter(self.config)
        self.get_key = get_key or self._default_get_key

    def _default_get_key(self, request: Request) -> str:
        """Get rate limit key from request.

        Uses X-Forwarded-For if available, otherwise client IP.
        """
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take first IP in chain
            return forwarded.split(",")[0].strip()

        # Fall back to client host
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for exempt paths
        path = request.url.path
        if any(path.startswith(exempt) for exempt in self.config.exempt_paths):
            return await call_next(request)

        # Get rate limit key
        key = self.get_key(request)

        # Check rate limit
        allowed, info = self.limiter.is_allowed(key)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": info["retry_after"],
                },
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": str(info["remaining"]),
                    "X-RateLimit-Reset": str(info["reset"]),
                    "Retry-After": str(info["retry_after"]),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])

        return response
