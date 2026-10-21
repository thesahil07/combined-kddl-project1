"""SQLAlchemy implementation of Skip Manager's tenant-scoped read model."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.interfaces.skip_manager_dashboard_repository import SkipManagerDashboardRepository
from app.domain.exceptions.application_errors import InvalidStateError, ValidationError


class SqlAlchemySkipManagerDashboardRepository(SkipManagerDashboardRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_dashboard(self, tenant_id: int, manager_employee_id: int) -> dict[str, object]:
        manager = self._session.execute(text("""
            SELECT full_name, employee_code
            FROM employees
            WHERE tenant_id=:tenant_id AND employee_id=:manager_employee_id
        """), {"tenant_id": tenant_id, "manager_employee_id": manager_employee_id}).mappings().one_or_none()
        if manager is None:
            raise ValidationError("manager employee profile not found")
        team_rows = self._session.execute(text("""
            SELECT e.employee_id, e.employee_code, e.full_name, e.designation, r.role_id, r.title AS role_title,
                   fn.name AS function_name, dep.name AS department_name, gb.band_code AS grade_band_code,
                   r.description_status,
                   CASE
                       WHEN c.cycle_id IS NULL OR f.form_id IS NULL THEN 'PENDING'
                       WHEN f.self_assessment_date IS NULL THEN 'IN_PROGRESS'
                       ELSE 'COMPLETED'
                   END AS self_assessment_status,
                   CASE
                       WHEN c.cycle_id IS NULL OR f.form_id IS NULL OR f.self_assessment_date IS NULL THEN 'PENDING'
                       WHEN f.manager_assessment_date IS NULL THEN 'IN_PROGRESS'
                       ELSE 'COMPLETED'
                   END AS manager_assessment_status,
                   COALESCE(g.behaviour_gap_items, 0) AS behaviour_gap_items,
                   COALESCE(g.functional_gap_items, 0) AS functional_gap_items,
                   COALESCE(g.has_gap, 0) AS has_gap,
                   CASE
                       WHEN c.cycle_id IS NULL THEN 'NOT_CONFIGURED'
                       -- A form is created when an employee opens an assessment.  Until then,
                       -- Success Behaviours are available to every active employee.
                       WHEN f.form_id IS NULL THEN 'PENDING_WITH_EMPLOYEE'
                       WHEN NOT EXISTS (SELECT 1 FROM assessment_line_items x WHERE x.form_id=f.form_id AND x.item_type='BEHAVIOUR') THEN 'NOT_CONFIGURED'
                       WHEN f.behaviour_self_submitted_at IS NULL THEN 'PENDING_WITH_EMPLOYEE'
                       ELSE 'COMPLETED'
                   END AS behaviour_employee_status,
                   CASE
                       WHEN c.cycle_id IS NULL THEN 'NOT_CONFIGURED'
                       WHEN f.form_id IS NULL THEN 'PENDING_WITH_MANAGER'
                       WHEN NOT EXISTS (SELECT 1 FROM assessment_line_items x WHERE x.form_id=f.form_id AND x.item_type='BEHAVIOUR') THEN 'NOT_CONFIGURED'
                       WHEN f.behaviour_manager_submitted_at IS NULL THEN 'PENDING_WITH_MANAGER'
                       ELSE 'COMPLETED'
                   END AS behaviour_manager_status,
                   CASE
                       WHEN c.cycle_id IS NULL THEN 'NOT_CONFIGURED'
                       WHEN skill_form.form_id IS NULL AND EXISTS (
                           SELECT 1
                           FROM functional_skills fs
                           JOIN desired_level_matrix dlm
                             ON dlm.tenant_id=fs.tenant_id
                            AND dlm.division_id=e.division_id
                            AND dlm.item_type='SKILL'
                            AND dlm.item_id=fs.skill_id
                            AND dlm.department_id <=> e.department_id
                            AND dlm.grade_band_id=e.grade_band_id
                           WHERE fs.tenant_id=e.tenant_id
                             AND fs.division_id=e.division_id
                             AND fs.function_id=e.function_id
                             AND fs.department_id <=> e.department_id
                       ) THEN 'PENDING_WITH_EMPLOYEE'
                       WHEN skill_form.form_id IS NULL OR NOT EXISTS (SELECT 1 FROM assessment_line_items x WHERE x.form_id=skill_form.form_id AND x.item_type='SKILL') THEN 'NOT_CONFIGURED'
                       WHEN skill_form.functional_self_submitted_at IS NULL THEN 'PENDING_WITH_EMPLOYEE'
                       ELSE 'COMPLETED'
                   END AS functional_employee_status,
                   CASE
                       WHEN c.cycle_id IS NULL THEN 'NOT_CONFIGURED'
                       WHEN skill_form.form_id IS NULL AND EXISTS (
                           SELECT 1
                           FROM functional_skills fs
                           JOIN desired_level_matrix dlm
                             ON dlm.tenant_id=fs.tenant_id
                            AND dlm.division_id=e.division_id
                            AND dlm.item_type='SKILL'
                            AND dlm.item_id=fs.skill_id
                            AND dlm.department_id <=> e.department_id
                            AND dlm.grade_band_id=e.grade_band_id
                           WHERE fs.tenant_id=e.tenant_id
                             AND fs.division_id=e.division_id
                             AND fs.function_id=e.function_id
                             AND fs.department_id <=> e.department_id
                       ) THEN 'PENDING_WITH_MANAGER'
                       WHEN skill_form.form_id IS NULL OR NOT EXISTS (SELECT 1 FROM assessment_line_items x WHERE x.form_id=skill_form.form_id AND x.item_type='SKILL') THEN 'NOT_CONFIGURED'
                       WHEN skill_form.functional_manager_submitted_at IS NULL THEN 'PENDING_WITH_MANAGER'
                       ELSE 'COMPLETED'
                   END AS functional_manager_status
            FROM employees e
            LEFT JOIN roles r ON r.role_id = e.role_id AND r.tenant_id = e.tenant_id
            JOIN functions fn ON fn.function_id = e.function_id AND fn.tenant_id = e.tenant_id AND fn.division_id = e.division_id
            LEFT JOIN departments dep ON dep.department_id = e.department_id AND dep.tenant_id = e.tenant_id AND dep.division_id = e.division_id
            JOIN grade_bands gb ON gb.grade_band_id = e.grade_band_id AND gb.tenant_id = e.tenant_id
            LEFT JOIN assessment_cycles c ON c.tenant_id = e.tenant_id
                AND c.status IN ('NOT_STARTED', 'IN_PROGRESS')
            LEFT JOIN assessment_forms f ON f.cycle_id = c.cycle_id AND f.employee_id = e.employee_id
                AND f.assessment_type = 'BEHAVIOUR'
            LEFT JOIN assessment_forms skill_form ON skill_form.cycle_id = c.cycle_id AND skill_form.employee_id = e.employee_id
                AND skill_form.assessment_type = 'SKILL'
            LEFT JOIN (
                SELECT af.employee_id,
                       SUM(CASE WHEN ali.item_type='BEHAVIOUR' AND ali.gap < 0 THEN 1 ELSE 0 END) AS behaviour_gap_items,
                       SUM(CASE WHEN ali.item_type='SKILL' AND ali.gap < 0 THEN 1 ELSE 0 END) AS functional_gap_items,
                       MAX(CASE WHEN ali.gap < 0 THEN 1 ELSE 0 END) AS has_gap
                FROM assessment_forms af
                JOIN assessment_cycles active_cycle ON active_cycle.cycle_id=af.cycle_id
                    AND active_cycle.tenant_id=af.tenant_id AND active_cycle.status='IN_PROGRESS'
                JOIN assessment_line_items ali ON ali.form_id = af.form_id
                WHERE af.tenant_id = :tenant_id AND ali.gap < 0
                GROUP BY af.employee_id
            ) g ON g.employee_id = e.employee_id
            WHERE e.tenant_id = :tenant_id AND e.manager_employee_id = :manager_employee_id
                AND e.status = 'ACTIVE'
            ORDER BY e.full_name
        """), {"tenant_id": tenant_id, "manager_employee_id": manager_employee_id}).mappings().all()
        team = [dict(row) for row in team_rows]
        active_cycle = self._session.execute(text("""
            SELECT name, period_start, period_end
            FROM assessment_cycles
            WHERE tenant_id=:tenant_id AND status IN ('NOT_STARTED', 'IN_PROGRESS')
            ORDER BY CASE status WHEN 'IN_PROGRESS' THEN 0 ELSE 1 END, period_start DESC
            LIMIT 1
        """), {"tenant_id": tenant_id}).mappings().one_or_none()
        assignment_rows = self._session.execute(text("""
            SELECT r.role_id, r.title AS role_title, r.description_status,
                   fn.name AS function_name, NULL AS department_name,
                   NULL AS grade_band_code, 0 AS employee_id,
                   'Mapped role' AS full_name, r.title AS designation
            FROM role_definition_assignments a
            JOIN roles r ON r.role_id = a.role_id AND r.tenant_id = a.tenant_id
            JOIN functions fn ON fn.function_id = r.function_id AND fn.tenant_id = r.tenant_id AND fn.division_id = r.division_id
            WHERE a.tenant_id = :tenant_id AND a.manager_employee_id = :manager_employee_id
            ORDER BY r.title
        """), {"tenant_id": tenant_id, "manager_employee_id": manager_employee_id}).mappings().all()
        assigned_roles = [dict(row) for row in assignment_rows]
        return {
            "manager": dict(manager),
            "active_cycle": dict(active_cycle) if active_cycle else None,
            "team": team,
            "assigned_roles": assigned_roles,
            "team_size": len(team),
            "pending_self_assessments": sum(
                row["behaviour_employee_status"] == "PENDING_WITH_EMPLOYEE"
                or row["functional_employee_status"] == "PENDING_WITH_EMPLOYEE" for row in team
            ),
            "pending_manager_assessments": sum(
                row["behaviour_manager_status"] == "PENDING_WITH_MANAGER"
                or row["functional_manager_status"] == "PENDING_WITH_MANAGER" for row in team
            ),
            "pending_employee_sections": sum(
                (row["behaviour_employee_status"] == "PENDING_WITH_EMPLOYEE")
                + (row["functional_employee_status"] == "PENDING_WITH_EMPLOYEE") for row in team
            ),
            "pending_manager_sections": sum(
                (row["behaviour_manager_status"] == "PENDING_WITH_MANAGER")
                + (row["functional_manager_status"] == "PENDING_WITH_MANAGER") for row in team
            ),
            "employees_with_gaps": sum(bool(row["has_gap"]) for row in team),
            "behaviour_gap_items": sum(int(row["behaviour_gap_items"]) for row in team),
            "functional_gap_items": sum(int(row["functional_gap_items"]) for row in team),
            "gap_items": sum(int(row["behaviour_gap_items"]) + int(row["functional_gap_items"]) for row in team),
            "role_definition_status": {
                "not_started": sum(row["description_status"] == "NOT_STARTED" for row in assigned_roles),
                "draft": sum(row["description_status"] == "DRAFT" for row in assigned_roles),
                "submitted": sum(row["description_status"] == "SUBMITTED" for row in assigned_roles),
            },
        }

    def is_team_role(self, tenant_id: int, manager_employee_id: int, role_id: int) -> bool:
        return self._session.execute(text("""
            SELECT EXISTS(
                SELECT 1 FROM role_definition_assignments
                WHERE tenant_id = :tenant_id AND manager_employee_id = :manager_employee_id
                    AND role_id = :role_id
            )
        """), {"tenant_id": tenant_id, "manager_employee_id": manager_employee_id, "role_id": role_id}).scalar_one() == 1

    def is_team_member(self, tenant_id: int, manager_employee_id: int, employee_id: int) -> bool:
        return self._session.execute(text("""
            SELECT EXISTS(SELECT 1 FROM employees WHERE tenant_id=:tenant_id
                AND manager_employee_id=:manager_employee_id AND employee_id=:employee_id AND status='ACTIVE')
        """), {"tenant_id": tenant_id, "manager_employee_id": manager_employee_id,
                 "employee_id": employee_id}).scalar_one() == 1

    def get_team_member_role_definition(
        self, tenant_id: int, employee_id: int
    ) -> dict[str, object] | None:
        record = self._session.execute(text("""
            SELECT e.employee_id, e.employee_code, e.full_name, r.title AS role_title,
                   rd.role_definition, rd.key_responsibilities, rd.kpis,
                   rd.knowledge_required, rd.skills_required, rd.attitudes_behaviours
            FROM employees e
            JOIN roles r ON r.role_id=e.role_id AND r.tenant_id=e.tenant_id
            LEFT JOIN role_descriptions rd ON rd.role_id=r.role_id
            WHERE e.tenant_id=:tenant_id AND e.employee_id=:employee_id
            ORDER BY rd.version DESC
            LIMIT 1
        """), {"tenant_id": tenant_id, "employee_id": employee_id}).mappings().one_or_none()
        return dict(record) if record is not None else None

    def get_employee_assessment(self, tenant_id: int, employee_id: int) -> dict[str, object] | None:
        records = self._session.execute(text("""
            SELECT ac.cycle_id, ac.name AS cycle_name, af.form_id, af.status AS form_status,
                   af.behaviour_manager_submitted_at, af.functional_manager_submitted_at,
                   ali.item_type, ali.item_id, ali.desired_level, ali.self_assessment_level,
                   ali.manager_assessment_level,
                   CASE WHEN ali.item_type='BEHAVIOUR' THEN sb.code ELSE fs.code END AS code,
                   CASE WHEN ali.item_type='BEHAVIOUR' THEN sb.name ELSE fs.name END AS name,
                   CASE WHEN ali.item_type='BEHAVIOUR' THEN sb.definition ELSE fs.definition END AS definition
            FROM assessment_cycles ac
            JOIN assessment_forms af ON af.tenant_id=ac.tenant_id AND af.cycle_id=ac.cycle_id
            JOIN assessment_line_items ali ON ali.form_id=af.form_id
            LEFT JOIN success_behaviours sb ON ali.item_type='BEHAVIOUR' AND sb.tenant_id=af.tenant_id AND sb.behaviour_id=ali.item_id
            LEFT JOIN functional_skills fs ON ali.item_type='SKILL' AND fs.tenant_id=af.tenant_id AND fs.skill_id=ali.item_id
            WHERE af.tenant_id=:tenant_id AND af.employee_id=:employee_id AND ac.status='IN_PROGRESS'
            ORDER BY ac.period_start DESC, ali.item_type, code
        """), {"tenant_id": tenant_id, "employee_id": employee_id}).mappings().all()
        if not records:
            return None
        first = records[0]
        return {"cycle": {"cycle_id": first["cycle_id"], "name": first["cycle_name"]},
                "form_status": first["form_status"],
                "behaviour_is_submitted": any(row["item_type"] == "BEHAVIOUR" and row["behaviour_manager_submitted_at"] is not None for row in records),
                "functional_is_submitted": any(row["item_type"] == "SKILL" and row["functional_manager_submitted_at"] is not None for row in records),
                "success_behaviours": [dict(row) for row in records if row["item_type"] == "BEHAVIOUR"],
                "functional_skills": [dict(row) for row in records if row["item_type"] == "SKILL"]}

    def save_manager_assessment(self, tenant_id: int, employee_id: int, actor_user_id: int,
                                item_type: str, items: list[dict[str, int]], submit: bool) -> dict[str, object]:
        assessment = self.get_employee_assessment(tenant_id, employee_id)
        if assessment is None:
            raise InvalidStateError("no active assessment is available for this employee")
        section = "success_behaviours" if item_type == "BEHAVIOUR" else "functional_skills"
        current_items = assessment[section]
        submitted_key = "behaviour_is_submitted" if item_type == "BEHAVIOUR" else "functional_is_submitted"
        if assessment[submitted_key]:
            raise InvalidStateError("this assessment section has already been submitted and is read-only")
        allowed_ids = {int(item["item_id"]) for item in current_items}
        submitted_ids = {item["item_id"] for item in items}
        if not allowed_ids or not submitted_ids.issubset(allowed_ids):
            raise ValidationError("assessment contains an invalid item")
        if submit and submitted_ids != allowed_ids:
            raise ValidationError("rate every assessment item before submitting")
        form_id = int(current_items[0]["form_id"])
        self._session.execute(text("""
            UPDATE assessment_line_items ali JOIN assessment_forms af ON af.form_id=ali.form_id
            SET ali.manager_assessment_level=:level, ali.data_quality_flag='OK'
            WHERE ali.form_id=:form_id AND ali.item_type=:item_type AND ali.item_id=:item_id
                AND af.tenant_id=:tenant_id AND af.employee_id=:employee_id
        """), [{"level": item["self_assessment_level"], "item_id": item["item_id"], "form_id": form_id,
                  "item_type": item_type, "tenant_id": tenant_id, "employee_id": employee_id} for item in items])
        if submit:
            remaining = self._session.execute(text("""
                SELECT COUNT(*) FROM assessment_line_items WHERE form_id=:form_id
                    AND item_type=:item_type AND manager_assessment_level IS NULL
            """), {"form_id": form_id, "item_type": item_type}).scalar_one()
            if remaining:
                raise ValidationError("rate every assessment item before submitting")
            submitted_column = "behaviour_manager_submitted_at" if item_type == "BEHAVIOUR" else "functional_manager_submitted_at"
            self._session.execute(text(f"""
                UPDATE assessment_forms SET {submitted_column}=UTC_TIMESTAMP(), status='MANAGER_SUBMITTED', manager_assessment_date=CURDATE()
                WHERE form_id=:form_id AND tenant_id=:tenant_id AND employee_id=:employee_id
            """), {"form_id": form_id, "tenant_id": tenant_id, "employee_id": employee_id})
        self._session.execute(text("""
            INSERT INTO audit_log (tenant_id, actor_user_id, action, entity_type, entity_id, after_json)
            VALUES (:tenant_id, :actor_user_id, :action, 'assessment_forms', :form_id, :after_json)
        """), {"tenant_id": tenant_id, "actor_user_id": actor_user_id,
                 "action": 'MANAGER_ASSESSMENT_SUBMITTED' if submit else 'MANAGER_ASSESSMENT_SAVED',
                 "form_id": form_id, "after_json": '{\"item_type\": \"' + item_type + '\"}'})
        return self.get_employee_assessment(tenant_id, employee_id) or {}

    def get_employee_previous_assessments(self, tenant_id: int, employee_id: int) -> list[dict[str, object]]:
        records = self._session.execute(text("""
            SELECT ac.cycle_id, ac.name AS cycle_name, ac.period_start, ac.period_end, af.status,
                   ali.item_type, ali.item_id, ali.desired_level, ali.self_assessment_level,
                   ali.manager_assessment_level, ali.gap,
                   CASE WHEN ali.item_type='BEHAVIOUR' THEN sb.name ELSE fs.name END AS item_name
            FROM assessment_forms af JOIN assessment_cycles ac ON ac.cycle_id=af.cycle_id AND ac.tenant_id=af.tenant_id
            JOIN assessment_line_items ali ON ali.form_id=af.form_id
            LEFT JOIN success_behaviours sb ON ali.item_type='BEHAVIOUR' AND sb.tenant_id=af.tenant_id AND sb.behaviour_id=ali.item_id
            LEFT JOIN functional_skills fs ON ali.item_type='SKILL' AND fs.tenant_id=af.tenant_id AND fs.skill_id=ali.item_id
            WHERE af.tenant_id=:tenant_id AND af.employee_id=:employee_id AND ac.status='CLOSED'
            ORDER BY ac.period_end DESC, ali.item_type, item_name
        """), {"tenant_id": tenant_id, "employee_id": employee_id}).mappings().all()
        cycles: dict[int, dict[str, object]] = {}
        for row in records:
            cycle = cycles.setdefault(int(row["cycle_id"]), {"cycle_id": row["cycle_id"], "name": row["cycle_name"],
                "period_start": row["period_start"], "period_end": row["period_end"], "form_status": row["status"],
                "success_behaviours": [], "functional_skills": []})
            key = "success_behaviours" if row["item_type"] == "BEHAVIOUR" else "functional_skills"
            cycle[key].append({name: row[name] for name in ("item_id", "item_name", "desired_level", "self_assessment_level", "manager_assessment_level", "gap")})
        return list(cycles.values())

    def get_submitted_assessment(
        self, tenant_id: int, manager_employee_id: int, employee_id: int
    ) -> dict[str, object] | None:
        """Return the current-cycle submitted report for one direct report only."""
        employee = self._session.execute(text("""
            SELECT e.employee_id, e.employee_code, e.full_name, d.name AS division_name
            FROM employees e
            JOIN divisions d ON d.division_id=e.division_id AND d.tenant_id=e.tenant_id
            WHERE e.tenant_id=:tenant_id AND e.employee_id=:employee_id
              AND e.manager_employee_id=:manager_employee_id AND e.status='ACTIVE'
        """), {"tenant_id": tenant_id, "employee_id": employee_id,
                "manager_employee_id": manager_employee_id}).mappings().one_or_none()
        if employee is None:
            return None

        items = self._session.execute(text("""
            SELECT ali.item_type, ali.item_id, ali.desired_level,
                   ali.self_assessment_level, ali.manager_assessment_level, ali.gap,
                   COALESCE(sb.name, fs.name) AS item_name
            FROM assessment_cycles ac
            JOIN assessment_forms af ON af.cycle_id=ac.cycle_id AND af.tenant_id=ac.tenant_id
            JOIN assessment_line_items ali ON ali.form_id=af.form_id
            LEFT JOIN success_behaviours sb ON ali.item_type='BEHAVIOUR'
                AND sb.behaviour_id=ali.item_id AND sb.tenant_id=af.tenant_id
            LEFT JOIN functional_skills fs ON ali.item_type='SKILL'
                AND fs.skill_id=ali.item_id AND fs.tenant_id=af.tenant_id
            WHERE af.tenant_id=:tenant_id AND af.employee_id=:employee_id
              AND ac.status IN ('NOT_STARTED', 'IN_PROGRESS')
              AND ac.cycle_id=(
                  SELECT cycle_id FROM assessment_cycles
                  WHERE tenant_id=:tenant_id AND status IN ('NOT_STARTED', 'IN_PROGRESS')
                  ORDER BY CASE status WHEN 'IN_PROGRESS' THEN 0 ELSE 1 END, period_start DESC
                  LIMIT 1
              )
              AND ((af.assessment_type='BEHAVIOUR' AND af.behaviour_self_submitted_at IS NOT NULL)
                OR (af.assessment_type='SKILL' AND af.functional_self_submitted_at IS NOT NULL))
            ORDER BY ac.period_start DESC, ali.item_type, item_name
        """), {"tenant_id": tenant_id, "employee_id": employee_id}).mappings().all()
        if not items:
            return None
        return {
            "employee": dict(employee),
            "success_behaviours": [dict(item) for item in items if item["item_type"] == "BEHAVIOUR"],
            "functional_skills": [dict(item) for item in items if item["item_type"] == "SKILL"],
        }

    def get_gap_matrices(self, tenant_id: int, manager_employee_id: int) -> dict[str, object]:
        """Return separate, read-only matrices for behaviour and functional-skill assessments."""
        records = self._session.execute(text("""
            SELECT e.employee_id, e.employee_code, e.full_name, r.title AS role_title,
                   gb.band_code AS grade_band_code, e.designation,
                   ali.item_type, ali.item_id, ali.desired_level,
                   ali.self_assessment_level, ali.manager_assessment_level, ali.gap,
                   CASE WHEN ali.item_type = 'BEHAVIOUR' THEN sb.name ELSE fs.name END AS item_name
            FROM employees e
            JOIN assessment_forms af ON af.employee_id = e.employee_id AND af.tenant_id = e.tenant_id
            JOIN assessment_cycles ac ON ac.cycle_id = af.cycle_id AND ac.tenant_id = af.tenant_id
                AND ac.status IN ('NOT_STARTED', 'IN_PROGRESS')
            JOIN assessment_line_items ali ON ali.form_id = af.form_id
            LEFT JOIN success_behaviours sb ON ali.item_type = 'BEHAVIOUR'
                AND sb.behaviour_id = ali.item_id AND sb.tenant_id = e.tenant_id
            LEFT JOIN functional_skills fs ON ali.item_type = 'SKILL'
                AND fs.skill_id = ali.item_id AND fs.tenant_id = e.tenant_id
            LEFT JOIN roles r ON r.role_id = e.role_id AND r.tenant_id = e.tenant_id
            JOIN grade_bands gb ON gb.grade_band_id = e.grade_band_id AND gb.tenant_id = e.tenant_id
            WHERE e.tenant_id = :tenant_id AND e.manager_employee_id = :manager_employee_id
                AND e.status = 'ACTIVE'
            ORDER BY ali.item_type, item_name, e.full_name
        """), {"tenant_id": tenant_id, "manager_employee_id": manager_employee_id}).mappings().all()
        # The Gaps page is a team view, not merely a view of employees who
        # already have an assessment form.  Keep every active direct report in
        # the result and leave their values blank until an assessment starts.
        team_members = self._session.execute(text("""
            SELECT e.employee_id, e.employee_code, e.full_name, r.title AS role_title,
                   gb.band_code AS grade_band_code, e.designation
            FROM employees e
            LEFT JOIN roles r ON r.role_id=e.role_id AND r.tenant_id=e.tenant_id
            JOIN grade_bands gb ON gb.grade_band_id=e.grade_band_id AND gb.tenant_id=e.tenant_id
            WHERE e.tenant_id=:tenant_id AND e.manager_employee_id=:manager_employee_id
              AND e.status='ACTIVE'
            ORDER BY e.full_name
        """), {"tenant_id": tenant_id, "manager_employee_id": manager_employee_id}).mappings().all()

        matrices: dict[str, dict[str, object]] = {
            "success_behaviours": {"items": [], "rows": []},
            "functional_skills": {"items": [], "rows": []},
        }
        by_type: dict[str, dict[int, dict[str, object]]] = {"BEHAVIOUR": {}, "SKILL": {}}
        item_names: dict[str, dict[int, str]] = {"BEHAVIOUR": {}, "SKILL": {}}
        # Forms are created only once someone opens an assessment.  Populate
        # the Gaps headers from configured master data as well, so a manager
        # can still see their complete team before that happens.
        behaviour_items = self._session.execute(text("""
            SELECT behaviour_id, name
            FROM success_behaviours
            WHERE tenant_id=:tenant_id
            ORDER BY name
        """), {"tenant_id": tenant_id}).mappings().all()
        configured_skills = self._session.execute(text("""
            SELECT DISTINCT fs.skill_id, fs.name
            FROM employees e
            JOIN functional_skills fs ON fs.tenant_id=e.tenant_id
                AND fs.division_id=e.division_id
                AND fs.function_id=e.function_id
                AND fs.department_id <=> e.department_id
            JOIN desired_level_matrix dlm ON dlm.tenant_id=fs.tenant_id
                AND dlm.division_id=e.division_id
                AND dlm.item_type='SKILL'
                AND dlm.item_id=fs.skill_id
                AND dlm.department_id <=> e.department_id
                AND dlm.grade_band_id=e.grade_band_id
            WHERE e.tenant_id=:tenant_id
              AND e.manager_employee_id=:manager_employee_id
              AND e.status='ACTIVE'
            ORDER BY fs.name
        """), {"tenant_id": tenant_id,
                "manager_employee_id": manager_employee_id}).mappings().all()
        configured_skill_assignments = self._session.execute(text("""
            SELECT e.employee_id, fs.skill_id, dlm.desired_level
            FROM employees e
            JOIN functional_skills fs ON fs.tenant_id=e.tenant_id
                AND fs.division_id=e.division_id
                AND fs.function_id=e.function_id
                AND fs.department_id <=> e.department_id
            JOIN desired_level_matrix dlm ON dlm.tenant_id=fs.tenant_id
                AND dlm.division_id=e.division_id
                AND dlm.item_type='SKILL'
                AND dlm.item_id=fs.skill_id
                AND dlm.department_id <=> e.department_id
                AND dlm.grade_band_id=e.grade_band_id
            WHERE e.tenant_id=:tenant_id
              AND e.manager_employee_id=:manager_employee_id
              AND e.status='ACTIVE'
        """), {"tenant_id": tenant_id,
                "manager_employee_id": manager_employee_id}).mappings().all()
        configured_behaviour_assignments = self._session.execute(text("""
            SELECT e.employee_id, sb.behaviour_id,
                   COALESCE(role_matrix.desired_level, band_matrix.desired_level,
                       CASE gb.band_group
                           WHEN 'WORKMEN' THEN 1
                           WHEN 'SUB_STAFF' THEN 1
                           WHEN 'EXECUTIVE' THEN CASE WHEN gb.band_code='E1' THEN 1 ELSE 2 END
                           WHEN 'MANAGERIAL' THEN CASE WHEN gb.band_code IN ('M1','M2') THEN 3 ELSE 4 END
                           ELSE 4
                       END
                   ) AS desired_level
            FROM employees e
            JOIN grade_bands gb ON gb.grade_band_id=e.grade_band_id AND gb.tenant_id=e.tenant_id
            JOIN success_behaviours sb ON sb.tenant_id=e.tenant_id
            LEFT JOIN desired_level_matrix role_matrix ON role_matrix.tenant_id=sb.tenant_id
                AND role_matrix.division_id=e.division_id
                AND role_matrix.item_type='BEHAVIOUR'
                AND role_matrix.item_id=sb.behaviour_id
                AND role_matrix.grade_band_id=e.grade_band_id
                AND role_matrix.role_id=e.role_id
            LEFT JOIN desired_level_matrix band_matrix ON band_matrix.tenant_id=sb.tenant_id
                AND band_matrix.division_id=e.division_id
                AND band_matrix.item_type='BEHAVIOUR'
                AND band_matrix.item_id=sb.behaviour_id
                AND band_matrix.grade_band_id=e.grade_band_id
                AND band_matrix.role_id IS NULL
            WHERE e.tenant_id=:tenant_id
              AND e.manager_employee_id=:manager_employee_id
              AND e.status='ACTIVE'
        """), {"tenant_id": tenant_id,
                "manager_employee_id": manager_employee_id}).mappings().all()
        item_names["BEHAVIOUR"].update({
            int(item["behaviour_id"]): str(item["name"]) for item in behaviour_items
        })
        item_names["SKILL"].update({
            int(item["skill_id"]): str(item["name"]) for item in configured_skills
        })
        for record in records:
            item_type = str(record["item_type"])
            item_id = int(record["item_id"])
            item_names[item_type][item_id] = str(record["item_name"])
            employee_id = int(record["employee_id"])
            row = by_type[item_type].setdefault(employee_id, {
                "employee_id": employee_id,
                "employee_code": record["employee_code"],
                "full_name": record["full_name"],
                "role_title": record["role_title"],
                "grade_band_code": record["grade_band_code"],
                "designation": record["designation"],
                "values": {},
            })
            row["values"][str(item_id)] = {
                "desired_level": record["desired_level"],
                "self_assessment_level": record["self_assessment_level"],
                "manager_assessment_level": record["manager_assessment_level"],
                "gap": record["gap"],
            }
        for item_type in ("BEHAVIOUR", "SKILL"):
            for member in team_members:
                employee_id = int(member["employee_id"])
                by_type[item_type].setdefault(employee_id, {
                    "employee_id": employee_id,
                    "employee_code": member["employee_code"],
                    "full_name": member["full_name"],
                    "role_title": member["role_title"],
                    "grade_band_code": member["grade_band_code"],
                    "designation": member["designation"],
                    "values": {},
                })
        for assignment in configured_skill_assignments:
            row = by_type["SKILL"][int(assignment["employee_id"])]
            row["values"].setdefault(str(assignment["skill_id"]), {
                "desired_level": assignment["desired_level"],
                "self_assessment_level": None,
                "manager_assessment_level": None,
                "gap": None,
            })
        for assignment in configured_behaviour_assignments:
            row = by_type["BEHAVIOUR"][int(assignment["employee_id"])]
            row["values"].setdefault(str(assignment["behaviour_id"]), {
                "desired_level": assignment["desired_level"],
                "self_assessment_level": None,
                "manager_assessment_level": None,
                "gap": None,
            })
        for item_type, response_key in (("BEHAVIOUR", "success_behaviours"), ("SKILL", "functional_skills")):
            matrices[response_key]["items"] = [
                {"item_id": item_id, "name": name}
                for item_id, name in sorted(item_names[item_type].items(), key=lambda item: item[1])
            ]
            matrices[response_key]["rows"] = sorted(
                by_type[item_type].values(), key=lambda row: str(row["full_name"])
            )
        return matrices
