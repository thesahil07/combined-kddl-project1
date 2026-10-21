"""Correct desired-level skill references that cross division boundaries."""

from alembic import op


revision = "20260929_0015"
down_revision = "20260929_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Functional skill codes are division-local.  Earlier imports resolved the
    # code without its division, causing D1 desired-level rows to point to D2
    # skills when both divisions used the same code.  The skill's department is
    # likewise the canonical department for a SKILL matrix row.
    op.execute("""
        UPDATE desired_level_matrix matrix_row
        JOIN functional_skills incorrect_skill
          ON incorrect_skill.skill_id = matrix_row.item_id
        JOIN functional_skills correct_skill
          ON correct_skill.tenant_id = matrix_row.tenant_id
         AND correct_skill.division_id = matrix_row.division_id
         AND correct_skill.code = incorrect_skill.code
        SET matrix_row.item_id = correct_skill.skill_id,
            matrix_row.department_id = correct_skill.department_id
        WHERE matrix_row.item_type = 'SKILL'
          AND incorrect_skill.division_id <> matrix_row.division_id
    """)


def downgrade() -> None:
    # The prior incorrect reference cannot be inferred reliably after repair.
    pass
