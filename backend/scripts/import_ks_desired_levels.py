"""Safely refresh functional-skill desired levels from the KDDL KS workbooks."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings


TENANT_ID = 1
MAIN_SHEET = "KS Matrix (Updated & Future Pro"
TECHNICAL_SHEET = "Desired Levels"
LEVEL_COLUMNS = {
    "S3": ("S3",),
    "E1": ("E1",),
    "E2&E3": ("E2", "E3"),
    "E4": ("E4",),
    "M1 & M2": ("M1", "M2"),
    "M3 & M4": ("M3", "M4"),
    "LM 1 & LM 2": ("LM1", "LM2"),
}
SOURCE_LEVEL_CORRECTIONS = {("D054", "E1"): "L2", ("D055", "E1"): "L2"}
DIVISIONS = {"DIAL 1": 1, "DIAL 2": 2}


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def key(value: object) -> str:
    return re.sub(r"\s+", " ", clean(value)).upper()


def level(value: object) -> int | None:
    value = key(value)
    if value in {"X", ""}:
        return None
    match = re.fullmatch(r"L([1-4])", value)
    if not match:
        raise ValueError(f"Expected L1 to L4 or X, found {clean(value)!r}.")
    return int(match.group(1))


def rows_from_sheet(path: Path, sheet_name: str) -> list[dict[str, object]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        worksheet = workbook[sheet_name]
        rows = list(worksheet.iter_rows(values_only=True))
        headers = [clean(value) for value in rows[1 if sheet_name == MAIN_SHEET else 0]]
        return [
            dict(zip(headers, values, strict=True))
            for values in rows[(2 if sheet_name == MAIN_SHEET else 1) :]
            if any(clean(value) for value in values)
        ]
    finally:
        workbook.close()


def main_entries(path: Path) -> tuple[list[dict[str, object]], list[str]]:
    entries: list[dict[str, object]] = []
    warnings: list[str] = []
    function_name = department_name = ""
    for row in rows_from_sheet(path, MAIN_SHEET):
        if clean(row.get("FUNCTION")):
            function_name = clean(row["FUNCTION"])
        if clean(row.get("DEPARTMENT")):
            department_name = clean(row["DEPARTMENT"])
        code = clean(row.get("SKILL CODE"))
        if not code:
            continue
        levels: dict[str, int] = {}
        for column, bands in LEVEL_COLUMNS.items():
            try:
                source_level = level(SOURCE_LEVEL_CORRECTIONS.get((code, column), row.get(column)))
            except ValueError as error:
                warnings.append(f"{code} / {column}: {error}")
                continue
            if source_level is not None:
                levels.update({band: source_level for band in bands})
        entries.append(
            {
                "code": code,
                "function": function_name,
                "department": department_name,
                "levels": levels,
            },
        )
    return entries, warnings


def technical_entries(path: Path) -> list[dict[str, object]]:
    entries = []
    for row in rows_from_sheet(path, TECHNICAL_SHEET):
        entries.append(
            {
                "division": clean(row["Division"]),
                "department": clean(row["Department"]),
                "band": clean(row["Band Code"]),
                "code": clean(row["Skill Code"]),
                "name": clean(row["Skill Name"]),
                "level": int(row["Expected Level"]),
            },
        )
    return entries


def import_desired_levels(
    main_workbook: Path,
    technical_workbook: Path | None,
    dry_run: bool,
) -> dict[str, object]:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured.")

    entries, warnings = main_entries(main_workbook)
    technical = technical_entries(technical_workbook) if technical_workbook else []
    counts: Counter[str] = Counter()
    counts["source_skills"] = len(entries)
    engine = create_engine(settings.database_url)

    with engine.begin() as connection:
        bands = {
            row["band_code"]: row["grade_band_id"]
            for row in connection.execute(
                text("SELECT grade_band_id, band_code FROM grade_bands WHERE tenant_id=:tenant_id"),
                {"tenant_id": TENANT_ID},
            ).mappings()
        }
        for division_id in DIVISIONS.values():
            skills = connection.execute(
                text("""
                    SELECT fs.skill_id, fs.code, fs.function_id, fs.department_id,
                           f.name AS function_name, d.name AS department_name
                    FROM functional_skills fs
                    JOIN functions f ON f.function_id=fs.function_id
                    LEFT JOIN departments d ON d.department_id=fs.department_id
                    WHERE fs.tenant_id=:tenant_id AND fs.division_id=:division_id
                """),
                {"tenant_id": TENANT_ID, "division_id": division_id},
            ).mappings().all()
            skill_index = {clean(row["code"]).upper(): row for row in skills}
            for entry in entries:
                skill = skill_index.get(key(entry["code"]))
                if skill is None:
                    counts["main_skills_not_found"] += 1
                    continue
                if key(skill["function_name"]) != key(entry["function"]) or key(skill["department_name"]) != key(entry["department"]):
                    counts["main_scope_mismatches"] += 1
                    continue
                connection.execute(
                    text("""
                        DELETE FROM desired_level_matrix
                        WHERE tenant_id=:tenant_id AND division_id=:division_id
                          AND item_type='SKILL' AND item_id=:item_id AND role_id IS NULL
                    """),
                    {"tenant_id": TENANT_ID, "division_id": division_id, "item_id": skill["skill_id"]},
                )
                for band, desired_level in entry["levels"].items():
                    connection.execute(
                        text("""
                            INSERT INTO desired_level_matrix
                                (tenant_id, division_id, item_type, item_id, grade_band_id, role_id, department_id, desired_level)
                            VALUES (:tenant_id, :division_id, 'SKILL', :item_id, :grade_band_id, NULL, :department_id, :desired_level)
                        """),
                        {
                            "tenant_id": TENANT_ID,
                            "division_id": division_id,
                            "item_id": skill["skill_id"],
                            "grade_band_id": bands[band],
                            "department_id": skill["department_id"],
                            "desired_level": desired_level,
                        },
                    )
                    counts["main_levels_loaded"] += 1
                counts["main_skills_loaded"] += 1

        for entry in technical:
            division_id = DIVISIONS.get(key(entry["division"]))
            if division_id is None:
                raise ValueError(f"Unknown division in Technical Projects workbook: {entry['division']}")
            function = connection.execute(
                text("""
                    SELECT f.function_id, d.department_id
                    FROM functions f JOIN departments d ON d.function_id=f.function_id
                    WHERE f.tenant_id=:tenant_id AND f.division_id=:division_id
                      AND UPPER(TRIM(f.name))='TECHNICAL PROJECTS'
                      AND UPPER(TRIM(d.name))=:department
                """),
                {"tenant_id": TENANT_ID, "division_id": division_id, "department": key(entry["department"])},
            ).mappings().one_or_none()
            if function is None:
                raise ValueError("Technical Projects function and department are not configured for Dial 2.")
            scoped_code = f"{entry['code']}-TP"
            skill = connection.execute(
                text("""
                    SELECT skill_id FROM functional_skills
                    WHERE tenant_id=:tenant_id AND division_id=:division_id AND code=:code
                """),
                {"tenant_id": TENANT_ID, "division_id": division_id, "code": scoped_code},
            ).scalar_one_or_none()
            if skill is None:
                skill = connection.execute(
                    text("""
                        INSERT INTO functional_skills
                            (tenant_id, division_id, function_id, department_id, code, name, definition, source)
                        VALUES (:tenant_id, :division_id, :function_id, :department_id, :code, :name, :definition, 'MANUAL')
                    """),
                    {
                        "tenant_id": TENANT_ID,
                        "division_id": division_id,
                        "function_id": function["function_id"],
                        "department_id": function["department_id"],
                        "code": scoped_code,
                        "name": entry["name"],
                        "definition": f"Functional capability: {entry['name']}.",
                    },
                ).lastrowid
                counts["technical_skills_created"] += 1
            connection.execute(
                text("""
                    DELETE FROM desired_level_matrix
                    WHERE tenant_id=:tenant_id AND division_id=:division_id AND item_type='SKILL'
                      AND item_id=:item_id AND grade_band_id=:grade_band_id AND role_id IS NULL
                """),
                {
                    "tenant_id": TENANT_ID,
                    "division_id": division_id,
                    "item_id": skill,
                    "grade_band_id": bands[key(entry["band"])],
                },
            )
            connection.execute(
                text("""
                    INSERT INTO desired_level_matrix
                        (tenant_id, division_id, item_type, item_id, grade_band_id, role_id, department_id, desired_level)
                    VALUES (:tenant_id, :division_id, 'SKILL', :item_id, :grade_band_id, NULL, :department_id, :desired_level)
                """),
                {
                    "tenant_id": TENANT_ID,
                    "division_id": division_id,
                    "item_id": skill,
                    "grade_band_id": bands[key(entry["band"])],
                    "department_id": function["department_id"],
                    "desired_level": entry["level"],
                },
            )
            counts["technical_levels_loaded"] += 1
        if dry_run:
            connection.rollback()
    return {"counts": dict(counts), "warnings": warnings}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("main_workbook", type=Path)
    parser.add_argument(
        "technical_workbook",
        type=Path,
        nargs="?",
        help="Optional Technical Projects mapping workbook.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(import_desired_levels(args.main_workbook, args.technical_workbook, args.dry_run))
