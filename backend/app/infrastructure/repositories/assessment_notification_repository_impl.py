"""SQL implementation for notification recipients and submission summaries."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.entities.assessment_notification import (
    AssessmentNotificationItem,
    AssessmentSubmissionNotification,
)
from app.domain.interfaces.assessment_notification_repository import (
    AssessmentNotificationRepository,
)


class SqlAlchemyAssessmentNotificationRepository(AssessmentNotificationRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def recipients(self, tenant_id: int) -> list[str]:
        rows = self._session.execute(text("""
            SELECT email FROM assessment_notification_recipients
            WHERE tenant_id=:tenant_id AND is_active=1 ORDER BY email
        """), {"tenant_id": tenant_id}).scalars().all()
        return [str(email) for email in rows]

    def submission(
        self, tenant_id: int, employee_id: int, item_type: str,
    ) -> AssessmentSubmissionNotification | None:
        rows = self._session.execute(text("""
            SELECT e.full_name AS employee_name, e.employee_code,
                   manager.full_name AS manager_name, ac.name AS cycle_name,
                   COALESCE(sb.name, fs.name) AS item_name, ali.desired_level,
                   ali.self_assessment_level, ali.manager_assessment_level, ali.gap
            FROM assessment_forms af
            JOIN employees e ON e.employee_id=af.employee_id AND e.tenant_id=af.tenant_id
            LEFT JOIN employees manager ON manager.employee_id=af.manager_employee_id
                AND manager.tenant_id=af.tenant_id
            JOIN assessment_cycles ac ON ac.cycle_id=af.cycle_id AND ac.tenant_id=af.tenant_id
            JOIN assessment_line_items ali ON ali.form_id=af.form_id AND ali.item_type=:item_type
            LEFT JOIN success_behaviours sb ON sb.behaviour_id=ali.item_id
                AND sb.tenant_id=af.tenant_id AND ali.item_type='BEHAVIOUR'
            LEFT JOIN functional_skills fs ON fs.skill_id=ali.item_id
                AND fs.tenant_id=af.tenant_id AND ali.item_type='SKILL'
            WHERE af.tenant_id=:tenant_id AND af.employee_id=:employee_id
              AND af.assessment_type=:assessment_type
            ORDER BY item_name
        """), {
            "tenant_id": tenant_id, "employee_id": employee_id,
            "item_type": item_type, "assessment_type": item_type,
        }).mappings().all()
        if not rows:
            return None
        first = rows[0]
        return AssessmentSubmissionNotification(
            employee_name=str(first["employee_name"]),
            employee_code=str(first["employee_code"]),
            manager_name=str(first["manager_name"]) if first["manager_name"] else None,
            cycle_name=str(first["cycle_name"]),
            assessment_type="Success Behaviours" if item_type == "BEHAVIOUR" else "Functional Skills",
            items=tuple(
                AssessmentNotificationItem(
                    name=str(row["item_name"]), desired_level=int(row["desired_level"]),
                    self_assessment_level=row["self_assessment_level"],
                    manager_assessment_level=row["manager_assessment_level"], gap=row["gap"],
                ) for row in rows
            ),
        )

    def audit_delivery(
        self, tenant_id: int, actor_user_id: int, employee_id: int,
        item_type: str, outcome: str,
    ) -> None:
        self._session.execute(text("""
            INSERT INTO audit_log (tenant_id, actor_user_id, action, entity_type, entity_id, after_json)
            VALUES (:tenant_id, :actor_user_id, :action, 'assessment_forms', :employee_id, :after_json)
        """), {
            "tenant_id": tenant_id, "actor_user_id": actor_user_id,
            "action": f"ASSESSMENT_EMAIL_{outcome}", "employee_id": employee_id,
            "after_json": '{"item_type":"' + item_type + '"}',
        })
