from app.application.use_cases.get_employee_workspace import GetEmployeeWorkspaceUseCase
from app.application.use_cases.save_employee_assessment import SaveEmployeeAssessmentUseCase
from app.application.use_cases.start_employee_assessment import StartEmployeeAssessmentUseCase


class FakeEmployeeWorkspaceRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def get_dashboard(self, tenant_id: int, employee_id: int) -> dict[str, object]:
        self.calls.append(("dashboard", tenant_id, employee_id))
        return {"success_behaviours_status": "PENDING"}

    def get_role(self, tenant_id: int, employee_id: int) -> dict[str, object]:
        self.calls.append(("role", tenant_id, employee_id))
        return {"title": "Fictional role"}

    def get_current_assessment(self, tenant_id: int, employee_id: int, item_type: str):
        self.calls.append(("current", tenant_id, employee_id, item_type))
        return None

    def get_previous_assessments(self, tenant_id: int, employee_id: int) -> list[dict[str, object]]:
        self.calls.append(("previous", tenant_id, employee_id))
        return []

    def start_assessment(self, tenant_id: int, employee_id: int, actor_user_id: int, item_type: str):
        self.calls.append(("start", tenant_id, employee_id, actor_user_id, item_type))
        return {"items": []}

    def save_assessment(self, tenant_id: int, employee_id: int, actor_user_id: int, item_type: str, items, submit: bool):
        self.calls.append(("save", tenant_id, employee_id, actor_user_id, item_type, items, submit))
        return {"items": items}


def test_employee_workspace_use_cases_keep_the_trusted_tenant_and_employee_scope() -> None:
    repository = FakeEmployeeWorkspaceRepository()
    reader = GetEmployeeWorkspaceUseCase(repository)  # type: ignore[arg-type]
    starter = StartEmployeeAssessmentUseCase(repository)  # type: ignore[arg-type]
    saver = SaveEmployeeAssessmentUseCase(repository)  # type: ignore[arg-type]

    assert reader.dashboard(7, 11)["success_behaviours_status"] == "PENDING"
    assert starter.execute(7, 11, 4, "BEHAVIOUR") == {"items": []}
    assert saver.execute(7, 11, 4, "SKILL", [{"item_id": 9, "self_assessment_level": 3}], True) == {"items": [{"item_id": 9, "self_assessment_level": 3}]}
    assert repository.calls == [
        ("dashboard", 7, 11),
        ("start", 7, 11, 4, "BEHAVIOUR"),
        ("save", 7, 11, 4, "SKILL", [{"item_id": 9, "self_assessment_level": 3}], True),
    ]
