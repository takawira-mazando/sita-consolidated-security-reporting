import openpyxl

file_path = r"C:\Users\HosiTech\Downloads\HOSI-UNIFIED DATA MANAGED SERVICE PROJECT FLIGHT PLAN 2026.xlsx"
wb = openpyxl.load_workbook(file_path)
ws = wb["Project Plan "]

with open("excel_dump2.txt", "w", encoding="utf-8") as f:
    for i in range(70, 96):
        row_data = []
        for cell in ws[i]:
            row_data.append(str(cell.value).replace('\n', ' ')[:30] if cell.value else "")
        f.write(f"Row {i}: {row_data}\n")
