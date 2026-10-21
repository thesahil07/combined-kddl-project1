"""SMTP adapter using tenant-owned database configuration."""

import smtplib
from email.message import EmailMessage

from app.domain.interfaces.email_sender import EmailSender
from app.infrastructure.repositories.email_delivery_configuration_repository_impl import (
    SqlAlchemyEmailDeliveryConfigurationRepository,
)
from sqlalchemy.orm import Session


class SmtpEmailSender(EmailSender):
    def __init__(self, session: Session) -> None:
        self._configuration = SqlAlchemyEmailDeliveryConfigurationRepository(session)

    def send(
        self, tenant_id: int, recipients: list[str], subject: str, body: str,
    ) -> bool:
        configuration = self._configuration.active(tenant_id)
        if not recipients or configuration is None:
            return False
        message = EmailMessage()
        message["From"] = configuration.from_email
        message["To"] = ", ".join(recipients)
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(configuration.host, configuration.port, timeout=10) as client:
            if configuration.use_tls:
                client.starttls()
            if configuration.username and configuration.password:
                client.login(configuration.username, configuration.password)
            client.send_message(message)
        return True
