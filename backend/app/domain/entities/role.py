"""Minimal role entity used by Module D only."""

from dataclasses import dataclass
from enum import StrEnum


class DescriptionStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    VALIDATED = "VALIDATED"


@dataclass(frozen=True, slots=True)
class Role:
    role_id: int | None
    tenant_id: int
    division_id: int
    function_id: int
    title: str
    description_status: DescriptionStatus = DescriptionStatus.NOT_STARTED
    ask_status: str = "NOT_MAPPED"
    tier: str = "NONE"
    merged_into_role_id: int | None = None

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("role title is required")
