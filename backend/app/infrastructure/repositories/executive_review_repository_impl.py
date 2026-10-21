"""Tenant-scoped SQL read model for Executive Review."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.interfaces.executive_review_repository import ExecutiveReviewRepository


class SqlAlchemyExecutiveReviewRepository(ExecutiveReviewRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_dashboard(self, tenant_id: int, division_id: int | None) -> dict[str, object]:
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
        filters = {"tenant_id": tenant_id, "division_id": division_id,
                   "cycle_id": cycle["cycle_id"] if cycle else None}
        manpower = int(self._session.execute(text("""
            SELECT COUNT(*) FROM employees
            WHERE tenant_id=:tenant_id AND status='ACTIVE'
              AND (:division_id IS NULL OR division_id=:division_id)
        """), filters).scalar_one())
        assessed = int(self._session.execute(text("""
            SELECT COUNT(DISTINCT e.employee_id)
            FROM employees e JOIN assessment_forms af
              ON af.tenant_id=e.tenant_id AND af.employee_id=e.employee_id
            WHERE e.tenant_id=:tenant_id AND e.status='ACTIVE'
              AND (:division_id IS NULL OR e.division_id=:division_id)
              AND af.cycle_id=:cycle_id
              AND ((af.assessment_type='BEHAVIOUR' AND af.behaviour_self_submitted_at IS NOT NULL)
                OR (af.assessment_type='SKILL' AND af.functional_self_submitted_at IS NOT NULL))
        """), filters).scalar_one()) if cycle else 0
        manager_pending = int(self._session.execute(text("""
            SELECT COUNT(DISTINCT af.employee_id) FROM assessment_forms af
            JOIN employees e ON e.employee_id=af.employee_id AND e.tenant_id=af.tenant_id
            WHERE af.tenant_id=:tenant_id AND af.cycle_id=:cycle_id AND e.status='ACTIVE'
              AND (:division_id IS NULL OR e.division_id=:division_id)
              AND ((af.assessment_type='BEHAVIOUR' AND af.behaviour_self_submitted_at IS NOT NULL AND af.behaviour_manager_submitted_at IS NULL)
                OR (af.assessment_type='SKILL' AND af.functional_self_submitted_at IS NOT NULL AND af.functional_manager_submitted_at IS NULL))
        """), filters).scalar_one()) if cycle else 0
        gap_items = int(self._session.execute(text("""
            SELECT COUNT(*) FROM assessment_line_items ali
            JOIN assessment_forms af ON af.form_id=ali.form_id AND af.tenant_id=:tenant_id
            JOIN employees e ON e.employee_id=af.employee_id AND e.tenant_id=af.tenant_id
            WHERE af.cycle_id=:cycle_id AND e.status='ACTIVE'
              AND (:division_id IS NULL OR e.division_id=:division_id)
              AND ali.gap < 0
        """), filters).scalar_one()) if cycle else 0
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
        return {"entity": dict(entity) if entity else None, "divisions": [dict(row) for row in divisions], "active_cycle": dict(cycle) if cycle else None,
                "selected_division_id": division_id, "people_assessed": assessed,
                "total_manpower": manpower, "manager_assessments_pending": manager_pending,
                "critical_roles": critical_roles, "critical_roles_without_successor": without_successor,
                "reported_gap_items": gap_items}
