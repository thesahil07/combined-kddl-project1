"""Save or submit a direct report's manager assessment."""

from app.domain.interfaces.skip_manager_dashboard_repository import SkipManagerDashboardRepository
from app.application.services.assessment_submission_notifier import AssessmentSubmissionNotifier


class SaveManagerAssessmentUseCase:
    def __init__(
        self, repository: SkipManagerDashboardRepository,
        notifier: AssessmentSubmissionNotifier | None = None,
    ) -> None:
        self._repository = repository
        self._notifier = notifier

    def execute(
        self, tenant_id: int, employee_id: int, actor_user_id: int, item_type: str,
        items: list[dict[str, int]], submit: bool,
    ) -> dict[str, object]:
        assessment = self._repository.save_manager_assessment(
            tenant_id, employee_id, actor_user_id, item_type, items, submit
        )
        if submit and self._notifier is not None:
            self._notifier.notify(
                tenant_id, employee_id, actor_user_id, item_type, "Manager",
            )
        return assessment
