
def main():
    with open('new_credentials.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    accounts = []
    current = {}
    for line in lines:
        line = line.strip()
        if not line:
            if current:
                accounts.append(current)
                current = {}
            continue
        parts = line.split(': ', 1)
        if len(parts) == 2:
            current[parts[0]] = parts[1]
    if current:
        accounts.append(current)

    md = []
    md.append('# Administrator Credentials\n\nThese credentials have been generated and seeded into the database. Please store them securely in a password manager and rotate the passwords after your first login.\n\n')

    md.append('## System Admin (Tier 4)\n')
    md.append('- **Role:** System Admin\n- **Scope:** National Estate\n- **Email:** `admin@example.com`\n- **Password:** `admin123` *(existing)*\n\n')

    md.append('## National Superadmins (Tier 3)\n| Name | Role | Email | Password | Scope |\n|---|---|---|---|---|\n')
    for a in accounts:
        if a.get('Role', '').startswith('National Superadmin'):
            name = a['Role'].split('(')[1].rstrip(')')
            md.append(f"| {name} | Transversal Admin | `{a['Email']}` | `{a['Password']}` | {a['Scope']} |\n")
    md.append('\n')

    md.append('## Department Admins (Tier 2)\n| Name | Email | Password | Department Scope |\n|---|---|---|---|\n')
    for a in accounts:
        if a.get('Role') == 'Dept Admin':
            name = a['Scope'].title() + ' Dept Admin'
            md.append(f"| {name} | `{a['Email']}` | `{a['Password']}` | `{a['Scope']}` |\n")
    md.append('\n')

    md.append('## Branch Admins (Tier 1)\n| Name | Email | Password | Branch Scope |\n|---|---|---|---|\n')
    for a in accounts:
        if a.get('Role') == 'Branch Admin':
            name = a['Scope'].split('/')[1].strip().title() + ' Branch Admin'
            md.append(f"| {name} | `{a['Email']}` | `{a['Password']}` | `{a['Scope']}` |\n")

    md.append('\n> [!CAUTION]\n> These are raw, plain-text credentials for high-privileged accounts on the platform. Delete this artifact once you have securely backed them up to your enterprise password vault.\n')

    with open(r'C:\Users\HosiTech\.gemini\antigravity-ide\brain\a54c9896-ca59-4b4d-b434-6d467c42f22e\admin_credentials.md', 'w', encoding='utf-8') as f:
        f.writelines(md)

if __name__ == "__main__":
    main()
