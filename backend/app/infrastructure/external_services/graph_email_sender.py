"""Microsoft Graph application-permission email adapter."""

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from app.domain.interfaces.email_sender import EmailSender
from app.infrastructure.repositories.email_delivery_configuration_repository_impl import (
    GraphConfiguration,
    SqlAlchemyEmailDeliveryConfigurationRepository,
)


class GraphEmailSender(EmailSender):
    """Send HTML notifications through Microsoft Graph sendMail."""

    def __init__(self, session: Session) -> None:
        self._configuration = SqlAlchemyEmailDeliveryConfigurationRepository(session)

    def send(
        self, tenant_id: int, recipients: list[str], subject: str, body: str,
    ) -> bool:
        configuration = self._configuration.active_graph(tenant_id)
        if configuration is None or not recipients:
            return False
        access_token = self._access_token(configuration)
        payload = json.dumps({
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": body},
                "toRecipients": [
                    {"emailAddress": {"address": recipient}}
                    for recipient in recipients
                ],
            },
            "saveToSentItems": True,
        }).encode()
        request = Request(
            f"https://graph.microsoft.com/v1.0/users/{configuration.from_email}/sendMail",
            data=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=15):
            pass
        return True

    @staticmethod
    def _access_token(configuration: GraphConfiguration) -> str:
        # Kept local to the adapter so no Graph-specific protocol leaks upward.
        request = Request(
            f"https://login.microsoftonline.com/{configuration.tenant_id}/oauth2/v2.0/token",
            data=urlencode({
                "client_id": configuration.client_id,
                "client_secret": configuration.client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            }).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urlopen(request, timeout=15) as response:
            token = json.loads(response.read().decode()).get("access_token")
        if not token:
            raise OSError("Microsoft Graph did not return an access token")
        return str(token)
