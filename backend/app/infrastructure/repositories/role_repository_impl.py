from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.role import DescriptionStatus, Role
from app.domain.interfaces.role_repository import RoleRepository
from app.infrastructure.database.models.module_b import FunctionModel, RoleModel


def _role(model: RoleModel) -> Role:
    return Role(model.role_id, model.tenant_id, model.division_id, model.function_id, model.title,
                DescriptionStatus(model.description_status))


class SqlAlchemyRoleRepository(RoleRepository):
    def __init__(self, session: Session) -> None:
        self._session = session
    def create(self, role: Role) -> Role:
        function = self._session.scalar(select(FunctionModel).where(
            FunctionModel.function_id == role.function_id,
            FunctionModel.tenant_id == role.tenant_id,
            FunctionModel.division_id == role.division_id,
        ))
        if function is None:
            raise ValueError("function does not belong to the selected tenant division")
        model = RoleModel(tenant_id=role.tenant_id, division_id=role.division_id, function_id=role.function_id, title=role.title, description_status=role.description_status.value)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _role(model)
    def get_scoped(self, role_id: int, tenant_id: int) -> Role | None:
        model = self._session.scalar(select(RoleModel).where(RoleModel.role_id == role_id, RoleModel.tenant_id == tenant_id))
        return _role(model) if model else None
    def list_scoped(self, tenant_id: int, division_id: int | None) -> list[Role]:
        query = select(RoleModel).where(RoleModel.tenant_id == tenant_id)
        if division_id is not None:
            query = query.where(RoleModel.division_id == division_id)
        return [_role(row) for row in self._session.scalars(query).all()]
    def set_description_status(self, role_id: int, tenant_id: int, status: str) -> None:
        model = self._session.scalar(select(RoleModel).where(RoleModel.role_id == role_id, RoleModel.tenant_id == tenant_id))
        if model is None:
            raise ValueError("role not found")
        model.description_status = status
