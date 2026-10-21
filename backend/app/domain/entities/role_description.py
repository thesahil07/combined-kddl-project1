"""Immutable representation of one role-description version."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RoleDescription:
    role_description_id: int | None
    role_id: int
    version: int
    people_count: int | None
    role_definition: str
    key_responsibilities: str
    kpis: str
    education_certifications: str
    minimum_relevant_experience: str
    knowledge_required: str
    skills_required: str
    attitudes_behaviours: str
    equipment_process_refs: str | None
    ai_refined: bool
    validated_by_employee_id: int | None
    validated_at: datetime | None

    @property
    def is_validated(self) -> bool:
        return self.validated_at is not None
