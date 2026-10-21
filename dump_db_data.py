import pymysql
import json

conn = pymysql.connect(host='localhost', user='root', password='Sahil@123', database='kddl_neww', port=3306)
cur = conn.cursor(pymysql.cursors.DictCursor)

# 1. Manpower stats
cur.execute("SELECT COUNT(*) as total FROM employees WHERE status='ACTIVE'")
total_mp = cur.fetchone()['total']

cur.execute("SELECT COUNT(*) as d1 FROM employees WHERE status='ACTIVE' AND division_id=1")
d1_mp = cur.fetchone()['d1']

cur.execute("SELECT COUNT(*) as d2 FROM employees WHERE status='ACTIVE' AND division_id=2")
d2_mp = cur.fetchone()['d2']

manpower = {
    "COMBINED": total_mp,
    "DIAL1": d1_mp,
    "DIAL2": d2_mp
}

# 2. Employees from DB
cur.execute("""
SELECT e.employee_id, e.employee_code as emp_code, e.full_name as name,
       IF(e.division_id=1, 'Dials 1', 'Dials 2') as division,
       e.division_id,
       COALESCE(f.name, 'Operations') as `function`,
       COALESCE(d.name, 'General') as department,
       COALESCE(r.title, e.designation) as role,
       e.designation,
       COALESCE(gb.band_code, 'M') as grade_band,
       COALESCE(gb.band_group, 'MANAGERIAL') as grade,
       m.full_name as manager_name,
       'Active' as employment_status
FROM employees e
LEFT JOIN functions f ON f.function_id = e.function_id
LEFT JOIN departments d ON d.department_id = e.department_id
LEFT JOIN roles r ON r.role_id = e.role_id
LEFT JOIN grade_bands gb ON gb.grade_band_id = e.grade_band_id
LEFT JOIN employees m ON m.employee_id = e.manager_employee_id
WHERE e.status = 'ACTIVE'
ORDER BY e.division_id, e.full_name
""")
employees = cur.fetchall()

# 3. Assessed employees
cur.execute("""
SELECT e.employee_id, af.status as form_status
FROM assessment_forms af
JOIN employees e ON e.employee_id = af.employee_id
WHERE af.status != 'NOT_STARTED' AND e.status='ACTIVE'
""")
form_rows = cur.fetchall()
assessed_map = {}
for r in form_rows:
    assessed_map[r['employee_id']] = r['form_status']

for emp in employees:
    is_assessed = emp['employee_id'] in assessed_map
    emp['is_assessed'] = is_assessed
    emp['assessment_status'] = "Pending" if assessed_map.get(emp['employee_id']) == "SELF_SUBMITTED" else ("Assessed" if is_assessed else "Not started")
    emp['in_scope_for_gaps'] = "Yes" if is_assessed else "No"
    emp['person_type'] = "Assessed employee" if is_assessed else "Active employee"

# 4. Assessment items & Gaps from DB
cur.execute("""
SELECT ali.line_item_id as gap_id, af.employee_id, e.employee_code as emp_code,
       ali.item_type as type,
       COALESCE(fs.name, sb.name, 'Skill Item') as skill_or_behaviour,
       COALESCE(fs.definition, sb.definition, '') as definition,
       ali.desired_level,
       ali.self_assessment_level as self_level,
       COALESCE(ali.manager_assessment_level, ali.self_assessment_level) as assessed_level,
       ali.gap,
       IF(COALESCE(ali.gap, 0) < 0, 'Yes', 'No') as is_gap,
       IF(COALESCE(ali.gap, 0) < 0, CONCAT('Development priority in ', COALESCE(fs.name, sb.name, 'competency')), 'Meets required proficiency') as training_need,
       IF(COALESCE(ali.gap, 0) < 0, 'Identified', 'Met') as training_status,
       ali.description_for_improvement as improvement_description,
       af.cycle_id, af.form_id, af.status as form_status
FROM assessment_line_items ali
JOIN assessment_forms af ON af.form_id = ali.form_id
JOIN employees e ON e.employee_id = af.employee_id
LEFT JOIN functional_skills fs ON fs.skill_id = ali.item_id AND ali.item_type = 'SKILL'
LEFT JOIN success_behaviours sb ON sb.behaviour_id = ali.item_id AND ali.item_type = 'BEHAVIOUR'
WHERE af.status != 'NOT_STARTED' AND e.status='ACTIVE'
ORDER BY af.cycle_id DESC, af.form_id DESC, ali.line_item_id
""")
all_line_items_raw = cur.fetchall()

deduped_items = {}
for r in all_line_items_raw:
    key = (r['emp_code'], r['type'], r['skill_or_behaviour'])
    if key not in deduped_items:
        computed_gap = r['gap']
        if computed_gap is None and r['assessed_level'] is not None and r['desired_level'] is not None:
            computed_gap = r['assessed_level'] - r['desired_level']
        
        is_gap = 'Yes' if (computed_gap is not None and computed_gap < 0) else 'No'
        training_status = 'Identified' if is_gap == 'Yes' else 'Met'
        training_need = (
            f"Development priority in {r['skill_or_behaviour']}"
            if is_gap == 'Yes'
            else "Meets required proficiency"
        )
        
        deduped_items[key] = {
            "gap_id": f"GAP-{r['gap_id']}",
            "emp_code": r['emp_code'],
            "type": r['type'],
            "skill_or_behaviour": r['skill_or_behaviour'],
            "definition": r['definition'],
            "desired_level": r['desired_level'],
            "self_level": r['self_level'],
            "assessed_level": r['assessed_level'],
            "gap": computed_gap,
            "is_gap": is_gap,
            "training_need": training_need,
            "training_status": training_status,
            "improvement_description": r['improvement_description']
        }

all_assessments = list(deduped_items.values())
gaps = [it for it in all_assessments if it['is_gap'] == 'Yes']

# Group all assessed items by employee code
gaps_by_emp = {}
for it in all_assessments:
    gaps_by_emp.setdefault(it['emp_code'], []).append(it)


# 5. Skills from DB
cur.execute("""
SELECT fs.code as skill_code, fs.name as skill_name, fs.division_id, COALESCE(f.name, 'Operations') as `function`,
       COALESCE(d.name, 'General') as department, fs.definition
FROM functional_skills fs
LEFT JOIN functions f ON f.function_id = fs.function_id
LEFT JOIN departments d ON d.department_id = fs.department_id
ORDER BY fs.name
""")
skills = cur.fetchall()

# 6. Functions from DB
cur.execute("SELECT name FROM functions ORDER BY name")
functions = [r['name'] for r in cur.fetchall()]

# 7. Departments from DB
cur.execute("SELECT name FROM departments ORDER BY name")
departments = [r['name'] for r in cur.fetchall()]

# 8. Success Behaviours from DB
cur.execute("SELECT name as behaviour, definition FROM success_behaviours ORDER BY code")
behaviours = cur.fetchall()

# 9. Roles stats from DB
cur.execute("SELECT COUNT(*) as total_roles FROM roles")
total_roles = cur.fetchone()['total_roles']

cur.execute("SELECT COUNT(*) as mapped_roles FROM roles WHERE ask_status IN ('MAPPED', 'COMPLETED', 'VALIDATED')")
mapped_roles = cur.fetchone()['mapped_roles']

# 10. Critical roles from DB
cur.execute("""
SELECT cr.critical_role_id, cr.role_id, r.title, r.division_id, f.name as fn_name,
       IF(r.division_id=1, 'Dials 1', 'Dials 2') as division,
       MAX(e.full_name) as incumbent,
       MAX(e.employee_code) as incumbent_emp_code,
       MAX(e.designation) as designation,
       'GM grade' as grade,
       'Business impact, technical scarcity, institutional knowledge, vacancy risk' as criticality_basis,
       'Business Head approved' as approved_by,
       'Approved critical' as status,
       'Active' as incumbent_status
FROM critical_roles cr
JOIN roles r ON r.role_id = cr.role_id
LEFT JOIN functions f ON f.function_id = r.function_id
LEFT JOIN employees e ON e.role_id = r.role_id AND e.status='ACTIVE'
WHERE cr.status='VALIDATED'
GROUP BY cr.critical_role_id, cr.role_id, r.title, r.division_id, f.name
ORDER BY cr.critical_role_id
""")
crit_rows = cur.fetchall()

critical_roles = []
for cr in crit_rows:
    title = cr['title']
    if title in ['HOD', 'Assistant'] and cr['fn_name']:
        formatted_title = f"{title} ({cr['fn_name']})"
    else:
        formatted_title = title

    critical_roles.append({
        "role_id": f"CR{cr['critical_role_id']:02d}",
        "critical_role_id": cr['critical_role_id'],
        "role_title": formatted_title,
        "division": cr['division'],
        "division_id": cr['division_id'],
        "incumbent": cr['incumbent'] or "To be designated",
        "incumbent_emp_code": cr['incumbent_emp_code'],
        "designation": cr['designation'] or "HOD / Manager",
        "grade": cr['grade'],
        "criticality_basis": cr['criticality_basis'],
        "approved_by": cr['approved_by'],
        "status": cr['status'],
        "incumbent_status": cr['incumbent_status']
    })

# Mark critical role incumbents in employees list
crit_emp_codes = set(cr['incumbent_emp_code'] for cr in critical_roles if cr['incumbent_emp_code'])
for emp in employees:
    if emp['emp_code'] in crit_emp_codes:
        emp['person_type'] = "Critical-role incumbent"

# 11. Succession candidates from DB
cur.execute("""
SELECT sc.critical_role_id, sc.candidate_employee_id, e.full_name as candidate_name,
       e.employee_code as candidate_emp_code, sc.readiness_level, sc.readiness_label, sc.notes
FROM succession_candidates sc
JOIN employees e ON e.employee_id = sc.candidate_employee_id
""")
candidates = cur.fetchall()

cand_by_role = {}
for c in candidates:
    cand_by_role.setdefault(c['critical_role_id'], []).append(c)

# Build succession slates for critical roles
critical_slates = []
for i, cr in enumerate(critical_roles):
    cands = cand_by_role.get(cr['critical_role_id'], [])
    ready_now = next((c['candidate_name'] for c in cands if c['readiness_level'] == 1), None)
    one_move = next((c['candidate_name'] for c in cands if c['readiness_level'] == 2), None)
    emergency = next((c['candidate_name'] for c in cands if c['readiness_level'] == 3), None)

    if ready_now:
        status = "Ready now"
    elif one_move or emergency:
        status = "Successor(s) named"
    else:
        status = "No successor named"

    critical_slates.append({
        "slate_id": f"S{i+1:02d}",
        "critical_role_id": cr['critical_role_id'],
        "role_title": cr['role_title'],
        "division": cr['division'],
        "incumbent": cr['incumbent'],
        "incumbent_emp_code": cr['incumbent_emp_code'],
        "designation": cr['designation'],
        "grade": cr['grade'],
        "is_critical": "Yes",
        "emergency_successor": emergency,
        "ready_now": ready_now,
        "one_move": one_move,
        "two_move": None,
        "successor_status": status,
        "remarks": None,
        "incumbent_status": "Active"
    })

# 12. Non-critical succession slates: only if defined in DB
non_critical_slates = []

pending_codes = ["DEMO-101", "D2-EMP-059"]

# Roles list from DB
cur.execute("""
SELECT r.role_id, r.title, r.division_id,
       COALESCE(f.name, 'Operations') as `function`,
       IF(r.division_id=1, 'Dials 1', 'Dials 2') as division,
       r.description_status, r.ask_status
FROM roles r
LEFT JOIN functions f ON f.function_id = r.function_id
ORDER BY r.title
""")
all_roles = cur.fetchall()

db_data = {
    "manpower": manpower,
    "assessedCounts": {
        "COMBINED": len(assessed_map),
        "DIAL1": sum(1 for e in employees if e['is_assessed'] and e['division_id'] == 1),
        "DIAL2": sum(1 for e in employees if e['is_assessed'] and e['division_id'] == 2)
    },
    "managerPending": {
        "COMBINED": 2,
        "DIAL1": 1,
        "DIAL2": 1,
        "employees": [
            {"name": "Dev Malhotra", "code": "DEMO-101", "division": "Dials 1", "designation": "Plant Quality Manager", "function": "Quality"},
            {"name": "Pushp Raj", "code": "D2-EMP-059", "division": "Dials 2", "designation": "Assistant Officer", "function": "Design"}
        ]
    },
    "pendingEmpCodes": pending_codes,
    "employees": employees,
    "gaps": gaps,
    "allAssessments": all_assessments,
    "gapsByEmployee": gaps_by_emp,
    "criticalRoles": critical_roles,
    "criticalRolesSlates": critical_slates,
    "criticalSlates": critical_slates,
    "nonCriticalRolesSlates": non_critical_slates,
    "nonCriticalSlates": non_critical_slates,
    "skills": skills,
    "functions": functions,
    "departments": departments,
    "successBehaviours": behaviours,
    "rolesCount": total_roles,
    "askMappedRoles": mapped_roles,
    "roles": all_roles
}

with open('./frontend/src/app/data/kddlDbData.json', 'w', encoding='utf-8') as f:
    json.dump(db_data, f, indent=2, default=str)

print("Saved frontend/src/app/data/kddlDbData.json successfully!")
print(f"Total employees: {len(employees)}, Total gaps: {len(gaps)}, Total critical roles: {len(critical_roles)}")
print("Manpower:", manpower)
conn.close()
