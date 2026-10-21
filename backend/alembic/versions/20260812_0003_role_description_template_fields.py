"""Add the distinct role-definition sections required by the RD template.

Revision ID: 20260812_0003
Revises: 20260812_0002
"""

from alembic import op
from sqlalchemy import inspect


revision = "20260812_0003"
down_revision = "20260812_0002"
branch_labels = None
depends_on = None

_FIELDS = (
    "education_certifications",
    "minimum_relevant_experience",
    "knowledge_required",
    "skills_required",
    "attitudes_behaviours",
)


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("role_descriptions")}
    for field in _FIELDS:
        if field not in columns:
            op.execute(f"ALTER TABLE role_descriptions ADD COLUMN {field} TEXT NULL")
            op.execute(f"UPDATE role_descriptions SET {field} = '' WHERE {field} IS NULL")
            op.execute(f"ALTER TABLE role_descriptions MODIFY COLUMN {field} TEXT NOT NULL")


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("role_descriptions")}
    for field in _FIELDS:
        if field in columns:
            op.execute(f"ALTER TABLE role_descriptions DROP COLUMN {field}")
