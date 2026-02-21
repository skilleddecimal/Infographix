"""Security headers middleware."""

from dataclasses import dataclass, field
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class SecurityConfig:
    """Security headers configuration."""

    # Content Security Policy
    csp_default_src: str = "'self'"
    csp_script_src: str = "'self'"
    csp_style_src: str = "'self' 'unsafe-inline'"
    csp_img_src: str = "'self' data: https:"
    csp_font_src: str = "'self'"
    csp_connect_src: str = "'self'"
    csp_frame_ancestors: str = "'none'"

    # Other security headers
    enable_hsts: bool = True
    hsts_max_age: int = 31536000  # 1 year
    hsts_include_subdomains: bool = True
    hsts_preload: bool = False

    x_content_type_options: bool = True
    x_frame_options: str = "DENY"
    x_xss_protection: bool = True
    referrer_policy: str = "strict-origin-when-cross-origin"
    permissions_policy: str = "geolocation=(), microphone=(), camera=()"

    # CORS (handled separately but referenced here)
    enable_cors: bool = True


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security headers to responses.

    Implements security best practices including:
    - Content Security Policy (CSP)
    - HTTP Strict Transport Security (HSTS)
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    """

    def __init__(
        self,
        app,
        config: SecurityConfig | None = None,
    ):
        super().__init__(app)
        self.config = config or SecurityConfig()

    def _build_csp(self) -> str:
        """Build Content Security Policy header value."""
        config = self.config
        directives = [
            f"default-src {config.csp_default_src}",
            f"script-src {config.csp_script_src}",
            f"style-src {config.csp_style_src}",
            f"img-src {config.csp_img_src}",
            f"font-src {config.csp_font_src}",
            f"connect-src {config.csp_connect_src}",
            f"frame-ancestors {config.csp_frame_ancestors}",
        ]
        return "; ".join(directives)

    def _build_hsts(self) -> str:
        """Build HSTS header value."""
        config = self.config
        value = f"max-age={config.hsts_max_age}"
        if config.hsts_include_subdomains:
            value += "; includeSubDomains"
        if config.hsts_preload:
            value += "; preload"
        return value

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add security headers."""
        response = await call_next(request)

        config = self.config

        # Content Security Policy
        response.headers["Content-Security-Policy"] = self._build_csp()

        # HSTS (only for HTTPS)
        if config.enable_hsts:
            response.headers["Strict-Transport-Security"] = self._build_hsts()

        # X-Content-Type-Options
        if config.x_content_type_options:
            response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        if config.x_frame_options:
            response.headers["X-Frame-Options"] = config.x_frame_options

        # X-XSS-Protection (legacy but still useful)
        if config.x_xss_protection:
            response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy
        if config.referrer_policy:
            response.headers["Referrer-Policy"] = config.referrer_policy

        # Permissions-Policy (Feature-Policy successor)
        if config.permissions_policy:
            response.headers["Permissions-Policy"] = config.permissions_policy

        return response


class CORSConfig:
    """CORS configuration."""

    def __init__(
        self,
        allow_origins: list[str] | None = None,
        allow_methods: list[str] | None = None,
        allow_headers: list[str] | None = None,
        allow_credentials: bool = False,
        expose_headers: list[str] | None = None,
        max_age: int = 600,
    ):
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials
        self.expose_headers = expose_headers or []
        self.max_age = max_age


def add_security_headers(
    response: Response,
    config: SecurityConfig | None = None,
) -> Response:
    """Add security headers to a response.

    Utility function for adding headers outside of middleware.
    """
    config = config or SecurityConfig()

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = config.x_frame_options
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = config.referrer_policy

    return response
