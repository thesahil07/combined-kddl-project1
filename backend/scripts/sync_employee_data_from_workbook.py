"""Safely synchronize employee master data from the populated client workbook.

Matches existing records by division plus employee code/name, updates employee
codes in two phases to avoid unique-key collisions, then applies the supplied
role, manager and profile values only when every reference resolves.
"""

from __future__ import annotations

import argparse
import os
import re
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import openpyxl
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


TENANT_ID = 1
DEFAULT_WORKBOOK = Path(
    r"C:\Users\Bhawna Narula\VVNT-Founder\OneDrive - VVNT\WIP_Items"
    r"\Customers - Existing\PGC\FY26\KDDL\KDDL Data"
    r"\Dials_Client Data_Populated_Employee.xlsx"
)


def clean(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def normalized(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean(value).casefold())


def as_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    return value if isinstance(value, date) else None


def division_code(value: object) -> str:
    match = re.search(r"([12])", clean(value))
    if match is None:
        raise ValueError(f"unsupported division value: {value!r}")
    return f"D{match.group(1)}"


def workbook_records(path: Path) -> list[dict[str, object]]:
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = book["Employees"]
        rows = sheet.iter_rows(values_only=True)
        headers = [clean(value) for value in next(rows)]
        records: list[dict[str, object]] = []
        for row_number, row in enumerate(rows, 2):
            values = dict(zip(headers, row, strict=False))
            code = clean(values.get("Employee Code *"))
            if not code:
                continue
            records.append({
                "source_row": row_number,
                "employee_code": code,
                "full_name": clean(values.get("Full Name *")),
                "division_code": division_code(values.get("Division Code *")),
                "grade_code": clean(values.get("Grade Band Code *")),
                "designation": clean(values.get("Designation *")),
                "function_name": clean(values.get("Function Name *")),
                "department_name": clean(values.get("Department Name")),
                "role_title": clean(values.get("Role Title")),
                "manager_name": clean(values.get("Manager")),
                "manager_code": clean(values.get("Manager Employee Code")),
                "date_of_joining": as_date(values.get("Date of Joining")),
                "tenure_start_date": as_date(values.get("Tenure Start Date")),
                "last_promotion_date": as_date(values.get("Last Promotion Date")),
                "retirement_date": as_date(values.get("Retirement Date")),
                "qualification": clean(values.get("Qualification")) or None,
                "status": clean(values.get("Status *")).upper(),
            })
        return records
    finally:
        book.close()


def sync(path: Path, apply: bool) -> dict[str, object]:
    records = workbook_records(path)
    load_dotenv()
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    with engine.begin() as connection:
        divisions = {row["code"]: int(row["division_id"]) for row in connection.execute(text("""
            SELECT division_id, code FROM divisions WHERE tenant_id=:tenant_id
        """), {"tenant_id": TENANT_ID}).mappings()}
        employees = [dict(row) for row in connection.execute(text("""
            SELECT employee_id, division_id, employee_code, full_name
            FROM employees WHERE tenant_id=:tenant_id
        """), {"tenant_id": TENANT_ID}).mappings()]
        by_code = {(row["division_id"], normalized(row["employee_code"])): row for row in employees}
        by_name: dict[tuple[int, str], list[dict[str, object]]] = defaultdict(list)
        for employee in employees:
            by_name[(int(employee["division_id"]), normalized(employee["full_name"]))].append(employee)

        grades = {(normalized(row["band_code"])): int(row["grade_band_id"]) for row in connection.execute(text("""
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
        role_rows: dict[tuple[int, str], list[dict[str, object]]] = defaultdict(list)
        for role in connection.execute(text("""
            SELECT role_id, division_id, title FROM roles WHERE tenant_id=:tenant_id
        """), {"tenant_id": TENANT_ID}).mappings():
            role_rows[(int(role["division_id"]), normalized(role["title"]))].append(dict(role))

        resolved: list[dict[str, object]] = []
        issues: list[str] = []
        for record in records:
            division_id = divisions.get(str(record["division_code"]))
            if division_id is None:
                issues.append(f"row {record['source_row']}: division not found")
                continue
            # Employee code is the workbook's durable identifier.  Names may
            # legitimately change (for example, a correction to a surname),
            # so an exact code is authoritative even when the current name
            # differs.
            existing = by_code.get((division_id, normalized(record["employee_code"])))
            if existing is None:
                candidates = by_name[(division_id, normalized(record["full_name"]))]
                if len(candidates) != 1:
                    issues.append(f"row {record['source_row']}: employee match is missing or ambiguous")
                    continue
                existing = candidates[0]
            grade_id = grades.get(normalized(record["grade_code"]))
            function_id = functions.get((division_id, normalized(record["function_name"])))
            department_id = departments.get((division_id, normalized(record["department_name"])))
            roles = role_rows[(division_id, normalized(record["role_title"]))] if record["role_title"] else []
            if grade_id is None or function_id is None or (record["department_name"] and department_id is None):
                issues.append(f"row {record['source_row']}: grade, function, or department is not mapped")
                continue
            if record["role_title"] and len(roles) != 1:
                issues.append(f"row {record['source_row']}: role is missing or ambiguous")
                continue
            if record["status"] not in {"ACTIVE", "SEPARATED"}:
                issues.append(f"row {record['source_row']}: invalid status")
                continue
            resolved.append({**record, "employee_id": int(existing["employee_id"]), "division_id": division_id,
                             "grade_band_id": grade_id, "function_id": function_id,
                             "department_id": department_id, "role_id": int(roles[0]["role_id"]) if roles else None})

        manager_by_new_code = {(int(record["division_id"]), normalized(record["employee_code"])): int(record["employee_id"])
                               for record in resolved}
        # Employee codes are tenant-unique.  Senior leaders can sit in an
        # entity-level division while managing people in either Dials division,
        # so the established employee-master lookup must not be division-bound.
        manager_by_current_code = {normalized(row["employee_code"]): int(row["employee_id"])
                                   for row in employees}
        for record in resolved:
            manager_code = str(record["manager_code"])
            division_id = int(record["division_id"])
            manager_id = None
            if manager_code:
                manager_id = manager_by_new_code.get((division_id, normalized(manager_code)))
                manager_id = manager_id or manager_by_current_code.get(normalized(manager_code))
            if manager_id is None and record["manager_name"]:
                name_matches = by_name[(division_id, normalized(record["manager_name"]))]
                if len(name_matches) == 1:
                    manager_id = int(name_matches[0]["employee_id"])
            # Some senior managers are listed only as references in this
            # employee workbook. Preserve the established relationship until
            # their own source record is supplied; never erase it on a lookup
            # failure.
            if (manager_code or record["manager_name"]) and manager_id is None:
                issues.append(f"row {record['source_row']}: manager reference is not in the employee master; relationship preserved")
                record["manager_should_update"] = False
            else:
                record["manager_should_update"] = True
            record["manager_employee_id"] = manager_id

        applicable = [record for record in resolved if not any(
            issue.startswith(f"row {record['source_row']}:") and "relationship preserved" not in issue
            for issue in issues
        )]
        applicable_ids = {int(record["employee_id"]) for record in applicable}
        # Never silently take an employee code from an employee outside this
        # source workbook.  This prevents a partial sync from violating the
        # tenant-scoped unique employee-code constraint.
        applicable_codes = {normalized(record["employee_code"]) for record in applicable}
        for employee in employees:
            employee_id = int(employee["employee_id"])
            if employee_id not in applicable_ids and normalized(employee["employee_code"]) in applicable_codes:
                issues.append(
                    f"employee {employee['employee_code']}: target code conflicts with a record outside the safe sync"
                )
        if any(issue.startswith("employee ") for issue in issues):
            applicable = []
            applicable_ids = set()
        code_changes = sum(record["employee_code"] != next(
            employee["employee_code"] for employee in employees if int(employee["employee_id"]) == record["employee_id"]
        ) for record in applicable)
        if apply:
            # Move linked login emails and employee codes through unique,
            # temporary values first. Codes can swap between two people, so
            # direct per-row updates are not safe.
            for employee_id in applicable_ids:
                connection.execute(text("""
                    UPDATE users SET email=CONCAT('SYNC-', employee_id, '@KDDL')
                    WHERE tenant_id=:tenant_id AND employee_id=:employee_id
                """), {"tenant_id": TENANT_ID, "employee_id": employee_id})
            for employee_id in applicable_ids:
                connection.execute(text("""
                    UPDATE employees SET employee_code=CONCAT('SYNC-', employee_id)
                    WHERE tenant_id=:tenant_id AND employee_id=:employee_id
                """), {"tenant_id": TENANT_ID, "employee_id": employee_id})
            for record in applicable:
                connection.execute(text("""
                    UPDATE employees SET employee_code=:employee_code, full_name=:full_name,
                        division_id=:division_id, grade_band_id=:grade_band_id, designation=:designation,
                        function_id=:function_id, department_id=:department_id, role_id=:role_id,
                        manager_employee_id=CASE WHEN :manager_should_update THEN :manager_employee_id ELSE manager_employee_id END,
                        date_of_joining=:date_of_joining,
                        tenure_start_date=:tenure_start_date, last_promotion_date=:last_promotion_date,
                        retirement_date=:retirement_date, qualification=:qualification, status=:status
                    WHERE tenant_id=:tenant_id AND employee_id=:employee_id
                """), {**record, "tenant_id": TENANT_ID})
            for record in applicable:
                connection.execute(text("""
                    UPDATE users SET email=CONCAT(:employee_code, '@KDDL')
                    WHERE tenant_id=:tenant_id AND employee_id=:employee_id
                """), {"tenant_id": TENANT_ID, "employee_id": record["employee_id"],
                           "employee_code": record["employee_code"]})
        return {"source_records": len(records), "resolved": len(resolved), "applicable": len(applicable),
                "code_changes": code_changes, "issues": issues[:100]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(sync(args.workbook, args.apply))


if __name__ == "__main__":
    main()
