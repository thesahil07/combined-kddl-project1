"""SQL read/write model for an employee's own workspace."""

from datetime import date
import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.exceptions.application_errors import InvalidStateError, ResourceNotFoundError, ValidationError
from app.domain.interfaces.employee_workspace_repository import EmployeeWorkspaceRepository


class SqlAlchemyEmployeeWorkspaceRepository(EmployeeWorkspaceRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_dashboard(self, tenant_id: int, employee_id: int) -> dict[str, object]:
        record = self._session.execute(text("""
            SELECT e.full_name, e.employee_code, ac.cycle_id, ac.name, ac.period_start, ac.period_end,
                   behaviour_form.form_id AS behaviour_form_id, behaviour_form.status AS behaviour_form_status,
                   behaviour_form.behaviour_self_submitted_at,
                   skill_form.form_id AS skill_form_id, skill_form.status AS skill_form_status,
                   skill_form.functional_self_submitted_at
            FROM employees e
            LEFT JOIN assessment_cycles ac ON ac.tenant_id = e.tenant_id
                AND ac.status = 'IN_PROGRESS'
            LEFT JOIN assessment_forms behaviour_form ON behaviour_form.tenant_id = e.tenant_id
                AND behaviour_form.cycle_id = ac.cycle_id AND behaviour_form.employee_id = e.employee_id
                AND behaviour_form.assessment_type = 'BEHAVIOUR'
            LEFT JOIN assessment_forms skill_form ON skill_form.tenant_id = e.tenant_id
                AND skill_form.cycle_id = ac.cycle_id AND skill_form.employee_id = e.employee_id
                AND skill_form.assessment_type = 'SKILL'
            WHERE e.tenant_id = :tenant_id AND e.employee_id = :employee_id
            ORDER BY ac.period_start DESC
            LIMIT 1
        """), {"tenant_id": tenant_id, "employee_id": employee_id}).mappings().one_or_none()
        if record is None:
            raise ResourceNotFoundError("employee profile not found")
        if record["cycle_id"] is None:
            return {"employee": {"full_name": record["full_name"], "employee_code": record["employee_code"]}, "active_cycle": None, "success_behaviours_status": "PENDING", "functional_skills_status": "PENDING"}
        return {
            "employee": {"full_name": record["full_name"], "employee_code": record["employee_code"]},
            "active_cycle": {
                "cycle_id": record["cycle_id"], "name": record["name"],
                "period_start": record["period_start"], "period_end": record["period_end"],
            },
            "form_status": record["behaviour_form_status"] or record["skill_form_status"] or "NOT_STARTED",
            "success_behaviours_status": "COMPLETE" if record["behaviour_self_submitted_at"] else "PENDING",
            "functional_skills_status": "COMPLETE" if record["functional_self_submitted_at"] else "PENDING",
        }

    def get_role(self, tenant_id: int, employee_id: int) -> dict[str, object] | None:
        record = self._session.execute(text("""
            SELECT r.role_id, r.title, r.description_status, rd.role_definition,
                   rd.key_responsibilities, rd.kpis, rd.knowledge_required,
                   rd.skills_required, rd.attitudes_behaviours
            FROM employees e
            JOIN roles r ON r.role_id = e.role_id AND r.tenant_id = e.tenant_id
            LEFT JOIN role_descriptions rd ON rd.role_id = r.role_id
                AND rd.version = (SELECT MAX(current_rd.version)
                                  FROM role_descriptions current_rd
                                  WHERE current_rd.role_id = r.role_id)
            WHERE e.tenant_id = :tenant_id AND e.employee_id = :employee_id
        """), {"tenant_id": tenant_id, "employee_id": employee_id}).mappings().one_or_none()
        return dict(record) if record else None

    def start_assessment(
        self, tenant_id: int, employee_id: int, actor_user_id: int, item_type: str
    ) -> dict[str, object]:
        cycle = self._active_cycle(tenant_id)
        employee = self._session.execute(text("""
            SELECT role_id, manager_employee_id, division_id, function_id, department_id, grade_band_id
            FROM employees
            WHERE tenant_id = :tenant_id AND employee_id = :employee_id AND status = 'ACTIVE'
        """), {"tenant_id": tenant_id, "employee_id": employee_id}).mappings().one_or_none()
        if employee is None or employee["manager_employee_id"] is None:
            raise InvalidStateError("an active employee and reporting manager are required before starting an assessment")
        self._session.execute(text("""
            INSERT INTO assessment_forms (tenant_id, cycle_id, assessment_type, employee_id, role_id, manager_employee_id, status)
            VALUES (:tenant_id, :cycle_id, :item_type, :employee_id, :role_id, :manager_employee_id, 'NOT_STARTED')
            ON DUPLICATE KEY UPDATE form_id = LAST_INSERT_ID(form_id)
        """), {"tenant_id": tenant_id, "cycle_id": cycle["cycle_id"], "employee_id": employee_id,
                 "role_id": employee["role_id"], "manager_employee_id": employee["manager_employee_id"], "item_type": item_type})
        form_id = self._form_id(tenant_id, cycle["cycle_id"], employee_id, item_type)
        if item_type == "BEHAVIOUR":
            items_query = """
                SELECT sb.behaviour_id AS item_id,
                       COALESCE(role_matrix.desired_level, band_matrix.desired_level,
                         CASE gb.band_group WHEN 'WORKMEN' THEN 1 WHEN 'SUB_STAFF' THEN 1
                         WHEN 'EXECUTIVE' THEN CASE WHEN gb.band_code = 'E1' THEN 1 ELSE 2 END
                         WHEN 'MANAGERIAL' THEN CASE WHEN gb.band_code IN ('M1', 'M2') THEN 3 ELSE 4 END
                         ELSE 4 END) AS desired_level
                FROM success_behaviours sb
                JOIN grade_bands gb ON gb.grade_band_id = :grade_band_id AND gb.tenant_id = sb.tenant_id
                LEFT JOIN desired_level_matrix role_matrix ON role_matrix.tenant_id = sb.tenant_id
                    AND role_matrix.item_type = 'BEHAVIOUR' AND role_matrix.item_id = sb.behaviour_id
                    AND role_matrix.grade_band_id = :grade_band_id AND role_matrix.role_id = :role_id AND role_matrix.division_id = :division_id
                LEFT JOIN desired_level_matrix band_matrix ON band_matrix.tenant_id = sb.tenant_id
                    AND band_matrix.item_type = 'BEHAVIOUR' AND band_matrix.item_id = sb.behaviour_id
                    AND band_matrix.grade_band_id = :grade_band_id AND band_matrix.role_id IS NULL AND band_matrix.division_id = :division_id
                WHERE sb.tenant_id = :tenant_id
            """
        else:
            # Functional assessments are deliberately not role-driven.  The
            # employee's division, function and department determine the skill
            # set; their grade band determines each skill's desired level.
            items_query = """
                SELECT fs.skill_id AS item_id, skill_matrix.desired_level
                FROM functional_skills fs
                JOIN desired_level_matrix skill_matrix ON skill_matrix.tenant_id = fs.tenant_id
                    AND skill_matrix.division_id = :division_id
                    AND skill_matrix.item_type = 'SKILL'
                    AND skill_matrix.item_id = fs.skill_id
                    AND skill_matrix.department_id <=> :department_id
                    AND skill_matrix.grade_band_id = :grade_band_id
                WHERE fs.tenant_id = :tenant_id
                    AND fs.division_id = :division_id
                    AND fs.function_id = :function_id
                    AND fs.department_id <=> :department_id
            """
        item_rows = self._session.execute(text(items_query), {
            "tenant_id": tenant_id, "role_id": employee["role_id"], "function_id": employee["function_id"],
            "grade_band_id": employee["grade_band_id"], "department_id": employee["department_id"], "division_id": employee["division_id"],
        }).mappings().all()
        if not item_rows:
            raise InvalidStateError("no active assessment items are configured for this cycle")
        self._session.execute(text("""
            INSERT INTO assessment_line_items (form_id, item_type, item_id, desired_level)
            VALUES (:form_id, :item_type, :item_id, :desired_level)
            ON DUPLICATE KEY UPDATE desired_level = desired_level
        """), [{"form_id": form_id, "item_type": item_type, "item_id": row["item_id"],
                  "desired_level": row["desired_level"]} for row in item_rows])
        self._audit(tenant_id, actor_user_id, "EMPLOYEE_ASSESSMENT_STARTED", "assessment_forms", form_id, {"item_type": item_type})
        assessment = self.get_current_assessment(tenant_id, employee_id, item_type)
        if assessment is None:
            raise ResourceNotFoundError("assessment form was not created")
        return assessment

    def get_current_assessment(
        self, tenant_id: int, employee_id: int, item_type: str
    ) -> dict[str, object] | None:
        cycle = self._active_cycle(tenant_id, required=False)
        if cycle is None:
            return None
        rows = self._items_for_cycle(tenant_id, employee_id, int(cycle["cycle_id"]), item_type)
        if not rows:
            return None
        return {"cycle": dict(cycle), "form_status": rows[0]["form_status"],
                "is_submitted": rows[0]["section_submitted_at"] is not None,
                "items": [dict(row) for row in rows]}

    def save_assessment(
        self, tenant_id: int, employee_id: int, actor_user_id: int, item_type: str,
        items: list[dict[str, int]], submit: bool,
    ) -> dict[str, object]:
        cycle = self._active_cycle(tenant_id)
        form_id = self._form_id(tenant_id, int(cycle["cycle_id"]), employee_id, item_type)
        existing = self._items_for_cycle(tenant_id, employee_id, int(cycle["cycle_id"]), item_type)
        if existing and existing[0]["section_submitted_at"] is not None:
            raise InvalidStateError("this assessment section has already been submitted and is read-only")
        allowed_item_ids = {int(row["item_id"]) for row in existing}
        requested_item_ids = {item["item_id"] for item in items}
        if not allowed_item_ids or not requested_item_ids.issubset(allowed_item_ids):
            raise ValidationError("assessment contains an invalid item")
        if submit and requested_item_ids != allowed_item_ids:
            raise ValidationError("rate every assessment item before submitting")
        self._session.execute(text("""
            UPDATE assessment_line_items ali
            JOIN assessment_forms af ON af.form_id = ali.form_id
            SET ali.self_assessment_level = :level, ali.data_quality_flag = 'OK'
            WHERE ali.form_id = :form_id AND ali.item_type = :item_type AND ali.item_id = :item_id
                AND af.tenant_id = :tenant_id AND af.employee_id = :employee_id
        """), [{"level": item["self_assessment_level"], "item_id": item["item_id"], "form_id": form_id,
                  "item_type": item_type, "tenant_id": tenant_id, "employee_id": employee_id} for item in items])
        if submit:
            remaining = self._session.execute(text("""
                SELECT COUNT(*) FROM assessment_line_items
                WHERE form_id = :form_id AND item_type = :item_type AND self_assessment_level IS NULL
            """), {"form_id": form_id, "item_type": item_type}).scalar_one()
            if remaining:
                raise ValidationError("rate every assessment item before submitting")
            submitted_column = "behaviour_self_submitted_at" if item_type == "BEHAVIOUR" else "functional_self_submitted_at"
            self._session.execute(text(f"""
                UPDATE assessment_forms SET {submitted_column} = UTC_TIMESTAMP(), status = 'SELF_SUBMITTED', self_assessment_date = :today
                WHERE form_id = :form_id AND tenant_id = :tenant_id AND employee_id = :employee_id
            """), {"today": date.today(), "form_id": form_id, "tenant_id": tenant_id, "employee_id": employee_id})
        self._audit(tenant_id, actor_user_id, "EMPLOYEE_SELF_ASSESSMENT_SUBMITTED" if submit else "EMPLOYEE_SELF_ASSESSMENT_SAVED", "assessment_forms", form_id, {"item_type": item_type, "item_count": len(items)})
        assessment = self.get_current_assessment(tenant_id, employee_id, item_type)
        if assessment is None:
            raise ResourceNotFoundError("assessment form not found")
        return assessment

    def get_previous_assessments(self, tenant_id: int, employee_id: int) -> list[dict[str, object]]:
        rows = self._session.execute(text("""
            SELECT ac.cycle_id, ac.name AS cycle_name, ac.period_start, ac.period_end, af.status,
                   ali.item_type, ali.item_id, ali.desired_level, ali.self_assessment_level,
                   ali.manager_assessment_level, ali.gap,
                   CASE WHEN ali.item_type = 'BEHAVIOUR' THEN sb.name ELSE fs.name END AS item_name
            FROM assessment_forms af
            JOIN assessment_cycles ac ON ac.cycle_id = af.cycle_id AND ac.tenant_id = af.tenant_id
            JOIN assessment_line_items ali ON ali.form_id = af.form_id
            LEFT JOIN success_behaviours sb ON ali.item_type = 'BEHAVIOUR'
                AND sb.behaviour_id = ali.item_id AND sb.tenant_id = af.tenant_id
            LEFT JOIN functional_skills fs ON ali.item_type = 'SKILL'
                AND fs.skill_id = ali.item_id AND fs.tenant_id = af.tenant_id
            WHERE af.tenant_id = :tenant_id AND af.employee_id = :employee_id AND ac.status = 'CLOSED'
            ORDER BY ac.period_end DESC, ali.item_type, item_name
        """), {"tenant_id": tenant_id, "employee_id": employee_id}).mappings().all()
        cycles: dict[int, dict[str, object]] = {}
        for row in rows:
            cycle = cycles.setdefault(int(row["cycle_id"]), {
                "cycle_id": row["cycle_id"], "name": row["cycle_name"], "period_start": row["period_start"],
                "period_end": row["period_end"], "form_status": row["status"],
                "success_behaviours": [], "functional_skills": [],
            })
            key = "success_behaviours" if row["item_type"] == "BEHAVIOUR" else "functional_skills"
            cycle[key].append({key: row[key] for key in ("item_id", "item_name", "desired_level", "self_assessment_level", "manager_assessment_level", "gap")})
        return list(cycles.values())

    def _active_cycle(self, tenant_id: int, required: bool = True):
        cycle = self._session.execute(text("""
            SELECT cycle_id, name, period_start, period_end FROM assessment_cycles
            WHERE tenant_id = :tenant_id AND status = 'IN_PROGRESS'
            ORDER BY period_start DESC LIMIT 1
        """), {"tenant_id": tenant_id}).mappings().one_or_none()
        if cycle is None and required:
            raise InvalidStateError("there is no active assessment cycle")
        return cycle

    def _form_id(self, tenant_id: int, cycle_id: int, employee_id: int, item_type: str) -> int:
        form_id = self._session.execute(text("""
            SELECT form_id FROM assessment_forms
            WHERE tenant_id = :tenant_id AND cycle_id = :cycle_id AND employee_id = :employee_id
                AND assessment_type = :item_type
        """), {"tenant_id": tenant_id, "cycle_id": cycle_id, "employee_id": employee_id, "item_type": item_type}).scalar_one_or_none()
        if form_id is None:
            raise InvalidStateError("start the assessment before saving it")
        return int(form_id)

    def _items_for_cycle(self, tenant_id: int, employee_id: int, cycle_id: int, item_type: str):
        return self._session.execute(text("""
            SELECT af.status AS form_status, ali.item_id, ali.desired_level, ali.self_assessment_level,
                   CASE WHEN :item_type = 'BEHAVIOUR' THEN af.behaviour_self_submitted_at ELSE af.functional_self_submitted_at END AS section_submitted_at,
                   CASE WHEN ali.item_type = 'BEHAVIOUR' THEN sb.code ELSE fs.code END AS code,
                   CASE WHEN ali.item_type = 'BEHAVIOUR' THEN sb.name ELSE fs.name END AS name,
                   CASE WHEN ali.item_type = 'BEHAVIOUR' THEN sb.definition ELSE fs.definition END AS definition
            FROM assessment_forms af
            JOIN assessment_line_items ali ON ali.form_id = af.form_id AND ali.item_type = :item_type
            LEFT JOIN success_behaviours sb ON ali.item_type = 'BEHAVIOUR'
                AND sb.behaviour_id = ali.item_id AND sb.tenant_id = af.tenant_id
            LEFT JOIN functional_skills fs ON ali.item_type = 'SKILL'
                AND fs.skill_id = ali.item_id AND fs.tenant_id = af.tenant_id
            WHERE af.tenant_id = :tenant_id AND af.employee_id = :employee_id AND af.cycle_id = :cycle_id
                AND af.assessment_type = :item_type
            ORDER BY code
        """), {"tenant_id": tenant_id, "employee_id": employee_id, "cycle_id": cycle_id,
                 "item_type": item_type}).mappings().all()

    def _audit(self, tenant_id: int, actor_user_id: int, action: str, entity_type: str, entity_id: int, after: dict[str, object]) -> None:
        self._session.execute(text("""
            INSERT INTO audit_log (tenant_id, actor_user_id, action, entity_type, entity_id, after_json)
            VALUES (:tenant_id, :actor_user_id, :action, :entity_type, :entity_id, :after_json)
        """), {"tenant_id": tenant_id, "actor_user_id": actor_user_id, "action": action,
                 "entity_type": entity_type, "entity_id": entity_id, "after_json": json.dumps(after)})
