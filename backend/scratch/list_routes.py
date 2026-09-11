import re

files = [
    'app/api/routers/admin.py',
    'app/api/routers/metrics.py',
    'app/api/routers/findings.py',
]

for fname in files:
    try:
        with open(fname) as f:
            content = f.read()
        routes = re.findall(r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', content)
        prefix_match = re.search(r'APIRouter\(prefix=["\']([^"\']+)["\']', content)
        prefix = prefix_match.group(1) if prefix_match else ''
        print(f'{fname} (prefix="{prefix}"):')
        for method, path in routes:
            print(f'  {method.upper():<8} {prefix}{path}')
    except Exception as e:
        print(f'{fname}: ERROR {e}')
