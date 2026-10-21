"""Environment-backed application configuration."""

from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str | None
    jwt_secret: str | None
    jwt_expiry_minutes: int | None
    env: str | None
    redis_url: str | None
    frontend_origins: tuple[str, ...]
    email_config_encryption_key: str | None

    def require_jwt_settings(self) -> tuple[str, int]:
        if not self.jwt_secret or not self.jwt_expiry_minutes:
            raise RuntimeError("JWT_SECRET and JWT_EXPIRY_MINUTES must be configured.")
        return self.jwt_secret, self.jwt_expiry_minutes


def _optional_int(name: str) -> int | None:
    value = getenv(name)
    return int(value) if value else None


settings = Settings(
    database_url=getenv("DATABASE_URL"),
    jwt_secret=getenv("JWT_SECRET"),
    jwt_expiry_minutes=_optional_int("JWT_EXPIRY_MINUTES"),
    env=getenv("ENV"),
    redis_url=getenv("REDIS_URL"),
    frontend_origins=tuple(
        origin.strip()
        for origin in getenv(
            "FRONTEND_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ),
    email_config_encryption_key=getenv("EMAIL_CONFIG_ENCRYPTION_KEY"),
)
