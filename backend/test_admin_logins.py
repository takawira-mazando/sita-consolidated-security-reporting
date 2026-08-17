import re
import time

import httpx


def test_logins():
    with open('C:\\Users\\HosiTech\\.gemini\\antigravity-ide\\brain\\a54c9896-ca59-4b4d-b434-6d467c42f22e\\admin_credentials.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple regex to extract email and password from the markdown tables
    # Looking for lines like: | name | `email` | `password` | scope |
    # and: - **Email:** `admin@example.com`
    #      - **Password:** `admin123` *(existing)*
    
    accounts = []
    
    # Extract from lists
    email_matches = re.findall(r'- \*\*Email:\*\* `([^`]+)`', content)
    pwd_matches = re.findall(r'- \*\*Password:\*\* `([^`]+)`', content)
    for email, pwd in zip(email_matches, pwd_matches):
        accounts.append((email, pwd))
        
    # Extract from tables
    for line in content.splitlines():
        if not line.startswith('|'):
            continue
        ticks = re.findall(r'`([^`]+)`', line)
        if len(ticks) >= 2:
            email = ticks[0].strip()
            pwd = ticks[1].strip()
            if '@' in email:
                accounts.append((email, pwd))

    print(f"Found {len(accounts)} accounts to test.")
    
    success = 0
    failed = 0
    
    for email, pwd in accounts:
        try:
            r = httpx.post("http://localhost:8000/api/v1/auth/login", json={"email": email, "password": pwd})
            if r.status_code == 200:
                data = r.json()
                print(f"[OK] {email} - Logged in successfully (roles: {data['user'].get('roles')})")
                success += 1
            else:
                print(f"[FAIL] {email} - HTTP {r.status_code} - {r.text}")
                failed += 1
            time.sleep(1) # Prevent 429 Too Many Requests
        except Exception as e:
            print(f"[ERROR] {email} - {str(e)}")
            failed += 1
            
    print(f"\nResults: {success} successful, {failed} failed.")

if __name__ == '__main__':
    test_logins()
