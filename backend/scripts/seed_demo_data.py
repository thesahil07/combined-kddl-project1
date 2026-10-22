"""Seed safe, fictional local-development data for the KDDL platform.

Run with ``DEMO_SEED_PASSWORD`` set.  This script deliberately contains no
real KDDL data and is safe to run more than once against a local database.
"""

from __future__ import annotations

from os import getenv
from pathlib import Path
import sys

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.infrastructure.security.password_hasher import PasswordHasher


def _id(connection, query: str, **params: object) -> int:
    result = connection.execute(text(query), params).scalar_one_or_none()
    if result is None:
        raise RuntimeError("Expected seed record was not created.")
    return int(result)


def main() -> None:
    password = getenv("DEMO_SEED_PASSWORD", "KddlDemo!2026")
    if not password:
        raise SystemExit("Set DEMO_SEED_PASSWORD before running this script.")
    if not settings.database_url:
        raise SystemExit("DATABASE_URL is not configured.")

    password_hash = PasswordHasher().hash(password)
    engine = create_engine(settings.database_url, pool_pre_ping=True)

    with engine.begin() as connection:
        tenant_id = connection.execute(text("SELECT tenant_id FROM tenants ORDER BY tenant_id LIMIT 1")).scalar_one_or_none()
        if tenant_id is None:
            raise SystemExit("Create a tenant through the onboarding flow before adding demo data.")
        tenant_id = int(tenant_id)

        for name, code in (("Dials 1 - Demo", "D1"), ("Dials 2 - Demo", "D2")):
            connection.execute(text("""
                INSERT INTO divisions (tenant_id, name, code)
                VALUES (:tenant_id, :name, :code)
                ON DUPLICATE KEY UPDATE name = VALUES(name)
            """), {"tenant_id": tenant_id, "name": name, "code": code})
        dials_1 = _id(connection, "SELECT division_id FROM divisions WHERE tenant_id=:tenant_id AND code='D1'", tenant_id=tenant_id)
        dials_2 = _id(connection, "SELECT division_id FROM divisions WHERE tenant_id=:tenant_id AND code='D2'", tenant_id=tenant_id)

        for name in ("Production", "Quality", "Human Resources"):
            connection.execute(text("""
                INSERT INTO functions (tenant_id, name)
                SELECT :tenant_id, :name FROM DUAL
                WHERE NOT EXISTS (SELECT 1 FROM functions WHERE tenant_id=:tenant_id AND name=:name)
            """), {"tenant_id": tenant_id, "name": name})
        production = _id(connection, "SELECT function_id FROM functions WHERE tenant_id=:tenant_id AND name='Production'", tenant_id=tenant_id)
        quality = _id(connection, "SELECT function_id FROM functions WHERE tenant_id=:tenant_id AND name='Quality'", tenant_id=tenant_id)
        hr = _id(connection, "SELECT function_id FROM functions WHERE tenant_id=:tenant_id AND name='Human Resources'", tenant_id=tenant_id)

        for function_id, name in ((production, "Assembly"), (quality, "Quality Assurance"), (hr, "People Operations")):
            connection.execute(text("""
                INSERT INTO departments (tenant_id, function_id, name)
                SELECT :tenant_id, :function_id, :name FROM DUAL
                WHERE NOT EXISTS (
                    SELECT 1 FROM departments
                    WHERE tenant_id=:tenant_id AND function_id=:function_id AND name=:name
                )
            """), {"tenant_id": tenant_id, "function_id": function_id, "name": name})
        assembly = _id(connection, "SELECT department_id FROM departments WHERE tenant_id=:tenant_id AND function_id=:function_id AND name='Assembly'", tenant_id=tenant_id, function_id=production)
        qa = _id(connection, "SELECT department_id FROM departments WHERE tenant_id=:tenant_id AND function_id=:function_id AND name='Quality Assurance'", tenant_id=tenant_id, function_id=quality)
        people_ops = _id(connection, "SELECT department_id FROM departments WHERE tenant_id=:tenant_id AND function_id=:function_id AND name='People Operations'", tenant_id=tenant_id, function_id=hr)
        m2 = _id(connection, "SELECT grade_band_id FROM grade_bands WHERE tenant_id=:tenant_id AND band_code='M2'", tenant_id=tenant_id)
        e2 = _id(connection, "SELECT grade_band_id FROM grade_bands WHERE tenant_id=:tenant_id AND band_code='E2'", tenant_id=tenant_id)
        e3 = _id(connection, "SELECT grade_band_id FROM grade_bands WHERE tenant_id=:tenant_id AND band_code='E3'", tenant_id=tenant_id)

        role_specs = (
            (dials_1, production, "Production Manager"),
            (dials_1, production, "Production Engineer"),
            (dials_2, quality, "Quality Manager"),
            (dials_2, quality, "Quality Analyst"),
            (dials_1, hr, "HR Business Partner"),
        )
        for division_id, function_id, title in role_specs:
            existing = connection.execute(text("""
                SELECT role_id FROM roles
                WHERE tenant_id=:tenant_id AND division_id=:division_id AND function_id=:function_id AND title=:title
                LIMIT 1
            """), {"tenant_id": tenant_id, "division_id": division_id, "function_id": function_id, "title": title}).scalar_one_or_none()
            if existing is None:
                connection.execute(text("""
                    INSERT INTO roles (tenant_id, division_id, function_id, title)
                    VALUES (:tenant_id, :division_id, :function_id, :title)
                """), {"tenant_id": tenant_id, "division_id": division_id, "function_id": function_id, "title": title})

        def role_id(division_id: int, function_id: int, title: str) -> int:
            return _id(connection, """
                SELECT role_id FROM roles WHERE tenant_id=:tenant_id AND division_id=:division_id
                AND function_id=:function_id AND title=:title LIMIT 1
            """, tenant_id=tenant_id, division_id=division_id, function_id=function_id, title=title)

        production_manager = role_id(dials_1, production, "Production Manager")
        production_engineer = role_id(dials_1, production, "Production Engineer")
        quality_manager = role_id(dials_2, quality, "Quality Manager")
        quality_analyst = role_id(dials_2, quality, "Quality Analyst")
        hr_partner = role_id(dials_1, hr, "HR Business Partner")

        employees = (
            ("DEMO-100", "Asha Verma", dials_1, m2, "Production Manager", production, assembly, production_manager, None),
            ("DEMO-101", "Dev Malhotra", dials_1, e2, "Production Engineer", production, assembly, production_engineer, "DEMO-100"),
            ("DEMO-102", "Nisha Kapoor", dials_2, m2, "Quality Manager", quality, qa, quality_manager, None),
            ("DEMO-103", "Kabir Singh", dials_2, e2, "Quality Analyst", quality, qa, quality_analyst, "DEMO-102"),
            ("DEMO-104", "Sunita Joshi", dials_1, e3, "HR Business Partner", hr, people_ops, hr_partner, None),
            # Fictional direct reports for the local Skip Manager dashboard.
            ("DEMO-105", "Meera Iyer", dials_2, e2, "Quality Analyst", quality, qa, quality_analyst, "DEMO-102"),
            ("DEMO-106", "Arjun Mehta", dials_2, e3, "Quality Analyst", quality, qa, quality_analyst, "DEMO-102"),
            ("DEMO-107", "Priya Nair", dials_2, e2, "Quality Analyst", quality, qa, quality_analyst, "DEMO-102"),
        )
        for code, name, division_id, grade_band_id, designation, function_id, department_id, assigned_role_id, manager_code in employees:
            manager_id = None if manager_code is None else _id(connection, "SELECT employee_id FROM employees WHERE tenant_id=:tenant_id AND employee_code=:code", tenant_id=tenant_id, code=manager_code)
            connection.execute(text("""
                INSERT INTO employees (
                    tenant_id, division_id, employee_code, full_name, grade_band_id, designation,
                    function_id, department_id, role_id, manager_employee_id, status
                ) VALUES (
                    :tenant_id, :division_id, :code, :name, :grade_band_id, :designation,
                    :function_id, :department_id, :role_id, :manager_employee_id, 'ACTIVE'
                ) ON DUPLICATE KEY UPDATE
                    full_name=VALUES(full_name), designation=VALUES(designation), role_id=VALUES(role_id),
                    manager_employee_id=VALUES(manager_employee_id), status='ACTIVE'
            """), {"tenant_id": tenant_id, "division_id": division_id, "code": code, "name": name,
                  "grade_band_id": grade_band_id, "designation": designation, "function_id": function_id,
                  "department_id": department_id, "role_id": assigned_role_id, "manager_employee_id": manager_id})

        asha = _id(connection, "SELECT employee_id FROM employees WHERE tenant_id=:tenant_id AND employee_code='DEMO-100'", tenant_id=tenant_id)
        dev = _id(connection, "SELECT employee_id FROM employees WHERE tenant_id=:tenant_id AND employee_code='DEMO-101'", tenant_id=tenant_id)
        nisha = _id(connection, "SELECT employee_id FROM employees WHERE tenant_id=:tenant_id AND employee_code='DEMO-102'", tenant_id=tenant_id)
        sunita = _id(connection, "SELECT employee_id FROM employees WHERE tenant_id=:tenant_id AND employee_code='DEMO-104'", tenant_id=tenant_id)
        users = (
            ("pgc.admin@demo.kddl.local", "PGC_ADMIN", None, None, None),
            ("hr.spoc@demo.kddl.local", "HR_SPOC", sunita, dials_1, tenant_id),
            ("hod.manager@demo.kddl.local", "HOD_MANAGER", asha, None, tenant_id),
            ("employee@demo.kddl.local", "EMPLOYEE", dev, None, tenant_id),
            ("skip.manager@demo.kddl.local", "SKIP_MANAGER", nisha, None, tenant_id),
            ("sponsor.viewer@demo.kddl.local", "SPONSOR_VIEWER", None, None, tenant_id),
        )
        for email, role, employee_id, division_scope_id, user_tenant_id in users:
            connection.execute(text("""
                INSERT INTO users (tenant_id, email, password_hash, role, employee_id, division_scope_id, status)
                VALUES (:tenant_id, :email, :password_hash, :role, :employee_id, :division_scope_id, 'ACTIVE')
                ON DUPLICATE KEY UPDATE password_hash=VALUES(password_hash), role=VALUES(role),
                    employee_id=VALUES(employee_id), division_scope_id=VALUES(division_scope_id), status='ACTIVE'
            """), {"tenant_id": user_tenant_id, "email": email, "password_hash": password_hash,
            "role": role, "employee_id": employee_id, "division_scope_id": division_scope_id})

        # Fictional local assessment fixture for the Skip Manager view.  These
        # values demonstrate the two independent assessment grids only; they
        # are not KDDL employee data and must not be used outside local dev.
        ask_version = connection.execute(text("""
            SELECT version_id FROM ask_dictionary_versions
            WHERE tenant_id = :tenant_id ORDER BY version_no LIMIT 1
        """), {"tenant_id": tenant_id}).scalar_one_or_none()
        if ask_version is None:
            connection.execute(text("""
                INSERT INTO ask_dictionary_versions (tenant_id, version_no, status)
                VALUES (:tenant_id, 1, 'APPROVED')
            """), {"tenant_id": tenant_id})
            ask_version = _id(connection, "SELECT version_id FROM ask_dictionary_versions WHERE tenant_id=:tenant_id AND version_no=1", tenant_id=tenant_id)

        cycle_id = connection.execute(text("""
            SELECT cycle_id FROM assessment_cycles
            WHERE tenant_id = :tenant_id AND name = 'FY2026 Demo Assessment'
            LIMIT 1
        """), {"tenant_id": tenant_id}).scalar_one_or_none()
        if cycle_id is None:
            connection.execute(text("""
                INSERT INTO assessment_cycles (tenant_id, name, ask_version_id, period_start, period_end, status)
                VALUES (:tenant_id, 'FY2026 Demo Assessment', :ask_version_id, '2026-04-01', '2027-03-31', 'IN_PROGRESS')
            """), {"tenant_id": tenant_id, "ask_version_id": ask_version})
            cycle_id = _id(connection, "SELECT cycle_id FROM assessment_cycles WHERE tenant_id=:tenant_id AND name='FY2026 Demo Assessment'", tenant_id=tenant_id)

        skill_specs = (
            ("Q001", "Root Cause Analysis", "Uses structured analysis to identify causes of quality issues."),
            ("Q002", "Process Quality Control", "Applies quality-control methods consistently in day-to-day work."),
            ("Q003", "Quality Systems", "Uses documented quality systems and improvement practices."),
        )
        for code, name, definition in skill_specs:
            connection.execute(text("""
                INSERT INTO functional_skills (tenant_id, function_id, code, name, definition, source)
                SELECT :tenant_id, :function_id, :code, :name, :definition, 'MANUAL' FROM DUAL
                WHERE NOT EXISTS (SELECT 1 FROM functional_skills WHERE tenant_id=:tenant_id AND code=:code)
            """), {"tenant_id": tenant_id, "function_id": quality, "code": code, "name": name, "definition": definition})

        behaviour_items = connection.execute(text("""
            SELECT behaviour_id FROM success_behaviours WHERE tenant_id=:tenant_id ORDER BY code
        """), {"tenant_id": tenant_id}).scalars().all()
        skill_items = connection.execute(text("""
            SELECT skill_id FROM functional_skills WHERE tenant_id=:tenant_id AND function_id=:function_id ORDER BY code
        """), {"tenant_id": tenant_id, "function_id": quality}).scalars().all()
        level_patterns = ((3, 2, 2), (3, 3, 2), (3, 2, 3), (3, 3, 3))
        for employee_index, employee_code in enumerate(("DEMO-103", "DEMO-105", "DEMO-106", "DEMO-107")):
            employee_id = _id(connection, "SELECT employee_id FROM employees WHERE tenant_id=:tenant_id AND employee_code=:code", tenant_id=tenant_id, code=employee_code)
            employee_role_id = _id(connection, "SELECT role_id FROM employees WHERE tenant_id=:tenant_id AND employee_id=:employee_id", tenant_id=tenant_id, employee_id=employee_id)
            form_id = connection.execute(text("""
                SELECT form_id FROM assessment_forms WHERE cycle_id=:cycle_id AND employee_id=:employee_id
            """), {"cycle_id": cycle_id, "employee_id": employee_id}).scalar_one_or_none()
            if form_id is None:
                connection.execute(text("""
                    INSERT INTO assessment_forms (tenant_id, cycle_id, employee_id, role_id, manager_employee_id,
                                                  skip_manager_employee_id, status, self_assessment_date, manager_assessment_date)
                    VALUES (:tenant_id, :cycle_id, :employee_id, :role_id, :manager_employee_id,
                            :skip_manager_employee_id, 'MANAGER_SUBMITTED', '2026-07-10', '2026-07-14')
                """), {"tenant_id": tenant_id, "cycle_id": cycle_id, "employee_id": employee_id,
                      "role_id": employee_role_id, "manager_employee_id": nisha, "skip_manager_employee_id": nisha})
                form_id = _id(connection, "SELECT form_id FROM assessment_forms WHERE cycle_id=:cycle_id AND employee_id=:employee_id", cycle_id=cycle_id, employee_id=employee_id)
            desired, self_level, manager_level = level_patterns[employee_index]
            for item_id in behaviour_items:
                connection.execute(text("""
                    INSERT INTO assessment_line_items (form_id, item_type, item_id, desired_level, self_assessment_level, manager_assessment_level)
                    VALUES (:form_id, 'BEHAVIOUR', :item_id, :desired_level, :self_level, :manager_level)
                    ON DUPLICATE KEY UPDATE desired_level=VALUES(desired_level), self_assessment_level=VALUES(self_assessment_level), manager_assessment_level=VALUES(manager_assessment_level)
                """), {"form_id": form_id, "item_id": item_id, "desired_level": desired,
                      "self_level": self_level, "manager_level": manager_level})
            for skill_index, item_id in enumerate(skill_items):
                connection.execute(text("""
                    INSERT INTO assessment_line_items (form_id, item_type, item_id, desired_level, self_assessment_level, manager_assessment_level)
                    VALUES (:form_id, 'SKILL', :item_id, :desired_level, :self_level, :manager_level)
                    ON DUPLICATE KEY UPDATE desired_level=VALUES(desired_level), self_assessment_level=VALUES(self_assessment_level), manager_assessment_level=VALUES(manager_assessment_level)
                """), {"form_id": form_id, "item_id": item_id, "desired_level": 3,
                      "self_level": max(1, self_level - (skill_index % 2)), "manager_level": max(1, manager_level - (skill_index % 2))})

        pgc_user_id = _id(connection, "SELECT user_id FROM users WHERE email='pgc.admin@demo.kddl.local'")
        # Local demo convenience: map every existing tenant role to the demo
        # Skip Manager. Production mappings must be created by an authorised
        # assignment workflow, never automatically inferred from reporting lines.
        connection.execute(text("""
            INSERT INTO role_definition_assignments (tenant_id, manager_employee_id, role_id, assigned_by_user_id)
            SELECT :tenant_id, :manager_employee_id, r.role_id, :assigned_by_user_id
            FROM roles r
            WHERE r.tenant_id = :tenant_id
            ON DUPLICATE KEY UPDATE assigned_by_user_id=VALUES(assigned_by_user_id)
        """), {"tenant_id": tenant_id, "manager_employee_id": nisha,
              "assigned_by_user_id": pgc_user_id})

        skip_manager_user_id = _id(connection, "SELECT user_id FROM users WHERE email='skip.manager@demo.kddl.local'")
        connection.execute(text("""
            INSERT INTO admin_console_access (tenant_id, user_id, granted_by_user_id)
            VALUES (:tenant_id, :user_id, :granted_by_user_id)
            ON DUPLICATE KEY UPDATE tenant_id=tenant_id
        """), {"tenant_id": tenant_id, "user_id": skip_manager_user_id, "granted_by_user_id": pgc_user_id})

    print("Seeded fictional demo data: 6 users, 8 employees, 2 divisions, and sample assessment matrices.")


if __name__ == "__main__":
    main()
