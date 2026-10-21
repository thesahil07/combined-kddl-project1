"""Add tenant-scoped, skill-specific functional level definitions.

Revision ID: 20261015_0018
Revises: 20261010_0017
"""

from alembic import op
from sqlalchemy import inspect


revision = "20261015_0018"
down_revision = "20261010_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "functional_skill_level_definitions" not in inspector.get_table_names():
        op.execute("""
            CREATE TABLE functional_skill_level_definitions (
              definition_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
              tenant_id BIGINT UNSIGNED NOT NULL,
              skill_id BIGINT UNSIGNED NOT NULL,
              level TINYINT NOT NULL,
              description TEXT NOT NULL,
              CONSTRAINT fk_functional_skill_level_tenant
                FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
              CONSTRAINT fk_functional_skill_level_skill
                FOREIGN KEY (skill_id) REFERENCES functional_skills(skill_id),
              UNIQUE KEY uq_functional_skill_level (tenant_id, skill_id, level)
            ) ENGINE=InnoDB
        """)


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if "functional_skill_level_definitions" in inspector.get_table_names():
        op.execute("DROP TABLE functional_skill_level_definitions")
