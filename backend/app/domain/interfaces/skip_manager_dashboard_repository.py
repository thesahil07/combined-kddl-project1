"""Read-model contract for the Skip Manager workspace."""

from abc import ABC, abstractmethod


class SkipManagerDashboardRepository(ABC):
    @abstractmethod
    def get_dashboard(self, tenant_id: int, manager_employee_id: int) -> dict[str, object]: ...

    @abstractmethod
    def is_team_role(self, tenant_id: int, manager_employee_id: int, role_id: int) -> bool: ...

    @abstractmethod
    def get_gap_matrices(self, tenant_id: int, manager_employee_id: int) -> dict[str, object]: ...

    @abstractmethod
    def is_team_member(self, tenant_id: int, manager_employee_id: int, employee_id: int) -> bool: ...

    @abstractmethod
    def get_employee_assessment(self, tenant_id: int, employee_id: int) -> dict[str, object] | None: ...

    @abstractmethod
    def save_manager_assessment(
        self, tenant_id: int, employee_id: int, actor_user_id: int, item_type: str,
        items: list[dict[str, int]], submit: bool,
    ) -> dict[str, object]: ...

    @abstractmethod
    def get_employee_previous_assessments(self, tenant_id: int, employee_id: int) -> list[dict[str, object]]: ...

    @abstractmethod
    def get_submitted_assessment(
        self, tenant_id: int, manager_employee_id: int, employee_id: int
    ) -> dict[str, object] | None: ...
