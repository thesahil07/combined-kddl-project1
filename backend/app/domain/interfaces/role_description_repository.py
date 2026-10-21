from abc import ABC, abstractmethod

from app.domain.entities.role_description import RoleDescription


class RoleDescriptionRepository(ABC):
    @abstractmethod
    def current_scoped(self, role_id: int, tenant_id: int) -> RoleDescription | None: ...
    @abstractmethod
    def save(self, description: RoleDescription) -> RoleDescription: ...
