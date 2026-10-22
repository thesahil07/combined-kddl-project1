import io
import openpyxl
from fastapi.testclient import TestClient

from app.application.use_cases.get_admin_console import GetAdminConsoleUseCase
from app.domain.interfaces.admin_console_repository import AdminConsoleRepository
from app.main import app
from app.presentation.api.dependencies import (
    TenantScope,
    get_admin_console_use_case,
    require_admin_console_access,
)


class FakeAdminConsoleRepo(AdminConsoleRepository):
    def get_assessment_report(self, division_id=None, cycle_id=None, page=1, page_size=20, employee_name=None):
        return None

    def get_submitted_assessment(self, employee_id: int, cycle_id: int | None = None):
        return None

    def export_assessment_gaps_excel(
        self,
        tenant_id: int,
        division_id: int | None = None,
        cycle_id: int | None = None,
        employee_name: str | None = None,
    ) -> tuple[bytes, str]:
        from openpyxl import Workbook

        wb = Workbook()
        ws_all = wb.active
        ws_all.title = "All Assessment Gaps"

        headers = [
            "Employee Name",
            "Employee Code",
            "Division",
            "Function",
            "Department",
            "Role",
            "Grade",
            "Manager Name",
            "Category",
            "Skill / Behaviour Name",
            "Desired Level (DL)",
            "Self Assessment Level (SAL)",
            "Manager Assessment Level (MAL)",
            "Gap (MAL - DL)",
            "Gap Status",
        ]
        ws_all.append(headers)

        ws_sb = wb.create_sheet(title="Success Behaviours")
        ws_sb.append(headers)

        ws_fs = wb.create_sheet(title="Functional Skills")
        ws_fs.append(headers)

        sample_row = [
            "Aarav Sharma",
            "EMP001",
            "Precision Engineering",
            "Engineering",
            "Design",
            "Senior Engineer",
            "E3",
            "Rajesh Kumar",
            "Success Behaviour",
            "Problem Solving",
            4,
            3,
            2,
            -2,
            "Negative Gap (-2)",
        ]
        ws_all.append(sample_row)
        ws_sb.append(sample_row)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue(), "KDDL_Assessment_Gaps_Export_2026.xlsx"


def test_admin_console_export_excel_endpoint():
    fake_repo = FakeAdminConsoleRepo()
    fake_use_case = GetAdminConsoleUseCase(fake_repo)

    app.dependency_overrides[get_admin_console_use_case] = lambda: fake_use_case
    app.dependency_overrides[require_admin_console_access] = lambda: TenantScope(
        tenant_id=1, division_scope_id=None, is_platform_admin=True
    )

    client = TestClient(app)
    response = client.get("/api/v1/admin-console/export-excel?cycle_id=1")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "attachment; filename=" in response.headers["content-disposition"]
    assert "Assessment_Gaps_Export" in response.headers["content-disposition"]

    # Verify openpyxl can read the returned workbook
    wb = openpyxl.load_workbook(io.BytesIO(response.content))
    sheet_names = wb.sheetnames
    assert "All Assessment Gaps" in sheet_names
    assert "Success Behaviours" in sheet_names
    assert "Functional Skills" in sheet_names

    ws = wb["All Assessment Gaps"]
    row1 = [cell.value for cell in ws[1]]
    assert "Employee Name" in row1
    assert "Employee Code" in row1
    assert "Function" in row1
    assert "Department" in row1
    assert "Role" in row1
    assert "Grade" in row1
    assert "Manager Name" in row1
    assert "Desired Level (DL)" in row1
    assert "Self Assessment Level (SAL)" in row1
    assert "Manager Assessment Level (MAL)" in row1
    assert "Gap (MAL - DL)" in row1
