"""Add Microsoft Graph credentials to tenant email delivery configuration.

Revision ID: 20261010_0017
Revises: 20260930_0016
"""

from alembic import op
from sqlalchemy import inspect


revision = "20261010_0017"
down_revision = "20260930_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {
        column["name"]
        for column in inspector.get_columns("email_delivery_configurations")
    }
    if "delivery_provider" not in columns:
        op.execute(
            "ALTER TABLE email_delivery_configurations "
            "ADD COLUMN delivery_provider VARCHAR(20) NOT NULL DEFAULT 'SMTP' "
            "COMMENT 'Internal: SMTP or GRAPH' AFTER tenant_id"
        )
    if "graph_tenant_id" not in columns:
        op.execute(
            "ALTER TABLE email_delivery_configurations "
            "ADD COLUMN graph_tenant_id VARCHAR(64) NULL "
            "COMMENT 'Internal: Microsoft Entra tenant identifier' AFTER smtp_use_tls"
        )
    if "graph_client_id" not in columns:
        op.execute(
            "ALTER TABLE email_delivery_configurations "
            "ADD COLUMN graph_client_id VARCHAR(64) NULL "
            "COMMENT 'Internal: Microsoft Entra application identifier' AFTER graph_tenant_id"
        )
    if "graph_client_secret_encrypted" not in columns:
        op.execute(
            "ALTER TABLE email_delivery_configurations "
            "ADD COLUMN graph_client_secret_encrypted TEXT NULL "
            "COMMENT 'Restricted: Fernet-encrypted Microsoft Entra client secret' "
            "AFTER graph_client_id"
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {
        column["name"]
        for column in inspector.get_columns("email_delivery_configurations")
    }
    for column in (
        "graph_client_secret_encrypted",
        "graph_client_id",
        "graph_tenant_id",
        "delivery_provider",
    ):
        if column in columns:
            op.execute(
                f"ALTER TABLE email_delivery_configurations DROP COLUMN {column}"
            )
