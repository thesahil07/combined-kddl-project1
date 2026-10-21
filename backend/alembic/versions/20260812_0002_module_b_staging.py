"""Add Module B upload staging and employee date of birth.

Revision ID: 20260812_0002
Revises: 20260812_0001
"""

from alembic import op
from sqlalchemy import inspect
import re

revision = "20260812_0002"
down_revision = "20260812_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("employees")}
    if "date_of_birth" not in columns:
        op.execute("ALTER TABLE employees ADD COLUMN date_of_birth DATE NULL AFTER tenure_start_date")
    tables = set(inspector.get_table_names())
    if "employee_upload_batches" not in tables:
        op.execute("""CREATE TABLE employee_upload_batches (
        batch_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        tenant_id BIGINT UNSIGNED NOT NULL, uploaded_by_user_id BIGINT UNSIGNED NOT NULL,
        status ENUM('DRAFT','PUBLISHED','REJECTED') NOT NULL DEFAULT 'DRAFT',
        rejection_reason TEXT NULL, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        published_at DATETIME NULL,
        CONSTRAINT fk_upload_batch_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id),
        CONSTRAINT fk_upload_batch_user FOREIGN KEY (uploaded_by_user_id) REFERENCES users(user_id)
    ) ENGINE=InnoDB""")
    if "employee_upload_rows" not in tables:
        batch_type = str(op.get_bind().exec_driver_sql("SHOW COLUMNS FROM employee_upload_batches LIKE 'batch_id'").first()[1]).upper()
        if not re.fullmatch(r"(?:TINYINT|SMALLINT|MEDIUMINT|INT|BIGINT)(?: UNSIGNED)?", batch_type):
            raise RuntimeError("Unsupported employee_upload_batches.batch_id type")
        op.execute(f"""CREATE TABLE employee_upload_rows (
        upload_row_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, batch_id {batch_type} NOT NULL,
        `row_number` INT UNSIGNED NOT NULL, employee_code VARCHAR(30) NULL, raw_json JSON NOT NULL,
        validation_error TEXT NULL, accepted BOOLEAN NOT NULL DEFAULT FALSE,
        staged_role_title VARCHAR(150) NULL,
        CONSTRAINT fk_upload_row_batch FOREIGN KEY (batch_id) REFERENCES employee_upload_batches(batch_id),
        UNIQUE KEY uq_upload_row_number (batch_id, `row_number`)
    ) ENGINE=InnoDB""")


def downgrade() -> None:
    op.execute("DROP TABLE employee_upload_rows")
    op.execute("DROP TABLE employee_upload_batches")
    op.execute("ALTER TABLE employees DROP COLUMN date_of_birth")
