"""Replace closed-cycle Success Behaviour assessments from the supplied workbook."""

from __future__ import annotations

import argparse
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import openpyxl
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


TENANT_ID = 1
CYCLE_NAME = "FY 2025 Cycle 2"
SUBMITTED_AT = datetime(2026, 3, 31, 17, 0, 0)
DEFAULT_WORKBOOK = Path(r"C:\Users\Bhawna Narula\Downloads\Previous Cycle data_SB.xlsx")
SHEETS = (("D1 — Success Behaviours", "D1"), ("D2 — Success Behaviours", "D2"))


def clean(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def normalized(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean(value).casefold())


def rating(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(float(value))
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid assessment rating {value!r}") from error
    if parsed == 0:
        return None
    if parsed not in {1, 2, 3, 4}:
        raise ValueError(f"Assessment rating must be between 1 and 4, got {value!r}")
    return parsed


def workbook_records(workbook_path: Path) -> list[dict[str, object]]:
    workbook = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
    records: list[dict[str, object]] = []
    try:
        for sheet_name, division_code in SHEETS:
            sheet = workbook[sheet_name]
            for row_number, row in enumerate(sheet.iter_rows(min_row=3, values_only=True), 3):
                employee_code = clean(row[1])
                if not employee_code:
                    continue
                for behaviour_number, column in enumerate(range(3, 18, 3), 1):
                    records.append({
                        "source_sheet": sheet_name,
                        "source_row": row_number,
                        "division_code": division_code,
                        "employee_code": employee_code,
                        "employee_name": clean(row[2]),
                        "behaviour_code": f"SB{behaviour_number:02d}",
                        "desired_level": rating(row[column]),
                        "self_assessment_level": rating(row[column + 1]),
                        "manager_assessment_level": rating(row[column + 2]),
                    })
    finally:
        workbook.close()
    return records


def import_assessments(workbook_path: Path, apply: bool) -> dict[str, int]:
    load_dotenv()
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    source_records = workbook_records(workbook_path)
    counts: dict[str, int] = defaultdict(int)
    with engine.begin() as connection:
        cycle_id = connection.execute(text("""SELECT cycle_id FROM assessment_cycles
            WHERE tenant_id=:tenant_id AND name=:name AND status='CLOSED'"""),
            {"tenant_id": TENANT_ID, "name": CYCLE_NAME}).scalar_one()
        divisions = {row["code"]: int(row["division_id"]) for row in connection.execute(text(
            "SELECT division_id, code FROM divisions WHERE tenant_id=:tenant_id"), {"tenant_id": TENANT_ID}).mappings()}
        employees = {(int(row["division_id"]), normalized(row["employee_code"])): dict(row) for row in connection.execute(text("""
            SELECT employee_id, division_id, employee_code, role_id, manager_employee_id
            FROM employees WHERE tenant_id=:tenant_id"""), {"tenant_id": TENANT_ID}).mappings()}
        behaviours = {row["code"]: int(row["behaviour_id"]) for row in connection.execute(text(
            "SELECT behaviour_id, code FROM success_behaviours WHERE tenant_id=:tenant_id"), {"tenant_id": TENANT_ID}).mappings()}

        imported: dict[int, dict[int, dict[str, object]]] = defaultdict(dict)
        for record in source_records:
            counts["source_entries"] += 1
            employee = employees.get((divisions[record["division_code"]], normalized(record["employee_code"])))
            if employee is None:
                counts["unmatched_employee_entries"] += 1
                continue
            behaviour_id = behaviours.get(record["behaviour_code"])
            if behaviour_id is None:
                raise ValueError(f"Missing Success Behaviour {record['behaviour_code']} in master data")
            imported[int(employee["employee_id"])][behaviour_id] = {**record, **employee}
            counts["matched_entries"] += 1

        if apply:
            connection.execute(text("""DELETE line_item FROM assessment_line_items line_item
                JOIN assessment_forms form ON form.form_id=line_item.form_id
                WHERE form.tenant_id=:tenant_id AND form.cycle_id=:cycle_id AND form.assessment_type='BEHAVIOUR'"""),
                {"tenant_id": TENANT_ID, "cycle_id": cycle_id})
            connection.execute(text("""DELETE FROM assessment_forms
                WHERE tenant_id=:tenant_id AND cycle_id=:cycle_id AND assessment_type='BEHAVIOUR'"""),
                {"tenant_id": TENANT_ID, "cycle_id": cycle_id})
            for employee_id, behaviour_records in imported.items():
                sample = next(iter(behaviour_records.values()))
                has_manager_rating = any(item["manager_assessment_level"] is not None for item in behaviour_records.values())
                result = connection.execute(text("""INSERT INTO assessment_forms
                    (tenant_id, cycle_id, assessment_type, employee_id, role_id, manager_employee_id, status,
                     self_assessment_date, behaviour_self_submitted_at, manager_assessment_date, behaviour_manager_submitted_at)
                    VALUES (:tenant_id,:cycle_id,'BEHAVIOUR',:employee_id,:role_id,:manager_employee_id,:status,
                     :self_date,:self_submitted_at,:manager_date,:manager_submitted_at)"""), {
                    "tenant_id": TENANT_ID, "cycle_id": cycle_id, "employee_id": employee_id,
                    "role_id": sample["role_id"], "manager_employee_id": sample["manager_employee_id"],
                    "status": "MANAGER_SUBMITTED" if has_manager_rating else "SELF_SUBMITTED",
                    "self_date": SUBMITTED_AT.date(), "self_submitted_at": SUBMITTED_AT,
                    "manager_date": SUBMITTED_AT.date() if has_manager_rating else None,
                    "manager_submitted_at": SUBMITTED_AT if has_manager_rating else None,
                })
                connection.execute(text("""INSERT INTO assessment_line_items
                    (form_id,item_type,item_id,desired_level,self_assessment_level,manager_assessment_level)
                    VALUES (:form_id,'BEHAVIOUR',:item_id,:desired_level,:self_level,:manager_level)"""), [
                    {"form_id": int(result.lastrowid), "item_id": behaviour_id,
                     "desired_level": item["desired_level"], "self_level": item["self_assessment_level"],
                     "manager_level": item["manager_assessment_level"]}
                    for behaviour_id, item in behaviour_records.items()
                ])
            counts["forms_created"] = len(imported)
            counts["line_items_created"] = sum(len(items) for items in imported.values())
        else:
            connection.rollback()
    return dict(counts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Replace previous-cycle Success Behaviour assessment records.")
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()
    print(import_assessments(arguments.workbook, arguments.apply))


if __name__ == "__main__":
    main()
