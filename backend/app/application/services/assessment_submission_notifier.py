"""Best-effort post-submission email notification workflow."""

import smtplib

from app.domain.entities.assessment_notification import AssessmentSubmissionNotification
from app.domain.interfaces.assessment_notification_repository import AssessmentNotificationRepository
from app.domain.interfaces.email_sender import EmailSender


class AssessmentSubmissionNotifier:
    def __init__(
        self, repository: AssessmentNotificationRepository, sender: EmailSender,
    ) -> None:
        self._repository = repository
        self._sender = sender

    def notify(
        self, tenant_id: int, employee_id: int, actor_user_id: int, item_type: str,
        submitted_by: str,
    ) -> None:
        recipients = self._repository.recipients(tenant_id)
        submission = self._repository.submission(tenant_id, employee_id, item_type)
        if not recipients or submission is None:
            self._repository.audit_delivery(tenant_id, actor_user_id, employee_id, item_type, "SKIPPED")
            return
        try:
            delivered = self._sender.send(
                tenant_id, recipients, self._subject(submission, submitted_by),
                self._body(submission, submitted_by),
            )
            self._repository.audit_delivery(tenant_id, actor_user_id, employee_id, item_type, "SENT" if delivered else "NOT_CONFIGURED")
        except (OSError, smtplib.SMTPException):
            self._repository.audit_delivery(tenant_id, actor_user_id, employee_id, item_type, "FAILED")

    @staticmethod
    def _subject(submission: AssessmentSubmissionNotification, submitted_by: str) -> str:
        return f"{submission.assessment_type} submitted by {submitted_by} — {submission.employee_name}"

    @staticmethod
    def _body(submission: AssessmentSubmissionNotification, submitted_by: str) -> str:
        lines = [
            f"{submitted_by} submission recorded", "",
            f"Employee: {submission.employee_name} ({submission.employee_code})",
            f"Manager: {submission.manager_name or 'Not assigned'}",
            f"Cycle: {submission.cycle_name}",
            f"Assessment: {submission.assessment_type}", "",
            "Skill Name | DL | SAL | MAL | GAP",
        ]
        lines.extend(
            f"{item.name} | L{item.desired_level} | {AssessmentSubmissionNotifier._level(item.self_assessment_level)} | {AssessmentSubmissionNotifier._level(item.manager_assessment_level)} | {item.gap if item.gap is not None else '—'}"
            for item in submission.items
        )
        return "\n".join(lines)

    @staticmethod
    def _level(value: int | None) -> str:
        return f"L{value}" if value is not None else "—"
