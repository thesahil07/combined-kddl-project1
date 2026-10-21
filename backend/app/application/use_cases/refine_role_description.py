from typing import Protocol

from app.domain.interfaces.role_description_repository import RoleDescriptionRepository
from app.domain.exceptions.application_errors import ResourceNotFoundError


class DescriptionRefiner(Protocol):
    def refine(self, text: str) -> str: ...


class RefineRoleDescriptionUseCase:
    def __init__(self, descriptions: RoleDescriptionRepository, refiner: DescriptionRefiner) -> None:
        self._descriptions = descriptions
        self._refiner = refiner

    def execute(self, role_id: int, tenant_id: int) -> str:
        description = self._descriptions.current_scoped(role_id, tenant_id)
        if description is None:
            raise ResourceNotFoundError("draft role description not found")
        source = "\n\n".join((description.role_definition, description.key_responsibilities, description.kpis, description.specifications_experience))
        return self._refiner.refine(source)
