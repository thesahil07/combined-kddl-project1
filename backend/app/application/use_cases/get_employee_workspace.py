"""Read an employee's tenant-scoped workspace."""

from app.domain.interfaces.employee_workspace_repository import EmployeeWorkspaceRepository


class GetEmployeeWorkspaceUseCase:
    def __init__(self, repository: EmployeeWorkspaceRepository) -> None:
        self._repository = repository

    def dashboard(self, tenant_id: int, employee_id: int) -> dict[str, object]:
        return self._repository.get_dashboard(tenant_id, employee_id)

    def role(self, tenant_id: int, employee_id: int) -> dict[str, object] | None:
        return self._repository.get_role(tenant_id, employee_id)

    def current_assessment(
        self, tenant_id: int, employee_id: int, item_type: str
    ) -> dict[str, object] | None:
        return self._repository.get_current_assessment(tenant_id, employee_id, item_type)

    def previous_assessments(self, tenant_id: int, employee_id: int) -> list[dict[str, object]]:
        return self._repository.get_previous_assessments(tenant_id, employee_id)
