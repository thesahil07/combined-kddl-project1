"""Validated input contracts for employee self-assessments."""

from pydantic import BaseModel, Field


class EmployeeAssessmentItemRequest(BaseModel):
    item_id: int = Field(gt=0)
    self_assessment_level: int = Field(ge=1, le=4)


class EmployeeAssessmentRequest(BaseModel):
    items: list[EmployeeAssessmentItemRequest] = Field(min_length=1)
