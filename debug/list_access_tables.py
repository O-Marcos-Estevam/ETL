import pyodbc
import sys
import os

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except: pass

db_path = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\02. Dev\ETL\Base Fundos_V2 - Copia.accdb'
conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + db_path + ';'

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    with open('table_list_safe.txt', 'w', encoding='utf-8') as f:
        print("Listing Tables:")
        for row in cursor.tables():
            if row.table_type == 'TABLE':
                print(f"- {row.table_name}")
                f.write(f"{row.table_name}\n")
            
    conn.close()
except Exception as e:
    print(f"Error: {e}")
