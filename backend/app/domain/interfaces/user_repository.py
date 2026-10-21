"""User persistence boundary."""

from abc import ABC, abstractmethod

from app.domain.entities.user import User


class UserRepository(ABC):
    @abstractmethod
    def get_by_email(self, email: str) -> tuple[User, str] | None: ...

    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None: ...

    def get_password_hash(self, user_id: int) -> str | None: ...

    @abstractmethod
    def create(self, user: User, password_hash: str) -> User: ...

    @abstractmethod
    def update_last_login(self, user_id: int) -> None: ...

    def update_password_hash(self, user_id: int, password_hash: str) -> None: ...
