"""Scope functional skills and preserve independent section submission states.

Revision ID: 20260918_0007
Revises: 20260813_0006
"""

from alembic import op
from sqlalchemy import inspect


revision = "20260918_0007"
down_revision = "20260813_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    form_columns = {column["name"] for column in inspector.get_columns("assessment_forms")}
    skill_columns = {column["name"] for column in inspector.get_columns("functional_skills")}
    matrix_columns = {column["name"] for column in inspector.get_columns("desired_level_matrix")}
    if "department_id" not in skill_columns:
        op.execute("ALTER TABLE functional_skills ADD COLUMN department_id BIGINT UNSIGNED NULL AFTER function_id")
        op.execute("ALTER TABLE functional_skills ADD CONSTRAINT fk_skill_department FOREIGN KEY (department_id) REFERENCES departments(department_id)")
    if "department_id" not in matrix_columns:
        op.execute("ALTER TABLE desired_level_matrix ADD COLUMN department_id BIGINT UNSIGNED NULL AFTER role_id")
        op.execute("ALTER TABLE desired_level_matrix ADD CONSTRAINT fk_matrix_department FOREIGN KEY (department_id) REFERENCES departments(department_id)")
    for column in ("behaviour_self_submitted_at", "functional_self_submitted_at", "behaviour_manager_submitted_at", "functional_manager_submitted_at"):
        if column not in form_columns:
            op.execute(f"ALTER TABLE assessment_forms ADD COLUMN {column} DATETIME NULL")
    op.execute("""
        UPDATE assessment_forms af
        SET behaviour_self_submitted_at = CASE WHEN EXISTS (SELECT 1 FROM assessment_line_items x WHERE x.form_id=af.form_id AND x.item_type='BEHAVIOUR') AND NOT EXISTS (SELECT 1 FROM assessment_line_items x WHERE x.form_id=af.form_id AND x.item_type='BEHAVIOUR' AND x.self_assessment_level IS NULL) THEN COALESCE(af.self_assessment_date, af.updated_at) END,
            functional_self_submitted_at = CASE WHEN EXISTS (SELECT 1 FROM assessment_line_items x WHERE x.form_id=af.form_id AND x.item_type='SKILL') AND NOT EXISTS (SELECT 1 FROM assessment_line_items x WHERE x.form_id=af.form_id AND x.item_type='SKILL' AND x.self_assessment_level IS NULL) THEN COALESCE(af.self_assessment_date, af.updated_at) END,
            behaviour_manager_submitted_at = CASE WHEN EXISTS (SELECT 1 FROM assessment_line_items x WHERE x.form_id=af.form_id AND x.item_type='BEHAVIOUR') AND NOT EXISTS (SELECT 1 FROM assessment_line_items x WHERE x.form_id=af.form_id AND x.item_type='BEHAVIOUR' AND x.manager_assessment_level IS NULL) THEN COALESCE(af.manager_assessment_date, af.updated_at) END,
            functional_manager_submitted_at = CASE WHEN EXISTS (SELECT 1 FROM assessment_line_items x WHERE x.form_id=af.form_id AND x.item_type='SKILL') AND NOT EXISTS (SELECT 1 FROM assessment_line_items x WHERE x.form_id=af.form_id AND x.item_type='SKILL' AND x.manager_assessment_level IS NULL) THEN COALESCE(af.manager_assessment_date, af.updated_at) END
    """)


def downgrade() -> None:
    # Submission evidence must remain recoverable; this additive migration is intentionally non-destructive.
    pass
