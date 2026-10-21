"""Redis-backed login rate limiter; failures deny login rather than bypass it."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Protocol


class RateLimiter(Protocol):
    def allow(self, key: str) -> bool: ...


class LoginRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: object) -> object:
        if request.url.path != "/api/v1/auth/login" or request.method != "POST":
            return await call_next(request)  # type: ignore[operator]
        limiter: RateLimiter | None = getattr(request.app.state, "rate_limiter", None)
        if limiter is None:
            return JSONResponse({"detail": "rate limiter unavailable"}, status_code=503)
        client_ip = request.client.host if request.client else "unknown"
        try:
            allowed = limiter.allow(f"login:{client_ip}")
        except Exception:
            return JSONResponse({"detail": "rate limiter unavailable"}, status_code=503)
        if not allowed:
            return JSONResponse({"detail": "too many login attempts"}, status_code=429)
        return await call_next(request)  # type: ignore[operator]
