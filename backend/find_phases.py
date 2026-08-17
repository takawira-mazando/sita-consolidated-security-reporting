import openpyxl

file_path = r"C:\Users\HosiTech\Downloads\HOSI-UNIFIED DATA MANAGED SERVICE PROJECT FLIGHT PLAN 2026.xlsx"
wb = openpyxl.load_workbook(file_path)
ws = wb["Project Plan "]

for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
    row_str = str(row)
    if "Phase 11" in row_str or "Phase 12" in row_str or "Phase 13" in row_str or "SAST" in row_str or "Tenancy" in row_str:
        print(f"Row {row_idx}: {row}")
