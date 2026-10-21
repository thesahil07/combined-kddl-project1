"""Import Division 1 role master and validated descriptions from the approved workbook."""

from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
import argparse
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


DEFAULT_WORKBOOK = Path(
    r"C:\Users\Bhawna Narula\VVNT-Founder\OneDrive - VVNT\WIP_Items\Customers - Existing\PGC\FY26\KDDL\KDDL Data\Copy of 4.1 Role Description Exercise-Dials 1.xlsx"
)
TENANT_ID = 1
DIVISION_ID = 1
VALIDATOR_NAME = "Avinash Kumar"
VALIDATED_AT = datetime(2026, 4, 1)

FIELDS = {
    "ROLE": "title",
    "# PEOPLE (DIALS 1)": "people_count",
    "FUNCTION": "function_name",
    "DEPARTMENT": "department_name",
    "ROLE DEFINITION": "role_definition",
    "KEY RESPONSIBILITIES IN THE ROLE": "key_responsibilities",
    "KEY PERFORMANCE INDICATORS (KPI) FOR THE ROLE": "kpis",
    "EDUCATION/DEGREE/DIPLOMA OR CERTIFICATIONS REQUIRED TO PERFORM THE ROLE": "education_certifications",
    "MINIMUM RELEVANT EXPERIENCE REQUIRED TO PERFORM THE ROLE": "minimum_relevant_experience",
    "KNOWLEDGE REQUIRED TO PERFORM THE ROLE": "knowledge_required",
    "SKILLS REQUIRED TO PERFORM THE ROLE": "skills_required",
    "ATTITUDE/BEHAVIOURS REQUIRED TO PERFORM THE ROLE": "attitudes_behaviours",
}


def text_value(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).replace("\r\n", "\n").replace("\xa0", " ").strip()


def clean(value: object) -> str:
    return " ".join(text_value(value).split())


def normalized(value: object) -> str:
    return clean(value).casefold()


def row_values(data: pd.DataFrame, label: str) -> list[str]:
    target = normalized(label)
    for _, row in data.iterrows():
        values = [text_value(value) for value in row.tolist()]
        label_index = next((index for index, value in enumerate(values[:3]) if normalized(value) == target), None)
        if label_index is not None:
            return values[label_index + 1 :]
    return []


def role_number(value: str) -> str:
    try:
        return str(int(float(value)))
    except ValueError:
        return clean(value)


def detailed_roles(path: Path, overview_sheet: str) -> Iterable[dict[str, object]]:
    workbook = pd.ExcelFile(path)
    for sheet in workbook.sheet_names:
        if sheet == overview_sheet:
            continue
        data = pd.read_excel(path, sheet_name=sheet, header=None).fillna("")
        role_numbers = row_values(data, "ROLE #")
        values_by_field = {key: row_values(data, key) for key in FIELDS}
        if not role_numbers:
            role_numbers = [""] * len(values_by_field["ROLE"])
        for index, source_number in enumerate(role_numbers):
            record = {
                destination: values_by_field[label][index]
                if index < len(values_by_field[label]) else ""
                for label, destination in FIELDS.items()
            }
            record["source_role_number"] = role_number(source_number)
            record["sheet"] = sheet
            if clean(record["role_definition"]):
                yield record


def overview_roles(path: Path, overview_sheet: str) -> tuple[list[dict[str, str]], dict[str, dict[str, str]]]:
    data = pd.read_excel(path, sheet_name=overview_sheet, header=1).fillna("")
    roles: list[dict[str, str]] = []
    by_number: dict[str, dict[str, str]] = {}
    function_name = ""
    department_name = ""
    for _, row in data.iterrows():
        function_name = clean(row["FUNCTION"]) or function_name
        department_name = clean(row["DEPARTMENT"]) or department_name
        title = clean(row["ROLES"])
        source_number = role_number(clean(row["#"]))
        if not title or not source_number:
            continue
        record = {
            "source_role_number": source_number,
            "function_name": function_name,
            "department_name": department_name,
            "title": title,
        }
        roles.append(record)
        by_number[source_number] = record
    duplicate_titles = Counter(
        (normalized(role["function_name"]), normalized(role["title"])) for role in roles
    )
    for role in roles:
        key = normalized(role["function_name"]), normalized(role["title"])
        if duplicate_titles[key] > 1 and role["department_name"]:
            role["title"] = f"{role['title']} ({role['department_name']})"
    return roles, by_number


def function_id(connection, name: str, function_ids: dict[str, int]) -> int:
    key = normalized(name)
    if key in function_ids:
        return function_ids[key]
    result = connection.execute(text("""
        INSERT INTO functions (tenant_id, division_id, name)
        VALUES (:tenant_id, :division_id, :name)
    """), {"tenant_id": TENANT_ID, "division_id": DIVISION_ID, "name": clean(name)})
    identifier = int(result.lastrowid)
    function_ids[key] = identifier
    return identifier


def role_id(connection, title: str, function_id_value: int, role_ids: dict[tuple[int, str], int]) -> int:
    key = function_id_value, normalized(title)
    if key in role_ids:
        return role_ids[key]
    result = connection.execute(text("""
        INSERT INTO roles (tenant_id, division_id, function_id, title, description_status)
        VALUES (:tenant_id, :division_id, :function_id, :title, 'NOT_STARTED')
    """), {
        "tenant_id": TENANT_ID, "division_id": DIVISION_ID,
        "function_id": function_id_value, "title": clean(title),
    })
    identifier = int(result.lastrowid)
    role_ids[key] = identifier
    return identifier


def import_description(connection, role_id_value: int, validator_id: int, record: dict[str, object]) -> bool:
    existing = connection.execute(text("""
        SELECT role_description_id FROM role_descriptions
        WHERE role_id=:role_id AND role_definition=:role_definition
          AND validated_by_employee_id=:validator_id AND validated_at=:validated_at
        LIMIT 1
    """), {
        "role_id": role_id_value, "role_definition": text_value(record["role_definition"]),
        "validator_id": validator_id, "validated_at": VALIDATED_AT,
    }).scalar_one_or_none()
    if existing is not None:
        return False
    version = connection.execute(text("""
        SELECT COALESCE(MAX(version), 0) + 1 FROM role_descriptions WHERE role_id=:role_id
    """), {"role_id": role_id_value}).scalar_one()
    connection.execute(text("""
        INSERT INTO role_descriptions (
          role_id, version, people_count, role_definition, key_responsibilities, kpis,
          specifications_experience, equipment_process_refs, ai_refined,
          validated_by_employee_id, validated_at, education_certifications,
          minimum_relevant_experience, knowledge_required, skills_required, attitudes_behaviours
        ) VALUES (
          :role_id, :version, :people_count, :role_definition, :key_responsibilities, :kpis,
          :specifications_experience, NULL, 0, :validator_id, :validated_at,
          :education_certifications, :minimum_relevant_experience, :knowledge_required,
          :skills_required, :attitudes_behaviours
        )
    """), {
        "role_id": role_id_value, "version": version,
        "people_count": int(float(record["people_count"])) if clean(record["people_count"]) else None,
        "role_definition": text_value(record["role_definition"]),
        "key_responsibilities": text_value(record["key_responsibilities"]),
        "kpis": text_value(record["kpis"]),
        "specifications_experience": "",
        "validator_id": validator_id, "validated_at": VALIDATED_AT,
        "education_certifications": text_value(record["education_certifications"]),
        "minimum_relevant_experience": text_value(record["minimum_relevant_experience"]),
        "knowledge_required": text_value(record["knowledge_required"]),
        "skills_required": text_value(record["skills_required"]),
        "attitudes_behaviours": text_value(record["attitudes_behaviours"]),
    })
    connection.execute(text("""
        UPDATE roles SET description_status='VALIDATED' WHERE role_id=:role_id
    """), {"role_id": role_id_value})
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--overview-sheet", default="Dials 1")
    parser.add_argument("--division-id", type=int, default=1)
    parser.add_argument("--validator", default="Avinash Kumar")
    arguments = parser.parse_args()
    global DIVISION_ID, VALIDATOR_NAME
    DIVISION_ID = arguments.division_id
    VALIDATOR_NAME = arguments.validator
    load_dotenv()
    engine = create_engine(os.environ["DATABASE_URL"])
    master_roles, roles_by_number = overview_roles(arguments.workbook, arguments.overview_sheet)
    details = list(detailed_roles(arguments.workbook, arguments.overview_sheet))
    duplicate_details = Counter(
        (normalized(str(record["function_name"])), normalized(str(record["title"])))
        for record in details if clean(record["title"])
    )
    with engine.begin() as connection:
        validator_id = connection.execute(text("""
            SELECT employee_id FROM employees
            WHERE tenant_id=:tenant_id AND division_id=:division_id AND full_name=:full_name
        """), {
            "tenant_id": TENANT_ID, "division_id": DIVISION_ID,
            "full_name": VALIDATOR_NAME,
        }).scalar_one()
        function_ids = {
            normalized(row["name"]): int(row["function_id"])
            for row in connection.execute(text("""
                SELECT function_id, name FROM functions
                WHERE tenant_id=:tenant_id AND division_id=:division_id
            """), {"tenant_id": TENANT_ID, "division_id": DIVISION_ID}).mappings()
        }
        role_ids = {
            (int(row["function_id"]), normalized(row["title"])): int(row["role_id"])
            for row in connection.execute(text("""
                SELECT role_id, function_id, title FROM roles
                WHERE tenant_id=:tenant_id AND division_id=:division_id
            """), {"tenant_id": TENANT_ID, "division_id": DIVISION_ID}).mappings()
        }
        for role in master_roles:
            role_id(connection, role["title"], function_id(connection, role["function_name"], function_ids), role_ids)
        imported = 0
        for record in details:
            fallback = roles_by_number.get(str(record["source_role_number"]), {})
            title = clean(record["title"]) or fallback.get("title", "")
            function_name = clean(record["function_name"]) or fallback.get("function_name", "")
            department_name = clean(record["department_name"]) or fallback.get("department_name", "")
            duplicate_key = normalized(function_name), normalized(clean(record["title"]))
            if clean(record["title"]) and duplicate_details[duplicate_key] > 1 and department_name:
                title = f"{title} ({department_name})"
            if not title or not function_name:
                continue
            identifier = role_id(connection, title, function_id(connection, function_name, function_ids), role_ids)
            imported += import_description(connection, identifier, validator_id, record)
    print(f"Master roles processed: {len(master_roles)}")
    print(f"Validated descriptions inserted: {imported}")
    print(f"Detailed descriptions in workbook: {len(details)}")


if __name__ == "__main__":
    main()
