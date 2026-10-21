"""Role-description validation stays outside HTTP and persistence layers."""

from app.domain.entities.role_description import RoleDescription


def can_validate(description: RoleDescription) -> bool:
    return description.people_count is not None and all(
        field.strip()
        for field in (
            description.role_definition,
            description.key_responsibilities,
            description.kpis,
            description.education_certifications,
            description.minimum_relevant_experience,
            description.knowledge_required,
            description.skills_required,
            description.attitudes_behaviours,
        )
    )
