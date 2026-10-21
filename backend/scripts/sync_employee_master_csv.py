"""Synchronize the KDDL employee master CSV and provision accounts for new people.

The CSV is treated as tenant-scoped employee-master data.  Employee codes are
the primary match key; a unique division/name match supports a supplied code
correction.  Manager relationships are applied after all employee rows exist,
so cross-division entity leaders can be selected safely.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from app.infrastructure.security.password_hasher import PasswordHasher


TENANT_ID = 1
DEFAULT_CSV = Path(r"C:\Users\Bhawna Narula\Downloads\Talent_Client_Data_Template_Populated_FINAL (1)(Employees).csv")
ONBOARDING_PASSWORD = "KddlDemo!2026"


def clean(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def normalized(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean(value).casefold())


def parse_date(value: object):
    source = clean(value)
    if not source:
        return None
    for pattern in ("%d-%b-%Y", "%d-%b-%y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(source, pattern).date()
        except ValueError:
            pass
    raise ValueError(f"unsupported date: {source}")


def division_code(value: object) -> str:
    match = re.search(r"([12])", clean(value))
    if match is None:
        raise ValueError(f"unsupported division: {value!r}")
    return f"D{match.group(1)}"


def read_records(path: Path) -> list[dict[str, object]]:
    # The client export is Windows-1252 encoded; this retains characters such
    # as en-dashes without silently replacing them.
    with path.open(encoding="cp1252", newline="") as source:
        rows = csv.DictReader(source)
        records: list[dict[str, object]] = []
        for row_number, row in enumerate(rows, 2):
            code = clean(row.get("Employee Code *"))
            if not code:
                continue
            records.append({
                "source_row": row_number,
                "employee_code": code,
                "full_name": clean(row.get("Full Name *")),
                "division_code": division_code(row.get("Division Code *")),
                "grade_code": clean(row.get("Grade Band Code *")),
                "designation": clean(row.get("Designation *")),
                "function_name": clean(row.get("Function Name *")),
                "department_name": clean(row.get("Department Name")),
                "role_title": clean(row.get("Role Title")),
                "manager_code": clean(row.get("Manager Employee Code")),
                "date_of_birth": parse_date(row.get("Date of Birth")),
                "date_of_joining": parse_date(row.get("Date of Joining")),
                "tenure_start_date": parse_date(row.get("Tenure Start Date")),
                "last_promotion_date": parse_date(row.get("Last Promotion Date")),
                "retirement_date": parse_date(row.get("Retirement Date")),
                "qualification": clean(row.get("Qualification")) or None,
                "status": clean(row.get("Status *")).upper(),
            })
        return records


def sync(path: Path, apply: bool) -> dict[str, object]:
    records = read_records(path)
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    with engine.begin() as connection:
        divisions = {str(row["code"]): int(row["division_id"]) for row in connection.execute(text("""
            SELECT division_id, code FROM divisions WHERE tenant_id=:tenant_id
        """), {"tenant_id": TENANT_ID}).mappings()}
        employee_rows = [dict(row) for row in connection.execute(text("""
            SELECT employee_id, division_id, employee_code, full_name FROM employees WHERE tenant_id=:tenant_id
        """), {"tenant_id": TENANT_ID}).mappings()]
        by_code = {normalized(row["employee_code"]): row for row in employee_rows}
        by_name: dict[tuple[int, str], list[dict[str, object]]] = {}
        for employee in employee_rows:
            by_name.setdefault((int(employee["division_id"]), normalized(employee["full_name"])), []).append(employee)
        grades = {normalized(row["band_code"]): int(row["grade_band_id"]) for row in connection.execute(text("""
            SELECT grade_band_id, band_code FROM grade_bands WHERE tenant_id=:tenant_id
        """), {"tenant_id": TENANT_ID}).mappings()}
        functions = {(int(row["division_id"]), normalized(row["name"])): int(row["function_id"])
                     for row in connection.execute(text("""
            SELECT function_id, division_id, name FROM functions WHERE tenant_id=:tenant_id
        """), {"tenant_id": TENANT_ID}).mappings()}
        departments = {(int(row["division_id"]), normalized(row["name"])): int(row["department_id"])
                       for row in connection.execute(text("""
            SELECT department_id, division_id, name FROM departments WHERE tenant_id=:tenant_id
        """), {"tenant_id": TENANT_ID}).mappings()}
        roles = {(int(row["division_id"]), normalized(row["title"])): int(row["role_id"])
                 for row in connection.execute(text("""
            SELECT role_id, division_id, title FROM roles WHERE tenant_id=:tenant_id
        """), {"tenant_id": TENANT_ID}).mappings()}

        resolved: list[dict[str, object]] = []
        issues: list[str] = []
        for record in records:
            division_id = divisions.get(str(record["division_code"]))
            existing = by_code.get(normalized(record["employee_code"]))
            if existing is None:
                matches = by_name.get((division_id or 0, normalized(record["full_name"])), [])
                if len(matches) != 1:
                    issues.append(f"row {record['source_row']}: employee match is missing or ambiguous")
                    continue
                existing = matches[0]
            grade_id = grades.get(normalized(record["grade_code"]))
            function_id = functions.get((division_id or 0, normalized(record["function_name"])))
            department_id = departments.get((division_id or 0, normalized(record["department_name"]))) if record["department_name"] else None
            role_id = roles.get((division_id or 0, normalized(record["role_title"]))) if record["role_title"] else None
            if division_id is None or grade_id is None or function_id is None or (record["department_name"] and department_id is None) or (record["role_title"] and role_id is None) or record["status"] not in {"ACTIVE", "SEPARATED"}:
                issues.append(f"row {record['source_row']}: organisational mapping is missing or invalid")
                continue
            resolved.append({**record, "employee_id": int(existing["employee_id"]) if existing else None,
                             "division_id": division_id, "grade_band_id": grade_id, "function_id": function_id,
                             "department_id": department_id, "role_id": role_id})

        manager_ids = {normalized(row["employee_code"]): int(row["employee_id"]) for row in employee_rows}
        manager_ids.update({normalized(row["employee_code"]): int(row["employee_id"])
                            for row in resolved if row["employee_id"] is not None})
        for record in resolved:
            manager_code = str(record["manager_code"])
            record["manager_employee_id"] = manager_ids.get(normalized(manager_code)) if manager_code else None
            if manager_code and record["manager_employee_id"] is None:
                issues.append(f"row {record['source_row']}: manager code {manager_code} is missing")

        applicable = [record for record in resolved if not any(issue.startswith(f"row {record['source_row']}:") for issue in issues)]
        new_records = [record for record in applicable if record["employee_id"] is None]
        if apply:
            for record in new_records:
                result = connection.execute(text("""
                    INSERT INTO employees (tenant_id, division_id, employee_code, full_name, grade_band_id,
                        designation, function_id, department_id, role_id, manager_employee_id, date_of_birth,
                        date_of_joining, tenure_start_date, last_promotion_date, retirement_date, qualification, status)
                    VALUES (:tenant_id, :division_id, :employee_code, :full_name, :grade_band_id,
                        :designation, :function_id, :department_id, :role_id, :manager_employee_id, :date_of_birth,
                        :date_of_joining, :tenure_start_date, :last_promotion_date, :retirement_date, :qualification, :status)
                """), {**record, "tenant_id": TENANT_ID})
                record["employee_id"] = int(result.lastrowid)
            for record in applicable:
                connection.execute(text("""
                    UPDATE employees SET division_id=:division_id, employee_code=:employee_code,
                        full_name=:full_name, grade_band_id=:grade_band_id, designation=:designation,
                        function_id=:function_id, department_id=:department_id, role_id=:role_id,
                        manager_employee_id=:manager_employee_id, date_of_birth=:date_of_birth,
                        date_of_joining=:date_of_joining, tenure_start_date=:tenure_start_date,
                        last_promotion_date=:last_promotion_date, retirement_date=:retirement_date,
                        qualification=:qualification, status=:status
                    WHERE tenant_id=:tenant_id AND employee_id=:employee_id
                """), {**record, "tenant_id": TENANT_ID})
            user_employee_ids = {int(row["employee_id"]) for row in connection.execute(text("""
                SELECT employee_id FROM users WHERE tenant_id=:tenant_id AND employee_id IS NOT NULL
            """), {"tenant_id": TENANT_ID}).mappings()}
            password_hash = PasswordHasher().hash(ONBOARDING_PASSWORD)
            for record in new_records:
                connection.execute(text("""
                    INSERT INTO users (tenant_id, email, password_hash, role, employee_id, status)
                    VALUES (:tenant_id, :email, :password_hash, 'EMPLOYEE', :employee_id, 'ACTIVE')
                """), {"tenant_id": TENANT_ID, "email": f"{record['employee_code']}@KDDL",
                           "password_hash": password_hash, "employee_id": record["employee_id"]})
            # Existing accounts follow employee-code login names without replacing passwords.
            for record in applicable:
                if int(record["employee_id"]) in user_employee_ids:
                    connection.execute(text("""
                        UPDATE users SET email=:email WHERE tenant_id=:tenant_id AND employee_id=:employee_id
                    """), {"tenant_id": TENANT_ID, "employee_id": record["employee_id"],
                           "email": f"{record['employee_code']}@KDDL"})
        return {"source_records": len(records), "resolved": len(resolved), "applied": len(applicable),
                "new_employees": len(new_records), "issues": issues[:100]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()
    print(sync(arguments.csv, arguments.apply))
