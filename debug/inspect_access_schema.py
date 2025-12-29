import pyodbc
import sys

# Encoding fix
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except: pass

db_path = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\03. Arquivos Rotina\01. BD\Base Fundos_v2.accdb'
tables_to_check = ['Renda_Variável_Qore', 'Caixa_Qore', 'Cotas_Patrimonio_Qore', 'Passivo_Qore']

conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + db_path + ';'

try:
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
