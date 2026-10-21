"""Idempotently create KDDL's requested tenant/entity leadership hierarchy."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


TENANT_ID = 1


def scalar(connection, statement: str, params: dict[str, object]) -> int:
    value = connection.execute(text(statement), params).scalar_one()
    return int(value)


def ensure_hierarchy() -> None:
    load_dotenv("backend/.env")
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    with engine.begin() as connection:
        taratec_id = scalar(connection, """
            SELECT entity_id FROM entities
            WHERE tenant_id=:tenant_id AND code='TARATEC'
        """, {"tenant_id": TENANT_ID})
        connection.execute(text("""
            INSERT INTO entities (tenant_id, name, code)
            SELECT :tenant_id, 'Corporate', 'CORPORATE'
            WHERE NOT EXISTS (
                SELECT 1 FROM entities WHERE tenant_id=:tenant_id AND code='CORPORATE'
            )
        """), {"tenant_id": TENANT_ID})
        corporate_id = scalar(connection, """
            SELECT entity_id FROM entities
            WHERE tenant_id=:tenant_id AND code='CORPORATE'
        """, {"tenant_id": TENANT_ID})

        for entity_id, name, code in (
            (taratec_id, "Taratec Leadership", "TARATEC-LDR"),
            (corporate_id, "Corporate", "CORPORATE-HQ"),
        ):
            connection.execute(text("""
                INSERT INTO divisions (tenant_id, entity_id, name, code)
                SELECT :tenant_id, :entity_id, :name, :code
                WHERE NOT EXISTS (
                    SELECT 1 FROM divisions WHERE tenant_id=:tenant_id AND code=:code
                )
            """), {"tenant_id": TENANT_ID, "entity_id": entity_id, "name": name, "code": code})

        division_ids = {
            code: scalar(connection, """
                SELECT division_id FROM divisions WHERE tenant_id=:tenant_id AND code=:code
            """, {"tenant_id": TENANT_ID, "code": code})
            for code in ("TARATEC-LDR", "CORPORATE-HQ")
        }
        for division_id in division_ids.values():
            connection.execute(text("""
                INSERT INTO functions (tenant_id, division_id, name)
                SELECT :tenant_id, :division_id, 'Leadership'
                WHERE NOT EXISTS (
                    SELECT 1 FROM functions
                    WHERE tenant_id=:tenant_id AND division_id=:division_id AND name='Leadership'
                )
            """), {"tenant_id": TENANT_ID, "division_id": division_id})

        function_ids = {
            code: scalar(connection, """
                SELECT function_id FROM functions
                WHERE tenant_id=:tenant_id AND division_id=:division_id AND name='Leadership'
            """, {"tenant_id": TENANT_ID, "division_id": division_id})
            for code, division_id in division_ids.items()
        }
        leaders = (
            ("30195", "Rakesh Singh", "Business Head, Dials 1 & 2", "TARATEC-LDR", "30125"),
            ("30120", "Sandeep Gupta", "Commercial Head, Dials 1 & 2", "TARATEC-LDR", "30125"),
            ("30125", "B. Satish", "President, Watch Components Group", "CORPORATE-HQ", None),
        )
        grade_id = scalar(connection, """
            SELECT grade_band_id FROM grade_bands WHERE tenant_id=:tenant_id AND band_code='LM1'
        """, {"tenant_id": TENANT_ID})
        for code, name, title, division_code, _ in leaders:
            division_id = division_ids[division_code]
            function_id = function_ids[division_code]
            connection.execute(text("""
                INSERT INTO roles (tenant_id, division_id, function_id, title)
                SELECT :tenant_id, :division_id, :function_id, :title
                WHERE NOT EXISTS (
                    SELECT 1 FROM roles
                    WHERE tenant_id=:tenant_id AND division_id=:division_id AND title=:title
                )
            """), {"tenant_id": TENANT_ID, "division_id": division_id,
                   "function_id": function_id, "title": title})
            role_id = scalar(connection, """
                SELECT role_id FROM roles
                WHERE tenant_id=:tenant_id AND division_id=:division_id AND title=:title
            """, {"tenant_id": TENANT_ID, "division_id": division_id, "title": title})
            connection.execute(text("""
                INSERT INTO employees (tenant_id, division_id, employee_code, full_name, grade_band_id,
                    designation, function_id, role_id, status)
                VALUES (:tenant_id, :division_id, :employee_code, :full_name, :grade_band_id,
                    :designation, :function_id, :role_id, 'ACTIVE')
                ON DUPLICATE KEY UPDATE division_id=VALUES(division_id), full_name=VALUES(full_name),
                    grade_band_id=VALUES(grade_band_id), designation=VALUES(designation),
                    function_id=VALUES(function_id), role_id=VALUES(role_id), status='ACTIVE'
            """), {"tenant_id": TENANT_ID, "division_id": division_id, "employee_code": code,
                   "full_name": name, "grade_band_id": grade_id, "designation": title,
                   "function_id": function_id, "role_id": role_id})

        for code, _, _, _, manager_code in leaders:
            if manager_code is None:
                continue
            connection.execute(text("""
                UPDATE employees employee
                JOIN employees manager ON manager.tenant_id=employee.tenant_id
                    AND manager.employee_code=:manager_code
                SET employee.manager_employee_id=manager.employee_id
                WHERE employee.tenant_id=:tenant_id AND employee.employee_code=:employee_code
            """), {"tenant_id": TENANT_ID, "employee_code": code, "manager_code": manager_code})


if __name__ == "__main__":
    ensure_hierarchy()
    print("KDDL leadership hierarchy ensured.")
