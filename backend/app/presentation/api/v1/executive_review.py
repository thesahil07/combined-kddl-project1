"""Read-only Executive Review endpoints."""

from fastapi import APIRouter, Depends, Query

from app.application.use_cases.get_executive_review import GetExecutiveReviewUseCase
from app.presentation.api.dependencies import TenantScope, get_executive_review_use_case, require_executive_review_access

router = APIRouter(tags=["executive-review"])


@router.get("/dashboard")
def dashboard(
    division_id: int | None = Query(default=None, ge=1),
    scope: TenantScope = Depends(require_executive_review_access),
    use_case: GetExecutiveReviewUseCase = Depends(get_executive_review_use_case),
) -> dict[str, object]:
    if scope.tenant_id is None:
        return {}
    if scope.division_scope_id is not None:
        division_id = scope.division_scope_id
    return use_case.execute(scope.tenant_id, division_id)
