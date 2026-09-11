import requests, json

token = 'i_Hrfjn7ihujuyDUqniWJl32JnL-IUi-'
headers = {'Authorization': f'Bearer {token}'}

# Correct issues endpoint: /api/v4/Issues/{scope}/{scopeId}
url = 'https://cloud.appscan.com/api/v4/Issues/App/b816b09c-4240-4ea7-a4b5-f8ae89f62f57'
r = requests.get(url, headers=headers)
print(f'Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    items = data.get('Items', data) if isinstance(data, dict) else data
    if isinstance(items, list):
        print(f'Total issues: {len(items)}')
        for item in items[:10]:
            print(f"  - {item.get('Name')} | Severity: {item.get('Severity')} | Type: {item.get('IssueType')}")
        
        # Save
        with open('C:\\sita-platform\\appscan_issues.json', 'w') as f:
            json.dump(data, f, indent=2)
        print('Saved to appscan_issues.json')
    else:
        print(f'Unexpected format: {type(items)}')
        print(json.dumps(data, indent=2)[:2000])
else:
    print(r.text[:1000])