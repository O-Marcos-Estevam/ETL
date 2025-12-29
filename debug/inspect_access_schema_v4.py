import pyodbc
import sys
import os

# Encoding fix
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except: pass

db_path = r'C:\bloko\Fundos - Documentos\00. Monitoramento\01. Rotinas\02. Dev\ETL\Base Fundos_V2 - Copia.accdb'
tables_to_check = ['Renda_Variável_Qore', 'Caixa_Qore', 'Passivo_Qore', 'Cotas_Patrimonio_Qore']

conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + db_path + ';'

print(f"Drivers: {pyodbc.drivers()}")

try:
    if not os.path.exists(db_path):
        print(f"DB not found: {db_path}")
        sys.exit(1)
        
    print(f"Connecting to {db_path}...")
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    with open('schema_safe_log.txt', 'w', encoding='utf-8') as f:
        for table in tables_to_check:
            msg_table = f"\n--- TABLE: {table} ---"
            print(msg_table)
            f.write(msg_table + "\n")
            try:
                cursor.execute(f"SELECT TOP 1 * FROM {table}")
                columns = [column[0] for column in cursor.description]
                msg_cols = f"Columns: {columns}"
                print(msg_cols)
                f.write(msg_cols + "\n")
            except Exception as e:
                msg_err = f"Error querying {table}: {e}"
                print(msg_err)
                f.write(msg_err + "\n")
    
    conn.close()

except Exception as e:
    print(f"Connection failed: {e}")
