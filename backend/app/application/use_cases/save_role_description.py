from app.domain.entities.role import DescriptionStatus
from app.domain.entities.role_description import RoleDescription
from app.domain.interfaces.role_description_repository import RoleDescriptionRepository
from app.domain.interfaces.role_repository import RoleRepository
from app.domain.exceptions.application_errors import InvalidStateError, ResourceNotFoundError


class SaveRoleDescriptionUseCase:
    def __init__(self, descriptions: RoleDescriptionRepository, roles: RoleRepository) -> None:
        self._descriptions = descriptions
        self._roles = roles

    def execute(self, role_id: int, tenant_id: int, data: dict[str, object]) -> RoleDescription:
        role = self._roles.get_scoped(role_id, tenant_id)
        if role is None:
            raise ResourceNotFoundError("role not found")
        if role.description_status in (DescriptionStatus.SUBMITTED, DescriptionStatus.VALIDATED):
            raise InvalidStateError("submitted role definitions cannot be changed")
        current = self._descriptions.current_scoped(role_id, tenant_id)
        version = 1 if current is None else current.version + 1 if current.is_validated else current.version
        identifier = None if current is None or current.is_validated else current.role_description_id
        accepted_ai_suggestion = bool(data.pop("accepted_ai_suggestion", False))
        description = RoleDescription(
            identifier,
            role_id,
            version,
            data.pop("people_count", None),
            ai_refined=accepted_ai_suggestion,
            validated_by_employee_id=None,
            validated_at=None,
            **data,
        )
        saved = self._descriptions.save(description)
        self._roles.set_description_status(role_id, tenant_id, DescriptionStatus.DRAFT.value)
        return saved
