import pyodbc
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except: pass

db_path = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\02. Dev\ETL\Base Fundos_V2 - Copia.accdb'
tables_to_check = ['Renda_Fixa_Qore', 'Renda_Variavel_A_Vista', 'Caixa_Qore']

conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + db_path + ';'

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    with open('proxy_schema_log.txt', 'w', encoding='utf-8') as f:
        for table in tables_to_check:
            print(f"Inspecting {table}...")
            f.write(f"\n--- {table} ---\n")
            try:
                cursor.execute(f"SELECT TOP 1 * FROM {table}")
                cols = [c[0] for c in cursor.description]
                print(cols)
                f.write(f"{cols}\n")
            except Exception as e:
                print(f"Error: {e}")
                f.write(f"Error: {e}\n")

    conn.close()
except Exception as e:
    print(f"Conn Error: {e}")
