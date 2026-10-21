"""Add tenant-managed recipients for assessment submission notifications.

Revision ID: 20260928_0011
Revises: 20260919_0010
"""

from alembic import op
from sqlalchemy import inspect


revision = "20260928_0011"
down_revision = "20260919_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "assessment_notification_recipients" in inspector.get_table_names():
        return
    op.execute("""
        CREATE TABLE assessment_notification_recipients (
          notification_recipient_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
          tenant_id BIGINT UNSIGNED NOT NULL,
          email VARCHAR(150) NOT NULL,
          is_active BOOLEAN NOT NULL DEFAULT TRUE,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          CONSTRAINT fk_assessment_notification_recipient_tenant
            FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
          UNIQUE KEY uq_assessment_notification_recipient (tenant_id, email),
          KEY ix_assessment_notification_recipient_active (tenant_id, is_active)
        ) ENGINE=InnoDB
    """)


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if "assessment_notification_recipients" in inspector.get_table_names():
        op.execute("DROP TABLE assessment_notification_recipients")
