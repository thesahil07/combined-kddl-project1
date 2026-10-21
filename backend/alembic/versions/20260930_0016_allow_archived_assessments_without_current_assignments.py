"""Allow historical assessments to retain ratings without current HR assignments."""

from alembic import op


revision = "20260930_0016"
down_revision = "20260929_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A closed-cycle import may pre-date a current role or reporting assignment.
    # Current-cycle assessment creation still validates both fields in the
    # application service; this only preserves historical evidence as supplied.
    op.execute("ALTER TABLE assessment_forms MODIFY role_id BIGINT UNSIGNED NULL")
    op.execute("ALTER TABLE assessment_forms MODIFY manager_employee_id BIGINT UNSIGNED NULL")


def downgrade() -> None:
    # MySQL will safely reject this downgrade while archival rows with unknown
    # historic assignments remain, rather than inventing a role or manager.
    op.execute("ALTER TABLE assessment_forms MODIFY role_id BIGINT UNSIGNED NOT NULL")
    op.execute("ALTER TABLE assessment_forms MODIFY manager_employee_id BIGINT UNSIGNED NOT NULL")
