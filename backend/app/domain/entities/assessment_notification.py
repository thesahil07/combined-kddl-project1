"""Restricted-PII data needed for a submission notification."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AssessmentNotificationItem:
    name: str
    desired_level: int
    self_assessment_level: int | None
    manager_assessment_level: int | None
    gap: int | None


@dataclass(frozen=True, slots=True)
class AssessmentSubmissionNotification:
    employee_name: str
    employee_code: str
    manager_name: str | None
    cycle_name: str
    assessment_type: str
    items: tuple[AssessmentNotificationItem, ...]
