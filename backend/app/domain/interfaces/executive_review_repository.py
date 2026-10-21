"""Read model contract for the Executive Review dashboard."""

from abc import ABC, abstractmethod


class ExecutiveReviewRepository(ABC):
    @abstractmethod
    def get_dashboard(self, tenant_id: int, division_id: int | None) -> dict[str, object]: ...
