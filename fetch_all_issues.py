import requests, json

token = 'i_Hrfjn7ihujuyDUqniWJl32JnL-IUi-'
headers = {'Authorization': f'Bearer {token}'}

url = 'https://cloud.appscan.com/api/v4/Issues/Application/b816b09c-4240-4ea7-a4b5-f8ae89f62f57'
r = requests.get(url, headers=headers)
print(f'Status: {r.status_code}')

if r.status_code == 200:
    data = r.json()
    items = data.get('Items', data) if isinstance(data, dict) else data
    if isinstance(items, list):
        print(f'Total issues: {len(items)}')
        
        sev_counts = {}
        for item in items:
            sev = item.get('Severity', 'Unknown')
            sev_counts[sev] = sev_counts.get(sev, 0) + 1
        print('By severity:', sev_counts)
        
        print('\n=== CRITICAL & HIGH ISSUES ===')
        for item in items:
            if item.get('Severity') in ['Critical', 'High']:
                name = item.get('Name') or 'N/A'
                desc = item.get('Description') or 'No description'
                rem = item.get('Remediation') or 'No remediation'
                print(f"\n--- {name} ---")
                print(f"  Severity: {item.get('Severity')}")
                print(f"  Type: {item.get('IssueType')}")
                print(f"  Location: {item.get('Location')}")
                print(f"  Description: {desc[:300]}...")
                print(f"  Remediation: {rem[:300]}...")
        
        # Save all
        with open('C:\\sita-platform\\appscan_issues.json', 'w') as f:
            json.dump(data, f, indent=2)
        print('\nSaved to appscan_issues.json')
    else:
        print(f'Unexpected format: {type(items)}')
else:
    print(r.text[:1000])