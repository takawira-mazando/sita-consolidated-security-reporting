import openpyxl

file_path = r"C:\Users\HosiTech\Downloads\HOSI-UNIFIED DATA MANAGED SERVICE PROJECT FLIGHT PLAN 2026.xlsx"
wb = openpyxl.load_workbook(file_path)
ws = wb["Project Plan "]

# Add a spacer row
ws.append([])

# Add Phase header (Column B)
ws.append([None, "Phase 13: Multi-Tenancy Architecture Implementation"])

# Task 1: Last week Friday (2026-08-07)
ws.append([
    None,
    None,
    "Tenancy Hierarchical Model & RLS Implementation",
    "Completed",
    1,
    "2026-08-07 00:00:00",
    "2026-08-07 00:00:00",
    "Lead Dev",
    "Implemented 3-Tier Tenancy tree and Row-Level Security via SQLAlchemy tenant_filter"
])

# Task 2: Yesterday (2026-08-11)
ws.append([
    None,
    None,
    "Delegated RBAC & Tenancy Documentation",
    "Completed",
    1,
    "2026-08-11 00:00:00",
    "2026-08-11 00:00:00",
    "Lead Dev",
    "Enforced strict downward role delegation and generated Stakeholder Tenancy Explainer docs"
])

wb.save(file_path)
print("Tenancy deliverables successfully added to Project Plan.")
