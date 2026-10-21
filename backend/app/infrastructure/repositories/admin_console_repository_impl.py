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
            SELECT division_id, name FROM divisions
            WHERE tenant_id=:tenant_id ORDER BY name
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
            WHERE e.tenant_id=:tenant_id AND e.status='ACTIVE'
              AND (:division_id IS NULL OR e.division_id=:division_id)
              AND (:employee_name IS NULL OR LOWER(e.full_name) LIKE CONCAT('%', LOWER(:employee_name), '%'))
        """), {"tenant_id": tenant_id, "division_id": division_id,
               "employee_name": employee_name}).scalar_one()
        rows = self._session.execute(text("""
            SELECT e.employee_id, e.employee_code, e.full_name, d.name AS division_name,
                   manager.full_name AS manager_name, COALESCE(r.title, e.designation) AS role_title,
                   CASE WHEN behaviour.form_id IS NULL THEN 'NOT_CONFIGURED'
                        WHEN behaviour.behaviour_self_submitted_at IS NULL THEN 'PENDING_WITH_EMPLOYEE'
                        ELSE 'COMPLETED' END AS behaviour_self_status,
                   CASE WHEN behaviour.form_id IS NULL THEN 'NOT_CONFIGURED'
                        WHEN behaviour.behaviour_manager_submitted_at IS NULL THEN 'PENDING_WITH_MANAGER'
                        ELSE 'COMPLETED' END AS behaviour_manager_status,
                   CASE WHEN functional.form_id IS NULL THEN 'NOT_CONFIGURED'
                        WHEN functional.functional_self_submitted_at IS NULL THEN 'PENDING_WITH_EMPLOYEE'
                        ELSE 'COMPLETED' END AS functional_self_status,
                   CASE WHEN functional.form_id IS NULL THEN 'NOT_CONFIGURED'
                        WHEN functional.functional_manager_submitted_at IS NULL THEN 'PENDING_WITH_MANAGER'
                        ELSE 'COMPLETED' END AS functional_manager_status,
                   COALESCE(g.behaviour_gaps, 0) AS behaviour_gaps,
                   COALESCE(g.functional_gaps, 0) AS functional_gaps
            FROM employees e
            JOIN divisions d ON d.division_id=e.division_id AND d.tenant_id=e.tenant_id
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
            WHERE e.tenant_id=:tenant_id AND e.status='ACTIVE'
              AND (:division_id IS NULL OR e.division_id=:division_id)
              AND (:employee_name IS NULL OR LOWER(e.full_name) LIKE CONCAT('%', LOWER(:employee_name), '%'))
            ORDER BY d.name, manager.full_name, e.full_name
            LIMIT :limit OFFSET :offset
        """), {"tenant_id": tenant_id, "division_id": division_id,
                "employee_name": employee_name, "cycle_id": selected_cycle,
                "limit": page_size, "offset": (page - 1) * page_size}).mappings().all() if selected_cycle else []
        results = [dict(row) for row in rows]
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
                "behaviour_self_pending": sum(row["behaviour_self_status"] == "PENDING_WITH_EMPLOYEE" for row in results),
                "behaviour_manager_pending": sum(row["behaviour_manager_status"] == "PENDING_WITH_MANAGER" for row in results),
                "functional_self_pending": sum(row["functional_self_status"] == "PENDING_WITH_EMPLOYEE" for row in results),
                "functional_manager_pending": sum(row["functional_manager_status"] == "PENDING_WITH_MANAGER" for row in results),
                "behaviour_gaps": sum(int(row["behaviour_gaps"]) for row in results),
                "functional_gaps": sum(int(row["functional_gaps"]) for row in results),
            },
        }

    def get_submitted_assessment(self, tenant_id: int, employee_id: int, cycle_id: int) -> dict[str, object] | None:
        employee = self._session.execute(text("""
            SELECT e.employee_id, e.employee_code, e.full_name, d.name AS division_name
            FROM employees e JOIN divisions d ON d.division_id=e.division_id AND d.tenant_id=e.tenant_id
            WHERE e.tenant_id=:tenant_id AND e.employee_id=:employee_id
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
