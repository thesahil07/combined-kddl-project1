"""Add tenant-scoped entities above divisions."""

from alembic import op
from sqlalchemy import inspect


revision = "20260929_0014"
down_revision = "20260929_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "entities" not in inspector.get_table_names():
        op.execute("""
            CREATE TABLE entities (
                entity_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                tenant_id BIGINT UNSIGNED NOT NULL,
                name VARCHAR(100) NOT NULL,
                code VARCHAR(20) NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_entities_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
                UNIQUE KEY uq_entity_code (tenant_id, code)
            ) ENGINE=InnoDB
        """)
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("divisions")}
    if "entity_id" not in columns:
        op.execute("ALTER TABLE divisions ADD COLUMN entity_id BIGINT UNSIGNED NULL AFTER tenant_id")
        op.execute("ALTER TABLE divisions ADD CONSTRAINT fk_divisions_entity FOREIGN KEY (entity_id) REFERENCES entities(entity_id)")


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("divisions")}
    if "entity_id" in columns:
        op.execute("ALTER TABLE divisions DROP FOREIGN KEY fk_divisions_entity")
        op.execute("ALTER TABLE divisions DROP COLUMN entity_id")
    if "entities" in inspect(op.get_bind()).get_table_names():
        op.execute("DROP TABLE entities")
