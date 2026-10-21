from abc import ABC, abstractmethod

from app.domain.entities.role import Role


class RoleRepository(ABC):
    @abstractmethod
    def create(self, role: Role) -> Role: ...
    @abstractmethod
    def get_scoped(self, role_id: int, tenant_id: int) -> Role | None: ...
    @abstractmethod
    def list_scoped(self, tenant_id: int, division_id: int | None) -> list[Role]: ...
    @abstractmethod
    def set_description_status(self, role_id: int, tenant_id: int, status: str) -> None: ...
