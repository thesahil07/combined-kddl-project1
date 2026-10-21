"""Module D role creation and role-description endpoints."""

from fastapi import APIRouter, Depends

from app.application.dtos.role_dtos import CreateRoleRequest, RoleDescriptionRequest
from app.application.use_cases.create_role import CreateRoleUseCase
from app.application.use_cases.save_role_description import SaveRoleDescriptionUseCase
from app.application.use_cases.validate_role_description import ValidateRoleDescriptionUseCase
from app.application.use_cases.refine_role_description import RefineRoleDescriptionUseCase
from app.application.use_cases.list_roles import ListRolesUseCase
from app.domain.entities.user import User
from app.domain.value_objects.role import Role
from app.presentation.api.dependencies import (TenantScope, get_create_role_use_case,
    get_list_roles_use_case, get_refine_role_description_use_case,
    get_save_role_description_use_case, get_validate_role_description_use_case,
    require_role, require_target_tenant_scope,
    require_tenant_scope)

router = APIRouter(tags=["role-descriptions"])


@router.post("")
def create_role(
    payload: CreateRoleRequest,
    scope: TenantScope = Depends(require_target_tenant_scope),
    _: User = Depends(require_role(Role.HR_SPOC, Role.PGC_ADMIN)),
    use_case: CreateRoleUseCase = Depends(get_create_role_use_case),
):
    return use_case.execute(scope.tenant_id or 0, payload.division_id, payload.function_id, payload.title)


@router.get("")
def list_roles(
    scope: TenantScope = Depends(require_target_tenant_scope),
    use_case: ListRolesUseCase = Depends(get_list_roles_use_case),
):
    return {"items": use_case.execute(scope.tenant_id or 0, scope.division_scope_id)}


@router.put("/{role_id}/description")
@router.post("/{role_id}/description")
def save_description(
    role_id: int,
    payload: RoleDescriptionRequest,
    scope: TenantScope = Depends(require_tenant_scope),
    _: User = Depends(require_role(Role.HOD_MANAGER)),
    use_case: SaveRoleDescriptionUseCase = Depends(get_save_role_description_use_case),
):
    return use_case.execute(role_id, scope.tenant_id or 0, payload.model_dump())


@router.post("/{role_id}/description/validate")
def validate_description(
    role_id: int,
    user: User = Depends(require_role(Role.HOD_MANAGER)),
    scope: TenantScope = Depends(require_tenant_scope),
    use_case: ValidateRoleDescriptionUseCase = Depends(get_validate_role_description_use_case),
):
    return use_case.execute(role_id, scope.tenant_id or 0, user.employee_id)


@router.post("/{role_id}/description/ai-refine")
def ai_refine(
    role_id: int,
    scope: TenantScope = Depends(require_tenant_scope),
    _: User = Depends(require_role(Role.HOD_MANAGER)),
    use_case: RefineRoleDescriptionUseCase = Depends(get_refine_role_description_use_case),
):
    suggestion = use_case.execute(role_id, scope.tenant_id or 0)
    return {"role_id": role_id, "tenant_id": scope.tenant_id, "suggestion": suggestion}
