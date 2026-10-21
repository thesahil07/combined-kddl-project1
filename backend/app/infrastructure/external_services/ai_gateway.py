from typing import Protocol

from app.domain.exceptions.application_errors import ExternalServiceUnavailableError


class AIGatewayUnavailableError(ExternalServiceUnavailableError):
    pass


class RoleDescriptionAIGateway(Protocol):
    def refine_role_description(self, draft: str) -> str: ...


class UnavailableRoleDescriptionAIGateway:
    def refine_role_description(self, draft: str) -> str:
        raise AIGatewayUnavailableError("role-description AI gateway is unavailable")
