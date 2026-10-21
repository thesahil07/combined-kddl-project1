"""Employee self-service workspace endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.application.dtos.employee_assessment_dtos import EmployeeAssessmentRequest
from app.application.use_cases.get_employee_workspace import GetEmployeeWorkspaceUseCase
from app.application.use_cases.save_employee_assessment import SaveEmployeeAssessmentUseCase
from app.application.use_cases.start_employee_assessment import StartEmployeeAssessmentUseCase
from app.presentation.api.dependencies import (
    EmployeeScope,
    get_employee_workspace_use_case,
    get_save_employee_assessment_use_case,
    get_start_employee_assessment_use_case,
    require_employee_scope,
    get_current_user,
    get_session,
)
from app.domain.entities.user import User

router = APIRouter(tags=["employee"])


@router.get("/dashboard")
def dashboard(
    employee: EmployeeScope = Depends(require_employee_scope),
    use_case: GetEmployeeWorkspaceUseCase = Depends(get_employee_workspace_use_case),
) -> dict[str, object]:
    return use_case.dashboard(employee.tenant_id, employee.employee_id)


@router.get("/role")
def role(
    employee: EmployeeScope = Depends(require_employee_scope),
    use_case: GetEmployeeWorkspaceUseCase = Depends(get_employee_workspace_use_case),
) -> dict[str, object] | None:
    return use_case.role(employee.tenant_id, employee.employee_id)


@router.get("/level-definitions/{item_type}/{item_id}")
def level_definitions(
    item_type: str,
    item_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    if user.tenant_id is None:
        return {"levels": []}
    if item_type == "functional-skills":
        rows = session.execute(text("""
            SELECT level, CONCAT('Level ', level) AS title, description
            FROM functional_skill_level_definitions
            WHERE tenant_id=:tenant_id AND skill_id=:item_id ORDER BY level
        """), {"tenant_id": user.tenant_id, "item_id": item_id}).mappings().all()
    elif item_type == "success-behaviours":
        rows = session.execute(text("""
            SELECT level, title, description FROM proficiency_scale_levels
            WHERE tenant_id=:tenant_id AND scale_type='BEHAVIOUR' ORDER BY level
        """), {"tenant_id": user.tenant_id}).mappings().all()
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="assessment type not found")
    return {"levels": [dict(row) for row in rows]}


@router.post("/assessments/{assessment_type}/start")
def start_assessment(
    assessment_type: str,
    employee: EmployeeScope = Depends(require_employee_scope),
    use_case: StartEmployeeAssessmentUseCase = Depends(get_start_employee_assessment_use_case),
) -> dict[str, object]:
    return use_case.execute(employee.tenant_id, employee.employee_id, employee.user_id, _item_type(assessment_type))


@router.get("/assessments/previous")
def previous_assessments(
    employee: EmployeeScope = Depends(require_employee_scope),
    use_case: GetEmployeeWorkspaceUseCase = Depends(get_employee_workspace_use_case),
) -> list[dict[str, object]]:
    return use_case.previous_assessments(employee.tenant_id, employee.employee_id)


@router.get("/assessments/{assessment_type}")
def current_assessment(
    assessment_type: str,
    employee: EmployeeScope = Depends(require_employee_scope),
    use_case: GetEmployeeWorkspaceUseCase = Depends(get_employee_workspace_use_case),
) -> dict[str, object] | None:
    return use_case.current_assessment(employee.tenant_id, employee.employee_id, _item_type(assessment_type))


@router.put("/assessments/{assessment_type}")
def save_assessment(
    assessment_type: str,
    payload: EmployeeAssessmentRequest,
    employee: EmployeeScope = Depends(require_employee_scope),
    use_case: SaveEmployeeAssessmentUseCase = Depends(get_save_employee_assessment_use_case),
) -> dict[str, object]:
    return use_case.execute(employee.tenant_id, employee.employee_id, employee.user_id, _item_type(assessment_type), [item.model_dump() for item in payload.items], False)


@router.post("/assessments/{assessment_type}/submit")
def submit_assessment(
    assessment_type: str,
    payload: EmployeeAssessmentRequest,
    employee: EmployeeScope = Depends(require_employee_scope),
    use_case: SaveEmployeeAssessmentUseCase = Depends(get_save_employee_assessment_use_case),
) -> dict[str, object]:
    return use_case.execute(employee.tenant_id, employee.employee_id, employee.user_id, _item_type(assessment_type), [item.model_dump() for item in payload.items], True)


def _item_type(assessment_type: str) -> str:
    mappings = {"success-behaviours": "BEHAVIOUR", "functional-skills": "SKILL"}
    if assessment_type not in mappings:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="assessment type not found")
    return mappings[assessment_type]
