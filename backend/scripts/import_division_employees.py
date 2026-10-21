"""Import user-supplied employee records and reporting lines into one division."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings


def clean(value: str | None) -> str:
    return (value or "").strip()


def key(value: str) -> str:
    return " ".join(clean(value).lower().replace(".", "").split())


def parsed_date(value: str) -> str | None:
    value = clean(value)
    if not value:
        return None
    if any(character.isalpha() for character in value):
        return datetime.strptime(value, "%d-%b-%Y").date().isoformat()
    first, second, year = (int(part) for part in value.split("-"))
    date_format = "%m-%d-%Y" if second > 12 else "%d-%m-%Y"
    return datetime.strptime(f"{first:02d}-{second:02d}-{year:04d}", date_format).date().isoformat()


def load_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return [{column: clean(value) for column, value in row.items()} for row in csv.DictReader(file, delimiter="\t")]


def get_or_create(connection, select_sql: str, insert_sql: str, params: dict[str, object]) -> int:
    value = connection.execute(text(select_sql), params).scalar_one_or_none()
    return int(value) if value is not None else int(connection.execute(text(insert_sql), params).lastrowid)


def import_employees(
    employees_path: Path, managers_path: Path, tenant_id: int, division_id: int, dry_run: bool
) -> dict[str, object]:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    employees, mappings = load_tsv(employees_path), load_tsv(managers_path)
    required = {"Name of Employee", "Function", "Department", "Designation", "Grade", "Date of Joining KDDL"}
    if not employees or required.difference(employees[0]) or not ({"Role", "Process/Role"} & set(employees[0])):
        raise ValueError("employee file has missing required columns")
    engine = create_engine(settings.database_url)
    counts: dict[str, object] = {"employees_created": 0, "employees_existing": 0, "manager_links": 0, "unresolved_managers": []}
    aliases = {
        key(row["Employee"]): (key(row["Source Name"]), key(row.get("Source Function")))
        for row in mappings if clean(row.get("Source Name"))
    }
    manager_by_employee = {key(row["Employee"]): clean(row["Manager"]) for row in mappings}
    with engine.begin() as connection:
        division_ok = connection.execute(text("SELECT division_id FROM divisions WHERE tenant_id=:tenant_id AND division_id=:division_id"), {"tenant_id": tenant_id, "division_id": division_id}).scalar_one_or_none()
        if division_ok is None:
            raise ValueError("division is not in the tenant")
        people: dict[tuple[str, str], int] = {}
        for sequence, row in enumerate(employees, start=1):
            name, function_name, department_name = (clean(row[field]) for field in ("Name of Employee", "Function", "Department"))
            role_title = clean(row.get("Role") or row.get("Process/Role") or row.get("Designation"))
            grade = clean(row["Grade"]).replace("-", "").upper()
            if not all((name, function_name, department_name, role_title, grade)):
                raise ValueError(f"incomplete employee row for {name or 'unknown'}")
            function_id = get_or_create(connection, "SELECT function_id FROM functions WHERE tenant_id=:tenant_id AND division_id=:division_id AND name=:name", "INSERT INTO functions (tenant_id, division_id, name) VALUES (:tenant_id, :division_id, :name)", {"tenant_id": tenant_id, "division_id": division_id, "name": function_name})
            department_id = get_or_create(connection, "SELECT department_id FROM departments WHERE tenant_id=:tenant_id AND division_id=:division_id AND function_id=:function_id AND name=:name", "INSERT INTO departments (tenant_id, division_id, function_id, name) VALUES (:tenant_id, :division_id, :function_id, :name)", {"tenant_id": tenant_id, "division_id": division_id, "function_id": function_id, "name": department_name})
            role_id = get_or_create(connection, "SELECT role_id FROM roles WHERE tenant_id=:tenant_id AND division_id=:division_id AND function_id=:function_id AND title=:title LIMIT 1", "INSERT INTO roles (tenant_id, division_id, function_id, title) VALUES (:tenant_id, :division_id, :function_id, :title)", {"tenant_id": tenant_id, "division_id": division_id, "function_id": function_id, "title": role_title})
            grade_id = connection.execute(text("SELECT grade_band_id FROM grade_bands WHERE tenant_id=:tenant_id AND band_code=:grade"), {"tenant_id": tenant_id, "grade": grade}).scalar_one_or_none()
            if grade_id is None and grade == "SS":
                grade_id = connection.execute(text("INSERT INTO grade_bands (tenant_id, band_code, band_group, designation_label, sort_order) VALUES (:tenant_id, 'SS', 'SUB_STAFF', 'Sub Staff', 3)"), {"tenant_id": tenant_id}).lastrowid
            if grade_id is None:
                raise ValueError(f"unknown grade {grade} for {name}")
            joining = parsed_date(row["Date of Joining KDDL"])
            params = {"tenant_id": tenant_id, "division_id": division_id, "name": name, "function_id": function_id, "department_id": department_id, "joining": joining}
            employee_id = connection.execute(text("SELECT employee_id FROM employees WHERE tenant_id=:tenant_id AND division_id=:division_id AND full_name=:name AND function_id=:function_id AND COALESCE(department_id,0)=:department_id AND date_of_joining=:joining"), params).scalar_one_or_none()
            if employee_id is None:
                employee_id = connection.execute(text("""INSERT INTO employees (tenant_id, division_id, employee_code, full_name, grade_band_id, designation, function_id, department_id, role_id, qualification, date_of_joining, status)
                    VALUES (:tenant_id,:division_id,:employee_code,:name,:grade_band_id,:designation,:function_id,:department_id,:role_id,:qualification,:joining,'ACTIVE')"""), {**params, "employee_code": f"D{division_id}-EMP-{sequence:03d}", "grade_band_id": grade_id, "designation": clean(row["Designation"]), "role_id": role_id, "qualification": clean(row.get("Education")) or None}).lastrowid
                counts["employees_created"] = int(counts["employees_created"]) + 1
            else:
                counts["employees_existing"] = int(counts["employees_existing"]) + 1
            people[(key(name), key(function_name))] = int(employee_id)
        for requested_name, manager_name in manager_by_employee.items():
            source_name, source_function = aliases.get(requested_name, (requested_name, ""))
            employee_id = next((identifier for (name, function), identifier in people.items() if name == source_name and (not source_function or function == source_function)), None)
            manager_id = next((identifier for (name, _), identifier in people.items() if name == key(manager_name)), None)
            if employee_id is None:
                continue
            if manager_id is None:
                counts["unresolved_managers"].append({"employee": requested_name, "manager": manager_name})
                continue
            connection.execute(text("UPDATE employees SET manager_employee_id=:manager_id WHERE tenant_id=:tenant_id AND employee_id=:employee_id"), {"tenant_id": tenant_id, "employee_id": employee_id, "manager_id": manager_id})
            counts["manager_links"] = int(counts["manager_links"]) + 1
        if dry_run:
            connection.rollback()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("employees", type=Path)
    parser.add_argument("managers", type=Path)
    parser.add_argument("--tenant-id", type=int, default=1)
    parser.add_argument("--division-id", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(import_employees(args.employees, args.managers, args.tenant_id, args.division_id, args.dry_run))


if __name__ == "__main__":
    main()
