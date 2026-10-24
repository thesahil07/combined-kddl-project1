import io, openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import text
from app.presentation.api.dependencies import initialize_database_engine, get_session

initialize_database_engine()
s = next(get_session())

tenant_id = 1
division_id = None
cycle_id = 1
employee_name = None

# 1. Cycles
cycles = s.execute(text("""
    SELECT cycle_id, name FROM assessment_cycles
    WHERE tenant_id=:tenant_id AND status IN ('NOT_STARTED', 'IN_PROGRESS')
    ORDER BY period_start DESC
"""), {"tenant_id": tenant_id}).mappings().all()

selected_cycle_id = cycle_id or (cycles[0]["cycle_id"] if cycles else None)
print("Selected cycle id:", selected_cycle_id)

# 2. Status query
status_query = text("""
    SELECT e.employee_id, e.employee_code, e.full_name AS employee_name, d.name AS division_name,
           COALESCE(m.full_name, 'Not assigned') AS manager_name,
           COALESCE(f.name, '—') AS function_name,
           COALESCE(dep.name, '—') AS department_name,
           COALESCE(r.title, e.designation, '—') AS role_title,
           COALESCE(gb.band_code, '—') AS grade,
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

print("Status rows count:", len(status_rows))

# 3. Line items query
line_query = text("""
    SELECT
        e.employee_code,
        e.full_name AS employee_name,
        d.name AS division_name,
        COALESCE(f.name, '—') AS function_name,
        COALESCE(dep.name, '—') AS department_name,
        COALESCE(r.title, e.designation, '—') AS role_title,
        COALESCE(gb.band_code, '—') AS grade,
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
      AND af.cycle_id = :cycle_id
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

print("Line rows count (evaluated items only):", len(line_rows))
gap_rows = [r for r in line_rows if r["gap"] is not None and r["gap"] < 0]
print("Actual gap rows count:", len(gap_rows))
sb_rows = [r for r in line_rows if r["item_type"] == "BEHAVIOUR"]
print("Success behaviour rows count:", len(sb_rows))
fs_rows = [r for r in line_rows if r["item_type"] == "SKILL"]
print("Functional skill rows count:", len(fs_rows))

s.close()
