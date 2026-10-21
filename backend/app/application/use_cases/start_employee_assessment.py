"""Create the signed-in employee's assessment form and line items."""

from app.domain.interfaces.employee_workspace_repository import EmployeeWorkspaceRepository


class StartEmployeeAssessmentUseCase:
    def __init__(self, repository: EmployeeWorkspaceRepository) -> None:
        self._repository = repository

    def execute(
        self, tenant_id: int, employee_id: int, actor_user_id: int, item_type: str
    ) -> dict[str, object]:
        return self._repository.start_assessment(tenant_id, employee_id, actor_user_id, item_type)
