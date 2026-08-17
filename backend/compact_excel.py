import openpyxl

file_path = r"C:\Users\HosiTech\Downloads\HOSI-UNIFIED DATA MANAGED SERVICE PROJECT FLIGHT PLAN 2026.xlsx"
wb = openpyxl.load_workbook(file_path)
ws = wb["Project Plan "]

for i in range(70, 98):
    row_data = [str(cell.value) if cell.value else "" for cell in ws[i]]
    if any(row_data):
        print(f"{i}: {row_data[:5]}")
