"""Living RBAC contract examples; retain until the real module routes supersede them."""

from fastapi import APIRouter, Depends

from app.domain.value_objects.role import Role
from app.presentation.api.dependencies import TenantScope, require_role, require_tenant_scope

router = APIRouter(tags=["rbac-examples"])


@router.get("/admin/tenants")
def list_tenants(_: object = Depends(require_role(Role.PGC_ADMIN))) -> dict[str, list[object]]:
    return {"items": []}


@router.get("/employees")
def list_employees(scope: TenantScope = Depends(require_tenant_scope)) -> dict[str, object]:
    """Placeholder proves all employee queries must receive a trusted scope."""
    return {"items": scope.filter_records([]), "tenant_id": scope.tenant_id,
            "division_scope_id": scope.division_scope_id}


@router.get("/admin/ks-generation/ping")
def ks_generation_ping(_: object = Depends(require_role(Role.PGC_ADMIN))) -> dict[str, str]:
    return {"status": "pgc-admin-only"}
