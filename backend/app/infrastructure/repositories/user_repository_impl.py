"""SQLAlchemy user repository."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.user import User
from app.domain.interfaces.user_repository import UserRepository
from app.infrastructure.database.models.tenancy_identity import UserModel


def _to_entity(model: UserModel) -> User:
    return User(model.user_id, model.tenant_id, model.email, model.role, model.employee_id,
                model.division_scope_id, model.status)


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_email(self, email: str) -> tuple[User, str] | None:
        model = self._session.scalar(select(UserModel).where(UserModel.email == email))
        return (_to_entity(model), model.password_hash) if model else None

    def get_by_id(self, user_id: int) -> User | None:
        model = self._session.get(UserModel, user_id)
        return _to_entity(model) if model else None

    def get_password_hash(self, user_id: int) -> str | None:
        model = self._session.get(UserModel, user_id)
        return model.password_hash if model else None

    def create(self, user: User, password_hash: str) -> User:
        model = UserModel(user_id=user.user_id, tenant_id=user.tenant_id, email=user.email,
                          password_hash=password_hash, role=user.role, employee_id=user.employee_id,
                          division_scope_id=user.division_scope_id, status=user.status)
        self._session.add(model)
        self._session.flush()
        return _to_entity(model)

    def update_last_login(self, user_id: int) -> None:
        model = self._session.get(UserModel, user_id)
        if model:
            model.last_login_at = datetime.now(timezone.utc)

    def update_password_hash(self, user_id: int, password_hash: str) -> None:
        model = self._session.get(UserModel, user_id)
        if model is None:
            raise ValueError("user does not exist")
        model.password_hash = password_hash
