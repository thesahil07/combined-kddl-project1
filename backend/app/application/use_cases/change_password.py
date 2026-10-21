"""Authenticated self-service password change workflow."""

from app.domain.entities.user import User, UserStatus
from app.domain.interfaces.auth_services import PasswordManager
from app.domain.interfaces.user_repository import UserRepository


class ChangePasswordUseCase:
    def __init__(self, users: UserRepository, passwords: PasswordManager) -> None:
        self._users = users
        self._passwords = passwords

    def execute(self, user: User, current_password: str, new_password: str) -> bool:
        if user.status is not UserStatus.ACTIVE or current_password == new_password:
            return False
        password_hash = self._users.get_password_hash(user.user_id)
        if password_hash is None or not self._passwords.verify(current_password, password_hash):
            return False
        self._users.update_password_hash(user.user_id, self._passwords.hash(new_password))
        return True
