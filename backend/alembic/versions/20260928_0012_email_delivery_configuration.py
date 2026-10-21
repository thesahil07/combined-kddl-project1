"""Store encrypted, tenant-managed SMTP delivery configuration.

Revision ID: 20260928_0012
Revises: 20260928_0011
"""

from alembic import op
from sqlalchemy import inspect


revision = "20260928_0012"
down_revision = "20260928_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "email_delivery_configurations" in inspector.get_table_names():
        return
    op.execute("""
        CREATE TABLE email_delivery_configurations (
          email_delivery_configuration_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
          tenant_id BIGINT UNSIGNED NOT NULL,
          smtp_host VARCHAR(255) NOT NULL,
          smtp_port SMALLINT UNSIGNED NOT NULL DEFAULT 587,
          smtp_username VARCHAR(255) NULL,
          smtp_password_encrypted TEXT NOT NULL,
          smtp_from_email VARCHAR(150) NOT NULL,
          smtp_use_tls BOOLEAN NOT NULL DEFAULT TRUE,
          is_active BOOLEAN NOT NULL DEFAULT TRUE,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          CONSTRAINT fk_email_delivery_configuration_tenant
            FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
          UNIQUE KEY uq_email_delivery_configuration_tenant (tenant_id)
        ) ENGINE=InnoDB
    """)


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if "email_delivery_configurations" in inspector.get_table_names():
        op.execute("DROP TABLE email_delivery_configurations")
