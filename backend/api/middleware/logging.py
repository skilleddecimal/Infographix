"""Request logging middleware."""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logger
logger = logging.getLogger("infographix.api")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses.

    Logs request details, response status, and timing information.
    """

    def __init__(
        self,
        app,
        log_request_body: bool = False,
        log_response_body: bool = False,
        exclude_paths: list[str] | None = None,
    ):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.exclude_paths = exclude_paths or ["/health", "/ready"]

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with logging."""
        # Skip logging for excluded paths
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        # Generate request ID
        request_id = str(uuid.uuid4())[:8]

        # Store start time
        start_time = time.time()

        # Extract request info
        client_ip = self._get_client_ip(request)
        method = request.method
        path = request.url.path
        query = str(request.query_params) if request.query_params else ""

        # Log request
        logger.info(
            f"[{request_id}] {method} {path}"
            + (f"?{query}" if query else "")
            + f" - Client: {client_ip}"
        )

        # Add request ID to state
        request.state.request_id = request_id

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error
            duration = (time.time() - start_time) * 1000
            logger.error(
                f"[{request_id}] {method} {path} - ERROR - {duration:.2f}ms - {str(e)}"
            )
            raise

        # Calculate duration
        duration = (time.time() - start_time) * 1000

        # Log response
        status = response.status_code
        log_level = logging.INFO if status < 400 else logging.WARNING if status < 500 else logging.ERROR

        logger.log(
            log_level,
            f"[{request_id}] {method} {path} - {status} - {duration:.2f}ms"
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check X-Forwarded-For header
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to client host
        return request.client.host if request.client else "unknown"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that ensures every request has a unique ID."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Check for existing request ID in headers
        request_id = request.headers.get("X-Request-ID")

        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in request state
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers["X-Request-ID"] = request_id

        return response
