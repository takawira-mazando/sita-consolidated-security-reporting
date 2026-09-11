import json
from app.lake.writer import record_to_finding
from app.tenant import department_for_app, branch_for_app

with open('C:/sita-platform/backend/appscan_real_issues.json', 'r') as f:
    real_issues = json.load(f)

issue = real_issues[0]
record = {
    'external_id': str(issue.get('Id')),
    'app_name': 'xyz application',
    'title': issue.get('IssueType'),
    'description': f"{issue.get('IssueType')} found at {issue.get('Location')}",
    'category': f"CWE-{issue.get('Cwe')}" if issue.get('Cwe') else None,
    'first_seen': issue.get('DateCreated'),
    'last_seen': issue.get('LastFound') or issue.get('LastUpdated'),
    'status': issue.get('Status', 'Open'),
    'severity': 'medium',
    'raw_data': issue,
    'source': 'appscan_real',
}

print('Testing record_to_finding...')
result = record_to_finding(record, 'appscan_real')
print('Result keys:', result.keys())
print('app_name:', result.get('app_name'))
print('department_id:', result.get('department_id'))
print('branch_id:', result.get('branch_id'))
print('ministry_id:', result.get('ministry_id'))
print('cluster_id:', result.get('cluster_id'))