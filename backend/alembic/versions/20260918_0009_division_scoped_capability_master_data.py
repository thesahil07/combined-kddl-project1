"""Scope capability master data to a division within its tenant.

Revision ID: 20260918_0009
Revises: 20260918_0008
"""

from alembic import op
from sqlalchemy import inspect


revision = "20260918_0009"
down_revision = "20260918_0008"
branch_labels = None
depends_on = None


def _add_division_column(table: str, after: str) -> None:
    inspector = inspect(op.get_bind())
    if "division_id" not in {column["name"] for column in inspector.get_columns(table)}:
        op.execute(f"ALTER TABLE {table} ADD COLUMN division_id BIGINT UNSIGNED NULL AFTER {after}")


def upgrade() -> None:
    _add_division_column("functions", "tenant_id")
    _add_division_column("departments", "tenant_id")
    _add_division_column("functional_skills", "tenant_id")
    _add_division_column("desired_level_matrix", "tenant_id")

    # Give existing shared rows a source division, using their assigned roles/employees.
    op.execute("""
        UPDATE functions f
        SET division_id = COALESCE(
            (SELECT MIN(r.division_id) FROM roles r WHERE r.tenant_id=f.tenant_id AND r.function_id=f.function_id),
            (SELECT MIN(e.division_id) FROM employees e WHERE e.tenant_id=f.tenant_id AND e.function_id=f.function_id),
            (SELECT MIN(d.division_id) FROM divisions d WHERE d.tenant_id=f.tenant_id)
        )
        WHERE division_id IS NULL
    """)
    op.execute("UPDATE departments d JOIN functions f ON f.function_id=d.function_id SET d.division_id=f.division_id WHERE d.division_id IS NULL")
    op.execute("UPDATE functional_skills s JOIN functions f ON f.function_id=s.function_id SET s.division_id=f.division_id WHERE s.division_id IS NULL")
    op.execute("""
        UPDATE desired_level_matrix m
        LEFT JOIN roles r ON r.role_id=m.role_id
        LEFT JOIN functional_skills s ON m.item_type='SKILL' AND s.skill_id=m.item_id AND s.tenant_id=m.tenant_id
        SET m.division_id=COALESCE(r.division_id, s.division_id, (SELECT MIN(d.division_id) FROM divisions d WHERE d.tenant_id=m.tenant_id))
        WHERE m.division_id IS NULL
    """)

    indexes = {table: {index["name"] for index in inspect(op.get_bind()).get_indexes(table)} for table in ("functions", "departments", "functional_skills", "desired_level_matrix")}
    if "uq_function_name" in indexes["functions"]:
        if "ix_function_tenant_name" not in indexes["functions"]:
            op.execute("ALTER TABLE functions ADD INDEX ix_function_tenant_name (tenant_id, name)")
        op.execute("ALTER TABLE functions DROP INDEX uq_function_name")
    if "uq_skill_code" in indexes["functional_skills"]:
        op.execute("ALTER TABLE functional_skills ADD INDEX ix_skill_tenant_code (tenant_id, code)")
        op.execute("ALTER TABLE functional_skills DROP INDEX uq_skill_code")
    if "uq_matrix_item_band_role" in indexes["desired_level_matrix"]:
        op.execute("ALTER TABLE desired_level_matrix ADD INDEX ix_matrix_item_band_role (tenant_id, item_type, item_id, grade_band_id, role_id)")
        op.execute("ALTER TABLE desired_level_matrix DROP INDEX uq_matrix_item_band_role")
    indexes = {table: {index["name"] for index in inspect(op.get_bind()).get_indexes(table)} for table in indexes}
    if "uq_function_division_name" not in indexes["functions"]:
        op.execute("ALTER TABLE functions ADD UNIQUE KEY uq_function_division_name (tenant_id, division_id, name)")
    if "uq_department_division_function_name" not in indexes["departments"]:
        op.execute("ALTER TABLE departments ADD UNIQUE KEY uq_department_division_function_name (tenant_id, division_id, function_id, name)")
    if "uq_skill_division_code" not in indexes["functional_skills"]:
        op.execute("ALTER TABLE functional_skills ADD UNIQUE KEY uq_skill_division_code (tenant_id, division_id, code)")
    if "uq_matrix_division_item_band_role" not in indexes["desired_level_matrix"]:
        op.execute("ALTER TABLE desired_level_matrix ADD UNIQUE KEY uq_matrix_division_item_band_role (tenant_id, division_id, item_type, item_id, grade_band_id, role_id)")

    # Clone shared functions and departments, then repoint each employee/role to its own division's records.
    op.execute("""
        INSERT INTO functions (tenant_id, division_id, name)
        SELECT DISTINCT f.tenant_id, r.division_id, f.name
        FROM roles r JOIN functions f ON f.function_id=r.function_id
        LEFT JOIN functions target ON target.tenant_id=f.tenant_id AND target.division_id=r.division_id AND target.name=f.name
        WHERE f.division_id<>r.division_id AND target.function_id IS NULL
    """)
    op.execute("""
        INSERT INTO functions (tenant_id, division_id, name)
        SELECT DISTINCT f.tenant_id, e.division_id, f.name
        FROM employees e JOIN functions f ON f.function_id=e.function_id
        LEFT JOIN functions target ON target.tenant_id=f.tenant_id AND target.division_id=e.division_id AND target.name=f.name
        WHERE f.division_id<>e.division_id AND target.function_id IS NULL
    """)
    op.execute("""
        UPDATE roles r JOIN functions current_function ON current_function.function_id=r.function_id
        JOIN functions target_function ON target_function.tenant_id=current_function.tenant_id
            AND target_function.division_id=r.division_id AND target_function.name=current_function.name
        SET r.function_id=target_function.function_id
        WHERE current_function.division_id<>r.division_id
    """)
    op.execute("""
        UPDATE employees e JOIN functions current_function ON current_function.function_id=e.function_id
        JOIN functions target_function ON target_function.tenant_id=current_function.tenant_id
            AND target_function.division_id=e.division_id AND target_function.name=current_function.name
        SET e.function_id=target_function.function_id
        WHERE current_function.division_id<>e.division_id
    """)
    op.execute("""
        INSERT INTO departments (tenant_id, division_id, function_id, name)
        SELECT DISTINCT e.tenant_id, e.division_id, e.function_id, source_department.name
        FROM employees e JOIN departments source_department ON source_department.department_id=e.department_id
        LEFT JOIN departments target_department ON target_department.tenant_id=e.tenant_id
            AND target_department.division_id=e.division_id AND target_department.function_id=e.function_id
            AND target_department.name=source_department.name
        WHERE target_department.department_id IS NULL
    """)
    op.execute("""
        UPDATE employees e JOIN departments source_department ON source_department.department_id=e.department_id
        JOIN departments target_department ON target_department.tenant_id=e.tenant_id
            AND target_department.division_id=e.division_id AND target_department.function_id=e.function_id
            AND target_department.name=source_department.name
        SET e.department_id=target_department.department_id
        WHERE source_department.division_id<>e.division_id OR source_department.function_id<>e.function_id
    """)

    # Functional skills are copied to every division that has the matching function.
    op.execute("""
        INSERT INTO functional_skills (tenant_id, division_id, function_id, department_id, code, name, definition, source, ai_generation_id)
        SELECT s.tenant_id, target_function.division_id, target_function.function_id, target_department.department_id,
               s.code, s.name, s.definition, s.source, s.ai_generation_id
        FROM functional_skills s
        JOIN functions source_function ON source_function.function_id=s.function_id
        JOIN functions target_function ON target_function.tenant_id=s.tenant_id AND target_function.name=source_function.name
            AND target_function.division_id<>s.division_id
        LEFT JOIN departments source_department ON source_department.department_id=s.department_id
        LEFT JOIN departments target_department ON target_department.tenant_id=s.tenant_id
            AND target_department.division_id=target_function.division_id AND target_department.function_id=target_function.function_id
            AND target_department.name=source_department.name
        LEFT JOIN functional_skills existing ON existing.tenant_id=s.tenant_id AND existing.division_id=target_function.division_id
            AND existing.function_id=target_function.function_id AND existing.name=s.name
        WHERE existing.skill_id IS NULL
    """)

    for table in ("functions", "departments", "functional_skills", "desired_level_matrix"):
        op.execute(f"ALTER TABLE {table} MODIFY division_id BIGINT UNSIGNED NOT NULL")
        op.execute(f"ALTER TABLE {table} ADD CONSTRAINT fk_{table}_division FOREIGN KEY (division_id) REFERENCES divisions(division_id)")


def downgrade() -> None:
    # Removing division scope would merge cloned master data and lose provenance.
    pass
