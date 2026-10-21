"""Map each role-definition task to its responsible manager.

Revision ID: 20260813_0006
Revises: 20260812_0005
"""

from alembic import op
from sqlalchemy import inspect


revision = "20260813_0006"
down_revision = "20260812_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "role_definition_assignments" in set(inspect(op.get_bind()).get_table_names()):
        return
    op.execute("""CREATE TABLE role_definition_assignments (
        assignment_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        tenant_id BIGINT UNSIGNED NOT NULL,
        manager_employee_id BIGINT UNSIGNED NOT NULL,
        role_id BIGINT UNSIGNED NOT NULL,
        assigned_by_user_id BIGINT UNSIGNED NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_rd_assignment_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
        CONSTRAINT fk_rd_assignment_manager FOREIGN KEY (manager_employee_id) REFERENCES employees(employee_id),
        CONSTRAINT fk_rd_assignment_role FOREIGN KEY (role_id) REFERENCES roles(role_id),
        CONSTRAINT fk_rd_assignment_actor FOREIGN KEY (assigned_by_user_id) REFERENCES users(user_id),
        UNIQUE KEY uq_rd_assignment_manager_role (tenant_id, manager_employee_id, role_id)
    ) ENGINE=InnoDB""")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS role_definition_assignments")
