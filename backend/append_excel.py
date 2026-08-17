from datetime import datetime

import openpyxl

file_path = r"C:\Users\HosiTech\Downloads\HOSI-UNIFIED DATA MANAGED SERVICE PROJECT FLIGHT PLAN 2026.xlsx"
wb = openpyxl.load_workbook(file_path)
ws = wb["Project Plan "]

today = datetime.now().strftime("%Y-%m-%d 00:00:00")

# Add a spacer row
ws.append([])

# Add Phase header (Column B)
ws.append([None, "Phase 12: Static Application Security Testing (SAST)"])

# Add Tasks
ws.append([
    None,
    None,
    "Backend SAST Setup & Scan (Bandit)",
    "Completed",
    1,
    today,
    today,
    "Lead Dev",
    "Bandit configured via pyproject.toml and integrated"
])

ws.append([
    None,
    None,
    "Frontend SAST Setup & Scan (Semgrep)",
    "Completed",
    1,
    today,
    today,
    "Lead Dev",
    "Semgrep installed and React components scanned"
])

ws.append([
    None,
    None,
    "Vulnerability Remediation",
    "Completed",
    1,
    today,
    today,
    "Lead Dev",
    "DOMPurify implemented, Dockerfile secured, Bandit suppressions added"
])

wb.save(file_path)
print("SAST deliverables successfully added to Project Plan.")
