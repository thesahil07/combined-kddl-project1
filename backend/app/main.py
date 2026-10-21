"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.presentation.api.v1.router import router as v1_router
from app.presentation.middlewares.rate_limit import LoginRateLimitMiddleware
from app.presentation.middlewares.security_headers import SecurityHeadersMiddleware
from app.presentation.api.dependencies import dispose_database_engine, initialize_database_engine
from app.infrastructure.security.rate_limiter import InMemoryRateLimiter, RedisRateLimiter
from app.domain.exceptions.application_errors import (
    ApplicationError, AuthorizationError, ExternalServiceUnavailableError,
    InvalidStateError, ResourceNotFoundError, ValidationError,
)
from redis import Redis

@asynccontextmanager
async def lifespan(application: FastAPI):
    initialize_database_engine()
    if settings.env == "local":
        application.state.rate_limiter = InMemoryRateLimiter()
    elif settings.redis_url:
        application.state.rate_limiter = RedisRateLimiter(Redis.from_url(settings.redis_url))
    yield
    dispose_database_engine()


app = FastAPI(title="KDDL Dials Talent Transformation Platform", lifespan=lifespan)
app.add_middleware(LoginRateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.env == "local" else list(settings.frontend_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(v1_router, prefix="/api/v1")


@app.exception_handler(ApplicationError)
async def application_error_handler(_: Request, error: ApplicationError) -> JSONResponse:
    status_code = 400
    for error_type, code in (
        (ResourceNotFoundError, 404),
        (ValidationError, 422),
        (InvalidStateError, 409),
        (AuthorizationError, 403),
        (ExternalServiceUnavailableError, 503),
    ):
        if isinstance(error, error_type):
            status_code = code
            break
    return JSONResponse(status_code=status_code, content={"detail": str(error)})


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(_: Request, __: SQLAlchemyError) -> JSONResponse:
    """Do not leak database implementation details to API callers."""
    return JSONResponse(status_code=500, content={"detail": "database operation failed"})


@app.get("/api/v1/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
