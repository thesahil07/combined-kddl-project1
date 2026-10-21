"""Replace workbook-controlled tenant master and employee data safely."""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

import openpyxl
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from app.infrastructure.security.password_hasher import PasswordHasher

TENANT_ID = 1
DEFAULT_WORKBOOK = Path(r"C:\Users\Bhawna Narula\VVNT-Founder\OneDrive - VVNT\WIP_Items\Customers - Existing\PGC\FY26\KDDL\KDDL Data\Talent_Client_Data_Template_Populated_FINAL (1).xlsx")


def clean(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def rows(workbook: openpyxl.Workbook, sheet_name: str) -> list[dict[str, object]]:
    sheet = workbook[sheet_name]
    headers = [clean(sheet.cell(1, column).value) for column in range(1, sheet.max_column + 1)]
    return [dict(zip(headers, values)) for values in sheet.iter_rows(min_row=2, values_only=True)
            if any(value not in (None, "") for value in values)]


def division_code(value: object) -> str:
    return "D1" if clean(value).casefold() in {"dial 1", "dials 1", "d1"} else "D2"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()
    if not arguments.apply:
        raise SystemExit("Use --apply after reviewing the workbook counts.")
    load_dotenv()
    workbook = openpyxl.load_workbook(arguments.workbook, data_only=True)
    source = {name: rows(workbook, name) for name in (
        "Functions", "Departments", "Grade Bands", "Roles", "Role Descriptions",
        "Functional Skills", "Success Behaviours", "Desired Level Matrix", "Employees",
    )}
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    with engine.begin() as connection:
        # Clear dependent data first; assessment results cannot outlive replaced employees/roles.
        for statement in (
            "DELETE ali FROM assessment_line_items ali JOIN assessment_forms af ON af.form_id=ali.form_id WHERE af.tenant_id=:tenant_id",
            "DELETE FROM assessment_forms WHERE tenant_id=:tenant_id",
            "DELETE FROM outstanding_assessment_flags WHERE tenant_id=:tenant_id",
            "DELETE FROM priority_score_records WHERE tenant_id=:tenant_id",
            "DELETE sc FROM succession_candidates sc JOIN critical_roles cr ON cr.critical_role_id=sc.critical_role_id WHERE cr.tenant_id=:tenant_id",
            "DELETE FROM critical_roles WHERE tenant_id=:tenant_id",
            "DELETE FROM desired_level_matrix WHERE tenant_id=:tenant_id",
            "DELETE FROM functional_skills WHERE tenant_id=:tenant_id",
            "DELETE FROM role_descriptions WHERE role_id IN (SELECT role_id FROM roles WHERE tenant_id=:tenant_id)",
            "DELETE FROM executive_review_access WHERE tenant_id=:tenant_id",
            "DELETE FROM admin_console_access WHERE tenant_id=:tenant_id",
            "DELETE FROM audit_log WHERE tenant_id=:tenant_id",
            "DELETE FROM users WHERE tenant_id=:tenant_id",
            "DELETE rda FROM role_definition_assignments rda JOIN employees e ON e.employee_id=rda.manager_employee_id WHERE e.tenant_id=:tenant_id",
            "UPDATE employees SET manager_employee_id=NULL WHERE tenant_id=:tenant_id",
            "DELETE FROM employees WHERE tenant_id=:tenant_id",
            "DELETE FROM roles WHERE tenant_id=:tenant_id",
            "DELETE FROM departments WHERE tenant_id=:tenant_id",
            "DELETE FROM functions WHERE tenant_id=:tenant_id",
            "DELETE FROM success_behaviours WHERE tenant_id=:tenant_id",
            "DELETE FROM grade_bands WHERE tenant_id=:tenant_id",
        ):
            connection.execute(text(statement), {"tenant_id": TENANT_ID})

        divisions = {row["code"]: int(row["division_id"]) for row in connection.execute(text(
            "SELECT division_id, code FROM divisions WHERE tenant_id=:tenant_id"), {"tenant_id": TENANT_ID}).mappings()}
        connection.execute(text("""INSERT INTO grade_bands (tenant_id, band_code, band_group, designation_label, sort_order)
            VALUES (:tenant_id,:code,:group,:label,:sort)"""), [
            {"tenant_id": TENANT_ID, "code": clean(row["Band Code *"]), "group": clean(row["Band Group *"]),
             "label": clean(row["Designation Label *"]), "sort": int(row["Sort Order *"])} for row in source["Grade Bands"]])
        bands = {row["band_code"]: int(row["grade_band_id"]) for row in connection.execute(text(
            "SELECT grade_band_id, band_code FROM grade_bands WHERE tenant_id=:tenant_id"), {"tenant_id": TENANT_ID}).mappings()}
        connection.execute(text("INSERT INTO functions (tenant_id, division_id, name) VALUES (:tenant_id,:division_id,:name)"), [
            {"tenant_id": TENANT_ID, "division_id": divisions[division_code(row["Division Code *"])], "name": clean(row["Function Name *"])} for row in source["Functions"]])
        functions = {(int(row["division_id"]), clean(row["name"]).casefold()): int(row["function_id"]) for row in connection.execute(text(
            "SELECT function_id, division_id, name FROM functions WHERE tenant_id=:tenant_id"), {"tenant_id": TENANT_ID}).mappings()}
        function_id = lambda division, name: functions[(division, clean(name).casefold())]
        connection.execute(text("INSERT INTO departments (tenant_id, division_id, function_id, name) VALUES (:tenant_id,:division_id,:function_id,:name)"), [
            {"tenant_id": TENANT_ID, "division_id": divisions[division_code(row["Division Code *"])], "function_id": function_id(divisions[division_code(row["Division Code *"])], row["Function Name *"]), "name": clean(row["Department Name *"])} for row in source["Departments"]])
        departments = {(int(row["division_id"]), int(row["function_id"]), clean(row["name"]).casefold()): int(row["department_id"]) for row in connection.execute(text(
            "SELECT department_id, division_id, function_id, name FROM departments WHERE tenant_id=:tenant_id"), {"tenant_id": TENANT_ID}).mappings()}
        connection.execute(text("INSERT INTO roles (tenant_id, division_id, function_id, title, description_status) VALUES (:tenant_id,:division_id,:function_id,:title,'VALIDATED')"), [
            {"tenant_id": TENANT_ID, "division_id": divisions[division_code(row["Division Code *"])], "function_id": function_id(divisions[division_code(row["Division Code *"])], row["Function Name *"]), "title": clean(row["Role Title *"])} for row in source["Roles"]])
        roles = {(int(row["division_id"]), int(row["function_id"]), clean(row["title"]).casefold()): int(row["role_id"]) for row in connection.execute(text(
            "SELECT role_id, division_id, function_id, title FROM roles WHERE tenant_id=:tenant_id"), {"tenant_id": TENANT_ID}).mappings()}
        connection.execute(text("INSERT INTO employees (tenant_id, division_id, employee_code, full_name, grade_band_id, designation, function_id, department_id, role_id, date_of_birth, date_of_joining, tenure_start_date, last_promotion_date, retirement_date, qualification, status) VALUES (:tenant_id,:division_id,:code,:name,:band,:designation,:function_id,:department_id,:role_id,:dob,:doj,:tenure,:promotion,:retirement,:qualification,:status)"), [
            {"tenant_id": TENANT_ID, "division_id": divisions[division_code(row["Division Code *"])], "code": clean(row["Employee Code *"]), "name": clean(row["Full Name *"]), "band": bands[clean(row["Grade Band Code *"])], "designation": clean(row["Designation *"]), "function_id": function_id(divisions[division_code(row["Division Code *"])], row["Function Name *"]), "department_id": departments.get((divisions[division_code(row["Division Code *"])], function_id(divisions[division_code(row["Division Code *"])], row["Function Name *"]), clean(row["Department Name"]).casefold())), "role_id": roles.get((divisions[division_code(row["Division Code *"])], function_id(divisions[division_code(row["Division Code *"])], row["Function Name *"]), clean(row["Role Title"]).casefold())), "dob": row["Date of Birth"], "doj": row["Date of Joining"], "tenure": row["Tenure Start Date"], "promotion": row["Last Promotion Date"], "retirement": row["Retirement Date"], "qualification": clean(row["Qualification"]), "status": clean(row["Status *"]) or "ACTIVE"} for row in source["Employees"]])
        employees = {clean(row["employee_code"]): int(row["employee_id"]) for row in connection.execute(text("SELECT employee_id, employee_code FROM employees WHERE tenant_id=:tenant_id"), {"tenant_id": TENANT_ID}).mappings()}
        connection.execute(text("""INSERT INTO role_descriptions (role_id, version, people_count, role_definition, key_responsibilities, kpis, specifications_experience, education_certifications, minimum_relevant_experience, knowledge_required, skills_required, attitudes_behaviours, ai_refined, validated_by_employee_id, validated_at)
            VALUES (:role_id,1,:people_count,:definition,:responsibilities,:kpis,:specifications,:education,:experience,:knowledge,:skills,:attitudes,FALSE,:validator,:validated_at)"""), [{"role_id": roles[(divisions[division_code(row["Division Code *"])], function_id(divisions[division_code(row["Division Code *"])], row["Function Name *"]), clean(row["Role Title *"]).casefold())], "people_count": row["People Count"], "definition": clean(row["Role Definition *"]), "responsibilities": clean(row["Key Responsibilities *"]), "kpis": clean(row["KPIs *"]), "specifications": clean(row["Specifications / Experience *"]), "education": clean(row["Education & Certifications *"]), "experience": clean(row["Minimum Relevant Experience *"]), "knowledge": clean(row["Knowledge Required *"]), "skills": clean(row["Skills Required *"]), "attitudes": clean(row["Attitudes & Behaviours *"]), "validator": employees.get(clean(row["Validated By (Employee Code)"])), "validated_at": row["Validated On"]} for row in source["Role Descriptions"]])
        for row in source["Employees"]:
            if clean(row["Manager Employee Code"]): connection.execute(text("UPDATE employees SET manager_employee_id=:manager WHERE tenant_id=:tenant_id AND employee_code=:code"), {"tenant_id": TENANT_ID, "code": clean(row["Employee Code *"]), "manager": employees.get(clean(row["Manager Employee Code"]))})
        hasher = PasswordHasher()
        connection.execute(text("INSERT INTO users (tenant_id,email,password_hash,role,employee_id,status) VALUES (:tenant_id,:email,:password,'EMPLOYEE',:employee_id,'ACTIVE')"), [{"tenant_id": TENANT_ID, "email": f"{code.lower()}@demo.kddl.local", "password": hasher.hash("KddlDemo!2026"), "employee_id": employee_id} for code, employee_id in employees.items()])
        connection.execute(text("INSERT INTO success_behaviours (tenant_id, code, name, definition) VALUES (:tenant_id,:code,:name,:definition)"), [{"tenant_id": TENANT_ID, "code": clean(row["Behaviour Code *"]), "name": clean(row["Behaviour Name *"]), "definition": clean(row["Definition *"])} for row in source["Success Behaviours"]])
        connection.execute(text("INSERT INTO functional_skills (tenant_id, division_id, function_id, department_id, code, name, definition) VALUES (:tenant_id,:division_id,:function_id,:department_id,:code,:name,:definition)"), [{"tenant_id": TENANT_ID, "division_id": divisions[division_code(row["Division Code *"])], "function_id": function_id(divisions[division_code(row["Division Code *"])], row["Function Name *"]), "department_id": departments.get((divisions[division_code(row["Division Code *"])], function_id(divisions[division_code(row["Division Code *"])], row["Function Name *"]), clean(row["Department Name"]).casefold())), "code": clean(row["Skill Code *"]), "name": clean(row["Skill Name *"]), "definition": clean(row["Definition *"])} for row in source["Functional Skills"]])
        # Skill codes are reused between Dials 1 and Dials 2.  Keep the division in
        # this lookup so a D1 desired-level row never points to the same-coded D2
        # skill.  The functional skill itself is also the authoritative department
        # mapping for a SKILL row in the desired-level matrix.
        skills = {
            (int(row["division_id"]), clean(row["code"])): {
                "skill_id": int(row["skill_id"]),
                "department_id": row["department_id"],
            }
            for row in connection.execute(text("""SELECT skill_id, division_id, department_id, code
                FROM functional_skills WHERE tenant_id=:tenant_id"""), {"tenant_id": TENANT_ID}).mappings()
        }
        behaviours = {clean(row["code"]): int(row["behaviour_id"]) for row in connection.execute(text("SELECT behaviour_id, code FROM success_behaviours WHERE tenant_id=:tenant_id"), {"tenant_id": TENANT_ID}).mappings()}
        matrix_rows = []
        for row in source["Desired Level Matrix"]:
            division_id = divisions[division_code(row["Division Code *"])]
            item_type = clean(row["Item Type *"])
            if item_type == "SKILL":
                skill = skills[(division_id, clean(row["Item Code *"]))]
                item_id = skill["skill_id"]
                department_id = skill["department_id"]
            else:
                item_id = behaviours[clean(row["Item Code *"])]
                department_id = next((value for (division, _function, department), value in departments.items()
                                      if division == division_id and department == clean(row["Department Name"]).casefold()), None)
            matrix_rows.append({"tenant_id": TENANT_ID, "division_id": division_id, "item_type": item_type,
                                "item_id": item_id, "department_id": department_id,
                                "band": bands[clean(row["Grade Band Code *"])], "level": int(row["Desired Level *"])})
        connection.execute(text("INSERT INTO desired_level_matrix (tenant_id, division_id, item_type, item_id, department_id, grade_band_id, desired_level) VALUES (:tenant_id,:division_id,:item_type,:item_id,:department_id,:band,:level)"), matrix_rows)
    print({name: len(data) for name, data in source.items()})


if __name__ == "__main__": main()
