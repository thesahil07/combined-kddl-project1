import urllib.request, json

login_data = json.dumps({'email': 'hr.spoc@demo.kddl.local', 'password': 'KddlDemo!2026'}).encode('utf-8')
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/login', data=login_data, headers={'Content-Type': 'application/json'})
token = json.loads(urllib.request.urlopen(req).read().decode())['access_token']

req2 = urllib.request.Request('http://127.0.0.1:8000/api/v1/admin-console/assessment-report?page=1&page_size=10', headers={'Authorization': f'Bearer {token}'})
data = json.loads(urllib.request.urlopen(req2).read().decode())
print('Total employees:', data['total_employees'])
for e in data['employees']:
    print(f"{e['full_name']} ({e['employee_code']}): b_self={e['behaviour_self_status']}, f_self={e['functional_self_status']}, b_gaps={e['behaviour_gaps']}, f_gaps={e['functional_gaps']}")
