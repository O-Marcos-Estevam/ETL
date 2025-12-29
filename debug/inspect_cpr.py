import pyodbc
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except: pass

db_path = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\02. Dev\ETL\Base Fundos_V2 - Copia.accdb'
table = 'CPR_QORE'
conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + db_path + ';'

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    print(f"Inspecting {table}...")
    cursor.execute(f"SELECT TOP 1 * FROM {table}")
    cols = [c[0] for c in cursor.description]
    print(cols)
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
