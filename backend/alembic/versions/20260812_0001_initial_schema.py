"""Create the KDDL schema exactly as reviewed in the source DDL.

Revision ID: 20260812_0001
Revises:
"""

from pathlib import Path
import re

from alembic import op

revision = "20260812_0001"
down_revision = None
branch_labels = None
depends_on = None

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_WORKSPACE_ROOT = _BACKEND_ROOT.parent
_SOURCE = _WORKSPACE_ROOT / "docs" / "kddl-talent-platform-schema.sql"
if not _SOURCE.exists():
    _SOURCE = _BACKEND_ROOT / "docs" / "kddl-talent-platform-schema.sql"


def _schema_statements() -> list[str]:
    """Return DDL only: migration must not install the reference seed data."""
    source = _SOURCE.read_text(encoding="utf-8")
    before_seed_data = source.split("-- 9. SEED DATA", maxsplit=1)[0]
    # A semicolon appears inside an explanatory SQL comment. Strip complete
    # comment lines before splitting so they can never be executed as DDL.
    ddl_only = re.sub(r"(?m)^\s*--.*$", "", before_seed_data)
    statements = [statement.strip() for statement in ddl_only.split(";")]
    return [
        statement
        for statement in statements
        if statement
        and not re.match(r"^(--[\\s\\S]*?\\n)?SET FOREIGN_KEY_CHECKS", statement)
    ]


def upgrade() -> None:
    for statement in _schema_statements():
        op.execute(statement)


def downgrade() -> None:
    bind = op.get_bind()
    tables = [
        "succession_candidates", "assumptions_config", "critical_roles", "priority_score_records",
        "outstanding_assessment_flags", "assessment_line_items", "assessment_forms", "assessment_cycles",
        "audit_log", "ai_generation_log", "ask_dictionary_versions", "desired_level_matrix",
        "functional_skills", "success_behaviours", "proficiency_scale_levels", "vacant_positions",
        "employees", "role_descriptions", "roles", "departments", "functions", "grade_bands",
        "users", "divisions", "tenants",
    ]
    for table in tables:
        bind.exec_driver_sql(f"DROP TABLE IF EXISTS {table}")
