from app.application.services.assessment_submission_notifier import AssessmentSubmissionNotifier
from app.domain.entities.assessment_notification import (
    AssessmentNotificationItem,
    AssessmentSubmissionNotification,
)


class FakeRepository:
    def __init__(self) -> None:
        self.audit: list[str] = []

    def recipients(self, tenant_id: int) -> list[str]:
        return ["bhawna.narula@vvnt.in"]

    def submission(self, tenant_id: int, employee_id: int, item_type: str):
        return AssessmentSubmissionNotification(
            employee_name="Demo Employee", employee_code="D1-EMP-001",
            manager_name="Demo Manager", cycle_name="FY 2026 Cycle 1",
            assessment_type="Success Behaviours",
            items=(AssessmentNotificationItem("Ownership", 2, 2, None, None),),
        )

    def audit_delivery(self, *args) -> None:
        self.audit.append(args[-1])


class FakeSender:
    def __init__(self) -> None:
        self.message: tuple[list[str], str, str] | None = None

    def send(self, tenant_id: int, recipients: list[str], subject: str, body: str) -> bool:
        self.message = recipients, subject, body
        return True


def test_submission_notification_contains_assessment_levels_and_is_audited() -> None:
    repository = FakeRepository()
    sender = FakeSender()

    AssessmentSubmissionNotifier(repository, sender).notify(1, 1, 1, "BEHAVIOUR", "Employee")

    assert sender.message is not None
    assert sender.message[0] == ["bhawna.narula@vvnt.in"]
    assert "submitted by Employee" in sender.message[1]
    assert "<table" in sender.message[2]
    assert "Ownership" in sender.message[2]
    assert "L2" in sender.message[2]
    assert repository.audit == ["SENT"]
