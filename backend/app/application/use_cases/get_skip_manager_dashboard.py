"""Build the read-only Skip Manager dashboard."""

from app.domain.interfaces.skip_manager_dashboard_repository import SkipManagerDashboardRepository
from app.domain.exceptions.application_errors import AuthorizationError


class GetSkipManagerDashboardUseCase:
    def __init__(self, repository: SkipManagerDashboardRepository) -> None:
        self._repository = repository

    def execute(self, tenant_id: int, manager_employee_id: int) -> dict[str, object]:
        return self._repository.get_dashboard(tenant_id, manager_employee_id)

    def can_author_role(self, tenant_id: int, manager_employee_id: int, role_id: int) -> bool:
        return self._repository.is_team_role(tenant_id, manager_employee_id, role_id)

    def ensure_can_author_role(self, tenant_id: int, manager_employee_id: int, role_id: int) -> None:
        if not self.can_author_role(tenant_id, manager_employee_id, role_id):
            raise AuthorizationError("role is outside the manager's assigned scope")

    def get_gap_matrices(self, tenant_id: int, manager_employee_id: int) -> dict[str, object]:
        return self._repository.get_gap_matrices(tenant_id, manager_employee_id)

    def ensure_can_assess_employee(self, tenant_id: int, manager_employee_id: int, employee_id: int) -> None:
        if not self._repository.is_team_member(tenant_id, manager_employee_id, employee_id):
            raise AuthorizationError("employee is outside the manager's direct-team scope")

    def get_employee_assessment(self, tenant_id: int, employee_id: int) -> dict[str, object] | None:
        return self._repository.get_employee_assessment(tenant_id, employee_id)

    def get_employee_previous_assessments(self, tenant_id: int, employee_id: int) -> list[dict[str, object]]:
        return self._repository.get_employee_previous_assessments(tenant_id, employee_id)

    def get_submitted_assessment(
        self, tenant_id: int, manager_employee_id: int, employee_id: int
    ) -> dict[str, object] | None:
        return self._repository.get_submitted_assessment(
            tenant_id, manager_employee_id, employee_id
        )
