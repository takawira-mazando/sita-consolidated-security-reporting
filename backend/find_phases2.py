import openpyxl

file_path = r"C:\Users\HosiTech\Downloads\HOSI-UNIFIED DATA MANAGED SERVICE PROJECT FLIGHT PLAN 2026.xlsx"
wb = openpyxl.load_workbook(file_path)
ws = wb["Project Plan "]

for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
    for cell in row:
        if cell and isinstance(cell, str):
            if "Phase 11" in cell or "Phase 12" in cell or "Phase 13" in cell:
                print(f"Row {row_idx}: {cell}")
                break
