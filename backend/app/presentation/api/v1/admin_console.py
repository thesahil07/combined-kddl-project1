"""HR assessment oversight endpoints."""

from fastapi import APIRouter, Depends, Query

from app.application.use_cases.get_admin_console import GetAdminConsoleUseCase
from app.presentation.api.dependencies import TenantScope, get_admin_console_use_case, require_admin_console_access

router = APIRouter(tags=["admin-console"])


@router.get("/assessment-report")
def assessment_report(
    division_id: int | None = Query(default=None),
    cycle_id: int | None = Query(default=None),
    employee_name: str | None = Query(default=None, min_length=1, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=5, le=100),
    scope: TenantScope = Depends(require_admin_console_access),
    use_case: GetAdminConsoleUseCase = Depends(get_admin_console_use_case),
) -> dict[str, object]:
    if scope.tenant_id is None:
        return {"divisions": [], "cycles": [], "selected_cycle_id": None, "employees": [], "summary": {}, "page": page, "page_size": page_size, "total_employees": 0}
    if scope.division_scope_id is not None:
        division_id = scope.division_scope_id
    return use_case.execute(
        scope.tenant_id, division_id, cycle_id, employee_name, page, page_size,
    )


@router.get("/assessments/{employee_id}")
def submitted_assessment(
    employee_id: int,
    cycle_id: int = Query(..., ge=1),
    scope: TenantScope = Depends(require_admin_console_access),
    use_case: GetAdminConsoleUseCase = Depends(get_admin_console_use_case),
) -> dict[str, object] | None:
    if scope.tenant_id is None:
        return None
    return use_case.get_submitted_assessment(scope.tenant_id, employee_id, cycle_id)
