"""Add a submitted-for-review role-description state.

Revision ID: 20260812_0005
Revises: 20260812_0004
"""

from alembic import op


revision = "20260812_0005"
down_revision = "20260812_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE roles MODIFY description_status ENUM('NOT_STARTED','DRAFT','SUBMITTED','VALIDATED') NOT NULL DEFAULT 'NOT_STARTED'")


def downgrade() -> None:
    op.execute("UPDATE roles SET description_status='DRAFT' WHERE description_status='SUBMITTED'")
    op.execute("ALTER TABLE roles MODIFY description_status ENUM('NOT_STARTED','DRAFT','VALIDATED') NOT NULL DEFAULT 'NOT_STARTED'")
