from app.domain.entities.role import Role
from app.domain.interfaces.role_repository import RoleRepository


class ListRolesUseCase:
    def __init__(self, roles: RoleRepository) -> None: self._roles = roles
    def execute(self, tenant_id: int, division_id: int | None) -> list[Role]:
        return self._roles.list_scoped(tenant_id, division_id)
