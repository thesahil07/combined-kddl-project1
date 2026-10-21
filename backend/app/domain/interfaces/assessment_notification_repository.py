"""Tenant-scoped notification configuration and assessment read model."""

from abc import ABC, abstractmethod

from app.domain.entities.assessment_notification import AssessmentSubmissionNotification


class AssessmentNotificationRepository(ABC):
    @abstractmethod
    def recipients(self, tenant_id: int) -> list[str]: ...

    @abstractmethod
    def submission(
        self, tenant_id: int, employee_id: int, item_type: str,
    ) -> AssessmentSubmissionNotification | None: ...

    @abstractmethod
    def audit_delivery(
        self, tenant_id: int, actor_user_id: int, employee_id: int,
        item_type: str, outcome: str,
    ) -> None: ...
