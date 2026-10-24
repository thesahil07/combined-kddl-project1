import io, openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import text
import dotenv
dotenv.load_dotenv('backend/.env')
from app.presentation.api.dependencies import initialize_database_engine, get_session

initialize_database_engine()
s = next(get_session())

tenant_id = 1
division_id = None
cycle_id = 1
employee_name = None

# Query divisions
divisions = s.execute(text("SELECT division_id, code, name FROM divisions WHERE tenant_id=:tenant_id"), {"tenant_id": tenant_id}).mappings().all()

# Query cycles
cycles = s.execute(text("""
    SELECT cycle_id, name FROM assessment_cycles
    WHERE tenant_id=:tenant_id AND status IN ('NOT_STARTED', 'IN_PROGRESS')
    ORDER BY period_start DESC
"""), {"tenant_id": tenant_id}).mappings().all()
selected_cycle_id = cycle_id or (cycles[0]["cycle_id"] if cycles else None)

# Division label
division_label = "All_Entities"
if division_id is not None:
    div_row = s.execute(
        text("SELECT name FROM divisions WHERE tenant_id=:tenant_id AND division_id=:division_id"),
        {"tenant_id": tenant_id, "division_id": division_id},
    ).scalar_one_or_none()
    if div_row:
        division_label = str(div_row).replace(" - Demo", "").replace(" - ", "_").replace(" ", "_")

cycle_name = "All_Cycles"
if selected_cycle_id is not None:
    for c in cycles:
        if c["cycle_id"] == selected_cycle_id:
            cycle_name = str(c["name"]).replace(" - ", "_").replace(" ", "_")
            break

emp_part = f"_{str(employee_name).strip().replace(' ', '_')}" if employee_name else ""
filename = f"KDDL_Assessment_Gaps_Export_{division_label}{emp_part}_{cycle_name}.xlsx"

# Status query
status_query = text("""
    SELECT e.employee_id, e.employee_code, e.full_name AS employee_name,
           REPLACE(d.name, ' - Demo', '') AS division_name,
           COALESCE(m.full_name, 'Not assigned') AS manager_name,
           COALESCE(f.name, '-') AS function_name,
           COALESCE(dep.name, '-') AS department_name,
           COALESCE(r.title, e.designation, '-') AS role_title,
           COALESCE(gb.band_code, '-') AS grade,
           CASE WHEN behaviour.form_id IS NULL THEN 'PENDING_WITH_EMPLOYEE'
                WHEN behaviour.behaviour_self_submitted_at IS NULL THEN 'PENDING_WITH_EMPLOYEE'
                ELSE 'COMPLETED' END AS behaviour_self_status,
           CASE WHEN behaviour.form_id IS NULL THEN 'PENDING_WITH_MANAGER'
                WHEN behaviour.behaviour_manager_submitted_at IS NULL THEN 'PENDING_WITH_MANAGER'
                ELSE 'COMPLETED' END AS behaviour_manager_status,
           CASE WHEN functional.form_id IS NULL AND EXISTS (
                    SELECT 1 FROM functional_skills fs
                    JOIN desired_level_matrix dlm ON dlm.tenant_id=fs.tenant_id
                        AND dlm.division_id=e.division_id AND dlm.item_type='SKILL'
                        AND dlm.item_id=fs.skill_id AND dlm.department_id <=> e.department_id
                        AND dlm.grade_band_id=e.grade_band_id
                    WHERE fs.tenant_id=e.tenant_id AND fs.division_id=e.division_id
                        AND fs.function_id=e.function_id AND fs.department_id <=> e.department_id
                ) THEN 'PENDING_WITH_EMPLOYEE'
                WHEN functional.form_id IS NULL THEN 'NOT_CONFIGURED'
                WHEN functional.functional_self_submitted_at IS NULL THEN 'PENDING_WITH_EMPLOYEE'
                ELSE 'COMPLETED' END AS functional_self_status,
           CASE WHEN functional.form_id IS NULL AND EXISTS (
                    SELECT 1 FROM functional_skills fs
                    JOIN desired_level_matrix dlm ON dlm.tenant_id=fs.tenant_id
                        AND dlm.division_id=e.division_id AND dlm.item_type='SKILL'
                        AND dlm.item_id=fs.skill_id AND dlm.department_id <=> e.department_id
                        AND dlm.grade_band_id=e.grade_band_id
                    WHERE fs.tenant_id=e.tenant_id AND fs.division_id=e.division_id
                        AND fs.function_id=e.function_id AND fs.department_id <=> e.department_id
                ) THEN 'PENDING_WITH_MANAGER'
                WHEN functional.form_id IS NULL THEN 'NOT_CONFIGURED'
                WHEN functional.functional_manager_submitted_at IS NULL THEN 'PENDING_WITH_MANAGER'
                ELSE 'COMPLETED' END AS functional_manager_status,
           COALESCE(g.behaviour_gaps, 0) AS behaviour_gaps,
           COALESCE(g.functional_gaps, 0) AS functional_gaps
    FROM employees e
    JOIN divisions d ON d.division_id=e.division_id AND d.tenant_id=e.tenant_id
    JOIN entities en ON en.entity_id=d.entity_id AND en.tenant_id=d.tenant_id
    LEFT JOIN employees m ON m.employee_id=e.manager_employee_id AND m.tenant_id=e.tenant_id
    LEFT JOIN roles r ON r.role_id=e.role_id AND r.tenant_id=e.tenant_id AND r.division_id=e.division_id
    LEFT JOIN functions f ON f.function_id=e.function_id
    LEFT JOIN departments dep ON dep.department_id=e.department_id
    LEFT JOIN grade_bands gb ON gb.grade_band_id=e.grade_band_id
    LEFT JOIN assessment_forms behaviour ON behaviour.tenant_id=e.tenant_id AND behaviour.employee_id=e.employee_id
        AND behaviour.cycle_id=:cycle_id AND behaviour.assessment_type='BEHAVIOUR'
    LEFT JOIN assessment_forms functional ON functional.tenant_id=e.tenant_id AND functional.employee_id=e.employee_id
        AND functional.cycle_id=:cycle_id AND functional.assessment_type='SKILL'
    LEFT JOIN (
        SELECT af.employee_id,
            SUM(CASE WHEN ali.item_type='BEHAVIOUR' AND ali.gap < 0 THEN 1 ELSE 0 END) AS behaviour_gaps,
            SUM(CASE WHEN ali.item_type='SKILL' AND ali.gap < 0 THEN 1 ELSE 0 END) AS functional_gaps
        FROM assessment_forms af JOIN assessment_line_items ali ON ali.form_id=af.form_id
        WHERE af.tenant_id=:tenant_id AND af.cycle_id=:cycle_id GROUP BY af.employee_id
    ) g ON g.employee_id=e.employee_id
    WHERE e.tenant_id=:tenant_id AND e.status='ACTIVE' AND en.code <> 'CORPORATE'
      AND d.code <> 'TARATEC-LDR'
      AND (:division_id IS NULL OR e.division_id=:division_id)
      AND (:employee_name IS NULL OR LOWER(e.full_name) LIKE :employee_name_like OR LOWER(e.employee_code) LIKE :employee_name_like)
    ORDER BY d.name, e.full_name
""")

status_rows = s.execute(status_query, {
    "tenant_id": tenant_id,
    "division_id": division_id,
    "cycle_id": selected_cycle_id,
    "employee_name": employee_name,
    "employee_name_like": f"%{employee_name.lower()}%" if employee_name else "%",
}).mappings().all()

# Line items query (Evaluated items only)
line_query = text("""
    SELECT
        e.employee_code,
        e.full_name AS employee_name,
        REPLACE(d.name, ' - Demo', '') AS division_name,
        COALESCE(f.name, '-') AS function_name,
        COALESCE(dep.name, '-') AS department_name,
        COALESCE(r.title, e.designation, '-') AS role_title,
        COALESCE(gb.band_code, '-') AS grade,
        COALESCE(m.full_name, 'Not assigned') AS manager_name,
        ali.item_type,
        COALESCE(sb.name, fs.name) AS item_name,
        ali.desired_level,
        ali.self_assessment_level,
        ali.manager_assessment_level,
        ali.gap,
        af.status AS form_status
    FROM assessment_forms af
    JOIN employees e ON e.employee_id = af.employee_id AND e.tenant_id = af.tenant_id
    JOIN divisions d ON d.division_id = e.division_id AND d.tenant_id = e.tenant_id
    JOIN entities en ON en.entity_id = d.entity_id AND en.tenant_id = d.tenant_id
    JOIN assessment_line_items ali ON ali.form_id = af.form_id
    LEFT JOIN functions f ON f.function_id = e.function_id
    LEFT JOIN departments dep ON dep.department_id = e.department_id
    LEFT JOIN roles r ON r.role_id = e.role_id
    LEFT JOIN grade_bands gb ON gb.grade_band_id = e.grade_band_id
    LEFT JOIN employees m ON m.employee_id = e.manager_employee_id
    LEFT JOIN success_behaviours sb ON ali.item_type = 'BEHAVIOUR' AND sb.behaviour_id = ali.item_id AND sb.tenant_id = e.tenant_id
    LEFT JOIN functional_skills fs ON ali.item_type = 'SKILL' AND fs.skill_id = ali.item_id AND fs.tenant_id = e.tenant_id
    WHERE af.tenant_id = :tenant_id
      AND (:cycle_id IS NULL OR af.cycle_id = :cycle_id)
      AND e.status = 'ACTIVE'
      AND en.code <> 'CORPORATE' AND d.code <> 'TARATEC-LDR'
      AND (:division_id IS NULL OR e.division_id = :division_id)
      AND (:employee_name IS NULL OR LOWER(e.full_name) LIKE :employee_name_like OR LOWER(e.employee_code) LIKE :employee_name_like)
    ORDER BY d.name, e.full_name, ali.item_type, item_name
""")

line_rows = s.execute(line_query, {
    "tenant_id": tenant_id,
    "division_id": division_id,
    "cycle_id": selected_cycle_id,
    "employee_name": employee_name,
    "employee_name_like": f"%{employee_name.lower()}%" if employee_name else "%",
}).mappings().all()

wb = openpyxl.Workbook()
ws_all = wb.active
ws_all.title = "All Assessment Gaps"
ws_status = wb.create_sheet("Assessment Status Summary")
ws_sb = wb.create_sheet("Success Behaviours")
ws_fs = wb.create_sheet("Functional Skills")

header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
regular_font = Font(name="Calibri", size=10)
thin_border = Border(
    left=Side(style="thin", color="E2E8F0"),
    right=Side(style="thin", color="E2E8F0"),
    top=Side(style="thin", color="E2E8F0"),
    bottom=Side(style="thin", color="E2E8F0"),
)
red_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
red_font = Font(name="Calibri", size=10, bold=True, color="991B1B")
green_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
green_font = Font(name="Calibri", size=10, bold=True, color="166534")
blue_fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
blue_font = Font(name="Calibri", size=10, bold=True, color="1E40AF")
amber_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
amber_font = Font(name="Calibri", size=10, bold=True, color="92400E")

# Setup detail sheets headers
detail_headers = [
    "Employee Name",
    "Employee Code",
    "Division",
    "Function",
    "Department",
    "Role",
    "Grade",
    "Manager Name",
    "Category",
    "Skill / Behaviour Name",
    "Desired Level (DL)",
    "Self Assessment Level (SAL)",
    "Manager Assessment Level (MAL)",
    "Gap (MAL - DL)",
    "Gap Status",
]

for ws in [ws_all, ws_sb, ws_fs]:
    ws.views.sheetView[0].showGridLines = True
    ws.append(detail_headers)
    ws.row_dimensions[1].height = 28
    ws.freeze_panes = "A2"
    for col_idx in range(1, len(detail_headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

def append_detail_row(ws, r):
    cat_display = "-"
    if r["item_type"] == "BEHAVIOUR":
        cat_display = "Success Behaviour"
    elif r["item_type"] == "SKILL":
        cat_display = "Functional Skill"

    dl = f"L{r['desired_level']}" if r["desired_level"] is not None else "-"
    sal = f"L{r['self_assessment_level']}" if r["self_assessment_level"] is not None else "-"
    mal = f"L{r['manager_assessment_level']}" if r["manager_assessment_level"] is not None else "-"

    gap_val = r["gap"]
    gap_display = "-"
    gap_status = "-"

    if gap_val is not None:
        gap_display = int(gap_val)
        if gap_val < 0:
            gap_status = f"Negative Gap ({gap_val})"
        elif gap_val == 0:
            gap_status = "Meets Desired Level (0)"
        else:
            gap_status = f"Exceeds Desired Level (+{gap_val})"

    row_data = [
        str(r["employee_name"]),
        str(r["employee_code"]),
        str(r["division_name"]),
        str(r["function_name"]),
        str(r["department_name"]),
        str(r["role_title"]),
        str(r["grade"]),
        str(r["manager_name"]),
        cat_display,
        str(r["item_name"] or "-"),
        dl,
        sal,
        mal,
        gap_display,
        gap_status,
    ]
    ws.append(row_data)
    row_idx = ws.max_row
    ws.row_dimensions[row_idx].height = 22

    for col_idx in range(1, len(row_data) + 1):
        cell = ws.cell(row=row_idx, column=col_idx)
        cell.font = regular_font
        cell.border = thin_border

        if col_idx in (2, 7, 9, 11, 12, 13, 14, 15):
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.alignment = Alignment(horizontal="left", vertical="center")

        if col_idx in (14, 15) and gap_val is not None:
            if gap_val < 0:
                cell.fill = red_fill
                cell.font = red_font
            elif gap_val == 0:
                cell.fill = green_fill
                cell.font = green_font
            elif gap_val > 0:
                cell.fill = blue_fill
                cell.font = blue_font

# Populate detail sheets:
# Sheet 1: ONLY actual reported gaps (gap < 0), exactly matching the KPI card!
gap_count = 0
for r in line_rows:
    if r["gap"] is not None and r["gap"] < 0:
        append_detail_row(ws_all, r)
        gap_count += 1
    if r["item_type"] == "BEHAVIOUR":
        append_detail_row(ws_sb, r)
    elif r["item_type"] == "SKILL":
        append_detail_row(ws_fs, r)

print(f"Populated ws_all with {gap_count} gaps, ws_sb with {ws_sb.max_row - 1} behaviours, ws_fs with {ws_fs.max_row - 1} skills")

# Setup status sheet
status_headers = [
    "Employee Name",
    "Employee Code",
    "Division",
    "Function",
    "Department",
    "Role",
    "Grade",
    "Manager Name",
    "Behaviour Self Status",
    "Behaviour Manager Status",
    "Functional Self Status",
    "Functional Manager Status",
    "Behaviour Gaps",
    "Functional Gaps",
    "Total Gaps",
]
ws_status.views.sheetView[0].showGridLines = True
ws_status.append(status_headers)
ws_status.row_dimensions[1].height = 28
ws_status.freeze_panes = "A2"
for col_idx in range(1, len(status_headers) + 1):
    cell = ws_status.cell(row=1, column=col_idx)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = thin_border

def format_status(val: str) -> str:
    return str(val).replace("_", " ").title()

for s_row in status_rows:
    tot_gaps = int(s_row["behaviour_gaps"]) + int(s_row["functional_gaps"])
    row_data = [
        str(s_row["employee_name"]),
        str(s_row["employee_code"]),
        str(s_row["division_name"]),
        str(s_row["function_name"]),
        str(s_row["department_name"]),
        str(s_row["role_title"]),
        str(s_row["grade"]),
        str(s_row["manager_name"]),
        format_status(s_row["behaviour_self_status"]),
        format_status(s_row["behaviour_manager_status"]),
        format_status(s_row["functional_self_status"]),
        format_status(s_row["functional_manager_status"]),
        int(s_row["behaviour_gaps"]),
        int(s_row["functional_gaps"]),
        tot_gaps,
    ]
    ws_status.append(row_data)
    r_idx = ws_status.max_row
    ws_status.row_dimensions[r_idx].height = 22
    for col_idx in range(1, len(row_data) + 1):
        c_cell = ws_status.cell(row=r_idx, column=col_idx)
        c_cell.font = regular_font
        c_cell.border = thin_border
        if col_idx in (2, 7, 9, 10, 11, 12, 13, 14, 15):
            c_cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            c_cell.alignment = Alignment(horizontal="left", vertical="center")

        val_str = str(c_cell.value)
        if val_str == "Completed":
            c_cell.fill = green_fill
            c_cell.font = green_font
        elif "Pending" in val_str:
            c_cell.fill = amber_fill
            c_cell.font = amber_font

        if col_idx in (13, 14, 15) and isinstance(c_cell.value, int) and c_cell.value > 0:
            c_cell.fill = red_fill
            c_cell.font = red_font

print(f"Populated ws_status with {ws_status.max_row - 1} employees")

# Autofit column widths
for ws in [ws_all, ws_status, ws_sb, ws_fs]:
    ws.auto_filter.ref = ws.dimensions
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val = str(cell.value or "")
            if len(val) > max_len:
                max_len = len(val)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

buf = io.BytesIO()
wb.save(buf)
print(f"Excel generated successfully! File size: {len(buf.getvalue())} bytes. Filename: {filename}")
s.close()
