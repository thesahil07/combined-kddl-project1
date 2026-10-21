"""Capture the requested people count in the role-definition template.

Revision ID: 20260812_0004
Revises: 20260812_0003
"""

from alembic import op
from sqlalchemy import inspect


revision = "20260812_0004"
down_revision = "20260812_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("role_descriptions")}
    if "people_count" not in columns:
        op.execute("ALTER TABLE role_descriptions ADD COLUMN people_count INT UNSIGNED NULL AFTER version")


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("role_descriptions")}
    if "people_count" in columns:
        op.execute("ALTER TABLE role_descriptions DROP COLUMN people_count")
