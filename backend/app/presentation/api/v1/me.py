"""Authenticated current-user profile endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.user import User
from app.domain.value_objects.role import Role
from app.infrastructure.database.models.tenancy_identity import AdminConsoleAccessModel, ExecutiveReviewAccessModel
from app.infrastructure.database.models.module_b import EmployeeModel
from app.presentation.api.dependencies import get_current_user, get_session

router = APIRouter(tags=["auth"])


class MeResponse(BaseModel):
    user_id: int
    tenant_id: int | None
    email: str
    role: str
    employee_id: int | None
    division_scope_id: int | None
    status: str
    admin_console_access: bool
    executive_review_access: bool
    is_manager: bool


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> MeResponse:
    permitted = current_user.role is Role.HR_SPOC or (
        current_user.tenant_id is not None and session.scalar(select(AdminConsoleAccessModel.access_id).where(
            AdminConsoleAccessModel.tenant_id == current_user.tenant_id,
            AdminConsoleAccessModel.user_id == current_user.user_id,
        )) is not None
    )
    is_manager = current_user.tenant_id is not None and current_user.employee_id is not None and session.scalar(
        select(EmployeeModel.employee_id).where(
            EmployeeModel.tenant_id == current_user.tenant_id,
            EmployeeModel.manager_employee_id == current_user.employee_id,
            EmployeeModel.status == "ACTIVE",
        ).limit(1)
    ) is not None
    executive_permitted = current_user.tenant_id is not None and session.scalar(select(ExecutiveReviewAccessModel.access_id).where(
        ExecutiveReviewAccessModel.tenant_id == current_user.tenant_id,
        ExecutiveReviewAccessModel.user_id == current_user.user_id,
    )) is not None
    return MeResponse(**current_user.__dict__, admin_console_access=permitted, executive_review_access=executive_permitted, is_manager=is_manager) if hasattr(current_user, "__dict__") else MeResponse(
        user_id=current_user.user_id, tenant_id=current_user.tenant_id, email=current_user.email,
        role=current_user.role.value, employee_id=current_user.employee_id,
        division_scope_id=current_user.division_scope_id, status=current_user.status.value,
        admin_console_access=permitted, executive_review_access=executive_permitted, is_manager=is_manager)
