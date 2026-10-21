"""Encrypted, tenant-scoped SMTP configuration access."""

from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings


@dataclass(frozen=True, slots=True)
class SmtpConfiguration:
    host: str
    port: int
    username: str | None
    password: str | None
    from_email: str
    use_tls: bool


@dataclass(frozen=True, slots=True)
class GraphConfiguration:
    tenant_id: str
    client_id: str
    client_secret: str
    from_email: str


class SqlAlchemyEmailDeliveryConfigurationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def active(self, tenant_id: int) -> SmtpConfiguration | None:
        row = self._session.execute(text("""
            SELECT smtp_host, smtp_port, smtp_username, smtp_password_encrypted,
                   smtp_from_email, smtp_use_tls
            FROM email_delivery_configurations
            WHERE tenant_id=:tenant_id AND is_active=1
        """), {"tenant_id": tenant_id}).mappings().one_or_none()
        if row is None or not settings.email_config_encryption_key:
            return None
        password = self._decrypt(str(row["smtp_password_encrypted"]))
        if password is None:
            return None
        return SmtpConfiguration(
            host=str(row["smtp_host"]), port=int(row["smtp_port"]),
            username=str(row["smtp_username"]) if row["smtp_username"] else None,
            password=password, from_email=str(row["smtp_from_email"]),
            use_tls=bool(row["smtp_use_tls"]),
        )

    def active_graph(self, tenant_id: int) -> GraphConfiguration | None:
        row = self._session.execute(text("""
            SELECT graph_tenant_id, graph_client_id, graph_client_secret_encrypted,
                   smtp_from_email
            FROM email_delivery_configurations
            WHERE tenant_id=:tenant_id AND is_active=1 AND delivery_provider='GRAPH'
        """), {"tenant_id": tenant_id}).mappings().one_or_none()
        if row is None or not settings.email_config_encryption_key:
            return None
        secret = self._decrypt(str(row["graph_client_secret_encrypted"] or ""))
        if not secret or not row["graph_tenant_id"] or not row["graph_client_id"]:
            return None
        return GraphConfiguration(
            tenant_id=str(row["graph_tenant_id"]),
            client_id=str(row["graph_client_id"]),
            client_secret=secret,
            from_email=str(row["smtp_from_email"]),
        )

    @staticmethod
    def _decrypt(value: str) -> str | None:
        try:
            cipher = Fernet(settings.email_config_encryption_key.encode())
            return cipher.decrypt(value.encode()).decode()
        except (InvalidToken, ValueError):
            return None
