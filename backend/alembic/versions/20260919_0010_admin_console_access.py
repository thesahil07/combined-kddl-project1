"""Add user-level access grants for the assessment administration console."""

from alembic import op
from sqlalchemy import inspect


revision = "20260919_0010"
down_revision = "20260918_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "admin_console_access" in inspect(op.get_bind()).get_table_names():
        return
    op.execute("""
        CREATE TABLE admin_console_access (
            access_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            tenant_id BIGINT UNSIGNED NOT NULL,
            user_id BIGINT UNSIGNED NOT NULL,
            granted_by_user_id BIGINT UNSIGNED NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_admin_console_access_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
            CONSTRAINT fk_admin_console_access_user FOREIGN KEY (user_id) REFERENCES users(user_id),
            CONSTRAINT fk_admin_console_access_granted_by FOREIGN KEY (granted_by_user_id) REFERENCES users(user_id),
            UNIQUE KEY uq_admin_console_access_user (tenant_id, user_id)
        ) ENGINE=InnoDB
    """)


def downgrade() -> None:
    if "admin_console_access" in inspect(op.get_bind()).get_table_names():
        op.execute("DROP TABLE admin_console_access")
