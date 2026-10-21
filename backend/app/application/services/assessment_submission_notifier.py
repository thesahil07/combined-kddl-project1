"""Best-effort post-submission email notification workflow."""

from html import escape
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
        metadata = (
            ("Employee", f"{submission.employee_name} ({submission.employee_code})"),
            ("Manager", submission.manager_name or "Not assigned"),
            ("Cycle", submission.cycle_name),
            ("Assessment", submission.assessment_type),
        )
        metadata_html = "".join(
            f"<tr><th style=\"text-align:left;padding:6px 12px 6px 0;color:#596576\">{escape(label)}</th>"
            f"<td style=\"padding:6px 0\">{escape(value)}</td></tr>"
            for label, value in metadata
        )
        item_rows = "".join(
            "<tr>"
            f"<td style=\"padding:8px;border:1px solid #dfe5ea\">{escape(item.name)}</td>"
            f"<td style=\"padding:8px;border:1px solid #dfe5ea;text-align:center\">L{item.desired_level}</td>"
            f"<td style=\"padding:8px;border:1px solid #dfe5ea;text-align:center\">{AssessmentSubmissionNotifier._level(item.self_assessment_level)}</td>"
            f"<td style=\"padding:8px;border:1px solid #dfe5ea;text-align:center\">{AssessmentSubmissionNotifier._level(item.manager_assessment_level)}</td>"
            f"<td style=\"padding:8px;border:1px solid #dfe5ea;text-align:center\">{item.gap if item.gap is not None else '—'}</td>"
            "</tr>"
            for item in submission.items
        )
        return (
            "<html><body style=\"font-family:Arial,sans-serif;color:#1a1f2b\">"
            f"<p><strong>{escape(submitted_by)} submission recorded</strong></p>"
            f"<table role=\"presentation\" style=\"border-collapse:collapse;margin:0 0 20px\">{metadata_html}</table>"
            "<table style=\"border-collapse:collapse;width:100%;max-width:800px\">"
            "<thead><tr style=\"background:#1a1f2b;color:#ffffff\">"
            "<th style=\"padding:9px;text-align:left\">Skill Name</th>"
            "<th style=\"padding:9px\">DL</th><th style=\"padding:9px\">SAL</th>"
            "<th style=\"padding:9px\">MAL</th><th style=\"padding:9px\">GAP</th>"
            f"</tr></thead><tbody>{item_rows}</tbody></table></body></html>"
        )

    @staticmethod
    def _level(value: int | None) -> str:
        return f"L{value}" if value is not None else "—"
