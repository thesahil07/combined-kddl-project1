"""Keep cycles shared while separating behaviour and skill assessment forms.

Revision ID: 20260918_0008
Revises: 20260918_0007
"""

from alembic import op
from sqlalchemy import inspect


revision = "20260918_0008"
down_revision = "20260918_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    form_columns = {column["name"] for column in inspector.get_columns("assessment_forms")}
    indexes = {index["name"] for index in inspector.get_indexes("assessment_forms")}
    if "uq_form_employee_cycle" in indexes:
        op.execute("ALTER TABLE assessment_forms ADD INDEX ix_form_employee_cycle (cycle_id, employee_id)")
        op.execute("ALTER TABLE assessment_forms DROP INDEX uq_form_employee_cycle")
    if "assessment_type" not in form_columns:
        op.execute("ALTER TABLE assessment_forms ADD COLUMN assessment_type ENUM('BEHAVIOUR','SKILL') NULL AFTER cycle_id")
        op.execute("""
            UPDATE assessment_forms f
            SET assessment_type = CASE
                WHEN EXISTS (SELECT 1 FROM assessment_line_items x WHERE x.form_id=f.form_id AND x.item_type='BEHAVIOUR') THEN 'BEHAVIOUR'
                ELSE 'SKILL'
            END
        """)
        op.execute("""
            INSERT INTO assessment_forms
                (tenant_id, cycle_id, assessment_type, employee_id, role_id, manager_employee_id,
                 skip_manager_employee_id, status, self_assessment_date, behaviour_self_submitted_at,
                 functional_self_submitted_at, manager_assessment_date, behaviour_manager_submitted_at,
                 functional_manager_submitted_at, employee_signed_at, manager_signed_at,
                 skip_manager_signed_at, head_hr_signed_at, created_at, updated_at)
            SELECT f.tenant_id, f.cycle_id, 'SKILL', f.employee_id, f.role_id, f.manager_employee_id,
                   f.skip_manager_employee_id, f.status, f.self_assessment_date, NULL,
                   f.functional_self_submitted_at, f.manager_assessment_date, NULL,
                   f.functional_manager_submitted_at, f.employee_signed_at, f.manager_signed_at,
                   f.skip_manager_signed_at, f.head_hr_signed_at, f.created_at, f.updated_at
            FROM assessment_forms f
            WHERE f.assessment_type='BEHAVIOUR'
              AND EXISTS (SELECT 1 FROM assessment_line_items x WHERE x.form_id=f.form_id AND x.item_type='SKILL')
        """)
        op.execute("""
            UPDATE assessment_line_items ali
            JOIN assessment_forms old_form ON old_form.form_id=ali.form_id AND old_form.assessment_type='BEHAVIOUR'
            JOIN assessment_forms skill_form ON skill_form.tenant_id=old_form.tenant_id
                AND skill_form.cycle_id=old_form.cycle_id AND skill_form.employee_id=old_form.employee_id
                AND skill_form.assessment_type='SKILL'
            SET ali.form_id=skill_form.form_id
            WHERE ali.item_type='SKILL'
        """)
        op.execute("ALTER TABLE assessment_forms MODIFY assessment_type ENUM('BEHAVIOUR','SKILL') NOT NULL")

    op.execute("""
        UPDATE assessment_forms f
        SET assessment_type = CASE
            WHEN EXISTS (SELECT 1 FROM assessment_line_items x WHERE x.form_id=f.form_id AND x.item_type='BEHAVIOUR') THEN 'BEHAVIOUR'
            ELSE 'SKILL'
        END
        WHERE assessment_type IS NULL
    """)
    op.execute("""
        INSERT INTO assessment_forms
            (tenant_id, cycle_id, assessment_type, employee_id, role_id, manager_employee_id,
             skip_manager_employee_id, status, self_assessment_date, behaviour_self_submitted_at,
             functional_self_submitted_at, manager_assessment_date, behaviour_manager_submitted_at,
             functional_manager_submitted_at, employee_signed_at, manager_signed_at,
             skip_manager_signed_at, head_hr_signed_at, created_at, updated_at)
        SELECT f.tenant_id, f.cycle_id, 'SKILL', f.employee_id, f.role_id, f.manager_employee_id,
               f.skip_manager_employee_id, f.status, f.self_assessment_date, NULL,
               f.functional_self_submitted_at, f.manager_assessment_date, NULL,
               f.functional_manager_submitted_at, f.employee_signed_at, f.manager_signed_at,
               f.skip_manager_signed_at, f.head_hr_signed_at, f.created_at, f.updated_at
        FROM assessment_forms f
        WHERE f.assessment_type='BEHAVIOUR'
          AND EXISTS (SELECT 1 FROM assessment_line_items x WHERE x.form_id=f.form_id AND x.item_type='SKILL')
          AND NOT EXISTS (SELECT 1 FROM assessment_forms y WHERE y.tenant_id=f.tenant_id AND y.cycle_id=f.cycle_id AND y.employee_id=f.employee_id AND y.assessment_type='SKILL')
    """)
    op.execute("""
        UPDATE assessment_line_items ali
        JOIN assessment_forms old_form ON old_form.form_id=ali.form_id AND old_form.assessment_type='BEHAVIOUR'
        JOIN assessment_forms skill_form ON skill_form.tenant_id=old_form.tenant_id
            AND skill_form.cycle_id=old_form.cycle_id AND skill_form.employee_id=old_form.employee_id
            AND skill_form.assessment_type='SKILL'
        SET ali.form_id=skill_form.form_id
        WHERE ali.item_type='SKILL'
    """)
    op.execute("ALTER TABLE assessment_forms MODIFY assessment_type ENUM('BEHAVIOUR','SKILL') NOT NULL")
    if "uq_form_employee_cycle_type" not in indexes:
        op.execute("ALTER TABLE assessment_forms ADD UNIQUE KEY uq_form_employee_cycle_type (cycle_id, employee_id, assessment_type)")


def downgrade() -> None:
    # Combining independently submitted forms would discard submission evidence.
    pass
