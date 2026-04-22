import requests

# Добавить рабочий день
response = requests.post(
    'http://localhost:8000/api/admin/add-work-day',
    headers={'X-Admin-Secret-Key': 'default-secret'},
    json={
        'date': '2026-04-22',
        'time_slots': ['10:00', '11:00', '12:00', '14:00', '15:00']
    }
)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")