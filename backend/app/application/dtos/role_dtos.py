from pydantic import BaseModel, ConfigDict, Field


class CreateRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    division_id: int
    function_id: int
    title: str = Field(min_length=1, max_length=150)


class RoleDescriptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    people_count: int | None = Field(default=None, ge=0)
    role_definition: str = ""
    key_responsibilities: str = ""
    kpis: str = ""
    education_certifications: str = ""
    minimum_relevant_experience: str = ""
    knowledge_required: str = ""
    skills_required: str = ""
    attitudes_behaviours: str = ""
    equipment_process_refs: str | None = None
    accepted_ai_suggestion: bool = False
