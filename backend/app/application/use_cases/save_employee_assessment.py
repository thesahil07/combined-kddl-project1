"""Save or submit an employee's self-assessment ratings."""

from app.domain.interfaces.employee_workspace_repository import EmployeeWorkspaceRepository
from app.application.services.assessment_submission_notifier import AssessmentSubmissionNotifier


class SaveEmployeeAssessmentUseCase:
    def __init__(
        self, repository: EmployeeWorkspaceRepository,
        notifier: AssessmentSubmissionNotifier | None = None,
    ) -> None:
        self._repository = repository
        self._notifier = notifier

    def execute(
        self,
        tenant_id: int,
        employee_id: int,
        actor_user_id: int,
        item_type: str,
        items: list[dict[str, int]],
        submit: bool,
    ) -> dict[str, object]:
        assessment = self._repository.save_assessment(
            tenant_id, employee_id, actor_user_id, item_type, items, submit
        )
        if submit and self._notifier is not None:
            self._notifier.notify(
                tenant_id, employee_id, actor_user_id, item_type, "Employee",
            )
        return assessment
