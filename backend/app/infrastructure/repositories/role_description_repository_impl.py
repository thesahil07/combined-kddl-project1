from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.domain.entities.role_description import RoleDescription
from app.domain.interfaces.role_description_repository import RoleDescriptionRepository
from app.infrastructure.database.models.module_b import RoleDescriptionModel, RoleModel


def _description(model: RoleDescriptionModel) -> RoleDescription:
    return RoleDescription(model.role_description_id, model.role_id, model.version, model.people_count, model.role_definition, model.key_responsibilities, model.kpis, model.education_certifications, model.minimum_relevant_experience, model.knowledge_required, model.skills_required, model.attitudes_behaviours, model.equipment_process_refs, model.ai_refined, model.validated_by_employee_id, model.validated_at)


class SqlAlchemyRoleDescriptionRepository(RoleDescriptionRepository):
    def __init__(self, session: Session) -> None:
        self._session = session
    def current_scoped(self, role_id: int, tenant_id: int) -> RoleDescription | None:
        query = select(RoleDescriptionModel).join(RoleModel, RoleModel.role_id == RoleDescriptionModel.role_id).where(RoleDescriptionModel.role_id == role_id, RoleModel.tenant_id == tenant_id).order_by(desc(RoleDescriptionModel.version))
        model = self._session.scalar(query)
        return _description(model) if model else None
    def save(self, description: RoleDescription) -> RoleDescription:
        if description.role_description_id is None:
            model = RoleDescriptionModel(role_id=description.role_id, version=description.version, people_count=description.people_count, role_definition=description.role_definition, key_responsibilities=description.key_responsibilities, kpis=description.kpis, education_certifications=description.education_certifications, minimum_relevant_experience=description.minimum_relevant_experience, knowledge_required=description.knowledge_required, skills_required=description.skills_required, attitudes_behaviours=description.attitudes_behaviours, specifications_experience=_legacy_specifications_experience(description), equipment_process_refs=description.equipment_process_refs, ai_refined=description.ai_refined, validated_by_employee_id=description.validated_by_employee_id, validated_at=description.validated_at)
            self._session.add(model)
        else:
            model = self._session.get(RoleDescriptionModel, description.role_description_id)
            if model is None:
                raise ValueError("description not found")
            model.people_count, model.role_definition, model.key_responsibilities, model.kpis = description.people_count, description.role_definition, description.key_responsibilities, description.kpis
            model.education_certifications, model.minimum_relevant_experience = description.education_certifications, description.minimum_relevant_experience
            model.knowledge_required, model.skills_required, model.attitudes_behaviours = description.knowledge_required, description.skills_required, description.attitudes_behaviours
            model.specifications_experience, model.equipment_process_refs, model.ai_refined = _legacy_specifications_experience(description), description.equipment_process_refs, description.ai_refined
            model.validated_by_employee_id, model.validated_at = description.validated_by_employee_id, description.validated_at
        self._session.flush()
        self._session.refresh(model)
        return _description(model)


def _legacy_specifications_experience(description: RoleDescription) -> str:
    """Retain the previous combined field for backwards-compatible reporting."""
    return f"Education / certifications:\n{description.education_certifications}\n\nMinimum relevant experience:\n{description.minimum_relevant_experience}"
