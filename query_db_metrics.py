import pymysql

conn = pymysql.connect(host='localhost', user='root', password='Sahil@123', database='kddl_neww', port=3306, autocommit=True)
cur = conn.cursor()

# 1. Total employees in DB
cur.execute("SELECT COUNT(*) FROM employees WHERE status='ACTIVE'")
print("Active employees in DB:", cur.fetchone()[0])

cur.execute("SELECT division_id, COUNT(*) FROM employees WHERE status='ACTIVE' GROUP BY division_id")
print("Active employees by division:", cur.fetchall())

# 2. Assessed employees in DB
cur.execute("""
SELECT e.division_id, COUNT(DISTINCT af.employee_id)
FROM assessment_forms af
JOIN employees e ON e.employee_id = af.employee_id
WHERE af.status != 'NOT_STARTED'
GROUP BY e.division_id
""")
print("Assessed employees by division:", cur.fetchall())

# 3. Pending assessments
cur.execute("""
SELECT af.employee_id, e.full_name, e.employee_code, e.division_id, e.designation, f.name as fn_name
FROM assessment_forms af
JOIN employees e ON e.employee_id = af.employee_id
LEFT JOIN functions f ON f.function_id = e.function_id
WHERE af.status = 'SELF_SUBMITTED'
""")
print("Pending assessments in DB:")
for r in cur.fetchall():
    print(r)

# 4. Gaps in DB
cur.execute("""
SELECT e.division_id, COUNT(*)
FROM assessment_line_items ali
JOIN assessment_forms af ON af.form_id = ali.form_id
JOIN employees e ON e.employee_id = af.employee_id
WHERE ali.gap < 0
GROUP BY e.division_id
""")
print("Gaps by division in DB:", cur.fetchall())

conn.close()
