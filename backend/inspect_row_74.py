import openpyxl

file_path = r"C:\Users\HosiTech\Downloads\HOSI-UNIFIED DATA MANAGED SERVICE PROJECT FLIGHT PLAN 2026.xlsx"
wb = openpyxl.load_workbook(file_path)
ws = wb["Project Plan "]

row_74_data = []
for col in range(1, 10):
    cell = ws.cell(row=74, column=col)
    row_74_data.append((cell.value, cell.number_format))
    
print("Row 74:", row_74_data)
