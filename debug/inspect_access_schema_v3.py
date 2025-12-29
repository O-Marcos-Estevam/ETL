import pyodbc
import sys
import os

# Encoding fix
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except: pass

db_path = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\02. Dev\ETL\temp_base.accdb'
tables_to_check = ['Renda_Variável_Qore', 'Caixa_Qore', 'Passivo_Qore']

conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + db_path + ';'

try:
    if not os.path.exists(db_path):
        print(f"DB not found: {db_path}")
        sys.exit(1)
        
    print(f"Connecting to {db_path}...")
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    for table in tables_to_check:
        print(f"\n--- TABLE: {table} ---")
        try:
            cursor.execute(f"SELECT TOP 1 * FROM {table}")
            columns = [column[0] for column in cursor.description]
            print(f"Columns: {columns}")
        except Exception as e:
            print(f"Error querying {table}: {e}")

    conn.close()

except Exception as e:
    print(f"Connection failed: {e}")
