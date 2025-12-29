import openpyxl
import os

file_path = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\02. Dev\ETL\Relatórios\Novo\CARTEIRA_DIARIA_55523261_08-12-2025-5d6909a2-64d7-4af2-8ecd-0dba2748e744.xlsx'
output_file = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\02. Dev\ETL\inspect_excel_columns.txt'

try:
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb.active
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Inspecting: {os.path.basename(file_path)}\n\n")
        
        for i, row in enumerate(ws.iter_rows(max_row=30, max_col=10, values_only=True)):
            # Print row index and non-none values
            clean_row = [str(cell) if cell is not None else "" for cell in row]
            f.write(f"Row {i}: {clean_row}\n")

    print(f"Saved inspection to {output_file}")

except Exception as e:
    print(f"Error: {e}")
