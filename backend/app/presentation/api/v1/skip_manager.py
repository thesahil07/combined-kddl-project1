"""Skip Manager's tenant-scoped workspace endpoints."""

from fastapi import APIRouter, Depends

from app.application.use_cases.get_skip_manager_dashboard import GetSkipManagerDashboardUseCase
from app.application.use_cases.save_role_description import SaveRoleDescriptionUseCase
from app.application.use_cases.submit_role_description import SubmitRoleDescriptionUseCase
from app.application.dtos.role_dtos import RoleDescriptionRequest
from app.application.dtos.employee_assessment_dtos import EmployeeAssessmentRequest
from app.application.use_cases.save_manager_assessment import SaveManagerAssessmentUseCase
from app.application.use_cases.start_employee_assessment import StartEmployeeAssessmentUseCase
from app.domain.exceptions.application_errors import InvalidStateError
from app.domain.interfaces.role_description_repository import RoleDescriptionRepository
from app.presentation.api.dependencies import (
    SkipManagerScope,
    get_skip_manager_dashboard_use_case,
    get_save_role_description_use_case,
    get_submit_role_description_use_case,
    get_role_description_repository,
    get_save_manager_assessment_use_case,
    get_start_employee_assessment_use_case,
    require_skip_manager_scope,
)

router = APIRouter(tags=["skip-manager"])


@router.get("/dashboard")
def dashboard(
    manager: SkipManagerScope = Depends(require_skip_manager_scope),
    use_case: GetSkipManagerDashboardUseCase = Depends(get_skip_manager_dashboard_use_case),
) -> dict[str, object]:
    return use_case.execute(manager.tenant_id, manager.manager_employee_id)


@router.get("/gaps")
def gaps(
    manager: SkipManagerScope = Depends(require_skip_manager_scope),
    use_case: GetSkipManagerDashboardUseCase = Depends(get_skip_manager_dashboard_use_case),
) -> dict[str, object]:
    return use_case.get_gap_matrices(manager.tenant_id, manager.manager_employee_id)


@router.get("/assessments/{employee_id}")
def employee_assessment(
    employee_id: int,
    manager: SkipManagerScope = Depends(require_skip_manager_scope),
    dashboard: GetSkipManagerDashboardUseCase = Depends(get_skip_manager_dashboard_use_case),
    start_assessment: StartEmployeeAssessmentUseCase = Depends(get_start_employee_assessment_use_case),
) -> dict[str, object] | None:
    dashboard.ensure_can_assess_employee(manager.tenant_id, manager.manager_employee_id, employee_id)
    # Managers may complete their assessment first. Create each available
    # section on demand so a direct report does not have to open it first.
    for item_type in ("BEHAVIOUR", "SKILL"):
        try:
            start_assessment.execute(manager.tenant_id, employee_id, manager.user_id, item_type)
        except InvalidStateError:
            # A functional-skill mapping may genuinely be absent. The returned
            # assessment then simply contains no items for that section.
            pass
    return dashboard.get_employee_assessment(manager.tenant_id, employee_id)


@router.put("/assessments/{employee_id}/{assessment_type}")
def save_manager_assessment(
    employee_id: int,
    assessment_type: str,
    payload: EmployeeAssessmentRequest,
    manager: SkipManagerScope = Depends(require_skip_manager_scope),
    dashboard: GetSkipManagerDashboardUseCase = Depends(get_skip_manager_dashboard_use_case),
    use_case: SaveManagerAssessmentUseCase = Depends(get_save_manager_assessment_use_case),
) -> dict[str, object]:
    dashboard.ensure_can_assess_employee(manager.tenant_id, manager.manager_employee_id, employee_id)
    return use_case.execute(manager.tenant_id, employee_id, manager.user_id, _item_type(assessment_type), [item.model_dump() for item in payload.items], False)


@router.post("/assessments/{employee_id}/{assessment_type}/submit")
def submit_manager_assessment(
    employee_id: int,
    assessment_type: str,
    payload: EmployeeAssessmentRequest,
    manager: SkipManagerScope = Depends(require_skip_manager_scope),
    dashboard: GetSkipManagerDashboardUseCase = Depends(get_skip_manager_dashboard_use_case),
    use_case: SaveManagerAssessmentUseCase = Depends(get_save_manager_assessment_use_case),
) -> dict[str, object]:
    dashboard.ensure_can_assess_employee(manager.tenant_id, manager.manager_employee_id, employee_id)
    return use_case.execute(manager.tenant_id, employee_id, manager.user_id, _item_type(assessment_type), [item.model_dump() for item in payload.items], True)


@router.get("/assessments/{employee_id}/previous")
def employee_previous_assessments(
    employee_id: int,
    manager: SkipManagerScope = Depends(require_skip_manager_scope),
    dashboard: GetSkipManagerDashboardUseCase = Depends(get_skip_manager_dashboard_use_case),
) -> list[dict[str, object]]:
    dashboard.ensure_can_assess_employee(manager.tenant_id, manager.manager_employee_id, employee_id)
    return dashboard.get_employee_previous_assessments(manager.tenant_id, employee_id)


@router.get("/assessments/{employee_id}/submitted")
def submitted_employee_assessment(
    employee_id: int,
    manager: SkipManagerScope = Depends(require_skip_manager_scope),
    dashboard: GetSkipManagerDashboardUseCase = Depends(get_skip_manager_dashboard_use_case),
) -> dict[str, object] | None:
    """Read-only current-cycle assessment submitted by a direct report."""
    dashboard.ensure_can_assess_employee(manager.tenant_id, manager.manager_employee_id, employee_id)
    return dashboard.get_submitted_assessment(
        manager.tenant_id, manager.manager_employee_id, employee_id
    )


@router.get("/team-members/{employee_id}/role-definition")
def team_member_role_definition(
    employee_id: int,
    manager: SkipManagerScope = Depends(require_skip_manager_scope),
    dashboard: GetSkipManagerDashboardUseCase = Depends(get_skip_manager_dashboard_use_case),
) -> dict[str, object] | None:
    """Read a direct report's current role definition without permitting edits."""
    dashboard.ensure_can_assess_employee(
        manager.tenant_id, manager.manager_employee_id, employee_id
    )
    return dashboard.get_team_member_role_definition(manager.tenant_id, employee_id)


def _item_type(assessment_type: str) -> str:
    mappings = {"success-behaviours": "BEHAVIOUR", "functional-skills": "SKILL"}
    if assessment_type not in mappings:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="assessment type not found")
    return mappings[assessment_type]


@router.put("/role-definitions/{role_id}")
def save_team_role_definition(
    role_id: int,
    payload: RoleDescriptionRequest,
    manager: SkipManagerScope = Depends(require_skip_manager_scope),
    dashboard: GetSkipManagerDashboardUseCase = Depends(get_skip_manager_dashboard_use_case),
    use_case: SaveRoleDescriptionUseCase = Depends(get_save_role_description_use_case),
):
    dashboard.ensure_can_author_role(manager.tenant_id, manager.manager_employee_id, role_id)
    return use_case.execute(role_id, manager.tenant_id, payload.model_dump())


@router.get("/role-definitions/{role_id}")
def get_team_role_definition(
    role_id: int,
    manager: SkipManagerScope = Depends(require_skip_manager_scope),
    dashboard: GetSkipManagerDashboardUseCase = Depends(get_skip_manager_dashboard_use_case),
    descriptions: RoleDescriptionRepository = Depends(get_role_description_repository),
) -> dict[str, object]:
    dashboard.ensure_can_author_role(manager.tenant_id, manager.manager_employee_id, role_id)
    description = descriptions.current_scoped(role_id, manager.tenant_id)
    if description is None:
        return {}
    return {
        "people_count": description.people_count,
        "role_definition": description.role_definition,
        "key_responsibilities": description.key_responsibilities,
        "kpis": description.kpis,
        "education_certifications": description.education_certifications,
        "minimum_relevant_experience": description.minimum_relevant_experience,
        "knowledge_required": description.knowledge_required,
        "skills_required": description.skills_required,
        "attitudes_behaviours": description.attitudes_behaviours,
        "equipment_process_refs": description.equipment_process_refs,
    }


@router.post("/role-definitions/{role_id}/submit")
def submit_team_role_definition(
    role_id: int,
    payload: RoleDescriptionRequest,
    manager: SkipManagerScope = Depends(require_skip_manager_scope),
    dashboard: GetSkipManagerDashboardUseCase = Depends(get_skip_manager_dashboard_use_case),
    use_case: SubmitRoleDescriptionUseCase = Depends(get_submit_role_description_use_case),
):
    dashboard.ensure_can_author_role(manager.tenant_id, manager.manager_employee_id, role_id)
    return use_case.execute(role_id, manager.tenant_id, payload.model_dump())
