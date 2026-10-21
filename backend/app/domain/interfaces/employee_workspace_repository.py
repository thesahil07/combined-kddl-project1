"""Read/write contract for an employee's own assessment workspace."""

from abc import ABC, abstractmethod


class EmployeeWorkspaceRepository(ABC):
    @abstractmethod
    def get_dashboard(self, tenant_id: int, employee_id: int) -> dict[str, object]: ...

    @abstractmethod
    def get_role(self, tenant_id: int, employee_id: int) -> dict[str, object] | None: ...

    @abstractmethod
    def start_assessment(
        self, tenant_id: int, employee_id: int, actor_user_id: int, item_type: str
    ) -> dict[str, object]: ...

    @abstractmethod
    def get_current_assessment(
        self, tenant_id: int, employee_id: int, item_type: str
    ) -> dict[str, object] | None: ...

    @abstractmethod
    def save_assessment(
        self,
        tenant_id: int,
        employee_id: int,
        actor_user_id: int,
        item_type: str,
        items: list[dict[str, int]],
        submit: bool,
    ) -> dict[str, object]: ...

    @abstractmethod
    def get_previous_assessments(self, tenant_id: int, employee_id: int) -> list[dict[str, object]]: ...
