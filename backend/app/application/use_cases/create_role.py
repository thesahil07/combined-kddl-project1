from app.domain.entities.role import Role
from app.domain.interfaces.role_repository import RoleRepository


class CreateRoleUseCase:
    def __init__(self, roles: RoleRepository) -> None:
        self._roles = roles

    def execute(self, tenant_id: int, division_id: int, function_id: int, title: str) -> Role:
        return self._roles.create(Role(None, tenant_id, division_id, function_id, title))
