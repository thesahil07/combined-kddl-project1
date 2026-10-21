"""Authentication service contracts."""

from typing import Protocol

from app.domain.entities.user import User


class PasswordVerifier(Protocol):
    def verify(self, password: str, password_hash: str) -> bool: ...


class PasswordManager(PasswordVerifier, Protocol):
    def hash(self, password: str) -> str: ...


class TokenIssuer(Protocol):
    def issue(self, user: User) -> str: ...
