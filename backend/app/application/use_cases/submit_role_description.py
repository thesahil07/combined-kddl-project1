"""Submit a complete role-description draft for review."""

from app.application.use_cases.save_role_description import SaveRoleDescriptionUseCase
from app.domain.entities.role import DescriptionStatus
from app.domain.entities.role_description import RoleDescription
from app.domain.interfaces.role_repository import RoleRepository
from app.domain.rules.role_description_validation import can_validate
from app.domain.exceptions.application_errors import ValidationError


class SubmitRoleDescriptionUseCase:
    def __init__(self, save_draft: SaveRoleDescriptionUseCase, roles: RoleRepository) -> None:
        self._save_draft = save_draft
        self._roles = roles

    def execute(self, role_id: int, tenant_id: int, data: dict[str, object]) -> RoleDescription:
        required_fields = {
            "people_count": "No. of people in this role",
            "role_definition": "Role definition",
            "key_responsibilities": "Key responsibilities in the role",
            "kpis": "Key performance indicators (KPI) for the role",
            "education_certifications": "Education / degree / diploma or certifications required",
            "minimum_relevant_experience": "Minimum relevant experience required",
            "knowledge_required": "Knowledge required to perform the role",
            "skills_required": "Skills required to perform the role",
            "attitudes_behaviours": "Attitude / behaviours required to perform the role",
        }
        missing = [label for field, label in required_fields.items() if data.get(field) is None or not str(data.get(field)).strip()]
        if missing:
            raise ValidationError("Missing mandatory fields: " + "; ".join(missing))
        saved = self._save_draft.execute(role_id, tenant_id, data)
        if not can_validate(saved):
            raise ValidationError("all role-definition template fields are required before submission")
        self._roles.set_description_status(role_id, tenant_id, DescriptionStatus.SUBMITTED.value)
        return saved
