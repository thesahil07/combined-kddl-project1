"""Short-lived JWT access-token adapter."""

from datetime import datetime, timedelta, timezone

import jwt

from app.domain.entities.user import User


class InvalidTokenError(ValueError):
    pass


class TokenService:
    def __init__(self, secret: str, expiry_minutes: int) -> None:
        self._secret = secret
        self._expiry_minutes = expiry_minutes

    def issue(self, user: User) -> str:
        now = datetime.now(timezone.utc)
        claims = {"sub": str(user.user_id), "tenant_id": user.tenant_id, "role": user.role.value,
                  "division_scope_id": user.division_scope_id, "iat": now,
                  "exp": now + timedelta(minutes=self._expiry_minutes)}
        return jwt.encode(claims, self._secret, algorithm="HS256")

    def verify(self, token: str) -> dict[str, object]:
        try:
            return jwt.decode(token, self._secret, algorithms=["HS256"], options={"require": ["exp", "sub"]})
        except jwt.PyJWTError as error:
            raise InvalidTokenError("invalid token") from error
