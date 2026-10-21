"""Tenant-scoped SQL read model for Executive Review."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.interfaces.executive_review_repository import ExecutiveReviewRepository


class SqlAlchemyExecutiveReviewRepository(ExecutiveReviewRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_dashboard(
        self, tenant_id: int, division_id: int | None, function_name: str | None = None
    ) -> dict[str, object]:
        divisions = self._session.execute(text("""
            SELECT division_id, name, code, entity_id FROM divisions
            WHERE tenant_id=:tenant_id ORDER BY name
        """), {"tenant_id": tenant_id}).mappings().all()
        entity = self._session.execute(text("""
            SELECT entity_id, name, code FROM entities
            WHERE tenant_id=:tenant_id AND entity_id IN (
                SELECT DISTINCT entity_id FROM divisions
                WHERE tenant_id=:tenant_id AND (:division_id IS NULL OR division_id=:division_id)
            ) ORDER BY name LIMIT 1
        """), {"tenant_id": tenant_id, "division_id": division_id}).mappings().one_or_none()
        cycle = self._session.execute(text("""
            SELECT cycle_id, name, period_start, period_end FROM assessment_cycles
            WHERE tenant_id=:tenant_id AND status='IN_PROGRESS'
            ORDER BY period_start DESC LIMIT 1
        """), {"tenant_id": tenant_id}).mappings().one_or_none()
        filters = {
            "tenant_id": tenant_id,
            "division_id": division_id,
            "function_name": function_name,
            "cycle_id": cycle["cycle_id"] if cycle else None,
        }
        manpower = int(self._session.execute(text("""
            SELECT COUNT(*) FROM employees e
            LEFT JOIN functions f ON f.function_id = e.function_id
            WHERE e.tenant_id=:tenant_id AND e.status='ACTIVE'
              AND (:division_id IS NULL OR e.division_id=:division_id)
              AND (:function_name IS NULL OR TRIM(f.name)=:function_name)
        """), filters).scalar_one())
        dial1_manpower = int(self._session.execute(text("""
            SELECT COUNT(*) FROM employees e
            LEFT JOIN functions f ON f.function_id = e.function_id
            WHERE e.tenant_id=:tenant_id AND e.status='ACTIVE'
              AND e.division_id=1
              AND (:function_name IS NULL OR TRIM(f.name)=:function_name)
        """), filters).scalar_one())
        dial2_manpower = int(self._session.execute(text("""
            SELECT COUNT(*) FROM employees e
            LEFT JOIN functions f ON f.function_id = e.function_id
            WHERE e.tenant_id=:tenant_id AND e.status='ACTIVE'
              AND e.division_id=2
              AND (:function_name IS NULL OR TRIM(f.name)=:function_name)
        """), filters).scalar_one())
        assessed = int(self._session.execute(text("""
            SELECT COUNT(DISTINCT e.employee_id)
            FROM employees e JOIN assessment_forms af
              ON af.tenant_id=e.tenant_id AND af.employee_id=e.employee_id
            LEFT JOIN functions f ON f.function_id = e.function_id
            WHERE e.tenant_id=:tenant_id AND e.status='ACTIVE'
              AND (:division_id IS NULL OR e.division_id=:division_id)
              AND (:function_name IS NULL OR TRIM(f.name)=:function_name)
              AND af.status != 'NOT_STARTED'
        """), filters).scalar_one())
        dial1_assessed = int(self._session.execute(text("""
            SELECT COUNT(DISTINCT e.employee_id)
            FROM employees e JOIN assessment_forms af
              ON af.tenant_id=e.tenant_id AND af.employee_id=e.employee_id
            LEFT JOIN functions f ON f.function_id = e.function_id
            WHERE e.tenant_id=:tenant_id AND e.status='ACTIVE'
              AND e.division_id = 1
              AND (:function_name IS NULL OR TRIM(f.name)=:function_name)
              AND af.status != 'NOT_STARTED'
        """), filters).scalar_one())
        dial2_assessed = int(self._session.execute(text("""
            SELECT COUNT(DISTINCT e.employee_id)
            FROM employees e JOIN assessment_forms af
              ON af.tenant_id=e.tenant_id AND af.employee_id=e.employee_id
            LEFT JOIN functions f ON f.function_id = e.function_id
            WHERE e.tenant_id=:tenant_id AND e.status='ACTIVE'
              AND e.division_id = 2
              AND (:function_name IS NULL OR TRIM(f.name)=:function_name)
              AND af.status != 'NOT_STARTED'
        """), filters).scalar_one())
        manager_pending = int(self._session.execute(text("""
            SELECT COUNT(DISTINCT af.employee_id) FROM assessment_forms af
            JOIN employees e ON e.employee_id=af.employee_id AND e.tenant_id=af.tenant_id
            LEFT JOIN functions f ON f.function_id = e.function_id
            WHERE af.tenant_id=:tenant_id AND e.status='ACTIVE'
              AND (:division_id IS NULL OR e.division_id=:division_id)
              AND (:function_name IS NULL OR TRIM(f.name)=:function_name)
              AND af.status = 'SELF_SUBMITTED'
        """), filters).scalar_one())
        assessed_population = assessed
        gap_items = int(self._session.execute(text("""
            SELECT COUNT(*) FROM assessment_line_items ali
            JOIN assessment_forms af ON af.form_id=ali.form_id AND af.tenant_id=:tenant_id
            JOIN employees e ON e.employee_id=af.employee_id AND e.tenant_id=af.tenant_id
            LEFT JOIN functions f ON f.function_id = e.function_id
            WHERE e.status='ACTIVE'
              AND (:division_id IS NULL OR e.division_id=:division_id)
              AND (:function_name IS NULL OR TRIM(f.name)=:function_name)
              AND ali.gap < 0
        """), filters).scalar_one())
        dial1_gaps = int(self._session.execute(text("""
            SELECT COUNT(*) FROM assessment_line_items ali
            JOIN assessment_forms af ON af.form_id=ali.form_id AND af.tenant_id=:tenant_id
            JOIN employees e ON e.employee_id=af.employee_id AND e.tenant_id=af.tenant_id
            LEFT JOIN functions f ON f.function_id = e.function_id
            WHERE e.status='ACTIVE'
              AND e.division_id = 1
              AND (:function_name IS NULL OR TRIM(f.name)=:function_name)
              AND ali.gap < 0
        """), filters).scalar_one())
        dial2_gaps = int(self._session.execute(text("""
            SELECT COUNT(*) FROM assessment_line_items ali
            JOIN assessment_forms af ON af.form_id=ali.form_id AND af.tenant_id=:tenant_id
            JOIN employees e ON e.employee_id=af.employee_id AND e.tenant_id=af.tenant_id
            LEFT JOIN functions f ON f.function_id = e.function_id
            WHERE e.status='ACTIVE'
              AND e.division_id = 2
              AND (:function_name IS NULL OR TRIM(f.name)=:function_name)
              AND ali.gap < 0
        """), filters).scalar_one())
        people_with_gaps = int(self._session.execute(text("""
            SELECT COUNT(DISTINCT e.employee_id) FROM assessment_line_items ali
            JOIN assessment_forms af ON af.form_id=ali.form_id AND af.tenant_id=:tenant_id
            JOIN employees e ON e.employee_id=af.employee_id AND e.tenant_id=af.tenant_id
            LEFT JOIN functions f ON f.function_id = e.function_id
            WHERE e.status='ACTIVE'
              AND (:division_id IS NULL OR e.division_id=:division_id)
              AND (:function_name IS NULL OR TRIM(f.name)=:function_name)
              AND ali.gap < 0
        """), filters).scalar_one())
        critical_roles = int(self._session.execute(text("""
            SELECT COUNT(*) FROM critical_roles cr JOIN roles r ON r.role_id=cr.role_id
            WHERE cr.tenant_id=:tenant_id AND cr.status='VALIDATED'
              AND (:division_id IS NULL OR r.division_id=:division_id)
        """), filters).scalar_one())
        without_successor = int(self._session.execute(text("""
            SELECT COUNT(*) FROM critical_roles cr JOIN roles r ON r.role_id=cr.role_id
            WHERE cr.tenant_id=:tenant_id AND cr.status='VALIDATED'
              AND (:division_id IS NULL OR r.division_id=:division_id)
              AND NOT EXISTS (SELECT 1 FROM succession_candidates sc WHERE sc.critical_role_id=cr.critical_role_id)
        """), filters).scalar_one())
        ready_now_cover = int(self._session.execute(text("""
            SELECT COUNT(DISTINCT cr.critical_role_id) FROM critical_roles cr
            JOIN roles r ON r.role_id=cr.role_id
            JOIN succession_candidates sc ON sc.critical_role_id=cr.critical_role_id
            WHERE cr.tenant_id=:tenant_id AND cr.status='VALIDATED'
              AND (:division_id IS NULL OR r.division_id=:division_id)
              AND (sc.readiness_level = 1 OR sc.readiness_label LIKE '%Ready%')
        """), filters).scalar_one())
        successor_named = int(self._session.execute(text("""
            SELECT COUNT(DISTINCT cr.critical_role_id) FROM critical_roles cr
            JOIN roles r ON r.role_id=cr.role_id
            JOIN succession_candidates sc ON sc.critical_role_id=cr.critical_role_id
            WHERE cr.tenant_id=:tenant_id AND cr.status='VALIDATED'
              AND (:division_id IS NULL OR r.division_id=:division_id)
        """), filters).scalar_one())
        roles_count = int(self._session.execute(text("""
            SELECT COUNT(DISTINCT title) FROM roles
            WHERE tenant_id=:tenant_id
              AND (:division_id IS NULL OR division_id=:division_id)
        """), filters).scalar_one())
        skills_count = int(self._session.execute(text("""
            SELECT COUNT(*) FROM functional_skills
            WHERE tenant_id=:tenant_id
              AND (:division_id IS NULL OR division_id=:division_id)
        """), filters).scalar_one())
        behaviours_count = int(self._session.execute(text("""
            SELECT COUNT(*) FROM success_behaviours
            WHERE tenant_id=:tenant_id
        """), filters).scalar_one())
        functions_count = int(self._session.execute(text("""
            SELECT COUNT(*) FROM functions
            WHERE tenant_id=:tenant_id
              AND (:division_id IS NULL OR division_id=:division_id)
        """), filters).scalar_one())
        departments_count = int(self._session.execute(text("""
            SELECT COUNT(*) FROM departments
            WHERE tenant_id=:tenant_id
              AND (:division_id IS NULL OR division_id=:division_id)
        """), filters).scalar_one())
        ask_mapped_roles = int(self._session.execute(text("""
            SELECT COUNT(*) FROM roles
            WHERE tenant_id=:tenant_id
              AND (:division_id IS NULL OR division_id=:division_id)
              AND ask_status != 'NOT_MAPPED'
        """), filters).scalar_one())

        skills_rows = self._session.execute(text("""
            SELECT fs.code as skill_code, fs.name as skill_name,
                   COALESCE(f.name, 'Operations') as `function`,
                   COALESCE(d.name, 'General') as department,
                   fs.definition
            FROM functional_skills fs
            LEFT JOIN functions f ON f.function_id = fs.function_id
            LEFT JOIN departments d ON d.department_id = fs.department_id
            WHERE fs.tenant_id=:tenant_id
              AND (:division_id IS NULL OR fs.division_id=:division_id)
            ORDER BY fs.name
        """), filters).mappings().all()

        roles_rows = self._session.execute(text("""
            SELECT r.role_id, r.title, r.division_id,
                   COALESCE(f.name, 'Operations') as `function`,
                   IF(r.division_id=1, 'Dials 1', 'Dials 2') as division,
                   r.description_status, r.ask_status
            FROM roles r
            LEFT JOIN functions f ON f.function_id = r.function_id
            WHERE r.tenant_id=:tenant_id
              AND (:division_id IS NULL OR r.division_id=:division_id)
            ORDER BY r.title
        """), filters).mappings().all()

        behaviours_rows = self._session.execute(text("""
            SELECT code, name as behaviour, definition
            FROM success_behaviours
            WHERE tenant_id=:tenant_id
            ORDER BY code
        """), filters).mappings().all()

        grade_band_gaps_rows = self._session.execute(text("""
            SELECT 
                CASE 
                    WHEN gb.band_code LIKE 'LM%' THEN 'LM'
                    WHEN gb.band_code LIKE 'M%' THEN 'M'
                    WHEN gb.band_code LIKE 'E%' THEN 'E'
                    WHEN gb.band_code LIKE 'S%' THEN 'S3'
                    ELSE gb.band_code
                END AS band,
                COUNT(DISTINCT CASE WHEN e.status = 'ACTIVE' AND af.status != 'NOT_STARTED' THEN e.employee_id END) AS total,
                COUNT(DISTINCT CASE WHEN e.status = 'ACTIVE' AND af.status != 'NOT_STARTED' AND ali.gap < 0 THEN e.employee_id END) AS gapped
            FROM grade_bands gb
            LEFT JOIN employees e ON e.grade_band_id = gb.grade_band_id AND e.tenant_id = :tenant_id AND (:division_id IS NULL OR e.division_id = :division_id)
            LEFT JOIN assessment_forms af ON af.employee_id = e.employee_id
            LEFT JOIN assessment_line_items ali ON ali.form_id = af.form_id AND ali.gap < 0
            WHERE gb.tenant_id = :tenant_id
              AND gb.band_code NOT IN ('A1', 'A2', 'A3', 'SS', 'S1', 'S2')
            GROUP BY band
            ORDER BY 
                CASE band
                    WHEN 'LM' THEN 1
                    WHEN 'M' THEN 2
                    WHEN 'E' THEN 3
                    WHEN 'S3' THEN 4
                    ELSE 5
                END
        """), filters).mappings().all()

        function_gaps_rows = self._session.execute(text("""
            SELECT 
                TRIM(f.name) AS function_name,
                COUNT(ali.line_item_id) AS gap_count
            FROM assessment_line_items ali
            JOIN assessment_forms af ON af.form_id = ali.form_id
            JOIN employees e ON e.employee_id = af.employee_id
            JOIN functions f ON f.function_id = e.function_id
            WHERE e.tenant_id = :tenant_id
              AND e.status = 'ACTIVE'
              AND ali.gap < 0
              AND (:division_id IS NULL OR e.division_id = :division_id)
            GROUP BY TRIM(f.name)
            ORDER BY gap_count DESC
        """), filters).mappings().all()

        employee_gaps_rows = self._session.execute(text("""
            SELECT 
                e.employee_code AS emp_code,
                e.full_name AS name,
                COALESCE(e.designation, '—') AS designation,
                COALESCE(TRIM(f.name), 'General') AS function_name,
                IF(e.division_id = 1, 'Dial 1', 'Dial 2') AS division,
                CASE 
                    WHEN gb.band_code LIKE 'LM%' THEN 'LM'
                    WHEN gb.band_code LIKE 'M%' THEN 'M'
                    WHEN gb.band_code LIKE 'E%' THEN 'E'
                    WHEN gb.band_code LIKE 'S%' THEN 'S3'
                    ELSE gb.band_code
                END AS grade_band,
                COUNT(DISTINCT CASE WHEN ali.gap < 0 THEN ali.line_item_id END) AS gaps
            FROM employees e
            JOIN grade_bands gb ON gb.grade_band_id = e.grade_band_id
            JOIN assessment_forms af ON af.employee_id = e.employee_id
            LEFT JOIN assessment_line_items ali ON ali.form_id = af.form_id AND ali.gap < 0
            LEFT JOIN functions f ON f.function_id = e.function_id
            WHERE e.tenant_id = :tenant_id
              AND e.status = 'ACTIVE'
              AND af.status != 'NOT_STARTED'
              AND (:division_id IS NULL OR e.division_id = :division_id)
              AND (:function_name IS NULL OR TRIM(f.name) = :function_name)
            GROUP BY e.employee_id, e.employee_code, e.full_name, e.designation, f.name, e.division_id, gb.band_code
            ORDER BY gaps DESC, e.full_name ASC
        """), filters).mappings().all()

        ask_completion_pct = int(round(assessed * 100.0 / manpower)) if manpower > 0 else 0
        dial1_ask_completion_pct = int(round(dial1_assessed * 100.0 / dial1_manpower)) if dial1_manpower > 0 else 0
        dial2_ask_completion_pct = int(round(dial2_assessed * 100.0 / dial2_manpower)) if dial2_manpower > 0 else 0

        return {"entity": dict(entity) if entity else None, "divisions": [dict(row) for row in divisions], "active_cycle": dict(cycle) if cycle else None,
                "selected_division_id": division_id, "people_assessed": assessed, "assessed_population": assessed_population,
                "total_manpower": manpower, "dial1_manpower": dial1_manpower, "dial2_manpower": dial2_manpower,
                "ask_completion_pct": ask_completion_pct,
                "dial1_ask_completion_pct": dial1_ask_completion_pct,
                "dial2_ask_completion_pct": dial2_ask_completion_pct,
                "manager_assessments_pending": manager_pending,
                "critical_roles": critical_roles, "critical_roles_without_successor": without_successor,
                "ready_now_cover": ready_now_cover,
                "successor_named": successor_named,
                "criticality_basis": "VALIDATED",
                "succession_plan_count": critical_roles,
                "reported_gap_items": gap_items,
                "dial1_assessed": dial1_assessed,
                "dial2_assessed": dial2_assessed,
                "dial1_gaps": dial1_gaps,
                "dial2_gaps": dial2_gaps,
                "people_with_gaps": people_with_gaps,
                "roles_count": roles_count,
                "skills_count": skills_count,
                "behaviours_count": behaviours_count,
                "functions_count": functions_count,
                "departments_count": departments_count,
                "ask_mapped_roles": ask_mapped_roles,
                "skills": [dict(row) for row in skills_rows],
                "roles": [dict(row) for row in roles_rows],
                "success_behaviours": [dict(row) for row in behaviours_rows],
                "gaps_by_grade_band": [dict(row) for row in grade_band_gaps_rows],
                "gaps_by_function": [dict(row) for row in function_gaps_rows],
                "employee_gaps": [dict(row) for row in employee_gaps_rows]}


