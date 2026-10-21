"""Read model for authorised tenant-wide assessment reporting."""

from abc import ABC, abstractmethod


class AdminConsoleRepository(ABC):
    @abstractmethod
    def get_assessment_report(
        self, tenant_id: int, division_id: int | None, cycle_id: int | None,
        employee_name: str | None, page: int, page_size: int,
    ) -> dict[str, object]: ...

    @abstractmethod
    def get_submitted_assessment(self, tenant_id: int, employee_id: int, cycle_id: int) -> dict[str, object] | None: ...
