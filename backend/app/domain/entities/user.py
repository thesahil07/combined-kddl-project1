"""Framework-independent authenticated-user entity."""

from dataclasses import dataclass
from enum import StrEnum

from app.domain.value_objects.role import Role


UserRole = Role


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


@dataclass(frozen=True, slots=True)
class User:
    user_id: int
    tenant_id: int | None
    email: str
    role: UserRole
    employee_id: int | None
    division_scope_id: int | None
    status: UserStatus

    def __post_init__(self) -> None:
        if self.role is UserRole.PGC_ADMIN and self.tenant_id is not None:
            raise ValueError("PGC_ADMIN must not be assigned to a tenant.")
        if self.role is not UserRole.PGC_ADMIN and self.tenant_id is None:
            raise ValueError("Tenant users must be assigned to a tenant.")
