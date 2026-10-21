"""Tenant-scoped SQL read model for the assessment administration console."""

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
