"""Retrieve tenant-scoped executive workforce intelligence."""

from app.domain.interfaces.executive_review_repository import ExecutiveReviewRepository


class GetExecutiveReviewUseCase:
    def __init__(self, repository: ExecutiveReviewRepository) -> None:
        self._repository = repository

    def execute(self, tenant_id: int, division_id: int | None) -> dict[str, object]:
        return self._repository.get_dashboard(tenant_id, division_id)
