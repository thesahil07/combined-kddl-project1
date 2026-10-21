"""Framework-independent login workflow."""

from dataclasses import dataclass

from app.domain.entities.user import User, UserStatus
from app.domain.interfaces.auth_services import PasswordVerifier, TokenIssuer
from app.domain.interfaces.user_repository import UserRepository


@dataclass(frozen=True, slots=True)
class LoginResult:
    user: User | None = None
    access_token: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.user is not None and self.access_token is not None


class LoginUseCase:
    def __init__(self, users: UserRepository, hasher: PasswordVerifier, tokens: TokenIssuer) -> None:
        self._users, self._hasher, self._tokens = users, hasher, tokens

    def execute(self, email: str, password: str) -> LoginResult:
        record = self._users.get_by_email(email)
        if record is None:
            return LoginResult()
        user, password_hash = record
        if user.status is not UserStatus.ACTIVE or not self._hasher.verify(password, password_hash):
            return LoginResult()
        token = self._tokens.issue(user)
        self._users.update_last_login(user.user_id)
        return LoginResult(user=user, access_token=token)
