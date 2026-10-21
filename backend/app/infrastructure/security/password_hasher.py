"""Argon2id password hashing adapter."""

from passlib.context import CryptContext


class PasswordHasher:
    _context = CryptContext(schemes=["argon2"], deprecated="auto", argon2__type="ID")

    def hash(self, password: str) -> str:
        return self._context.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return self._context.verify(password, password_hash)
