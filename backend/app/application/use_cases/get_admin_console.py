"""Retrieve tenant-scoped assessment oversight data."""

from app.domain.interfaces.admin_console_repository import AdminConsoleRepository


class GetAdminConsoleUseCase:
    def __init__(self, repository: AdminConsoleRepository) -> None:
        self._repository = repository

    def execute(
        self, tenant_id: int, division_id: int | None, cycle_id: int | None,
        employee_name: str | None, page: int, page_size: int,
    ) -> dict[str, object]:
        return self._repository.get_assessment_report(
            tenant_id, division_id, cycle_id, employee_name, page, page_size,
        )

    def get_submitted_assessment(self, tenant_id: int, employee_id: int, cycle_id: int) -> dict[str, object] | None:
        return self._repository.get_submitted_assessment(tenant_id, employee_id, cycle_id)

    def export_excel(
        self, tenant_id: int, division_id: int | None, cycle_id: int | None,
        employee_name: str | None,
    ) -> tuple[bytes, str]:
        return self._repository.export_assessment_gaps_excel(
            tenant_id, division_id, cycle_id, employee_name
        )
