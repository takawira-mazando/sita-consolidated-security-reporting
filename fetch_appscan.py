import requests, json

token = 'i_Hrfjn7ihujuyDUqniWJl32JnL-IUi-'
headers = {'Authorization': f'Bearer {token}'}

# Get issues for the app
r = requests.get('https://cloud.appscan.com/api/v4/Issues?AppId=b816b09c-4240-4ea7-a4b5-f8ae89f62f57', headers=headers)
print(r.status_code)
data = r.json()
items = data.get('Items', [])
print(f'Total issues: {len(items)}')
for item in items[:10]:
    print(f"  - {item.get('Name')} | Severity: {item.get('Severity')} | Type: {item.get('IssueType')}")

# Get full details for critical/high issues
critical_high = [i for i in items if i.get('Severity') in ['Critical', 'High']]
print(f'\nCritical/High issues: {len(critical_high)}')
for item in critical_high:
    print(f"\n--- {item.get('Name')} ---")
    print(f"  Severity: {item.get('Severity')}")
    print(f"  Type: {item.get('IssueType')}")
    print(f"  URL: {item.get('Url')}")
    print(f"  Description: {item.get('Description')[:200]}...")
    print(f"  Remediation: {item.get('Remediation')[:200] if item.get('Remediation') else 'N/A'}...")

# Save all issues to file
with open('C:\\sita-platform\\appscan_issues.json', 'w') as f:
    json.dump(data, f, indent=2)
print('\nSaved all issues to C:\\sita-platform\\appscan_issues.json')