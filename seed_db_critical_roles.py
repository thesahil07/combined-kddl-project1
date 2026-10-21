import pymysql

conn = pymysql.connect(host='localhost', user='root', password='Sahil@123', database='kddl_neww', port=3306, autocommit=True)
cur = conn.cursor()

# Get 8 leadership roles for Division 1
cur.execute("""
SELECT role_id, title FROM roles
WHERE tenant_id=1 AND division_id=1
ORDER BY role_id
LIMIT 8
""")
div1_roles = cur.fetchall()

# Get 7 leadership roles for Division 2
cur.execute("""
SELECT role_id, title FROM roles
WHERE tenant_id=1 AND division_id=2
ORDER BY role_id
LIMIT 7
""")
div2_roles = cur.fetchall()

all_selected_roles = div1_roles + div2_roles
print(f"Selected {len(all_selected_roles)} roles:")
for r in all_selected_roles:
    print(r)

# Clear existing critical_roles and candidates if any
cur.execute("DELETE FROM succession_candidates WHERE tenant_id=1")
cur.execute("DELETE FROM critical_roles WHERE tenant_id=1")

# Insert 15 validated critical roles
inserted_critical_ids = []
for role_id, title in all_selected_roles:
    cur.execute("""
        INSERT INTO critical_roles (tenant_id, role_id, criteria_business_impact, criteria_technical_scarcity,
                                    criteria_institutional_knowledge, criteria_vacancy_risk, criteria_thin_succession_depth,
                                    tier, risk_situation, status, validated_at)
        VALUES (1, %s, 1, 1, 1, 0, 1, 'TIER1', 'SITUATION_1_CRITICAL', 'VALIDATED', NOW())
    """, (role_id,))
    inserted_critical_ids.append(cur.lastrowid)

print(f"Inserted {len(inserted_critical_ids)} critical roles into critical_roles table.")

# Get potential candidate employees for succession
cur.execute("SELECT employee_id FROM employees WHERE tenant_id=1 AND status='ACTIVE' LIMIT 20")
candidate_emps = [r[0] for r in cur.fetchall()]

# We want 9 roles to have successors named (and 1 of them to be Ready Now), 6 without successor
# 1st role: Ready now (readiness_level=1)
cur.execute("""
    INSERT INTO succession_candidates (tenant_id, critical_role_id, candidate_employee_id, readiness_level, readiness_label, estimated_ready_date, notes)
    VALUES (1, %s, %s, 1, 'Ready now (< 6 months)', DATE_ADD(CURRENT_DATE, INTERVAL 3 MONTH), 'Demonstrated readiness')
""", (inserted_critical_ids[0], candidate_emps[0]))

# Next 8 roles: 1-2 moves (readiness_level=2 or 3)
for i in range(1, 9):
    cur.execute("""
        INSERT INTO succession_candidates (tenant_id, critical_role_id, candidate_employee_id, readiness_level, readiness_label, estimated_ready_date, notes)
        VALUES (1, %s, %s, 2, '1 move away (6-18 months)', DATE_ADD(CURRENT_DATE, INTERVAL 12 MONTH), 'Candidate identified')
    """, (inserted_critical_ids[i], candidate_emps[i]))

# The remaining 6 roles (indices 9 to 14) have NO candidate inserted -> without_successor = 6!

cur.execute("SELECT COUNT(*) FROM critical_roles WHERE status='VALIDATED'")
print("Validated critical roles count in DB:", cur.fetchone()[0])

cur.execute("""
SELECT COUNT(*) FROM critical_roles cr
WHERE cr.status='VALIDATED'
  AND NOT EXISTS (SELECT 1 FROM succession_candidates sc WHERE sc.critical_role_id=cr.critical_role_id)
""")
print("Critical roles without successor in DB:", cur.fetchone()[0])

conn.close()
