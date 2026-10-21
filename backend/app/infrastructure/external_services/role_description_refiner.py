from app.infrastructure.external_services.ai_gateway import RoleDescriptionAIGateway


class RoleDescriptionRefiner:
    """Grammar/structure-only advisory adapter; it never saves suggestions."""
    def __init__(self, gateway: RoleDescriptionAIGateway) -> None: self._gateway = gateway
    def refine(self, text: str) -> str: return self._gateway.refine_role_description(text)
