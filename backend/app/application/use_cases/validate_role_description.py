from datetime import datetime, timezone

from app.domain.entities.role import DescriptionStatus
from app.domain.entities.role_description import RoleDescription
from app.domain.interfaces.role_description_repository import RoleDescriptionRepository
from app.domain.interfaces.role_repository import RoleRepository
from app.domain.rules.role_description_validation import can_validate
from app.domain.exceptions.application_errors import ValidationError


class ValidateRoleDescriptionUseCase:
    def __init__(self, descriptions: RoleDescriptionRepository, roles: RoleRepository) -> None:
        self._descriptions = descriptions
        self._roles = roles

    def execute(self, role_id: int, tenant_id: int, employee_id: int | None) -> RoleDescription:
        current = self._descriptions.current_scoped(role_id, tenant_id)
        if current is None or not can_validate(current):
            raise ValidationError("description is incomplete")
        validated = RoleDescription(
            current.role_description_id, current.role_id, current.version, current.people_count,
            current.role_definition, current.key_responsibilities, current.kpis,
            current.education_certifications, current.minimum_relevant_experience,
            current.knowledge_required, current.skills_required, current.attitudes_behaviours,
            current.equipment_process_refs,
            current.ai_refined, employee_id, datetime.now(timezone.utc),
        )
        saved = self._descriptions.save(validated)
        self._roles.set_description_status(role_id, tenant_id, DescriptionStatus.VALIDATED.value)
        return saved
