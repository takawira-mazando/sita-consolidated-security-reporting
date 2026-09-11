import json
import pandas as pd
from app.processing.normaliser import Normaliser
from app.lake.writer import record_to_finding

with open('C:/sita-platform/backend/appscan_real_issues.json', 'r') as f:
    real_issues = json.load(f)

issue = real_issues[0]
record = {
    'source': 'appscan',
    'external_id': str(issue.get('Id')),
    'application_name': 'xyz application',
    'vulnerability_name': issue.get('IssueType'),
    'description': f"{issue.get('IssueType')} found at {issue.get('Location')}",
    'owasp_category': f"CWE-{issue.get('Cwe')}" if issue.get('Cwe') else None,
    'severity': issue.get('Severity'),
    'status': issue.get('Status', 'Open'),
    'first_found_date': issue.get('DateCreated'),
    'last_found_date': issue.get('LastFound') or issue.get('LastUpdated'),
    'cve': issue.get('Cve'),
    'cvss': issue.get('Cvss'),
    'raw_data': issue,
}

normaliser = Normaliser()
df = normaliser.normalise(pd.DataFrame([record]), 'appscan')
if df is not None and not df.empty:
    row = df.to_dict(orient='records')[0]
    row["source"] = "appscan_real"
    print('Normalized row:', row)
    print()
    result = record_to_finding(row, 'appscan_real')
    print('record_to_finding result:')
    print('  app_name:', result.get('app_name'))
    print('  department_id:', result.get('department_id'))
    print('  branch_id:', result.get('branch_id'))
    print('  external_id:', result.get('external_id'))