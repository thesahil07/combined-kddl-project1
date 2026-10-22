import io
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.interfaces.admin_console_repository import AdminConsoleRepository


class SqlAlchemyAdminConsoleRepository(AdminConsoleRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_assessment_report(
        self, tenant_id: int, division_id: int | None, cycle_id: int | None,
        employee_name: str | None, page: int, page_size: int,
    ) -> dict[str, object]:
        divisions = self._session.execute(text("""
            SELECT d.division_id, d.name FROM divisions d
            JOIN entities en ON en.entity_id=d.entity_id AND en.tenant_id=d.tenant_id
            WHERE d.tenant_id=:tenant_id AND en.code <> 'CORPORATE'
              AND d.code <> 'TARATEC-LDR' ORDER BY d.name
        """), {"tenant_id": tenant_id}).mappings().all()
        cycles = self._session.execute(text("""
            SELECT cycle_id, name, period_start, period_end, status FROM assessment_cycles
            WHERE tenant_id=:tenant_id ORDER BY period_start DESC
        """), {"tenant_id": tenant_id}).mappings().all()
        selected_cycle = cycle_id or (cycles[0]["cycle_id"] if cycles else None)
        if selected_cycle is not None and not any(row["cycle_id"] == selected_cycle for row in cycles):
            raise ValueError("assessment cycle is outside the tenant scope")
        count = self._session.execute(text("""
            SELECT COUNT(*) FROM employees e
            JOIN divisions d ON d.division_id=e.division_id AND d.tenant_id=e.tenant_id
            JOIN entities en ON en.entity_id=d.entity_id AND en.tenant_id=d.tenant_id
            WHERE e.tenant_id=:tenant_id AND e.status='ACTIVE' AND en.code <> 'CORPORATE'
              AND d.code <> 'TARATEC-LDR'
              AND (:division_id IS NULL OR e.division_id=:division_id)
              AND (:employee_name IS NULL OR LOWER(e.full_name) LIKE CONCAT('%', LOWER(:employee_name), '%'))
        """), {"tenant_id": tenant_id, "division_id": division_id,
               "employee_name": employee_name}).scalar_one()
        rows = self._session.execute(text("""
            SELECT e.employee_id, e.employee_code, e.full_name, d.name AS division_name,
                   manager.full_name AS manager_name, COALESCE(r.title, e.designation) AS role_title,
                   CASE WHEN behaviour.form_id IS NULL THEN 'PENDING_WITH_EMPLOYEE'
                        WHEN behaviour.behaviour_self_submitted_at IS NULL THEN 'PENDING_WITH_EMPLOYEE'
                        ELSE 'COMPLETED' END AS behaviour_self_status,
                   CASE WHEN behaviour.form_id IS NULL THEN 'PENDING_WITH_MANAGER'
                        WHEN behaviour.behaviour_manager_submitted_at IS NULL THEN 'PENDING_WITH_MANAGER'
                        ELSE 'COMPLETED' END AS behaviour_manager_status,
                   CASE WHEN functional.form_id IS NULL AND EXISTS (
                            SELECT 1 FROM functional_skills fs
                            JOIN desired_level_matrix dlm ON dlm.tenant_id=fs.tenant_id
                                AND dlm.division_id=e.division_id AND dlm.item_type='SKILL'
                                AND dlm.item_id=fs.skill_id AND dlm.department_id <=> e.department_id
                                AND dlm.grade_band_id=e.grade_band_id
                            WHERE fs.tenant_id=e.tenant_id AND fs.division_id=e.division_id
                                AND fs.function_id=e.function_id AND fs.department_id <=> e.department_id
                        ) THEN 'PENDING_WITH_EMPLOYEE'
                        WHEN functional.form_id IS NULL THEN 'NOT_CONFIGURED'
                        WHEN functional.functional_self_submitted_at IS NULL THEN 'PENDING_WITH_EMPLOYEE'
                        ELSE 'COMPLETED' END AS functional_self_status,
                   CASE WHEN functional.form_id IS NULL AND EXISTS (
                            SELECT 1 FROM functional_skills fs
                            JOIN desired_level_matrix dlm ON dlm.tenant_id=fs.tenant_id
                                AND dlm.division_id=e.division_id AND dlm.item_type='SKILL'
                                AND dlm.item_id=fs.skill_id AND dlm.department_id <=> e.department_id
                                AND dlm.grade_band_id=e.grade_band_id
                            WHERE fs.tenant_id=e.tenant_id AND fs.division_id=e.division_id
                                AND fs.function_id=e.function_id AND fs.department_id <=> e.department_id
                        ) THEN 'PENDING_WITH_MANAGER'
                        WHEN functional.form_id IS NULL THEN 'NOT_CONFIGURED'
                        WHEN functional.functional_manager_submitted_at IS NULL THEN 'PENDING_WITH_MANAGER'
                        ELSE 'COMPLETED' END AS functional_manager_status,
                   COALESCE(g.behaviour_gaps, 0) AS behaviour_gaps,
                   COALESCE(g.functional_gaps, 0) AS functional_gaps
            FROM employees e
            JOIN divisions d ON d.division_id=e.division_id AND d.tenant_id=e.tenant_id
            JOIN entities en ON en.entity_id=d.entity_id AND en.tenant_id=d.tenant_id
            LEFT JOIN employees manager ON manager.employee_id=e.manager_employee_id AND manager.tenant_id=e.tenant_id
            LEFT JOIN roles r ON r.role_id=e.role_id AND r.tenant_id=e.tenant_id AND r.division_id=e.division_id
            LEFT JOIN assessment_forms behaviour ON behaviour.tenant_id=e.tenant_id AND behaviour.employee_id=e.employee_id
                AND behaviour.cycle_id=:cycle_id AND behaviour.assessment_type='BEHAVIOUR'
            LEFT JOIN assessment_forms functional ON functional.tenant_id=e.tenant_id AND functional.employee_id=e.employee_id
                AND functional.cycle_id=:cycle_id AND functional.assessment_type='SKILL'
            LEFT JOIN (
                SELECT af.employee_id,
                    SUM(CASE WHEN ali.item_type='BEHAVIOUR' AND ali.gap < 0 THEN 1 ELSE 0 END) AS behaviour_gaps,
                    SUM(CASE WHEN ali.item_type='SKILL' AND ali.gap < 0 THEN 1 ELSE 0 END) AS functional_gaps
                FROM assessment_forms af JOIN assessment_line_items ali ON ali.form_id=af.form_id
                WHERE af.tenant_id=:tenant_id AND af.cycle_id=:cycle_id GROUP BY af.employee_id
            ) g ON g.employee_id=e.employee_id
            WHERE e.tenant_id=:tenant_id AND e.status='ACTIVE' AND en.code <> 'CORPORATE'
              AND d.code <> 'TARATEC-LDR'
              AND (:division_id IS NULL OR e.division_id=:division_id)
              AND (:employee_name IS NULL OR LOWER(e.full_name) LIKE CONCAT('%', LOWER(:employee_name), '%'))
            ORDER BY d.name, manager.full_name, e.full_name
            LIMIT :limit OFFSET :offset
        """), {"tenant_id": tenant_id, "division_id": division_id,
                "employee_name": employee_name, "cycle_id": selected_cycle,
                "limit": page_size, "offset": (page - 1) * page_size}).mappings().all() if selected_cycle else []
        results = [dict(row) for row in rows]
        # KPIs describe the complete filtered population, not merely the page
        # currently rendered in the employee table.
        summary = self._session.execute(text("""
            SELECT
                COALESCE(SUM(CASE WHEN (
                    behaviour.form_id IS NULL OR behaviour.behaviour_self_submitted_at IS NULL
                    OR (
                        (functional.form_id IS NOT NULL AND functional.functional_self_submitted_at IS NULL)
                        OR (functional.form_id IS NULL AND EXISTS (
                            SELECT 1 FROM functional_skills fs
                            JOIN desired_level_matrix dlm ON dlm.tenant_id=fs.tenant_id
                                AND dlm.division_id=e.division_id AND dlm.item_type='SKILL'
                                AND dlm.item_id=fs.skill_id AND dlm.department_id <=> e.department_id
                                AND dlm.grade_band_id=e.grade_band_id
                            WHERE fs.tenant_id=e.tenant_id AND fs.division_id=e.division_id
                                AND fs.function_id=e.function_id AND fs.department_id <=> e.department_id
                        ))
                    )
                ) THEN 1 ELSE 0 END), 0) AS self_pending_employees,
                COALESCE(SUM(CASE WHEN (
                    behaviour.form_id IS NULL OR behaviour.behaviour_manager_submitted_at IS NULL
                    OR (
                        (functional.form_id IS NOT NULL AND functional.functional_manager_submitted_at IS NULL)
                        OR (functional.form_id IS NULL AND EXISTS (
                            SELECT 1 FROM functional_skills fs
                            JOIN desired_level_matrix dlm ON dlm.tenant_id=fs.tenant_id
                                AND dlm.division_id=e.division_id AND dlm.item_type='SKILL'
                                AND dlm.item_id=fs.skill_id AND dlm.department_id <=> e.department_id
                                AND dlm.grade_band_id=e.grade_band_id
                            WHERE fs.tenant_id=e.tenant_id AND fs.division_id=e.division_id
                                AND fs.function_id=e.function_id AND fs.department_id <=> e.department_id
                        ))
                    )
                ) THEN 1 ELSE 0 END), 0) AS manager_pending_employees,
                COALESCE(SUM(CASE WHEN behaviour.form_id IS NULL
                    OR behaviour.behaviour_self_submitted_at IS NULL THEN 1 ELSE 0 END), 0) AS behaviour_self_pending,
                COALESCE(SUM(CASE WHEN behaviour.form_id IS NULL
                    OR behaviour.behaviour_manager_submitted_at IS NULL THEN 1 ELSE 0 END), 0) AS behaviour_manager_pending,
                COALESCE(SUM(CASE WHEN functional.form_id IS NOT NULL
                    AND functional.functional_self_submitted_at IS NULL THEN 1
                    WHEN functional.form_id IS NULL AND EXISTS (
                        SELECT 1 FROM functional_skills fs
                        JOIN desired_level_matrix dlm ON dlm.tenant_id=fs.tenant_id
                            AND dlm.division_id=e.division_id AND dlm.item_type='SKILL'
                            AND dlm.item_id=fs.skill_id AND dlm.department_id <=> e.department_id
                            AND dlm.grade_band_id=e.grade_band_id
                        WHERE fs.tenant_id=e.tenant_id AND fs.division_id=e.division_id
                            AND fs.function_id=e.function_id AND fs.department_id <=> e.department_id
                    ) THEN 1 ELSE 0 END), 0) AS functional_self_pending,
                COALESCE(SUM(CASE WHEN functional.form_id IS NOT NULL
                    AND functional.functional_manager_submitted_at IS NULL THEN 1
                    WHEN functional.form_id IS NULL AND EXISTS (
                        SELECT 1 FROM functional_skills fs
                        JOIN desired_level_matrix dlm ON dlm.tenant_id=fs.tenant_id
                            AND dlm.division_id=e.division_id AND dlm.item_type='SKILL'
                            AND dlm.item_id=fs.skill_id AND dlm.department_id <=> e.department_id
                            AND dlm.grade_band_id=e.grade_band_id
                        WHERE fs.tenant_id=e.tenant_id AND fs.division_id=e.division_id
                            AND fs.function_id=e.function_id AND fs.department_id <=> e.department_id
                    ) THEN 1 ELSE 0 END), 0) AS functional_manager_pending,
                COALESCE(SUM(g.behaviour_gaps), 0) AS behaviour_gaps,
                COALESCE(SUM(g.functional_gaps), 0) AS functional_gaps
            FROM employees e
            JOIN divisions d ON d.division_id=e.division_id AND d.tenant_id=e.tenant_id
            JOIN entities en ON en.entity_id=d.entity_id AND en.tenant_id=d.tenant_id
            LEFT JOIN assessment_forms behaviour ON behaviour.tenant_id=e.tenant_id AND behaviour.employee_id=e.employee_id
                AND behaviour.cycle_id=:cycle_id AND behaviour.assessment_type='BEHAVIOUR'
            LEFT JOIN assessment_forms functional ON functional.tenant_id=e.tenant_id AND functional.employee_id=e.employee_id
                AND functional.cycle_id=:cycle_id AND functional.assessment_type='SKILL'
            LEFT JOIN (
                SELECT af.employee_id,
                    SUM(CASE WHEN ali.item_type='BEHAVIOUR' AND ali.gap < 0 THEN 1 ELSE 0 END) AS behaviour_gaps,
                    SUM(CASE WHEN ali.item_type='SKILL' AND ali.gap < 0 THEN 1 ELSE 0 END) AS functional_gaps
                FROM assessment_forms af JOIN assessment_line_items ali ON ali.form_id=af.form_id
                WHERE af.tenant_id=:tenant_id AND af.cycle_id=:cycle_id GROUP BY af.employee_id
            ) g ON g.employee_id=e.employee_id
            WHERE e.tenant_id=:tenant_id AND e.status='ACTIVE' AND en.code <> 'CORPORATE'
              AND d.code <> 'TARATEC-LDR'
              AND (:division_id IS NULL OR e.division_id=:division_id)
              AND (:employee_name IS NULL OR LOWER(e.full_name) LIKE CONCAT('%', LOWER(:employee_name), '%'))
        """), {"tenant_id": tenant_id, "division_id": division_id,
                "employee_name": employee_name, "cycle_id": selected_cycle}).mappings().one() if selected_cycle else {
                    "self_pending_employees": 0, "manager_pending_employees": 0,
                    "behaviour_self_pending": 0, "behaviour_manager_pending": 0,
                    "functional_self_pending": 0, "functional_manager_pending": 0,
                    "behaviour_gaps": 0, "functional_gaps": 0,
                }
        return {
            "divisions": [dict(row) for row in divisions],
            "cycles": [dict(row) for row in cycles],
            "selected_cycle_id": selected_cycle,
            "page": page,
            "page_size": page_size,
            "total_employees": int(count),
            "employees": results,
            "summary": {
                "employees": int(count),
                "self_pending_employees": int(summary.get("self_pending_employees", 0)),
                "manager_pending_employees": int(summary.get("manager_pending_employees", 0)),
                "behaviour_self_pending": int(summary["behaviour_self_pending"]),
                "behaviour_manager_pending": int(summary["behaviour_manager_pending"]),
                "functional_self_pending": int(summary["functional_self_pending"]),
                "functional_manager_pending": int(summary["functional_manager_pending"]),
                "behaviour_gaps": int(summary["behaviour_gaps"]),
                "functional_gaps": int(summary["functional_gaps"]),
            },
        }

    def get_submitted_assessment(self, tenant_id: int, employee_id: int, cycle_id: int) -> dict[str, object] | None:
        employee = self._session.execute(text("""
            SELECT e.employee_id, e.employee_code, e.full_name, d.name AS division_name
            FROM employees e
            JOIN divisions d ON d.division_id=e.division_id AND d.tenant_id=e.tenant_id
            JOIN entities en ON en.entity_id=d.entity_id AND en.tenant_id=d.tenant_id
            WHERE e.tenant_id=:tenant_id AND e.employee_id=:employee_id
              AND e.status='ACTIVE' AND en.code <> 'CORPORATE'
              AND d.code <> 'TARATEC-LDR'
        """), {"tenant_id": tenant_id, "employee_id": employee_id}).mappings().one_or_none()
        if employee is None:
            return None
        items = self._session.execute(text("""
            SELECT af.assessment_type, ali.item_type, ali.item_id, ali.desired_level,
                   ali.self_assessment_level, ali.manager_assessment_level, ali.gap,
                   COALESCE(sb.name, fs.name) AS item_name
            FROM assessment_forms af JOIN assessment_line_items ali ON ali.form_id=af.form_id
            LEFT JOIN success_behaviours sb ON ali.item_type='BEHAVIOUR' AND sb.behaviour_id=ali.item_id AND sb.tenant_id=af.tenant_id
            LEFT JOIN functional_skills fs ON ali.item_type='SKILL' AND fs.skill_id=ali.item_id AND fs.tenant_id=af.tenant_id
            WHERE af.tenant_id=:tenant_id AND af.employee_id=:employee_id AND af.cycle_id=:cycle_id
              AND ((af.assessment_type='BEHAVIOUR' AND af.behaviour_self_submitted_at IS NOT NULL)
                OR (af.assessment_type='SKILL' AND af.functional_self_submitted_at IS NOT NULL))
            ORDER BY af.assessment_type, item_name
        """), {"tenant_id": tenant_id, "employee_id": employee_id, "cycle_id": cycle_id}).mappings().all()
        if not items:
            return None
        return {
            "employee": dict(employee),
            "success_behaviours": [dict(item) for item in items if item["item_type"] == "BEHAVIOUR"],
            "functional_skills": [dict(item) for item in items if item["item_type"] == "SKILL"],
        }

    def export_assessment_gaps_excel(
        self, tenant_id: int, division_id: int | None = None, cycle_id: int | None = None,
        employee_name: str | None = None,
    ) -> tuple[bytes, str]:
        division_label = "All_Entities"
        if division_id is not None:
            div_row = self._session.execute(
                text("SELECT name FROM divisions WHERE tenant_id=:tenant_id AND division_id=:division_id"),
                {"tenant_id": tenant_id, "division_id": division_id},
            ).scalar_one_or_none()
            if div_row:
                division_label = str(div_row).replace(" - ", "_").replace(" ", "_")

        cycles = self._session.execute(text("""
            SELECT cycle_id, name FROM assessment_cycles
            WHERE tenant_id=:tenant_id ORDER BY period_start DESC
        """), {"tenant_id": tenant_id}).mappings().all()

        selected_cycle_id = cycle_id or (cycles[0]["cycle_id"] if cycles else None)
        cycle_name = "All_Cycles"
        if selected_cycle_id is not None:
            for c in cycles:
                if c["cycle_id"] == selected_cycle_id:
                    cycle_name = str(c["name"]).replace(" - ", "_").replace(" ", "_")
                    break

        emp_part = f"_{str(employee_name).strip().replace(' ', '_')}" if employee_name else ""
        filename = f"KDDL_Assessment_{division_label}{emp_part}_{cycle_name}.xlsx"

        status_query = text("""
            SELECT e.employee_id, e.employee_code, e.full_name AS employee_name, d.name AS division_name,
                   COALESCE(m.full_name, 'Not assigned') AS manager_name,
                   COALESCE(f.name, '—') AS function_name,
                   COALESCE(dep.name, '—') AS department_name,
                   COALESCE(r.title, e.designation, '—') AS role_title,
                   COALESCE(gb.band_code, '—') AS grade,
                   CASE WHEN behaviour.form_id IS NULL THEN 'PENDING_WITH_EMPLOYEE'
                        WHEN behaviour.behaviour_self_submitted_at IS NULL THEN 'PENDING_WITH_EMPLOYEE'
                        ELSE 'COMPLETED' END AS behaviour_self_status,
                   CASE WHEN behaviour.form_id IS NULL THEN 'PENDING_WITH_MANAGER'
                        WHEN behaviour.behaviour_manager_submitted_at IS NULL THEN 'PENDING_WITH_MANAGER'
                        ELSE 'COMPLETED' END AS behaviour_manager_status,
                   CASE WHEN functional.form_id IS NULL AND EXISTS (
                            SELECT 1 FROM functional_skills fs
                            JOIN desired_level_matrix dlm ON dlm.tenant_id=fs.tenant_id
                                AND dlm.division_id=e.division_id AND dlm.item_type='SKILL'
                                AND dlm.item_id=fs.skill_id AND dlm.department_id <=> e.department_id
                                AND dlm.grade_band_id=e.grade_band_id
                            WHERE fs.tenant_id=e.tenant_id AND fs.division_id=e.division_id
                                AND fs.function_id=e.function_id AND fs.department_id <=> e.department_id
                        ) THEN 'PENDING_WITH_EMPLOYEE'
                        WHEN functional.form_id IS NULL THEN 'NOT_CONFIGURED'
                        WHEN functional.functional_self_submitted_at IS NULL THEN 'PENDING_WITH_EMPLOYEE'
                        ELSE 'COMPLETED' END AS functional_self_status,
                   CASE WHEN functional.form_id IS NULL AND EXISTS (
                            SELECT 1 FROM functional_skills fs
                            JOIN desired_level_matrix dlm ON dlm.tenant_id=fs.tenant_id
                                AND dlm.division_id=e.division_id AND dlm.item_type='SKILL'
                                AND dlm.item_id=fs.skill_id AND dlm.department_id <=> e.department_id
                                AND dlm.grade_band_id=e.grade_band_id
                            WHERE fs.tenant_id=e.tenant_id AND fs.division_id=e.division_id
                                AND fs.function_id=e.function_id AND fs.department_id <=> e.department_id
                        ) THEN 'PENDING_WITH_MANAGER'
                        WHEN functional.form_id IS NULL THEN 'NOT_CONFIGURED'
                        WHEN functional.functional_manager_submitted_at IS NULL THEN 'PENDING_WITH_MANAGER'
                        ELSE 'COMPLETED' END AS functional_manager_status,
                   COALESCE(g.behaviour_gaps, 0) AS behaviour_gaps,
                   COALESCE(g.functional_gaps, 0) AS functional_gaps
            FROM employees e
            JOIN divisions d ON d.division_id=e.division_id AND d.tenant_id=e.tenant_id
            JOIN entities en ON en.entity_id=d.entity_id AND en.tenant_id=d.tenant_id
            LEFT JOIN employees m ON m.employee_id=e.manager_employee_id AND m.tenant_id=e.tenant_id
            LEFT JOIN roles r ON r.role_id=e.role_id AND r.tenant_id=e.tenant_id AND r.division_id=e.division_id
            LEFT JOIN functions f ON f.function_id=e.function_id
            LEFT JOIN departments dep ON dep.department_id=e.department_id
            LEFT JOIN grade_bands gb ON gb.grade_band_id=e.grade_band_id
            LEFT JOIN assessment_forms behaviour ON behaviour.tenant_id=e.tenant_id AND behaviour.employee_id=e.employee_id
                AND behaviour.cycle_id=:cycle_id AND behaviour.assessment_type='BEHAVIOUR'
            LEFT JOIN assessment_forms functional ON functional.tenant_id=e.tenant_id AND functional.employee_id=e.employee_id
                AND functional.cycle_id=:cycle_id AND functional.assessment_type='SKILL'
            LEFT JOIN (
                SELECT af.employee_id,
                    SUM(CASE WHEN ali.item_type='BEHAVIOUR' AND ali.gap < 0 THEN 1 ELSE 0 END) AS behaviour_gaps,
                    SUM(CASE WHEN ali.item_type='SKILL' AND ali.gap < 0 THEN 1 ELSE 0 END) AS functional_gaps
                FROM assessment_forms af JOIN assessment_line_items ali ON ali.form_id=af.form_id
                WHERE af.tenant_id=:tenant_id AND af.cycle_id=:cycle_id GROUP BY af.employee_id
            ) g ON g.employee_id=e.employee_id
            WHERE e.tenant_id=:tenant_id AND e.status='ACTIVE' AND en.code <> 'CORPORATE'
              AND d.code <> 'TARATEC-LDR'
              AND (:division_id IS NULL OR e.division_id=:division_id)
              AND (:employee_name IS NULL OR LOWER(e.full_name) LIKE :employee_name_like OR LOWER(e.employee_code) LIKE :employee_name_like)
            ORDER BY d.name, m.full_name, e.full_name
        """)

        status_rows = self._session.execute(status_query, {
            "tenant_id": tenant_id,
            "division_id": division_id,
            "cycle_id": selected_cycle_id,
            "employee_name": employee_name,
            "employee_name_like": f"%{employee_name.lower()}%" if employee_name else "%",
        }).mappings().all()

        line_query = text("""
            SELECT
                e.employee_code,
                e.full_name AS employee_name,
                d.name AS division_name,
                COALESCE(f.name, '—') AS function_name,
                COALESCE(dep.name, '—') AS department_name,
                COALESCE(r.title, e.designation, '—') AS role_title,
                COALESCE(gb.band_code, '—') AS grade,
                COALESCE(m.full_name, 'Not assigned') AS manager_name,
                ali.item_type,
                COALESCE(sb.name, fs.name) AS item_name,
                ali.desired_level,
                ali.self_assessment_level,
                ali.manager_assessment_level,
                ali.gap,
                af.status AS form_status
            FROM employees e
            JOIN divisions d ON d.division_id = e.division_id AND d.tenant_id = e.tenant_id
            JOIN entities en ON en.entity_id = d.entity_id AND en.tenant_id = d.tenant_id
            LEFT JOIN functions f ON f.function_id = e.function_id
            LEFT JOIN departments dep ON dep.department_id = e.department_id
            LEFT JOIN roles r ON r.role_id = e.role_id
            LEFT JOIN grade_bands gb ON gb.grade_band_id = e.grade_band_id
            LEFT JOIN employees m ON m.employee_id = e.manager_employee_id
            LEFT JOIN assessment_forms af ON af.employee_id = e.employee_id
                AND af.tenant_id = e.tenant_id
                AND (:cycle_id IS NULL OR af.cycle_id = :cycle_id)
            LEFT JOIN assessment_line_items ali ON ali.form_id = af.form_id
            LEFT JOIN success_behaviours sb ON ali.item_type = 'BEHAVIOUR' AND sb.behaviour_id = ali.item_id AND sb.tenant_id = e.tenant_id
            LEFT JOIN functional_skills fs ON ali.item_type = 'SKILL' AND fs.skill_id = ali.item_id AND fs.tenant_id = e.tenant_id
            WHERE e.tenant_id = :tenant_id AND e.status = 'ACTIVE'
              AND en.code <> 'CORPORATE' AND d.code <> 'TARATEC-LDR'
              AND (:division_id IS NULL OR e.division_id = :division_id)
              AND (:employee_name IS NULL OR LOWER(e.full_name) LIKE :employee_name_like OR LOWER(e.employee_code) LIKE :employee_name_like)
            ORDER BY e.full_name, ali.item_type, item_name
        """)

        line_rows = self._session.execute(line_query, {
            "tenant_id": tenant_id,
            "division_id": division_id,
            "cycle_id": selected_cycle_id,
            "employee_name": employee_name,
            "employee_name_like": f"%{employee_name.lower()}%" if employee_name else "%",
        }).mappings().all()

        wb = openpyxl.Workbook()
        ws_status = wb.active
        ws_status.title = "Assessment Status Summary"
        ws_all = wb.create_sheet("All Assessment Gaps")
        ws_sb = wb.create_sheet("Success Behaviours")
        ws_fs = wb.create_sheet("Functional Skills")

        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        regular_font = Font(name="Calibri", size=10)
        thin_border = Border(
            left=Side(style="thin", color="E2E8F0"),
            right=Side(style="thin", color="E2E8F0"),
            top=Side(style="thin", color="E2E8F0"),
            bottom=Side(style="thin", color="E2E8F0"),
        )
        red_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
        red_font = Font(name="Calibri", size=10, bold=True, color="991B1B")
        green_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
        green_font = Font(name="Calibri", size=10, bold=True, color="166534")
        blue_fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
        blue_font = Font(name="Calibri", size=10, bold=True, color="1E40AF")
        amber_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
        amber_font = Font(name="Calibri", size=10, bold=True, color="92400E")

        # 1. Populate Assessment Status Summary (Exact table from UI)
        status_headers = [
            "Employee Name",
            "Employee Code",
            "Division",
            "Function",
            "Department",
            "Role",
            "Grade",
            "Manager Name",
            "Behaviour Self Status",
            "Behaviour Manager Status",
            "Functional Self Status",
            "Functional Manager Status",
            "Behaviour Gaps",
            "Functional Gaps",
            "Total Gaps",
        ]
        ws_status.views.sheetView[0].showGridLines = True
        ws_status.append(status_headers)
        ws_status.row_dimensions[1].height = 28
        ws_status.freeze_panes = "A2"
        for col_idx in range(1, len(status_headers) + 1):
            cell = ws_status.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border

        def format_status(val: str) -> str:
            return str(val).replace("_", " ").title()

        for s_row in status_rows:
            tot_gaps = int(s_row["behaviour_gaps"]) + int(s_row["functional_gaps"])
            row_data = [
                str(s_row["employee_name"]),
                str(s_row["employee_code"]),
                str(s_row["division_name"]),
                str(s_row["function_name"]),
                str(s_row["department_name"]),
                str(s_row["role_title"]),
                str(s_row["grade"]),
                str(s_row["manager_name"]),
                format_status(s_row["behaviour_self_status"]),
                format_status(s_row["behaviour_manager_status"]),
                format_status(s_row["functional_self_status"]),
                format_status(s_row["functional_manager_status"]),
                int(s_row["behaviour_gaps"]),
                int(s_row["functional_gaps"]),
                tot_gaps,
            ]
            ws_status.append(row_data)
            r_idx = ws_status.max_row
            ws_status.row_dimensions[r_idx].height = 22
            for col_idx in range(1, len(row_data) + 1):
                c_cell = ws_status.cell(row=r_idx, column=col_idx)
                c_cell.font = regular_font
                c_cell.border = thin_border
                if col_idx in (2, 7, 9, 10, 11, 12, 13, 14, 15):
                    c_cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    c_cell.alignment = Alignment(horizontal="left", vertical="center")

                # Status color formatting
                val_str = str(c_cell.value)
                if val_str == "Completed":
                    c_cell.fill = green_fill
                    c_cell.font = green_font
                elif "Pending" in val_str:
                    c_cell.fill = amber_fill
                    c_cell.font = amber_font

                if col_idx in (13, 14, 15) and isinstance(c_cell.value, int) and c_cell.value > 0:
                    c_cell.fill = red_fill
                    c_cell.font = red_font

        # 2. Populate Detailed Gaps and Skills sheets
        detail_headers = [
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

        detail_sheets = [ws_all, ws_sb, ws_fs]
        for ws in detail_sheets:
            ws.views.sheetView[0].showGridLines = True
            ws.append(detail_headers)
            ws.row_dimensions[1].height = 28
            ws.freeze_panes = "A2"
            for col_idx in range(1, len(detail_headers) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = thin_border

        def append_detail_row(ws, r):
            cat_display = "—"
            if r["item_type"] == "BEHAVIOUR":
                cat_display = "Success Behaviour"
            elif r["item_type"] == "SKILL":
                cat_display = "Functional Skill"

            dl = f"L{r['desired_level']}" if r["desired_level"] is not None else "-"
            sal = f"L{r['self_assessment_level']}" if r["self_assessment_level"] is not None else ("Pending" if r["item_type"] else "-")
            mal = f"L{r['manager_assessment_level']}" if r["manager_assessment_level"] is not None else ("Pending" if r["item_type"] else "-")

            gap_val = r["gap"]
            gap_display = "-"
            gap_status = "Pending Assessment" if r["item_type"] else "Not Started"

            if gap_val is not None:
                gap_display = int(gap_val)
                if gap_val < 0:
                    gap_status = f"Negative Gap ({gap_val})"
                elif gap_val == 0:
                    gap_status = "Meets Desired Level (0)"
                else:
                    gap_status = f"Exceeds Desired Level (+{gap_val})"

            row_data = [
                str(r["employee_name"]),
                str(r["employee_code"]),
                str(r["division_name"]),
                str(r["function_name"]),
                str(r["department_name"]),
                str(r["role_title"]),
                str(r["grade"]),
                str(r["manager_name"]),
                cat_display,
                str(r["item_name"] or "No assessment started"),
                dl,
                sal,
                mal,
                gap_display,
                gap_status,
            ]
            ws.append(row_data)
            row_idx = ws.max_row
            ws.row_dimensions[row_idx].height = 22

            for col_idx in range(1, len(row_data) + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.font = regular_font
                cell.border = thin_border

                if col_idx in (2, 7, 9, 11, 12, 13, 14, 15):
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")

                if col_idx in (14, 15) and gap_val is not None:
                    if gap_val < 0:
                        cell.fill = red_fill
                        cell.font = red_font
                    elif gap_val == 0:
                        cell.fill = green_fill
                        cell.font = green_font
                    elif gap_val > 0:
                        cell.fill = blue_fill
                        cell.font = blue_font

        for r in line_rows:
            append_detail_row(ws_all, r)
            if r["item_type"] == "BEHAVIOUR":
                append_detail_row(ws_sb, r)
            elif r["item_type"] == "SKILL":
                append_detail_row(ws_fs, r)

        for ws in [ws_status, ws_all, ws_sb, ws_fs]:
            ws.auto_filter.ref = ws.dimensions
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    val = str(cell.value or "")
                    if len(val) > max_len:
                        max_len = len(val)
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf.getvalue(), filename

