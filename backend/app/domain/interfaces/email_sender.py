"""Port for sending notification email without exposing SMTP to workflows."""

from abc import ABC, abstractmethod


class EmailSender(ABC):
    @abstractmethod
    def send(
        self, tenant_id: int, recipients: list[str], subject: str, body: str,
    ) -> bool: ...
